"""
Experiment Agent - Code generation and backtest execution (REFACTORED)

Refactored to inherit from BaseAgent, eliminating infrastructure duplication.
Now focuses purely on business logic.

Responsible for:
- Generating trading strategy code from experiment plans
- Executing backtests on historical data
- Collecting and validating results
- Handling execution errors
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - agents/base_agent (BaseAgent基类继承),
#                   typing (类型系统), anthropic (Anthropic客户端),
#                   core/state (ResearchState, BacktestResults, ExperimentPlan),
#                   tools/file_manager (FileManager文件管理),
#                   tools/data_fetcher (FinancialDataFetcher金融数据获取),
#                   tools/backtest_engine (BacktestEngine回测引擎),
#                   pandas (数据处理)
# OUTPUT: 对外提供 - ExperimentAgent类,继承自BaseAgent,
#                   实现_execute()方法,输出策略代码、回测结果、性能指标
# POSITION: 系统地位 - Agent/Experiment (智能体层-实验智能体)
#                     继承BaseAgent,消除基础设施重复代码,
#                     Pipeline第三阶段,执行策略代码生成和回测
#
# 注意：当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import Dict, Any, Optional
from anthropic import Anthropic

from agents.base_agent import BaseAgent
from core.state import ResearchState, BacktestResults, ExperimentPlan
from tools.file_manager import FileManager
from tools.data_fetcher import FinancialDataFetcher
from tools.backtest_engine import BacktestEngine
import pandas as pd


class ExperimentAgent(BaseAgent):
    """
    Agent responsible for experiment execution and validation.

    Refactored to use BaseAgent for infrastructure.
    All memory, LLM calling, and output management handled by base class.
    """

    def __init__(
        self,
        llm: Anthropic,
        file_manager: FileManager,
        data_fetcher: FinancialDataFetcher,
        backtest_engine: BacktestEngine
    ):
        """
        Initialize Experiment Agent.

        Args:
            llm: Anthropic client instance
            file_manager: FileManager instance
            data_fetcher: Financial data fetcher
            backtest_engine: Backtest engine
        """
        # Initialize base agent (handles memory, LLM service, output manager)
        super().__init__(llm, file_manager, agent_name="experiment")

        # Agent-specific tools
        self.data_fetcher = data_fetcher
        self.backtest_engine = backtest_engine

    def _execute(self, state: ResearchState) -> ResearchState:
        """
        Execute experiment agent workflow (business logic only).

        All infrastructure (memory loading, logging, etc.) handled by BaseAgent.

        Args:
            state: Current research state

        Returns:
            Updated research state with experiment outputs
        """
        # Consult knowledge graph for implementation patterns
        related_tools = self.intelligence.knowledge_graph.search_knowledge(
            query="indicator strategy",
            node_type="tool"
        )

        if related_tools:
            self.logger.info(f"✓ Found {len(related_tools)} relevant tools/indicators in knowledge graph")

        # Step 1: Generate strategy code
        self.logger.info("Generating trading strategy code...")
        strategy_code = self.generate_strategy_code(
            experiment_plan=state["experiment_plan"],
            hypothesis=state["hypothesis"],
            methodology=state["methodology"]
        )
        state["experiment_code"] = strategy_code

        self.logger.info(f"✓ Generated strategy code ({len(strategy_code)} characters)")

        # Save code
        self.save_artifact(
            content=strategy_code,
            project_id=state["project_id"],
            filename="strategy.py",
            subdir="experiments",
            format="text"
        )

        # Step 2: Prepare data
        self.logger.info("Fetching historical data...")
        data = self.prepare_data(state["experiment_plan"])

        if data is None or data.empty:
            state["validation_status"] = "failed"
            state["error_messages"] = "Failed to fetch required data"
            self.logger.error("Data fetch failed")
            return state

        self.logger.info(f"✓ Fetched {len(data)} data points")

        # Step 3: Execute backtest
        self.logger.info("Running backtest...")
        try:
            results = self.execute_backtest(strategy_code, data)

            if results.get("success"):
                state["results_data"] = self.backtest_engine.format_results(results)
                state["execution_logs"] = results.get("execution_logs", "")
                state["validation_status"] = "success"

                self.logger.info(f"✓ Backtest completed successfully")
                self.logger.info(f"  Total Return: {results.get('total_return', 0)*100:.2f}%")
                self.logger.info(f"  Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
                self.logger.info(f"  Max Drawdown: {results.get('max_drawdown', 0)*100:.2f}%")

            else:
                state["validation_status"] = "failed"
                state["error_messages"] = results.get("error", "Unknown error")
                self.logger.error(f"Backtest failed: {results.get('error')}")

        except Exception as e:
            state["validation_status"] = "failed"
            state["error_messages"] = str(e)
            self.logger.error(f"Execution error: {e}")

        # Step 4: Validate results
        if state["validation_status"] == "success":
            validation_passed = self.validate_results(
                state["results_data"],
                state["experiment_plan"]
            )

            if not validation_passed:
                state["validation_status"] = "partial"
                self.logger.warning("Results did not meet all success criteria")

        # Save results
        if state["validation_status"] in ["success", "partial"]:
            self.save_artifact(
                content=dict(state["results_data"]),
                project_id=state["project_id"],
                filename="backtest_results.json",
                subdir="experiments",
                format="json"
            )

        # Save execution logs
        self.save_artifact(
            content=state.get("execution_logs", ""),
            project_id=state["project_id"],
            filename="execution_logs.txt",
            subdir="experiments",
            format="text"
        )

        # Record mistake if failed
        if state["validation_status"] == "failed":
            error_msg = state.get("error_messages", "Unknown")
            self.intelligence.memory_manager.record_mistake(
                mistake_id=f"M_EXP_{state['project_id'][:8]}",
                description="Backtest execution failed",
                severity=3,
                root_cause=error_msg[:100],
                prevention="Validate strategy code and data before execution",
                project_id=state["project_id"]
            )

        # Update knowledge graph with experiment insights
        if state["validation_status"] in ["success", "partial"]:
            findings = [
                f"Strategy type validated: {state['experiment_plan']['methodology'][:100]}",
                f"Performance metrics recorded"
            ]

            self.intelligence.knowledge_graph.update_knowledge_from_research(
                project_id=state["project_id"],
                findings=findings,
                llm=self.llm
            )

        return state

    def _generate_execution_summary(self, state: ResearchState) -> Dict[str, Any]:
        """
        Generate execution summary for daily log.

        Overrides base class to provide agent-specific summary.

        Args:
            state: Current research state

        Returns:
            Execution summary dict
        """
        strategy_code = state.get("experiment_code", "")
        execution_status = state.get("validation_status", "unknown")

        execution_log = f"""## Backtest Execution

