"""
Financial data fetching utilities using yfinance and other sources.
"""

import yfinance as yf
import pandas as pd
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from config.data_sources import FINANCIAL_DATA_CONFIG, DEFAULT_BACKTEST_PARAMS
import time


class FinancialDataFetcher:
    """
    Fetches historical financial data for backtesting.
    """

    def __init__(self):
        self.config = FINANCIAL_DATA_CONFIG
        self.default_params = DEFAULT_BACKTEST_PARAMS

    def fetch_data(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical price data for multiple symbols.

        Args:
            symbols: List of ticker symbols (e.g., ["AAPL", "MSFT"])
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (None = today)
            interval: Data frequency (1m, 5m, 15m, 1h, 1d, 1wk, 1mo)

        Returns:
            Dictionary mapping symbol to DataFrame with OHLCV data
        """
        if start_date is None:
            start_date = self.default_params["start_date"]

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        data = {}

        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(
                    start=start_date,
                    end=end_date,
                    interval=interval,
                    auto_adjust=True  # Adjust for splits and dividends
                )

                if not df.empty:
                    # Standardize column names
                    df.columns = [col.lower() for col in df.columns]
                    data[symbol] = df
                else:
                    print(f"Warning: No data retrieved for {symbol}")

                # Rate limiting
                time.sleep(0.5)

            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")

        return data

    def fetch_single_symbol(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch data for a single symbol.

        Args:
            symbol: Ticker symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Data frequency

        Returns:
            DataFrame with OHLCV data or None if fetch failed
        """
        result = self.fetch_data([symbol], start_date, end_date, interval)
        return result.get(symbol)

    def fetch_intraday_data(
        self,
        symbols: List[str],
        period: str = "5d",
        interval: str = "5m"
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch recent intraday data.

        Args:
            symbols: List of ticker symbols
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Intraday interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h)

        Returns:
            Dictionary mapping symbol to DataFrame
        """
        data = {}

        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period, interval=interval)

                if not df.empty:
                    df.columns = [col.lower() for col in df.columns]
                    data[symbol] = df

                time.sleep(0.5)

            except Exception as e:
                print(f"Error fetching intraday data for {symbol}: {e}")

        return data

    def get_ticker_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker information and metadata.

        Args:
            symbol: Ticker symbol

        Returns:
            Dictionary with ticker information
        """
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info

        except Exception as e:
            print(f"Error fetching info for {symbol}: {e}")
            return {}

    def validate_symbols(self, symbols: List[str]) -> List[str]:
        """
        Validate that symbols exist and have data.

        Args:
            symbols: List of ticker symbols to validate

        Returns:
            List of valid symbols
        """
        valid_symbols = []

        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                # Try to fetch 1 day of data
                df = ticker.history(period="1d")

                if not df.empty:
                    valid_symbols.append(symbol)
                else:
                    print(f"Warning: No data available for {symbol}")

            except Exception as e:
                print(f"Error validating {symbol}: {e}")

        return valid_symbols

    def calculate_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate returns from price data.

        Args:
            df: DataFrame with 'close' column

        Returns:
            DataFrame with added return columns
        """
        df = df.copy()

        # Simple returns
        df['return'] = df['close'].pct_change()

        # Log returns
        df['log_return'] = pd.Series(
            data=pd.Series.log(df['close']).diff(),
            index=df.index
        )

        # Cumulative returns
        df['cum_return'] = (1 + df['return']).cumprod() - 1

        return df

    def resample_data(
        self,
        df: pd.DataFrame,
        frequency: str = "1W"
    ) -> pd.DataFrame:
        """
        Resample data to different frequency.

        Args:
            df: DataFrame with OHLCV data
            frequency: Target frequency (1D, 1W, 1M, etc.)

        Returns:
            Resampled DataFrame
        """
        resampled = pd.DataFrame()

        # Handle OHLCV columns appropriately
        if 'open' in df.columns:
            resampled['open'] = df['open'].resample(frequency).first()
        if 'high' in df.columns:
            resampled['high'] = df['high'].resample(frequency).max()
        if 'low' in df.columns:
            resampled['low'] = df['low'].resample(frequency).min()
        if 'close' in df.columns:
            resampled['close'] = df['close'].resample(frequency).last()
        if 'volume' in df.columns:
            resampled['volume'] = df['volume'].resample(frequency).sum()

        return resampled.dropna()

    def merge_multiple_symbols(
        self,
        data: Dict[str, pd.DataFrame],
        column: str = "close"
    ) -> pd.DataFrame:
        """
        Merge data from multiple symbols into single DataFrame.

        Args:
            data: Dictionary mapping symbols to DataFrames
            column: Column to extract (default: close)

        Returns:
            DataFrame with symbols as columns
        """
        merged = pd.DataFrame()

        for symbol, df in data.items():
            if column in df.columns:
                merged[symbol] = df[column]

        return merged

    def get_trading_days(
        self,
        start_date: str,
        end_date: Optional[str] = None
    ) -> pd.DatetimeIndex:
        """
        Get list of valid trading days.

        Args:
            start_date: Start date
            end_date: End date (None = today)

        Returns:
            DatetimeIndex of trading days
        """
        # Fetch SPY as proxy for trading days
        spy_data = self.fetch_single_symbol("SPY", start_date, end_date)

        if spy_data is not None and not spy_data.empty:
            return spy_data.index

        # Fallback: business days
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        return pd.bdate_range(start=start_date, end=end_date)
