import os

import httpx
import pytest
import sentry_sdk
from sentry_sdk.transport import Transport

from poltergit.config import Settings
from poltergit.github import enrich
from poltergit.ollama import ModelError, Ollama
from poltergit.search import SearchError, index_repository, search
from poltergit.telemetry import Trace


def test_github_reads_pr_reviews_and_linked_issues(repo, monkeypatch):
    base = "https://github.com/example/haunted"
    seen = []

    def respond(request):
        seen.append(request.url.path)
        path = request.url.path
        if path.endswith('/pulls'):
            data = [{"id": 1, "number": 10, "title": "Fix reconnects", "body": "Fixes #11", "html_url": base + "/pull/10"}]
        elif path.endswith('/issues/11'):
            data = {"id": 2, "title": "Gateway reservation", "body": "Wait for the reservation", "html_url": base + "/issues/11"}
        elif path.endswith('/pulls/10/comments'):
            data = [{"id": 3, "body": "The three-second wait is required.", "html_url": base + "/pull/10#discussion_r3"}]
        else:
            data = []
        return httpx.Response(200, json=data)

    original = httpx.Client
    monkeypatch.setattr('poltergit.github.httpx.Client', lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(respond)))
    sources, warnings = enrich(base, repo.history("src/client.py:13").evidence)
    assert {s.kind for s in sources} == {"pull_request", "issue", "comment"}
    assert len(sources) == 3
    assert not warnings
    assert '/repos/example/haunted/pulls/10/comments' in seen


def test_github_rate_limit_preserves_local_history(repo, monkeypatch):
    original = httpx.Client
    transport = httpx.MockTransport(lambda request: httpx.Response(403, json={"message": "Rate limit"}))
    monkeypatch.setattr('poltergit.github.httpx.Client', lambda **kwargs: original(**kwargs, transport=transport))
    sources, warnings = enrich("https://github.com/example/haunted", repo.history("src/client.py:13").evidence)
    assert sources == []
    assert "HTTP 403" in warnings[0]


def test_embedding_shape_and_nan_are_validated(monkeypatch):
    monkeypatch.setattr(Ollama, "request", lambda *args: {"embeddings": [[0.0] * 767 + [float('nan')]]})
    with pytest.raises(ModelError):
        Ollama(Settings()).embed(["history"])


def test_sentry_transaction_contains_agent_metrics_but_no_source(tmp_path):
    envelopes = []

    class MemoryTransport(Transport):
        def capture_envelope(self, envelope):
            envelopes.append(envelope)

    with sentry_sdk.init(dsn="https://public@example.invalid/1", transport=MemoryTransport,
                         traces_sample_rate=1.0, default_integrations=False,
                         stream_gen_ai_spans=False):
        with Trace(Settings(sentry_dsn="configured", state_dir=tmp_path)) as trace:
            with trace.step("Let the line speak", "gen_ai.chat", **{
                "gen_ai.request.model": "gemma4:e4b", "gen_ai.operation.name": "chat",
                "gen_ai.usage.input_tokens": 50, "gen_ai.usage.output_tokens": 20,
                "gen_ai.usage.total_cost": 0.0,
            }):
                pass
        sentry_sdk.flush()
    transactions = [item.payload.json for env in envelopes for item in env.items if item.headers.get("type") == "transaction"]
    assert transactions
    transaction = transactions[0]
    assert transaction["contexts"]["trace"]["op"] == "gen_ai.invoke_agent"
    assert transaction["spans"][0]["data"]["gen_ai.usage.input_tokens"] == 50
    assert transaction["spans"][0]["data"]["gen_ai.usage.total_cost"] == 0
    assert "messages" not in str(transaction)


@pytest.mark.skipif(not os.environ.get("POLTERGIT_TEST_DATABASE_URL"), reason="Requires a disposable pgvector database (CI provides one).")
def test_postgres_hybrid_search_and_stale_revision(repo, tmp_path, monkeypatch):
    settings = Settings(database_url=os.environ["POLTERGIT_TEST_DATABASE_URL"], state_dir=tmp_path)

    def embed(self, texts, **kwargs):
        # Deterministic test vectors exercise the real SQL, independent of model downloads.
        return [[1.0 if "gateway" in text.lower() else 0.0, 1.0] + [0.0] * 766 for text in texts]

    monkeypatch.setattr(Ollama, "embed", embed)
    count, warnings = index_repository(repo, settings)
    assert count == 6
    matches = search(repo, "gateway reservation", settings)
    assert any("reservation" in m.body for m in matches[:2])
    repo.revision = "0" * 40
    with pytest.raises(SearchError, match="stale"):
        search(repo, "gateway reservation", settings)
