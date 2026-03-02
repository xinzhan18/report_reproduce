"""
LangGraph pipeline orchestration for research automation.

Connects all four agents in a workflow with error handling, checkpointing,
and experiment→planning feedback loop driven by ExperimentFeedback.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - langgraph (Pipeline框架), typing (类型系统),
#                   core/state (ResearchState, ExperimentFeedback 状态定义),
#                   agents (四个Agent类),
#                   tools (PaperFetcher, FileManager, PDFReader),
#                   market_data (LocalDataLoader),
#                   config/llm_config (LLM客户端),
#                   core/persistence (Checkpointer)
# OUTPUT: 对外提供 - create_research_pipeline()函数,返回LangGraph编排器,
#                   should_continue_after_experiment()条件路由函数
# POSITION: 系统地位 - Core/Pipeline (核心层-编排器)
#                     系统的控制流中枢,编排四个Agent的执行顺序
#                     支持 experiment→planning 反馈回路（最多 2 次迭代）
#
# 注意：当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from core.state import ResearchState, create_initial_state
from agents.ideation import IdeationAgent
from agents.planning import PlanningAgent
from agents.experiment import ExperimentAgent
from agents.writing import WritingAgent
from tools.paper_fetcher import PaperFetcher
from tools.file_manager import FileManager
from market_data import LocalDataLoader
from tools.pdf_reader import PDFReader
from config.llm_config import get_llm
from core.persistence import get_checkpointer


def should_continue_after_experiment(state: ResearchState) -> str:
    """
    Conditional routing after experiment based on ExperimentFeedback.

    Routes:
    - "success" / "partial" → writing
    - "revise_plan" (iteration < 2) → planning (feedback loop)
    - otherwise → failed

    Args:
        state: Current research state

    Returns:
        Next node name
    """
    feedback = state.get("experiment_feedback")
    if not feedback:
        return "failed"

    verdict = feedback.get("verdict", "failed")

    if verdict == "success":
        return "writing"
    elif verdict == "partial":
        return "writing"
    elif verdict == "revise_plan" and state.get("iteration", 0) < 2:
        return "planning"
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
    data_loader = LocalDataLoader()

    # Initialize agents
    pdf_reader = PDFReader()
    ideation_agent = IdeationAgent(llm, paper_fetcher, file_manager, pdf_reader=pdf_reader)
    planning_agent = PlanningAgent(llm, file_manager)
    experiment_agent = ExperimentAgent(llm, file_manager, data_loader)
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

    # Linear flow: ideation → planning → experiment
    workflow.add_edge("ideation", "planning")
    workflow.add_edge("planning", "experiment")

    # Conditional routing after experiment (feedback loop)
    workflow.add_conditional_edges(
        "experiment",
        should_continue_after_experiment,
        {
            "writing": "writing",        # Success/partial → writing
            "planning": "planning",      # Revise plan → feedback loop
            "failed": "failed"           # Failed → error handler
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
        rd = result['results_data']
        print(f"  IC Mean: {rd['ic_mean']:.4f}, ICIR: {rd['icir']:.4f}")
        print(f"  Rank IC: {rd['rank_ic_mean']:.4f}, L/S Return: {rd['long_short_return']:.4f}")
    else:
        print(f"\n✗ Research failed: {result.get('error_messages', 'Unknown error')}")


if __name__ == "__main__":
    main()
