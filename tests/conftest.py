import pytest

from poltergit.demo import create_demo
from poltergit.git_history import Repository


@pytest.fixture
def repo(tmp_path):
    return Repository(create_demo(tmp_path / "haunted"))
