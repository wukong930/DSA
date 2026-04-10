# -*- coding: utf-8 -*-
"""TimesFM 2.5 Price Forecast Service.

Wraps Google TimesFM 2.5 (200M) to predict future stock prices.
Lazy-loads the model on first call to avoid startup overhead.
Gated behind ENABLE_FORECAST config flag (default: False).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
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
    lower_bound: list[float]               # 10th percentile lower
    upper_bound: list[float]               # 90th percentile upper
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
    """TimesFM 2.5 200M price forecast service with lazy model loading."""

    def __init__(self):
        self._model = None

    def _ensure_model(self):
        """Load model on first use."""
        if self._model is not None:
            return

        try:
            import timesfm
            import torch

            use_compile = torch.cuda.is_available()
            self._model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
                "google/timesfm-2.5-200m-pytorch",
                torch_compile=use_compile,
            )
            self._model.compile(timesfm.ForecastConfig(
                max_context=1024,
                max_horizon=256,
                normalize_inputs=True,
                use_continuous_quantile_head=True,
                force_flip_invariance=True,
                infer_is_positive=True,
                fix_quantile_crossing=True,
            ))
            device = "CUDA" if use_compile else "CPU"
            logger.info(f"TimesFM 2.5 200M model loaded successfully ({device}, compile={use_compile})")
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
            df: OHLCV DataFrame with at least 30 rows, must have 'close' column.
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

        horizon_days = min(horizon_days, 256)

        try:
            import torch
            with torch.no_grad():
                point_forecast, quantile_forecast = self._model.forecast(
                    horizon=horizon_days,
                    inputs=[close_series],
                )

            return self._build_result(
                stock_code, horizon_days, close_series,
                point_forecast[0], quantile_forecast[0] if quantile_forecast is not None and len(quantile_forecast) > 0 else None,
            )

        except Exception as e:
            logger.error(f"{stock_code}: TimesFM forecast failed: {e}", exc_info=True)
            return None

    def forecast_batch(
        self,
        stocks: list[tuple[pd.DataFrame, str]],
        horizon_days: int = 5,
    ) -> dict[str, Optional[ForecastResult]]:
        """
        Batch-predict multiple stocks in a single model call.

        Args:
            stocks: List of (DataFrame, stock_code) tuples.
            horizon_days: Number of trading days to predict.

        Returns:
            Dict mapping stock_code to ForecastResult (or None on failure).
        """
        try:
            self._ensure_model()
        except Exception:
            return {code: None for _, code in stocks}

        all_series: list[np.ndarray] = []
        valid_codes: list[str] = []
        skipped: dict[str, None] = {}

        for raw_df, stock_code in stocks:
            df = raw_df.copy()
            df.columns = [c.lower().strip() for c in df.columns]

            if "close" not in df.columns:
                logger.warning(f"{stock_code}: DataFrame missing 'close' column, skipping batch entry")
                skipped[stock_code] = None
                continue

            close_series = df["close"].dropna().values.astype(np.float32)
            if len(close_series) < 30:
                logger.warning(f"{stock_code}: Not enough data ({len(close_series)} rows), skipping batch entry")
                skipped[stock_code] = None
                continue

            all_series.append(close_series)
            valid_codes.append(stock_code)

        if not all_series:
            return skipped

        horizon_days = min(horizon_days, 256)

        try:
            import torch
            with torch.no_grad():
                point_forecasts, quantile_forecasts = self._model.forecast(
                    horizon=horizon_days,
                    inputs=all_series,
                )

            results: dict[str, Optional[ForecastResult]] = dict(skipped)
            for i, stock_code in enumerate(valid_codes):
                try:
                    q = quantile_forecasts[i] if quantile_forecasts is not None and i < len(quantile_forecasts) else None
                    results[stock_code] = self._build_result(
                        stock_code, horizon_days, all_series[i],
                        point_forecasts[i], q,
                    )
                except Exception as e:
                    logger.warning(f"{stock_code}: Failed to build result from batch: {e}")
                    results[stock_code] = None

            logger.info(f"Batch forecast complete: {len(valid_codes)} stocks in one call")
            return results

        except Exception as e:
            logger.error(f"Batch forecast failed: {e}", exc_info=True)
            return {code: None for _, code in stocks}

    @staticmethod
    def _build_result(
        stock_code: str,
        horizon_days: int,
        close_series: np.ndarray,
        point_forecast: np.ndarray,
        quantile_forecast: np.ndarray | None,
    ) -> ForecastResult:
        """Build a ForecastResult from raw model output."""
        predicted = [round(float(p), 2) for p in point_forecast[:horizon_days]]

        # v2.5 quantile shape: (horizon, 11) — mean + 10th to 90th percentiles
        # index 1 = 10th percentile (lower), index -1 = 90th percentile (upper)
        if quantile_forecast is not None and len(quantile_forecast) > 0:
            lower = [round(float(quantile_forecast[i, 1]), 2) for i in range(min(horizon_days, quantile_forecast.shape[0]))]
            upper = [round(float(quantile_forecast[i, -1]), 2) for i in range(min(horizon_days, quantile_forecast.shape[0]))]
        else:
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
