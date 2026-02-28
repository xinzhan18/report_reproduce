"""
DataFetcher 路由器 — ExperimentAgent 的唯一数据入口。

根据 data_config 中的 market 字段路由到对应数据源。
可用数据源在初始化时自动注册，缺少 akshare/ccxt 不会报错。
"""

# INPUT:  market_data.base (DataSource), market_data.yfinance_source (YFinanceSource),
#         market_data.akshare_source (AkShareSource), market_data.ccxt_source (CCXTSource),
#         pandas
# OUTPUT: DataFetcher 类
# POSITION: market_data 层 - 数据获取路由器，ExperimentAgent 调用入口

import pandas as pd
from market_data.base import DataSource


class DataFetcher:
    """数据获取路由器。根据 market 类型分发到对应 DataSource。"""

    def __init__(self):
        self.sources: dict[str, DataSource] = {}
        # 所有数据源都 try_register，缺包则跳过
        self._try_register("market_data.yfinance_source", "YFinanceSource", "yfinance")
        self._try_register("market_data.akshare_source", "AkShareSource", "akshare")
        self._try_register("market_data.ccxt_source", "CCXTSource", "ccxt")

    def _register(self, source: DataSource):
        for market in source.available_markets():
            self.sources[market] = source

    def _try_register(self, module_path: str, class_name: str, package_name: str):
        """尝试注册数据源，依赖包缺失则跳过。"""
        try:
            __import__(package_name)
            import importlib
            mod = importlib.import_module(module_path)
            source_cls = getattr(mod, class_name)
            self._register(source_cls())
        except ImportError:
            pass

    def fetch(self, data_config: dict) -> dict[str, pd.DataFrame]:
        """根据 data_config 获取数据。ExperimentAgent 的唯一入口。

        Args:
            data_config: 包含 market, symbols, start_date, end_date, interval 字段

        Returns:
            {symbol: DataFrame}
        """
        market = data_config.get("market", "us_equity")
        symbols = data_config.get("symbols", ["SPY"])
        start = data_config.get("start_date", "2015-01-01")
        end = data_config.get("end_date", None)
        interval = data_config.get("interval", "1d")

        source = self.sources.get(market)
        if source is None:
            raise ValueError(
                f"No data source for market '{market}'. "
                f"Available: {list(self.sources.keys())}"
            )

        return source.fetch(symbols, start, end, interval)

    def fetch_single_symbol(self, symbol: str, start_date: str | None = None,
                            end_date: str | None = None, interval: str = "1d") -> pd.DataFrame | None:
        """向后兼容方法。"""
        config = {
            "symbols": [symbol],
            "start_date": start_date or "2015-01-01",
            "end_date": end_date,
            "interval": interval,
            "market": "us_equity",
        }
        result = self.fetch(config)
        return result.get(symbol)
