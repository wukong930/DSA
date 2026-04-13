# -*- coding: utf-8 -*-
"""Built-in factors for strategy backtesting."""

from __future__ import annotations

import pandas as pd

from src.backtest_bt.factors.base import BaseFactor, FactorRegistry


@FactorRegistry.register
class MAGoldenCross(BaseFactor):
    """MA5 crosses above MA20."""
    name = "ma_golden_cross"
    description = "MA5 上穿 MA20 金叉信号"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        ma5 = df["close"].rolling(5).mean()
        ma20 = df["close"].rolling(20).mean()
        cross = (ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))
        return cross.astype(float)


@FactorRegistry.register
class MADeathCross(BaseFactor):
    """MA5 crosses below MA20."""
    name = "ma_death_cross"
    description = "MA5 下穿 MA20 死叉信号"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        ma5 = df["close"].rolling(5).mean()
        ma20 = df["close"].rolling(20).mean()
        cross = (ma5 < ma20) & (ma5.shift(1) >= ma20.shift(1))
        return cross.astype(float)


@FactorRegistry.register
class RSIFactor(BaseFactor):
    """RSI(14) value."""
    name = "rsi_14"
    description = "14 日 RSI 指标值"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        delta = df["close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, float("nan"))
        return 100 - (100 / (1 + rs))


@FactorRegistry.register
class MACDHistogram(BaseFactor):
    """MACD histogram (DIF - DEA)."""
    name = "macd_hist"
    description = "MACD 柱状图（DIF - DEA）"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        return (dif - dea) * 2


@FactorRegistry.register
class BollingerBandWidth(BaseFactor):
    """Bollinger Band width (normalized)."""
    name = "boll_width"
    description = "布林带宽度（标准化）"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        ma20 = df["close"].rolling(20).mean()
        std20 = df["close"].rolling(20).std()
        upper = ma20 + 2 * std20
        lower = ma20 - 2 * std20
        width = (upper - lower) / ma20
        return width


@FactorRegistry.register
class VolumePriceDivergence(BaseFactor):
    """Volume-price divergence: price up but volume down."""
    name = "vol_price_divergence"
    description = "量价背离（价涨量缩）"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        price_up = df["close"].pct_change() > 0
        vol_down = df["volume"].pct_change() < 0
        return (price_up & vol_down).astype(float)


@FactorRegistry.register
class VolumeRatio(BaseFactor):
    """5-day volume ratio vs 20-day average."""
    name = "volume_ratio"
    description = "5 日量比（相对 20 日均量）"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        vol5 = df["volume"].rolling(5).mean()
        vol20 = df["volume"].rolling(20).mean()
        return vol5 / vol20.replace(0, float("nan"))


@FactorRegistry.register
class BullTrend(BaseFactor):
    """Multi-MA bullish alignment: MA5 > MA10 > MA20."""
    name = "bull_trend"
    description = "多头排列（MA5 > MA10 > MA20）"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        ma5 = df["close"].rolling(5).mean()
        ma10 = df["close"].rolling(10).mean()
        ma20 = df["close"].rolling(20).mean()
        return ((ma5 > ma10) & (ma10 > ma20)).astype(float)
