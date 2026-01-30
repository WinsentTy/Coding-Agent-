import pytest
from shared.diff_manager import DiffManager

@pytest.fixture
def diff_manager():
    return DiffManager()

def test_apply_diff_single_block(diff_manager):
    original = "line1\nline2\nline3\n"
    diff = """<<<<<< SEARCH
line2
======
line2_modified
>>>>>> REPLACE"""
    
    expected = "line1\nline2_modified\nline3\n"
    assert diff_manager.apply_diff(original, diff) == expected

def test_apply_diff_multiple_blocks(diff_manager):
    original = "line1\nline2\nline3\nline4\n"
    diff = """<<<<<< SEARCH
line1
======
line1_mod
>>>>>> REPLACE
<<<<<< SEARCH
line4
======
line4_mod
>>>>>> REPLACE"""
    
    expected = "line1_mod\nline2\nline3\nline4_mod\n"
    assert diff_manager.apply_diff(original, diff) == expected

def test_apply_diff_full_replacement(diff_manager):
    original = "line1\n"
    diff = "line1_mod\n" # No markers
    assert diff_manager.apply_diff(original, diff) == diff

def test_apply_diff_missing_block(diff_manager):
    original = "line1\n"
    diff = """<<<<<< SEARCH
missing
======
new
>>>>>> REPLACE"""
    
    with pytest.raises(ValueError, match="Search block not found"):
        diff_manager.apply_diff(original, diff)

def test_apply_diff_ambiguous_block(diff_manager):
    original = "line1\nline1\n"
    diff = """<<<<<< SEARCH
line1
======
new
>>>>>> REPLACE"""
    
    with pytest.raises(ValueError, match="Ambiguous update"):
        diff_manager.apply_diff(original, diff)
