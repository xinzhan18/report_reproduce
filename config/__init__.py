"""
Configuration module for the research automation system.
"""

from .llm_config import get_llm, get_haiku_llm
from .agent_config import AGENT_CONFIG
from .data_sources import DATA_SOURCE_CONFIG

__all__ = [
    'get_llm',
    'get_haiku_llm',
    'AGENT_CONFIG',
    'DATA_SOURCE_CONFIG',
]
