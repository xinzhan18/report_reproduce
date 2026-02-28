"""
compute_metrics — 标准量化指标计算辅助函数

从资金曲线计算标准量化指标，注入到 sandbox 供 LLM 生成的代码调用。
"""

# INPUT:  pandas, numpy
# OUTPUT: compute_metrics() 函数
# POSITION: agents/experiment 子包 - 指标计算辅助

import pandas as pd
import numpy as np


def compute_metrics(portfolio_values: pd.Series, initial_capital: float = 100000) -> dict:
    """从资金曲线计算标准量化指标。

    Args:
        portfolio_values: 每日资金曲线 Series（index 为日期）
        initial_capital: 初始资金

    Returns:
        包含 total_return, sharpe_ratio, max_drawdown, volatility, cagr,
        sortino_ratio, calmar_ratio 的 dict
    """
    returns = portfolio_values.pct_change().dropna()
    total_return = (portfolio_values.iloc[-1] / initial_capital) - 1
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0.0
    cummax = portfolio_values.cummax()
    max_dd = ((portfolio_values - cummax) / cummax).min()
    vol = returns.std() * np.sqrt(252)
    years = len(returns) / 252
    cagr = ((1 + total_return) ** (1 / years) - 1) if years > 0 else 0.0
    sortino_downside = returns[returns < 0].std() * np.sqrt(252)
    sortino = (returns.mean() / sortino_downside * np.sqrt(252)) if sortino_downside > 0 else 0.0
    calmar = cagr / abs(max_dd) if max_dd != 0 else 0.0
    return {
        "total_return": float(total_return),
        "sharpe_ratio": float(sharpe),
        "max_drawdown": float(max_dd),
        "volatility": float(vol),
        "cagr": float(cagr),
        "sortino_ratio": float(sortino),
        "calmar_ratio": float(calmar),
    }
