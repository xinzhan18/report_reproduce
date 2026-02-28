# config/ - 系统配置层

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 管理系统所有配置,包括LLM模型、API认证、Agent参数、数据源
2. **依赖**: os (环境变量), pathlib (路径管理), anthropic SDK (API配置), 无核心业务依赖
3. **输出**: LLM配置(llm_config)、认证配置(auth_config)、Agent配置(agent_config)、数据源配置(data_sources)

## 文件清单

### llm_config.py
- **角色**: LLM基础配置 (Model Configuration)
- **功能**: 定义Claude模型选择、温度参数、token限制等LLM基础配置

### llm_config_oauth.py
- **角色**: OAuth认证配置 (OAuth LLM Config)
- **功能**: 支持OAuth2.0认证的LLM配置,用于生产环境的安全认证

### auth_config.py
- **角色**: API认证配置 (Authentication)
- **功能**: 管理Anthropic API密钥、OAuth配置、认证令牌等安全凭证

### agent_config.py
- **角色**: Agent参数配置 (Agent Parameters)
- **功能**: 定义四个Agent的具体参数、行为配置。experiment 配置含 max_agent_turns/sandbox_timeout/sandbox_cleanup/sandbox_base_dir

### multi_llm_config.py
- **角色**: 多模型配置 (Multi-Model Config)
- **功能**: 支持多个LLM模型的配置切换,为不同Agent分配不同模型

### data_sources.py
- **角色**: 数据源配置 (Data Source Settings)
- **功能**: 配置arXiv API、Yahoo Finance等外部数据源的访问参数

### __init__.py
- **角色**: 模块初始化
- **功能**: 导出所有配置类,提供统一的包接口

## 更新历史

- 2026-02-27: 创建此文档,记录当前架构
