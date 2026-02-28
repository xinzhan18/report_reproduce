# agents/ - AI智能体层

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 实现四个核心研究智能体,负责从文献分析到报告生成的完整研究流程
2. **依赖**: agents.llm (LLM调用), core.memory (AgentMemory), core.knowledge_graph, core.state, config.agent_config, tools/*
3. **输出**: BaseAgent抽象基类, IdeationAgent, PlanningAgent, ExperimentAgent, WritingAgent

## 架构模式

所有四个Agent统一继承自BaseAgent (Template Method Pattern):
- **BaseAgent**: 提供 `__call__` 生命周期、`call_llm()` / `call_llm_json()`、`save_artifact()`
- **子类Agent**: 仅实现 `_execute()` 业务逻辑和可选的 `_generate_execution_summary()`
- 无 services 中间层：LLM 调用通过 `agents.llm` 模块级函数；记忆通过 `core.memory.AgentMemory`；文件保存内联

## 文件清单

### base_agent.py
- **角色**: Agent抽象基类 (Template Method Pattern)
- **功能**: 定义 `__call__` 生命周期 (setup→execute→save_log)，提供 `call_llm()`、`call_llm_json()`、`save_artifact()`

### llm.py
- **角色**: LLM 调用模块 (无状态函数)
- **功能**: `call_llm()` 带自动重试、`call_llm_json()` 返回解析后的 JSON、`extract_json()` 从文本提取 JSON

### ideation_agent.py
- **角色**: 文献智能体 (Research Ideation) - 继承BaseAgent
- **功能**: 三阶段深度文献分析流水线：Stage1 扫描+LLM排序(RankedPaper)、Stage2 PDF深度阅读+缓存(StructuredInsights)、Stage3 跨论文综合→研究缺口→假设生成(ResearchSynthesis→ResearchGap→Hypothesis)
- **依赖**: PDFReader(PDF下载/解析)、DocumentMemoryManager(分析缓存)、KnowledgeGraph(上下文注入)

### planning_agent.py
- **角色**: 规划智能体 (Experiment Planning) - 继承BaseAgent
- **功能**: 文献驱动的迭代实验规划：注入KG上下文+IdeationAgent结构化数据(structured_insights.json/research_synthesis.json)，迭代生成计划(generate_plan)→LLM可行性评估(evaluate_feasibility)→修订（最多max_iterations轮），产出ExperimentPlan+详细方法论+data_config.json
- **依赖**: KnowledgeGraph(上下文注入)、FileManager(加载上游文献数据、保存data_config.json)

### experiment/ (子包)
- **角色**: 实验智能体 (Agentic Tool-Use 自治执行引擎) - 继承BaseAgent
- **功能**: 通过 Anthropic tool_use API 实现多轮 agentic 循环，LLM 拥有 bash/文件读写/Python 执行等 6 个工具，自主迭代完成实验（写代码→运行→调试→提交结果）。包含 SandboxManager 隔离执行环境、compute_metrics 辅助函数注入、路径逃逸防护。产出 strategy.py+backtest_results.json+execution_logs.txt。
- **子文件**: agent.py (主类), sandbox.py (沙箱管理), tools.py (tool schema+dispatch), prompts.py (prompt模板), metrics.py (指标计算), __init__.py
- **依赖**: KnowledgeGraph(上下文注入)、FileManager(加载data_config.json)、market_data.DataFetcher(获取金融数据)、config.llm_config(模型名称解析)

### writing_agent.py
- **角色**: 写作智能体 (Report Generation) - 继承BaseAgent
- **功能**: 研究报告生成、文档整合、学术写作

### __init__.py
- **角色**: 模块初始化
- **功能**: 导出四个Agent

## 更新历史

- 2026-03-01: ExperimentAgent 升级为 Agentic Tool-Use 引擎：从单文件 experiment_agent.py 重构为 agents/experiment/ 子包（agent.py/sandbox.py/tools.py/prompts.py/metrics.py）；LLM 通过 tool_use API 自主迭代执行实验；新增 SandboxManager 隔离环境、6 个工具 schema、路径逃逸防护
- 2026-03-01: ExperimentAgent 重写为通用代码执行引擎：不限 Backtrader，支持任意 Python 策略脚本；新增 compute_metrics()、_execute_code()、_map_to_backtest_results()；删除 _build_kg_context()、execute_backtest()、BacktestEngine 依赖；数据层迁移到 market_data.DataFetcher
- 2026-02-28: ExperimentAgent 重构为迭代式策略代码生成与回测执行：KG+文献+数据上下文注入、generate→validate→execute→analyze迭代循环、LLM结果分析替代硬编码validate_results、删除retry_on_failure死代码
- 2026-02-28: PlanningAgent 增加 data_config 字段输出，保存 data_config.json 供 ExperimentAgent 使用
- 2026-02-28: PlanningAgent 重构为文献驱动迭代规划：KG+文献上下文注入、generate_plan+evaluate_feasibility迭代循环、删除硬编码specify_resources/浅层validate_feasibility
- 2026-02-28: IdeationAgent 重构为三阶段深度文献分析流水线，集成 PDFReader + DocumentMemoryManager + KnowledgeGraph
- 2026-02-28: 重构：消除 services/utils 间接层，扁平化目录结构，LLM/Memory/Output 直接集成到 BaseAgent
- 2026-02-28: 重构PlanningAgent/WritingAgent/ExperimentAgent继承BaseAgent
- 2026-02-27: 创建此文档
