"""
LocalDataLoader — 本地面板数据加载器

从本地 CSV 文件加载量价数据，替代远程 DataFetcher。
支持 A 股和加密货币市场。
"""

# INPUT:  pathlib, pandas, json, logging
# OUTPUT: LocalDataLoader 类
# POSITION: market_data 层 - 本地数据加载器，ExperimentAgent 调用入口

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger("market_data.local_data_loader")


class LocalDataLoader:
    """本地面板数据加载器。

    目录结构:
        data/market/a_shares/000001.SZ.csv
        data/market/a_shares/000002.SZ.csv
        data/market/crypto/BTCUSDT.csv

    CSV 格式: date,open,high,low,close,volume (DatetimeIndex)
    """

    def __init__(self, data_dir: str = "data/market"):
        self.data_dir = Path(data_dir).resolve()

    def load(self, data_config: dict) -> dict[str, pd.DataFrame]:
        """根据 data_config 加载数据。

        Args:
            data_config: {
                "market": "a_shares" | "crypto",
                "universe": "all" | ["000001.SZ", ...],
                "start_date": "2018-01-01",  # optional
                "end_date": "2024-12-31",    # optional
            }

        Returns:
            {symbol: DataFrame(date, OHLCV)}
        """
        market = data_config.get("market", "a_shares")
        universe = data_config.get("universe", "all")
        start_date = data_config.get("start_date")
        end_date = data_config.get("end_date")

        market_dir = self.data_dir / market
        if not market_dir.exists():
            logger.warning(f"Market directory not found: {market_dir}")
            return {}

        # 确定要加载的文件
        if universe == "all":
            csv_files = sorted(market_dir.glob("*.csv"))
        else:
            csv_files = []
            for symbol in universe:
                csv_path = market_dir / f"{symbol}.csv"
                if csv_path.exists():
                    csv_files.append(csv_path)
                else:
                    logger.warning(f"CSV not found: {csv_path}")

        result = {}
        for csv_path in csv_files:
            symbol = csv_path.stem  # 去掉 .csv 后缀
            try:
                df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
                # 标准化列名为小写
                df.columns = [c.lower() for c in df.columns]

                # 日期过滤
                if start_date:
                    df = df[df.index >= start_date]
                if end_date:
                    df = df[df.index <= end_date]

                if len(df) > 0:
                    result[symbol] = df
                else:
                    logger.warning(f"No data in range for {symbol}")
            except Exception as e:
                logger.warning(f"Failed to load {csv_path}: {e}")

        logger.info(f"Loaded {len(result)} symbols from {market_dir}")
        return result
