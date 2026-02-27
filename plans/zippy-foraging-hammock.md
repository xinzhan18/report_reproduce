# 三级文档系统实施计划

## Context (背景与目标)

当前代码库已经是一个成熟的量化金融研究自动化系统，拥有60个Python文件分布在多个核心代码目录中。但是缺乏系统化的文档层级结构，导致代码维护时难以快速理解模块间的依赖关系和每个文件的职责定位。

本次任务目标是实施一个**三级文档系统**，强制建立"代码更新→文档更新"的回环检查机制：

1. **文件级头注释**：每个Python文件顶部添加中文INPUT/OUTPUT/POSITION注释
2. **文件夹级CLAUDE.md**：每个目录包含架构说明和文件清单
3. **根级CLAUDE.md扩展**：添加全局架构地图和强制回环检查规则

这将确保每次代码修改后，文档自动保持同步，形成自维护的文档生态。

---

## Implementation Approach (实施方案)

### Phase 1: 创建模板和更新根文档 (优先级最高)

**1.1 更新根CLAUDE.md**

在现有的 `F:\shuxu\report_reproduce\CLAUDE.md` 末尾追加以下内容：

```markdown
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
│   - IdeationAgent, PlanningAgent, ExperimentAgent,         │
│     WritingAgent                                            │
│   - Services: LLMService, IntelligenceContext,             │
│     OutputManager                                           │
│   - Utils: JSONParser, PromptBuilder                        │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Intelligence & State (core/)                      │
│   - State management, Memory system, Knowledge graph       │
│   - AgentMemoryManager, DocumentMemoryManager              │
│   - Database, SelfReflection, AgentPersona                 │
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

- **agents/** - AI智能体层 (4个核心Agent + services + utils)
- **config/** - 系统配置层 (LLM、认证、数据源配置)
- **core/** - 核心基础设施层 (状态、Pipeline、记忆、数据库)
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

### 规则 4: 审查责任

- **开发者**: 每次提交代码时执行回环检查
- **Claude Code**: 修改代码时主动执行回环检查
- **Code Review**: PR 审查必须验证文档完整性

---

## 文档维护工具 (Documentation Maintenance Tools)

### 检查所有文件夹是否有 CLAUDE.md (Bash)

```bash
# Check all folders have CLAUDE.md
for dir in agents agents/services agents/utils config core tools scheduler tests scripts \
           docs outputs plans; do
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

### PowerShell版本 (Windows)

```powershell
# Check folders
$folders = @("agents", "agents/services", "agents/utils", "config", "core", "tools",
             "scheduler", "tests", "scripts", "docs", "outputs", "plans")

foreach ($dir in $folders) {
    if (!(Test-Path "$dir/CLAUDE.md")) {
        Write-Host "❌ Missing: $dir/CLAUDE.md"
    } else {
        Write-Host "✓ Found: $dir/CLAUDE.md"
    }
}

# Check file headers
Get-ChildItem -Path . -Recurse -Filter "*.py" -Exclude "__pycache__" | ForEach-Object {
    $content = Get-Content $_.FullName -TotalCount 20
    if ($content -notmatch "# INPUT:") {
        Write-Host "❌ Missing header: $($_.FullName)"
    }
}
```
```

---

### Phase 2: 创建所有文件夹的CLAUDE.md (12个文件)

按照以下顺序创建，使用统一模板：

**核心代码模块 (10个):**
1. `agents/CLAUDE.md`
2. `agents/services/CLAUDE.md`
3. `agents/utils/CLAUDE.md`
4. `config/CLAUDE.md`
5. `core/CLAUDE.md`
6. `tools/CLAUDE.md`
7. `scheduler/CLAUDE.md`
8. `tests/CLAUDE.md`
9. `scripts/CLAUDE.md`
10. `docs/CLAUDE.md`

**输出和计划目录 (2个):**
11. `outputs/CLAUDE.md`
12. `plans/CLAUDE.md`

**注意**: `data/` 及其所有子目录不创建CLAUDE.md（数据存储目录，非代码模块）

**文件夹CLAUDE.md模板:**

```markdown
# [文件夹名称] - [简要描述]

