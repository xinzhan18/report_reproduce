# 全 Agent Agentic Tool-Use 架构升级

## Context

当前 FARS 系统中，ExperimentAgent 已升级为 Agentic Tool-Use 模式（多轮 tool_use 循环），但其他 3 个 Agent 仍然是"单次 LLM 调用"模式：
- **IdeationAgent**: 7+ 次独立 LLM 调用，无法迭代修正文献排序/分析
- **PlanningAgent**: 3-6 次 LLM 调用（有简单迭代），但无法自主验证
- **WritingAgent**: 8 个报告节独立生成 + 1 次润色，无法跨节检查一致性

**目标**：将 Agentic Tool-Use 循环提升为 BaseAgent 通用能力，所有 4 个 Agent 都获得工具自治执行能力。同时集成 Playwright 浏览器、ToolRegistry 注册中心，建立工程化可维护的架构。

---

## 架构设计

### 核心模式

```
BaseAgent._agentic_loop()     ← 通用循环（新增到 base_agent.py）
  ↕ 调用
ToolRegistry                   ← 每个 Agent 实例持有一个（新建 tool_registry.py）
  ↕ 管理
工具集 = 通用工具 + Agent 专用工具
  ├─ bash, write_file, read_file      ← 沙箱工具 (已有 SandboxManager)
  ├─ search_papers, read_pdf           ← 论文工具 (包装 PaperFetcher/PDFReader)
  ├─ search_knowledge_graph            ← 知识图谱工具 (包装 KG)
  ├─ browse_webpage, google_search     ← 浏览器工具 (新建 BrowserManager)
  └─ submit_result                     ← 提交工具 (每个 Agent 不同 schema)
```

### 子类只需实现 4 个钩子

```python
class MyAgent(BaseAgent):
    def _register_tools(self, state):     # 注册工具到 self.tool_registry
    def _build_tool_system_prompt(self, state):  # 构建 system prompt
    def _build_task_prompt(self, state):   # 构建初始 user message
    def _on_submit_result(self, results, state):  # 映射结果到 state
```

---

## 文件结构

```
agents/
  base_agent.py               [修改] 新增 _agentic_loop, _register_tools, call_llm_tools
  llm.py                      [修改] 新增 call_llm_tools()
  tool_registry.py             [新建] ToolRegistry 类
  browser_manager.py           [新建] Playwright BrowserManager
  __init__.py                  [修改] 更新导入路径

  ideation/                    [新建] 从 ideation_agent.py 拆出
    __init__.py
    agent.py                   IdeationAgent 主类
    tools.py                   7 个工具 schema + executor
    prompts.py                 system/task prompt 模板

  planning/                    [新建] 从 planning_agent.py 拆出
    __init__.py
    agent.py                   PlanningAgent 主类
    tools.py                   5 个工具 schema + executor
    prompts.py                 system/task prompt 模板

  experiment/                  [修改] 适配 BaseAgent._agentic_loop
    agent.py                   删除内联 loop，用 base loop
    tools.py                   适配 ToolRegistry 格式
    sandbox.py                 不变
    prompts.py                 不变
    metrics.py                 不变

  writing/                     [新建] 从 writing_agent.py 拆出
    __init__.py
    agent.py                   WritingAgent 主类
    tools.py                   6 个工具 schema + executor
    prompts.py                 system/task prompt 模板

  ideation_agent.py            [删除]
  planning_agent.py            [删除]
  writing_agent.py             [删除]

core/
  pipeline.py                  [修改] 更新 import 路径

config/
  agent_config.py              [修改] 每个 Agent 增加 max_agent_turns/max_tokens
```

---

## 各 Agent 工具列表

### IdeationAgent (7 工具)

| 工具 | 描述 | 后端 |
|------|------|------|
| `search_papers` | 按关键词搜索 arXiv 论文 | PaperFetcher.fetch_papers_by_keywords |
| `fetch_recent_papers` | 获取最近论文 | PaperFetcher.fetch_recent_papers |
| `download_and_read_pdf` | 下载 PDF 并提取全文+分段 | PDFReader.download_pdf + extract_text + extract_sections |
| `search_knowledge_graph` | 查询知识图谱 | KnowledgeGraph.search_knowledge |
| `browse_webpage` | 浏览网页 | BrowserManager.browse |
| `google_search` | Google 搜索 | BrowserManager.search_google |
| `submit_result` | 提交：papers_reviewed, literature_summary, research_gaps, hypothesis | 特殊处理 |

### PlanningAgent (5 工具)

| 工具 | 描述 | 后端 |
|------|------|------|
| `read_upstream_file` | 读取上游产出文件 | FileManager.load_json/load_text |
| `search_knowledge_graph` | 查询知识图谱 | KnowledgeGraph.search_knowledge |
| `browse_webpage` | 浏览网页验证数据可用性 | BrowserManager.browse |
| `google_search` | Google 搜索方法论参考 | BrowserManager.search_google |
| `submit_result` | 提交：experiment_plan, methodology, expected_outcomes, data_config | 特殊处理 |

