"""
Configuration for data sources (papers, financial data, etc.).
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - typing.Dict/List/Any
# OUTPUT: 对外提供 - ARXIV_CONFIG/SSRN_CONFIG/FINANCIAL_DATA_CONFIG等配置字典, get_enabled_paper_sources/get_enabled_financial_sources函数
# POSITION: 系统地位 - [Config/Data Layer] - 数据源配置中心,定义arXiv/Yahoo Finance/Alpha Vantage等数据源参数
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from typing import Dict, List, Any


# arXiv API configuration
ARXIV_CONFIG = {
    "base_url": "http://export.arxiv.org/api/query",
    "max_results_per_query": 100,
    "search_fields": ["ti", "abs", "cat"],  # Title, abstract, category
    "sort_by": "submittedDate",
    "sort_order": "descending",
}


# SSRN configuration (if API access is available)
SSRN_CONFIG = {
    "enabled": False,  # Set to True if you have SSRN API access
    "base_url": "https://api.ssrn.com/v1",
    "api_key": None,  # Set via environment variable
}


# Academic database configuration
ACADEMIC_DB_CONFIG = {
    "ieee": {
        "enabled": False,
        "api_key": None,
    },
    "acm": {
        "enabled": False,
        "api_key": None,
    },
    "springer": {
        "enabled": False,
        "api_key": None,
    },
}


# Financial data sources
FINANCIAL_DATA_CONFIG = {
    "primary_source": "yfinance",  # Yahoo Finance via yfinance
    "backup_sources": ["alpha_vantage"],  # Backup data sources

    "yfinance": {
        "enabled": True,
        "rate_limit": 2000,  # Requests per hour (conservative)
        "timeout": 30,  # Seconds
    },

    "alpha_vantage": {
        "enabled": False,  # Set to True if you have API key
        "api_key": None,  # Set via environment variable
        "rate_limit": 5,  # Requests per minute (free tier)
    },

    "quandl": {
        "enabled": False,
        "api_key": None,
    },
}


# Default symbols for backtesting (keyed by market type)
DEFAULT_SYMBOLS = {
    "us_equity": ["SPY", "QQQ", "IWM", "DIA"],  # Major US ETFs
    "cn_equity": ["000001", "000300", "600519"],  # 平安银行、沪深300ETF、茅台
    "hk_equity": ["0700.HK", "9988.HK"],  # 腾讯、阿里
    "crypto": ["BTC/USDT", "ETH/USDT"],  # 主流加密货币
    "sectors": ["XLF", "XLE", "XLK", "XLV", "XLI"],  # Sector ETFs
    "international": ["EFA", "EEM", "VWO"],  # International ETFs
    "fixed_income": ["TLT", "IEF", "LQD", "HYG"],  # Bond ETFs
    "commodities": ["GLD", "SLV", "USO"],  # Commodity ETFs
}


# Data frequency options
DATA_FREQUENCIES = {
    "1m": "1 minute",
    "5m": "5 minutes",
    "15m": "15 minutes",
    "1h": "1 hour",
    "1d": "1 day",
    "1wk": "1 week",
    "1mo": "1 month",
}


# Default backtest parameters
DEFAULT_BACKTEST_PARAMS = {
    "start_date": "2010-01-01",  # Default start date
    "end_date": None,  # None = today
    "initial_capital": 100000,  # $100k starting capital
    "commission": 0.001,  # 0.1% per trade
    "slippage": 0.001,  # 0.1% slippage
    "frequency": "1d",  # Daily data
}


# Data source configuration aggregation
DATA_SOURCE_CONFIG: Dict[str, Any] = {
    "arxiv": ARXIV_CONFIG,
    "ssrn": SSRN_CONFIG,
    "academic_db": ACADEMIC_DB_CONFIG,
    "financial_data": FINANCIAL_DATA_CONFIG,
    "default_symbols": DEFAULT_SYMBOLS,
    "data_frequencies": DATA_FREQUENCIES,
    "backtest_params": DEFAULT_BACKTEST_PARAMS,
}


def get_enabled_paper_sources() -> List[str]:
    """
    Get list of enabled paper data sources.

    Returns:
        List of enabled source names
    """
    sources = ["arxiv"]  # arXiv always enabled

    if SSRN_CONFIG.get("enabled"):
        sources.append("ssrn")

    for db_name, db_config in ACADEMIC_DB_CONFIG.items():
        if db_config.get("enabled"):
            sources.append(db_name)

    return sources


def get_enabled_financial_sources() -> List[str]:
    """
    Get list of enabled financial data sources.

    Returns:
        List of enabled source names
    """
    sources = []

    for source_name, source_config in FINANCIAL_DATA_CONFIG.items():
        if source_name not in ["primary_source", "backup_sources"]:
            if source_config.get("enabled"):
                sources.append(source_name)

    return sources