**一旦此文件夹有变化，请更新本文件**

## 三行架构说明

1. **职责**: [此文件夹的主要职责]
2. **依赖**: [依赖的外部模块]
3. **输出**: [对外提供的接口/类/函数]

## 文件清单

### [文件名1.py]
- **角色**: [在系统中的角色]
- **功能**: [核心功能描述]

### [文件名2.py]
- **角色**: [在系统中的角色]
- **功能**: [核心功能描述]

[... 列出所有文件 ...]

## 更新历史

- 2026-02-27: 创建此文档，记录当前架构
```

---

### Phase 3: 为所有Python文件添加头注释 (60个文件)

**实施顺序（按依赖关系）:**

**第1批 - 核心基础 (3个):**
- `core/state.py` - 状态定义（所有模块都依赖）
- `config/llm_config.py` - LLM配置（所有Agent都依赖）
- `agents/base_agent.py` - Agent基类（所有Agent继承）

**第2批 - 服务和工具 (10个):**
- `agents/services/llm_service.py`
- `agents/services/intelligence_context.py`
- `agents/services/output_manager.py`
- `agents/utils/json_parser.py`
- `agents/utils/prompt_builder.py`
- `tools/paper_fetcher.py`
- `tools/data_fetcher.py`
- `tools/backtest_engine.py`
- `tools/file_manager.py`
- `core/pipeline.py`

**第3批 - 四个Agent (4个):**
- `agents/ideation_agent.py`
- `agents/planning_agent.py`
- `agents/experiment_agent.py`
- `agents/writing_agent.py`

**第4批 - 剩余核心模块 (15个):**
- `core/agent_memory_manager.py`
- `core/knowledge_graph.py`
- `core/database.py`
- `core/agent_persona.py`
- `core/self_reflection.py`
- `core/iteration_memory.py`
- `core/document_memory_manager.py`
- `core/document_tracker.py`
- `core/database_extensions.py`
- `core/persistence.py`
- `core/logging_config.py`
- `config/auth_config.py`
- `config/agent_config.py`
- `config/multi_llm_config.py`
- `config/llm_config_oauth.py`

**第5批 - 其他模块 (28个):**
- 所有 `tools/` 下的其他文件
- 所有 `scheduler/` 下的文件
- 所有 `tests/` 下的文件
- 所有 `scripts/` 下的文件
- 所有 `config/` 下的其他文件
- 所有 `__init__.py` 文件

**文件头注释模板 (中文):**

```python
"""
[保留现有的英文 docstring]
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - [列出关键import和它们提供的功能]
# OUTPUT: 对外提供 - [列出导出的类/函数及其用途]
# POSITION: 系统地位 - [Core/Agent/Tool/Config/Support] - [在架构中的定位]
#
# 注意：当本文件更新时，必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

[现有的import语句和代码...]
```

**示例 - core/state.py 的文件头:**

```python
"""
State management for the research automation system.

