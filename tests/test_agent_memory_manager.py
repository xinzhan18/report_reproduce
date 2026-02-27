"""
Tests for AgentMemoryManager - Markdown-based memory system
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from datetime import datetime, timedelta
import shutil

# Import directly from the module file to avoid core.__init__.py
module_path = Path(__file__).parent.parent / "core" / "agent_memory_manager.py"
spec = importlib.util.spec_from_file_location("agent_memory_manager", module_path)
memory_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory_module)

AgentMemoryManager = memory_module.AgentMemoryManager
get_agent_memory_manager = memory_module.get_agent_memory_manager


@pytest.fixture
def temp_memory_dir(tmp_path):
    """创建临时测试目录"""
    return tmp_path / "test_agents"


@pytest.fixture
def ideation_manager(temp_memory_dir):
    """创建ideation agent的memory manager"""
    return AgentMemoryManager("ideation", base_path=str(temp_memory_dir))


class TestAgentMemoryManager:
    """测试AgentMemoryManager核心功能"""

    def test_initialization(self, ideation_manager, temp_memory_dir):
        """测试初始化创建正确的目录结构"""
        assert ideation_manager.agent_dir.exists()
        assert ideation_manager.daily_dir.exists()
        assert ideation_manager.agent_name == "ideation"

    def test_load_all_memories_creates_defaults(self, ideation_manager):
        """测试加载记忆时自动创建默认文件"""
        memories = ideation_manager.load_all_memories()

        # 验证返回所有必要的记忆类型
        assert "persona" in memories
        assert "memory" in memories
        assert "mistakes" in memories
        assert "daily_recent" in memories

        # 验证文件已创建
        assert ideation_manager.persona_file.exists()
        assert ideation_manager.memory_file.exists()
        assert ideation_manager.mistakes_file.exists()

        # 验证persona包含预期内容
        assert "Ideation Agent - Persona" in memories["persona"]
        assert "Core Identity" in memories["persona"]

    def test_save_daily_log(self, ideation_manager):
        """测试保存每日日志"""
        today = datetime.now().strftime("%Y-%m-%d")

        ideation_manager.save_daily_log(
            project_id="test_project_001",
            execution_log="Scanned 25 papers, found 3 gaps",
            learnings=["Learning 1", "Learning 2"],
            mistakes=["Mistake 1"],
            reflection="Good execution overall"
        )

        # 验证文件创建
        daily_file = ideation_manager.daily_dir / f"{today}.md"
        assert daily_file.exists()

        # 验证内容
        content = daily_file.read_text(encoding="utf-8")
        assert "test_project_001" in content
        assert "Scanned 25 papers" in content
        assert "Learning 1" in content
        assert "Mistake 1" in content
        assert "Good execution overall" in content

    def test_save_daily_log_append(self, ideation_manager):
        """测试同一天多次保存会追加内容"""
        today = datetime.now().strftime("%Y-%m-%d")

        # 第一次保存
        ideation_manager.save_daily_log(
            project_id="project_001",
            execution_log="First execution"
        )

        # 第二次保存
        ideation_manager.save_daily_log(
            project_id="project_002",
            execution_log="Second execution"
        )

        # 验证内容都存在
        daily_file = ideation_manager.daily_dir / f"{today}.md"
        content = daily_file.read_text(encoding="utf-8")
        assert "project_001" in content
        assert "project_002" in content
        assert "First execution" in content
        assert "Second execution" in content

    def test_update_memory(self, ideation_manager):
        """测试更新总体记忆"""
        # 先加载以创建默认文件
        ideation_manager.load_all_memories()

        # 添加新洞察
        ideation_manager.update_memory(
            new_insight="Momentum strategies work better in trending markets",
            category="Domain Knowledge"
        )

        # 验证内容
        content = ideation_manager.memory_file.read_text(encoding="utf-8")
        assert "Domain Knowledge" in content
        assert "Momentum strategies work better in trending markets" in content

    def test_record_mistake(self, ideation_manager):
        """测试记录错误"""
        # 先加载以创建默认文件
        ideation_manager.load_all_memories()

        # 记录错误
        ideation_manager.record_mistake(
            mistake_id="M001",
            description="Literature search too broad",
            severity=3,
            root_cause="Did not use exclusion keywords",
            prevention="Use NOT operator in search",
            project_id="test_project"
        )

        # 验证内容
        content = ideation_manager.mistakes_file.read_text(encoding="utf-8")
        assert "M001" in content
        assert "Literature search too broad" in content
        assert "3/5" in content
        assert "Did not use exclusion keywords" in content

    def test_load_recent_daily_logs(self, ideation_manager):
        """测试加载最近的daily logs"""
        # 创建多天的日志
        today = datetime.now()
        for i in range(5):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_file = ideation_manager.daily_dir / f"{date}.md"
            daily_file.write_text(f"# {date}\nTest content for {date}", encoding="utf-8")

        # 加载记忆（默认最近3天）
        memories = ideation_manager.load_all_memories()
        daily_recent = memories["daily_recent"]

        # 验证只包含最近3天
        for i in range(3):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            assert date in daily_recent

        # 验证不包含更早的
        old_date = (today - timedelta(days=4)).strftime("%Y-%m-%d")
        assert old_date not in daily_recent

    def test_get_agent_memory_manager(self, temp_memory_dir):
        """测试工厂函数"""
        manager = get_agent_memory_manager("planning")
        assert manager.agent_name == "planning"
        assert isinstance(manager, AgentMemoryManager)

    def test_multiple_agents(self, temp_memory_dir):
        """测试多个agent的记忆系统互不干扰"""
        ideation_mgr = AgentMemoryManager("ideation", base_path=str(temp_memory_dir))
        planning_mgr = AgentMemoryManager("planning", base_path=str(temp_memory_dir))

        # 加载各自的记忆
        ideation_mem = ideation_mgr.load_all_memories()
        planning_mem = planning_mgr.load_all_memories()

        # 验证persona不同
        assert "Ideation Agent" in ideation_mem["persona"]
        assert "Planning Agent" in planning_mem["persona"]

        # 保存daily log
        ideation_mgr.save_daily_log(project_id="ideation_project", execution_log="Ideation work")
        planning_mgr.save_daily_log(project_id="planning_project", execution_log="Planning work")

        # 验证文件在不同目录
        today = datetime.now().strftime("%Y-%m-%d")
        ideation_daily = ideation_mgr.daily_dir / f"{today}.md"
        planning_daily = planning_mgr.daily_dir / f"{today}.md"

        assert ideation_daily.exists()
        assert planning_daily.exists()

        # 验证内容独立
        assert "ideation_project" in ideation_daily.read_text()
        assert "planning_project" in planning_daily.read_text()
        assert "ideation_project" not in planning_daily.read_text()


class TestPersonaTemplates:
    """测试各个agent的persona模板"""

    def test_all_agent_personas_exist(self, temp_memory_dir):
        """测试所有四个agent都有persona模板"""
        agents = ["ideation", "planning", "experiment", "writing"]

        for agent_name in agents:
            manager = AgentMemoryManager(agent_name, base_path=str(temp_memory_dir))
            memories = manager.load_all_memories()

            # 验证persona包含必要部分
            persona = memories["persona"]
            assert f"{agent_name.title()} Agent - Persona" in persona
            assert "Core Identity" in persona
            assert "Personality & Approach" in persona

    def test_ideation_persona_content(self, temp_memory_dir):
        """测试Ideation agent的persona内容"""
        manager = AgentMemoryManager("ideation", base_path=str(temp_memory_dir))
        memories = manager.load_all_memories()
        persona = memories["persona"]

        # 验证关键特征
        assert "文献扫描" in persona or "literature" in persona.lower()
        assert "假设生成" in persona or "hypothesis" in persona.lower()
        assert "好奇" in persona or "curious" in persona.lower()

    def test_planning_persona_content(self, temp_memory_dir):
        """测试Planning agent的persona内容"""
        manager = AgentMemoryManager("planning", base_path=str(temp_memory_dir))
        memories = manager.load_all_memories()
        persona = memories["persona"]

        # 验证关键特征
        assert "实验规划" in persona or "experiment" in persona.lower()
        assert "严谨" in persona or "rigorous" in persona.lower()

    def test_experiment_persona_content(self, temp_memory_dir):
        """测试Experiment agent的persona内容"""
        manager = AgentMemoryManager("experiment", base_path=str(temp_memory_dir))
        memories = manager.load_all_memories()
        persona = memories["persona"]

        # 验证关键特征
        assert "回测" in persona or "backtest" in persona.lower()
        assert "代码" in persona or "code" in persona.lower()

    def test_writing_persona_content(self, temp_memory_dir):
        """测试Writing agent的persona内容"""
        manager = AgentMemoryManager("writing", base_path=str(temp_memory_dir))
        memories = manager.load_all_memories()
        persona = memories["persona"]

        # 验证关键特征
        assert "报告" in persona or "report" in persona.lower()
        assert "清晰" in persona or "clear" in persona.lower()


class TestMemoryIntegration:
    """测试记忆系统的集成场景"""

    def test_complete_workflow(self, temp_memory_dir):
        """测试完整的工作流程"""
        manager = AgentMemoryManager("ideation", base_path=str(temp_memory_dir))

        # 1. 首次加载（创建默认文件）
        memories = manager.load_all_memories()
        assert memories["persona"]
        assert memories["memory"]
        assert memories["mistakes"]

        # 2. 执行任务并保存日志
        manager.save_daily_log(
            project_id="proj_001",
            execution_log="Scanned 30 papers",
            learnings=["Found momentum pattern"],
            mistakes=[]
        )

        # 3. 记录新洞察到长期记忆
        manager.update_memory(
            new_insight="Momentum strategies effective in bull markets",
            category="Domain Knowledge"
        )

        # 4. 记录错误
        manager.record_mistake(
            mistake_id="M001",
            description="Search too broad",
            severity=2,
            root_cause="No exclusion keywords",
            prevention="Use NOT operator",
            project_id="proj_001"
        )

        # 5. 第二次加载（应该包含所有更新）
        memories2 = manager.load_all_memories()

        # 验证更新已保存
        assert "Momentum strategies effective" in memories2["memory"]
        assert "M001" in memories2["mistakes"]
        assert "proj_001" in memories2["daily_recent"]

    def test_memory_persistence_across_sessions(self, temp_memory_dir):
        """测试记忆在会话间持久化"""
        # 会话1：创建并保存
        manager1 = AgentMemoryManager("ideation", base_path=str(temp_memory_dir))
        manager1.load_all_memories()
        manager1.update_memory("Important insight", "Test")

        # 会话2：新实例应该能读取
        manager2 = AgentMemoryManager("ideation", base_path=str(temp_memory_dir))
        memories = manager2.load_all_memories()

        assert "Important insight" in memories["memory"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
