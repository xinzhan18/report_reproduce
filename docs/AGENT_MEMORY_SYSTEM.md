# Agent Memory System 使用指南

## 概述

新的Agent Memory System使用**Markdown文件**管理agent的记忆、性格和学习，取代了之前的SQLite数据库系统。

---

## 快速开始

### 1. 初始化Agent记忆文件

**首次使用前，运行初始化脚本**：

```bash
python scripts/initialize_agent_memories.py
```

这将为所有4个agent（ideation, planning, experiment, writing）创建记忆文件：

```
data/agents/
├── ideation/
│   ├── persona.md          # 性格和工作风格
│   ├── memory.md           # 长期知识积累
│   ├── mistakes.md         # 错误记录和预防
│   └── daily/              # 每日执行日志（自动创建）
├── planning/
│   ├── persona.md
│   ├── memory.md
│   ├── mistakes.md
│   └── daily/
├── experiment/
│   ├── persona.md
│   ├── memory.md
│   ├── mistakes.md
│   └── daily/
└── writing/
    ├── persona.md
    ├── memory.md
    ├── mistakes.md
    └── daily/
```

### 2. 运行系统

初始化后，正常运行research pipeline：

```bash
python -m core.pipeline "momentum strategies in equity markets"
```

Agent会自动：
1. 在执行前加载所有记忆文件
2. 使用persona指导LLM行为
3. 在执行后保存daily log
4. 记录learnings和mistakes

---

## 文件说明

### persona.md - Agent性格档案

**用途**：定义agent的"灵魂" - 性格、工作风格、优势、弱点

**示例** (ideation/persona.md)：
```markdown
# Ideation Agent - Persona

## Core Identity
我是研究构思智能体，负责文献扫描、分析和假设生成。

## Personality & Approach

### 我的性格特征
- **高度好奇** - 我对新的研究方向充满好奇
- **深度分析** - 我会仔细分析每篇论文
- **创造性思考** - 我擅长从现有研究中生成创新的假设

### 我的工作风格
当面对一个新的研究方向时，我会：
1. 首先广泛扫描相关文献，建立全局视野
2. 然后深入分析关键论文，理解核心方法
3. 最后综合信息，识别研究缝隙并生成假设

### 我需要注意的弱点
- 有时过于雄心勃勃，提出的假设范围太广
- 可能在文献综述中陷入细节，失去主线
```

**可以编辑**：你可以直接编辑这个文件来定制agent性格！

---

### memory.md - 长期知识库

**用途**：存储跨项目的领域知识、策略、洞察

**自动更新**：Agent在学到新知识时会自动追加内容

**示例内容**：
```markdown
# Ideation Agent - Long-term Memory

## Domain Knowledge

### Momentum Strategies (2026-02-27)
观察：动量策略在牛市中表现优异，但在震荡市中容易失效
来源：分析了15篇动量策略论文（2023-2026）
关键洞察：需要结合市场状态识别机制
相关项目：proj_001, proj_005

### Mean Reversion (2026-03-01)
观察：均值回归在高波动环境中信号更可靠
来源：project_003的文献综述
关键洞察：需要动态调整回归窗口期
```

**手动编辑**：你也可以手动添加领域知识供agent参考

---

### mistakes.md - 错误注册表

**用途**：记录错误、分析原因、制定预防策略

**自动记录**：当agent遇到错误时会自动记录

**示例内容**：
```markdown
# Ideation Agent - Mistake Registry

## Active Mistakes (Must Avoid)

### M001: 文献搜索过于宽泛
- **Severity**: ⚠️ Medium (2/5)
- **First Occurred**: 2026-02-20 (proj_010)
- **Recurrence**: 3 times
- **Description**: 初始关键词搜索过于宽泛，返回大量低相关论文
- **Root Cause**: 没有预先定义排除关键词
- **How to Prevent**:
  - 使用排除关键词（如 NOT "machine learning"）
  - 预先限制时间范围（最近3年）
  - 使用arXiv分类过滤
- **Status**: ⚠️ Active - 仍在发生

## Resolved Mistakes (Learned)

### M002: 未考虑数据可得性 ✅
- **Occurred**: 2026-02-18
- **Resolution**: 现在在gap分析中默认评估实用性
- **Lesson**: 学术研究和实用策略有gap
```

**Agent会学习**：每次执行前，agent会读取这个文件避免重复错误

---

### daily/*.md - 每日执行日志

**用途**：记录每次执行的详细过程、结果、反思

**自动创建**：每次agent执行时自动保存到 `YYYY-MM-DD.md`

**示例内容**：
```markdown
# 2026-02-27 - Ideation Agent Daily Log

### Project: proj_015_momentum_emerging_markets

**Execution Time**: 14:30:15

**Execution Log**:
## Literature Review Execution
- Total papers found: 28
- Research direction: momentum strategies in emerging markets
- Research gaps identified: 5

### Research Gaps Found
- 跨市场动量策略 - 缺乏多个新兴市场的联合分析
- 高频数据可用性 - 新兴市场的高频数据研究几乎空白
- ...

**New Learnings**:
- 新兴市场的动量效应衰减更快
- 流动性筛选至关重要

**Reflection**:
## What Went Well
✅ 成功识别了数据质量这一核心问题
✅ 假设明确且可测试

## What Could Improve
⚠️ 初始论文筛选过于宽泛，浪费了10分钟
```

---

