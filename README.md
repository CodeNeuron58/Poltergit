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

Full setup, the local web interface, integrations, and submission instructions
are being built in the next local commits.