Defines the ResearchState TypedDict that flows through the entire pipeline.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - typing (TypedDict, List, Dict), dataclasses (dataclass), datetime
# OUTPUT: 对外提供 - ResearchState, PaperMetadata, ExperimentPlan, BacktestResults,
#                   RankedPaper, StructuredInsights, DeepInsights, ResearchGap,
#                   Hypothesis, ResearchSynthesis, create_initial_state()
# POSITION: 系统地位 - Core/State (核心层-状态定义)
#                     整个系统的数据契约，所有Agent和Pipeline的状态流转基础
#
# 注意：当本文件更新时，必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import TypedDict, List, Dict, Optional, Literal, Any
from dataclasses import dataclass, field
from datetime import datetime
```

**示例 - agents/base_agent.py 的文件头:**

```python
"""
BaseAgent - Foundation class for all research agents

Implements Template Method Pattern to eliminate code duplication across agents.
All agents inherit from this class and implement only their specific business logic.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - core/state (ResearchState), config/agent_config (Agent配置),
#                   agents/services (LLMService, IntelligenceContext, OutputManager),
#                   abc (抽象基类), logging (日志系统)
# OUTPUT: 对外提供 - BaseAgent抽象基类，定义execute()生命周期、call_llm()、
#                   save_artifact()等通用方法，子类只需实现_execute()
# POSITION: 系统地位 - Agent/Base (智能体层-抽象基类)
#                     Template Method Pattern核心实现，消除四个Agent的重复代码
#
# 注意：当本文件更新时，必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from pathlib import Path
```

**示例 - tools/paper_fetcher.py 的文件头:**

```python
"""
Paper fetching utilities for arXiv and other academic sources.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - arxiv SDK (论文搜索), requests (HTTP请求),
#                   core/state (PaperMetadata数据结构),
#                   config/data_sources (ARXIV_CONFIG配置)
# OUTPUT: 对外提供 - PaperFetcher类，提供fetch_recent_papers()、
#                   fetch_by_id()、search_papers()、filter_papers_by_relevance()
# POSITION: 系统地位 - Tool/Fetcher (工具层-数据获取)
#                     IdeationAgent的核心依赖，负责文献数据源对接
#
# 注意：当本文件更新时，必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import arxiv
import requests
from typing import List, Optional, Dict, Any
```

---

## Critical Files (关键文件路径)

执行时需要修改或创建的关键文件：

### 需要更新的现有文件 (1个):
- `F:\shuxu\report_reproduce\CLAUDE.md` - 追加全局架构地图和回环检查规则

### 需要创建的文件夹CLAUDE.md (12个):
- `F:\shuxu\report_reproduce\agents\CLAUDE.md`
- `F:\shuxu\report_reproduce\agents\services\CLAUDE.md`
- `F:\shuxu\report_reproduce\agents\utils\CLAUDE.md`
- `F:\shuxu\report_reproduce\config\CLAUDE.md`
- `F:\shuxu\report_reproduce\core\CLAUDE.md`
- `F:\shuxu\report_reproduce\tools\CLAUDE.md`
- `F:\shuxu\report_reproduce\scheduler\CLAUDE.md`
- `F:\shuxu\report_reproduce\tests\CLAUDE.md`
- `F:\shuxu\report_reproduce\scripts\CLAUDE.md`
- `F:\shuxu\report_reproduce\docs\CLAUDE.md`
- `F:\shuxu\report_reproduce\outputs\CLAUDE.md`
- `F:\shuxu\report_reproduce\plans\CLAUDE.md`

### 需要添加文件头的Python文件 (60个):

**核心基础 (3个):**
- `F:\shuxu\report_reproduce\core\state.py`
- `F:\shuxu\report_reproduce\config\llm_config.py`
- `F:\shuxu\report_reproduce\agents\base_agent.py`

**服务和工具 (10个):**
- `F:\shuxu\report_reproduce\agents\services\llm_service.py`
- `F:\shuxu\report_reproduce\agents\services\intelligence_context.py`
- `F:\shuxu\report_reproduce\agents\services\output_manager.py`
- `F:\shuxu\report_reproduce\agents\utils\json_parser.py`
- `F:\shuxu\report_reproduce\agents\utils\prompt_builder.py`
- `F:\shuxu\report_reproduce\tools\paper_fetcher.py`
- `F:\shuxu\report_reproduce\tools\data_fetcher.py`
- `F:\shuxu\report_reproduce\tools\backtest_engine.py`
- `F:\shuxu\report_reproduce\tools\file_manager.py`
- `F:\shuxu\report_reproduce\core\pipeline.py`

**四个Agent (4个):**
- `F:\shuxu\report_reproduce\agents\ideation_agent.py`
- `F:\shuxu\report_reproduce\agents\planning_agent.py`
- `F:\shuxu\report_reproduce\agents\experiment_agent.py`
- `F:\shuxu\report_reproduce\agents\writing_agent.py`

**剩余核心模块 (15个):**
- `F:\shuxu\report_reproduce\core\agent_memory_manager.py`
- `F:\shuxu\report_reproduce\core\knowledge_graph.py`
- `F:\shuxu\report_reproduce\core\database.py`
- `F:\shuxu\report_reproduce\core\agent_persona.py`
- `F:\shuxu\report_reproduce\core\self_reflection.py`
- `F:\shuxu\report_reproduce\core\iteration_memory.py`
- `F:\shuxu\report_reproduce\core\document_memory_manager.py`
- `F:\shuxu\report_reproduce\core\document_tracker.py`
- `F:\shuxu\report_reproduce\core\database_extensions.py`
- `F:\shuxu\report_reproduce\core\persistence.py`
- `F:\shuxu\report_reproduce\core\logging_config.py`
- `F:\shuxu\report_reproduce\config\auth_config.py`
- `F:\shuxu\report_reproduce\config\agent_config.py`
- `F:\shuxu\report_reproduce\config\multi_llm_config.py`
- `F:\shuxu\report_reproduce\config\llm_config_oauth.py`

**其他模块 (28个):**
- 所有tools/下的其他文件 (5个): `pdf_reader.py`, `domain_classifier.py`, `citation_manager.py`, `smart_literature_access.py`, `data_sources.py`
- 所有scheduler/下的文件 (2个): `daily_scan.py`, `pipeline_runner.py`
- 所有tests/下的文件 (7个): `test_agents.py`, `test_base_agent.py`, `test_agent_memory_manager.py`, `test_document_memory.py`, `test_domain_classifier.py`, `test_pipeline.py`, `test_tools.py`
- 所有scripts/下的文件 (6个): `setup_oauth.py`, `test_auth.py`, `initialize_domains.py`, `initialize_agent_memories.py`, `classify_existing_papers.py`, `migrate_database_v2.py`
- 所有__init__.py文件 (8个): `agents/__init__.py`, `agents/services/__init__.py`, `agents/utils/__init__.py`, `config/__init__.py`, `core/__init__.py`, `tools/__init__.py`, `scheduler/__init__.py`, `tests/__init__.py`

---

## Verification (验证步骤)

### 自动化检查脚本

**Windows PowerShell版本:**

```powershell
# Save as verify-documentation.ps1