### Status: {execution_status.upper()}

### Strategy Code
- Code length: {len(strategy_code)} characters
"""

        if execution_status == "success":
            execution_log += f"""
### Results
- Sharpe Ratio: {state['results_data']['sharpe_ratio']:.2f}
- Total Return: {state['results_data']['total_return']*100:.2f}%
- Max Drawdown: {state['results_data']['max_drawdown']*100:.2f}%
- Win Rate: {state['results_data'].get('win_rate', 0)*100:.2f}%
"""
        else:
            execution_log += f"""
### Results
- Error: {state.get('error_messages', 'Unknown error')}
"""

        learnings = []
        mistakes_encountered = []

        if execution_status == "success":
            learnings.append(f"Successfully executed backtest with Sharpe {state['results_data']['sharpe_ratio']:.2f}")
            learnings.append(f"Strategy achieved {state['results_data']['total_return']*100:.2f}% total return")
        else:
            mistakes_encountered.append(f"Backtest failed: {state.get('error_messages', 'Unknown')[:200]}")
            learnings.append("Need to review code generation and data preparation")

        reflection_text = f"""## Reflection on Execution

### What Went Well
"""
        if execution_status == "success":
            reflection_text += """- Code generation successful
- Backtest executed without errors
- Results validated and recorded
"""
        else:
            reflection_text += """- Identified execution issues
- Error messages captured for debugging
"""

        reflection_text += f"""
### Areas for Improvement
"""
        if execution_status == "success":
            reflection_text += """- Consider parameter optimization
- Test robustness with different data periods
"""
        else:
            reflection_text += """- Debug code generation process
