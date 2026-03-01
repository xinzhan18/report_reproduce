# agents/ - AI智能体层

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 实现四个核心研究智能体,全部采用 Agentic Tool-Use 架构,通过 BaseAgent._agentic_loop() 实现多轮工具自治执行
2. **依赖**: agents.llm (LLM调用), agents.tool_registry (ToolRegistry), agents.browser_manager (BrowserManager), core.memory (AgentMemory), core.knowledge_graph, core.state, config.agent_config, tools/*
3. **输出**: BaseAgent抽象基类, ToolRegistry, BrowserManager, IdeationAgent, PlanningAgent, ExperimentAgent, WritingAgent

## 架构模式

所有四个Agent统一继承自BaseAgent，采用 Agentic Tool-Use 模式:

```
BaseAgent._agentic_loop()     ← 通用循环
  ↕ 调用
ToolRegistry                   ← 每个 Agent 实例持有一个
  ↕ 管理
工具集 = 通用工具 + Agent 专用工具
```

### 子类只需实现 4+1 个方法

```python
class MyAgent(BaseAgent):
    def _execute(self, state)                        # 业务逻辑（调用 _agentic_loop）
    def _register_tools(self, state)                  # 注册工具到 self.tool_registry
    def _build_tool_system_prompt(self, state) -> str # 构建 system prompt
    def _build_task_prompt(self, state) -> str         # 构建初始 user message
    def _on_submit_result(self, results, state)        # 映射结果到 state
```

## 文件清单

### base_agent.py
- **角色**: Agent抽象基类 (Template Method + Agentic Tool-Use Pattern)
- **功能**: `__call__` 生命周期, `_agentic_loop()` 通用工具循环, `_reflect_and_update_memory()` LLM 反思记忆更新, `call_llm()`/`call_llm_json()`/`save_artifact()`, 四个 hook 方法

### llm.py
- **角色**: LLM 调用模块 (无状态函数)
- **功能**: `call_llm()` 文本调用, `call_llm_json()` JSON 调用, `call_llm_tools()` 工具调用, `extract_json()` JSON 提取

### tool_registry.py
- **角色**: 工具注册中心
- **功能**: `ToolRegistry` 类,管理 Anthropic API 格式的 tool schema 和 executor；`register()`/`register_many()`/`get_schemas()`/`execute()`

### browser_manager.py
- **角色**: Playwright 浏览器管理器
- **功能**: `BrowserManager` 单例类,提供 `browse()` 网页浏览和 `search_google()` 搜索；惰性初始化；Playwright 不可用时 graceful degradation

### common_tools.py
- **角色**: 通用工具定义 (Shared Tool Definitions)
- **功能**: 4 个跨 Agent 共享的工具 schema + executor (browse_webpage, google_search, search_knowledge_graph, read_upstream_file)；`get_common_tools()` 接口供各 Agent tools.py 导入

### ideation/ (子包)
- **角色**: 文献智能体 (Agentic Tool-Use 引擎) - 继承BaseAgent
- **功能**: 自主搜索论文、下载 PDF、查询知识图谱、综合分析、生成假设。输出统一 `ideation.md`。7 个工具
- **产出**: `literature/ideation.md` (核心), `literature/papers_analyzed.json`, `literature/research_synthesis.json`
- **子文件**: agent.py (主类+_build_ideation_markdown), tools.py, prompts.py, __init__.py
- **依赖**: PaperFetcher, PDFReader, KnowledgeGraph, BrowserManager

### planning/ (子包)
- **角色**: 规划智能体 (Agentic Tool-Use 引擎) - 继承BaseAgent
- **功能**: 读取 ideation.md、查询知识图谱、设计实验方案。输出 `plan.md` 带 Implementation Checklist。支持修正模式（反馈回路）。5 个工具
- **产出**: `experiments/plan.md` (带 checklist), `experiments/data_config.json`
- **子文件**: agent.py (主类+_build_plan_markdown), tools.py, prompts.py (含 build_revision_task_prompt), __init__.py
- **依赖**: FileManager, KnowledgeGraph, BrowserManager

### experiment/ (子包)
- **角色**: 实验智能体 (Agentic Tool-Use 引擎) - 继承BaseAgent
- **功能**: 自主编写代码、运行实验。执行后回写 plan.md checklist + 构建 experiment.md + 写入 ExperimentFeedback。8 个工具
- **产出**: `experiments/plan.md` (回写), `experiments/experiment.md`, `experiments/strategy.py`, `experiments/backtest_results.json`
- **子文件**: agent.py (主类+checklist回写+experiment.md), sandbox.py, tools.py, prompts.py, metrics.py, __init__.py
- **依赖**: SandboxManager, DataFetcher, BrowserManager

### writing/ (子包)
- **角色**: 写作智能体 (Agentic Tool-Use 引擎) - 继承BaseAgent
- **功能**: 读取上游 ideation.md/plan.md/experiment.md，撰写报告。不写 state，仅保存文件。5 个工具
- **产出**: `reports/final_report.md`, `reports/final_report_formatted.md`
- **子文件**: agent.py (主类), tools.py, prompts.py, __init__.py
- **依赖**: FileManager, BrowserManager

### __init__.py
- **角色**: 模块初始化
- **功能**: 导出四个Agent

## Markdown 驱动数据流

```
IdeationAgent → ideation.md → PlanningAgent → plan.md → ExperimentAgent → plan.md (回写) + experiment.md → WritingAgent → report.md
                                    ↑                                          │
                                    └── revise_plan (feedback loop) ───────────┘
```

## 更新历史

- 2026-03-01: Markdown 驱动架构升级：ideation.md 统一输出、plan.md checklist + 回写、experiment.md 结果、ExperimentFeedback 反馈回路、State 精简
- 2026-03-01: BaseAgent 新增 _reflect_and_update_memory()：执行完成后用 haiku LLM 分析日志，自动提取 learnings/mistakes 写入 AgentMemory
- 2026-03-01: 10 项修复: Sortino 双重年化、BacktestEngine 假指标、PlanningAgent/WritingAgent prompt 修正、state["error"]→error_log、通用工具提取到 common_tools.py、删除死代码/配置、token 跟踪、沙箱安全增强
- 2026-03-01: 全 Agent Agentic Tool-Use 架构升级：BaseAgent 新增 _agentic_loop() 通用循环 + ToolRegistry 注册中心 + BrowserManager 浏览器 + call_llm_tools()；IdeationAgent/PlanningAgent/WritingAgent 从单文件重构为子包，全部采用 agentic tool-use 模式；ExperimentAgent 适配 BaseAgent._agentic_loop()；删除旧单文件 ideation_agent.py/planning_agent.py/writing_agent.py
- 2026-03-01: ExperimentAgent 升级为 Agentic Tool-Use 引擎
- 2026-02-28: 重构：消除 services/utils 间接层，扁平化目录结构
