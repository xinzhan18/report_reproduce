# agents/experiment/ - Agentic Tool-Use 实验执行引擎

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 通过 Anthropic tool_use API 实现多轮 agentic 循环，LLM 自主调用 bash/文件读写/Python 执行等工具完成实验
2. **依赖**: agents.base_agent (BaseAgent), agents.tool_registry, agents.browser_manager, core.state, tools.file_manager, market_data.DataFetcher, config.llm_config
3. **输出**: ExperimentAgent 类（继承 BaseAgent，Pipeline 第三阶段）

## 架构模式

```
_execute(state)
  ├─ 数据准备 (DataFetcher.fetch)
  ├─ 创建 Sandbox (SandboxManager.create + inject_data + inject_helpers)
  └─ _agentic_loop(state, sandbox=..., timeout=..., browser=...)
      └─ LLM ←→ tools (bash/write_file/read_file/delete_file/run_python/browse_webpage/google_search/submit_result)
```

使用 BaseAgent._agentic_loop() 通用循环。

## 文件清单

### agent.py
- **角色**: ExperimentAgent 主类
- **功能**: 继承 BaseAgent，实现 _execute() + 四个 hook 方法 + _analyze_results() + _map_to_backtest_results() + _describe_data() + _collect_code_from_sandbox()

### sandbox.py
- **角色**: SandboxManager 沙箱管理器
- **功能**: 工作目录隔离、文件读写、进程执行（subprocess）、路径逃逸防护、命令黑名单、输出截断

### tools.py
- **角色**: Tool schema + executor
- **功能**: 8 个工具的 Anthropic API 格式 schema + executor + get_tool_definitions()；适配 ToolRegistry 格式

### prompts.py
- **角色**: Prompt 模板
- **功能**: SYSTEM_PROMPT_TEMPLATE + build_task_prompt()

### metrics.py
- **角色**: 指标计算辅助函数
- **功能**: compute_metrics() 源码注入到 sandbox

### __init__.py
- **角色**: 子包入口
- **功能**: 导出 ExperimentAgent

## 配置项 (config/agent_config.py)

| 配置 | 默认值 | 说明 |
|------|--------|------|
| max_agent_turns | 30 | 最大 tool-use 循环轮次 |
| max_tokens | 4096 | 每次 LLM 调用最大 token |
| sandbox_timeout | 300 | 单条命令超时(秒) |
| sandbox_cleanup | True | 实验后清理 sandbox |
| sandbox_base_dir | sandbox_workspaces | sandbox 根目录 |

## 更新历史

- 2026-03-01: 适配 BaseAgent._agentic_loop() 通用循环；tools.py 适配 ToolRegistry 格式 (get_tool_definitions)；新增浏览器工具 (browse_webpage, google_search)
- 2026-03-01: 创建子包，从单文件 experiment_agent.py 重构为 Agentic Tool-Use 引擎
