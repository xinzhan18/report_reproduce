"""
Tools module for paper fetching, data retrieval, and backtesting.
"""

# ============================================================================
# 文件头注释 (File Header)
# POSITION: 模块初始化文件 - 导出tools模块的工具类(PaperFetcher/FileManager/FinancialDataFetcher/BacktestEngine)
# ============================================================================

from .paper_fetcher import PaperFetcher
from .file_manager import FileManager
from .data_fetcher import FinancialDataFetcher
from .backtest_engine import BacktestEngine

__all__ = [
    'PaperFetcher',
    'FileManager',
    'FinancialDataFetcher',
    'BacktestEngine',
]
