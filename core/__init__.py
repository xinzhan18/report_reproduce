"""
Core module containing state management and pipeline orchestration.
"""

from .state import ResearchState, PaperMetadata
from .persistence import get_checkpointer, create_config
from .pipeline import create_research_pipeline

__all__ = [
    'ResearchState',
    'PaperMetadata',
    'get_checkpointer',
    'create_config',
    'create_research_pipeline',
]
