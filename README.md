# Poltergit

**A séance for your Git history. Every ghost brings receipts.**

Ask a line why it exists. Read the original sources. Honor code that has departed.

```powershell
uv sync
uv run poltergit demo
uv run poltergit why src/client.py:13 --repo .poltergit/demo --record
```

`--record` works without a model or an account. The demo uses fictional, clearly
labeled history in a real Git repository. All analysis reads committed `HEAD`.

Open the local interface:

```powershell
uv run poltergit serve --repo .poltergit/demo --record
```

Visit http://127.0.0.1:8787. Uncheck **Source excerpts only** to use Ollama.
Use `Ctrl+C` to stop the server.

```powershell
# Local model inference (requires the downloaded Ollama models)
uv run poltergit why src/client.py:13 --repo .poltergit/demo --no-animation

# Static memorial site
uv run poltergit ofrenda --repo .poltergit/demo --output site

# Optional local voice
uv sync --extra voice
uv run python scripts/download_voice.py
uv run --extra voice poltergit why src/client.py:13 --repo .poltergit/demo --speak

# Check setup / run tests
uv run poltergit doctor
uv run pytest
```

Copy `.env.example` to `.env` to configure optional integrations. On a
CPU-only machine, also set `POLTERGIT_TIMEOUT=600` there — answers take two
to three minutes without a GPU. See [docs/SETUP.md](docs/SETUP.md) for the
full setup guide. Use
`POLTERGIT_DATABASE_URL` for a Tiger Cloud or local pgvector database, then
`uv run poltergit index --repo .poltergit/demo`. Set `POLTERGIT_SENTRY_DSN` to
export content-free trace metadata. GitHub retrieval is opt-in with `--github`.
No Entire integration is included.

The GitHub Pages workflow is manual and publishes the fictional demo's ofrenda.
Nothing is published automatically by this local build.

See [HANDOFF.md](HANDOFF.md) for the exact stopping point and remaining work.
