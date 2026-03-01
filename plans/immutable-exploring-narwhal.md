# FARS 项目 10 项问题修复计划

## Context

项目全面审计发现 10 个问题：5 个正确性问题（指标计算错误、prompt/state 字段不匹配）和 5 个架构问题（死代码、重复代码、安全性）。这些问题导致流水线即使跑通也会产出不可信结果，且存在代码重复和安全隐患。本计划按依赖顺序分 4 批修复。

---

## 批次 1：简单修复（无依赖）

### Issue 3：PlanningAgent 引用不存在的上游文件

**文件**: `agents/planning/prompts.py`

IdeationAgent 实际输出: `papers_analyzed.json`, `research_synthesis.json`, `literature_summary.md`, `research_gaps.json`, `hypothesis.md`

- **Line 24**: `structured_insights.json` → `papers_analyzed.json`
- **Line 74**: `literature/structured_insights.json — Deep paper analyses` → `literature/papers_analyzed.json — Papers reviewed with metadata`

### Issue 4：WritingAgent prompt 声称有 `run_python` 但实际未注册

**文件**: `agents/writing/prompts.py`

- **Line 14**: 删除 `, run Python for visualizations`
- **Line 19**: 删除 `- **run_python**: Run Python scripts for generating charts and visualizations`
- **Line 38**: `3. Optionally generate visualizations using Python` → `3. Optionally browse the web for supplementary references`

**文档更新**:
- `agents/writing/CLAUDE.md`: 工具数 6→5，架构模式中删除 `run_python`
- `agents/writing/prompts.py` 文件头 OUTPUT: 不需变（仍是模板和函数）

### Issue 5：`state["error"]` 字段不存在于 ResearchState

**文件**: `agents/base_agent.py`

- **Line 89**: `state["error"] = str(e)` → `state["error_log"] = str(e)`

（ResearchState 有 `error_log: Optional[str]` 在 `core/state.py:219`）

---

## 批次 2：指标计算修复

### Issue 1：Sortino ratio 双重年化

**文件**: `agents/experiment/metrics.py`

当前代码（Line 34-35）:
```python
sortino_downside = returns[returns < 0].std() * np.sqrt(252)  # 已年化
sortino = (returns.mean() / sortino_downside * np.sqrt(252))   # 又乘 sqrt(252)
```

**修复**: 移除 Line 34 的 `* np.sqrt(252)`，保持与 Sharpe 计算模式一致:
```python
sortino_downside = returns[returns < 0].std()
sortino = (returns.mean() / sortino_downside * np.sqrt(252)) if sortino_downside > 0 else 0.0
```

### Issue 2：BacktestEngine 假指标

**文件**: `tools/backtest_engine.py`

三处硬编码（Line 187-197）:
- `years = 1` → 从 TimeReturn analyzer 获取实际天数
- `sortino_ratio = sharpe_ratio * 1.2` → 从日收益率计算
- `volatility = 0.15` → 从日收益率计算

**修复方案**:

步骤 1: `run_backtest()` 方法中添加 TimeReturn analyzer 命名（Line 105 附近）:
```python
cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn', timeframe=bt.TimeFrame.Days)
```

步骤 2: `_extract_metrics()` 中提取日收益率序列（Line 134 之后）:
```python
import pandas as pd

try:
    timereturn = strategy.analyzers.timereturn.get_analysis()
    daily_returns = pd.Series(timereturn) if timereturn else None
except (AttributeError, KeyError):
    daily_returns = None
```

步骤 3: 替换 Line 186-197 的硬编码计算:
```python
if daily_returns is not None and len(daily_returns) > 1:
    years = len(daily_returns) / 252
    cagr = ((1 + total_return) ** (1 / max(years, 1/252)) - 1) if years > 0 else 0
    volatility = float(daily_returns.std() * np.sqrt(252))
    downside = daily_returns[daily_returns < 0]
    if len(downside) > 0 and downside.std() > 0:
        sortino_ratio = float(daily_returns.mean() / downside.std() * np.sqrt(252))
    else:
        sortino_ratio = 0.0
else:
    years = 1
    cagr = total_return
    volatility = 0.0
    sortino_ratio = 0.0

calmar_ratio = cagr / abs(max_drawdown) if max_drawdown != 0 else 0
```

需在文件顶部添加 `import pandas as pd` 和 `import numpy as np`（如未导入）。

**文档更新**: `tools/CLAUDE.md` backtest_engine 描述补充 "从日收益率计算真实指标"

---

## 批次 3：架构优化

### Issue 7：提取通用工具执行器到 `agents/common_tools.py`

