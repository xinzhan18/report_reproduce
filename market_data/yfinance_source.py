"""
YFinance 数据源 — 美股/港股。

使用 yfinance 库从 Yahoo Finance 获取历史 OHLCV 数据。
"""

# INPUT:  yfinance (Yahoo Finance API), pandas, time, datetime
#         market_data.base (DataSource)
# OUTPUT: YFinanceSource 类
# POSITION: market_data 层 - 美股/港股数据源实现

import pandas as pd
import time
from datetime import datetime
from market_data.base import DataSource


class YFinanceSource(DataSource):
    """Yahoo Finance 数据源，支持美股和港股。"""

    def available_markets(self) -> list[str]:
        return ["us_equity", "hk_equity"]

    def fetch(self, symbols: list[str], start_date: str,
              end_date: str | None, interval: str) -> dict[str, pd.DataFrame]:
        import yfinance as yf

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        result = {}
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(
                    start=start_date,
                    end=end_date,
                    interval=interval,
                    auto_adjust=True,
                )
                if not df.empty:
                    df.columns = [col.lower() for col in df.columns]
                    result[symbol] = df
                time.sleep(0.5)
            except Exception as e:
                print(f"[YFinanceSource] Failed to fetch {symbol}: {e}")

        return result
