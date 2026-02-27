# core/ - 核心基础设施层

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 提供系统核心基础设施,包括状态管理、Pipeline编排、记忆系统、知识图谱、数据库
2. **依赖**: langgraph (Pipeline框架), sqlite3 (数据持久化), typing (类型系统), anthropic SDK
3. **输出**: ResearchState状态定义、LangGraph Pipeline、AgentMemory系统、KnowledgeGraph、Database持久化层

## 文件清单

### state.py
- **角色**: 状态定义 (State Schema)
- **功能**: 定义ResearchState TypedDict,是整个系统的数据契约,所有Agent和Pipeline的状态流转基础

### pipeline.py
- **角色**: Pipeline编排器 (Workflow Orchestration)
- **功能**: 使用LangGraph编排四个Agent的执行流程,实现状态路由、错误处理、checkpointing

### agent_memory_manager.py
- **角色**: Agent记忆管理器 (Memory Manager)
- **功能**: 管理Agent的Markdown记忆系统(persona/memory/daily/mistakes),默认路径从`data/agents/`迁移至`data/`,支持向后兼容

### document_memory_manager.py
- **角色**: 文档记忆管理器 (Document Memory)
- **功能**: 管理文献文档的记忆存储,支持文档跟踪、版本管理、内容索引

### knowledge_graph.py
- **角色**: 知识图谱 (Knowledge Graph)
- **功能**: 构建和查询研究领域的知识图谱,连接概念、论文、假设之间的关系

### database.py
- **角色**: 数据库核心 (Database Core)
- **功能**: SQLite数据库的核心操作,提供基础的CRUD接口和表结构定义

### database_extensions.py
- **角色**: 数据库扩展 (Database Extensions)
- **功能**: 扩展数据库功能,添加复杂查询、统计分析、数据迁移等高级操作

### persistence.py
- **角色**: 持久化管理器 (Persistence Manager)
- **功能**: 管理LangGraph的checkpoint持久化,支持Pipeline状态恢复和断点续传

### agent_persona.py
- **角色**: Agent人格系统 (Agent Persona)
- **功能**: 定义Agent的人格特征、风格偏好、决策模式,增强Agent的个性化

### self_reflection.py
- **角色**: 自我反思系统 (Self-Reflection)
- **功能**: 实现Agent的自我评估、错误反思、策略调整能力

### iteration_memory.py
- **角色**: 迭代记忆 (Iteration Memory)
- **功能**: 记录Pipeline多次迭代的历史,支持跨迭代的学习和优化

### document_tracker.py
- **角色**: 文档追踪器 (Document Tracker)
- **功能**: 追踪文献文档的访问历史、使用频率、关联关系

### logging_config.py
- **角色**: 日志配置 (Logging Configuration)
- **功能**: 配置系统日志输出,支持文件日志、控制台日志、日志级别管理

### __init__.py
- **角色**: 模块初始化
- **功能**: 导出核心类和函数,提供统一的包接口

## 更新历史

- 2026-02-28: agent_memory_manager.py默认路径从data/agents/迁移至data/,添加向后兼容和migrate_to_new_path()方法
- 2026-02-27: 创建此文档,记录当前架构
