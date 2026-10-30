import json

import pytest

from poltergit.config import Settings
from poltergit.models import Claim, ModelAnswer
from poltergit.ollama import ModelError, Ollama
from poltergit.seance import summon, validate_claims


def test_record_mode_never_calls_a_model(repo, tmp_path, monkeypatch):
    monkeypatch.setattr(Ollama, "answer", lambda *a: pytest.fail("Unexpected model call"))
    result = summon(repo, "src/client.py:13", Settings(state_dir=tmp_path), record_only=True)
    assert result.mode == "record"
    assert "The record is silent" in result.text
    assert "reservation" in result.claims[0].quote
    trace = json.loads(next((tmp_path / "traces").glob("*.json")).read_text())
    assert trace["spans"][0]["name"] == "Walk line history"
    assert "reservation" not in json.dumps(trace)


def test_valid_model_claims_carry_exact_support(repo, tmp_path, monkeypatch):
    evidence = repo.history("src/client.py:13").evidence[0]
    claims = [Claim(text="I wait for the gateway reservation to expire.", source_id=evidence.id,
                    quote="The upstream gateway keeps a closed session reserved for two seconds.")]
    monkeypatch.setattr(Ollama, "answer", lambda *a: (ModelAnswer(claims=claims), {"prompt_eval_count": 90, "eval_count": 25}))
    result = summon(repo, "src/client.py:13", Settings(state_dir=tmp_path))
    assert result.mode == "ollama"
    assert result.input_tokens == 90
    assert result.output_tokens == 25
    assert not result.silent
    assert result.inference_cost_usd == 0


@pytest.mark.parametrize("source_id,quote,text", [
    ("invented", "The upstream gateway keeps a closed session reserved for two seconds.", "I wait."),
    (None, "This made-up incident was never recorded anywhere.", "I wait."),
    (None, "The upstream gateway keeps a closed session reserved for two seconds.", "The author wanted this."),
])
def test_invalid_citations_and_impersonation_are_rejected(repo, source_id, quote, text):
    history = repo.history("src/client.py:13")
    result = ModelAnswer(claims=[Claim(text=text, quote=quote, source_id=source_id or history.evidence[0].id)])
    with pytest.raises(ModelError):
        validate_claims(result, history)


def test_model_failure_falls_back_with_error_span(repo, tmp_path, monkeypatch):
    def fail(*args):
        raise ModelError("Ollama is unavailable.")
    monkeypatch.setattr(Ollama, "answer", fail)
    result = summon(repo, "src/client.py:13", Settings(state_dir=tmp_path))
    assert result.mode == "record"
    assert result.warnings == ["Ollama is unavailable."]
    assert result.spans[-1]["status"] == "error"


def test_silence_is_preserved(repo, tmp_path, monkeypatch):
    monkeypatch.setattr(Ollama, "answer", lambda *a: (ModelAnswer(claims=[], silent=True), {}))
    result = summon(repo, "src/client.py:5", Settings(state_dir=tmp_path))
    assert result.text == "The record is silent."
    assert result.claims == []


@pytest.mark.parametrize("url,model", [("https://example.com", "gemma4:e4b"), ("http://127.0.0.1:11434", "gemma4:cloud")])
def test_remote_models_are_rejected(url, model):
    with pytest.raises(ModelError):
        Ollama(Settings(ollama_url=url, model=model))
