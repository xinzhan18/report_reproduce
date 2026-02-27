"""
Tests for pipeline orchestration.
"""

import pytest
from core.pipeline import create_research_pipeline
from core.state import create_initial_state


def test_pipeline_creation():
    """Test that pipeline can be created."""
    pipeline = create_research_pipeline()
    assert pipeline is not None


def test_initial_state_creation():
    """Test initial state creation."""
    state = create_initial_state("test research direction")
    assert state["research_direction"] == "test research direction"
    assert "project_id" in state
    assert state["status"] == "initialized"


# Add more integration tests here when ready to test with actual API
