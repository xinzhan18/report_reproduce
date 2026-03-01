"""
Research Automation Agent System - Agents Module

四个核心 Agent：Ideation / Planning / Experiment / Writing
全部采用 Agentic Tool-Use 架构，通过 BaseAgent._agentic_loop() 实现工具自治执行。
"""

# POSITION: agents 模块入口

from .ideation import IdeationAgent
from .planning import PlanningAgent
from .experiment import ExperimentAgent
from .writing import WritingAgent

__all__ = [
    'IdeationAgent',
    'PlanningAgent',
    'ExperimentAgent',
    'WritingAgent',
]