## 工作流程

### Agent执行时的记忆流程

```
1. 开始执行 (__call__ 方法被调用)
   ↓
2. 加载所有记忆
   - memories = memory_manager.load_all_memories()
   - 包含：persona, memory, mistakes, daily_recent (最近3天)
   ↓
3. 构建System Prompt
   - system_prompt = _build_system_prompt(memories)
   - 将所有记忆整合到system prompt中
   ↓
4. 执行主要任务
   - 所有LLM调用都使用system_prompt
   - Agent的行为受persona和past learnings影响
   ↓
5. 保存Daily Log
   - memory_manager.save_daily_log(...)
   - 记录：execution_log, learnings, mistakes, reflection
   ↓
6. 如果有错误，记录到mistakes.md
   - memory_manager.record_mistake(...)
```

---

## 高级用法

### 1. 手动编辑Persona

直接编辑 `data/agents/{agent_name}/persona.md`：

```bash
# 编辑ideation agent的性格
notepad data/agents/ideation/persona.md

# 或使用VSCode
code data/agents/ideation/persona.md
```

修改后，agent在下次执行时会自动加载新的persona。

### 2. 添加领域知识

手动向 `memory.md` 添加知识：

```bash
echo "\n### New Domain Knowledge (2026-02-27)\nMomentum strategies work best in trending markets\n" >> data/agents/ideation/memory.md
```

### 3. 查看Agent的学习历程

查看recent daily logs：

```bash
# 查看最近3天的执行日志
ls -lt data/agents/ideation/daily/ | head -4

# 查看特定日期
cat data/agents/ideation/daily/2026-02-27.md
```

### 4. 分析Mistake Trends

```bash
# 查看所有active mistakes
grep -A 10 "## Active Mistakes" data/agents/*/mistakes.md

# 统计mistake数量
grep "^### M" data/agents/*/mistakes.md | wc -l
```

---

## 与旧系统的对比

| 特性 | 旧系统 (SQLite) | 新系统 (Markdown) |
|-----|----------------|-------------------|
| **性格定义** | 数值化 (curiosity: 0.9) | 自然语言描述 |
| **可读性** | 需要SQL查询 | 直接用编辑器打开 |
| **LLM理解** | 需要Python转换 | 直接读取理解 |
| **版本控制** | 二进制数据库 | Git友好的文本文件 |
| **人工编辑** | 困难 | 简单 |
| **查看历史** | 需要写SQL | 直接查看.md文件 |

---

## 常见问题 (FAQ)

### Q: 为什么文件不是预先生成的？

**A**: 为了灵活性，文件采用**懒加载**方式 - 首次执行时自动创建。但你可以运行初始化脚本提前生成：
```bash
python scripts/initialize_agent_memories.py
```

### Q: 如何重置agent的记忆？

**A**: 删除对应的目录：
```bash
# 重置ideation agent
rm -rf data/agents/ideation

# 下次执行时会自动创建新的默认文件
```

### Q: 记忆文件会无限增长吗？

**A**:
- `persona.md` 和 `mistakes.md` 保持相对稳定
- `memory.md` 会增长，但可以手动整理或归档
- `daily/*.md` 会持续增加，建议定期归档旧日志

### Q: 可以多个项目共享记忆吗？

**A**: 可以！所有项目共享同一个 `data/agents/` 目录，agent会跨项目积累知识。

### Q: 如何备份agent记忆？

**A**: 直接复制整个目录：
```bash
# 备份
cp -r data/agents data/agents_backup_2026-02-27

# 恢复
cp -r data/agents_backup_2026-02-27 data/agents
```

或使用Git版本控制：
```bash
git add data/agents
git commit -m "Backup agent memories"
```

---

## 最佳实践

1. **定期查看daily logs** - 了解agent的学习进展
2. **手动整理memory.md** - 定期归纳重要洞察
3. **Review mistakes.md** - 确认错误是否被有效避免
4. **自定义persona** - 根据项目需求调整agent性格
5. **备份重要记忆** - 使用Git或手动备份

---

## 技术细节

### Memory Manager API

```python
from core.agent_memory_manager import get_agent_memory_manager

# 获取manager
manager = get_agent_memory_manager("ideation")

# 加载所有记忆
memories = manager.load_all_memories()
# Returns: {"persona": "...", "memory": "...", "mistakes": "...", "daily_recent": "..."}

# 保存daily log
manager.save_daily_log(
    project_id="proj_001",
    execution_log="Scanned 30 papers...",
    learnings=["Learning 1", "Learning 2"],
    mistakes=["Mistake 1"],
    reflection="Good execution overall"
)

# 更新长期记忆
manager.update_memory(
    new_insight="Momentum strategies effective in bull markets",
    category="Domain Knowledge"
)

# 记录错误
manager.record_mistake(
    mistake_id="M001",
    description="Search too broad",
    severity=2,
    root_cause="No exclusion keywords",
    prevention="Use NOT operator",
    project_id="proj_001"
)
```

---

## 总结

新的Markdown-based Memory System让agent拥有真正的"记忆"和"性格"：

✅ **自然语言** - LLM可以直接理解
✅ **人类可读** - 你可以查看和编辑
✅ **版本控制** - Git友好
✅ **持续学习** - 跨项目积累知识
✅ **错误预防** - 从past mistakes中学习

开始使用：
```bash
python scripts/initialize_agent_memories.py
```
