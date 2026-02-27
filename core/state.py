"""
State management for the research automation system.

Defines the ResearchState TypedDict that flows through the entire pipeline.
"""

from typing import TypedDict, List, Dict, Optional, Literal
from datetime import datetime


class PaperMetadata(TypedDict):
    """Metadata for a research paper."""
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    published: str
    categories: List[str]
    url: str
    pdf_url: Optional[str]


class ExperimentPlan(TypedDict):
    """Structure for experiment plan."""
    objective: str
    methodology: str
    data_requirements: List[str]
    implementation_steps: List[str]
    success_criteria: Dict[str, float]
    estimated_runtime: str
    risk_factors: List[str]


class BacktestResults(TypedDict):
    """Structure for backtest results."""
    total_return: float
    cagr: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_duration: float
    volatility: float


class ResearchState(TypedDict):
    """
    Main state object that flows through the entire research pipeline.

    This state is passed between agents and persisted at each checkpoint.
    """
    # ============= Input =============
    research_direction: str          # e.g., "quantitative finance momentum strategies"
    project_id: str                  # Unique identifier: "2026-02-27_momentum_strategies"

    # ============= Ideation Agent Outputs =============
    papers_reviewed: List[PaperMetadata]
    literature_summary: str          # Comprehensive analysis of papers
    research_gaps: List[str]         # Identified opportunities
    hypothesis: str                  # Concrete, testable research question

    # ============= Planning Agent Outputs =============
    experiment_plan: ExperimentPlan
    methodology: str                 # Detailed methodology description
    expected_outcomes: str           # What results would validate hypothesis
    resource_requirements: Dict[str, str]  # Data sources, compute, etc.

    # ============= Experiment Agent Outputs =============
    experiment_code: str             # Generated Python code for strategy
    execution_logs: str              # Logs from backtest execution
    results_data: BacktestResults    # Performance metrics
    validation_status: Literal["success", "partial", "failed"]
    error_messages: Optional[str]    # Error details if validation failed

    # ============= Writing Agent Outputs =============
    report_draft: str                # Initial report draft
    final_report: str                # Polished final report
    report_path: str                 # Path to saved report file

    # ============= Metadata =============
    iteration: int                   # Retry counter for failed experiments
    timestamp: str                   # ISO format timestamp
    status: Literal[
        "initialized",
        "ideation",
        "planning",
        "experiment",
        "writing",
        "completed",
        "failed"
    ]
    error_log: Optional[str]         # Accumulated error messages

    # ============= Quality Control =============
    requires_human_review: bool      # Flag for human-in-the-loop
    review_notes: Optional[str]      # Notes from human reviewers


def create_initial_state(
    research_direction: str,
    project_id: Optional[str] = None
) -> ResearchState:
    """
    Create initial research state with defaults.

    Args:
        research_direction: The research focus area
        project_id: Optional project ID (auto-generated if not provided)

    Returns:
        Initialized ResearchState
    """
    if project_id is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        direction_slug = research_direction.lower().replace(" ", "_")[:30]
        project_id = f"{timestamp}_{direction_slug}"

    return ResearchState(
        # Input
        research_direction=research_direction,
        project_id=project_id,

        # Ideation outputs
        papers_reviewed=[],
        literature_summary="",
        research_gaps=[],
        hypothesis="",

        # Planning outputs
        experiment_plan=ExperimentPlan(
            objective="",
            methodology="",
            data_requirements=[],
            implementation_steps=[],
            success_criteria={},
            estimated_runtime="",
            risk_factors=[]
        ),
        methodology="",
        expected_outcomes="",
        resource_requirements={},

        # Experiment outputs
        experiment_code="",
        execution_logs="",
        results_data=BacktestResults(
            total_return=0.0,
            cagr=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            calmar_ratio=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            total_trades=0,
            avg_trade_duration=0.0,
            volatility=0.0
        ),
        validation_status="success",
        error_messages=None,

        # Writing outputs
        report_draft="",
        final_report="",
        report_path="",

        # Metadata
        iteration=0,
        timestamp=datetime.now().isoformat(),
        status="initialized",
        error_log=None,

        # Quality control
        requires_human_review=False,
        review_notes=None
    )
