"""
ExperimentAgent — Agentic Tool-Use 自治执行引擎

Pipeline 第三阶段：LLM 拥有 bash、文件读写、Python 执行、依赖安装等工具，
通过多轮 tool_use 循环自主迭代完成实验。
"""

# INPUT:  agents.base_agent (BaseAgent), core.state (ResearchState, ExperimentPlan, BacktestResults),
#         tools.file_manager (FileManager), market_data (DataFetcher),
#         agents.experiment.sandbox (SandboxManager),
#         agents.experiment.tools (TOOL_SCHEMAS, execute_tool),
#         agents.experiment.prompts (SYSTEM_PROMPT_TEMPLATE, build_task_prompt),
#         config.llm_config (get_model_name), json, logging
# OUTPUT: ExperimentAgent 类
# POSITION: Agent层 - 实验智能体，Pipeline 第三阶段
#           Agentic Tool-Use 循环执行引擎

from typing import Dict, Any
import json
import logging

from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import ResearchState, ExperimentPlan, BacktestResults
from tools.file_manager import FileManager
from market_data import DataFetcher
from config.llm_config import get_model_name

from agents.experiment.sandbox import SandboxManager
from agents.experiment.tools import TOOL_SCHEMAS, execute_tool
from agents.experiment.prompts import SYSTEM_PROMPT_TEMPLATE, build_task_prompt

logger = logging.getLogger("agents.experiment")


