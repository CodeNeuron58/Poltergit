import pytest

from poltergit.git_history import GitError, function_names


def test_line_history_follows_the_changed_line(repo):
    history = repo.history("src/client.py:13")
    assert history.code.strip() == "time.sleep(3)"
    assert "reservation" in history.evidence[0].body
    assert len(history.evidence) == 2
    assert all("cache" not in s.title for s in history.evidence[:-1])


def test_dirty_file_does_not_change_head_line_numbers(repo):
    (repo.root / "src/client.py").write_text("# added\n" + repo.blob("HEAD", "src/client.py"))
    history = repo.history("src/client.py:13")
    assert history.code.strip() == "time.sleep(3)"
    assert "uncommitted" in history.warnings[0]


@pytest.mark.parametrize("target", ["../outside.py:1", "src/client.py:0", "src/client.py:999", "missing:1", "oops"])
def test_bad_targets_fail_clearly(repo, target):
    with pytest.raises(GitError):
        repo.history(target)


def test_ofrenda_contains_deleted_file_and_function(repo):
    memorials = repo.memorials()
    cache = next(m for m in memorials if m.kind == "file")
    assert cache.path == "src/old_cache.py"
    assert cache.days == 366
    assert "stale credentials" in cache.reason
    ping = next(m for m in memorials if m.kind == "function")
    assert ping.name == "legacy_ping"
    assert ping.born == "" and ping.days is None


def test_nested_functions_have_distinct_names():
    assert function_names("class A:\n def ping(self):\n  pass\ndef ping():\n pass\n") == {"A.ping", "ping"}
