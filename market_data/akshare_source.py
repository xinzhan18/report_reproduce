"""
AkShare 数据源 — A 股。

使用 akshare 库获取 A 股历史 OHLCV 数据（前复权）。
需要安装 akshare: pip install akshare
"""

# INPUT:  akshare (A股数据), pandas
#         market_data.base (DataSource)
# OUTPUT: AkShareSource 类
# POSITION: market_data 层 - A股数据源实现

import pandas as pd
from market_data.base import DataSource


class AkShareSource(DataSource):
    """A 股数据源（akshare）。"""

    def available_markets(self) -> list[str]:
        return ["cn_equity"]

    def fetch(self, symbols: list[str], start_date: str,
              end_date: str | None, interval: str) -> dict[str, pd.DataFrame]:
        import akshare as ak

        if end_date is None:
            from datetime import datetime
            end_date = datetime.now().strftime("%Y%m%d")

        # akshare 日期格式：YYYYMMDD
        start_fmt = start_date.replace("-", "")
        end_fmt = end_date.replace("-", "")

        result = {}
        for symbol in symbols:
            try:
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    start_date=start_fmt,
                    end_date=end_fmt,
                    adjust="qfq",
                )
                # 列名映射
                col_map = {"日期": "date", "开盘": "open", "最高": "high",
                           "最低": "low", "收盘": "close", "成交量": "volume"}
                df = df.rename(columns=col_map)
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                    df = df.set_index("date")
                # 只保留标准列
                keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
                df = df[keep]
                result[symbol] = df
            except Exception as e:
                print(f"[AkShareSource] Failed to fetch {symbol}: {e}")

        return result
