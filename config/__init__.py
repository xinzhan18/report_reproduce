"""
Configuration module for the research automation system.
"""

# ============================================================================
# 文件头注释 (File Header)
# POSITION: 模块初始化文件 - 导出config模块的配置函数和常量(get_llm/get_haiku_llm/AGENT_CONFIG/DATA_SOURCE_CONFIG)
# ============================================================================

from .llm_config import get_llm, get_haiku_llm
from .agent_config import AGENT_CONFIG
from .data_sources import DATA_SOURCE_CONFIG

__all__ = [
    'get_llm',
    'get_haiku_llm',
    'AGENT_CONFIG',
    'DATA_SOURCE_CONFIG',
]
