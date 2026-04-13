# -*- coding: utf-8 -*-
"""Trade enricher — supplements trade records with price context.

Enriches each trade in trade_list with:
- entry / exit price and bar
- high / low price during holding period
- position_value (entry_price * size)
- benchmark value at entry and exit
- relative return vs benchmark
- exit_reason, entry_signal (if captured by strategy)
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from src.data.external_loader import ExternalDataLoader

logger = logging.getLogger(__name__)

# Map of exit reason codes to human-readable Chinese labels
_EXIT_REASON_LABELS = {
    "ma_death_cross": "MA 死叉",
    "ma_golden_cross": "MA 金叉",
    "ma_bearish_cross": "MA 死叉",
    "ma_bullish_cross": "MA 金叉",
    "rsi_overbought": "RSI 超买",
    "rsi_oversold": "RSI 超卖",
    "rsi_exit_overbought": "RSI 退出超买",
    "rsi_exit_oversold": "RSI 退出超卖",
    "boll_upper_break": "布林上轨突破",
    "boll_lower_break": "布林下轨突破",
    "boll_exit": "布林带回归",
    "signal": "信号反转",
    "stop_loss": "止损",
    "take_profit": "止盈",
    "risk_exit": "风险止损",
    "manual_close": "手动平仓",
    "strategy": "策略平仓",
    "unknown": "未识别",
}

# Map of entry signal codes to Chinese labels
_ENTRY_SIGNAL_LABELS = {
    "ma_golden_cross": "MA 金叉买入",
    "ma_bullish_cross": "MA 金叉买入",
    "rsi_oversold": "RSI 超卖买入",
    "ma_death_cross_short": "MA 死叉做空",
    "rsi_overbought_short": "RSI 超买做空",
    "signal_buy": "买入信号",
    "signal_sell": "做空信号",
    "unknown": "未识别信号",
}


def _label(reason: Optional[str], labels: dict) -> str:
    if not reason:
        return "未记录"
    return labels.get(reason, reason)


def enrich_trades(
    trades: list[dict],
    data_by_code: dict[str, pd.DataFrame],
    benchmark_df: Optional[pd.DataFrame] = None,
) -> list[dict]:
    """Enrich trade records with price context.

    Args:
        trades: Raw trade list from backtest engine.
        data_by_code: {code: DataFrame with columns: date, open, high, low, close}
        benchmark_df: Optional benchmark DataFrame with date+close columns.

    Returns:
        Enriched trade list with additional fields.
    """
    if not trades:
        return trades

    # Normalize benchmark index
    bench_series: Optional[pd.Series] = None
    if benchmark_df is not None and not benchmark_df.empty:
        date_col = "date" if "date" in benchmark_df.columns else "datetime"
        if date_col in benchmark_df.columns:
            benchmark_df = benchmark_df.copy()
            benchmark_df[date_col] = pd.to_datetime(benchmark_df[date_col])
            bench_series = benchmark_df.set_index(date_col)["close"]

    enriched = []
    for trade in trades:
        code = trade.get("code", "")
        entry_date_str = trade.get("entry_date", "")
        exit_date_str = trade.get("exit_date", "")

        if not code or not entry_date_str:
            enriched.append(_mark_unenriched(trade))
            continue

        df = data_by_code.get(code)
        if df is None or df.empty:
            enriched.append(_mark_unenriched(trade))
            continue

        date_col = "date" if "date" in df.columns else "datetime"
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)

        try:
            entry_dt = pd.to_datetime(entry_date_str)
            exit_dt = pd.to_datetime(exit_date_str)
        except Exception:
            enriched.append(_mark_unenriched(trade))
            continue

        # Find bar index for entry and exit
        entry_idx = df.index.get_indexer([entry_dt], method="nearest")
        exit_idx = df.index.get_indexer([exit_dt], method="nearest")

        if entry_idx[0] < 0 or exit_idx[0] < 0:
            enriched.append(_mark_unenriched(trade))
            continue

        entry_idx, exit_idx = int(entry_idx[0]), int(exit_idx[0])

        # Extract prices
        entry_price = float(df.iloc[entry_idx]["close"])
        exit_price = float(df.iloc[exit_idx]["close"])

        # High / low during holding period
        holding = df.iloc[entry_idx:exit_idx + 1]
        high_price = float(holding["high"].max()) if "high" in holding.columns else None
        low_price = float(holding["low"].min()) if "low" in holding.columns else None

        # Position value from entry price
        size = abs(trade.get("size", 0))
        position_value = round(entry_price * size, 2) if size > 0 else None

        # Benchmark values at entry/exit
        bench_entry, bench_exit, relative_return = None, None, None
        if bench_series is not None:
            bench_entry = _nearest_value(bench_series, entry_dt)
            bench_exit = _nearest_value(bench_series, exit_dt)
            if bench_entry and bench_exit and bench_entry > 0:
                stock_return = (exit_price - entry_price) / entry_price
                bench_return = (bench_exit - bench_entry) / bench_entry
                relative_return = round((stock_return - bench_return) * 100, 2)

        enriched_trade = {
            **trade,
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "high_price": round(high_price, 2) if high_price else None,
            "low_price": round(low_price, 2) if low_price else None,
            "position_value": position_value,
            "bench_entry": round(bench_entry, 4) if bench_entry else None,
            "bench_exit": round(bench_exit, 4) if bench_exit else None,
            "relative_return": relative_return,
            "entry_signal": _label(trade.get("entry_signal"), _ENTRY_SIGNAL_LABELS),
            "exit_reason": _label(trade.get("exit_reason"), _EXIT_REASON_LABELS),
        }
        enriched.append(enriched_trade)

    return enriched


def _nearest_value(series: pd.Series, dt, tol: str = "1D") -> Optional[float]:
    """Get nearest value in series to dt within tolerance."""
    idx = series.index.get_indexer([dt], method="nearest")[0]
    if idx < 0:
        return None
    try:
        return float(series.iloc[idx])
    except (IndexError, ValueError):
        return None


def _mark_unenriched(trade: dict) -> dict:
    """Return trade with enrichment fields set to None."""
    return {
        **trade,
        "entry_price": None,
        "exit_price": None,
        "high_price": None,
        "low_price": None,
        "position_value": None,
        "bench_entry": None,
        "bench_exit": None,
        "relative_return": None,
        "entry_signal": "未记录",
        "exit_reason": "未记录",
    }
