"""
Unit tests for agents.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - pytest, unittest.mock, core.state, agents.*
# OUTPUT: 对外提供 - 测试函数集(test_ideation_agent_*/test_planning_agent_*/test_experiment_agent_*/test_writing_agent_*)
# POSITION: 系统地位 - [Tests/Unit Tests] - Agent单元测试,验证四个Agent的核心功能
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import pytest
from unittest.mock import Mock, MagicMock
from core.state import create_initial_state
from agents.ideation_agent import IdeationAgent
from agents.planning_agent import PlanningAgent
from agents.experiment_agent import ExperimentAgent
from agents.writing_agent import WritingAgent


@pytest.fixture
def mock_llm():
    """Create mock LLM client."""
    llm = Mock()
    response = Mock()
    response.content = [Mock(text="Mock response")]
    llm.messages.create.return_value = response
    return llm


@pytest.fixture
def mock_file_manager():
    """Create mock file manager."""
    return Mock()


@pytest.fixture
def mock_paper_fetcher():
    """Create mock paper fetcher."""
    fetcher = Mock()
    fetcher.fetch_recent_papers.return_value = []
    fetcher.fetch_papers_by_keywords.return_value = []
    fetcher.filter_papers_by_relevance.return_value = []
    return fetcher


def test_ideation_agent_initialization(mock_llm, mock_paper_fetcher, mock_file_manager):
    """Test Ideation Agent initialization."""
    agent = IdeationAgent(mock_llm, mock_paper_fetcher, mock_file_manager)
    assert agent is not None
    assert agent.llm == mock_llm
    assert agent.paper_fetcher == mock_paper_fetcher


def test_planning_agent_initialization(mock_llm, mock_file_manager):
    """Test Planning Agent initialization."""
    agent = PlanningAgent(mock_llm, mock_file_manager)
    assert agent is not None
    assert agent.llm == mock_llm


def test_experiment_agent_initialization(mock_llm, mock_file_manager):
    """Test Experiment Agent initialization."""
    data_fetcher = Mock()
    backtest_engine = Mock()
    agent = ExperimentAgent(mock_llm, mock_file_manager, data_fetcher, backtest_engine)
    assert agent is not None


def test_writing_agent_initialization(mock_llm, mock_file_manager):
    """Test Writing Agent initialization."""
    agent = WritingAgent(mock_llm, mock_file_manager)
    assert agent is not None


def test_create_initial_state():
    """Test initial state creation."""
    state = create_initial_state("momentum strategies")
    assert state["research_direction"] == "momentum strategies"
    assert state["status"] == "initialized"
    assert state["iteration"] == 0
