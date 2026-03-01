# core/ - 核心基础设施层

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 提供系统核心基础设施,包括状态管理、Pipeline编排、记忆系统、知识图谱、数据库
2. **依赖**: langgraph (Pipeline框架), sqlite3 (数据持久化), typing (类型系统), anthropic SDK
3. **输出**: ResearchState状态定义、LangGraph Pipeline、AgentMemory系统、KnowledgeGraph、Database持久化层

## 文件清单

### state.py
- **角色**: 状态定义 (State Schema)
- **功能**: 定义ResearchState TypedDict,是整个系统的数据契约

### pipeline.py
- **角色**: Pipeline编排器 (Workflow Orchestration)
- **功能**: 使用LangGraph编排四个Agent的执行流程,实现状态路由、错误处理、checkpointing

### memory.py
- **角色**: Agent记忆管理器 (Memory Manager)
- **功能**: AgentMemory类,管理 data/{agent_name}/ 下的 Markdown 记忆文件 (persona/memory/mistakes/daily)，直接构建 system prompt

### knowledge_graph.py
- **角色**: 知识图谱 (Knowledge Graph)
- **功能**: 构建和查询研究领域的知识图谱,连接概念、论文、假设之间的关系

### database.py
- **角色**: 数据库核心 (Database Core)
- **功能**: SQLite数据库的核心操作,提供基础的CRUD接口和表结构定义

### persistence.py
- **角色**: 持久化管理器 (Persistence Manager)
- **功能**: 管理LangGraph的checkpoint持久化,支持Pipeline状态恢复和断点续传

### __init__.py
- **角色**: 模块初始化
- **功能**: 导出核心类和函数

## 已删除文件

- `agent_memory_manager.py` → 替换为 `memory.py`
- `agent_persona.py` → 已删除 (死代码,从未被Agent调用)
- `self_reflection.py` → 已删除 (死代码,从未被Agent调用)
- `iteration_memory.py` → 已删除 (死代码，仅在 docs/ 中提及)
- `document_tracker.py` → 已删除 (死代码，仅在 docs/ 中提及)
- `logging_config.py` → 已删除 (死代码，仅在 docs/ 中提及)
- `document_memory_manager.py` → 已删除 (运行时必崩 bug，仅被已删除的 tests/scripts 使用)
- `database_extensions.py` → 已删除 (仅被已删除的 document_memory_manager 使用)

## 更新历史

- 2026-03-01: 删除 5 个死代码模块 (iteration_memory, document_tracker, logging_config, document_memory_manager, database_extensions)
- 2026-02-28: 重构: 用 memory.py (AgentMemory) 替代 agent_memory_manager.py，删除 agent_persona.py 和 self_reflection.py
- 2026-02-27: 创建此文档