**重复代码确认**:
- `_exec_browse_webpage`: ideation/tools.py:267, planning/tools.py:179, experiment/tools.py:222, writing/tools.py:197 — **100% 相同**
- `_exec_google_search`: ideation/tools.py:274, planning/tools.py:186, experiment/tools.py:229, writing/tools.py:204 — **100% 相同**
- `_exec_search_knowledge_graph`: ideation/tools.py:252, planning/tools.py:164 — **100% 相同**
- `_exec_read_upstream_file`: planning/tools.py:144, writing/tools.py:154 — **100% 相同**

**新建文件**: `agents/common_tools.py`

内容:
1. 4 个 schema dict: `BROWSE_WEBPAGE_SCHEMA`, `GOOGLE_SEARCH_SCHEMA`, `SEARCH_KNOWLEDGE_GRAPH_SCHEMA`, `READ_UPSTREAM_FILE_SCHEMA`
2. 4 个 executor 函数（从现有代码原样提取，保持签名 `(tool_input: dict, **context) -> str`）
3. `get_common_tools(include_browser, include_kg, include_file)` 返回 `list[tuple]` 供 `ToolRegistry.register_many()`

**修改 4 个 Agent 的 tools.py**:

| Agent | 删除的重复代码 | 导入方式 |
|-------|-------------|---------|
| ideation/tools.py | browse_webpage, google_search, search_kg 的 schema+executor | `get_common_tools(include_browser=True, include_kg=True, include_file=False)` |
| planning/tools.py | browse_webpage, google_search, search_kg, read_upstream 的 schema+executor | `get_common_tools(include_browser=True, include_kg=True, include_file=True)` |
| experiment/tools.py | browse_webpage, google_search 的 schema+executor | `get_common_tools(include_browser=True, include_kg=False, include_file=False)` |
| writing/tools.py | browse_webpage, google_search, read_upstream 的 schema+executor | `get_common_tools(include_browser=True, include_kg=False, include_file=True)` |

每个 `get_tool_definitions()` 函数中: `tools.extend(get_common_tools(...))`

**文档更新**:
- `agents/CLAUDE.md`: 添加 `common_tools.py` 条目
- 4 个子包 CLAUDE.md: 更新工具说明 "通用工具从 common_tools.py 导入"

### Issue 6：删除未使用的 LLM 配置文件

**确认死代码**: `config/__init__.py` 仅导入 `llm_config.py`；`multi_llm_config.py` 和 `llm_config_oauth.py` 无实际代码导入。

**删除文件**:
- `config/multi_llm_config.py`
- `config/llm_config_oauth.py`
- `config/auth_config.py`
- `scripts/setup_oauth.py`
- `scripts/test_auth.py`

**文档更新**:
- `config/CLAUDE.md`: 移除 3 个文件条目，添加"已删除文件"段

---

## 批次 4：清理和增强

### Issue 8：清理未使用的 core/ 模块

**确认死代码** (grep 结果):
- `core/iteration_memory.py` — 仅在 docs/ 中提及
- `core/document_tracker.py` — 仅在 docs/ 中提及
- `core/logging_config.py` — 仅在 docs/ 中提及
- `core/document_memory_manager.py` — 被 `tests/test_document_memory.py` 和 `scripts/initialize_domains.py` 使用，但模块本身有多处运行时必崩 bug
- `core/database_extensions.py` — 仅被 `document_memory_manager.py` 和 `scripts/initialize_domains.py` 使用

**删除文件**:
- `core/iteration_memory.py`
- `core/document_tracker.py`
- `core/logging_config.py`
- `core/document_memory_manager.py`
- `core/database_extensions.py`
- `tests/test_document_memory.py`（依赖已删除模块）
- `scripts/initialize_domains.py`（依赖已删除模块）
- `scripts/classify_existing_papers.py`（依赖 domain_classifier，而 domain_classifier 依赖 database_extensions）
- `scripts/migrate_database_v2.py`（创建已删除模块的表）

**修改文件**:
- `agents/ideation/agent.py` Line 10: 删除注释 `#         core.document_memory_manager,`

**文档更新**:
- `core/CLAUDE.md`: 移除 5 个文件条目，添加"已删除文件"段
- `core/__init__.py`: 无需改（不导入这些模块）

### Issue 9：添加 token 使用跟踪

**文件**: `agents/base_agent.py` 的 `_agentic_loop()` 方法

**修改**:
1. 循环前初始化计数器:
```python
total_input_tokens = 0
total_output_tokens = 0
```

2. 每次 `call_llm_tools()` 返回后（Line ~168 后）:
```python
if hasattr(response, 'usage'):
    total_input_tokens += response.usage.input_tokens
    total_output_tokens += response.usage.output_tokens
    self.logger.info(
        f"Turn {turn} tokens: in={response.usage.input_tokens}, "
        f"out={response.usage.output_tokens}"
    )
```

