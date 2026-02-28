"""
Tests for AgentMemory (core.memory) - Markdown-based memory system
"""

# INPUT:  pytest, core.memory.AgentMemory, datetime, pathlib
# OUTPUT: 测试函数集
# POSITION: Tests/Unit Tests - AgentMemory 单元测试

import pytest
from pathlib import Path
from datetime import datetime, timedelta

from core.memory import AgentMemory


@pytest.fixture
def temp_memory_dir(tmp_path):
    """创建临时测试目录"""
    return tmp_path / "test_data"


@pytest.fixture
def ideation_memory(temp_memory_dir):
    """创建 ideation agent 的 AgentMemory"""
    return AgentMemory("ideation", base_path=str(temp_memory_dir))


class TestAgentMemory:
    """测试 AgentMemory 核心功能"""

    def test_initialization(self, ideation_memory, temp_memory_dir):
        assert ideation_memory.agent_dir.exists()
        assert ideation_memory.daily_dir.exists()
        assert ideation_memory.agent_name == "ideation"

    def test_build_system_prompt_empty(self, ideation_memory):
        """没有文件时 build_system_prompt 返回空"""
        prompt = ideation_memory.build_system_prompt()
        assert isinstance(prompt, str)

    def test_build_system_prompt_with_files(self, ideation_memory):
        """有文件时 build_system_prompt 包含内容"""
        ideation_memory.persona_file.write_text("I am ideation agent", encoding="utf-8")
        ideation_memory.memory_file.write_text("Key insight", encoding="utf-8")
        ideation_memory.mistakes_file.write_text("Common mistake", encoding="utf-8")

        prompt = ideation_memory.build_system_prompt()
        assert "Agent Persona" in prompt
        assert "I am ideation agent" in prompt
        assert "Long-term Memory" in prompt
        assert "Key insight" in prompt
        assert "Common Mistakes" in prompt
        assert "Common mistake" in prompt

    def test_save_daily_log(self, ideation_memory):
        today = datetime.now().strftime("%Y-%m-%d")

        ideation_memory.save_daily_log(
            project_id="test_project_001",
            execution_log="Scanned 25 papers, found 3 gaps",
            learnings=["Learning 1", "Learning 2"],
            mistakes=["Mistake 1"],
            reflection="Good execution overall",
        )

        daily_file = ideation_memory.daily_dir / f"{today}.md"
        assert daily_file.exists()

        content = daily_file.read_text(encoding="utf-8")
        assert "test_project_001" in content
        assert "Scanned 25 papers" in content
        assert "Learning 1" in content
        assert "Mistake 1" in content
        assert "Good execution overall" in content

    def test_save_daily_log_append(self, ideation_memory):
        today = datetime.now().strftime("%Y-%m-%d")

        ideation_memory.save_daily_log(project_id="project_001", execution_log="First execution")
        ideation_memory.save_daily_log(project_id="project_002", execution_log="Second execution")

        daily_file = ideation_memory.daily_dir / f"{today}.md"
        content = daily_file.read_text(encoding="utf-8")
        assert "project_001" in content
        assert "project_002" in content
        assert "First execution" in content
        assert "Second execution" in content

    def test_add_learning(self, ideation_memory):
        ideation_memory.memory_file.write_text("# Memory\n", encoding="utf-8")
        ideation_memory.add_learning(
            "Momentum strategies work better in trending markets",
            category="Domain Knowledge",
        )

        content = ideation_memory.memory_file.read_text(encoding="utf-8")
        assert "Domain Knowledge" in content
        assert "Momentum strategies work better in trending markets" in content

    def test_record_mistake(self, ideation_memory):
        ideation_memory.mistakes_file.write_text(
            "# Mistakes\n\n## Active Mistakes (Must Avoid)\n", encoding="utf-8"
        )

        ideation_memory.record_mistake(
            description="Literature search too broad",
            severity=3,
            root_cause="Did not use exclusion keywords",
            prevention="Use NOT operator in search",
            project_id="test_project",
        )

        content = ideation_memory.mistakes_file.read_text(encoding="utf-8")
        assert "Literature search too broad" in content
        assert "3/5" in content
        assert "Did not use exclusion keywords" in content

    def test_recent_daily_logs(self, ideation_memory):
        today = datetime.now()
        for i in range(5):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_file = ideation_memory.daily_dir / f"{date}.md"
            daily_file.write_text(f"# {date}\nTest content for {date}", encoding="utf-8")

        prompt = ideation_memory.build_system_prompt()

        # 最近 3 天应出现在 prompt 中
        for i in range(3):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            assert date in prompt

        # 第 5 天不应出现
        old_date = (today - timedelta(days=4)).strftime("%Y-%m-%d")
        assert old_date not in prompt

    def test_multiple_agents(self, temp_memory_dir):
        ideation = AgentMemory("ideation", base_path=str(temp_memory_dir))
        planning = AgentMemory("planning", base_path=str(temp_memory_dir))

        ideation.persona_file.write_text("Ideation persona", encoding="utf-8")
        planning.persona_file.write_text("Planning persona", encoding="utf-8")

        assert "Ideation" in ideation.build_system_prompt()
        assert "Planning" in planning.build_system_prompt()


class TestMemoryIntegration:

    def test_complete_workflow(self, temp_memory_dir):
        memory = AgentMemory("ideation", base_path=str(temp_memory_dir))

        # 1. 创建初始文件
        memory.persona_file.write_text("# Ideation Persona\nI explore", encoding="utf-8")
        memory.memory_file.write_text("# Memory\n", encoding="utf-8")
        memory.mistakes_file.write_text("# Mistakes\n\n## Active Mistakes (Must Avoid)\n", encoding="utf-8")

        # 2. build prompt
        prompt = memory.build_system_prompt()
        assert "I explore" in prompt

        # 3. 保存日志
        memory.save_daily_log(project_id="proj_001", execution_log="Scanned 30 papers")

        # 4. 添加学习
        memory.add_learning("Momentum works in bull markets", "Domain Knowledge")

        # 5. 记录错误
        memory.record_mistake(
            description="Search too broad", severity=2,
            root_cause="No exclusion keywords", prevention="Use NOT operator",
            project_id="proj_001",
        )

        # 6. 第二次 build prompt 应包含所有内容
        prompt2 = memory.build_system_prompt()
        assert "Momentum works in bull markets" in prompt2
        assert "Search too broad" in prompt2

    def test_persistence_across_instances(self, temp_memory_dir):
        m1 = AgentMemory("ideation", base_path=str(temp_memory_dir))
        m1.memory_file.write_text("# Memory\n", encoding="utf-8")
        m1.add_learning("Important insight", "Test")

        m2 = AgentMemory("ideation", base_path=str(temp_memory_dir))
        prompt = m2.build_system_prompt()
        assert "Important insight" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
