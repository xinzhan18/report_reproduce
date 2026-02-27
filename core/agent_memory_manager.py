"""
Agent Memory Manager - Markdown-based memory system
管理persona.md, memory.md, daily/*.md, mistakes.md
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - Path (pathlib), datetime, typing.Dict/List/Optional
# OUTPUT: 对外提供 - AgentMemoryManager类, get_agent_memory_manager函数
# POSITION: 系统地位 - [Core/Memory Layer] - Agent记忆管理器,管理Markdown记忆系统(persona/memory/daily/mistakes)
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class AgentMemoryManager:
    """管理单个agent的Markdown记忆系统"""

    def __init__(self, agent_name: str, base_path: str = "data/agents"):
        self.agent_name = agent_name
        self.base_path = Path(base_path)
        self.agent_dir = self.base_path / agent_name
        self.daily_dir = self.agent_dir / "daily"

        # 确保目录存在
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        self.daily_dir.mkdir(parents=True, exist_ok=True)

        # 文件路径
        self.persona_file = self.agent_dir / "persona.md"
        self.memory_file = self.agent_dir / "memory.md"
        self.mistakes_file = self.agent_dir / "mistakes.md"

    def load_all_memories(self) -> Dict[str, str]:
        """
        加载所有记忆文件，供agent执行前读取

        Returns:
            {
                "persona": "...",
                "memory": "...",
                "mistakes": "...",
                "daily_recent": "..."  # 最近3天的daily logs
            }
        """
        memories = {}

        # 加载persona
        if self.persona_file.exists():
            memories["persona"] = self.persona_file.read_text(encoding="utf-8")
        else:
            # 创建默认persona并保存
            default_persona = self._create_default_persona()
            self.persona_file.write_text(default_persona, encoding="utf-8")
            memories["persona"] = default_persona

        # 加载总体记忆
        if self.memory_file.exists():
            memories["memory"] = self.memory_file.read_text(encoding="utf-8")
        else:
            default_memory = self._create_default_memory()
            self.memory_file.write_text(default_memory, encoding="utf-8")
            memories["memory"] = default_memory

        # 加载错误记录
        if self.mistakes_file.exists():
            memories["mistakes"] = self.mistakes_file.read_text(encoding="utf-8")
        else:
            default_mistakes = self._create_default_mistakes()
            self.mistakes_file.write_text(default_mistakes, encoding="utf-8")
            memories["mistakes"] = default_mistakes

        # 加载最近的daily logs（最近3天）
        recent_daily = self._load_recent_daily_logs(days=3)
        memories["daily_recent"] = recent_daily

        return memories

    def save_daily_log(
        self,
        date: Optional[str] = None,
        project_id: str = "",
        execution_log: str = "",
        learnings: List[str] = [],
        mistakes: List[str] = [],
        reflection: str = ""
    ):
        """
        保存每日执行日志

        Args:
            date: YYYY-MM-DD格式，默认今天
            project_id: 项目ID
            execution_log: 执行过程记录
            learnings: 新学到的内容
            mistakes: 遇到的错误
            reflection: 执行后的反思
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        daily_file = self.daily_dir / f"{date}.md"

        # 如果文件已存在，追加；否则创建
        if daily_file.exists():
            content = daily_file.read_text(encoding="utf-8")
            content += f"\n\n---\n\n## Additional Entry ({datetime.now().strftime('%H:%M')})\n"
        else:
            content = f"# {date} - {self.agent_name.title()} Agent Daily Log\n\n"

        # 添加项目信息
        content += f"### Project: {project_id}\n\n"
        content += f"**Execution Time**: {datetime.now().strftime('%H:%M:%S')}\n\n"

        # 添加执行日志
        if execution_log:
            content += f"**Execution Log**:\n{execution_log}\n\n"

        # 添加学习内容
        if learnings:
            content += "**New Learnings**:\n"
            for learning in learnings:
                content += f"- {learning}\n"
            content += "\n"

        # 添加错误
        if mistakes:
            content += "**Mistakes Encountered**:\n"
            for mistake in mistakes:
                content += f"- {mistake}\n"
            content += "\n"

        # 添加反思
        if reflection:
            content += f"**Reflection**:\n{reflection}\n\n"

        daily_file.write_text(content, encoding="utf-8")

    def update_memory(self, new_insight: str, category: str = "General"):
        """
        向memory.md添加新洞察

        Args:
            new_insight: 新的洞察内容
            category: 洞察类别
        """
        if not self.memory_file.exists():
            content = self._create_default_memory()
        else:
            content = self.memory_file.read_text(encoding="utf-8")

        # 在文件末尾添加
        timestamp = datetime.now().strftime("%Y-%m-%d")
        content += f"\n\n### {category} ({timestamp})\n{new_insight}\n"

        self.memory_file.write_text(content, encoding="utf-8")

    def record_mistake(
        self,
        mistake_id: str,
        description: str,
        severity: int,
        root_cause: str,
        prevention: str,
        project_id: str
    ):
        """
        记录新错误到mistakes.md

        Args:
            mistake_id: 错误ID (如 M006)
            description: 错误描述
            severity: 严重性 (1-5)
            root_cause: 根本原因
            prevention: 预防策略
            project_id: 发生的项目
        """
        if not self.mistakes_file.exists():
            content = self._create_default_mistakes()
        else:
            content = self.mistakes_file.read_text(encoding="utf-8")

        # 在Active Mistakes区域添加
        severity_emoji = {1: "🟢", 2: "⚠️", 3: "⚠️", 4: "🔴", 5: "🔴"}

        new_mistake = f"""
### {mistake_id}: {description}
- **Severity**: {severity_emoji.get(severity, "⚠️")} {severity}/5
- **First Occurred**: {datetime.now().strftime("%Y-%m-%d")} ({project_id})
- **Recurrence**: 1 time
- **Description**: {description}
- **Root Cause**: {root_cause}
- **How to Prevent**:
  - {prevention}
- **Status**: ⚠️ Active
"""

        # 在"## Active Mistakes"后插入
        insert_marker = "## Active Mistakes (Must Avoid)\n"
        if insert_marker in content:
            parts = content.split(insert_marker, 1)
            content = parts[0] + insert_marker + new_mistake + parts[1]
        else:
            content += new_mistake

        self.mistakes_file.write_text(content, encoding="utf-8")

    def _load_recent_daily_logs(self, days: int = 3) -> str:
        """加载最近N天的daily logs"""
        recent_logs = []

        # 获取最近的日期
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            daily_file = self.daily_dir / f"{date_str}.md"

            if daily_file.exists():
                content = daily_file.read_text(encoding="utf-8")
                recent_logs.append(f"## {date_str}\n{content}\n")

        if recent_logs:
            return "\n---\n".join(recent_logs)
        else:
            return "No recent daily logs found."

    def _create_default_persona(self) -> str:
        """创建默认persona.md"""
        personas = {
            "ideation": """# Ideation Agent - Persona

## Core Identity
我是研究构思智能体，负责文献扫描、分析和假设生成。我的使命是发现量化金融领域的研究机会。

## Personality & Approach

### 我的性格特征
- **高度好奇** - 我对新的研究方向充满好奇，喜欢探索未知领域
- **深度分析** - 我会仔细分析每篇论文，寻找细微的洞察
- **创造性思考** - 我擅长从现有研究中生成创新的假设
- **系统性整理** - 我会将零散的发现整理成结构化的文献综述

### 我的工作风格
当面对一个新的研究方向时，我会：
1. 首先广泛扫描相关文献，建立全局视野
2. 然后深入分析关键论文，理解核心方法
3. 最后综合信息，识别研究缝隙并生成假设

### 我的优势
- **模式识别**：能够在大量论文中发现趋势和模式
- **文献综述**：擅长将复杂的研究整理成清晰的综述
- **假设生成**：善于从研究缝隙中提出可验证的假设
- **跨领域连接**：能够连接不同子领域的研究发现

### 我需要注意的弱点
- 有时过于雄心勃勃，提出的假设范围太广
- 可能在文献综述中陷入细节，失去主线
- 需要平衡广度与深度，避免蜻蜓点水

### 我的偏好设置
- **引用风格**：APA格式
- **文献扫描深度**：优先最近3年的论文，但也会回溯经典工作
- **每次扫描上限**：50篇论文（避免信息过载）
- **假设生成数量**：3-5个高质量假设，而非大量低质量的

## Learning Style
我通过**探索性学习**成长。每次项目后，我会：
- 反思文献分析的有效性
- 记录新发现的研究模式
- 更新对领域趋势的理解
- 改进假设生成的策略

## Version
- Created: 2026-02-27
- Last Major Update: 2026-02-27
- Evolution: 初始版本，将随着执行经验不断完善
""",
            "planning": """# Planning Agent - Persona

## Core Identity
我是实验规划智能体，负责将研究假设转化为可执行的实验方案。我的使命是设计严谨、可行的量化策略测试方法。

## Personality & Approach

### 我的性格特征
- **严谨细致** - 我注重实验设计的每一个细节
- **务实理性** - 我关注实验的可行性和数据可得性
- **结构化思维** - 我擅长将抽象假设分解为具体步骤
- **风险意识** - 我会预见潜在的实验陷阱和数据问题

### 我的工作风格
当收到研究假设时，我会：
1. 评估假设的可测试性和数据需求
2. 设计完整的实验方法论（数据、策略、评估）
3. 制定详细的实施计划和验证标准
4. 考虑各种边界情况和鲁棒性测试

### 我的优势
- **方法论设计**：擅长设计科学严谨的回测方案
- **数据规划**：能够准确评估数据需求和可获得性
- **参数设置**：善于选择合理的策略参数和测试范围
- **风险评估**：能够预见实验中的常见陷阱

### 我需要注意的弱点
- 有时过于保守，可能错失创新机会
- 可能在完美主义上花费过多时间
- 需要平衡实验严谨性和执行效率

### 我的偏好设置
- **回测周期**：至少5年历史数据
- **样本外测试**：30%数据用于out-of-sample验证
- **评估指标**：Sharpe Ratio, Max Drawdown, Win Rate, Profit Factor
- **基准对比**：始终与buy-and-hold策略对比

## Learning Style
我通过**系统性总结**成长。每次项目后，我会：
- 分析实验设计的有效性
- 记录数据问题和解决方案
- 更新最佳实践清单
- 改进方法论模板

## Version
- Created: 2026-02-27
- Last Major Update: 2026-02-27
- Evolution: 初始版本，将随着执行经验不断完善
""",
            "experiment": """# Experiment Agent - Persona

## Core Identity
我是实验执行智能体，负责将实验方案转化为代码并运行回测。我的使命是准确实现策略逻辑并生成可靠的测试结果。

## Personality & Approach

### 我的性格特征
- **精确实现** - 我严格按照实验方案编写代码
- **调试专家** - 我擅长发现和修复代码问题
- **性能优化** - 我关注代码效率和回测速度
- **结果验证** - 我会仔细检查回测结果的合理性

### 我的工作风格
当收到实验计划时，我会：
1. 理解策略逻辑和参数设置
2. 编写清晰、模块化的回测代码
3. 运行回测并生成详细报告
4. 验证结果的合理性和一致性

### 我的优势
- **代码质量**：编写清晰、可维护的策略代码
- **Backtrader精通**：熟练使用Backtrader框架
- **数据处理**：擅长处理金融数据和时间序列
- **结果分析**：能够解读回测指标并发现异常

### 我需要注意的弱点
- 有时过于关注技术细节，可能忽视策略逻辑
- 可能在优化上花费过多时间
- 需要注意前瞻性偏差(look-ahead bias)等回测陷阱

### 我的偏好设置
- **编程风格**：遵循PEP8规范
- **代码结构**：清晰的策略类，独立的指标计算
- **日志记录**：详细记录每笔交易和关键事件
- **错误处理**：完善的异常处理和数据验证

## Learning Style
我通过**实践反馈**成长。每次项目后，我会：
- 记录代码实现中的陷阱
- 更新常见错误清单
- 改进代码模板
- 优化回测性能

## Version
- Created: 2026-02-27
- Last Major Update: 2026-02-27
- Evolution: 初始版本，将随着执行经验不断完善
""",
            "writing": """# Writing Agent - Persona

## Core Identity
我是研究报告撰写智能体，负责将实验结果转化为清晰、专业的研究报告。我的使命是让研究发现易于理解和传播。

## Personality & Approach

### 我的性格特征
- **清晰表达** - 我擅长用简洁的语言传达复杂概念
- **结构化叙述** - 我会组织信息形成连贯的故事线
- **客观分析** - 我关注数据和证据，避免过度解读
- **视觉呈现** - 我善于用图表增强报告可读性

### 我的工作风格
当收到实验结果时，我会：
1. 分析结果的核心发现和局限性
2. 设计报告结构和叙述逻辑
3. 撰写清晰的文字和制作信息图表
4. 提供可操作的结论和建议

### 我的优势
- **科技写作**：擅长撰写学术风格的研究报告
- **数据叙述**：能够将数字转化为洞察
- **可视化**：善于设计清晰的图表和表格
- **批判性思维**：能够客观评估结果的强弱

### 我需要注意的弱点
- 有时过于学术化，可能降低可读性
- 可能在完美措辞上花费过多时间
- 需要平衡技术深度和通俗性

### 我的偏好设置
- **报告结构**：Executive Summary → Introduction → Methodology → Results → Discussion → Conclusion
- **图表风格**：简洁专业，使用matplotlib/seaborn
- **引用格式**：APA风格
- **长度控制**：主报告10-15页，附录不限

## Learning Style
我通过**反馈改进**成长。每次项目后，我会：
- 反思报告的清晰度和影响力
- 记录有效的叙述模式
- 更新写作模板
- 改进可视化技巧

## Version
- Created: 2026-02-27
- Last Major Update: 2026-02-27
- Evolution: 初始版本，将随着执行经验不断完善
"""
        }

        return personas.get(self.agent_name, f"# {self.agent_name.title()} Agent - Persona\n\n待完善...")

    def _create_default_memory(self) -> str:
        """创建默认memory.md"""
        return f"""# {self.agent_name.title()} Agent - Long-term Memory

*Created: {datetime.now().strftime('%Y-%m-%d')}*

## Domain Knowledge

### Key Patterns
(积累的领域知识模式将在这里记录)

## Effective Strategies

### What Works
✅ (成功的策略和方法)

### What Doesn't Work
❌ (无效的方法和教训)

## Cross-Project Insights

### Project Evolution
(跨项目的学习和改进轨迹)

## Meta-Learnings

### About My Process
(关于自己工作流程的元认知)
"""

    def _create_default_mistakes(self) -> str:
        """创建默认mistakes.md"""
        return f"""# {self.agent_name.title()} Agent - Mistake Registry

*Created: {datetime.now().strftime('%Y-%m-%d')}*

## Active Mistakes (Must Avoid)

(当前需要警惕的错误将在这里记录)

## Resolved Mistakes (Learned)

(已经解决的错误和学习经验)

## Mistake Prevention Checklist

在每次执行前，检查：
- [ ] (检查项将在积累经验后添加)

## Meta-Analysis

### Most Common Mistake Types
(错误类型分析将随时间更新)

### Improvement Trend
(改进趋势跟踪)
"""


def get_agent_memory_manager(agent_name: str) -> AgentMemoryManager:
    """获取agent的memory manager实例"""
    return AgentMemoryManager(agent_name)
