import json
import re
import secrets
import threading
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import Settings
from .git_history import GitError, Repository
from .health import diagnose
from .seance import summon
from .voice import narrate

ASSETS = Path(__file__).parent / "static"
TEMPLATES = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"),
                        autoescape=select_autoescape(["html"]))


class SummonRequest(BaseModel):
    target: str = Field(min_length=3, max_length=1024)
    record: bool = False


class VoiceRequest(BaseModel):
    answer_id: str = Field(pattern=r"^[a-f0-9]{32}$")


def create_app(path: Path, settings: Settings | None = None, *, record_only: bool = False) -> FastAPI:
    settings = settings or Settings()
    initial = Repository(path)
    app = FastAPI(title="Poltergit", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"])
    nonce = secrets.token_urlsafe(32)
    lock = threading.Lock()
    answers = OrderedDict()
    memorial_cache = {}

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        if request.method not in {"GET", "HEAD"}:
            if not secrets.compare_digest(request.headers.get("X-Poltergit-Token", ""), nonce):
                return JSONResponse({"detail": "Reload the local app to reconnect."}, status_code=403)
            origin = request.headers.get("origin")
            if origin and origin != f"{request.url.scheme}://{request.url.netloc}":
                return JSONResponse({"detail": "Cross-origin requests are not allowed."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(GitError)
    async def git_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.get("/", response_class=HTMLResponse)
    def home():
        return TEMPLATES.get_template("index.html").render(repo=initial.root.name, nonce=nonce,
                                                           record_only=record_only)

    @app.get("/api/repo")
    def repository():
        repo = Repository(initial.root)
        files = repo.files()
        code_files = [p for p in files if p.endswith((".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".java", ".c", ".cpp", ".rb"))]
        preferred = "src/client.py" if "src/client.py" in files else (code_files or files or [""])[0]
        return {"name": repo.root.name, "revision": repo.revision, "files": files[:3000],
                "files_truncated": len(files) > 3000, "default_file": preferred,
                "remote": repo.remote, "record_only": record_only}

    @app.get("/api/file")
    def file(path: str):
        repo = Repository(initial.root)
        relative = repo.path(path)
        if relative not in repo.files():
            raise HTTPException(404, "This file is not tracked at HEAD.")
        content = repo.blob(repo.revision, relative)
        if "\x00" in content:
            raise HTTPException(400, "Select a text source file.")
        return {"path": relative, "lines": content.splitlines(), "revision": repo.revision}

    @app.post("/api/why")
    def why(body: SummonRequest):
        if not lock.acquire(blocking=False):
            raise HTTPException(409, "A séance is already in progress. Let this spirit finish.")
        try:
            answer = summon(Repository(initial.root), body.target, settings, record_only=body.record)
            answers[answer.trace_id] = answer
            while len(answers) > 32:
                answers.popitem(last=False)
            return answer
        finally:
            lock.release()

    @app.get("/api/ofrenda")
    def ofrenda():
        repo = Repository(initial.root)
        if repo.revision not in memorial_cache:
            memorial_cache.clear()
            memorial_cache[repo.revision] = repo.memorials()
        return {"memorials": memorial_cache[repo.revision], "limit": 80, "revision": repo.revision}

    @app.get("/api/status")
    def status():
        return {"checks": diagnose(settings)}

    @app.get("/api/traces")
    def traces():
        folder = settings.state_dir / "traces"
        paths = sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:30] if folder.exists() else []
        records = []
        for trace_path in paths:
            try:
                records.append(json.loads(trace_path.read_text(encoding="utf-8")))
            except (ValueError, OSError):
                continue
        return {"traces": records}

    @app.post("/api/voice")
    def voice(body: VoiceRequest):
        answer = answers.get(body.answer_id)
        if not answer:
            raise HTTPException(404, "Summon this line again before asking it to speak.")
        if not lock.acquire(blocking=False):
            raise HTTPException(409, "The room is busy. Try the voice again in a moment.")
        try:
            narrate(answer.text, settings, body.answer_id)
        except ValueError as exc:
            raise HTTPException(503, str(exc)) from exc
        finally:
            lock.release()
        return {"url": f"/api/audio/{body.answer_id}"}

    @app.get("/api/audio/{identifier}")
    def audio(identifier: str):
        if not re.fullmatch(r"[a-f0-9]{32}", identifier):
            raise HTTPException(404)
        audio_path = settings.state_dir / "audio" / f"{identifier}.wav"
        if not audio_path.is_file():
            raise HTTPException(404)
        return FileResponse(audio_path, media_type="audio/wav")

    app.mount("/static", StaticFiles(directory=ASSETS), name="static")
    return app
