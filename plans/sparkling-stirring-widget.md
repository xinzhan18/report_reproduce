# ExperimentAgent 升级：Agentic Tool-Use 自治执行引擎

## Context

当前 ExperimentAgent 是"生成一整段代码 → exec() 一次执行 → 看结果"的模式，太脆弱：
- LLM 必须一次生成完美代码，无法调试
- 无法安装缺失依赖
- 无法读取中间结果来决策下一步
- 无法拆分多文件项目

**目标**：升级为 **Agentic Tool-Use 循环**——LLM 像 Claude Code 一样，拥有 Bash、文件读写、Python 执行、依赖安装等工具，自主迭代完成实验。

**核心改动**：用 Anthropic tool_use API 实现多轮循环，LLM 每轮决定调用哪些工具，看到结果后决定下一步。

---

## 模块结构

```
agents/experiment_agent.py  → 删除（单文件）

agents/experiment/           ← 新建子包
  __init__.py               # 导出 ExperimentAgent
  agent.py                  # ExperimentAgent 主类（继承 BaseAgent + agentic loop）
  sandbox.py                # SandboxManager: 工作目录隔离 + 进程执行
  tools.py                  # 6 个 Tool schema + execute_tool dispatch
  prompts.py                # system prompt + task prompt 模板
  metrics.py                # compute_metrics() 辅助函数（迁移）
  CLAUDE.md                 # 模块文档
```

---

## 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `agents/experiment/agent.py` | **新建** | ExperimentAgent 主类 + _agentic_loop |
| `agents/experiment/sandbox.py` | **新建** | SandboxManager |
| `agents/experiment/tools.py` | **新建** | Tool schema + dispatch |
| `agents/experiment/prompts.py` | **新建** | Prompt 模板 |
| `agents/experiment/metrics.py` | **新建** | compute_metrics 迁移 |
| `agents/experiment/__init__.py` | **新建** | 导出 |
| `agents/experiment/CLAUDE.md` | **新建** | 模块文档 |
| `agents/experiment_agent.py` | **删除** | 被子包替代 |
| `agents/__init__.py` | **小改** | import 路径改为 `.experiment` |
| `config/agent_config.py` | **小改** | 增加 max_agent_turns/sandbox_timeout 配置 |
| `agents/CLAUDE.md` | **小改** | 更新描述 |
| 根 `CLAUDE.md` | **小改** | 更新描述 |

**不改**：`core/pipeline.py`、`core/state.py`、`agents/base_agent.py`、`agents/writing_agent.py`、`market_data/*`

---

## 核心设计

### 1. Agentic Loop（`agent.py` 核心流程）

```
_execute(state)
  │
  ├─ Step 1: 数据准备
  │    └─ data_fetcher.fetch(data_config) → dict[str, DataFrame]
  │
  ├─ Step 2: 创建 Sandbox
  │    ├─ SandboxManager.create(experiment_id)
  │    ├─ inject_data(data_dict)     → 写 CSV 到 sandbox/data/
  │    └─ inject_helpers()           → 写 compute_metrics.py
  │
  ├─ Step 3: Agentic Tool-Use 循环
  │    │
  │    │  messages = [user: task_prompt]
  │    │
  │    │  FOR turn = 1 TO MAX_TURNS (30):
  │    │    response = llm.messages.create(
  │    │      model, system=system_prompt, tools=ALL_TOOLS, messages
  │    │    )
  │    │    messages.append(assistant: response.content)
  │    │
  │    │    IF stop_reason == "end_turn": BREAK
  │    │    IF stop_reason == "tool_use":
  │    │      FOR EACH tool_use block:
  │    │        IF name == "submit_result":
  │    │          → 保存结果, BREAK
  │    │        ELSE:
  │    │          → execute_tool(name, input, sandbox)
  │    │      messages.append(user: tool_results)
  │    │
  │    └─ 返回 (submitted_results, execution_log)
  │
  ├─ Step 4: 结果映射
  │    ├─ _analyze_results() → LLM 评估质量
  │    └─ _map_to_backtest_results() → BacktestResults
  │
  └─ Step 5: 保存 + KG 更新
```

### 2. 六个工具定义（`tools.py`）

| 工具 | 用途 | input_schema |
|------|------|-------------|
| `bash` | 执行 shell 命令（pip install、ls、数据处理等） | `{command: str}` |
| `write_file` | 写文件到 sandbox | `{path: str, content: str}` |
| `read_file` | 读 sandbox 中的文件 | `{path: str}` |
| `delete_file` | 删除 sandbox 中的文件 | `{path: str}` |
| `run_python` | 运行 Python 脚本（subprocess） | `{script_path: str}` |
| `submit_result` | 提交最终结果（**结束循环**） | `{results: {metrics: {...}, description: str}}` |

每个 tool 是一个 Anthropic API 格式的 dict（name + description + input_schema）。`execute_tool()` 函数统一分发。

### 3. SandboxManager（`sandbox.py`）

