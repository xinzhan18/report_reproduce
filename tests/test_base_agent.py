"""
Tests for BaseAgent

Tests the Template Method Pattern and infrastructure handling.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - pytest, unittest.mock, agents.base_agent.BaseAgent, core.state
# OUTPUT: 对外提供 - 测试函数集(test_base_agent_*/MockAgent测试类)
# POSITION: 系统地位 - [Tests/Unit Tests] - BaseAgent单元测试,验证Template Method模式和生命周期管理
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import pytest
from unittest.mock import Mock, MagicMock, patch
from agents.base_agent import BaseAgent
from core.state import ResearchState, create_initial_state


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    def __init__(self, llm, file_manager):
        super().__init__(llm, file_manager, agent_name="mock")
        self.execute_called = False

    def _execute(self, state: ResearchState) -> ResearchState:
        """Mock execute method."""
        self.execute_called = True
        state["test_output"] = "test_value"
        return state


class TestBaseAgent:
    """Test suite for BaseAgent."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        llm = Mock()
        llm.messages = Mock()
        response = Mock()
        response.content = [Mock(text="Test response")]
        response.usage = Mock(input_tokens=100, output_tokens=50)
        llm.messages.create = Mock(return_value=response)
        return llm

    @pytest.fixture
    def mock_file_manager(self):
        """Create mock file manager."""
        return Mock()

    @pytest.fixture
    def mock_agent(self, mock_llm, mock_file_manager):
        """Create mock agent instance."""
        return MockAgent(mock_llm, mock_file_manager)

    def test_initialization(self, mock_agent):
        """Test agent initialization."""
        assert mock_agent.agent_name == "mock"
        assert mock_agent.llm is not None
        assert mock_agent.file_manager is not None
        assert mock_agent.intelligence is not None
        assert mock_agent.llm_service is not None
        assert mock_agent.output_manager is not None

    def test_template_method_flow(self, mock_agent):
        """Test that __call__ follows template method pattern."""
        state = create_initial_state("test research")

        # Mock intelligence context loading
        mock_agent.intelligence.load_context = Mock(return_value=({}, []))
        mock_agent.intelligence.save_execution_log = Mock()
        mock_agent.intelligence.update_knowledge = Mock()

        # Execute
        result = mock_agent(state)

        # Verify execute was called
        assert mock_agent.execute_called

        # Verify state was updated
        assert result["test_output"] == "test_value"

        # Verify setup and finalize were called
        assert mock_agent.intelligence.load_context.called
        assert mock_agent.intelligence.save_execution_log.called

    def test_call_llm(self, mock_agent, mock_llm):
        """Test call_llm convenience method."""
        # Setup
        mock_agent.intelligence.load_context = Mock(return_value=({}, []))

        # Call LLM
        result = mock_agent.call_llm("Test prompt", model="sonnet")

        # Verify
        assert result == "Test response"
        assert mock_llm.messages.create.called

    def test_save_artifact(self, mock_agent, mock_file_manager):
        """Test save_artifact convenience method."""
        # Setup
        mock_agent.intelligence.load_context = Mock(return_value=({}, []))

        # Save artifact
        mock_agent.save_artifact(
            content={"test": "data"},
            project_id="test_project",
            filename="test.json",
            subdir="outputs"
        )

        # Verify file manager was called
        # (OutputManager internally uses file_manager)
        # This is a shallow test - deeper testing requires OutputManager tests

    def test_error_handling(self, mock_agent):
        """Test error handling in __call__."""
        state = create_initial_state("test research")

        # Mock to raise error
        mock_agent.intelligence.load_context = Mock(side_effect=Exception("Test error"))

        # Should raise and set error status
        with pytest.raises(Exception):
            mock_agent(state)

        assert state["status"] == "error_mock"
        assert state["error"] == "Test error"

    def test_logger_exists(self, mock_agent):
        """Test that logger is properly initialized."""
        assert mock_agent.logger is not None
        assert mock_agent.logger.name == "agent.mock"


class TestBaseAgentSubclassing:
    """Test subclassing BaseAgent."""

    def test_abstract_execute_required(self):
        """Test that _execute must be implemented."""
        with pytest.raises(TypeError):
            # Cannot instantiate BaseAgent directly
            BaseAgent(Mock(), Mock(), "test")

    def test_custom_execution_summary(self):
        """Test custom execution summary generation."""

        class CustomAgent(BaseAgent):
            def _execute(self, state):
                return state

            def _generate_execution_summary(self, state):
                return {
                    "log": "Custom log",
                    "learnings": ["Custom learning"],
                    "mistakes": [],
                    "reflection": "Custom reflection"
                }

        agent = CustomAgent(Mock(), Mock(), "custom")
        agent.intelligence.load_context = Mock(return_value=({}, []))
        agent.intelligence.save_execution_log = Mock()
        agent.intelligence.update_knowledge = Mock()

        state = create_initial_state("test")
        agent(state)

        # Verify custom summary was used
        call_args = agent.intelligence.save_execution_log.call_args
        assert call_args is not None
        summary = call_args[1]["execution_summary"]
        assert summary["log"] == "Custom log"
        assert summary["learnings"] == ["Custom learning"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
