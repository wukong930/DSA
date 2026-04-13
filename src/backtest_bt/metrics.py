# -*- coding: utf-8 -*-
"""Backtest metrics computation.

Provides professional-grade performance metrics: Sharpe, Sortino, Calmar,
VaR, CVaR, Information Ratio, Alpha, Beta, etc.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 244  # A-share trading days
RISK_FREE_RATE = 0.02        # Annualized risk-free rate


def _safe_round(val: float, ndigits: int = 4) -> float:
    """Round a value, returning 0.0 for NaN/Inf."""
    if val is None or math.isnan(val) or math.isinf(val):
        return 0.0
    return round(val, ndigits)


@dataclass
class BacktestReport:
    """Complete backtest result with all metrics and time series."""

    # Core performance
    total_return_pct: float = 0.0
    annual_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration_days: int = 0
    win_rate_pct: float = 0.0
    profit_loss_ratio: float = 0.0

    # Risk metrics
    volatility_annual: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    information_ratio: Optional[float] = None
    beta: Optional[float] = None
    alpha: Optional[float] = None

    # Trade statistics
    total_trades: int = 0
    avg_holding_days: float = 0.0
    avg_profit_per_trade: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0

    # Factor attribution
    factor_ic: Optional[dict[str, float]] = None
    factor_ir: Optional[dict[str, float]] = None

    # Warnings
    benchmark_warning: Optional[str] = None
    warnings: list[str] = field(default_factory=list)

    # Rebalance history (for rolling rebalance mode)
    rebalance_history: list[dict] = field(default_factory=list)

    # Skipped stocks (no data available)
    skipped_codes: list[str] = field(default_factory=list)

    # Time series (for frontend charts)
    equity_curve: list[dict] = field(default_factory=list)
    drawdown_curve: list[dict] = field(default_factory=list)
    monthly_returns: list[dict] = field(default_factory=list)
    trade_list: list[dict] = field(default_factory=list)

    # Human-readable text report (generated after enrichment)
    text_report: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def compute_metrics(
    equity_series: pd.Series,
    benchmark_series: Optional[pd.Series] = None,
    trades: Optional[list[dict]] = None,
    risk_free_rate: float = RISK_FREE_RATE,
) -> BacktestReport:
    """Compute all backtest metrics from an equity curve.

    Args:
        equity_series: Daily portfolio value series (indexed by date).
        benchmark_series: Optional benchmark value series for relative metrics.
        trades: Optional list of trade dicts with keys: entry_date, exit_date,
                return_pct, holding_days, code.
        risk_free_rate: Annualized risk-free rate.
    """
    report = BacktestReport()

    if len(equity_series) < 2:
        return report

    # Daily returns
    returns = equity_series.pct_change().dropna()
    n_days = len(returns)

    # Total & annual return
    total_return = (equity_series.iloc[-1] / equity_series.iloc[0]) - 1
    report.total_return_pct = _safe_round(total_return * 100, 2)

    years = n_days / TRADING_DAYS_PER_YEAR
    if years > 0:
        annual_return = (1 + total_return) ** (1 / years) - 1
        report.annual_return_pct = _safe_round(annual_return * 100, 2)
    else:
        annual_return = 0.0

    # Volatility
    daily_vol = returns.std()
    annual_vol = daily_vol * math.sqrt(TRADING_DAYS_PER_YEAR)
    report.volatility_annual = _safe_round(annual_vol * 100, 2)

    # Sharpe
    daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
    excess = returns - daily_rf
    if daily_vol > 0:
        report.sharpe_ratio = _safe_round(
            (excess.mean() / daily_vol) * math.sqrt(TRADING_DAYS_PER_YEAR), 4
        )

    # Sortino
    downside = returns[returns < daily_rf] - daily_rf
    downside_vol = downside.std() if len(downside) > 0 else 0
    if downside_vol > 0:
        report.sortino_ratio = _safe_round(
            (excess.mean() / downside_vol) * math.sqrt(TRADING_DAYS_PER_YEAR), 4
        )

    # Drawdown
    cummax = equity_series.cummax()
    drawdown = (equity_series - cummax) / cummax
    report.max_drawdown_pct = _safe_round(abs(drawdown.min()) * 100, 2)

    # Max drawdown duration
    in_drawdown = drawdown < 0
    if in_drawdown.any():
        groups = (~in_drawdown).cumsum()
        dd_lengths = in_drawdown.groupby(groups).sum()
        report.max_drawdown_duration_days = int(dd_lengths.max())

    # Calmar
    if report.max_drawdown_pct > 0:
        report.calmar_ratio = _safe_round(
            report.annual_return_pct / report.max_drawdown_pct, 4
        )

    # VaR & CVaR (95%)
    sorted_returns = returns.sort_values()
    var_idx = int(len(sorted_returns) * 0.05)
    if var_idx > 0:
        report.var_95 = _safe_round(abs(sorted_returns.iloc[var_idx]) * 100, 4)
        report.cvar_95 = _safe_round(abs(sorted_returns.iloc[:var_idx].mean()) * 100, 4)

    # Benchmark-relative metrics
    if benchmark_series is not None and len(benchmark_series) >= 2:
        bench_returns = benchmark_series.pct_change().dropna()
        # Align
        common_idx = returns.index.intersection(bench_returns.index)
        if len(common_idx) > 10:
            r = returns.loc[common_idx]
            b = bench_returns.loc[common_idx]
            active = r - b

            # Information Ratio
            tracking_error = active.std()
            if tracking_error > 0:
                report.information_ratio = _safe_round(
                    (active.mean() / tracking_error) * math.sqrt(TRADING_DAYS_PER_YEAR), 4
                )

            # Beta & Alpha
            cov = np.cov(r.values, b.values)
            if cov[1, 1] > 0:
                report.beta = _safe_round(float(cov[0, 1] / cov[1, 1]), 4)
                benchmark_annual = (1 + b.mean()) ** TRADING_DAYS_PER_YEAR - 1
                report.alpha = _safe_round(
                    (annual_return - risk_free_rate)
                    - report.beta * (benchmark_annual - risk_free_rate),
                    4,
                )

    # Trade statistics
    if trades:
        report.total_trades = len(trades)
        returns_list = [t.get("return_pct", 0) for t in trades]
        wins = [r for r in returns_list if r > 0]
        losses = [r for r in returns_list if r < 0]

        if returns_list:
            report.win_rate_pct = _safe_round(len(wins) / len(returns_list) * 100, 2)
            report.avg_profit_per_trade = _safe_round(sum(returns_list) / len(returns_list), 4)

        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0
        if avg_loss > 0:
            report.profit_loss_ratio = _safe_round(avg_win / avg_loss, 4)

        holding_days = [t.get("holding_days", 0) for t in trades]
        if holding_days:
            report.avg_holding_days = _safe_round(sum(holding_days) / len(holding_days), 1)

        # Consecutive wins/losses
        report.max_consecutive_wins = _max_consecutive(returns_list, positive=True)
        report.max_consecutive_losses = _max_consecutive(returns_list, positive=False)

        # Trade list for frontend
        report.trade_list = trades

    # Equity curve for frontend
    report.equity_curve = _build_equity_curve(equity_series, benchmark_series)
    report.drawdown_curve = _build_drawdown_curve(equity_series)
    report.monthly_returns = _build_monthly_returns(returns)

    return report


def _max_consecutive(returns: list[float], positive: bool) -> int:
    max_count = 0
    count = 0
    for r in returns:
        if (positive and r > 0) or (not positive and r < 0):
            count += 1
            max_count = max(max_count, count)
        else:
            count = 0
    return max_count


def _build_equity_curve(
    equity: pd.Series, benchmark: Optional[pd.Series]
) -> list[dict]:
    result = []
    for date, value in equity.items():
        entry = {"date": str(date), "value": round(float(value), 2)}
        if benchmark is not None and date in benchmark.index:
            entry["benchmark"] = round(float(benchmark[date]), 2)
        result.append(entry)
    return result


def _build_drawdown_curve(equity: pd.Series) -> list[dict]:
    cummax = equity.cummax()
    dd = (equity - cummax) / cummax
    return [
        {"date": str(date), "drawdown_pct": round(float(v) * 100, 2)}
        for date, v in dd.items()
    ]


def _build_monthly_returns(returns: pd.Series) -> list[dict]:
    if returns.empty:
        return []
    monthly = returns.groupby([returns.index.year, returns.index.month]).apply(
        lambda x: (1 + x).prod() - 1
    )
    result = []
    for (year, month), ret in monthly.items():
        result.append({
            "year": int(year),
            "month": int(month),
            "return_pct": round(float(ret) * 100, 2),
        })
    return result
