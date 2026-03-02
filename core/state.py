"""
State management for the research automation system.

Defines the ResearchState TypedDict that flows through the entire pipeline.
Markdown-driven architecture: Agents exchange context via .md files, State holds
only routing signals and minimal shared data.

量化因子研究系统：FactorPlan + FactorResults 替代原有 ExperimentPlan + BacktestResults。
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - typing (TypedDict, List, Dict类型系统), dataclasses (数据类),
#                   datetime (时间戳)
# OUTPUT: 对外提供 - ResearchState, PaperMetadata, FactorPlan, FactorResults,
#                   ExperimentFeedback, RankedPaper, StructuredInsights, DeepInsights,
#                   ResearchGap, Hypothesis, ResearchSynthesis等状态类型定义
# POSITION: 系统地位 - Core/State (核心层-状态定义)
#                     整个系统的数据契约,所有Agent和Pipeline的状态流转基础
#                     Markdown 驱动架构：State 精简为路由信号，大块数据在 .md 文件中流转
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


class FactorPlan(TypedDict):
    """Structure for factor research plan."""
    objective: str
    factor_description: str       # 因子衡量什么
    factor_formula: str           # 公式或伪代码
    data_requirements: List[str]
    implementation_steps: List[str]
    test_universe: str            # "a_shares" | "crypto"
    test_period: str              # "2018-01-01 to 2024-12-31"
    rebalance_frequency: str      # "daily" | "weekly" | "monthly"
    success_criteria: Dict[str, float]  # {"ic_mean": 0.03, "icir": 0.5}
    risk_factors: List[str]
    estimated_runtime: str


class FactorResults(TypedDict):
    """Structure for factor evaluation results."""
    ic_mean: float              # Mean IC
    ic_std: float               # IC 标准差
    icir: float                 # IC / IC_std
    rank_ic_mean: float         # Mean Rank IC
    rank_icir: float            # Rank ICIR
    turnover_mean: float        # 平均换手率
    long_short_return: float    # 多空年化收益
    top_group_return: float     # 顶层分组年化收益
    bottom_group_return: float  # 底层分组年化收益
    monotonicity_score: float   # 分层单调性 (0-1)
    factor_coverage: float      # 因子覆盖率


class ExperimentFeedback(TypedDict):
    """Feedback from ExperimentAgent for pipeline routing.

    Used by should_continue_after_experiment() to decide:
    - "success" / "partial" → proceed to WritingAgent
    - "revise_plan" → route back to PlanningAgent
    - "failed" → end pipeline
    """
    verdict: str        # "success" | "partial" | "revise_plan" | "failed"
    analysis: str
    suggestions: list
    failed_steps: list  # plan.md 中未完成的 step 描述


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

    Markdown-driven: Large data (literature, plans, results) lives in .md files.
    State holds only routing signals, identifiers, and minimal shared data.
    """
    # ============= Input =============
    research_direction: str          # e.g., "quantitative finance momentum strategies"
    project_id: str                  # Unique identifier: "2026-02-27_momentum_strategies"

    # ============= Ideation Agent Output =============
    hypothesis: str                  # Concrete, testable research question (full text in ideation.md)

    # ============= Planning Agent Outputs =============
    experiment_plan: FactorPlan     # Structured factor plan data (also in plan.md)
    methodology: str                 # Detailed methodology description

    # ============= Experiment Agent Outputs =============
    results_data: FactorResults     # Factor evaluation metrics
    validation_status: Literal["success", "partial", "failed"]
    error_messages: Optional[str]    # Error details if validation failed
    experiment_feedback: Optional[ExperimentFeedback]  # Feedback loop for routing

    # ============= Metadata =============
    iteration: int                   # Feedback loop counter (max 2)
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

        # Ideation output
        hypothesis="",

        # Planning outputs
        experiment_plan=FactorPlan(
            objective="",
            factor_description="",
            factor_formula="",
            data_requirements=[],
            implementation_steps=[],
            test_universe="a_shares",
            test_period="",
            rebalance_frequency="daily",
            success_criteria={},
            risk_factors=[],
            estimated_runtime="",
        ),
        methodology="",

        # Experiment outputs
        results_data=FactorResults(
            ic_mean=0.0,
            ic_std=0.0,
            icir=0.0,
            rank_ic_mean=0.0,
            rank_icir=0.0,
            turnover_mean=0.0,
            long_short_return=0.0,
            top_group_return=0.0,
            bottom_group_return=0.0,
            monotonicity_score=0.0,
            factor_coverage=0.0,
        ),
        validation_status="success",
        error_messages=None,
        experiment_feedback=None,

        # Metadata
        iteration=0,
        timestamp=datetime.now().isoformat(),
        status="initialized",
        error_log=None,

        # Quality control
        requires_human_review=False,
        review_notes=None
    )
