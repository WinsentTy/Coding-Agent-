import pytest
from unittest.mock import MagicMock, patch
from code_agent.service import CodeAgentService
from shared.llm import MockLLMClient


@pytest.fixture
def mock_github_class():
    with patch('code_agent.service.Github') as MockGithub:
        yield MockGithub

def test_service_initialization(mock_github_class):
    service = CodeAgentService("fake-token", "owner/repo", MockLLMClient())
    assert service.repo is not None
    mock_github_class.return_value.get_repo.assert_called_with("owner/repo")

def test_check_code_syntax_error(mock_github_class):
    service = CodeAgentService("fake-token", "owner/repo", MockLLMClient())
    
    with patch('builtins.open', new_callable=MagicMock) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "def bad_syntax("
        
        result = service.check_code("test.py")
        assert "SyntaxError" in result

def test_check_code_valid(mock_github_class):
    service = CodeAgentService("fake-token", "owner/repo", MockLLMClient())
    
    with patch('builtins.open', new_callable=MagicMock) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "print('hello')"
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = service.check_code("test.py")
            assert result is None

