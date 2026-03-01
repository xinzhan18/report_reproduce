# agents/writing/ - Agentic Tool-Use 研究报告生成引擎

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 通过 Anthropic tool_use API 实现多轮 agentic 循环，LLM 自主读取所有上游产出、撰写报告各节、组装润色
2. **依赖**: agents.base_agent (BaseAgent), agents.tool_registry, agents.browser_manager, agents.common_tools, tools.file_manager, core.state
3. **输出**: WritingAgent 类（继承 BaseAgent，Pipeline 第四阶段）

## 架构模式

```
_execute(state)
  └─ _agentic_loop(state, file_manager=..., project_id=..., browser=...)
      └─ LLM ←→ tools (read_upstream_file/write_section/browse_webpage/google_search/submit_result)
```

通用工具 (read_upstream_file, browse_webpage, google_search) 从 `agents/common_tools.py` 导入。

## 文件清单

### agent.py
- **角色**: WritingAgent 主类
- **功能**: 继承 BaseAgent，实现 _execute() + 四个 hook 方法 + _build_state_summary() + _add_table_of_contents()

### tools.py
- **角色**: Tool schema + executor
- **功能**: 5 个工具 (write_section, submit_result 专用 + read_upstream_file, browse_webpage, google_search 通用)

### prompts.py
- **角色**: Prompt 模板
- **功能**: SYSTEM_PROMPT_TEMPLATE + build_task_prompt()

### __init__.py
- **角色**: 子包入口
- **功能**: 导出 WritingAgent

## 更新历史

- 2026-03-01: 删除 run_python 工具引用 (prompt 和 tools.py)；通用工具提取到 common_tools.py；工具数 6→5
- 2026-03-01: 创建子包，从 writing_agent.py 重构为 Agentic Tool-Use 引擎
