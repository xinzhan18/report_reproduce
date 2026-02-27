"""
Core module containing state management and pipeline orchestration.
"""

# ============================================================================
# 文件头注释 (File Header)
# POSITION: 模块初始化文件 - 导出core模块的核心类(ResearchState/PaperMetadata/get_checkpointer/create_config/create_research_pipeline)
# ============================================================================

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
