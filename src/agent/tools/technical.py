# -*- coding: utf-8 -*-
"""
Technical indicator tools — wraps TAIndicatorService as agent-callable tools.

Tools:
- get_technical_indicators: compute all 43 ta indicators for a stock
- get_technical_signals: extract trading signals from indicators
- get_selected_indicators: compute specific indicators by name
"""

import logging
from typing import Optional

from src.agent.tools.registry import ToolParameter, ToolDefinition

logger = logging.getLogger(__name__)


def _fetch_ohlcv(stock_code: str, days: int = 90):
    """Fetch OHLCV DataFrame for a stock. DB first, then DataFetcherManager fallback."""
    from datetime import date, timedelta
    import pandas as pd
    from data_provider.base import canonical_stock_code, DataFetchError
    from src.storage import get_db

    code = canonical_stock_code(stock_code)
    if not code:
        return None

    end_date = date.today()
    start_date = end_date - timedelta(days=int(days * 1.5))  # extra buffer for trading days

    # 1. Try DB
    try:
        db = get_db()
        bars = db.get_data_range(code, start_date, end_date)
        if bars and len(bars) >= 20:
            df = pd.DataFrame([b.to_dict() for b in bars])
            return df
    except Exception as e:
        logger.debug("technical_indicators(%s): DB lookup failed: %s", stock_code, e)

    # 2. Fallback to DataFetcherManager
    try:
        from data_provider import DataFetcherManager
        manager = DataFetcherManager()
        df, _ = manager.get_daily_data(code, days=days)
        if df is not None and not df.empty:
            return df
    except DataFetchError as e:
        logger.warning("technical_indicators(%s): DataFetcherManager failed: %s", stock_code, e)
    except Exception as e:
        logger.warning("technical_indicators(%s): unexpected error: %s", stock_code, e)

    return None


def _get_ta_service():
    from src.services.ta_indicator_service import TAIndicatorService
    return TAIndicatorService()


def _handle_get_technical_indicators(stock_code: str, days: int = 90) -> dict:
    """Compute all 43 technical indicators for a stock."""
    if not (stock_code and str(stock_code).strip()):
        return {"error": "stock_code is required"}

    df = _fetch_ohlcv(stock_code, days)
    if df is None or df.empty:
        return {"error": f"No data available for {stock_code}"}
    if len(df) < 20:
        return {"error": f"Insufficient data for {stock_code} (need >= 20 days, got {len(df)})"}

    try:
        service = _get_ta_service()
        result_df = service.compute_all(df)
        summary = service.get_summary(result_df)
        signals = service.get_signals(result_df)
        return {
            "stock_code": stock_code,
            "data_points": len(result_df),
            "indicators": summary,
            "signals": signals,
        }
    except Exception as e:
        logger.warning("get_technical_indicators(%s) failed: %s", stock_code, e, exc_info=True)
        return {"error": f"Failed to compute indicators: {e}"}


def _handle_get_technical_signals(stock_code: str) -> dict:
    """Extract trading signals (golden cross, overbought, etc.) from indicators."""
    if not (stock_code and str(stock_code).strip()):
        return {"error": "stock_code is required"}

    df = _fetch_ohlcv(stock_code, 90)
    if df is None or df.empty:
        return {"error": f"No data available for {stock_code}"}
    if len(df) < 20:
        return {"error": f"Insufficient data for {stock_code}"}

    try:
        service = _get_ta_service()
        result_df = service.compute_all(df)
        signals = service.get_signals(result_df)
        return {
            "stock_code": stock_code,
            "signals": signals,
            "signal_count": len(signals),
        }
    except Exception as e:
        logger.warning("get_technical_signals(%s) failed: %s", stock_code, e, exc_info=True)
        return {"error": f"Failed to extract signals: {e}"}


def _handle_get_selected_indicators(stock_code: str, indicators: str, days: int = 90) -> dict:
    """Compute specific indicators by name (comma-separated)."""
    if not (stock_code and str(stock_code).strip()):
        return {"error": "stock_code is required"}
    if not indicators:
        return {"error": "indicators list is required"}

    indicator_list = [i.strip() for i in indicators.split(",") if i.strip()]
    if not indicator_list:
        return {"error": "No valid indicator names provided"}

    df = _fetch_ohlcv(stock_code, days)
    if df is None or df.empty:
        return {"error": f"No data available for {stock_code}"}

    try:
        service = _get_ta_service()
        result_df = service.compute_selected(df, indicator_list)
        # Return last 5 rows of requested indicators
        cols = [c for c in indicator_list if c in result_df.columns]
        if not cols:
            return {"error": f"None of the requested indicators could be computed"}

        latest = result_df[cols].tail(5).round(4).to_dict(orient="records")
        return {
            "stock_code": stock_code,
            "indicators": cols,
            "recent_values": latest,
        }
    except Exception as e:
        logger.warning("get_selected_indicators(%s) failed: %s", stock_code, e, exc_info=True)
        return {"error": f"Failed to compute indicators: {e}"}


get_technical_indicators_tool = ToolDefinition(
    name="get_technical_indicators",
    description="Compute all 43 technical indicators (RSI, MACD, Bollinger Bands, ADX, "
                "Ichimoku, Stochastic, ATR, OBV, MFI, VWAP, etc.) for a stock. "
                "Returns indicator summary grouped by category (trend, momentum, "
                "volatility, volume) plus trading signals (golden/death cross, "
                "overbought/oversold).",
    parameters=[
        ToolParameter(
            name="stock_code",
            type="string",
            description="Stock code, e.g., '600519' or 'AAPL'",
        ),
        ToolParameter(
            name="days",
            type="integer",
            description="Number of trading days of history to use (default: 90)",
            required=False,
            default=90,
        ),
    ],
    handler=_handle_get_technical_indicators,
    category="analysis",
)

get_technical_signals_tool = ToolDefinition(
    name="get_technical_signals",
    description="Extract trading signals from technical indicators: MACD golden/death cross, "
                "RSI overbought/oversold, Bollinger Band squeeze/breakout, Stochastic crossovers. "
                "Quick signal check without full indicator dump.",
    parameters=[
        ToolParameter(
            name="stock_code",
            type="string",
            description="Stock code, e.g., '600519'",
        ),
    ],
    handler=_handle_get_technical_signals,
    category="analysis",
)

get_selected_indicators_tool = ToolDefinition(
    name="get_selected_indicators",
    description="Compute specific technical indicators by name. "
                "Available: sma_20, sma_50, sma_200, ema_12, ema_26, macd, macd_signal, "
                "macd_histogram, adx, rsi_14, stoch_rsi, bb_upper, bb_lower, bb_width, "
                "atr, obv, mfi, vwap, cmf, williams_r, tsi, psar, aroon_up, aroon_down, etc.",
    parameters=[
        ToolParameter(
            name="stock_code",
            type="string",
            description="Stock code, e.g., '600519'",
        ),
        ToolParameter(
            name="indicators",
            type="string",
            description="Comma-separated indicator names, e.g., 'rsi_14,macd,bb_upper,bb_lower'",
        ),
        ToolParameter(
            name="days",
            type="integer",
            description="Number of trading days (default: 90)",
            required=False,
            default=90,
        ),
    ],
    handler=_handle_get_selected_indicators,
    category="analysis",
)

ALL_TECHNICAL_TOOLS = [
    get_technical_indicators_tool,
    get_technical_signals_tool,
    get_selected_indicators_tool,
]
