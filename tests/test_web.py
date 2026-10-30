import re

import pytest
from fastapi.testclient import TestClient

from poltergit.config import Settings
from poltergit.ofrenda import export_site
from poltergit.web import create_app


@pytest.fixture
def client(repo, tmp_path):
    return TestClient(create_app(repo.root, Settings(state_dir=tmp_path / "state"), record_only=True))


def headers(client):
    html = client.get("/").text
    token = re.search(r'name="poltergit-token" content="([^"]+)"', html)[1]
    return {"X-Poltergit-Token": token}


def test_web_evidence_round_trip(client):
    response = client.post("/api/why", headers=headers(client), json={"target": "src/client.py:13", "record": True})
    assert response.status_code == 200
    data = response.json()
    assert data["history"]["code"].strip() == "time.sleep(3)"
    assert data["mode"] == "record"
    assert client.get("/api/traces").json()["traces"][0]["trace_id"] == data["trace_id"]


def test_cross_origin_and_missing_tokens_are_rejected(client):
    body = {"target": "src/client.py:13", "record": True}
    assert client.post("/api/why", json=body).status_code == 403
    assert client.post("/api/why", headers={**headers(client), "Origin": "https://evil.invalid"}, json=body).status_code == 403
    assert client.get("/", headers={"Host": "evil.invalid"}).status_code == 400


def test_path_escape_and_invalid_line_rejected(client):
    assert client.get("/api/file", params={"path": "../secrets"}).status_code == 400
    assert client.post("/api/why", headers=headers(client), json={"target": "src/client.py:999", "record": True}).status_code == 400


def test_missing_voice_is_actionable(client):
    response = client.post("/api/voice", headers=headers(client), json={"answer_id": "0" * 32})
    assert response.status_code == 404


def test_ofrenda_exports_portable_site(repo, tmp_path):
    destination = export_site(repo, tmp_path / "site")
    html = (destination / "index.html").read_text(encoding="utf-8")
    assert "old_cache.py" in html and "legacy_ping" in html
    assert "366 days of service" in html
    assert (destination / "styles.css").is_file()
    assert (destination / ".nojekyll").is_file()
    assert export_site(repo, destination) == destination


def test_export_never_replaces_unrelated_folder(repo, tmp_path):
    (tmp_path / "precious.txt").write_text("preserve")
    with pytest.raises(ValueError):
        export_site(repo, tmp_path)
    assert (tmp_path / "precious.txt").read_text() == "preserve"


def test_memorial_html_escapes_commit_content(repo, tmp_path, monkeypatch):
    memorials = repo.memorials()
    memorials[0].reason = '<script>alert("bad")</script>'
    monkeypatch.setattr(repo, "memorials", lambda limit: memorials)
    destination = export_site(repo, tmp_path / "site")
    html = (destination / "index.html").read_text(encoding="utf-8")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
