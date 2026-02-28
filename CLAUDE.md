# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**Research Automation Agent System (FARS)** - A fully automated research system for quantitative finance that orchestrates the entire research lifecycle using a multi-agent collaboration architecture powered by Claude AI (Anthropic API).

This system automates quantitative finance research from literature review through experiment execution to report generation using four specialized AI agents working in a pipeline.



## 开发规范

1. 任何情况下不要兼容旧代码 直接做完整的修改 采用最简单的方法来更新代码
2. 中文回复
---

## 全局架构地图 (Global Architecture Map)

### 五层架构设计

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 5: Scheduling & Automation (scheduler/)              │
│   - DailyScanner, PipelineRunner                           │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: Pipeline Orchestration (core/pipeline.py)         │
│   - LangGraph workflow, state routing                      │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Agents (agents/)                                  │
│   - BaseAgent, IdeationAgent, PlanningAgent,               │
│     ExperimentAgent, WritingAgent                           │
│   - agents/llm.py (call_llm / call_llm_json)              │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Intelligence & State (core/)                      │
│   - State management, Memory system, Knowledge graph       │
│   - AgentMemory (core/memory.py), DocumentMemoryManager    │
│   - Database, KnowledgeGraph                               │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: Tools & Configuration (tools/, config/)           │
│   - PaperFetcher, BacktestEngine, DataFetcher              │
│   - LLM Config, Auth Config, Agent Config                  │
└─────────────────────────────────────────────────────────────┘
```

### 数据流向 (Data Flow)

```
Scheduler → Pipeline → Agents → Tools → Data Storage
    ↓          ↓         ↓        ↓         ↓
  Config ← Core/State → Memory → Database → Outputs
```

### 模块目录清单

每个模块都有独立的CLAUDE.md文档：

- **agents/** - AI智能体层 (BaseAgent + 4个核心Agent + llm.py)
- **config/** - 系统配置层 (LLM、认证、数据源配置)
- **core/** - 核心基础设施层 (状态、Pipeline、AgentMemory、知识图谱、数据库)
- **data/** - Agent记忆数据 (persona.md, memory.md, mistakes.md, daily/)
- **tools/** - 工具库层 (数据获取、回测、文件管理)
- **scheduler/** - 调度自动化层 (定时任务、执行器)
- **tests/** - 测试套件层
- **scripts/** - 运维脚本层
- **docs/** - 项目文档
- **outputs/** - 研究输出目录
- **plans/** - 计划文档目录

---

## 强制回环检查规则 (Mandatory Loop-Back Check Rules)

### 规则 1: 文件修改必须更新三级文档

**任何代码修改后，必须按顺序检查和更新：**

1. **文件头注释** (INPUT/OUTPUT/POSITION) - 更新依赖、输出、地位
2. **所属文件夹的 CLAUDE.md** - 更新文件功能描述
3. **根目录 CLAUDE.md** - 如果涉及模块间关系变化

### 规则 2: 触发更新的场景

**文件头注释更新场景:**
- ✓ 添加/删除 import 语句 → 更新 INPUT
- ✓ 修改函数/类的公开接口 → 更新 OUTPUT
- ✓ 改变模块在系统中的职责 → 更新 POSITION

**文件夹 CLAUDE.md 更新场景:**
- ✓ 添加/删除文件 → 更新文件清单
- ✓ 修改文件的核心功能 → 更新文件功能描述
- ✓ 改变文件间的依赖关系 → 更新架构说明

**根 CLAUDE.md 更新场景:**
- ✓ 添加新模块/文件夹 → 更新模块目录清单
- ✓ 修改模块间的架构关系 → 更新五层架构设计
- ✓ 改变数据流或控制流 → 更新数据流向图

### 规则 3: 提交前检查清单

```
□ 已更新修改文件的文件头注释
□ 已更新所属文件夹的 CLAUDE.md
□ 如有必要，已更新根 CLAUDE.md
□ 所有三级文档内容一致
□ 更新历史已记录修改日期和内容
```
## Plan规则

### 规则1：
所有的plan doc必须存在一个对应的checklist 每次执行结束后就更新这个checklist

---

## 文档维护工具 (Documentation Maintenance Tools)

### 检查所有文件夹是否有 CLAUDE.md (Bash)

```bash
# Check all folders have CLAUDE.md
for dir in agents config core tools scheduler tests scripts; do
    if [ ! -f "$dir/CLAUDE.md" ]; then
        echo "❌ Missing: $dir/CLAUDE.md"
    else
        echo "✓ Found: $dir/CLAUDE.md"
    fi
done
```

### 检查所有Python文件是否有文件头注释 (Bash)

```bash
# Check all .py files have headers
find . -name "*.py" -not -path "*/.*" -not -path "*/__pycache__/*" | while read file; do
    if ! grep -q "# INPUT:" "$file"; then
        echo "❌ Missing header: $file"
    fi
done
```


