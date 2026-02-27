"""
State management for the research automation system.

Defines the ResearchState TypedDict that flows through the entire pipeline.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - typing (TypedDict, List, Dict类型系统), dataclasses (数据类),
#                   datetime (时间戳)
# OUTPUT: 对外提供 - ResearchState, PaperMetadata, ExperimentPlan, BacktestResults,
#                   RankedPaper, StructuredInsights, DeepInsights, ResearchGap,
#                   Hypothesis, ResearchSynthesis等状态类型定义
# POSITION: 系统地位 - Core/State (核心层-状态定义)
#                     整个系统的数据契约,所有Agent和Pipeline的状态流转基础
#
# 注意：当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import TypedDict, List, Dict, Optional, Literal, Any
from dataclasses import dataclass, field
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


# ============= Enhanced Literature Analysis Structures =============

@dataclass
class RankedPaper:
    """
    Paper with relevance ranking from quick filtering stage.

    Used in Stage 1 of three-stage analysis.
    """
    paper: PaperMetadata
    relevance_score: float  # 0.0 to 1.0
    relevance_reasons: List[str]
    should_analyze_deep: bool = field(default=False)


@dataclass
class StructuredInsights:
    """
    Structured analysis results from paper sections.

    Used in Stage 2 of three-stage analysis.
    Extracted from PDF sections (methodology, results, etc.)
    """
    paper_id: str
    title: str
    sections: Dict[str, str]  # section_name -> extracted_text

    # Structured extracted information
    key_innovations: List[str] = field(default_factory=list)
    methodology_summary: str = ""
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)
    research_gaps_mentioned: List[str] = field(default_factory=list)

    # Quality scores
    innovation_score: float = 0.0  # 0-1
    practical_feasibility: float = 0.0  # 0-1


@dataclass
class DeepInsights:
    """
    Deep analysis results from full paper reading.

    Used in Stage 3 of three-stage analysis.
    Includes complete information extraction for reproduction.
    """
    paper_id: str

    # Complete technical extraction
    equations: List[str] = field(default_factory=list)
    algorithms: List[str] = field(default_factory=list)
    code_patterns: List[str] = field(default_factory=list)

    # Core contributions and insights
    core_contribution: str = ""
    implementation_details: str = ""
    parameter_settings: Dict[str, Any] = field(default_factory=dict)
    experimental_setup: str = ""

    # Feasibility assessment
    data_requirements: List[str] = field(default_factory=list)
    computational_requirements: str = ""
    reproducibility_score: float = 0.0  # 0-1


@dataclass
class ResearchGap:
    """
    Identified research gap with supporting evidence.
    """
    description: str
    severity: str  # "major", "minor"
    evidence: List[str]  # References to papers/sections
    opportunity_score: float  # 0-1


@dataclass
class Hypothesis:
    """
    Research hypothesis with methodology and evidence.

    Enhanced with deeper supporting information from literature analysis.
    """
    statement: str
    rationale: str
    supporting_evidence: List[str]  # References to specific papers/sections
    feasibility_score: float  # 0-1
    novelty_score: float  # 0-1


@dataclass
class ResearchSynthesis:
    """
    Comprehensive synthesis across all analyzed papers.

    Final output of three-stage literature analysis.
    """
    literature_summary: str  # Comprehensive literature review

    # Thematic organization
    methodology_patterns: List[str] = field(default_factory=list)
    performance_trends: List[str] = field(default_factory=list)
    common_limitations: List[str] = field(default_factory=list)

    # Research opportunities
    identified_gaps: List[ResearchGap] = field(default_factory=list)
    hypotheses: List[Hypothesis] = field(default_factory=list)


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
