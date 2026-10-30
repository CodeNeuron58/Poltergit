import importlib.util
import shutil

from .config import Settings
from .ollama import ModelError, Ollama


def diagnose(settings: Settings) -> list[dict]:
    checks = [{"name": "Git", "status": "ready" if shutil.which("git") else "missing",
               "detail": "Committed history is read locally."}]
    try:
        probe = settings.model_copy(update={"timeout": 3})
        models = Ollama(probe).models()
        for name, model in (("Gemma", settings.model), ("EmbeddingGemma", settings.embedding_model)):
            ready = model in models or f"{model}:latest" in models
            checks.append({"name": name, "status": "ready" if ready else "missing",
                           "detail": model if ready else f"ollama pull {model}"})
    except ModelError:
        checks.append({"name": "Ollama", "status": "offline", "detail": "Start Ollama, then pull the configured models."})
    checks.append({"name": "Tiger Data / pgvector", "status": "configured" if settings.database_url else "optional",
                   "detail": "Run poltergit index to verify the connection." if settings.database_url else "Set POLTERGIT_DATABASE_URL for hybrid search."})
    checks.append({"name": "Sentry", "status": "configured" if settings.sentry_dsn else "local traces",
                   "detail": "Content-free trace export enabled." if settings.sentry_dsn else "Set POLTERGIT_SENTRY_DSN to export traces."})
    voice = settings.kokoro_model.is_file() and settings.kokoro_voices.is_file() and importlib.util.find_spec("kokoro_onnx") is not None
    checks.append({"name": "Kokoro", "status": "ready" if voice else "optional",
                   "detail": "Local voice files found." if voice else "Install voice extras and download the two model files."})
    checks.append({"name": "GitHub", "status": "enabled" if settings.github else "off",
                   "detail": "Read-only PR and issue retrieval." if settings.github else "Use --github to retrieve remote discussions."})
    return checks
