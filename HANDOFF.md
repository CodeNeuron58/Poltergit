# Poltergit handoff — 31 October 2026

Work was paused at the user's request. This is a working local prototype, not
a completed or submitted hackathon entry.

## Implemented

- Python package initialized with `uv init`; dependencies added using `uv add`.
- CLI: `why`, `demo`, `serve`, `ofrenda`, `index`, `search`, `doctor`.
- Committed-HEAD line history with `git log -L`, bounded line diffs, source
  messages, current code context, dirty-file and shallow-clone warnings.
- Structured Ollama answers speaking as the code. Citation IDs and exact source
  quotations are checked. Invalid/unavailable answers fall back to labeled source
  excerpts. Quote matching does not prove semantic entailment; model reliability
  still needs live evaluation.
- Read-only, opt-in GitHub PR, review-comment, issue, and discussion retrieval.
- PostgreSQL/pgvector schema, EmbeddingGemma indexing and keyword/vector
  reciprocal-rank search scoped to repository, revision, and embedding model.
- Content-free local traces and optional Sentry transactions with model metrics.
- Optional Kokoro ONNX narration with a quiet echo effect.
- Responsive local web interface, evidence cards, ofrenda, trace viewer, and
  dependency status. Localhost binding and anti-CSRF request tokens.
- Deleted-file and Python-function memorials. Function birth is found by AST
  comparison through up to 200 file revisions. Other languages get file-level
  memorials only. Renamed files are excluded; function removals inside rename
  commits are not currently included.
- Standalone, escaped HTML/CSS ofrenda export, GitHub Actions test workflows,
  and a manual demo-only GitHub Pages workflow.
- Fictional demo repository with six real commits; no real service is contacted
  by its code.

## Installed / downloaded

All Python packages were installed in `C:\Poltergit\.venv`; the exact complete
dependency graph is recorded in `uv.lock`. The project cache is `.uv-cache`.
`LOCAL-INSTALLS.txt` records the exact 56 installed package entries at handoff.

Direct runtime dependencies: Typer, Rich, FastAPI, Uvicorn, HTTPX,
Pydantic Settings, Jinja2, Sentry SDK, Psycopg with binary driver, pgvector.
Development dependencies: pytest, pytest-cov, Ruff.
Optional voice dependencies: kokoro-onnx and SoundFile, with ONNX Runtime,
NumPy, phonemizer, and espeak-ng loader among their transitive dependencies.

Downloaded to the existing Ollama installation's model storage:

- `gemma4:e4b`: approximately 6.6 GB.
- `embeddinggemma:latest`: approximately 621 MB.

Downloaded into the ignored project `models` directory:

- `kokoro-v1.0.onnx`: 325,532,387 bytes.
- `voices-v1.0.bin`: 28,214,398 bytes.

Git, uv, Python 3.12, Ollama, Docker, PostgreSQL, and Node were already installed.
No system application, Docker image, or database service was installed by this
work. The Docker daemon was not running; the installed PostgreSQL did not have
the pgvector extension file. No existing database was changed.

## Generated local state

- `.poltergit/demo`: isolated fictional Git repository.
- `.poltergit/traces`: content-free local JSON traces from smoke tests.
- `.poltergit/embedding-download.log`: model download output.
- `site`: generated demo ofrenda. Regenerate it to include the latest function
  birth-date implementation.
- `.pytest_cache`, Python bytecode, and pytest temporary repositories.
- `dist`: local Python distribution build artifacts, if the final build succeeds.

Models, caches, local state, `.env`, and generated site files are ignored by Git.
No credentials were requested in chat, created, or saved. `.env.example` has
empty credential fields. The user will connect Tiger Data and Sentry later.

## Validation and remaining work

The first 25 tests passed, covering Git, answer validation/fallbacks, web APIs,
CSRF/path protections, and HTML export. Browser testing verified the record-mode
séance and evidence cards with no console errors; the desktop layout and a narrow
mobile layout were inspected. The ofrenda tab was opened, but its final loaded
state and the trace tab were not visually verified before the stop request.

An additional Sentry envelope test exposed the SDK's default AI-span streaming
behavior: AI child spans were absent from the transaction envelope expected by
the test. Poltergit now explicitly uses transaction-contained AI spans and
attaches child spans to their transaction. See the final chat report for the
final test result: **29 passed, 1 skipped, 3 dependency deprecation warnings**.
The skipped test requires a disposable PostgreSQL database with pgvector.
The Python wheel and source distribution built successfully; their contents
include the web assets and exclude local caches, models, and secrets.
JavaScript syntax and `git diff --check` also passed.

Still to do:

1. Run actual Gemma answers on the delay, retry, and unknown-constant demo lines;
   evaluate factual support and silence behavior. Model downloads are complete,
   but inference was not tested before stopping.
2. Verify actual EmbeddingGemma output and Kokoro audio generation/playback.
3. Connect free Tiger Data and Sentry accounts; run live retrieval and inspect
   exported traces. PostgreSQL integration tests are opt-in locally and have a
   pgvector service configured in CI; CI has not run because nothing was pushed.
4. Finish browser verification of ofrenda, traces, voice, error states, mobile
   interactions, and accessibility. Capture final submission screenshots.
5. Run on an archived public project and validate its real history. No archived
   project has been cloned or analyzed yet.
6. Add an open-source license, finish setup/submission documentation, record the
   demo, verify hackathon category rules and deadline, and publish when ready.
   The brief says “Sat 1 Nov”; 1 November 2026 is Sunday.

Entire was intentionally omitted. The remaining intended categories are Gemma,
Tiger Data, and Sentry; eligibility and free-plan quotas have not been certified.
No remote repository was created, no commits were pushed, no site was deployed,
and no hackathon entry was submitted.

The localhost preview process was stopped and all downloads finished. The
temporary preview tab could not be closed through the browser tool after the
interruption; it may remain visible, but its server is no longer running.
