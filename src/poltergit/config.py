from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="POLTERGIT_", env_file=".env", extra="ignore"
    )
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "gemma4:e4b"
    embedding_model: str = "embeddinggemma"
    database_url: str = ""
    sentry_dsn: str = ""
    github_token: str = ""
    github: bool = False
    timeout: float = Field(default=180, ge=1, le=600)
    history_limit: int = Field(default=40, ge=1, le=200)
    state_dir: Path = Path(".poltergit")
    kokoro_model: Path = Path("models/kokoro-v1.0.onnx")
    kokoro_voices: Path = Path("models/voices-v1.0.bin")
    voice: str = "af_heart"

