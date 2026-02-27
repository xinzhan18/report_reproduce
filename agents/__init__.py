"""
Research Automation Agent System - Agents Module

This module contains the four core agents for automated research:
- Ideation Agent: Literature review and hypothesis generation
- Planning Agent: Experiment design and planning
- Experiment Agent: Code execution and validation
- Writing Agent: Report generation
"""

# ============================================================================
# 文件头注释 (File Header)
# POSITION: 模块初始化文件 - 导出agents模块的四个核心Agent(IdeationAgent/PlanningAgent/ExperimentAgent/WritingAgent)
# ============================================================================

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
