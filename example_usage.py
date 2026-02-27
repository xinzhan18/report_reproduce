"""
Example usage of the Research Automation Agent System.

This script demonstrates how to use the system for automated research.
"""

from core.pipeline import run_research_pipeline
from scheduler.pipeline_runner import PipelineRunner
from scheduler.daily_scan import DailyScanner


def example_single_research():
    """
    Example: Run a single research project.
    """
    print("Example 1: Running a single research project\n")

    # Define research direction
    research_direction = "momentum strategies in equity markets"

    # Run the complete pipeline
    result = run_research_pipeline(research_direction)

    # Check results
    print(f"\nResearch completed!")
    print(f"  Status: {result['status']}")
    print(f"  Project ID: {result['project_id']}")

    if result['status'] == 'completed':
        print(f"  Hypothesis: {result['hypothesis'][:100]}...")
        print(f"  Sharpe Ratio: {result['results_data']['sharpe_ratio']:.2f}")
        print(f"  Total Return: {result['results_data']['total_return']*100:.1f}%")
        print(f"  Report: {result['report_path']}")


def example_pipeline_runner():
    """
    Example: Use PipelineRunner for more control.
    """
    print("\nExample 2: Using PipelineRunner\n")

    runner = PipelineRunner()

    # Run a project
    result = runner.run_project(
        research_direction="mean reversion strategies in currency markets"
    )

    # List all projects
    projects = runner.list_projects()
    print(f"Total projects: {len(projects)}")

    # Get statistics
    stats = runner.get_statistics()
    print(f"\nStatistics:")
    print(f"  Completed: {stats['completed']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")

    # Resume a project (if needed)
    # result = runner.resume_project("2026-02-27_some_project")


def example_daily_scanner():
    """
    Example: Run the daily paper scanner.
    """
    print("\nExample 3: Daily Paper Scanner\n")

    scanner = DailyScanner()

    # Run scan once
    result = scanner.run_once()

    print(f"Scan Results:")
    print(f"  Papers found: {result['papers_found']}")
    print(f"  Relevant papers: {result.get('relevant_papers', 0)}")
    print(f"  Opportunities: {result.get('opportunities_identified', 0)}")
    print(f"  Pipelines triggered: {result['pipelines_triggered']}")

    # To run continuously (uncomment):
    # scanner.run_scheduler(scan_time="08:00")  # Daily at 8 AM


def example_custom_workflow():
    """
    Example: Custom workflow with individual agents.
    """
    print("\nExample 4: Custom Workflow\n")

    from anthropic import Anthropic
    from tools.paper_fetcher import PaperFetcher
    from tools.file_manager import FileManager
    from agents.ideation_agent import IdeationAgent
    from core.state import create_initial_state
    from config.llm_config import get_llm

    # Initialize components
    llm = get_llm()
    paper_fetcher = PaperFetcher()
    file_manager = FileManager()

    # Create initial state
    state = create_initial_state("factor models in quantitative finance")

    # Run just the ideation agent
    ideation_agent = IdeationAgent(llm, paper_fetcher, file_manager)
    state = ideation_agent(state)

    print(f"Hypothesis generated: {state['hypothesis'][:150]}...")
    print(f"Papers reviewed: {len(state['papers_reviewed'])}")
    print(f"Research gaps: {len(state['research_gaps'])}")


def main():
    """
    Main entry point - choose which example to run.
    """
    print("="*70)
    print("Research Automation Agent System - Examples")
    print("="*70)

    # Uncomment the example you want to run:

    # Example 1: Simple single research project
    # example_single_research()

    # Example 2: Using PipelineRunner
    # example_pipeline_runner()

    # Example 3: Daily scanner
    example_daily_scanner()

    # Example 4: Custom workflow
    # example_custom_workflow()

    print("\n" + "="*70)
    print("Example completed!")
    print("="*70)


if __name__ == "__main__":
    main()
