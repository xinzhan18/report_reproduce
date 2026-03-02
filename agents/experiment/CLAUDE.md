# agents/experiment/ - Agentic Tool-Use 因子研究执行引擎

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 通过 Anthropic tool_use API 实现多轮 agentic 循环，LLM 自主调用 bash/文件读写/Python 执行等工具完成因子计算与评估
2. **依赖**: agents.base_agent (BaseAgent), agents.tool_registry, agents.browser_manager, agents.common_tools, core.state (FactorPlan, FactorResults), tools.file_manager, market_data.LocalDataLoader, config.llm_config
3. **输出**: ExperimentAgent 类（继承 BaseAgent，Pipeline 第三阶段）

## 架构模式

```
_execute(state)
  ├─ 数据准备 (LocalDataLoader.load)
  ├─ 创建 Sandbox (SandboxManager.create + inject_data + inject_helpers)
  └─ _agentic_loop(state, sandbox=..., timeout=..., browser=...)
      └─ LLM ←→ tools (bash/write_file/read_file/delete_file/run_python/browse_webpage/google_search/submit_result)
```

Sandbox 注入:
- `data/*.csv` — per-symbol OHLCV CSV
- `data/panel.csv` — 长格式面板数据
- `data_manifest.json` — 文件清单 + 元信息
- `evaluate_factor.py` — 因子评估辅助函数

## 文件清单

### agent.py
- **角色**: ExperimentAgent 主类
- **功能**: 继承 BaseAgent，实现 _execute() + 四个 hook 方法 + _analyze_results() + _map_to_factor_results() + _describe_data() + _collect_code_from_sandbox() + _update_and_save_plan() + _update_plan_checklist() + _build_experiment_markdown() + _identify_failed_steps()
- **产出文件**: `experiments/plan.md` (回写 checklist), `experiments/experiment.md`, `experiments/factor_code.py`, `experiments/factor_results.json`
- **反馈回路**: 写入 `state["experiment_feedback"]` (ExperimentFeedback)

### sandbox.py
- **角色**: SandboxManager 沙箱管理器
- **功能**: 工作目录隔离、文件读写、进程执行（shell=False 安全执行）、面板数据注入（per-symbol CSV + panel.csv）、evaluate_factor.py 注入

### tools.py
- **角色**: Tool schema + executor
- **功能**: 8 个工具 (bash, write_file, read_file, delete_file, run_python, submit_result 专用 + browse_webpage, google_search 通用)

### prompts.py
- **角色**: Prompt 模板
- **功能**: SYSTEM_PROMPT_TEMPLATE (因子计算+评估 workflow) + build_task_prompt()

### metrics.py
- **角色**: 因子评估辅助函数
- **功能**: evaluate_factor() 源码注入到 sandbox，计算 IC/ICIR/分层收益/换手率/单调性等指标

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
| validation_metrics.min_ic_mean | 0.02 | 最小 IC 均值 |
| validation_metrics.min_icir | 0.3 | 最小 ICIR |
| validation_metrics.max_turnover | 0.8 | 最大换手率 |
| validation_metrics.min_coverage | 0.5 | 最小因子覆盖率 |

## 更新历史

- 2026-03-02: 因子研究改造：compute_metrics→evaluate_factor, BacktestResults→FactorResults, DataFetcher→LocalDataLoader, strategy.py→factor_code.py, backtest_results.json→factor_results.json, sandbox 注入面板数据+evaluate_factor
- 2026-03-01: Markdown 驱动：读取 plan.md 作为 task prompt，执行后回写 checklist 标记 + 构建 experiment.md + 写入 ExperimentFeedback
- 2026-03-01: 创建子包，从单文件 experiment_agent.py 重构为 Agentic Tool-Use 引擎
