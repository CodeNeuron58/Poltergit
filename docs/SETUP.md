# Setting up Poltergit

Everything runs locally. There is no account, API key, or service required for
the core experience — only optional integrations need configuration.

## Prerequisites

- Git
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Ollama](https://ollama.com) for local model inference

## Install

```powershell
uv sync
```

For the optional local voice, add the extras and download the two Kokoro ONNX
files (about 350 MB total, saved into the gitignored `models/` directory):

```powershell
uv sync --extra voice
uv run python scripts/download_voice.py
```

## Models

Pull the two Ollama models used by the séance (about 7.2 GB total):

```powershell
ollama pull gemma4:e4b
ollama pull embeddinggemma
```

Gemma answers the questions; EmbeddingGemma powers the optional pgvector
search. Both run entirely on your machine.

## Configuration

Copy `.env.example` to `.env`. All integrations are optional and default to
off:

- `POLTERGIT_DATABASE_URL` — PostgreSQL/pgvector (for example a free Tiger
  Cloud service, or `docker compose up db` locally) to enable hybrid search
  with `poltergit index` and `poltergit search`.
- `POLTERGIT_SENTRY_DSN` — a Sentry Developer project DSN to export
  content-free performance traces (no source code or prompts are sent).
- `POLTERGIT_GITHUB` / `POLTERGIT_GITHUB_TOKEN` — opt-in retrieval of pull
  requests, reviews, issues, and discussions. Public repositories work
  without a token.

On CPU-only machines, model inference takes two to three minutes per answer.
Set `POLTERGIT_TIMEOUT=600` in `.env` so long answers are not cut off, and
pre-warm the model with `ollama run gemma4:e4b "hi"` before a demo.

## Verify and try

```powershell
uv run poltergit doctor      # every local component should report ready
uv run poltergit demo        # create the fictional demo repository
uv run poltergit why src/client.py:13 --repo .poltergit/demo --record
uv run poltergit serve --repo .poltergit/demo --record
uv run poltergit ofrenda --repo .poltergit/demo --output site
uv run pytest
```

`--record` works with no model at all: it shows labeled source excerpts.
Leave it off to let Gemma answer.

## Troubleshooting

- **"Ollama is unavailable, timed out, or the model is missing"** — run
  `uv run poltergit doctor`. If answers time out on a CPU-only machine, raise
  `POLTERGIT_TIMEOUT` in `.env`.
- **"Kokoro model files are missing"** — run
  `uv run python scripts/download_voice.py`, or re-run `uv sync --extra voice`.
- **Databases** — the pgvector schema is created automatically by
  `poltergit index`; the connection string is read from
  `POLTERGIT_DATABASE_URL` and never logged.
