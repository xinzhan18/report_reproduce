"""
Experiment Agent - 策略代码生成与回测执行

Pipeline 第三阶段：生成交易策略代码、执行回测、验证结果。
"""

# INPUT:  agents.base_agent (BaseAgent), core.state, tools.file_manager,
#         tools.data_fetcher, tools.backtest_engine, pandas
# OUTPUT: ExperimentAgent 类
# POSITION: Agent层 - 实验智能体，Pipeline 第三阶段

from typing import Dict, Any, Optional
from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import ResearchState, BacktestResults, ExperimentPlan
from tools.file_manager import FileManager
from tools.data_fetcher import FinancialDataFetcher
from tools.backtest_engine import BacktestEngine
import pandas as pd


class ExperimentAgent(BaseAgent):
    """策略代码生成与回测执行 Agent。"""

    def __init__(self, llm: Anthropic, file_manager: FileManager,
                 data_fetcher: FinancialDataFetcher, backtest_engine: BacktestEngine):
        super().__init__(llm, file_manager, "experiment",
                         data_fetcher=data_fetcher, backtest_engine=backtest_engine)

    def _execute(self, state: ResearchState) -> ResearchState:
        # 查询知识图谱
        related_tools = self.knowledge_graph.search_knowledge(query="indicator strategy", node_type="tool")
        if related_tools:
            self.logger.info(f"Found {len(related_tools)} relevant tools/indicators in knowledge graph")

        # Step 1: 生成策略代码
        self.logger.info("Generating trading strategy code...")
        strategy_code = self.generate_strategy_code(
            experiment_plan=state["experiment_plan"],
            hypothesis=state["hypothesis"],
            methodology=state["methodology"],
        )
        state["experiment_code"] = strategy_code
        self.logger.info(f"Generated strategy code ({len(strategy_code)} characters)")

        self.save_artifact(
            content=strategy_code,
            project_id=state["project_id"],
            filename="strategy.py",
            subdir="experiments",
        )

        # Step 2: 获取数据
        self.logger.info("Fetching historical data...")
        data = self.prepare_data(state["experiment_plan"])
        if data is None or data.empty:
            state["validation_status"] = "failed"
            state["error_messages"] = "Failed to fetch required data"
            self.logger.error("Data fetch failed")
            return state

        self.logger.info(f"Fetched {len(data)} data points")

        # Step 3: 执行回测
        self.logger.info("Running backtest...")
        try:
            results = self.execute_backtest(strategy_code, data)
            if results.get("success"):
                state["results_data"] = self.backtest_engine.format_results(results)
                state["execution_logs"] = results.get("execution_logs", "")
                state["validation_status"] = "success"
                self.logger.info(f"Backtest completed successfully")
                self.logger.info(f"  Total Return: {results.get('total_return', 0) * 100:.2f}%")
                self.logger.info(f"  Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
                self.logger.info(f"  Max Drawdown: {results.get('max_drawdown', 0) * 100:.2f}%")
            else:
                state["validation_status"] = "failed"
                state["error_messages"] = results.get("error", "Unknown error")
                self.logger.error(f"Backtest failed: {results.get('error')}")
        except Exception as e:
            state["validation_status"] = "failed"
            state["error_messages"] = str(e)
            self.logger.error(f"Execution error: {e}")

        # Step 4: 验证结果
        if state["validation_status"] == "success":
            validation_passed = self.validate_results(state["results_data"], state["experiment_plan"])
            if not validation_passed:
                state["validation_status"] = "partial"
                self.logger.warning("Results did not meet all success criteria")

        # 保存结果
        if state["validation_status"] in ["success", "partial"]:
            self.save_artifact(
                content=dict(state["results_data"]),
                project_id=state["project_id"],
                filename="backtest_results.json",
                subdir="experiments",
            )

        self.save_artifact(
            content=state.get("execution_logs", ""),
            project_id=state["project_id"],
            filename="execution_logs.txt",
            subdir="experiments",
        )

        # 记录错误
        if state["validation_status"] == "failed":
            error_msg = state.get("error_messages", "Unknown")
            self.memory.record_mistake(
                description="Backtest execution failed",
                severity=3,
                root_cause=error_msg[:100],
                prevention="Validate strategy code and data before execution",
                project_id=state["project_id"],
            )

        # 更新知识图谱
        if state["validation_status"] in ["success", "partial"]:
            findings = [
                f"Strategy type validated: {state['experiment_plan']['methodology'][:100]}",
                f"Performance metrics recorded",
            ]
            self.knowledge_graph.update_knowledge_from_research(
                project_id=state["project_id"], findings=findings, llm=self.llm
            )

        return state

    def _generate_execution_summary(self, state: ResearchState) -> Dict[str, Any]:
        strategy_code = state.get("experiment_code", "")
        execution_status = state.get("validation_status", "unknown")

        log = f"Backtest {execution_status.upper()}: code={len(strategy_code)} chars"
        learnings = []
        mistakes = []

        if execution_status == "success":
            learnings.append(f"Sharpe {state['results_data']['sharpe_ratio']:.2f}")
            learnings.append(f"Return {state['results_data']['total_return'] * 100:.2f}%")
        else:
            mistakes.append(f"Backtest failed: {state.get('error_messages', 'Unknown')[:200]}")
            learnings.append("Need to review code generation and data preparation")

        return {"log": log, "learnings": learnings, "mistakes": mistakes, "reflection": f"Status: {execution_status}"}

    def generate_strategy_code(self, experiment_plan: ExperimentPlan, hypothesis: str, methodology: str) -> str:
        """生成 Backtrader 策略代码。"""
        steps_text = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(experiment_plan["implementation_steps"]))

        prompt = f"""You are an expert in quantitative finance and Python programming.
Generate a complete Backtrader strategy implementation based on the following specification.

Hypothesis:
{hypothesis}

Methodology:
{methodology}

Implementation Steps:
{steps_text}

Success Criteria:
{experiment_plan['success_criteria']}

Generate complete, production-ready Python code that:
1. Imports necessary libraries (backtrader, pandas, numpy)
2. Defines a Strategy class inheriting from bt.Strategy
3. Implements the strategy logic described in the methodology
4. Includes proper position sizing and risk management
5. Has clear comments explaining the logic
6. Follows best practices for backtesting

Requirements:
- Use bt.indicators for technical indicators
- Implement clear entry and exit logic
- Handle edge cases (first data points, positions, etc.)
- Keep it simple and maintainable
- No placeholder code - fully functional implementation

Output ONLY the Python code, no explanations. The code will be executed directly."""

        code = self.call_llm(prompt=prompt, max_tokens=4000, temperature=self.config.get("temperature", 0.2))

        # 提取代码块
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        return code

    def prepare_data(self, experiment_plan: ExperimentPlan) -> Optional[pd.DataFrame]:
        """获取并准备回测数据。"""
        data_reqs = experiment_plan["data_requirements"]

        symbol = "SPY"
        for req in data_reqs:
            req_lower = req.lower()
            if "spy" in req_lower:
                symbol = "SPY"
            elif "qqq" in req_lower:
                symbol = "QQQ"

        try:
            df = self.data_fetcher.fetch_single_symbol(
                symbol=symbol, start_date="2015-01-01", end_date=None, interval="1d"
            )
            if df is not None and not df.empty:
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                if all(col in df.columns for col in required_cols):
                    return df
        except Exception as e:
            self.logger.error(f"Error fetching data: {e}")

        return None

    def execute_backtest(self, strategy_code: str, data: pd.DataFrame) -> Dict[str, Any]:
        """执行回测。"""
        if not self.backtest_engine.validate_strategy_code(strategy_code):
            return {"success": False, "error": "Strategy code has syntax errors"}

        return BacktestEngine.execute_strategy_code(
            code=strategy_code, data=data, initial_capital=100000
        )

    def validate_results(self, results: BacktestResults, experiment_plan: ExperimentPlan) -> bool:
        """验证结果是否满足成功标准。"""
        criteria = experiment_plan["success_criteria"]
        validation_config = self.config.get("validation_metrics", {})

        checks = []
        min_sharpe = criteria.get("sharpe_ratio", validation_config.get("min_sharpe_ratio", 0.5))
        checks.append(results["sharpe_ratio"] >= min_sharpe)

        max_dd = criteria.get("max_drawdown", validation_config.get("max_drawdown_threshold", 0.5))
        checks.append(abs(results["max_drawdown"]) <= max_dd)

        min_trades = validation_config.get("min_trades", 10)
        checks.append(results["total_trades"] >= min_trades)

        return all(checks)

    def retry_on_failure(self, state: ResearchState, max_retries: int = 2) -> ResearchState:
        """失败时重试。"""
        if state["iteration"] >= max_retries:
            self.logger.info("Max retries reached")
            return state
        self.logger.info(f"Retrying experiment (attempt {state['iteration'] + 1})...")
        state["iteration"] += 1
        return self(state)
