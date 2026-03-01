# agents/planning/ - Agentic Tool-Use 实验规划引擎

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 通过 Anthropic tool_use API 实现多轮 agentic 循环，LLM 自主读取上游文献数据、查询知识图谱、设计实验方案
2. **依赖**: agents.base_agent (BaseAgent), agents.tool_registry, agents.browser_manager, tools.file_manager, core.knowledge_graph, core.state
3. **输出**: PlanningAgent 类（继承 BaseAgent，Pipeline 第二阶段）

## 架构模式

```
_execute(state)
  └─ _agentic_loop(state, file_manager=..., project_id=..., knowledge_graph=..., browser=...)
      └─ LLM ←→ tools (read_upstream_file/search_knowledge_graph/browse_webpage/google_search/submit_result)
```

## 文件清单

### agent.py
- **角色**: PlanningAgent 主类
- **功能**: 继承 BaseAgent，实现 _execute() + 四个 hook 方法 + _build_kg_context() + _build_planning_document()

### tools.py
- **角色**: Tool schema + executor
- **功能**: 5 个工具的 Anthropic API 格式 schema + executor + get_tool_definitions()

### prompts.py
- **角色**: Prompt 模板
- **功能**: SYSTEM_PROMPT_TEMPLATE + build_task_prompt()

### __init__.py
- **角色**: 子包入口
- **功能**: 导出 PlanningAgent

## 更新历史

- 2026-03-01: 创建子包，从 planning_agent.py 重构为 Agentic Tool-Use 引擎
