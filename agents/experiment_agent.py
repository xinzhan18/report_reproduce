"""
Experiment Agent - Code generation and backtest execution.

Responsible for:
- Generating trading strategy code from experiment plans
- Executing backtests on historical data
- Collecting and validating results
- Handling execution errors
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - typing (类型系统), anthropic (Anthropic客户端),
#                   core/state (ResearchState, BacktestResults, ExperimentPlan),
#                   tools/file_manager (文件管理),
#                   tools/data_fetcher (金融数据获取),
#                   tools/backtest_engine (回测引擎),
#                   config/agent_config (Agent配置),
#                   core/agent_memory_manager (记忆管理),
#                   pandas (数据处理)
# OUTPUT: 对外提供 - ExperimentAgent类,实现execute()方法,
#                   输出策略代码、回测结果、性能指标
# POSITION: 系统地位 - Agent/Experiment (智能体层-实验智能体)
#                     Pipeline第三阶段,执行策略代码生成和回测
#
# 注意：当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import Dict, Any, Optional
from anthropic import Anthropic
from core.state import ResearchState, BacktestResults, ExperimentPlan
from tools.file_manager import FileManager
from tools.data_fetcher import FinancialDataFetcher
from tools.backtest_engine import BacktestEngine
from config.agent_config import get_agent_config
from config.llm_config import get_model_name
from core.agent_memory_manager import get_agent_memory_manager
from core.knowledge_graph import get_knowledge_graph
import pandas as pd


class ExperimentAgent:
    """
    Agent responsible for experiment execution and validation.
    Enhanced with persona, self-reflection, and knowledge graph capabilities.
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
        self.llm = llm
        self.file_manager = file_manager
        self.data_fetcher = data_fetcher
        self.backtest_engine = backtest_engine
        self.config = get_agent_config("experiment")
        self.model = get_model_name(self.config.get("model", "sonnet"))

        # Initialize agent intelligence components (NEW: Markdown-based memory system)
        self.memory_manager = get_agent_memory_manager("experiment")
        self.knowledge_graph = get_knowledge_graph()

    def _build_system_prompt(self, memories: Dict[str, str]) -> str:
        """
        Build system prompt with persona and memory context.

        Args:
            memories: Dictionary containing persona, memory, mistakes, and daily logs

        Returns:
            Complete system prompt string
        """
        return f"""# Your Identity and Persona

{memories['persona']}

---

# Your Long-term Knowledge and Insights

{memories['memory']}

---

# Mistakes to Avoid (IMPORTANT - Review Before Each Task)

{memories['mistakes']}

---

# Recent Context (Last 3 Days of Work)

{memories['daily_recent']}

---

You are now executing a new task. Use your persona, knowledge, and past learnings to perform at your best. Avoid repeating past mistakes.
"""

    def __call__(self, state: ResearchState) -> ResearchState:
        """
        Execute experiment agent workflow.

        Args:
            state: Current research state

        Returns:
            Updated research state with experiment outputs
        """
        print(f"\n{'='*60}")
        print(f"Experiment Agent: Executing backtest")
        print(f"{'='*60}\n")

        # Update status
        state["status"] = "experiment"

        # Load all memories (persona, memory, mistakes, daily logs)
        print("🧠 Loading agent memories...")
        self.memories = self.memory_manager.load_all_memories()
        self.system_prompt = self._build_system_prompt(self.memories)
        print(f"✓ Loaded persona, long-term memory, mistakes registry, and recent daily logs")

        # Consult knowledge graph for implementation patterns
        related_tools = self.knowledge_graph.search_knowledge(
            query="indicator strategy",
            node_type="tool"
        )

        if related_tools:
            print(f"✓ Found {len(related_tools)} relevant tools/indicators in knowledge graph")

        # Step 1: Generate strategy code
        print("Generating trading strategy code...")
        strategy_code = self.generate_strategy_code(
            experiment_plan=state["experiment_plan"],
            hypothesis=state["hypothesis"],
            methodology=state["methodology"]
        )
        state["experiment_code"] = strategy_code

        print(f"✓ Generated strategy code ({len(strategy_code)} characters)")

        # Save code
        self.file_manager.save_text(
            content=strategy_code,
            project_id=state["project_id"],
            filename="strategy.py",
            subdir="experiments"
        )

        # Step 2: Prepare data
        print("\nFetching historical data...")
        data = self.prepare_data(state["experiment_plan"])

        if data is None or data.empty:
            state["validation_status"] = "failed"
            state["error_messages"] = "Failed to fetch required data"
            print("✗ Data fetch failed")
            return state

        print(f"✓ Fetched {len(data)} data points")

        # Step 3: Execute backtest
        print("\nRunning backtest...")
        try:
            results = self.execute_backtest(strategy_code, data)

            if results.get("success"):
                state["results_data"] = self.backtest_engine.format_results(results)
                state["execution_logs"] = results.get("execution_logs", "")
                state["validation_status"] = "success"

                print(f"✓ Backtest completed successfully")
                print(f"  Total Return: {results.get('total_return', 0)*100:.2f}%")
                print(f"  Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
                print(f"  Max Drawdown: {results.get('max_drawdown', 0)*100:.2f}%")

            else:
                state["validation_status"] = "failed"
                state["error_messages"] = results.get("error", "Unknown error")
                print(f"✗ Backtest failed: {results.get('error')}")

        except Exception as e:
            state["validation_status"] = "failed"
            state["error_messages"] = str(e)
            print(f"✗ Execution error: {e}")

        # Step 4: Validate results
        if state["validation_status"] == "success":
            validation_passed = self.validate_results(
                state["results_data"],
                state["experiment_plan"]
            )

            if not validation_passed:
                state["validation_status"] = "partial"
                print("\n⚠ Results did not meet all success criteria")

        # Save results
        if state["validation_status"] in ["success", "partial"]:
            self.file_manager.save_json(
                data=dict(state["results_data"]),
                project_id=state["project_id"],
                filename="backtest_results.json",
                subdir="experiments"
            )

        # Save execution logs
        self.file_manager.save_text(
            content=state.get("execution_logs", ""),
            project_id=state["project_id"],
            filename="execution_logs.txt",
            subdir="experiments"
        )

        print(f"\n{'='*60}")
        print(f"Experiment Agent: Completed ({state['validation_status']})")
        print(f"{'='*60}\n")

        # Self-reflection on experiment execution
        execution_context = {
            "strategy_generated": bool(strategy_code),
            "data_fetched": data is not None,
            "validation_status": state["validation_status"]
        }

        results = {
            "success": state["validation_status"] == "success",
            "code_length": len(strategy_code),
            "data_points": len(data) if data is not None else 0,
            "backtest_executed": "results_data" in state
        }

        if state["validation_status"] == "success":
            results["sharpe_ratio"] = state["results_data"]["sharpe_ratio"]
            results["total_return"] = state["results_data"]["total_return"]

        # Save daily log with execution details
        execution_status = state["validation_status"]
        execution_log = f"""## Backtest Execution

### Status: {execution_status.upper()}

### Strategy Code
- Code length: {len(strategy_code)} characters
- Data points: {len(data) if data is not None else 0}

### Results
"""
        if execution_status == "success":
            execution_log += f"""- Sharpe Ratio: {state['results_data']['sharpe_ratio']:.2f}
- Total Return: {state['results_data']['total_return']*100:.2f}%
- Max Drawdown: {state['results_data']['max_drawdown']*100:.2f}%
- Win Rate: {state['results_data'].get('win_rate', 0)*100:.2f}%
"""
        else:
            execution_log += f"""- Error: {state.get('error_messages', 'Unknown error')}
"""

        learnings = []
        mistakes_encountered = []

        if execution_status == "success":
            learnings.append(f"Successfully executed backtest with Sharpe {state['results_data']['sharpe_ratio']:.2f}")
            learnings.append(f"Strategy achieved {state['results_data']['total_return']*100:.2f}% total return")
        else:
            mistakes_encountered.append(f"Backtest failed: {state.get('error_messages', 'Unknown')[:200]}")
            learnings.append("Need to review code generation and data preparation")

        reflection_text = f"""
## Reflection on Execution

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

        self.memory_manager.save_daily_log(
            project_id=state["project_id"],
            execution_log=execution_log,
            learnings=learnings,
            mistakes=mistakes_encountered,
            reflection=reflection_text
        )

        print(f"✓ Daily log saved with backtest results and learnings")

        # Record mistake if failed
        if execution_status == "failed" and mistakes_encountered:
            self.memory_manager.record_mistake(
                mistake_id=f"M_EXP_{state['project_id'][:8]}",
                description=f"Backtest execution failed",
                severity=3,
                root_cause=state.get('error_messages', 'Unknown')[:100],
                prevention="Validate strategy code and data before execution",
                project_id=state["project_id"]
            )

        # Update knowledge graph with experiment insights
        if execution_status in ["success", "partial"]:
            findings = [
                f"Strategy type validated: {state['experiment_plan']['methodology'][:100]}",
                f"Performance metrics recorded"
            ]

            self.knowledge_graph.update_knowledge_from_research(
                project_id=state["project_id"],
                findings=findings,
                llm=self.llm
            )

        return state

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

        response = self.llm.messages.create(
            model=self.model,
            max_tokens=4000,
            temperature=self.config.get("temperature", 0.2),
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )

        code = response.content[0].text

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
            print(f"Error fetching data: {e}")

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
            print("Max retries reached")
            return state

        print(f"\nRetrying experiment (attempt {state['iteration'] + 1})...")

        # Increment iteration
        state["iteration"] += 1

        # Re-run experiment with modifications
        # (In a full implementation, you'd analyze the error and adjust the prompt)

        return self(state)
