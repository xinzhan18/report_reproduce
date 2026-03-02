"""
market_data — 本地面板数据加载模块。

提供 LocalDataLoader 从本地 CSV 文件加载量价数据。
"""

# POSITION: 模块初始化 - 导出 LocalDataLoader

from market_data.local_data_loader import LocalDataLoader

__all__ = ["LocalDataLoader"]
