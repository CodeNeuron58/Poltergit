import json
import sys
import time
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import Settings
from .demo import create_demo
from .git_history import GitError, Repository
from .seance import summon
from .telemetry import configure

app = typer.Typer(no_args_is_help=True, help="A séance for your Git history. Every ghost brings receipts.")
console = Console(highlight=False)
RepoOption = Annotated[Path, typer.Option("--repo", "-r", help="Repository to read (committed HEAD).")]


@app.command()
def why(
    target: Annotated[str, typer.Argument(help="A repository-relative file and line, e.g. src/client.py:13.")],
    repo: RepoOption = Path("."),
    record: bool = typer.Option(False, "--record", help="Read source excerpts without calling a model."),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable evidence and answer."),
    no_animation: bool = typer.Option(False, "--no-animation"),
    github: bool = typer.Option(False, "--github", help="Fetch related GitHub PRs, reviews, and issues."),
    speak: bool = typer.Option(False, "--speak", help="Write a local Kokoro WAV of the answer."),
):
    """Ask a line why it exists, with citations you can inspect."""
    settings = Settings()
    settings.github = settings.github or github
    configure(settings)
    try:
        answer = summon(Repository(repo), target, settings, record_only=record)
        if speak:
            from .voice import narrate
            output = narrate(answer.text, settings, answer.trace_id)
            if not json_output:
                console.print(f"Voice saved to {output}", markup=False)
    except (GitError, ValueError, OSError) as exc:
        typer.echo(f"Cannot summon: {exc}", err=True)
        raise typer.Exit(1) from exc
    if json_output:
        typer.echo(answer.model_dump_json(indent=2))
        return
    console.print(Panel(f"{target}\n{answer.history.code}", title="POLTERGIT / THE SÉANCE", border_style="dark_orange", markup=False))
    if no_animation or not sys.stdout.isatty():
        console.print(answer.text, markup=False)
    else:
        for char in answer.text:
            console.print(char, end="", markup=False, soft_wrap=True)
            time.sleep(0.012)
        console.print()
    sources = {s.id: s for s in answer.history.evidence}
    for number, claim in enumerate(answer.claims, 1):
        source = sources[claim.source_id]
        console.print(f"\n[{number}] {claim.text}\n    “{claim.quote}”\n    {source.title}\n    {source.url or source.sha}", markup=False)
    for warning in answer.warnings:
        console.print(f"Note: {warning}", style="yellow", markup=False)
    console.print(f"\n{answer.mode} · {len(answer.history.evidence)} sources · trace {answer.trace_id}", style="dim", markup=False)


@app.command()
def demo(destination: Path = typer.Option(Path(".poltergit/demo"), "--destination")):
    """Create a fictional repo with real Git history. Requires no services."""
    try:
        path = create_demo(destination)
    except (ValueError, OSError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    console.print(f"Created demo repository: {path}\n\nTry: uv run poltergit why src/client.py:13 --repo \"{path}\" --record", markup=False)


@app.command()
def serve(repo: RepoOption = Path("."), port: int = typer.Option(8787, min=1024, max=65535),
          record: bool = typer.Option(False, "--record", help="Default the web app to source excerpts.")):
    """Open the local séance room in your browser at http://127.0.0.1:8787."""
    import uvicorn
    from .web import create_app
    settings = Settings()
    configure(settings)
    try:
        application = create_app(repo, settings, record_only=record)
    except (GitError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    console.print(f"The door is open: http://127.0.0.1:{port}", markup=False)
    uvicorn.run(application, host="127.0.0.1", port=port, access_log=False)


@app.command()
def ofrenda(repo: RepoOption = Path("."), output: Path = typer.Option(Path("site"), "--output", "-o"),
            limit: int = typer.Option(80, min=1, max=500)):
    """Build a standalone memorial site for deleted files and Python functions."""
    from .ofrenda import export_site
    try:
        path = export_site(Repository(repo), output, limit)
    except (GitError, ValueError, OSError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    console.print(f"Ofrenda written to {path}. Open index.html or publish this folder with GitHub Pages.", markup=False)


@app.command()
def index(repo: RepoOption = Path("."), limit: int = typer.Option(100, min=1, max=500),
          github: bool = typer.Option(False, "--github")):
    """Embed recent history with EmbeddingGemma and index it in PostgreSQL/pgvector."""
    from .search import index_repository
    settings = Settings()
    settings.github = settings.github or github
    configure(settings)
    try:
        count, warnings = index_repository(Repository(repo), settings, limit)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    console.print(f"Indexed {count} evidence documents in PostgreSQL.")
    for warning in warnings:
        console.print(warning, markup=False)


@app.command()
def search(query: str, repo: RepoOption = Path(".")):
    """Find evidence using keyword + vector reciprocal-rank fusion."""
    from .search import search as find
    try:
        sources = find(Repository(repo), query, Settings())
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    typer.echo(json.dumps([s.model_dump() for s in sources], indent=2))


@app.command()
def doctor():
    """Check local dependencies and configured integrations without exposing secrets."""
    from .health import diagnose
    result = diagnose(Settings())
    table = Table(title="Poltergit / connection to the other side")
    table.add_column("Component")
    table.add_column("State")
    table.add_column("Next step")
    for check in result:
        table.add_row(check["name"], check["status"], check["detail"])
    console.print(table)


if __name__ == "__main__":
    app()
