"""
evaluate_factor — 因子评估辅助函数

计算 IC/ICIR/分层收益等因子评估指标，注入到 sandbox 供 LLM 生成的代码调用。
用户后续可替换函数体为自己的评估库，接口签名和返回 key 保持不变。
"""

# INPUT:  pandas, numpy
# OUTPUT: evaluate_factor() 函数
# POSITION: agents/experiment 子包 - 因子评估辅助

import pandas as pd
import numpy as np


def evaluate_factor(
    factor_values: pd.DataFrame,
    price_data: pd.DataFrame,
    n_groups: int = 5,
    holding_period: int = 1,
) -> dict:
    """因子评估接口。

    Args:
        factor_values: 因子值面板，index=date, columns=symbols
        price_data: 收盘价面板，index=date, columns=symbols (close)
        n_groups: 分层数量
        holding_period: 持仓周期（交易日数）

    Returns:
        包含 ic_mean/icir/rank_ic_mean/rank_icir/turnover_mean/
        long_short_return/top_group_return/bottom_group_return/
        monotonicity_score/factor_coverage 的 dict
    """
    # 对齐日期和品种
    common_dates = factor_values.index.intersection(price_data.index)
    common_symbols = factor_values.columns.intersection(price_data.columns)
    factor_values = factor_values.loc[common_dates, common_symbols].sort_index()
    price_data = price_data.loc[common_dates, common_symbols].sort_index()

    # 收益率（向前 holding_period 天）
    forward_returns = price_data.pct_change(holding_period).shift(-holding_period)

    # IC: 每期截面相关系数
    ic_series = []
    rank_ic_series = []
    for date in factor_values.index:
        fv = factor_values.loc[date].dropna()
        fr = forward_returns.loc[date].dropna() if date in forward_returns.index else pd.Series(dtype=float)
        common = fv.index.intersection(fr.index)
        if len(common) < 10:
            continue
        ic = fv[common].corr(fr[common])
        rank_ic = fv[common].rank().corr(fr[common].rank())
        if not np.isnan(ic):
            ic_series.append(ic)
        if not np.isnan(rank_ic):
            rank_ic_series.append(rank_ic)

    ic_series = np.array(ic_series) if ic_series else np.array([0.0])
    rank_ic_series = np.array(rank_ic_series) if rank_ic_series else np.array([0.0])

    ic_mean = float(np.mean(ic_series))
    ic_std = float(np.std(ic_series)) if len(ic_series) > 1 else 1e-8
    icir = ic_mean / ic_std if ic_std > 1e-8 else 0.0
    rank_ic_mean = float(np.mean(rank_ic_series))
    rank_ic_std = float(np.std(rank_ic_series)) if len(rank_ic_series) > 1 else 1e-8
    rank_icir = rank_ic_mean / rank_ic_std if rank_ic_std > 1e-8 else 0.0

    # 分层收益
    group_returns = _compute_group_returns(factor_values, forward_returns, n_groups)
    top_group_return = group_returns[-1] if group_returns else 0.0
    bottom_group_return = group_returns[0] if group_returns else 0.0
    long_short_return = top_group_return - bottom_group_return

    # 单调性分数
    monotonicity_score = _compute_monotonicity(group_returns)

    # 换手率
    turnover_mean = _compute_turnover(factor_values, n_groups)

    # 因子覆盖率
    total_cells = factor_values.shape[0] * factor_values.shape[1]
    valid_cells = factor_values.notna().sum().sum()
    factor_coverage = float(valid_cells / total_cells) if total_cells > 0 else 0.0

    return {
        "ic_mean": round(ic_mean, 6),
        "ic_std": round(float(ic_std), 6),
        "icir": round(icir, 4),
        "rank_ic_mean": round(rank_ic_mean, 6),
        "rank_icir": round(rank_icir, 4),
        "turnover_mean": round(turnover_mean, 4),
        "long_short_return": round(long_short_return, 4),
        "top_group_return": round(top_group_return, 4),
        "bottom_group_return": round(bottom_group_return, 4),
        "monotonicity_score": round(monotonicity_score, 4),
        "factor_coverage": round(factor_coverage, 4),
    }


def _compute_group_returns(
    factor_values: pd.DataFrame,
    forward_returns: pd.DataFrame,
    n_groups: int,
) -> list[float]:
    """计算各分层组的平均年化收益。"""
    group_total = [[] for _ in range(n_groups)]

    for date in factor_values.index:
        fv = factor_values.loc[date].dropna()
        fr = forward_returns.loc[date].dropna() if date in forward_returns.index else pd.Series(dtype=float)
        common = fv.index.intersection(fr.index)
        if len(common) < n_groups:
            continue
        ranked = fv[common].rank(method="first")
        group_size = len(common) / n_groups
        for i in range(n_groups):
            low = i * group_size
            high = (i + 1) * group_size
            members = ranked[(ranked > low) & (ranked <= high)].index
            if len(members) > 0:
                group_total[i].append(fr[members].mean())

    # 年化（假设日频 252 天）
    annualized = []
    for g in group_total:
        if g:
            mean_daily = np.mean(g)
            annualized.append(float(mean_daily * 252))
        else:
            annualized.append(0.0)
    return annualized


def _compute_monotonicity(group_returns: list[float]) -> float:
    """计算分层单调性分数 (0-1)，1 表示完全单调递增。"""
    if len(group_returns) < 2:
        return 0.0
    n = len(group_returns)
    concordant = 0
    total = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += 1
            if group_returns[j] > group_returns[i]:
                concordant += 1
    return concordant / total if total > 0 else 0.0


def _compute_turnover(factor_values: pd.DataFrame, n_groups: int) -> float:
    """计算顶层分组的平均换手率。"""
    dates = factor_values.index
    if len(dates) < 2:
        return 0.0

    turnovers = []
    prev_top = set()
    for date in dates:
        fv = factor_values.loc[date].dropna()
        if len(fv) < n_groups:
            continue
        ranked = fv.rank(method="first")
        threshold = len(fv) * (n_groups - 1) / n_groups
        top = set(ranked[ranked > threshold].index)
        if prev_top:
            overlap = len(top & prev_top)
            turnover = 1.0 - overlap / max(len(top), 1)
            turnovers.append(turnover)
        prev_top = top

    return float(np.mean(turnovers)) if turnovers else 0.0
