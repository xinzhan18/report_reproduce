"""
Tests for tools module.
"""

import pytest
from tools.file_manager import FileManager
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


def test_file_manager_initialization(temp_dir):
    """Test FileManager initialization."""
    fm = FileManager(base_dir=temp_dir)
    assert fm.base_dir == temp_dir
    assert fm.data_dir.exists()
    assert fm.output_dir.exists()


def test_create_project_structure(temp_dir):
    """Test project structure creation."""
    fm = FileManager(base_dir=temp_dir)
    project_path = fm.create_project_structure("test_project")

    assert project_path.exists()
    assert (project_path / "literature").exists()
    assert (project_path / "experiments").exists()
    assert (project_path / "reports").exists()


def test_save_and_load_json(temp_dir):
    """Test JSON save and load."""
    fm = FileManager(base_dir=temp_dir)
    fm.create_project_structure("test_project")

    test_data = {"key": "value", "number": 42}
    fm.save_json(test_data, "test_project", "test.json")

    loaded_data = fm.load_json("test_project", "test.json")
    assert loaded_data == test_data


def test_save_and_load_text(temp_dir):
    """Test text save and load."""
    fm = FileManager(base_dir=temp_dir)
    fm.create_project_structure("test_project")

    test_content = "This is test content"
    fm.save_text(test_content, "test_project", "test.txt")

    loaded_content = fm.load_text("test_project", "test.txt")
    assert loaded_content == test_content


# Add more tool tests here
