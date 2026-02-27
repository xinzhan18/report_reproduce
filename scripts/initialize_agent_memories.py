"""
Initialize agent memory system - Generate all persona and memory files
初始化agent记忆系统 - 生成所有persona和记忆文件
"""

import sys
import importlib.util
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import directly from the module file to avoid core.__init__.py
module_path = project_root / "core" / "agent_memory_manager.py"
spec = importlib.util.spec_from_file_location("agent_memory_manager", module_path)
memory_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory_module)

get_agent_memory_manager = memory_module.get_agent_memory_manager


def initialize_all_agents():
    """Initialize memory files for all four agents"""
    agents = ["ideation", "planning", "experiment", "writing"]

    print("=" * 70)
    print("Initializing Agent Memory System")
    print("=" * 70)
    print()

    for agent_name in agents:
        print(f"[*] Initializing {agent_name.upper()} Agent...")

        # Get memory manager
        manager = get_agent_memory_manager(agent_name)

        # Load all memories (this will create default files if they don't exist)
        memories = manager.load_all_memories()

        # Verify files were created
        files_created = []
        if manager.persona_file.exists():
            files_created.append(f"  + persona.md ({manager.persona_file.stat().st_size} bytes)")
        if manager.memory_file.exists():
            files_created.append(f"  + memory.md ({manager.memory_file.stat().st_size} bytes)")
        if manager.mistakes_file.exists():
            files_created.append(f"  + mistakes.md ({manager.mistakes_file.stat().st_size} bytes)")
        if manager.daily_dir.exists():
            files_created.append(f"  + daily/ directory")

        for file_info in files_created:
            print(f"  {file_info}")

        print(f"  Location: {manager.agent_dir}")
        print()

    print("=" * 70)
    print("[SUCCESS] All agent memory files initialized successfully!")
    print("=" * 70)
    print()
    print("You can now view and edit agent personas at:")
    print(f"   {project_root / 'data' / 'agents'}")
    print()
    print("Tips:")
    print("   - Edit persona.md to customize agent personalities")
    print("   - memory.md will accumulate knowledge over time")
    print("   - mistakes.md will track errors and prevention strategies")
    print("   - daily/*.md logs are created automatically during execution")
    print()


if __name__ == "__main__":
    initialize_all_agents()
