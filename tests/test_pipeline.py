"""
Tests for pipeline orchestration.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - pytest, core.pipeline, core.state
# OUTPUT: 对外提供 - 测试函数集(test_pipeline_creation/test_initial_state_creation等)
# POSITION: 系统地位 - [Tests/Integration Tests] - Pipeline集成测试,验证LangGraph流程编排
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

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
