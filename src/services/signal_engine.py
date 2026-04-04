# -*- coding: utf-8 -*-
"""Signal Engine — evaluate technical indicator conditions and emit signals.

Used by the monitoring service (Phase 3) and filter service (Phase 5).
Conditions are expressed as simple dicts so they can be stored as JSON in the DB.

Condition format:
    {"indicator": "rsi_14", "op": ">", "value": 70}
    {"indicator": "macd_histogram", "op": "cross_above", "value": 0}
    {"indicator": "close", "op": ">", "indicator2": "sma_200"}

Supported operators:
    >  <  >=  <=  ==
    cross_above   — previous row was ≤ value, current row is > value
    cross_below   — previous row was ≥ value, current row is < value
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)

OPERATORS = frozenset({">", "<", ">=", "<=", "==", "cross_above", "cross_below"})


@dataclass
class Signal:
    """A triggered signal from a condition evaluation."""

    indicator: str
    op: str
    threshold: float | str
    actual_value: float
    triggered_at: datetime = field(default_factory=datetime.now)
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "indicator": self.indicator,
            "op": self.op,
            "threshold": self.threshold,
            "actual_value": round(self.actual_value, 4),
            "triggered_at": self.triggered_at.isoformat(),
            "description": self.description,
        }


class SignalEngine:
    """Evaluate conditions against a DataFrame with indicator columns."""

    def evaluate(
        self,
        df: pd.DataFrame,
        conditions: list[dict],
    ) -> list[Signal]:
        """Evaluate all conditions against the latest rows of df.

        Args:
            df: DataFrame with indicator columns (output of TAIndicatorService).
            conditions: List of condition dicts.

        Returns:
            List of Signal objects for conditions that triggered.
        """
        if df is None or len(df) < 2:
            return []

        signals: list[Signal] = []
        for cond in conditions:
            try:
                signal = self._eval_one(df, cond)
                if signal:
                    signals.append(signal)
            except Exception as exc:
                logger.warning("Failed to evaluate condition %s: %s", cond, exc)
        return signals

    def evaluate_all_rows(
        self,
        df: pd.DataFrame,
        conditions: list[dict],
    ) -> pd.DataFrame:
        """Return a boolean DataFrame indicating which rows trigger each condition.

        Useful for backtesting or historical signal scanning.
        """
        if df is None or df.empty:
            return pd.DataFrame()

        result = pd.DataFrame(index=df.index)
        for i, cond in enumerate(conditions):
            col_name = self._condition_label(cond)
            result[col_name] = self._eval_series(df, cond)
        return result

    def _eval_one(self, df: pd.DataFrame, cond: dict) -> Optional[Signal]:
        """Evaluate a single condition against the last row."""
        indicator = cond.get("indicator", "")
        op = cond.get("op", "")
        indicator2 = cond.get("indicator2")

        if op not in OPERATORS:
            logger.warning("Unknown operator: %s", op)
            return None

        if indicator not in df.columns:
            logger.warning("Indicator '%s' not found in DataFrame columns", indicator)
            return None

        current = df[indicator].iloc[-1]
        if pd.isna(current):
            return None

        # Determine threshold: either a fixed value or another indicator column
        if indicator2:
            if indicator2 not in df.columns:
                logger.warning("Indicator2 '%s' not found in DataFrame columns", indicator2)
                return None
            threshold = df[indicator2].iloc[-1]
            if pd.isna(threshold):
                return None
            threshold_label = indicator2
        else:
            threshold = cond.get("value")
            if threshold is None:
                logger.warning("Condition missing 'value' or 'indicator2': %s", cond)
                return None
            threshold = float(threshold)
            threshold_label = threshold

        triggered = False

        if op == ">":
            triggered = current > threshold
        elif op == "<":
            triggered = current < threshold
        elif op == ">=":
            triggered = current >= threshold
        elif op == "<=":
            triggered = current <= threshold
        elif op == "==":
            triggered = abs(current - threshold) < 1e-9
        elif op in ("cross_above", "cross_below"):
            if len(df) < 2:
                return None
            prev = df[indicator].iloc[-2]
            if pd.isna(prev):
                return None
            if indicator2:
                prev_threshold = df[indicator2].iloc[-2]
                if pd.isna(prev_threshold):
                    return None
            else:
                prev_threshold = threshold

            if op == "cross_above":
                triggered = prev <= prev_threshold and current > threshold
            else:  # cross_below
                triggered = prev >= prev_threshold and current < threshold

        if not triggered:
            return None

        desc = f"{indicator} {op} {threshold_label} (actual: {current:.4f})"
        return Signal(
            indicator=indicator,
            op=op,
            threshold=threshold_label,
            actual_value=float(current),
            description=desc,
        )

    def _eval_series(self, df: pd.DataFrame, cond: dict) -> pd.Series:
        """Evaluate a condition across all rows, returning a boolean Series."""
        indicator = cond.get("indicator", "")
        op = cond.get("op", "")
        indicator2 = cond.get("indicator2")

        if indicator not in df.columns:
            return pd.Series(False, index=df.index)

        series = df[indicator]

        if indicator2:
            if indicator2 not in df.columns:
                return pd.Series(False, index=df.index)
            threshold_series = df[indicator2]
        else:
            val = cond.get("value")
            if val is None:
                return pd.Series(False, index=df.index)
            threshold_series = float(val)

        if op == ">":
            return series > threshold_series
        elif op == "<":
            return series < threshold_series
        elif op == ">=":
            return series >= threshold_series
        elif op == "<=":
            return series <= threshold_series
        elif op == "==":
            return (series - threshold_series).abs() < 1e-9
        elif op == "cross_above":
            prev = series.shift(1)
            if isinstance(threshold_series, pd.Series):
                prev_thresh = threshold_series.shift(1)
            else:
                prev_thresh = threshold_series
            return (prev <= prev_thresh) & (series > threshold_series)
        elif op == "cross_below":
            prev = series.shift(1)
            if isinstance(threshold_series, pd.Series):
                prev_thresh = threshold_series.shift(1)
            else:
                prev_thresh = threshold_series
            return (prev >= prev_thresh) & (series < threshold_series)

        return pd.Series(False, index=df.index)

    @staticmethod
    def _condition_label(cond: dict) -> str:
        indicator = cond.get("indicator", "?")
        op = cond.get("op", "?")
        indicator2 = cond.get("indicator2")
        if indicator2:
            return f"{indicator}_{op}_{indicator2}"
        return f"{indicator}_{op}_{cond.get('value', '?')}"

    @staticmethod
    def validate_condition(cond: dict) -> Optional[str]:
        """Validate a condition dict. Returns error message or None if valid."""
        if not isinstance(cond, dict):
            return "Condition must be a dict"
        indicator = cond.get("indicator")
        if not indicator:
            return "Missing 'indicator' field"
        op = cond.get("op")
        if op not in OPERATORS:
            return f"Invalid operator '{op}'. Must be one of: {', '.join(sorted(OPERATORS))}"
        if not cond.get("indicator2") and cond.get("value") is None:
            return "Must provide 'value' or 'indicator2'"
        if cond.get("value") is not None:
            try:
                float(cond["value"])
            except (TypeError, ValueError):
                return f"'value' must be numeric, got: {cond['value']}"
        return None

    @staticmethod
    def validate_conditions(conditions: list[dict]) -> Optional[str]:
        """Validate a list of conditions. Returns first error or None."""
        if not isinstance(conditions, list):
            return "Conditions must be a list"
        for i, cond in enumerate(conditions):
            err = SignalEngine.validate_condition(cond)
            if err:
                return f"Condition [{i}]: {err}"
        return None
