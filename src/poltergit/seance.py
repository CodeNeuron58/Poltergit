from .config import Settings
from .git_history import Repository
from .models import Answer, Claim, LineHistory, ModelAnswer
from .ollama import ModelError, Ollama
from .telemetry import Trace


def validate_claims(answer: ModelAnswer, history: LineHistory) -> list[Claim]:
    sources = {s.id: s for s in history.evidence}
    for claim in answer.claims:
        source = sources.get(claim.source_id)
        if source is None or len(claim.quote.strip()) < 12 or claim.quote not in source.body:
            raise ModelError("A generated citation did not match the record; showing source excerpts instead.")
        if not claim.text.strip().startswith(("I ", "I'm ", "I’ve ", "I've ", "My ")):
            raise ModelError("The answer did not speak as the code; showing source excerpts instead.")
    return answer.claims


def record_answer(history: LineHistory) -> tuple[str, list[Claim]]:
    # Explicitly an excerpt, not an AI explanation or a claim of causal relevance.
    claims = [Claim(text="My history records this message", source_id=s.id, quote=s.body[:1200])
              for s in history.evidence[:3] if s.body.strip()]
    return "I can show you what was written, but these excerpts alone do not establish why I exist. The record is silent beyond these words.", claims


def summon(repo: Repository, target: str, settings: Settings, *, record_only: bool = False,
           use_search: bool = True) -> Answer:
    with Trace(settings) as trace:
        with trace.step("Walk line history", "git.history"):
            history = repo.history(target, settings.history_limit)
        warnings = list(history.warnings)
        if settings.github:
            from .github import enrich
            with trace.step("Read GitHub discussions", "http.client"):
                sources, notes = enrich(repo.remote, history.evidence, settings.github_token)
                history.evidence.extend(sources)
                warnings.extend(notes)
        if settings.database_url and use_search:
            from .search import SearchError, search
            try:
                with trace.step("Hybrid evidence search", "db.query"):
                    matches = search(repo, history.code, settings, limit=5)
                known = {s.id for s in history.evidence}
                history.evidence.extend(s for s in matches if s.id not in known)
            except (SearchError, ModelError) as exc:
                warnings.append(str(exc))
        # Bound the prompt without dropping original line history first.
        if len(history.evidence) > 16:
            history.evidence = history.evidence[:16]
            warnings.append("The answer uses the first 16 sources; narrow the history for more detail.")
        total_chars = 0
        for source in history.evidence:
            budget = min(6000, max(0, 32000 - total_chars))
            if len(source.body) > budget:
                source.body = source.body[:budget]
                warnings.append("Long source text was truncated to fit the local model context.")
            total_chars += len(source.body)
        mode = "record"
        silent = True
        usage = {}
        text, claims = record_answer(history)
        if not record_only:
            try:
                with trace.step("Let the line speak", "gen_ai.chat",
                    **{"gen_ai.operation.name": "chat", "gen_ai.system": "ollama",
                       "gen_ai.request.model": settings.model}) as attributes:
                    model_answer, usage = Ollama(settings).answer(history)
                    attributes.update({"gen_ai.usage.input_tokens": usage.get("prompt_eval_count", 0),
                        "gen_ai.usage.output_tokens": usage.get("eval_count", 0),
                        "gen_ai.usage.total_cost": 0.0})
                with trace.step("Verify source quotations", "evidence.validate"):
                    claims = validate_claims(model_answer, history)
                silent = model_answer.silent or not claims
                text = "\n\n".join(c.text for c in claims)
                if silent:
                    text += ("\n\n" if text else "") + "The record is silent" + (" about the rest." if claims else ".")
                mode = "ollama"
            except ModelError as exc:
                warnings.append(str(exc))
                text, claims = record_answer(history)
        answer = Answer(history=history, text=text, claims=claims, mode=mode,
            model=settings.model if mode == "ollama" else "", silent=silent,
            warnings=list(dict.fromkeys(warnings)), trace_id=trace.id, spans=trace.spans,
            input_tokens=usage.get("prompt_eval_count", 0), output_tokens=usage.get("eval_count", 0))
    return answer
