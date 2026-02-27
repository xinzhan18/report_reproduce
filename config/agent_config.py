"""
Agent-specific configurations.
"""

from typing import Dict, Any


# Agent configurations
AGENT_CONFIG: Dict[str, Dict[str, Any]] = {
    "ideation": {
        "name": "Ideation Agent",
        "model": "sonnet",  # Use Sonnet for complex analysis
        "temperature": 0.7,  # Higher creativity for hypothesis generation
        "max_papers_per_scan": 50,
        "min_papers_for_trigger": 5,  # Minimum papers to trigger pipeline
        "focus_categories": [
            "q-fin.RM",  # Risk Management
            "q-fin.PM",  # Portfolio Management
            "q-fin.TR",  # Trading and Market Microstructure
            "q-fin.ST",  # Statistical Finance
            "q-fin.CP",  # Computational Finance
            "stat.ML",   # Machine Learning Statistics
            "cs.LG",     # Machine Learning (CS)
        ],
        "keywords": [
            "quantitative finance",
            "algorithmic trading",
            "portfolio optimization",
            "risk management",
            "market microstructure",
            "high-frequency trading",
            "factor models",
            "backtesting",
            "momentum strategies",
            "mean reversion",
            "pairs trading",
            "statistical arbitrage",
        ],
    },

    "planning": {
        "name": "Planning Agent",
        "model": "sonnet",  # Use Sonnet for systematic planning
        "temperature": 0.3,  # Lower temperature for structured planning
        "max_iterations": 3,  # Maximum plan revision attempts
        "require_feasibility_check": True,
    },

    "experiment": {
        "name": "Experiment Agent",
        "model": "sonnet",  # Use Sonnet for code generation
        "temperature": 0.2,  # Low temperature for precise code
        "max_retries": 2,  # Retry failed experiments
        "execution_timeout": 3600,  # 1 hour timeout for backtest
        "validation_metrics": {
            "min_sharpe_ratio": 0.5,  # Minimum acceptable Sharpe ratio
            "min_trades": 10,  # Minimum number of trades for statistical significance
            "max_drawdown_threshold": 0.5,  # Maximum 50% drawdown
        },
    },

    "writing": {
        "name": "Writing Agent",
        "model": "sonnet",  # Use Sonnet for high-quality writing
        "temperature": 0.4,  # Balanced creativity and structure
        "report_format": "markdown",  # Output format
        "include_visualizations": True,
        "citation_style": "APA",  # Or "IEEE", "Chicago", etc.
    },
}


# Pipeline configuration
PIPELINE_CONFIG = {
    "max_parallel_projects": 3,  # Maximum concurrent research projects
    "checkpoint_interval": 1,  # Checkpoint after each agent
    "error_retry_delay": 300,  # 5 minutes delay before retry
    "human_review_required": True,  # Require human review before publication
    "auto_archive_days": 90,  # Archive completed projects after 90 days
}


# Quality control thresholds
QUALITY_THRESHOLDS = {
    "min_papers_reviewed": 10,  # Minimum papers for literature review
    "min_research_gaps": 3,  # Minimum research gaps identified
    "min_experiment_steps": 5,  # Minimum implementation steps in plan
    "min_report_sections": 6,  # Minimum report sections (abstract, intro, lit review, methods, results, discussion)
}


def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific agent.

    Args:
        agent_name: Name of the agent (ideation, planning, experiment, writing)

    Returns:
        Configuration dictionary for the agent
    """
    return AGENT_CONFIG.get(agent_name, {})


def get_model_for_agent(agent_name: str) -> str:
    """
    Get the recommended model for an agent.

    Args:
        agent_name: Name of the agent

    Returns:
        Model type string (sonnet, opus, or haiku)
    """
    config = get_agent_config(agent_name)
    return config.get("model", "sonnet")
