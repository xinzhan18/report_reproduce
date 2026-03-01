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
- **功能**: `__call__` 生命周期, `_agentic_loop()` 通用工具循环, `call_llm()`/`call_llm_json()`/`save_artifact()`, 四个 hook 方法

### llm.py
- **角色**: LLM 调用模块 (无状态函数)
- **功能**: `call_llm()` 文本调用, `call_llm_json()` JSON 调用, `call_llm_tools()` 工具调用, `extract_json()` JSON 提取

### tool_registry.py
- **角色**: 工具注册中心
- **功能**: `ToolRegistry` 类,管理 Anthropic API 格式的 tool schema 和 executor；`register()`/`register_many()`/`get_schemas()`/`execute()`

### browser_manager.py
- **角色**: Playwright 浏览器管理器
- **功能**: `BrowserManager` 单例类,提供 `browse()` 网页浏览和 `search_google()` 搜索；惰性初始化；Playwright 不可用时 graceful degradation

### ideation/ (子包)
- **角色**: 文献智能体 (Agentic Tool-Use 引擎) - 继承BaseAgent
- **功能**: 通过 tool_use API 自主搜索论文、下载 PDF 深度阅读、查询知识图谱、综合分析、识别研究缺口、生成假设。7 个工具 (search_papers, fetch_recent_papers, download_and_read_pdf, search_knowledge_graph, browse_webpage, google_search, submit_result)
- **子文件**: agent.py (主类), tools.py (工具 schema+executor), prompts.py (prompt 模板), __init__.py
- **依赖**: PaperFetcher, PDFReader, KnowledgeGraph, BrowserManager

### planning/ (子包)
- **角色**: 规划智能体 (Agentic Tool-Use 引擎) - 继承BaseAgent
- **功能**: 通过 tool_use API 自主读取上游文献数据、查询知识图谱、验证数据可用性、设计实验方案。5 个工具 (read_upstream_file, search_knowledge_graph, browse_webpage, google_search, submit_result)
- **子文件**: agent.py (主类), tools.py (工具 schema+executor), prompts.py (prompt 模板), __init__.py
- **依赖**: FileManager, KnowledgeGraph, BrowserManager

### experiment/ (子包)
- **角色**: 实验智能体 (Agentic Tool-Use 引擎) - 继承BaseAgent
- **功能**: 通过 tool_use API 自主编写代码、运行实验、调试修复、提交结果。8 个工具 (bash, write_file, read_file, delete_file, run_python, browse_webpage, google_search, submit_result)
- **子文件**: agent.py (主类), sandbox.py (沙箱管理), tools.py (工具 schema+executor), prompts.py (prompt 模板), metrics.py (指标计算), __init__.py
- **依赖**: SandboxManager, DataFetcher, BrowserManager

### writing/ (子包)
- **角色**: 写作智能体 (Agentic Tool-Use 引擎) - 继承BaseAgent
- **功能**: 通过 tool_use API 自主读取所有上游产出、撰写各报告节、生成可视化、组装润色报告。6 个工具 (read_upstream_file, write_section, run_python, browse_webpage, google_search, submit_result)
- **子文件**: agent.py (主类), tools.py (工具 schema+executor), prompts.py (prompt 模板), __init__.py
- **依赖**: FileManager, BrowserManager

### __init__.py
- **角色**: 模块初始化
- **功能**: 导出四个Agent

## 更新历史

- 2026-03-01: 全 Agent Agentic Tool-Use 架构升级：BaseAgent 新增 _agentic_loop() 通用循环 + ToolRegistry 注册中心 + BrowserManager 浏览器 + call_llm_tools()；IdeationAgent/PlanningAgent/WritingAgent 从单文件重构为子包，全部采用 agentic tool-use 模式；ExperimentAgent 适配 BaseAgent._agentic_loop()；删除旧单文件 ideation_agent.py/planning_agent.py/writing_agent.py
- 2026-03-01: ExperimentAgent 升级为 Agentic Tool-Use 引擎
- 2026-02-28: 重构：消除 services/utils 间接层，扁平化目录结构
