# -*- coding: utf-8 -*-
"""Technical Analysis Indicator Service.

Wraps the `ta` library to compute 43 technical indicators on OHLCV DataFrames.
Provides full-set computation, selective computation, and signal extraction.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import ta
from ta.momentum import (
    RSIIndicator,
    StochRSIIndicator,
    StochasticOscillator,
    TSIIndicator,
    WilliamsRIndicator,
)
from ta.trend import (
    MACD,
    ADXIndicator,
    AroonIndicator,
    EMAIndicator,
    IchimokuIndicator,
    PSARIndicator,
    SMAIndicator,
)
from ta.volatility import (
    AverageTrueRange,
    BollingerBands,
    DonchianChannel,
    KeltnerChannel,
)
from ta.volume import (
    ChaikinMoneyFlowIndicator,
    ForceIndexIndicator,
    MFIIndicator,
    OnBalanceVolumeIndicator,
    VolumeWeightedAveragePrice,
)

logger = logging.getLogger(__name__)

# Indicator category registry: name → (category, description)
INDICATOR_CATALOG: dict[str, tuple[str, str]] = {
    # Trend
    "sma_20": ("trend", "SMA 20"),
    "sma_50": ("trend", "SMA 50"),
    "sma_200": ("trend", "SMA 200"),
    "ema_12": ("trend", "EMA 12"),
    "ema_26": ("trend", "EMA 26"),
    "macd": ("trend", "MACD Line"),
    "macd_signal": ("trend", "MACD Signal"),
    "macd_histogram": ("trend", "MACD Histogram"),
    "adx": ("trend", "ADX"),
    "adx_pos": ("trend", "ADX +DI"),
    "adx_neg": ("trend", "ADX -DI"),
    "ichimoku_a": ("trend", "Ichimoku Span A"),
    "ichimoku_b": ("trend", "Ichimoku Span B"),
    "ichimoku_base": ("trend", "Ichimoku Base Line"),
    "ichimoku_conv": ("trend", "Ichimoku Conversion Line"),
    "psar": ("trend", "Parabolic SAR"),
    "aroon_up": ("trend", "Aroon Up"),
    "aroon_down": ("trend", "Aroon Down"),
    "aroon_indicator": ("trend", "Aroon Indicator"),
    # Momentum
    "rsi_14": ("momentum", "RSI 14"),
    "stoch_rsi": ("momentum", "Stochastic RSI"),
    "stoch_rsi_k": ("momentum", "Stochastic RSI %K"),
    "stoch_rsi_d": ("momentum", "Stochastic RSI %D"),
    "stoch_k": ("momentum", "Stochastic %K"),
    "stoch_d": ("momentum", "Stochastic %D"),
    "tsi": ("momentum", "TSI"),
    "williams_r": ("momentum", "Williams %R"),
    # Volatility
    "bb_upper": ("volatility", "Bollinger Upper"),
    "bb_middle": ("volatility", "Bollinger Middle"),
    "bb_lower": ("volatility", "Bollinger Lower"),
    "bb_width": ("volatility", "Bollinger Width"),
    "bb_pband": ("volatility", "Bollinger %B"),
    "atr": ("volatility", "ATR"),
    "kc_upper": ("volatility", "Keltner Upper"),
    "kc_middle": ("volatility", "Keltner Middle"),
    "kc_lower": ("volatility", "Keltner Lower"),
    "dc_upper": ("volatility", "Donchian Upper"),
    "dc_middle": ("volatility", "Donchian Middle"),
    "dc_lower": ("volatility", "Donchian Lower"),
    # Volume
    "obv": ("volume", "OBV"),
    "mfi": ("volume", "MFI"),
    "vwap": ("volume", "VWAP"),
    "cmf": ("volume", "Chaikin Money Flow"),
    "force_index": ("volume", "Force Index"),
}


class TAIndicatorService:
    """Compute technical indicators on OHLCV DataFrames."""

    # Required columns in input DataFrame
    REQUIRED_COLS = {"open", "high", "low", "close", "volume"}

    def _validate_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and normalize column names to lowercase."""
        df = df.copy()
        df.columns = [c.lower().strip() for c in df.columns]
        missing = self.REQUIRED_COLS - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame missing required columns: {missing}")
        # Ensure numeric
        for col in self.REQUIRED_COLS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def compute_all(self, df: pd.DataFrame, fillna: bool = False) -> pd.DataFrame:
        """Compute all 43 indicators. Returns original df with indicator columns appended."""
        df = self._validate_df(df)
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        # ── Trend ──
        df["sma_20"] = SMAIndicator(close, window=20, fillna=fillna).sma_indicator()
        df["sma_50"] = SMAIndicator(close, window=50, fillna=fillna).sma_indicator()
        df["sma_200"] = SMAIndicator(close, window=200, fillna=fillna).sma_indicator()
        df["ema_12"] = EMAIndicator(close, window=12, fillna=fillna).ema_indicator()
        df["ema_26"] = EMAIndicator(close, window=26, fillna=fillna).ema_indicator()

        macd = MACD(close, fillna=fillna)
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_histogram"] = macd.macd_diff()

        adx = ADXIndicator(high, low, close, fillna=fillna)
        df["adx"] = adx.adx()
        df["adx_pos"] = adx.adx_pos()
        df["adx_neg"] = adx.adx_neg()

        ichimoku = IchimokuIndicator(high, low, fillna=fillna)
        df["ichimoku_a"] = ichimoku.ichimoku_a()
        df["ichimoku_b"] = ichimoku.ichimoku_b()
        df["ichimoku_base"] = ichimoku.ichimoku_base_line()
        df["ichimoku_conv"] = ichimoku.ichimoku_conversion_line()

        df["psar"] = PSARIndicator(high, low, close, fillna=fillna).psar()

        aroon = AroonIndicator(high, low, fillna=fillna)
        df["aroon_up"] = aroon.aroon_up()
        df["aroon_down"] = aroon.aroon_down()
        df["aroon_indicator"] = aroon.aroon_indicator()

        # ── Momentum ──
        df["rsi_14"] = RSIIndicator(close, window=14, fillna=fillna).rsi()

        stoch_rsi = StochRSIIndicator(close, fillna=fillna)
        df["stoch_rsi"] = stoch_rsi.stochrsi()
        df["stoch_rsi_k"] = stoch_rsi.stochrsi_k()
        df["stoch_rsi_d"] = stoch_rsi.stochrsi_d()

        stoch = StochasticOscillator(high, low, close, fillna=fillna)
        df["stoch_k"] = stoch.stoch()
        df["stoch_d"] = stoch.stoch_signal()

        df["tsi"] = TSIIndicator(close, fillna=fillna).tsi()
        df["williams_r"] = WilliamsRIndicator(high, low, close, fillna=fillna).williams_r()

        # ── Volatility ──
        bb = BollingerBands(close, fillna=fillna)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_middle"] = bb.bollinger_mavg()
        df["bb_lower"] = bb.bollinger_lband()
        df["bb_width"] = bb.bollinger_wband()
        df["bb_pband"] = bb.bollinger_pband()

        df["atr"] = AverageTrueRange(high, low, close, fillna=fillna).average_true_range()

        kc = KeltnerChannel(high, low, close, fillna=fillna)
        df["kc_upper"] = kc.keltner_channel_hband()
        df["kc_middle"] = kc.keltner_channel_mband()
        df["kc_lower"] = kc.keltner_channel_lband()

        dc = DonchianChannel(high, low, close, fillna=fillna)
        df["dc_upper"] = dc.donchian_channel_hband()
        df["dc_middle"] = dc.donchian_channel_mband()
        df["dc_lower"] = dc.donchian_channel_lband()

        # ── Volume ──
        df["obv"] = OnBalanceVolumeIndicator(close, volume, fillna=fillna).on_balance_volume()
        df["mfi"] = MFIIndicator(high, low, close, volume, fillna=fillna).money_flow_index()
        df["vwap"] = VolumeWeightedAveragePrice(high, low, close, volume, fillna=fillna).volume_weighted_average_price()
        df["cmf"] = ChaikinMoneyFlowIndicator(high, low, close, volume, fillna=fillna).chaikin_money_flow()
        df["force_index"] = ForceIndexIndicator(close, volume, fillna=fillna).force_index()

        return df

    def compute_selected(
        self, df: pd.DataFrame, indicators: list[str], fillna: bool = False
    ) -> pd.DataFrame:
        """Compute only the specified indicators by name.

        Uses compute_all internally then filters columns. For large datasets
        where only a few indicators are needed, this avoids manual wiring
        while keeping the API simple.
        """
        known = set(INDICATOR_CATALOG.keys())
        unknown = set(indicators) - known
        if unknown:
            logger.warning("Unknown indicators requested (skipped): %s", unknown)

        wanted = [i for i in indicators if i in known]
        if not wanted:
            return self._validate_df(df)

        result = self.compute_all(df, fillna=fillna)
        # Keep original columns + requested indicator columns
        original_cols = list(self._validate_df(df).columns)
        keep = original_cols + [c for c in wanted if c in result.columns]
        return result[keep]

    def get_signals(self, df: pd.DataFrame) -> dict:
        """Extract common trading signals from the latest row of indicator data.

        Returns a dict with signal categories and their states.
        Expects df to already have indicator columns (call compute_all first).
        """
        if df.empty:
            return {}

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        signals: dict = {}

        # RSI
        rsi = latest.get("rsi_14")
        if pd.notna(rsi):
            if rsi > 70:
                signals["rsi"] = {"value": round(rsi, 2), "signal": "overbought"}
            elif rsi < 30:
                signals["rsi"] = {"value": round(rsi, 2), "signal": "oversold"}
            else:
                signals["rsi"] = {"value": round(rsi, 2), "signal": "neutral"}

        # MACD crossover
        macd_val = latest.get("macd")
        macd_sig = latest.get("macd_signal")
        prev_macd = prev.get("macd")
        prev_sig = prev.get("macd_signal")
        if all(pd.notna(v) for v in [macd_val, macd_sig, prev_macd, prev_sig]):
            if prev_macd <= prev_sig and macd_val > macd_sig:
                signals["macd"] = {"value": round(macd_val, 4), "signal": "golden_cross"}
            elif prev_macd >= prev_sig and macd_val < macd_sig:
                signals["macd"] = {"value": round(macd_val, 4), "signal": "death_cross"}
            else:
                signals["macd"] = {
                    "value": round(macd_val, 4),
                    "signal": "bullish" if macd_val > macd_sig else "bearish",
                }

        # Bollinger Bands position
        close = latest.get("close")
        bb_upper = latest.get("bb_upper")
        bb_lower = latest.get("bb_lower")
        if all(pd.notna(v) for v in [close, bb_upper, bb_lower]):
            if close > bb_upper:
                signals["bollinger"] = {"signal": "above_upper"}
            elif close < bb_lower:
                signals["bollinger"] = {"signal": "below_lower"}
            else:
                signals["bollinger"] = {"signal": "within_bands"}

        # SMA trend (price vs SMA 20/50)
        sma_20 = latest.get("sma_20")
        sma_50 = latest.get("sma_50")
        if pd.notna(close) and pd.notna(sma_20) and pd.notna(sma_50):
            if close > sma_20 > sma_50:
                signals["sma_trend"] = {"signal": "strong_bullish"}
            elif close < sma_20 < sma_50:
                signals["sma_trend"] = {"signal": "strong_bearish"}
            elif close > sma_20:
                signals["sma_trend"] = {"signal": "bullish"}
            else:
                signals["sma_trend"] = {"signal": "bearish"}

        # ADX trend strength
        adx_val = latest.get("adx")
        adx_pos = latest.get("adx_pos")
        adx_neg = latest.get("adx_neg")
        if all(pd.notna(v) for v in [adx_val, adx_pos, adx_neg]):
            direction = "bullish" if adx_pos > adx_neg else "bearish"
            if adx_val > 25:
                signals["adx"] = {"value": round(adx_val, 2), "signal": f"strong_{direction}"}
            else:
                signals["adx"] = {"value": round(adx_val, 2), "signal": "weak_trend"}

        # MFI
        mfi = latest.get("mfi")
        if pd.notna(mfi):
            if mfi > 80:
                signals["mfi"] = {"value": round(mfi, 2), "signal": "overbought"}
            elif mfi < 20:
                signals["mfi"] = {"value": round(mfi, 2), "signal": "oversold"}
            else:
                signals["mfi"] = {"value": round(mfi, 2), "signal": "neutral"}

        # Williams %R
        wr = latest.get("williams_r")
        if pd.notna(wr):
            if wr > -20:
                signals["williams_r"] = {"value": round(wr, 2), "signal": "overbought"}
            elif wr < -80:
                signals["williams_r"] = {"value": round(wr, 2), "signal": "oversold"}
            else:
                signals["williams_r"] = {"value": round(wr, 2), "signal": "neutral"}

        # Stochastic
        stoch_k = latest.get("stoch_k")
        stoch_d = latest.get("stoch_d")
        prev_k = prev.get("stoch_k")
        prev_d = prev.get("stoch_d")
        if all(pd.notna(v) for v in [stoch_k, stoch_d, prev_k, prev_d]):
            if prev_k <= prev_d and stoch_k > stoch_d:
                signals["stochastic"] = {"value": round(stoch_k, 2), "signal": "golden_cross"}
            elif prev_k >= prev_d and stoch_k < stoch_d:
                signals["stochastic"] = {"value": round(stoch_k, 2), "signal": "death_cross"}
            elif stoch_k > 80:
                signals["stochastic"] = {"value": round(stoch_k, 2), "signal": "overbought"}
            elif stoch_k < 20:
                signals["stochastic"] = {"value": round(stoch_k, 2), "signal": "oversold"}
            else:
                signals["stochastic"] = {"value": round(stoch_k, 2), "signal": "neutral"}

        return signals

    def get_summary(self, df: pd.DataFrame) -> dict:
        """Get a concise summary of the latest indicator values.

        Returns a dict organized by category with rounded values.
        Expects df to already have indicator columns.
        """
        if df.empty:
            return {}

        latest = df.iloc[-1]
        summary: dict = {"trend": {}, "momentum": {}, "volatility": {}, "volume": {}}

        for name, (category, desc) in INDICATOR_CATALOG.items():
            val = latest.get(name)
            if pd.notna(val):
                summary[category][name] = {
                    "label": desc,
                    "value": round(float(val), 4),
                }

        return summary

    @staticmethod
    def list_indicators() -> dict[str, list[dict]]:
        """Return available indicators grouped by category."""
        result: dict[str, list[dict]] = {}
        for name, (category, desc) in INDICATOR_CATALOG.items():
            result.setdefault(category, []).append({"name": name, "description": desc})
        return result