Write-Host "=== Documentation System Verification ===" -ForegroundColor Cyan
Write-Host ""

# Check 1: All folders have CLAUDE.md
Write-Host "[Check 1] Verifying folder CLAUDE.md files..." -ForegroundColor Yellow
$folders = @("agents", "agents/services", "agents/utils", "config", "core", "tools",
             "scheduler", "tests", "scripts", "docs", "outputs", "plans")

$missing_folder_docs = 0
foreach ($dir in $folders) {
    if (!(Test-Path "$dir/CLAUDE.md")) {
        Write-Host "  ❌ Missing: $dir/CLAUDE.md" -ForegroundColor Red
        $missing_folder_docs++
    }
}

if ($missing_folder_docs -eq 0) {
    Write-Host "  ✓ All $($folders.Count) folders have CLAUDE.md" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Missing $missing_folder_docs folder CLAUDE.md files" -ForegroundColor Red
}
Write-Host ""

# Check 2: All Python files have headers
Write-Host "[Check 2] Verifying Python file headers..." -ForegroundColor Yellow
$py_files = Get-ChildItem -Path . -Recurse -Filter "*.py" -Exclude "__pycache__" |
            Where-Object { $_.FullName -notmatch "\\.git|\\.venv|\\.pytest_cache" }

$missing_headers = 0
foreach ($file in $py_files) {
    $content = Get-Content $file.FullName -TotalCount 25 -ErrorAction SilentlyContinue
    if ($content -notmatch "# INPUT:") {
        Write-Host "  ❌ Missing header: $($file.FullName)" -ForegroundColor Red
        $missing_headers++
    }
}

if ($missing_headers -eq 0) {
    Write-Host "  ✓ All $($py_files.Count) Python files have headers" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Missing $missing_headers file headers" -ForegroundColor Red
}
Write-Host ""

