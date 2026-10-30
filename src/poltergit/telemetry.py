"""Content-free local traces, optionally mirrored into Sentry Agent Monitoring."""

import json
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime

import sentry_sdk

from .config import Settings


def configure(settings: Settings) -> None:
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn, traces_sample_rate=1.0,
            send_default_pii=False, include_local_variables=False,
            default_integrations=False, environment="local",
            stream_gen_ai_spans=False,
            # Only explicitly instrumented transactions; no errors with source locals.
            before_send=lambda event, hint: None,
        )


class Trace:
    def __init__(self, settings: Settings, operation: str = "séance"):
        self.settings = settings
        self.operation = operation
        self.id = uuid.uuid4().hex
        self.spans: list[dict] = []

    def __enter__(self):
        self.started = time.perf_counter()
        self.transaction = sentry_sdk.start_transaction(name=f"poltergit.{self.operation}", op="gen_ai.invoke_agent")
        self.transaction.__enter__()
        self.transaction.set_data("gen_ai.agent.name", "Poltergit")
        self.transaction.set_data("gen_ai.operation.name", "invoke_agent")
        if self.settings.sentry_dsn:
            self.id = self.transaction.trace_id
        return self

    @contextmanager
    def step(self, name: str, op: str = "function", **attributes):
        start = time.perf_counter()
        record = {"name": name, "op": op, "status": "ok", "start_ms": round((start - self.started) * 1000, 2)}
        with self.transaction.start_child(op=op, name=name) as span:
            try:
                yield attributes
            except Exception as exc:
                record["status"] = "error"
                record["error_type"] = type(exc).__name__
                span.set_status("internal_error")
                raise
            finally:
                for key, value in attributes.items():
                    span.set_data(key, value)
                record["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
                record["attributes"] = attributes
                self.spans.append(record)

    def __exit__(self, exc_type, exc, tb):
        self.transaction.__exit__(exc_type, exc, tb)
        document = {"trace_id": self.id, "operation": self.operation,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "duration_ms": round((time.perf_counter() - self.started) * 1000, 2),
                    "status": "error" if exc else "ok", "spans": self.spans}
        try:
            target = self.settings.state_dir / "traces"
            target.mkdir(parents=True, exist_ok=True)
            (target / f"{self.id}.json").write_text(json.dumps(document, indent=2), encoding="utf-8")
        except OSError:
            # Telemetry must not break a successfully answered question.
            pass

