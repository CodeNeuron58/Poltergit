"""Read committed Git objects. Never execute code, hooks, or a repository's tools."""

import ast
import hashlib
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from .models import Evidence, LineHistory, Memorial


class GitError(ValueError):
    pass


class Repository:
    def __init__(self, path: Path | str):
        self.root = Path(path).resolve()
        root = self.git("rev-parse", "--show-toplevel").strip()
        self.root = Path(root).resolve()
        self.revision = self.git("rev-parse", "--verify", "HEAD").strip()

    def git(self, *args: str, check: bool = True) -> str:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
        try:
            result = subprocess.run(
                ["git", "--no-pager", "-c", "core.quotepath=false", "-c",
                 "core.fsmonitor=false", "-c", "diff.external=", *args],
                cwd=self.root, env=env, capture_output=True, encoding="utf-8",
                errors="replace", timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GitError("Git is unavailable or the history operation timed out.") from exc
        if check and result.returncode:
            raise GitError(result.stderr.strip() or "Git could not read this repository.")
        return result.stdout if result.returncode == 0 else ""

    @property
    def remote(self) -> str:
        remote = self.git("remote", "get-url", "origin", check=False).strip()
        match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([\w.-]+/[\w.-]+?)(?:\.git)?/?", remote)
        return f"https://github.com/{match[1]}" if match else ""

    @property
    def key(self) -> str:
        # Local root isolates worktrees/forks even when their origin URLs match.
        return hashlib.sha256(str(self.root).encode()).hexdigest()[:24]

    def path(self, value: str) -> str:
        if not value or any(c in value for c in ("\x00", "\n", "\r", ":")):
            raise GitError("Use a repository-relative file path without a colon.")
        target = (self.root / value).resolve()
        if not target.is_relative_to(self.root) or target == self.root:
            raise GitError("The file must be inside the selected repository.")
        return target.relative_to(self.root).as_posix()

    def blob(self, revision: str, path: str) -> str:
        size = self.git("cat-file", "-s", f"{revision}:{path}", check=False).strip()
        if not size:
            return ""
        if int(size) > 1_000_000:
            raise GitError("This file is too large; choose a text source file under 1 MB.")
        return self.git("show", f"{revision}:{path}")

    def commit(self, sha: str, path: str = "") -> Evidence:
        raw = self.git("show", "-s", "--format=%H%x00%cI%x00%B", sha)
        full_sha, date, message = raw.split("\x00", 2)
        body = message.strip()[:12000]
        return Evidence(id=f"commit:{full_sha}", title=body.splitlines()[0] if body else "Untitled commit",
                        body=body, sha=full_sha, date=date, path=path,
                        url=f"{self.remote}/commit/{full_sha}" if self.remote else "")

    def files(self) -> list[str]:
        return [p for p in self.git("ls-tree", "-r", "--name-only", "-z", self.revision).split("\x00") if p]

    def history(self, target: str, limit: int = 40) -> LineHistory:
        try:
            filename, raw_line = target.rsplit(":", 1)
            line = int(raw_line)
        except (ValueError, TypeError) as exc:
            raise GitError("Choose a line with path/to/file.py:42.") from exc
        path = self.path(filename)
        if path not in self.files():
            raise GitError("That file is not tracked at HEAD. Commit it first.")
        content = self.blob(self.revision, path)
        if "\x00" in content:
            raise GitError("Binary files cannot be summoned.")
        lines = content.splitlines()
        if line < 1 or line > len(lines):
            raise GitError(f"Line must be between 1 and {len(lines)}.")
        # -L walks the selected committed line, including earlier line numbers/renames.
        raw = self.git("log", "--no-ext-diff", "--no-textconv", f"-n{limit}",
                       "--format=%H", "--no-patch", f"-L{line},{line}:{path}", self.revision)
        shas = [s for s in raw.splitlines() if re.fullmatch(r"[a-f0-9]{40,64}", s)]
        evidence = [self.commit(s, path) for s in dict.fromkeys(shas)]
        warnings = []
        if self.git("status", "--porcelain", "--", path).strip():
            warnings.append("This file has uncommitted changes. Line numbers and evidence refer to HEAD.")
        if self.git("rev-parse", "--is-shallow-repository").strip() == "true":
            warnings.append("Shallow clone: older history may be missing. Fetch full history for a complete séance.")
        if len(shas) >= limit:
            warnings.append(f"History is capped at {limit} line-changing commits.")
        return LineHistory(repo=self.root.name, revision=self.revision, path=path, line=line,
                           code=lines[line - 1], evidence=evidence, warnings=warnings,
                           context=[{"line": n + 1, "code": lines[n]} for n in
                                    range(max(0, line - 5), min(len(lines), line + 4))])

    def recent(self, limit: int = 200) -> list[Evidence]:
        shas = self.git("log", f"-n{limit}", "--format=%H", self.revision).splitlines()
        return [self.commit(sha) for sha in shas]

    def memorials(self, limit: int = 80) -> list[Memorial]:
        shas = self.git("log", "--first-parent", f"-n{limit}", "--format=%H", self.revision).splitlines()
        records = []
        for sha in shas:
            parents = self.git("rev-list", "--parents", "-n1", sha).split()[1:]
            if not parents:
                continue
            parent = parents[0]
            change = self.commit(sha)
            entries = self.git("diff", "--no-ext-diff", "--no-textconv", "--name-status", "-z", "-M", parent, sha).split("\x00")
            i = 0
            while i < len(entries) - 1:
                status, path = entries[i:i + 2]
                i += 2
                if status.startswith(("R", "C")):
                    i += 1
                    continue
                removed: list[tuple[str, str]] = []
                if status == "D":
                    removed = [(path, "file")]
                elif status == "M" and path.endswith(".py"):
                    try:
                        before = function_names(self.blob(parent, path))
                        after = function_names(self.blob(sha, path))
                        removed = [(name, "function") for name in sorted(before - after)]
                    except (SyntaxError, GitError):
                        continue
                for name, kind in removed:
                    # File birth is exact for the last add before removal. Function birth
                    # requires its own structural history; don't invent it from file age.
                    born = ""
                    if kind == "file":
                        born = self.git("log", "--follow", "--diff-filter=A", "-n1", "--format=%cI", parent, "--", path).strip()
                    days = max(0, (datetime.fromisoformat(change.date) - datetime.fromisoformat(born)).days) if born else None
                    records.append(Memorial(name=name, path=path, kind=kind, born=born,
                        departed=change.date, days=days, removal_sha=sha, removal_url=change.url,
                        reason=change.body, epitaph=f"I was {'a file' if kind == 'file' else 'a function'} in {path}. My removal is recorded below."))
        return records


def function_names(source: str) -> set[str]:
    result = set()

    def visit(node: ast.AST, prefix: str = "") -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}.{child.name}" if prefix else child.name
                if not isinstance(child, ast.ClassDef):
                    result.add(name)
                visit(child, name)
            else:
                visit(child, prefix)

    visit(ast.parse(source))
    return result
