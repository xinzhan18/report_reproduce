"""
LangGraph pipeline orchestration for research automation.

Connects all four agents in a workflow with error handling and checkpointing.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - langgraph (Pipeline框架), typing (类型系统),
#                   core/state (ResearchState状态定义),
#                   agents (四个Agent类),
#                   tools (PaperFetcher, FileManager, DataFetcher, BacktestEngine),
#                   config/llm_config (LLM客户端),
#                   core/persistence (Checkpointer)
# OUTPUT: 对外提供 - create_research_pipeline()函数,返回LangGraph编排器,
#                   should_retry_experiment()条件路由函数
# POSITION: 系统地位 - Core/Pipeline (核心层-编排器)
#                     系统的控制流中枢,编排四个Agent的执行顺序
#
# 注意：当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from core.state import ResearchState, create_initial_state
from agents.ideation_agent import IdeationAgent
from agents.planning_agent import PlanningAgent
from agents.experiment_agent import ExperimentAgent
from agents.writing_agent import WritingAgent
from tools.paper_fetcher import PaperFetcher
from tools.file_manager import FileManager
from tools.data_fetcher import FinancialDataFetcher
from tools.backtest_engine import BacktestEngine
from config.llm_config import get_llm
from core.persistence import get_checkpointer


def should_retry_experiment(state: ResearchState) -> str:
    """
    Conditional routing: retry experiment if failed and under max retries.

    Args:
        state: Current research state

    Returns:
        Next node name
    """
    if state["validation_status"] == "failed" and state["iteration"] < 2:
        return "experiment"
    elif state["validation_status"] in ["success", "partial"]:
        return "writing"
    else:
        return "failed"


def create_research_pipeline():
    """
    Create the research automation pipeline with all agents.

    Returns:
        Compiled LangGraph workflow
    """
    # Initialize tools
    llm = get_llm("sonnet")
    paper_fetcher = PaperFetcher()
    file_manager = FileManager()
    data_fetcher = FinancialDataFetcher()
    backtest_engine = BacktestEngine()

    # Initialize agents
    ideation_agent = IdeationAgent(llm, paper_fetcher, file_manager)
    planning_agent = PlanningAgent(llm, file_manager)
    experiment_agent = ExperimentAgent(llm, file_manager, data_fetcher, backtest_engine)
    writing_agent = WritingAgent(llm, file_manager)

    # Create graph
    workflow = StateGraph(ResearchState)

    # Add nodes (agents)
    workflow.add_node("ideation", ideation_agent)
    workflow.add_node("planning", planning_agent)
    workflow.add_node("experiment", experiment_agent)
    workflow.add_node("writing", writing_agent)

    # Add error handler node
    def handle_failure(state: ResearchState) -> ResearchState:
        """Handle pipeline failure."""
        print(f"\n{'='*60}")
        print(f"PIPELINE FAILED")
        print(f"Error: {state.get('error_messages', 'Unknown error')}")
        print(f"{'='*60}\n")
        state["status"] = "failed"
        return state

    workflow.add_node("failed", handle_failure)

    # Define edges (workflow)
    workflow.set_entry_point("ideation")

    # Linear flow for main pipeline
    workflow.add_edge("ideation", "planning")
    workflow.add_edge("planning", "experiment")

    # Conditional routing after experiment
    workflow.add_conditional_edges(
        "experiment",
        should_retry_experiment,
        {
            "experiment": "experiment",  # Retry
            "writing": "writing",        # Success - continue to writing
            "failed": "failed"           # Failed - go to error handler
        }
    )

    # Writing leads to end
    workflow.add_edge("writing", END)
    workflow.add_edge("failed", END)

    # Compile with checkpointing
    checkpointer = get_checkpointer()
    compiled = workflow.compile(checkpointer=checkpointer)

    return compiled


def run_research_pipeline(
    research_direction: str,
    project_id: str = None
) -> ResearchState:
    """
    Run the complete research pipeline.

    Args:
        research_direction: Research focus area
        project_id: Optional project ID (auto-generated if not provided)

    Returns:
        Final research state
    """
    from core.persistence import create_config
    from tools.file_manager import FileManager

    # Create initial state
    initial_state = create_initial_state(research_direction, project_id)

    # Create project structure
    file_manager = FileManager()
    file_manager.create_project_structure(initial_state["project_id"])

    print(f"\n{'='*80}")
    print(f"RESEARCH AUTOMATION PIPELINE")
    print(f"Project ID: {initial_state['project_id']}")
    print(f"Research Direction: {research_direction}")
    print(f"{'='*80}\n")

    # Create pipeline
    pipeline = create_research_pipeline()

    # Create config for this project
    config = create_config(initial_state["project_id"])

    # Run pipeline
    try:
        final_state = pipeline.invoke(initial_state, config)

        print(f"\n{'='*80}")
        print(f"PIPELINE COMPLETED")
        print(f"Status: {final_state['status']}")
        if final_state['status'] == 'completed':
            print(f"Report: {final_state.get('report_path', 'N/A')}")
        print(f"{'='*80}\n")

        return final_state

    except Exception as e:
        print(f"\n{'='*80}")
        print(f"PIPELINE ERROR: {e}")
        print(f"{'='*80}\n")
        raise


def resume_research_pipeline(project_id: str) -> ResearchState:
    """
    Resume a research pipeline from checkpoint.

    Args:
        project_id: Project ID to resume

    Returns:
        Final research state
    """
    from core.persistence import create_config, get_project_state, get_checkpointer

    checkpointer = get_checkpointer()
    state = get_project_state(checkpointer, project_id)

    if state is None:
        raise ValueError(f"No checkpoint found for project {project_id}")

    print(f"\n{'='*80}")
    print(f"RESUMING RESEARCH PIPELINE")
    print(f"Project ID: {project_id}")
    print(f"Last Status: {state.get('status', 'unknown')}")
    print(f"{'='*80}\n")

    # Create pipeline
    pipeline = create_research_pipeline()

    # Create config
    config = create_config(project_id)

    # Resume pipeline
    try:
        final_state = pipeline.invoke(state, config)

        print(f"\n{'='*80}")
        print(f"PIPELINE COMPLETED")
        print(f"Status: {final_state['status']}")
        print(f"{'='*80}\n")

        return final_state

    except Exception as e:
        print(f"\n{'='*80}")
        print(f"PIPELINE ERROR: {e}")
        print(f"{'='*80}\n")
        raise


# Example usage function
def main():
    """Example usage of the research pipeline."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m core.pipeline <research_direction>")
        sys.exit(1)

    research_direction = " ".join(sys.argv[1:])

    # Run pipeline
    result = run_research_pipeline(research_direction)

    # Print summary
    if result["status"] == "completed":
        print(f"\n✓ Research completed successfully!")
        print(f"  Hypothesis: {result['hypothesis'][:100]}...")
        print(f"  Sharpe Ratio: {result['results_data']['sharpe_ratio']:.2f}")
        print(f"  Report: {result['report_path']}")
    else:
        print(f"\n✗ Research failed: {result.get('error_messages', 'Unknown error')}")


if __name__ == "__main__":
    main()
