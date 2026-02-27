"""
Research Automation Agent System - Agents Module

This module contains the four core agents for automated research:
- Ideation Agent: Literature review and hypothesis generation
- Planning Agent: Experiment design and planning
- Experiment Agent: Code execution and validation
- Writing Agent: Report generation
"""

from .ideation_agent import IdeationAgent
from .planning_agent import PlanningAgent
from .experiment_agent import ExperimentAgent
from .writing_agent import WritingAgent

__all__ = [
    'IdeationAgent',
    'PlanningAgent',
    'ExperimentAgent',
    'WritingAgent',
]
