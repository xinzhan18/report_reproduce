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
- **功能**: 文献扫描、深度分析、研究差距识别、假设生成

### planning_agent.py
- **角色**: 规划智能体 (Experiment Planning) - 继承BaseAgent
- **功能**: 实验设计、方法论规划、技术路线制定

### experiment_agent.py
- **角色**: 实验智能体 (Execution & Testing) - 继承BaseAgent
- **功能**: 策略代码生成、回测执行、结果分析

### writing_agent.py
- **角色**: 写作智能体 (Report Generation) - 继承BaseAgent
- **功能**: 研究报告生成、文档整合、学术写作

### __init__.py
- **角色**: 模块初始化
- **功能**: 导出四个Agent

## 更新历史

- 2026-02-28: 重构：消除 services/utils 间接层，扁平化目录结构，LLM/Memory/Output 直接集成到 BaseAgent
- 2026-02-28: 重构PlanningAgent/WritingAgent/ExperimentAgent继承BaseAgent
- 2026-02-27: 创建此文档
