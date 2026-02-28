"""
Tests for BaseAgent

Tests the Template Method Pattern and infrastructure handling.
"""

# INPUT:  pytest, unittest.mock, agents.base_agent.BaseAgent, core.state
# OUTPUT: 测试函数集
# POSITION: Tests/Unit Tests - BaseAgent 单元测试

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
        self.execute_called = True
        state["test_output"] = "test_value"
        return state


class TestBaseAgent:
    """Test suite for BaseAgent."""

    @pytest.fixture
    def mock_llm(self):
        llm = Mock()
        llm.messages = Mock()
        response = Mock()
        response.content = [Mock(text="Test response")]
        response.usage = Mock(input_tokens=100, output_tokens=50)
        llm.messages.create = Mock(return_value=response)
        return llm

    @pytest.fixture
    def mock_file_manager(self):
        return Mock()

    @pytest.fixture
    def mock_agent(self, mock_llm, mock_file_manager):
        return MockAgent(mock_llm, mock_file_manager)

    def test_initialization(self, mock_agent):
        assert mock_agent.agent_name == "mock"
        assert mock_agent.llm is not None
        assert mock_agent.file_manager is not None
        assert mock_agent.memory is not None
        assert mock_agent.knowledge_graph is not None

    def test_template_method_flow(self, mock_agent):
        state = create_initial_state("test research")
        result = mock_agent(state)

        assert mock_agent.execute_called
        assert result["test_output"] == "test_value"

    def test_call_llm(self, mock_agent, mock_llm):
        result = mock_agent.call_llm("Test prompt", model="sonnet")
        assert result == "Test response"
        assert mock_llm.messages.create.called

    def test_save_artifact(self, mock_agent, mock_file_manager):
        mock_agent.save_artifact(
            content={"test": "data"},
            project_id="test_project",
            filename="test.json",
            subdir="outputs",
        )
        assert mock_file_manager.save_json.called

    def test_error_handling(self, mock_agent):
        state = create_initial_state("test research")

        # 让 _execute 抛异常
        def raise_error(s):
            raise Exception("Test error")

        mock_agent._execute = raise_error

        with pytest.raises(Exception):
            mock_agent(state)

        assert state["status"] == "error_mock"
        assert state["error"] == "Test error"

    def test_logger_exists(self, mock_agent):
        assert mock_agent.logger is not None
        assert mock_agent.logger.name == "agent.mock"


class TestBaseAgentSubclassing:

    def test_abstract_execute_required(self):
        with pytest.raises(TypeError):
            BaseAgent(Mock(), Mock(), "test")

    def test_custom_execution_summary(self):
        class CustomAgent(BaseAgent):
            def _execute(self, state):
                return state

            def _generate_execution_summary(self, state):
                return {
                    "log": "Custom log",
                    "learnings": ["Custom learning"],
                    "mistakes": [],
                    "reflection": "Custom reflection",
                }

        agent = CustomAgent(Mock(), Mock(), "custom")
        state = create_initial_state("test")
        agent(state)
        # 验证 daily log 被保存（不抛异常即可）


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
