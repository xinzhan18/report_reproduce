"""
Initialize agent memory system - Generate all persona and memory files
初始化 agent 记忆系统
"""

# INPUT:  sys, pathlib, core.memory
# OUTPUT: initialize_all_agents 函数
# POSITION: Scripts/初始化脚本

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.memory import AgentMemory


def initialize_all_agents():
    """Initialize memory files for all four agents."""
    agents = ["ideation", "planning", "experiment", "writing"]

    print("=" * 70)
    print("Initializing Agent Memory System")
    print("=" * 70)
    print()

    for agent_name in agents:
        print(f"[*] Initializing {agent_name.upper()} Agent...")

        memory = AgentMemory(agent_name)

        # build_system_prompt will read existing files (or empty if not present)
        prompt = memory.build_system_prompt()

        files_created = []
        if memory.persona_file.exists():
            files_created.append(f"  + persona.md ({memory.persona_file.stat().st_size} bytes)")
        if memory.memory_file.exists():
            files_created.append(f"  + memory.md ({memory.memory_file.stat().st_size} bytes)")
        if memory.mistakes_file.exists():
            files_created.append(f"  + mistakes.md ({memory.mistakes_file.stat().st_size} bytes)")
        if memory.daily_dir.exists():
            files_created.append(f"  + daily/ directory")

        for file_info in files_created:
            print(f"  {file_info}")

        print(f"  Location: {memory.agent_dir}")
        print()

    print("=" * 70)
    print("[SUCCESS] All agent memory files initialized successfully!")
    print("=" * 70)
    print()
    print("You can now view and edit agent personas at:")
    print(f"   {project_root / 'data'}")
    print()


if __name__ == "__main__":
    initialize_all_agents()
