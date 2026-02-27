# tests/ - 测试套件层

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 提供系统各模块的单元测试和集成测试
2. **依赖**: pytest (测试框架), unittest.mock (Mock工具), 被测试的各个模块
3. **输出**: 完整的测试覆盖,确保系统质量和稳定性

## 文件清单

### test_agents.py
- **角色**: Agent测试 (Agent Tests)
- **功能**: 测试四个Agent的核心功能、输出格式、错误处理

### test_base_agent.py
- **角色**: BaseAgent测试 (Base Agent Tests)
- **功能**: 测试BaseAgent的Template Method模式实现、生命周期管理

### test_pipeline.py
- **角色**: Pipeline测试 (Pipeline Tests)
- **功能**: 测试LangGraph Pipeline的状态流转、路由逻辑、checkpointing

### test_tools.py
- **角色**: 工具测试 (Tools Tests)
- **功能**: 测试PaperFetcher、DataFetcher、BacktestEngine等工具的功能

### test_agent_memory_manager.py
- **角色**: 记忆管理器测试 (Memory Manager Tests)
- **功能**: 测试Agent记忆系统的存储、检索、更新、遗忘机制

### test_document_memory.py
- **角色**: 文档记忆测试 (Document Memory Tests)
- **功能**: 测试文档记忆系统的存储、索引、查询功能

### test_domain_classifier.py
- **角色**: 领域分类器测试 (Domain Classifier Tests)
- **功能**: 测试论文领域分类的准确性、多标签支持

### __init__.py
- **角色**: 测试模块初始化
- **功能**: 配置测试环境、共享fixtures

## 更新历史

- 2026-02-27: 创建此文档,记录当前架构