```python
class SandboxManager:
    def create(experiment_id) → Path        # 创建隔离工作目录
    def inject_data(data_dict)              # DataFrame → CSV 文件 + manifest
    def inject_helpers()                    # 写 compute_metrics.py
    def run_command(command) → {stdout, stderr, returncode}
    def run_python(script_path) → {stdout, stderr, returncode}
    def read_file(path) → str
    def write_file(path, content)
    def delete_file(path)
```

**安全机制**：
- **路径隔离**：`_resolve_path()` 禁止逃逸 workdir
- **命令黑名单**：禁止 `rm -rf /`、`shutdown`、`mkfs` 等
- **进程超时**：`subprocess.run(timeout=300)`
- **输出截断**：stdout/stderr 各截断 10000/5000 chars
- **轮次限制**：MAX_TURNS=30 防止无限循环

### 4. 数据注入方式

不再用 exec namespace 注入，改为文件系统：

```
sandbox/
  data/
    SPY.csv                 # DataFrame.to_csv()
    AAPL.csv
  data_manifest.json        # {"SPY": "data/SPY.csv", ...}
  compute_metrics.py        # 辅助函数源码
```

LLM 在 system prompt 中被告知：
- `pd.read_csv("data/SPY.csv", index_col=0, parse_dates=True)` 加载数据
- `from compute_metrics import compute_metrics` 导入辅助函数

### 5. Prompt 设计（`prompts.py`）

**System Prompt** 核心要素：
- 角色：量化金融研究员 + Python 程序员
- 工具说明：6 个工具的用途
- 工作流程：读 manifest → 写代码 → 运行 → 调试 → submit
- 数据格式：CSV 列名 open/high/low/close/volume
- compute_metrics 用法
- submit_result 格式
- 规则：缺包就 pip install、有错就 debug、必须 submit_result

**Task Prompt** 注入：hypothesis、methodology、implementation_steps、success_criteria、data_info

### 6. 与现有系统的集成

- **BaseAgent**：继承不变，`_execute(state)` 接口完全兼容
- **Pipeline**：`ExperimentAgent(llm, file_manager, data_fetcher)` 构造签名不变
- **State**：输出字段 `experiment_code/execution_logs/results_data/validation_status` 不变
- **WritingAgent**：读取 `BacktestResults` 格式不变
- **agents/__init__.py**：`from .experiment_agent` → `from .experiment`

---

## 实施步骤

1. 创建 `agents/experiment/` 目录
2. 写 `metrics.py`（从原文件迁移 compute_metrics）
3. 写 `sandbox.py`（SandboxManager）
4. 写 `tools.py`（6 个 tool schema + execute_tool）
5. 写 `prompts.py`（system/task prompt 模板）
6. 写 `agent.py`（ExperimentAgent + _agentic_loop）
7. 写 `__init__.py`
8. 更新 `agents/__init__.py`（import 路径）
9. 更新 `config/agent_config.py`（新增配置项）
10. 删除 `agents/experiment_agent.py`
11. 写 `agents/experiment/CLAUDE.md`
12. 更新 `agents/CLAUDE.md`、根 `CLAUDE.md`

---

## 验证

1. `python -c "import ast; ast.parse(open('agents/experiment/agent.py', encoding='utf-8').read())"`（所有新文件）
2. `python -c "from agents.experiment import ExperimentAgent; print('OK')"`
3. `python -c "from agents import ExperimentAgent; print('OK')"`
4. AST 验证 ExperimentAgent 包含 `_execute`, `_agentic_loop`, `_map_to_backtest_results`, `_analyze_results`
5. 验证 SandboxManager 路径隔离（尝试逃逸路径）
6. 验证 tool schema 符合 Anthropic API 格式
7. `pipeline.py` 中 ExperimentAgent 的 import 和实例化无需修改

---

## Checklist

**新建 `agents/experiment/`**：
- [ ] `metrics.py` — compute_metrics 迁移
- [ ] `sandbox.py` — SandboxManager（create/inject_data/inject_helpers/run_command/run_python/read_file/write_file/delete_file）
- [ ] `tools.py` — 6 个 tool schema（bash/write_file/read_file/delete_file/run_python/submit_result）+ execute_tool dispatch
- [ ] `prompts.py` — SYSTEM_PROMPT_TEMPLATE + TASK_PROMPT_TEMPLATE
- [ ] `agent.py` — ExperimentAgent._execute + _agentic_loop + _map_to_backtest_results + _analyze_results + _describe_data + _collect_code_from_sandbox + _generate_execution_summary
- [ ] `__init__.py` — 导出 ExperimentAgent
- [ ] `CLAUDE.md` — 模块文档

**修改**：
- [ ] `agents/__init__.py` — `from .experiment import ExperimentAgent`
- [ ] `config/agent_config.py` — 增加 max_agent_turns / sandbox_timeout / sandbox_cleanup
- [ ] 删除 `agents/experiment_agent.py`

**文档**：
- [ ] `agents/CLAUDE.md` 更新
- [ ] 根 `CLAUDE.md` 更新
