"""
CCXT 数据源 — 加密货币。

使用 ccxt 库从交易所获取加密货币 OHLCV 数据。
需要安装 ccxt: pip install ccxt
"""

# INPUT:  ccxt (加密货币交易所), pandas
#         market_data.base (DataSource)
# OUTPUT: CCXTSource 类
# POSITION: market_data 层 - 加密货币数据源实现

import pandas as pd
from market_data.base import DataSource


# ccxt interval 映射
_INTERVAL_MAP = {
    "1d": "1d", "1h": "1h", "4h": "4h",
    "15m": "15m", "5m": "5m", "1m": "1m",
}


class CCXTSource(DataSource):
    """加密货币数据源（ccxt，默认 Binance）。"""

    def __init__(self, exchange_id: str = "binance"):
        self.exchange_id = exchange_id

    def available_markets(self) -> list[str]:
        return ["crypto"]

    def fetch(self, symbols: list[str], start_date: str,
              end_date: str | None, interval: str) -> dict[str, pd.DataFrame]:
        import ccxt

        exchange_cls = getattr(ccxt, self.exchange_id)
        exchange = exchange_cls()

        timeframe = _INTERVAL_MAP.get(interval, "1d")
        since_ts = int(pd.Timestamp(start_date).timestamp() * 1000)

        result = {}
        for symbol in symbols:
            try:
                all_ohlcv = []
                fetch_since = since_ts
                while True:
                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe,
                                                  since=fetch_since, limit=1000)
                    if not ohlcv:
                        break
                    all_ohlcv.extend(ohlcv)
                    fetch_since = ohlcv[-1][0] + 1
                    if end_date and fetch_since > int(pd.Timestamp(end_date).timestamp() * 1000):
                        break
                    if len(ohlcv) < 1000:
                        break

                if all_ohlcv:
                    df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
                    df.index = pd.to_datetime(df["timestamp"], unit="ms")
                    df = df[["open", "high", "low", "close", "volume"]]
                    if end_date:
                        df = df[:end_date]
                    result[symbol] = df
            except Exception as e:
                print(f"[CCXTSource] Failed to fetch {symbol}: {e}")

        return result