### ExperimentAgent (8 工具，在已有 6 个基础上加 2 个)

| 工具 | 描述 | 后端 |
|------|------|------|
| `bash` | 执行 shell 命令 | SandboxManager.run_command |
| `write_file` | 写文件到 sandbox | SandboxManager.write_file |
| `read_file` | 读取 sandbox 文件 | SandboxManager.read_file |
| `delete_file` | 删除 sandbox 文件 | SandboxManager.delete_file |
| `run_python` | 运行 Python 脚本 | SandboxManager.run_python |
| `browse_webpage` | 浏览网页查文档 | BrowserManager.browse |
| `google_search` | Google 搜索调试信息 | BrowserManager.search_google |
| `submit_result` | 提交：metrics + description | 特殊处理 |

### WritingAgent (6 工具)

| 工具 | 描述 | 后端 |
|------|------|------|
| `read_upstream_file` | 读取所有上游产出 | FileManager.load_json/load_text |
| `write_section` | 写入报告节到文件 | FileManager.save_text |
| `run_python` | 运行可视化脚本生成图表 | SandboxManager.run_python |
| `browse_webpage` | 浏览网页补充信息 | BrowserManager.browse |
| `google_search` | Google 搜索参考资料 | BrowserManager.search_google |
| `submit_result` | 提交：report_draft, final_report | 特殊处理 |

---

## 核心代码接口

### ToolRegistry (agents/tool_registry.py)

```python
class ToolRegistry:
    def register(name, schema, executor) -> self       # 注册单个工具
    def register_many([(name, schema, executor)]) -> self  # 批量注册
    def get_schemas() -> list[dict]                    # 返回 Anthropic API 格式
    def execute(name, tool_input, **context) -> str    # 执行工具
    def get_tool_names() -> list[str]
```

- **schema**: Anthropic API tool 格式 `{name, description, input_schema}`
- **executor**: `(tool_input: dict, **context) -> str`，context 用于传递 sandbox/paper_fetcher 等运行时对象
- 每个 Agent 实例持有独立 ToolRegistry 实例

### BaseAgent 新增 (agents/base_agent.py)

```python
class BaseAgent:
    # 新增属性
    tool_registry: ToolRegistry        # 在 __call__ 中重建
    _submit_result_key = "submit_result"

    # 新增钩子（子类覆盖）
    def _register_tools(self, state)              # 注册工具
    def _build_tool_system_prompt(self, state)     # 构建 tool-use system prompt
    def _build_task_prompt(self, state)             # 构建初始 task prompt
    def _on_submit_result(self, results, state)    # 映射 submit 结果到 state

    # 新增方法
    def _agentic_loop(self, state, max_turns=None, **tool_context) -> (dict|None, str)
    def call_llm_tools(self, prompt, tools=None, **kwargs) -> response
```

- `_register_tools()` 默认空实现 → 不注册工具的旧 Agent 行为不变
- `_agentic_loop()` 是可选方法，子类在 `_execute()` 中决定是否调用
- `__call__` 中在 `_execute()` 前调用 `_register_tools()`

### BrowserManager (agents/browser_manager.py)

```python
class BrowserManager:
    @classmethod get_instance() -> BrowserManager   # 单例模式
    def browse(url, extract_text=True, max_text_length=10000) -> dict
    def search_google(query, max_results=5) -> list[dict]
    def cleanup()
```

- 惰性初始化 Playwright Chromium（headless）
- Playwright 不可用时 browse 工具不注册（graceful degradation）
- 每次 browse 创建新 page、用完关闭

### llm.py 新增

```python
def call_llm_tools(client, prompt, tools, system_prompt, model, max_tokens, temperature) -> response
    # 带 tools 参数的 LLM 调用，返回原始 response 对象
```

---

## 实施阶段

### Phase 1: 基础设施

**新建**:
- `agents/tool_registry.py` — ToolRegistry 类
- `agents/browser_manager.py` — BrowserManager (Playwright)

**修改**:
- `agents/base_agent.py` — 新增 `_agentic_loop`, `_register_tools`, `_build_tool_system_prompt`, `_build_task_prompt`, `_on_submit_result`, `call_llm_tools`；修改 `__call__`
- `agents/llm.py` — 新增 `call_llm_tools()`

**验证**: AST 解析；现有 Agent 不注册工具时行为不变

### Phase 2: ExperimentAgent 适配

**修改**:
- `agents/experiment/agent.py` — 删除内联 `_agentic_loop`，改用 `BaseAgent._agentic_loop`；实现 `_register_tools`, `_build_tool_system_prompt`, `_build_task_prompt`, `_on_submit_result`
- `agents/experiment/tools.py` — 将 TOOL_SCHEMAS + execute_tool 适配为 ToolRegistry 的 `(name, schema, executor)` 格式

