"""A reproducible, explicitly fictional repository for the demo and tests."""

import os
import subprocess
from pathlib import Path


def create_demo(destination: Path) -> Path:
    destination = destination.resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Demo destination must be empty; existing files are never overwritten.")
    destination.mkdir(parents=True, exist_ok=True)

    def git(*args: str, date: str = "2024-01-10T12:00:00+00:00") -> None:
        subprocess.run(
            ["git", "-c", "user.name=Poltergit Demo", "-c", "user.email=demo@example.invalid",
             "-c", "commit.gpgsign=false", "-c", "core.hooksPath=.git/no-hooks", *args],
            cwd=destination, env={**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date},
            check=True, capture_output=True, timeout=30,
        )

    def write(name: str, text: str) -> None:
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(message: str, date: str) -> None:
        git("add", "--all")
        git("commit", "-m", message, date=date)

    git("init", "-b", "main")
    write("README.md", "# The haunted client\n\nA fictional Git repository created by Poltergit.\nNothing here connects to a real service.\n")
    client = '''"""A fictional client for the Poltergit demo."""
import time

MAX_RETRIES = 3
MAGIC_NUMBER = 42


def connect(transport):
    for attempt in range(MAX_RETRIES):
        try:
            return transport.connect()
        except ConnectionError:
            time.sleep(1)
    raise ConnectionError("The other side is silent")


def legacy_ping(transport):
    return transport.ping()
'''
    write("src/client.py", client)
    write("src/old_cache.py", '"""The first cache, before the service had a name."""\nCACHE = {}\n\n\ndef remember(key, value):\n    CACHE[key] = value\n')
    commit("feat: introduce the client and an in-memory cache", "2024-01-10T12:00:00+00:00")
    client = client.replace("time.sleep(1)", "time.sleep(3)")
    write("src/client.py", client)
    commit("fix: wait three seconds before reconnecting\n\nThe upstream gateway keeps a closed session reserved for two seconds. A three-second delay gives that reservation time to expire and prevents a reconnect storm. Reproduced with the gateway simulator.", "2024-03-18T12:00:00+00:00")
    client = client.replace("MAX_RETRIES = 3", "MAX_RETRIES = 7")
    write("src/client.py", client)
    commit("fix: tolerate the gateway maintenance window\n\nSeven attempts cover the gateway's eighteen-second maintenance window with a three-second pause between attempts. Three attempts exhausted the retry budget before the gateway recovered.", "2024-06-02T12:00:00+00:00")
    client = client.replace("MAGIC_NUMBER = 42", "MAGIC_NUMBER = 43")
    write("src/client.py", client)
    commit("update", "2024-07-05T12:00:00+00:00")
    (destination / "src/old_cache.py").unlink()
    commit("refactor: retire the process-local cache\n\nThe shared cache now owns invalidation. Keeping a second cache here served stale credentials after rotation, so the old cache is removed.", "2025-01-10T12:00:00+00:00")
    client = client.replace('\n\ndef legacy_ping(transport):\n    return transport.ping()\n', '\n')
    write("src/client.py", client)
    commit("refactor: retire legacy_ping\n\nThe health endpoint replaces the legacy ping handshake. Removing the unused helper prevents new callers from depending on an obsolete protocol.", "2025-02-14T12:00:00+00:00")
    return destination
