# -*- coding: utf-8 -*-
"""Forecast endpoint — on-demand TimesFM price prediction."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{stock_code}", summary="Get price forecast for a stock")
async def get_forecast(stock_code: str, horizon: int = 5):
    """Return TimesFM price forecast for the given stock code."""
    from src.config import get_config

    config = get_config()
    if not config.enable_forecast:
        return JSONResponse(
            status_code=503,
            content={"error": "forecast_disabled", "message": "时序预测功能未启用，请设置 ENABLE_FORECAST=true"},
        )

    if horizon < 1 or horizon > 30:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_horizon", "message": "预测天数需在 1-30 之间"},
        )

    try:
        from src.services.forecast_service import ForecastService
        from src.storage import get_db
        import pandas as pd

        db = get_db()
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        bars = db.get_data_range(stock_code, start_date, end_date)

        if not bars or len(bars) < 30:
            return JSONResponse(
                status_code=400,
                content={"error": "insufficient_data", "message": f"历史数据不足（需要至少30条，当前{len(bars) if bars else 0}条）"},
            )

        df = pd.DataFrame([bar.to_dict() for bar in bars])
        service = ForecastService()
        result = service.forecast(df, stock_code, horizon_days=horizon)

        if result is None:
            return JSONResponse(
                status_code=500,
                content={"error": "forecast_failed", "message": "预测失败，请稍后重试"},
            )

        return result.to_dict()

    except Exception as e:
        logger.error(f"Forecast endpoint error for {stock_code}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": str(e)},
        )