# Check 3: Root CLAUDE.md has required sections
Write-Host "[Check 3] Verifying root CLAUDE.md sections..." -ForegroundColor Yellow
$root_content = Get-Content "CLAUDE.md" -Raw
$has_arch_map = $root_content -match "全局架构地图"
$has_loop_rules = $root_content -match "强制回环检查规则"

if ($has_arch_map -and $has_loop_rules) {
    Write-Host "  ✓ Root CLAUDE.md has all required sections" -ForegroundColor Green
} else {
    if (!$has_arch_map) {
        Write-Host "  ❌ Missing: 全局架构地图 section" -ForegroundColor Red
    }
    if (!$has_loop_rules) {
        Write-Host "  ❌ Missing: 强制回环检查规则 section" -ForegroundColor Red
    }
}
Write-Host ""

# Summary
Write-Host "=== Verification Summary ===" -ForegroundColor Cyan
Write-Host "Total folders checked: $($folders.Count)"
Write-Host "Total Python files checked: $($py_files.Count)"
Write-Host "Missing folder docs: $missing_folder_docs"
Write-Host "Missing file headers: $missing_headers"
Write-Host ""

if ($missing_folder_docs -eq 0 -and $missing_headers -eq 0 -and $has_arch_map -and $has_loop_rules) {
    Write-Host "✓ All documentation checks passed!" -ForegroundColor Green
} else {
    Write-Host "⚠ Some documentation checks failed. Please review above." -ForegroundColor Yellow
}
```

### 手动检查清单

执行完成后，手动验证以下内容：

- [ ] 根CLAUDE.md已添加全局架构地图
- [ ] 根CLAUDE.md已添加强制回环检查规则
- [ ] 根CLAUDE.md已添加文档维护工具脚本
- [ ] 所有12个核心代码文件夹都有CLAUDE.md
- [ ] 所有60个Python文件都有中文文件头注释
- [ ] 文件头注释格式正确 (INPUT/OUTPUT/POSITION)
- [ ] 每个文件夹CLAUDE.md都列出了该文件夹下的所有文件
- [ ] 架构说明准确反映了模块职责和依赖关系
- [ ] 运行验证脚本 `verify-documentation.ps1` 全部通过

### 端到端测试

完成文档系统后，进行以下测试：

1. **可读性测试**: 随机选择5个文件，通过文件头注释快速理解其职责
2. **导航测试**: 从根CLAUDE.md开始，能否在30秒内找到任意功能的实现文件
3. **一致性测试**: 选择一个模块，验证文件头注释、文件夹CLAUDE.md、根CLAUDE.md三级描述一致
4. **更新测试**: 模拟修改一个文件，验证回环检查流程是否清晰

---

## Success Criteria (成功标准)

- ✅ 12个核心代码文件夹全部拥有CLAUDE.md文档
- ✅ 60个Python文件全部拥有中文文件头注释
- ✅ 根CLAUDE.md包含完整的全局架构地图
- ✅ 根CLAUDE.md包含强制回环检查规则
- ✅ 所有文档验证脚本运行通过
- ✅ 三级文档内容一致性100%
- ✅ 任意文件可在30秒内通过文档定位
- ✅ 回环检查流程清晰可执行

---

## Notes (注意事项)

1. **保留现有docstring**: 所有文件的英文docstring必须保留，中文文件头注释添加在docstring之后
2. **中文注释规范**: 文件头注释必须使用中文，格式严格按照模板
3. **更新历史**: 每个CLAUDE.md的"更新历史"部分记录创建日期为2026-02-27
4. **__init__.py处理**: 对于__init__.py文件，如果内容为空或仅有导入，头注释可以简化
5. **数据目录**: data/及其所有子目录不创建CLAUDE.md（这些是数据存储目录，非代码模块）
6. **Git提交**: 建议分阶段提交 - Phase 1单独提交，Phase 2按模块提交，Phase 3分批提交
