"""
AgentMemory - 统一的 Markdown 记忆管理器

直接读取 data/{agent_name}/ 下的 persona.md / memory.md / mistakes.md / daily/
构建 system prompt 时不经过 dict 中转，彻底修复原 key 不匹配 bug。
"""

# INPUT:  pathlib, datetime, typing
# OUTPUT: AgentMemory 类
# POSITION: Core 层记忆管理

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional


class AgentMemory:
    """管理单个 agent 的 Markdown 记忆系统。"""

    def __init__(self, agent_name: str, base_path: str = "data"):
        self.agent_name = agent_name
        self.agent_dir = Path(base_path) / agent_name
        self.daily_dir = self.agent_dir / "daily"

        # 确保目录存在
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        self.daily_dir.mkdir(parents=True, exist_ok=True)

        # 文件路径
        self.persona_file = self.agent_dir / "persona.md"
        self.memory_file = self.agent_dir / "memory.md"
        self.mistakes_file = self.agent_dir / "mistakes.md"

    # ------------------------------------------------------------------
    # System prompt 构建（直接读文件，不经过 dict 中转）
    # ------------------------------------------------------------------

    def build_system_prompt(self) -> str:
        """读取所有记忆文件，拼接为 system prompt。"""
        parts: list[str] = []

        # 1. Persona
        persona = self._read_file(self.persona_file)
        if persona:
            parts.append("# Agent Persona\n")
            parts.append(persona)
            parts.append("\n\n")

        # 2. Long-term memory
        memory = self._read_file(self.memory_file)
        if memory:
            parts.append("# Long-term Memory\n")
            parts.append(memory)
            parts.append("\n\n")

        # 3. Mistakes
        mistakes = self._read_file(self.mistakes_file)
        if mistakes:
            parts.append("# Common Mistakes to Avoid\n")
            parts.append(mistakes)
            parts.append("\n\n")

        # 4. Recent daily logs
        daily = self._load_recent_daily_logs(days=3)
        if daily and daily != "No recent daily logs found.":
            parts.append("# Recent Execution Context\n")
            parts.append(daily)
            parts.append("\n")

        return "".join(parts)

    # ------------------------------------------------------------------
    # 写入操作
    # ------------------------------------------------------------------

    def save_daily_log(
        self,
        project_id: str,
        execution_log: str = "",
        learnings: Optional[List[str]] = None,
        mistakes: Optional[List[str]] = None,
        reflection: str = "",
    ):
        """保存每日执行日志。"""
        date = datetime.now().strftime("%Y-%m-%d")
        daily_file = self.daily_dir / f"{date}.md"

        if daily_file.exists():
            content = daily_file.read_text(encoding="utf-8")
            content += f"\n\n---\n\n## Additional Entry ({datetime.now().strftime('%H:%M')})\n"
        else:
            content = f"# {date} - {self.agent_name.title()} Agent Daily Log\n\n"

        content += f"### Project: {project_id}\n\n"
        content += f"**Execution Time**: {datetime.now().strftime('%H:%M:%S')}\n\n"

        if execution_log:
            content += f"**Execution Log**:\n{execution_log}\n\n"

        if learnings:
            content += "**New Learnings**:\n"
            for item in learnings:
                content += f"- {item}\n"
            content += "\n"

        if mistakes:
            content += "**Mistakes Encountered**:\n"
            for item in mistakes:
                content += f"- {item}\n"
            content += "\n"

        if reflection:
            content += f"**Reflection**:\n{reflection}\n\n"

        daily_file.write_text(content, encoding="utf-8")

    def add_learning(self, insight: str, category: str = "General"):
        """向 memory.md 追加新洞察。"""
        if not self.memory_file.exists():
            content = f"# {self.agent_name.title()} Agent - Long-term Memory\n"
        else:
            content = self.memory_file.read_text(encoding="utf-8")

        timestamp = datetime.now().strftime("%Y-%m-%d")
        content += f"\n\n### {category} ({timestamp})\n{insight}\n"
        self.memory_file.write_text(content, encoding="utf-8")

    def record_mistake(
        self,
        description: str,
        severity: int,
        root_cause: str,
        prevention: str,
        project_id: str,
    ):
        """记录新错误到 mistakes.md。"""
        if not self.mistakes_file.exists():
            content = f"# {self.agent_name.title()} Agent - Mistake Registry\n\n## Active Mistakes (Must Avoid)\n"
        else:
            content = self.mistakes_file.read_text(encoding="utf-8")

        severity_emoji = {1: "🟢", 2: "⚠️", 3: "⚠️", 4: "🔴", 5: "🔴"}
        new_mistake = f"""
### {description[:60]}
- **Severity**: {severity_emoji.get(severity, "⚠️")} {severity}/5
- **First Occurred**: {datetime.now().strftime("%Y-%m-%d")} ({project_id})
- **Description**: {description}
- **Root Cause**: {root_cause}
- **Prevention**: {prevention}
- **Status**: ⚠️ Active
"""
        insert_marker = "## Active Mistakes (Must Avoid)\n"
        if insert_marker in content:
            parts = content.split(insert_marker, 1)
            content = parts[0] + insert_marker + new_mistake + parts[1]
        else:
            content += new_mistake

        self.mistakes_file.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _read_file(self, path: Path) -> str:
        """安全读取文件，不存在则返回空字符串。"""
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _load_recent_daily_logs(self, days: int = 3) -> str:
        """加载最近 N 天的 daily logs。"""
        logs: list[str] = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            daily_file = self.daily_dir / f"{date.strftime('%Y-%m-%d')}.md"
            if daily_file.exists():
                content = daily_file.read_text(encoding="utf-8")
                logs.append(f"## {date.strftime('%Y-%m-%d')}\n{content}\n")

        return "\n---\n".join(logs) if logs else "No recent daily logs found."