**验证**: `from agents.experiment import ExperimentAgent` 成功；AST 验证必需方法存在

### Phase 3: IdeationAgent 升级

**新建**:
- `agents/ideation/__init__.py`
- `agents/ideation/agent.py`
- `agents/ideation/tools.py` — 7 个工具
- `agents/ideation/prompts.py`

**修改**:
- `agents/__init__.py` — `from .ideation import IdeationAgent`
- `core/pipeline.py` — 更新 import

**删除**: `agents/ideation_agent.py`

**验证**: `from agents import IdeationAgent` 成功；构造签名 `IdeationAgent(llm, paper_fetcher, file_manager, pdf_reader=pdf_reader)` 不变

### Phase 4: PlanningAgent 升级

**新建**:
- `agents/planning/__init__.py`
- `agents/planning/agent.py`
- `agents/planning/tools.py` — 5 个工具
- `agents/planning/prompts.py`

**修改**:
- `agents/__init__.py` — `from .planning import PlanningAgent`
- `core/pipeline.py` — 更新 import

**删除**: `agents/planning_agent.py`

**验证**: `from agents import PlanningAgent` 成功；构造签名 `PlanningAgent(llm, file_manager)` 不变

### Phase 5: WritingAgent 升级

**新建**:
- `agents/writing/__init__.py`
- `agents/writing/agent.py`
- `agents/writing/tools.py` — 6 个工具
- `agents/writing/prompts.py`

**修改**:
- `agents/__init__.py` — `from .writing import WritingAgent`
- `core/pipeline.py` — 更新 import

**删除**: `agents/writing_agent.py`

**验证**: `from agents import WritingAgent` 成功；构造签名 `WritingAgent(llm, file_manager)` 不变

### Phase 6: 配置 + 文档

**修改**:
- `config/agent_config.py` — 每个 Agent 增加 `max_agent_turns`, `max_tokens`
- 所有 CLAUDE.md（根目录、agents/、各子包）
- 文件头注释更新

---

## Pipeline 兼容性

`core/pipeline.py` 只需更新 import 路径：

```python
# 旧
from agents.ideation_agent import IdeationAgent
from agents.planning_agent import PlanningAgent

# 新
from agents.ideation import IdeationAgent
from agents.planning import PlanningAgent
```

构造签名完全不变。State 输出字段完全不变。

---

## 验证清单

每个 Phase 完成后验证：

1. `python -c "import ast; ast.parse(open(file, encoding='utf-8').read())"` — 所有新/改文件
2. `python -c "from agents import IdeationAgent, PlanningAgent, ExperimentAgent, WritingAgent; print('OK')"` — 导入成功
3. AST 验证每个 Agent 包含 `_execute`, `_register_tools`, `_build_tool_system_prompt`, `_build_task_prompt`, `_on_submit_result`
4. `BaseAgent._agentic_loop` 存在且签名正确
5. `ToolRegistry.register/execute/get_schemas` 方法存在
6. `BrowserManager.browse/search_google/cleanup` 方法存在
7. `pipeline.py` 中所有 Agent 的 import 和构造函数无需修改（除 import 路径）

---

## Checklist

**Phase 1 基础设施**:
- [x] `agents/tool_registry.py` — ToolRegistry 类
- [x] `agents/browser_manager.py` — BrowserManager (Playwright)
- [x] `agents/base_agent.py` — 新增 _agentic_loop + 钩子方法
- [x] `agents/llm.py` — 新增 call_llm_tools()

**Phase 2 ExperimentAgent**:
- [x] `agents/experiment/agent.py` — 迁移到 BaseAgent._agentic_loop
- [x] `agents/experiment/tools.py` — 适配 ToolRegistry 格式

**Phase 3 IdeationAgent**:
- [x] `agents/ideation/__init__.py`
- [x] `agents/ideation/agent.py`
- [x] `agents/ideation/tools.py` (7 工具)
- [x] `agents/ideation/prompts.py`
- [x] 删除 `agents/ideation_agent.py`

**Phase 4 PlanningAgent**:
- [x] `agents/planning/__init__.py`
- [x] `agents/planning/agent.py`
- [x] `agents/planning/tools.py` (5 工具)
- [x] `agents/planning/prompts.py`
- [x] 删除 `agents/planning_agent.py`

**Phase 5 WritingAgent**:
- [x] `agents/writing/__init__.py`
- [x] `agents/writing/agent.py`
- [x] `agents/writing/tools.py` (6 工具)
- [x] `agents/writing/prompts.py`
- [x] 删除 `agents/writing_agent.py`

**Phase 6 配置+文档**:
- [x] `config/agent_config.py` 更新
- [x] `agents/__init__.py` 更新
- [x] `core/pipeline.py` 更新 import
- [x] 所有 CLAUDE.md 更新
