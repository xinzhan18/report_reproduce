"""
数据源抽象基类。

所有数据源（yfinance、akshare、ccxt）继承此类，统一接口。
"""

# INPUT:  abc (抽象基类), pandas (DataFrame类型)
# OUTPUT: DataSource 抽象基类
# POSITION: market_data 层 - 数据源接口定义

from abc import ABC, abstractmethod
import pandas as pd


class DataSource(ABC):
    """数据源抽象基类。所有实现必须返回列名标准化为 open/high/low/close/volume 的 DataFrame。"""

    @abstractmethod
    def fetch(self, symbols: list[str], start_date: str,
              end_date: str | None, interval: str) -> dict[str, pd.DataFrame]:
        """获取多品种数据。

        Args:
            symbols: 品种代码列表
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD，None 表示今天
            interval: 数据频率 (1d, 1h, etc.)

        Returns:
            {symbol: DataFrame}，列名标准化为 open/high/low/close/volume
        """

    @abstractmethod
    def available_markets(self) -> list[str]:
        """返回支持的 market 标识列表（如 'us_equity', 'cn_equity', 'crypto'）。"""
