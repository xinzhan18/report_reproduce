"""
ExperimentAgent — Agentic Tool-Use 自治执行引擎

Pipeline 第三阶段：通过 BaseAgent._agentic_loop() 实现多轮 tool_use 循环，
LLM 拥有 bash、文件读写、Python 执行等工具，自主迭代完成实验。
执行完成后回写 plan.md checklist 标记完成/失败状态，
并将 ExperimentFeedback 写入 state 供 pipeline 路由决策。
"""

# INPUT:  agents.base_agent (BaseAgent), core.state (ResearchState, ExperimentPlan, BacktestResults, ExperimentFeedback),
#         tools.file_manager (FileManager), market_data (DataFetcher),
#         agents.experiment.sandbox (SandboxManager),
#         agents.experiment.tools (get_tool_definitions),
#         agents.experiment.prompts (SYSTEM_PROMPT_TEMPLATE, build_task_prompt),
#         agents.browser_manager (BrowserManager, is_playwright_available)
# OUTPUT: ExperimentAgent 类
#         产出文件: experiments/plan.md (回写 checklist), experiments/experiment.md (结果),
#                  experiments/strategy.py, experiments/backtest_results.json
# POSITION: Agent层 - 实验智能体，Pipeline 第三阶段
#           通过 BaseAgent._agentic_loop() 驱动的 Agentic Tool-Use 执行引擎
#           回写 plan.md checklist + 构建 experiment.md + 写入 ExperimentFeedback

from typing import Dict, Any, List
import json
import re
import logging

from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import ResearchState, ExperimentPlan, BacktestResults, ExperimentFeedback
from tools.file_manager import FileManager
from market_data import DataFetcher

from agents.experiment.sandbox import SandboxManager
from agents.experiment.tools import get_tool_definitions
from agents.experiment.prompts import SYSTEM_PROMPT_TEMPLATE, build_task_prompt
from agents.browser_manager import BrowserManager, is_playwright_available

logger = logging.getLogger("agents.experiment")


