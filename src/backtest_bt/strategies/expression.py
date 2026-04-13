# -*- coding: utf-8 -*-
"""Expression-based custom strategy.

Allows users to define trading strategies via buy/sell condition expressions.
Expressions can reference OHLCV data and registered factor values.
"""

from __future__ import annotations

import logging
import re
from typing import Optional
import concurrent.futures

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Reuse AST validation from factor expression module
from src.backtest_bt.factors.expression import _validate_ast
from src.backtest_bt.formula_translator import translate_formula


def validate_strategy_expression(expr: str) -> Optional[str]:
    """Validate a strategy expression. Returns error message or None if valid."""
    if not expr or not expr.strip():
        return "表达式不能为空"
    if len(expr) > 1000:
        return "表达式过长（最多 1000 字符）"
    translated = translate_formula(expr)
    return _validate_ast(translated)


class StrategyRegistry:
    """Global registry for custom expression strategies."""

    _strategies: dict[str, dict] = {}

    @classmethod
    def register(
        cls, name: str, buy_expression: str, sell_expression: str, description: str = ""
    ) -> Optional[str]:
        """Register a custom strategy. Returns error message or None."""
        if not name or not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$", name):
            return "策略名称只能包含字母、数字和下划线，且以字母开头"

        err = validate_strategy_expression(buy_expression)
        if err:
            return f"买入条件: {err}"
        err = validate_strategy_expression(sell_expression)
        if err:
            return f"卖出条件: {err}"

        cls._strategies[name] = {
            "name": name,
            "buy_expression": buy_expression,
            "sell_expression": sell_expression,
            "description": description or f"自定义策略: buy={buy_expression}, sell={sell_expression}",
        }
        logger.info("Registered custom strategy: %s", name)
        return None

    @classmethod
    def get(cls, name: str) -> Optional[dict]:
        return cls._strategies.get(name)

    @classmethod
    def list_all(cls) -> list[dict]:
        return list(cls._strategies.values())

    @classmethod
    def remove(cls, name: str) -> bool:
        if name in cls._strategies:
            del cls._strategies[name]
            return True
        return False


def _build_namespace(df: pd.DataFrame, precomputed_factors: Optional[dict[str, pd.Series]] = None) -> dict:
    """Build evaluation namespace from a DataFrame, including factor values.

    Args:
        df: OHLCV DataFrame.
        precomputed_factors: Optional {factor_name: pd.Series} from screener.
            When provided, these are used directly instead of recomputing.
    """
    ns = {
        "np": np,
        "pd": pd,
        "close": df["close"],
        "open": df["open"],
        "high": df["high"],
        "low": df["low"],
        "volume": df.get("volume", pd.Series(0, index=df.index)),
        "amount": df.get("amount", pd.Series(0, index=df.index)),
        "shift": df["close"].shift,
        "rolling": df["close"].rolling,
        "pct_change": df["close"].pct_change,
        "abs": abs,
        "max": max,
        "min": min,
        "True": True,
        "False": False,
    }

    if precomputed_factors:
        # Use screener's pre-computed factor time series directly
        for name, series in precomputed_factors.items():
            # Reindex to align with backtest DataFrame's index
            ns[name] = series.reindex(df.index, method="ffill")
    else:
        # Fallback: compute factors from scratch
        from src.backtest_bt.factors.base import FactorRegistry
        import src.backtest_bt.factors.builtin  # noqa: F401 — trigger registration

        for name, factor_cls in FactorRegistry.get_all().items():
            try:
                factor = factor_cls()
                series = factor.compute(df)
                ns[name] = series
            except Exception:
                pass  # Skip factors that fail on this data

    return ns