- Validate data requirements
- Review strategy logic
"""

        return {
            "log": execution_log,
            "learnings": learnings,
            "mistakes": mistakes_encountered,
            "reflection": reflection_text
        }

    def generate_strategy_code(
        self,
        experiment_plan: ExperimentPlan,
        hypothesis: str,
        methodology: str
    ) -> str:
        """
        Generate Backtrader strategy code from experiment plan.

        Args:
            experiment_plan: Experiment plan
            hypothesis: Research hypothesis
            methodology: Detailed methodology

        Returns:
            Python code string
        """
        steps_text = "\n".join(f"{i+1}. {step}"
                              for i, step in enumerate(experiment_plan["implementation_steps"]))

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

        code = self.call_llm(
            prompt=prompt,
            max_tokens=4000,
            temperature=self.config.get("temperature", 0.2)
        )

        # Extract code from markdown if present
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        return code

    def prepare_data(self, experiment_plan: ExperimentPlan) -> Optional[pd.DataFrame]:
        """
        Fetch and prepare data for backtesting.

        Args:
            experiment_plan: Experiment plan with data requirements

        Returns:
            DataFrame with OHLCV data or None if failed
        """
        data_reqs = experiment_plan["data_requirements"]

        # Parse data requirements (simplified)
        # Default to SPY if no specific symbol mentioned
        symbol = "SPY"
        for req in data_reqs:
            req_lower = req.lower()
            if "spy" in req_lower:
                symbol = "SPY"
            elif "qqq" in req_lower:
                symbol = "QQQ"
            # Add more symbol detection logic as needed

        # Fetch data
        try:
            df = self.data_fetcher.fetch_single_symbol(
                symbol=symbol,
                start_date="2015-01-01",  # Default 10 years
                end_date=None,
                interval="1d"
            )

            if df is not None and not df.empty:
                # Ensure required columns
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                if all(col in df.columns for col in required_cols):
                    return df

        except Exception as e:
            self.logger.error(f"Error fetching data: {e}")

        return None

    def execute_backtest(
        self,
        strategy_code: str,
        data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Execute backtest with generated strategy code.

        Args:
            strategy_code: Python code defining strategy
            data: Historical OHLCV data

        Returns:
            Dictionary with results or error
        """
        # Validate code first
        if not self.backtest_engine.validate_strategy_code(strategy_code):
            return {
                "success": False,
                "error": "Strategy code has syntax errors"
            }

        # Execute strategy
        results = BacktestEngine.execute_strategy_code(
            code=strategy_code,
            data=data,
            initial_capital=100000
        )

        return results

    def validate_results(
        self,
        results: BacktestResults,
        experiment_plan: ExperimentPlan
    ) -> bool:
        """
        Validate that results meet success criteria.

        Args:
            results: Backtest results
            experiment_plan: Experiment plan with success criteria

        Returns:
            True if validation passed
        """
        criteria = experiment_plan["success_criteria"]
        validation_config = self.config.get("validation_metrics", {})

        # Check minimum thresholds
        checks = []

        # Sharpe ratio
        min_sharpe = criteria.get("sharpe_ratio", validation_config.get("min_sharpe_ratio", 0.5))
        checks.append(results["sharpe_ratio"] >= min_sharpe)

        # Max drawdown
        max_dd = criteria.get("max_drawdown", validation_config.get("max_drawdown_threshold", 0.5))
        checks.append(abs(results["max_drawdown"]) <= max_dd)

        # Minimum trades
        min_trades = validation_config.get("min_trades", 10)
        checks.append(results["total_trades"] >= min_trades)

        # All checks must pass
        return all(checks)

    def retry_on_failure(
        self,
        state: ResearchState,
        max_retries: int = 2
    ) -> ResearchState:
        """
        Retry experiment generation with modifications if it failed.

        Args:
            state: Current research state
            max_retries: Maximum retry attempts

        Returns:
            Updated state after retry
        """
        if state["iteration"] >= max_retries:
            self.logger.info("Max retries reached")
            return state

        self.logger.info(f"Retrying experiment (attempt {state['iteration'] + 1})...")

        # Increment iteration
        state["iteration"] += 1

        # Re-run experiment with modifications
        return self(state)
