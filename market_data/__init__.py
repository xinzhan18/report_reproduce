"""
market_data — 独立数据层模块。

提供统一的多市场金融数据获取接口。
"""

# POSITION: 模块初始化 - 导出 DataFetcher 和 DataSource

from market_data.fetcher import DataFetcher
from market_data.base import DataSource

__all__ = ["DataFetcher", "DataSource"]
