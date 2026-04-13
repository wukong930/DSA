# -*- coding: utf-8 -*-
"""Vectorbt-based full-market screening engine.

Uses vectorized operations for fast factor computation across thousands of stocks.
Supports lite mode (capped universe) and full mode (all A-shares + GPU).
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from src.backtest_bt.factors.base import BaseFactor
from src.data.external_loader import ExternalDataLoader

logger = logging.getLogger(__name__)

LITE_MAX_UNIVERSE = 500
FULL_MAX_UNIVERSE = 3000


class VectorbtScreener:
    """Full-market vectorized screening using vectorbt."""

    def __init__(self, loader: ExternalDataLoader, runtime_mode: str = "lite"):
        self.loader = loader
        self.runtime_mode = runtime_mode

    def screen(
        self,
        universe: list[str],
        factors: list[BaseFactor],
        start: str,
        end: str,
        top_n: int = 50,
    ) -> pd.DataFrame:
        """Screen universe by factor values, return top_n candidates.

        Convenience wrapper around screen_with_factors that discards factor data.
        """
        result_df, _ = self.screen_with_factors(universe, factors, start, end, top_n)
        return result_df

    def screen_with_factors(
        self,
        universe: list[str],
        factors: list[BaseFactor],
        start: str,
        end: str,
        top_n: int = 50,
    ) -> tuple[pd.DataFrame, dict[str, dict[str, pd.Series]]]:
        """Screen universe by factor values, return top_n candidates and factor time series.

        Args:
            universe: List of stock codes to screen.
            factors: Factor instances to compute.
            start: Start date (YYYY-MM-DD).
            end: End date (YYYY-MM-DD).
            top_n: Number of top stocks to return.

        Returns:
            (result_df, factor_data) where:
            - result_df: DataFrame with columns: code, factor values, composite_score
            - factor_data: {code: {factor_name: pd.Series}} full time series for each factor
        """
        if self.runtime_mode == "lite" and len(universe) > LITE_MAX_UNIVERSE:
            logger.info(
                "Lite mode: sampling %d from %d stocks",
                LITE_MAX_UNIVERSE, len(universe),
            )
            universe = sorted(universe)[:LITE_MAX_UNIVERSE]
        elif self.runtime_mode != "lite" and len(universe) > FULL_MAX_UNIVERSE:
            logger.warning(
                "Full mode: capping universe from %d to %d stocks to prevent OOM",
                len(universe), FULL_MAX_UNIVERSE,
            )
            universe = sorted(universe)[:FULL_MAX_UNIVERSE]

        data = self.loader.load_batch_daily(universe, start, end)
        if not data:
            logger.warning("No data loaded for screening")
            return pd.DataFrame(), {}

        rows = []
        factor_data: dict[str, dict[str, pd.Series]] = {}
        failed_factors = []
        for code, df in data.items():
            if len(df) < 20:
                continue
            factor_vals = {}
            code_factors: dict[str, pd.Series] = {}
            for factor in factors:
                try:
                    series = factor.compute(df)
                    # Store full time series for downstream strategy use
                    code_factors[factor.name] = series
                    last_val = series.iloc[-1] if len(series) > 0 else float("nan")
                    factor_vals[factor.name] = float(last_val) if pd.notna(last_val) else 0.0
                except Exception as e:
                    logger.warning("Factor %s failed for %s: %s", factor.name, code, e)
                    factor_vals[factor.name] = 0.0
                    failed_factors.append(f"{factor.name}({code}): {e}")
            rows.append({"code": code, **factor_vals})
            if code_factors:
                factor_data[code] = code_factors

        if not rows:
            return pd.DataFrame(), {}

        result = pd.DataFrame(rows)

        # Composite score: mean of all factor columns (normalized)
        factor_cols = [f.name for f in factors]
        for col in factor_cols:
            col_std = result[col].std()
            if col_std > 0:
                result[f"{col}_z"] = (result[col] - result[col].mean()) / col_std
            else:
                result[f"{col}_z"] = 0.0

        z_cols = [f"{c}_z" for c in factor_cols]
        result["composite_score"] = result[z_cols].mean(axis=1)
        result = result.sort_values("composite_score", ascending=False).head(top_n)

        # Clean up z-score columns
        result = result.drop(columns=z_cols)
        result = result.reset_index(drop=True)
        # Attach screening warnings for upstream consumption
        result.attrs["failed_factors"] = failed_factors

        # Filter factor_data to only include top_n codes
        top_codes = set(result["code"].tolist())
        factor_data = {c: v for c, v in factor_data.items() if c in top_codes}

        return result, factor_data

    def quick_backtest(
        self,
        code: str,
        signals: pd.Series,
        start: str,
        end: str,
        initial_cash: float = 1_000_000,
    ) -> dict:
        """Quick vectorized backtest for a single stock (preview mode).

        Args:
            code: Stock code.
            signals: Boolean series (True = hold, False = cash).
            start: Start date.
            end: End date.
            initial_cash: Starting capital.

        Returns:
            Dict with total_return_pct, max_drawdown_pct, trade_count.
        """
        try:
            import vectorbt as vbt
        except ImportError:
            logger.warning("vectorbt not installed, quick_backtest unavailable")
            return {"error": "vectorbt not installed"}

        df = self.loader.load_daily(code, start, end)
        close = df.set_index("date")["close"] if "date" in df.columns else df["close"]

        entries = signals & ~signals.shift(1, fill_value=False)
        exits = ~signals & signals.shift(1, fill_value=False)

        # Align to close index
        entries = entries.reindex(close.index, fill_value=False)
        exits = exits.reindex(close.index, fill_value=False)

        pf = vbt.Portfolio.from_signals(
            close, entries, exits, init_cash=initial_cash, freq="1D"
        )

        return {
            "total_return_pct": round(float(pf.total_return() * 100), 2),
            "max_drawdown_pct": round(float(pf.max_drawdown() * 100), 2),
            "trade_count": int(pf.trades.count()),
            "sharpe_ratio": round(float(pf.sharpe_ratio()), 4),
        }
