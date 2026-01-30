import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_github():
    return MagicMock()

@pytest.fixture
def mock_repo(mock_github):
    repo = MagicMock()
    mock_github.get_repo.return_value = repo
    return repo