def build_expression_strategy_class(name: str, buy_expr: str, sell_expr: str, factor_data: Optional[dict] = None):
    """Dynamically build a backtrader Strategy class from buy/sell expressions.

    Args:
        name: Strategy name.
        buy_expr: Buy condition expression.
        sell_expr: Sell condition expression.
        factor_data: Optional {code: {factor_name: pd.Series}} from screener.
    """
    import backtrader as bt

    # Translate TDX formulas to Python if needed
    translated_buy = translate_formula(buy_expr)
    translated_sell = translate_formula(sell_expr)

    # Capture factor_data in closure
    _factor_data = factor_data or {}

    class ExpressionStrategy(bt.Strategy):
        params = ()

        def __init__(self):
            self._completed_trades = []
            self._entry_signals = {}   # {data: (bar_idx, signal_str)}
            self._exit_reasons = {}    # {data: reason_str}
            self._buy_signals = {}
            self._sell_signals = {}
            self._bar_offsets = {}
            self._strategy_name = _name
            self._buy_expr_label = _name  # Use strategy name as label

            for d in self.datas:
                # Extract DataFrame from backtrader data feed
                df = _data_feed_to_df(d)
                if df.empty:
                    continue

                # Use pre-computed factors if available for this code
                code_factors = _factor_data.get(d._name, None)
                ns = _build_namespace(df, code_factors)
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        buy_future = executor.submit(
                            eval, translated_buy, {"__builtins__": {}}, ns  # noqa: S307
                        )
                        buy_series = buy_future.result(timeout=5)
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        sell_future = executor.submit(
                            eval, translated_sell, {"__builtins__": {}}, ns  # noqa: S307
                        )
                        sell_series = sell_future.result(timeout=5)

                    if not isinstance(buy_series, pd.Series):
                        buy_series = pd.Series(bool(buy_series), index=df.index)
                    if not isinstance(sell_series, pd.Series):
                        sell_series = pd.Series(bool(sell_series), index=df.index)

                    self._buy_signals[d] = buy_series.fillna(False).astype(bool).values
                    self._sell_signals[d] = sell_series.fillna(False).astype(bool).values
                    self._bar_offsets[d] = len(d) - len(df)
                except concurrent.futures.TimeoutError:
                    logger.warning("Strategy expression eval timed out (5s) for %s", d._name)
                    self._buy_signals[d] = np.array([])
                    self._sell_signals[d] = np.array([])
                except Exception as e:
                    logger.warning("Strategy expression eval failed for %s: %s", d._name, e)
                    self._buy_signals[d] = np.array([])
                    self._sell_signals[d] = np.array([])

        def next(self):
            for d in self.datas:
                buy_arr = self._buy_signals.get(d)
                sell_arr = self._sell_signals.get(d)
                if buy_arr is None or len(buy_arr) == 0:
                    continue

                idx = len(d) - 1 - self._bar_offsets.get(d, 0)
                if idx < 0 or idx >= len(buy_arr):
                    continue

                pos = self.getposition(d)
                if not pos.size and buy_arr[idx]:
                    price = d.close[0]
                    if price > 0:
                        available = self.broker.getcash() * 0.95
                        size = int(available / len(self.datas) / price / 100) * 100
                        if size >= 100:
                            # Record entry signal: use strategy name as signal label
                            self._entry_signals[d] = f"signal_buy[{self._strategy_name}]"
                            self.buy(data=d, size=size)
                elif pos.size and sell_arr[idx]:
                    if not hasattr(self, '_exit_reasons'):
                        self._exit_reasons = {}
                    self._exit_reasons[d] = f"signal_sell[{self._strategy_name}]"
                    self.close(data=d)

        def notify_trade(self, trade):
            if trade.isclosed:
                open_size = getattr(self, '_open_sizes', {}).pop(trade.ref, 0)
                cost = abs(trade.price * open_size) if open_size else 0.0
                entry_signal = getattr(self, '_entry_signals', {}).pop(trade.data, None)
                exit_reason = getattr(self, '_exit_reasons', {}).pop(trade.data, None)
                self._completed_trades.append({
                    "code": trade.data._name,
                    "entry_date": str(bt.num2date(trade.dtopen).date()),
                    "exit_date": str(bt.num2date(trade.dtclose).date()),
                    "return_pct": round(trade.pnlcomm / cost * 100, 2) if cost > 1e-9 else 0.0,
                    "holding_days": (bt.num2date(trade.dtclose) - bt.num2date(trade.dtopen)).days,
                    "pnl": round(trade.pnlcomm, 2),
                    "entry_signal": entry_signal,
                    "exit_reason": exit_reason,
                })
            elif trade.isopen:
                if not hasattr(self, '_open_sizes'):
                    self._open_sizes = {}
                self._open_sizes[trade.ref] = abs(trade.size)

    ExpressionStrategy.__name__ = f"ExprStrategy_{name}"
    return ExpressionStrategy


def _data_feed_to_df(data) -> pd.DataFrame:
    """Extract a pandas DataFrame from a backtrader data feed."""
    try:
        length = len(data)
        if length == 0:
            return pd.DataFrame()

        dates = [data.datetime.date(-length + i + 1) for i in range(length)]
        df = pd.DataFrame({
            "date": dates,
            "open": [data.open[-length + i + 1] for i in range(length)],
            "high": [data.high[-length + i + 1] for i in range(length)],
            "low": [data.low[-length + i + 1] for i in range(length)],
            "close": [data.close[-length + i + 1] for i in range(length)],
            "volume": [data.volume[-length + i + 1] for i in range(length)],
        })
        df = df.set_index("date")
        return df
    except Exception as e:
        logger.warning("Failed to extract DataFrame from data feed: %s", e)
        return pd.DataFrame()