class ExperimentAgent(BaseAgent):
    """Agentic Tool-Use 自治实验执行引擎。"""

    def __init__(self, llm: Anthropic, file_manager: FileManager,
                 data_fetcher: DataFetcher):
        super().__init__(llm, file_manager, "experiment",
                         data_fetcher=data_fetcher)

    # ==================================================================
    # Agentic 钩子
    # ==================================================================

    def _register_tools(self, state: ResearchState):
        """注册沙箱工具 + 浏览器工具到 ToolRegistry。"""
        include_browser = is_playwright_available()
        tool_defs = get_tool_definitions(include_browser=include_browser)
        self.tool_registry.register_many(tool_defs)
        self.logger.info(f"Registered {len(tool_defs)} tools: {self.tool_registry.get_tool_names()}")

    def _build_tool_system_prompt(self, state: ResearchState) -> str:
        """构建 experiment system prompt。"""
        agent_memory = self._system_prompt
        return SYSTEM_PROMPT_TEMPLATE.format(agent_memory=agent_memory)

    def _build_task_prompt(self, state: ResearchState) -> str:
        """构建 experiment task prompt — 读取 plan.md 作为上下文。"""
        # 读取 plan.md
        plan_md = self.file_manager.load_text(
            state["project_id"], "plan.md", subdir="experiments"
        ) or ""

        return build_task_prompt(
            hypothesis=state["hypothesis"],
            methodology=state["methodology"],
            plan_md=plan_md,
            success_criteria=state["experiment_plan"]["success_criteria"],
            data_info=state.get("_data_info", ""),
        )

    def _on_submit_result(self, results: dict, state: ResearchState):
        """submit_result 不在此处理，由 _execute 处理结果映射。"""
        pass

    # ==================================================================
    # 主流程
    # ==================================================================

    def _execute(self, state: ResearchState) -> ResearchState:
        project_id = state["project_id"]
        hypothesis = state["hypothesis"]
        experiment_plan: ExperimentPlan = state["experiment_plan"]

        # Step 1: 数据准备
        self.logger.info("Preparing data...")
        data_config = self.file_manager.load_json(
            project_id, "data_config.json", subdir="experiments"
        ) or {}
        data_dict = self.data_fetcher.fetch(data_config)
        if not data_dict:
            state["validation_status"] = "failed"
            state["error_messages"] = "Failed to fetch required data"
            state["experiment_feedback"] = ExperimentFeedback(
                verdict="failed",
                analysis="Data fetch failed — cannot proceed with experiment",
                suggestions=["Check data source configuration", "Verify network connectivity"],
                failed_steps=["Data preparation"],
            )
            state["iteration"] = state.get("iteration", 0) + 1
            self.logger.error("Data fetch failed")
            return state

        data_info = self._describe_data(data_dict, data_config)
        state["_data_info"] = data_info  # 供 _build_task_prompt 使用
        total_rows = sum(len(df) for df in data_dict.values())
        self.logger.info(f"Data ready: {len(data_dict)} symbol(s), {total_rows} total rows")

        # Step 2: 创建 Sandbox
        experiment_id = f"{project_id}_exp"
        sandbox = SandboxManager(base_dir=self.config.get("sandbox_base_dir", "sandbox_workspaces"))
        sandbox.create(experiment_id)
        sandbox.inject_data(data_dict)
        sandbox.inject_helpers()
        self.logger.info(f"Sandbox created at: {sandbox.workdir}")

        # Step 3: 构建 tool context 并运行 agentic loop
        sandbox_timeout = self.config.get("sandbox_timeout", 300)
        browser = BrowserManager.get_instance() if is_playwright_available() else None

        submitted_results, execution_log = self._agentic_loop(
            state=state,
            sandbox=sandbox,
            timeout=sandbox_timeout,
            browser=browser,
        )

        # Step 4: 结果映射
        if submitted_results:
            metrics = submitted_results.get("metrics", {})
            required = ["total_return", "sharpe_ratio", "max_drawdown", "total_trades"]
            missing = [k for k in required if k not in metrics]

            if missing:
                self.logger.warning(f"Submitted results missing required metrics: {missing}")
                state["validation_status"] = "failed"
                state["error_messages"] = f"Missing required metrics: {missing}"
                state["experiment_feedback"] = ExperimentFeedback(
                    verdict="failed",
                    analysis=f"Missing required metrics: {missing}",
                    suggestions=["Ensure strategy computes all required metrics"],
                    failed_steps=["Calculate metrics"],
                )
            else:
                # LLM 分析结果质量
                analysis = self._analyze_results(metrics, experiment_plan, hypothesis)
                verdict = analysis.get("verdict", "revise_plan")
                self.logger.info(f"Analysis verdict: {verdict}")
                self.logger.info(f"  Total Return: {metrics.get('total_return', 0) * 100:.2f}%")
                self.logger.info(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
                self.logger.info(f"  Max Drawdown: {metrics.get('max_drawdown', 0) * 100:.2f}%")
                self.logger.info(f"  Total Trades: {metrics.get('total_trades', 0)}")

                state["results_data"] = self._map_to_backtest_results(metrics)

                if verdict == "success":
                    state["validation_status"] = "success"
                elif verdict == "accept_partial":
                    state["validation_status"] = "partial"
                else:
                    state["validation_status"] = "partial"  # agentic loop 产出了结果，至少 partial

                # 写入 ExperimentFeedback
                failed_steps = self._identify_failed_steps(metrics, experiment_plan)
                feedback_verdict = verdict if verdict in ("success", "revise_plan") else (
                    "partial" if verdict == "accept_partial" else "revise_plan"
                )
                state["experiment_feedback"] = ExperimentFeedback(
                    verdict=feedback_verdict,
                    analysis=analysis.get("analysis", ""),
                    suggestions=analysis.get("suggestions", []),
                    failed_steps=failed_steps,
                )

                # 保存策略代码和结果
                strategy_code = self._collect_code_from_sandbox(sandbox)
                self.save_artifact(strategy_code, project_id, "strategy.py", "experiments")
                self.save_artifact(
                    dict(state["results_data"]), project_id, "backtest_results.json", "experiments"
                )

                # 回写 plan.md checklist
                self._update_and_save_plan(project_id, metrics, experiment_plan, analysis)

                # 构建并保存 experiment.md
                experiment_md = self._build_experiment_markdown(
                    strategy_code, metrics, analysis
                )
                self.save_artifact(experiment_md, project_id, "experiment.md", "experiments")
        else:
            state["validation_status"] = "failed"
            state["error_messages"] = "Agentic loop ended without submitting results"
            state["experiment_feedback"] = ExperimentFeedback(
                verdict="failed",
                analysis="Agentic loop ended without submitting results",
                suggestions=["Review tool-use loop and sandbox execution"],
                failed_steps=["Complete experiment execution"],
            )

        # 保存执行日志
        self.save_artifact(execution_log, project_id, "execution_logs.txt", "experiments")

        # 递增迭代计数器
        state["iteration"] = state.get("iteration", 0) + 1

        # 记录错误
        if state["validation_status"] == "failed":
            error_msg = state.get("error_messages", "Unknown")
            self.memory.record_mistake(
                description="Agentic experiment execution failed",
                severity=3,
                root_cause=error_msg[:100],
                prevention="Review sandbox execution and tool-use loop",
                project_id=project_id,
            )

        # Step 5: 知识图谱更新
        if state["validation_status"] in ("success", "partial"):
            rd = state["results_data"]
            findings = [
                f"Strategy validated: {experiment_plan['methodology'][:100]}",
                f"Sharpe={rd['sharpe_ratio']:.2f}, Return={rd['total_return']*100:.1f}%, "
                f"MaxDD={rd['max_drawdown']*100:.1f}%, Trades={rd['total_trades']}",
            ]
            self.knowledge_graph.update_knowledge_from_research(
                project_id=project_id, findings=findings, llm=self.llm,
            )

        # Sandbox 清理
        if self.config.get("sandbox_cleanup", True):
            sandbox.cleanup()

        # 清理临时 state key
        state.pop("_data_info", None)

        return state

    # ==================================================================
    # plan.md 回写
    # ==================================================================

    def _update_and_save_plan(
        self, project_id: str, metrics: dict,
        experiment_plan: ExperimentPlan, analysis: dict
    ):
        """读取 plan.md，更新 checklist 标记，追加 Execution Results 表格，回写。"""
        plan_md = self.file_manager.load_text(
            project_id, "plan.md", subdir="experiments"
        )
        if not plan_md:
            self.logger.warning("plan.md not found, skipping checklist update")
            return

        updated_plan = self._update_plan_checklist(plan_md, metrics, experiment_plan, analysis)
        self.save_artifact(updated_plan, project_id, "plan.md", "experiments")
        self.logger.info("Updated plan.md with execution results")

    def _update_plan_checklist(
        self, plan_md: str, metrics: dict,
        experiment_plan: ExperimentPlan, analysis: dict
    ) -> str:
        """解析 plan.md checklist，标记完成/失败状态，追加结果表格。"""
        lines = plan_md.split("\n")
        updated_lines = []
        success_criteria = experiment_plan.get("success_criteria", {})

        # 判断最后一个 step（验证）是否通过
        validation_passed = self._check_success_criteria(metrics, success_criteria)

        for line in lines:
            # 匹配 checklist 行: - [ ] Step N: ...
            match = re.match(r'^(\s*-\s+)\[ \]\s+(.*)', line)
            if match:
                prefix = match.group(1)
                step_text = match.group(2)
                # 最后一步"validate"检查 success criteria
                if "validate" in step_text.lower() or "success criteria" in step_text.lower():
                    if validation_passed:
                        updated_lines.append(f"{prefix}[x] {step_text}")
                    else:
                        failure_details = self._format_criteria_failures(metrics, success_criteria)
                        updated_lines.append(f"{prefix}[ ] {step_text} — FAILED: {failure_details}")
                else:
                    # 非验证步骤全部标记为完成（agentic loop 执行了就算完成）
                    updated_lines.append(f"{prefix}[x] {step_text}")
            else:
                updated_lines.append(line)

        # 追加 Execution Results 表格
        results_section = self._build_execution_results_table(metrics, success_criteria)
        updated_lines.append("")
        updated_lines.append(results_section)

        return "\n".join(updated_lines)

    def _check_success_criteria(self, metrics: dict, success_criteria: dict) -> bool:
        """检查 metrics 是否满足所有 success criteria。"""
        for metric_name, threshold in success_criteria.items():
            value = metrics.get(metric_name)
            if value is None:
                return False
            # max_drawdown 是负值，threshold 可以是正值表示 < threshold
            if metric_name == "max_drawdown":
                if abs(value) > abs(threshold):
                    return False
            else:
                if value < threshold:
                    return False
        return True

    def _format_criteria_failures(self, metrics: dict, success_criteria: dict) -> str:
        """格式化失败的 criteria 信息。"""
        failures = []
        for metric_name, threshold in success_criteria.items():
            value = metrics.get(metric_name, 0)
            if metric_name == "max_drawdown":
                if abs(value) > abs(threshold):
                    failures.append(f"{metric_name}={abs(value)*100:.1f}% > {abs(threshold)*100:.1f}%")
            else:
                if value < threshold:
                    failures.append(f"{metric_name}={value:.2f} < {threshold}")
        return ", ".join(failures) if failures else "Unknown"

    def _build_execution_results_table(self, metrics: dict, success_criteria: dict) -> str:
        """构建 Execution Results 表格。"""
        lines = ["## Execution Results", "| Metric | Value | Target | Status |",
                 "|--------|-------|--------|--------|"]
        for metric_name, threshold in success_criteria.items():
            value = metrics.get(metric_name, 0)
            if metric_name == "max_drawdown":
                val_str = f"{abs(value)*100:.1f}%"
                tgt_str = f"< {abs(threshold)*100:.1f}%"
                status = "PASS" if abs(value) <= abs(threshold) else "FAIL"
            elif metric_name in ("total_trades",):
                val_str = str(int(value))
                tgt_str = f">= {int(threshold)}"
                status = "PASS" if value >= threshold else "FAIL"
            else:
                val_str = f"{value:.2f}"
                tgt_str = f"> {threshold}"
                status = "PASS" if value >= threshold else "FAIL"
            lines.append(f"| {metric_name} | {val_str} | {tgt_str} | {status} |")

        # 额外指标
        extra_metrics = ["total_return", "cagr", "volatility", "win_rate"]
        for m in extra_metrics:
            if m in metrics and m not in success_criteria:
                val = metrics[m]
                if m in ("total_return", "cagr", "volatility", "win_rate"):
                    lines.append(f"| {m} | {val*100:.1f}% | - | - |")
                else:
                    lines.append(f"| {m} | {val:.2f} | - | - |")

        return "\n".join(lines)

    def _identify_failed_steps(self, metrics: dict, experiment_plan: ExperimentPlan) -> List[str]:
        """识别失败的步骤。"""
        failed = []
        success_criteria = experiment_plan.get("success_criteria", {})
        for metric_name, threshold in success_criteria.items():
            value = metrics.get(metric_name, 0)
            if metric_name == "max_drawdown":
                if abs(value) > abs(threshold):
                    failed.append(f"Validate {metric_name}: {abs(value)*100:.1f}% > {abs(threshold)*100:.1f}%")
            else:
                if value < threshold:
                    failed.append(f"Validate {metric_name}: {value:.2f} < {threshold}")
        return failed

    # ==================================================================
    # experiment.md 构建
    # ==================================================================

    def _build_experiment_markdown(
        self, strategy_code: str, metrics: dict, analysis: dict
    ) -> str:
        """构建 experiment.md（代码 + 指标 + 分析）。"""
        metrics_lines = ["| Metric | Value |", "|--------|-------|"]
        for k, v in metrics.items():
            if isinstance(v, float):
                metrics_lines.append(f"| {k} | {v:.4f} |")
            else:
                metrics_lines.append(f"| {k} | {v} |")

        return f"""# Experiment Results

## Strategy Code
```python
{strategy_code}
```

## Performance Summary
{chr(10).join(metrics_lines)}

## Analysis
**Verdict**: {analysis.get("verdict", "N/A")}

{analysis.get("analysis", "")}

### Suggestions
{chr(10).join("- " + s for s in analysis.get("suggestions", []))}
"""

    # ==================================================================
    # 结果分析
    # ==================================================================

    def _analyze_results(self, metrics: dict, experiment_plan: ExperimentPlan, hypothesis: str) -> dict:
        """LLM 分析执行结果，返回 verdict + analysis + suggestions。"""
        validation_config = self.config.get("validation_metrics", {})
        metrics_text = "\n".join(f"- {k}: {v}" for k, v in metrics.items())

        prompt = f"""You are evaluating strategy execution results for a quantitative trading strategy.

## Hypothesis
{hypothesis}

## Success Criteria (from experiment plan)
{json.dumps(experiment_plan['success_criteria'], indent=2)}

## System Validation Thresholds
- Min Sharpe Ratio: {validation_config.get('min_sharpe_ratio', 0.5)}
- Min Trades: {validation_config.get('min_trades', 10)}
- Max Drawdown: {validation_config.get('max_drawdown_threshold', 0.5)}

## Execution Results
{metrics_text}

Evaluate whether these results validate the hypothesis. Consider:
1. Do the metrics meet the success criteria?
2. Do the metrics meet system validation thresholds?
3. Is the number of trades sufficient for statistical significance?
4. Are the results practically meaningful (not just technically passing)?

Output as JSON:
{{
  "verdict": "success" | "revise_plan" | "accept_partial",
  "analysis": "2-3 sentence evaluation explaining your verdict",
  "suggestions": ["specific improvement suggestion 1", "suggestion 2"]
}}

Verdict rules:
- "success": Meets plan criteria AND system thresholds AND statistically significant
- "accept_partial": Partially meets criteria, no clear improvement path
- "revise_plan": Does not meet criteria but has specific improvement directions"""

        try:
            result = self.call_llm(prompt=prompt, max_tokens=1500, temperature=0.2, response_format="json")
            if isinstance(result, dict) and "verdict" in result:
                if result["verdict"] not in ("success", "revise_plan", "accept_partial"):
                    result["verdict"] = "revise_plan"
                return result
        except Exception as e:
            self.logger.warning(f"Analysis LLM call failed: {e}")

        # 降级：硬编码检查
        sharpe = metrics.get("sharpe_ratio", 0)
        trades = metrics.get("total_trades", 0)
        dd = abs(metrics.get("max_drawdown", 0))
        min_sharpe = validation_config.get("min_sharpe_ratio", 0.5)
        min_trades = validation_config.get("min_trades", 10)
        max_dd = validation_config.get("max_drawdown_threshold", 0.5)

        if sharpe >= min_sharpe and trades >= min_trades and dd <= max_dd:
            return {"verdict": "success", "analysis": "Metrics meet all thresholds (fallback check)", "suggestions": []}
        return {
            "verdict": "revise_plan",
            "analysis": f"Fallback check: sharpe={sharpe:.2f} (min {min_sharpe}), trades={trades} (min {min_trades}), dd={dd:.2f} (max {max_dd})",
            "suggestions": ["Improve signal quality", "Adjust parameters"],
        }

    # ==================================================================
    # 结果映射
    # ==================================================================

    def _map_to_backtest_results(self, metrics: dict) -> BacktestResults:
        """将 metrics dict 映射到 BacktestResults TypedDict。"""
        return BacktestResults(
            total_return=float(metrics.get("total_return", 0.0)),
            sharpe_ratio=float(metrics.get("sharpe_ratio", 0.0)),
            max_drawdown=float(metrics.get("max_drawdown", 0.0)),
            total_trades=int(metrics.get("total_trades", 0)),
            cagr=float(metrics.get("cagr", 0.0)),
            sortino_ratio=float(metrics.get("sortino_ratio", 0.0)),
            calmar_ratio=float(metrics.get("calmar_ratio", 0.0)),
            win_rate=float(metrics.get("win_rate", 0.0)),
            profit_factor=float(metrics.get("profit_factor", 0.0)),
            avg_trade_duration=float(metrics.get("avg_trade_duration", 0.0)),
            volatility=float(metrics.get("volatility", 0.0)),
        )

    # ==================================================================
    # 辅助方法
    # ==================================================================

    def _describe_data(self, data_dict: dict, data_config: dict) -> str:
        """生成数据描述信息，供 prompt 使用。"""
        import pandas as pd
        lines = [
            f"Market: {data_config.get('market', 'us_equity')}",
            f"Interval: {data_config.get('interval', '1d')}",
            f"Symbols ({len(data_dict)}):",
        ]
        for symbol, df in data_dict.items():
            lines.append(
                f"  - {symbol}: {len(df)} rows, {df.index[0]} to {df.index[-1]}, "
                f"columns={list(df.columns)}"
            )
        return "\n".join(lines)

    def _collect_code_from_sandbox(self, sandbox: SandboxManager) -> str:
        """收集 sandbox 中的所有 .py 文件代码（排除 compute_metrics.py）。"""
        files = sandbox.list_files()
        code_parts = []
        for f in files:
            if f.endswith(".py") and f != "compute_metrics.py":
                content = sandbox.read_file(f)
                if not content.startswith("[ERROR]"):
                    code_parts.append(f"# === {f} ===\n{content}")
        return "\n\n".join(code_parts) if code_parts else ""

    def _generate_execution_summary(self, state: ResearchState) -> Dict[str, Any]:
        execution_status = state.get("validation_status", "unknown")

        log = f"Agentic experiment {execution_status.upper()}"
        learnings = []
        mistakes = []

        if execution_status in ("success", "partial"):
            rd = state["results_data"]
            learnings.append(f"Sharpe {rd['sharpe_ratio']:.2f}")
            learnings.append(f"Return {rd['total_return'] * 100:.2f}%")
            if execution_status == "partial":
                learnings.append("Accepted partial results from agentic loop")
        else:
            mistakes.append(f"Agentic experiment failed: {state.get('error_messages', 'Unknown')[:200]}")
            learnings.append("Need to review tool-use loop and sandbox execution")

        return {"log": log, "learnings": learnings, "mistakes": mistakes, "reflection": f"Status: {execution_status}"}