3. 循环结束后记录总计:
```python
self.logger.info(
    f"Token summary: input={total_input_tokens}, "
    f"output={total_output_tokens}, "
    f"total={total_input_tokens + total_output_tokens}"
)
execution_log += (
    f"\n[TOKEN SUMMARY] input={total_input_tokens}, "
    f"output={total_output_tokens}, "
    f"total={total_input_tokens + total_output_tokens}"
)
```

**不修改 ResearchState**（保持简单，日志已足够可观测）。

### Issue 10：加强沙箱安全

**文件**: `agents/experiment/sandbox.py`

**修改 `run_command()` 方法（Line 74-111）**:

1. 添加 `import shlex` 到文件顶部
2. 增强黑名单（Line 24-28），添加: `"sudo"`, `"chmod 777"`, `"wget"`, `"curl"`, `"nc -l"`, `"netcat"`
3. 添加 shell 元字符检测:
```python
SHELL_METACHARACTERS = [';', '|', '&&', '||', '$(' , '`', '>>', '>', '<']
for meta in SHELL_METACHARACTERS:
    if meta in command:
        return {"stdout": "", "stderr": f"Blocked: shell metacharacter '{meta}' not allowed", "returncode": -1}
```
4. 改用 `shell=False` + `shlex.split()`:
```python
try:
    cmd_parts = shlex.split(command, posix=(os.name != 'nt'))
except ValueError as e:
    return {"stdout": "", "stderr": f"Invalid command: {e}", "returncode": -1}

result = subprocess.run(
    cmd_parts,
    shell=False,
    cwd=str(self.workdir),
    capture_output=True,
    text=True,
    timeout=timeout,
)
```
5. 添加 `import os` 到文件顶部
6. 添加 `FileNotFoundError` 异常处理

**文档更新**: `agents/experiment/CLAUDE.md` sandbox.py 描述添加 "shell=False 安全执行, 元字符检测"

---

## 关键文件清单

| 文件 | 操作 | Issues |
|------|------|--------|
| `agents/experiment/metrics.py` | 修改 | #1 |
| `tools/backtest_engine.py` | 修改 | #2 |
| `agents/planning/prompts.py` | 修改 | #3 |
| `agents/writing/prompts.py` | 修改 | #4 |
| `agents/base_agent.py` | 修改 | #5, #9 |
| `agents/common_tools.py` | **新建** | #7 |
| `agents/ideation/tools.py` | 修改 | #7 |
| `agents/planning/tools.py` | 修改 | #7 |
| `agents/experiment/tools.py` | 修改 | #7 |
| `agents/writing/tools.py` | 修改 | #7 |
| `agents/experiment/sandbox.py` | 修改 | #10 |
| `agents/ideation/agent.py` | 修改 | #8 (删注释) |
| `config/multi_llm_config.py` | **删除** | #6 |
| `config/llm_config_oauth.py` | **删除** | #6 |
| `config/auth_config.py` | **删除** | #6 |
| `scripts/setup_oauth.py` | **删除** | #6 |
| `scripts/test_auth.py` | **删除** | #6 |
| `core/iteration_memory.py` | **删除** | #8 |
| `core/document_tracker.py` | **删除** | #8 |
| `core/logging_config.py` | **删除** | #8 |
| `core/document_memory_manager.py` | **删除** | #8 |
| `core/database_extensions.py` | **删除** | #8 |
| `tests/test_document_memory.py` | **删除** | #8 |
| `scripts/initialize_domains.py` | **删除** | #8 |
| `scripts/classify_existing_papers.py` | **删除** | #8 |
| `scripts/migrate_database_v2.py` | **删除** | #8 |

**文档更新文件**: `agents/CLAUDE.md`, `agents/writing/CLAUDE.md`, `agents/experiment/CLAUDE.md`, `config/CLAUDE.md`, `core/CLAUDE.md`, `tools/CLAUDE.md`, 根 `CLAUDE.md` (模块清单无变化但工具描述可能需微调)

---

## 验证

1. **语法检查**: `python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in ['agents/base_agent.py', 'agents/common_tools.py', 'agents/experiment/metrics.py', 'tools/backtest_engine.py', 'agents/experiment/sandbox.py']]"`
2. **导入检查**: `python -c "from agents import *; from config import *; from core import *"`
3. **Sortino 验证**: metrics.py 的 Sortino 应 ≈ Sharpe（同量级），不再差 15x
4. **Sandbox 安全测试**: `sandbox.run_command("ls; whoami")` 应返回 blocked
5. **Token 日志**: 运行任意 Agent，日志中应出现 `Turn X tokens:` 行