class ExperimentAgent(BaseAgent):
    """Agentic Tool-Use 自治实验执行引擎。"""

    def __init__(self, llm: Anthropic, file_manager: FileManager,
                 data_fetcher: DataFetcher):
        super().__init__(llm, file_manager, "experiment",
                         data_fetcher=data_fetcher)

    # ==================================================================
    # 主流程
    # ==================================================================

    def _execute(self, state: ResearchState) -> ResearchState:
        project_id = state["project_id"]
        hypothesis = state["hypothesis"]
        experiment_plan: ExperimentPlan = state["experiment_plan"]
        methodology = state["methodology"]
        max_retries = self.config.get("max_retries", 2)

        # Step 1: 数据准备
        self.logger.info("Preparing data...")
        data_config = self.file_manager.load_json(
            project_id, "data_config.json", subdir="experiments"
        ) or {}
        data_dict = self.data_fetcher.fetch(data_config)
        if not data_dict:
            state["validation_status"] = "failed"
            state["error_messages"] = "Failed to fetch required data"
            state["iteration"] = max_retries
            self.logger.error("Data fetch failed")
            return state

        data_info = self._describe_data(data_dict, data_config)
        total_rows = sum(len(df) for df in data_dict.values())
        self.logger.info(f"Data ready: {len(data_dict)} symbol(s), {total_rows} total rows")

        # Step 2: 创建 Sandbox
        experiment_id = f"{project_id}_exp"
        sandbox = SandboxManager(base_dir=self.config.get("sandbox_base_dir", "sandbox_workspaces"))
        sandbox.create(experiment_id)
        sandbox.inject_data(data_dict)
        sandbox.inject_helpers()
        self.logger.info(f"Sandbox created at: {sandbox.workdir}")

        # Step 3: Agentic Tool-Use 循环
        max_turns = self.config.get("max_agent_turns", 30)
        sandbox_timeout = self.config.get("sandbox_timeout", 300)

        submitted_results, execution_log = self._agentic_loop(
            hypothesis=hypothesis,
            experiment_plan=experiment_plan,
            methodology=methodology,
            data_info=data_info,
            sandbox=sandbox,
            max_turns=max_turns,
            sandbox_timeout=sandbox_timeout,
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
            else:
                # LLM 分析结果质量
                analysis = self._analyze_results(metrics, experiment_plan, hypothesis)
                verdict = analysis.get("verdict", "revise")
                self.logger.info(f"Analysis verdict: {verdict}")
                self.logger.info(f"  Total Return: {metrics.get('total_return', 0) * 100:.2f}%")
                self.logger.info(f"  Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
                self.logger.info(f"  Max Drawdown: {metrics.get('max_drawdown', 0) * 100:.2f}%")
                self.logger.info(f"  Total Trades: {metrics.get('total_trades', 0)}")

                state["results_data"] = self._map_to_backtest_results(metrics)
                state["experiment_code"] = self._collect_code_from_sandbox(sandbox)
                state["execution_logs"] = execution_log

                if verdict == "success":
                    state["validation_status"] = "success"
                elif verdict == "accept_partial":
                    state["validation_status"] = "partial"
                else:
                    state["validation_status"] = "partial"  # agentic loop 产出了结果，至少 partial

                self.save_artifact(
                    state["experiment_code"], project_id, "strategy.py", "experiments"
                )
                self.save_artifact(
                    dict(state["results_data"]), project_id, "backtest_results.json", "experiments"
                )
        else:
            state["validation_status"] = "failed"
            state["error_messages"] = "Agentic loop ended without submitting results"
            state["experiment_code"] = self._collect_code_from_sandbox(sandbox)
            state["execution_logs"] = execution_log

        # 保存执行日志
        self.save_artifact(execution_log, project_id, "execution_logs.txt", "experiments")

        # 防止 pipeline should_retry_experiment 触发无限循环
        state["iteration"] = max_retries

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

        return state

    # ==================================================================
    # Agentic Tool-Use 循环
    # ==================================================================

    def _agentic_loop(
        self,
        hypothesis: str,
        experiment_plan: ExperimentPlan,
        methodology: str,
        data_info: str,
        sandbox: SandboxManager,
        max_turns: int = 30,
        sandbox_timeout: int = 300,
    ) -> tuple[dict | None, str]:
        """多轮 tool_use 循环。返回 (submitted_results, execution_log)。"""

        # 构建 prompts
        agent_memory = self._system_prompt  # BaseAgent 在 __call__ 中已构建
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(agent_memory=agent_memory)

        task_prompt = build_task_prompt(
            hypothesis=hypothesis,
            methodology=methodology,
            implementation_steps=experiment_plan["implementation_steps"],
            success_criteria=experiment_plan["success_criteria"],
            data_info=data_info,
        )

        model_id = get_model_name(self.config.get("model", "sonnet"))
        messages = [{"role": "user", "content": task_prompt}]
        log_lines = []
        submitted_results = None

        for turn in range(1, max_turns + 1):
            self.logger.info(f"--- Agentic Turn {turn}/{max_turns} ---")
            log_lines.append(f"\n{'='*40} Turn {turn} {'='*40}")

            try:
                response = self.llm.messages.create(
                    model=model_id,
                    max_tokens=4096,
                    temperature=self.config.get("temperature", 0.2),
                    system=system_prompt,
                    tools=TOOL_SCHEMAS,
                    messages=messages,
                )
            except Exception as e:
                self.logger.error(f"LLM API call failed: {e}")
                log_lines.append(f"[ERROR] LLM API call failed: {e}")
                break

            # 记录 assistant response
            messages.append({"role": "assistant", "content": response.content})

            # 记录文本输出
            for block in response.content:
                if block.type == "text" and block.text.strip():
                    self.logger.info(f"LLM: {block.text[:200]}")
                    log_lines.append(f"[LLM] {block.text}")

            # 检查 stop reason
            if response.stop_reason == "end_turn":
                self.logger.info("LLM ended turn without tool use")
                log_lines.append("[INFO] LLM ended turn (no tool call)")
                break

            if response.stop_reason != "tool_use":
                self.logger.info(f"Unexpected stop_reason: {response.stop_reason}")
                log_lines.append(f"[INFO] Stop reason: {response.stop_reason}")
                break

            # 处理 tool_use blocks
            tool_results = []
            should_break = False

            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id

                self.logger.info(f"Tool: {tool_name}({json.dumps(tool_input)[:200]})")
                log_lines.append(f"[TOOL] {tool_name}: {json.dumps(tool_input)[:500]}")

                # submit_result 特殊处理：截获结果，结束循环
                if tool_name == "submit_result":
                    submitted_results = tool_input.get("results", tool_input)
                    self.logger.info(f"Results submitted: {json.dumps(submitted_results)[:300]}")
                    log_lines.append(f"[SUBMIT] {json.dumps(submitted_results)[:1000]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": "Results submitted successfully. Experiment complete.",
                    })
                    should_break = True
                else:
                    # 执行工具
                    result_str = execute_tool(tool_name, tool_input, sandbox, timeout=sandbox_timeout)
                    log_lines.append(f"[RESULT] {result_str[:500]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result_str,
                    })

            # 将 tool results 追加为 user message
            messages.append({"role": "user", "content": tool_results})

            if should_break:
                break

        else:
            self.logger.warning(f"Agentic loop reached max turns ({max_turns})")
            log_lines.append(f"[WARNING] Reached max turns ({max_turns})")

        execution_log = "\n".join(log_lines)
        return submitted_results, execution_log

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
  "verdict": "success" | "revise" | "accept_partial",
  "analysis": "2-3 sentence evaluation explaining your verdict",
  "suggestions": ["specific improvement suggestion 1", "suggestion 2"]
}}

Verdict rules:
- "success": Meets plan criteria AND system thresholds AND statistically significant
- "accept_partial": Partially meets criteria, no clear improvement path
- "revise": Does not meet criteria but has specific improvement directions"""

        try:
            result = self.call_llm(prompt=prompt, max_tokens=1500, temperature=0.2, response_format="json")
            if isinstance(result, dict) and "verdict" in result:
                if result["verdict"] not in ("success", "revise", "accept_partial"):
                    result["verdict"] = "revise"
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
            "verdict": "revise",
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
        code_len = len(state.get("experiment_code", ""))

        log = f"Agentic experiment {execution_status.upper()}: code={code_len} chars"
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
