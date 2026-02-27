# agents/ - AI智能体层

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 实现四个核心研究智能体,负责从文献分析到报告生成的完整研究流程
2. **依赖**: core/state (ResearchState), config/agent_config (Agent配置), services (LLM/Intelligence/Output服务), utils (JSON解析/Prompt构建)
3. **输出**: BaseAgent抽象基类, IdeationAgent, PlanningAgent, ExperimentAgent, WritingAgent四个具体实现

## 架构模式

所有四个Agent统一继承自BaseAgent (Template Method Pattern):
- **BaseAgent**: 提供execute()生命周期、call_llm()、save_artifact()等基础设施
- **子类Agent**: 仅实现`_execute()`业务逻辑和`_generate_execution_summary()`
- 消除了~790行基础设施重复代码

## 文件清单

### base_agent.py
- **角色**: Agent抽象基类 (Template Method Pattern)
- **功能**: 定义execute()生命周期,提供call_llm()、save_artifact()等通用方法,消除代码重复
- **行数**: ~339行

### ideation_agent.py
- **角色**: 文献智能体 (Research Ideation) - 继承BaseAgent
- **功能**: 文献扫描、深度分析、研究差距识别、假设生成,输出研究方向
- **行数**: ~422行

### planning_agent.py
- **角色**: 规划智能体 (Experiment Planning) - 继承BaseAgent
- **功能**: 实验设计、方法论规划、技术路线制定,输出实验计划
- **重构**: 从独立实现重构为继承BaseAgent,消除~260行重复代码

### experiment_agent.py
- **角色**: 实验智能体 (Execution & Testing) - 继承BaseAgent
- **功能**: 策略代码生成、回测执行、结果分析,输出实验数据和策略代码
- **重构**: 从独立实现重构为继承BaseAgent,消除~280行重复代码

### writing_agent.py
- **角色**: 写作智能体 (Report Generation) - 继承BaseAgent
- **功能**: 研究报告生成、文档整合、学术写作,输出完整研究报告
- **重构**: 从独立实现重构为继承BaseAgent,消除~250行重复代码

### __init__.py
- **角色**: 模块初始化
- **功能**: 导出四个Agent和BaseAgent,提供统一的包接口

## 子模块

### services/ - Agent服务层
包含LLMService (LLM调用封装)、IntelligenceContext (智能上下文管理)、OutputManager (输出管理器)

### utils/ - Agent工具层
包含JSONParser (JSON解析工具)、PromptBuilder (Prompt构建工具)

## 更新历史

- 2026-02-28: 重构PlanningAgent/WritingAgent/ExperimentAgent继承BaseAgent,消除~790行重复代码
- 2026-02-27: 创建此文档,记录当前架构
