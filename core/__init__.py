"""
Core module containing state management and pipeline orchestration.
"""

# POSITION: 模块初始化文件
# 注意: pipeline 不在此处导入以避免循环依赖 (agents ↔ core)
# 使用 from core.pipeline import create_research_pipeline 直接导入

from .state import ResearchState, PaperMetadata

__all__ = [
    'ResearchState',
    'PaperMetadata',
]
