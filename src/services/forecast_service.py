# -*- coding: utf-8 -*-
"""TimesFM v2.5 Price Forecast Service.

Wraps Google TimesFM 2.5 (200M) to predict future stock prices.
Lazy-loads the model on first call to avoid startup overhead.
Gated behind ENABLE_FORECAST config flag (default: False).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    """Prediction output from TimesFM."""
    stock_code: str
    horizon_days: int
    predicted_prices: list[float]          # point forecasts per day
    lower_bound: list[float]               # 80% confidence lower
    upper_bound: list[float]               # 80% confidence upper
    trend: str                             # "up" | "down" | "neutral"
    trend_pct: float                       # predicted % change over horizon
    last_close: float                      # last observed close price
    model_version: str = "timesfm-2.5-200m"

    def to_dict(self) -> dict:
        return {
            "stock_code": self.stock_code,
            "horizon_days": self.horizon_days,
            "predicted_prices": self.predicted_prices,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "trend": self.trend,
            "trend_pct": round(self.trend_pct, 2),
            "last_close": self.last_close,
            "model_version": self.model_version,
        }


class ForecastService:
    """TimesFM v2.5 200M price forecast service with lazy model loading."""

    def __init__(self):
        self._model = None

    def _ensure_model(self):
        """Load model on first use."""
        if self._model is not None:
            return

        try:
            import timesfm

            self._model = timesfm.TimesFm(
                hparams=timesfm.TimesFmHparams(
                    per_core_batch_size=32,
                    horizon_len=128,
                ),
                checkpoint=timesfm.TimesFmCheckpoint(
                    huggingface_repo_id="google/timesfm-2.5-200m-pytorch",
                ),
            )
            logger.info("TimesFM 2.5 200M model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load TimesFM model: {e}")
            raise

    def forecast(
        self,
        df: pd.DataFrame,
        stock_code: str,
        horizon_days: int = 5,
    ) -> Optional[ForecastResult]:
        """
        Predict future close prices.

        Args:
            df: OHLCV DataFrame with at least 60 rows, must have 'close' column.
            stock_code: Stock code for labeling.
            horizon_days: Number of trading days to predict (default 5).

        Returns:
            ForecastResult or None if prediction fails.
        """
        try:
            self._ensure_model()
        except Exception:
            return None

        df = df.copy()
        df.columns = [c.lower().strip() for c in df.columns]

        if "close" not in df.columns:
            logger.warning(f"{stock_code}: DataFrame missing 'close' column")
            return None

        close_series = df["close"].dropna().values.astype(np.float32)

        if len(close_series) < 30:
            logger.warning(f"{stock_code}: Not enough data for forecast ({len(close_series)} rows)")
            return None

        try:
            # TimesFM expects list of 1-D arrays
            point_forecast, quantile_forecast = self._model.forecast(
                [close_series],
                freq=[0],  # 0 = daily
                prediction_length=horizon_days,
            )

            predicted = point_forecast[0][:horizon_days].tolist()
            predicted = [round(p, 2) for p in predicted]

            # Quantile forecasts: index 0 = 10th percentile, index 8 = 90th percentile
            # Use 10th and 90th as confidence bounds
            if quantile_forecast is not None and len(quantile_forecast) > 0:
                q = quantile_forecast[0]
                lower = [round(float(q[i, 0]), 2) for i in range(min(horizon_days, q.shape[0]))]
                upper = [round(float(q[i, -1]), 2) for i in range(min(horizon_days, q.shape[0]))]
            else:
                # Fallback: ±3% band
                lower = [round(p * 0.97, 2) for p in predicted]
                upper = [round(p * 1.03, 2) for p in predicted]

            last_close = float(close_series[-1])
            final_predicted = predicted[-1] if predicted else last_close
            trend_pct = ((final_predicted - last_close) / last_close) * 100 if last_close > 0 else 0.0

            if trend_pct > 1.0:
                trend = "up"
            elif trend_pct < -1.0:
                trend = "down"
            else:
                trend = "neutral"

            result = ForecastResult(
                stock_code=stock_code,
                horizon_days=horizon_days,
                predicted_prices=predicted,
                lower_bound=lower,
                upper_bound=upper,
                trend=trend,
                trend_pct=trend_pct,
                last_close=last_close,
            )

            logger.info(
                f"{stock_code} forecast complete: trend={trend}, "
                f"change={trend_pct:+.2f}%, "
                f"predicted={predicted}"
            )
            return result

        except Exception as e:
            logger.error(f"{stock_code}: TimesFM forecast failed: {e}", exc_info=True)
            return None
