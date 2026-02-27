# agents/services/ - Agent服务层

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 为所有Agent提供通用服务能力,包括LLM调用、智能上下文、输出管理
2. **依赖**: config/llm_config (LLM配置), core/agent_memory_manager (记忆管理), anthropic SDK (Claude API)
3. **输出**: LLMService, IntelligenceContext, OutputManager三个服务类,被所有Agent通过BaseAgent使用

## 文件清单

### llm_service.py
- **角色**: LLM调用服务 (API Wrapper)
- **功能**: 封装Anthropic API调用,支持streaming、retry、model selection,提供统一的LLM接口

### intelligence_context.py
- **角色**: 智能上下文服务 (Context Manager)
- **功能**: 管理Agent的记忆系统、知识图谱、自我反思,提供上下文感知能力

### output_manager.py
- **角色**: 输出管理服务 (Output Handler)
- **功能**: 统一管理Agent的文件输出、JSON序列化、artifact保存,确保输出规范性

### __init__.py
- **角色**: 模块初始化
- **功能**: 导出三个服务类,提供统一的包接口

## 更新历史

- 2026-02-27: 创建此文档,记录当前架构
