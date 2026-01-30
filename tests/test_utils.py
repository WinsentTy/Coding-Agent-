from unittest.mock import patch
from shared.utils import generate_repo_map

@patch("os.walk")
@patch("os.path.exists")
@patch("builtins.open")
def test_generate_repo_map_small(mock_open, mock_exists, mock_walk):
    # Setup mock file system
    mock_walk.return_value = [
        ("/root", [], ["file1.py"]),
    ]
    mock_open.return_value.__enter__.return_value.read.return_value = "def foo(): pass"
    
    repo_map = generate_repo_map("/root")
    assert "file1.py" in repo_map
    assert "def foo():" in repo_map

@patch("os.walk")
@patch("os.path.exists")
@patch("builtins.open")
def test_generate_repo_map_truncated(mock_open, mock_exists, mock_walk):
    # Setup mock file system with many files
    # We will mock walk to return enough items to exceed a small limit
    mock_walk.return_value = [
        ("/root", [], ["file1.py", "file2.py", "file3.py"]),
    ]
    mock_open.return_value.__enter__.return_value.read.return_value = "def foo(): pass"
    
    # Set a very small limit
    repo_map = generate_repo_map("/root", max_chars=50)
    
    assert "truncated" in repo_map
    assert "file3.py" not in repo_map # Should be cut off
