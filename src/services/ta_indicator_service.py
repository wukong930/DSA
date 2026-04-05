# -*- coding: utf-8 -*-
"""Technical Analysis Indicator Service.

Wraps the `ta` library to compute 43 technical indicators on OHLCV DataFrames.
Provides full-set computation, selective computation, and signal extraction.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
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


# ---------------------------------------------------------------------------
# Indicator metadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IndicatorMeta:
    category: str       # 原始分类: trend / momentum / volatility / volume
    description: str    # 英文描述: "SMA 20"
    cn_name: str        # 中文名: "20日均线"
    cn_desc: str        # 通俗解释
    scenario: str       # 场景分组: timing / trend / risk / flow


# Indicator category registry: name → IndicatorMeta
INDICATOR_CATALOG: dict[str, IndicatorMeta] = {
    # ── Trend ──
    "sma_20":          IndicatorMeta("trend", "SMA 20",                  "20日均线",       "近20天平均价格，判断短期趋势方向",           "trend"),
    "sma_50":          IndicatorMeta("trend", "SMA 50",                  "50日均线",       "近50天平均价格，判断中期趋势方向",           "trend"),
    "sma_200":         IndicatorMeta("trend", "SMA 200",                 "200日均线",      "近200天平均价格，判断长期趋势（牛熊分界线）", "trend"),
    "ema_12":          IndicatorMeta("trend", "EMA 12",                  "12日指数均线",   "对近期价格更敏感的短期均线",                 "trend"),
    "ema_26":          IndicatorMeta("trend", "EMA 26",                  "26日指数均线",   "中期指数均线，常与EMA12配合使用",            "trend"),
    "macd":            IndicatorMeta("trend", "MACD Line",               "MACD 线",        "快慢均线差值，判断趋势动能变化",             "timing"),
    "macd_signal":     IndicatorMeta("trend", "MACD Signal",             "MACD 信号线",    "MACD的平滑线，金叉死叉的参考线",            "timing"),
    "macd_histogram":  IndicatorMeta("trend", "MACD Histogram",          "MACD 柱状图",    "MACD与信号线的差值，红柱看涨绿柱看跌",      "timing"),
    "adx":             IndicatorMeta("trend", "ADX",                     "趋势强度 ADX",   "衡量趋势强弱，>25有趋势 <20无趋势",         "trend"),
    "adx_pos":         IndicatorMeta("trend", "ADX +DI",                 "ADX 多头指标",   "多头力量强度，越高多头越强",                 "trend"),
    "adx_neg":         IndicatorMeta("trend", "ADX -DI",                 "ADX 空头指标",   "空头力量强度，越高空头越强",                 "trend"),
    "ichimoku_a":      IndicatorMeta("trend", "Ichimoku Span A",         "一目均衡 先行A", "云层上沿，价格在云层上方为多头",             "trend"),
    "ichimoku_b":      IndicatorMeta("trend", "Ichimoku Span B",         "一目均衡 先行B", "云层下沿，价格在云层下方为空头",             "trend"),
    "ichimoku_base":   IndicatorMeta("trend", "Ichimoku Base Line",      "一目均衡 基准线", "中期均衡价格，可作为支撑/阻力参考",         "trend"),
    "ichimoku_conv":   IndicatorMeta("trend", "Ichimoku Conversion Line","一目均衡 转换线", "短期均衡价格，与基准线交叉产生信号",         "trend"),
    "psar":            IndicatorMeta("trend", "Parabolic SAR",           "抛物线 SAR",     "跟踪止损指标，点在价格下方为多头",           "trend"),
    "aroon_up":        IndicatorMeta("trend", "Aroon Up",                "阿隆上升线",     "衡量上升趋势强度，越高上涨趋势越强",         "trend"),
    "aroon_down":      IndicatorMeta("trend", "Aroon Down",              "阿隆下降线",     "衡量下降趋势强度，越高下跌趋势越强",         "trend"),
    "aroon_indicator": IndicatorMeta("trend", "Aroon Indicator",         "阿隆振荡器",     "上升线与下降线之差，正值看涨负值看跌",       "trend"),
    # ── Momentum ──
    "rsi_14":          IndicatorMeta("momentum", "RSI 14",               "RSI 相对强弱(14日)", ">70超买可能回调，<30超卖可能反弹",       "timing"),
    "stoch_rsi":       IndicatorMeta("momentum", "Stochastic RSI",       "随机RSI",            "RSI的随机指标化，更灵敏的超买超卖信号",   "timing"),
    "stoch_rsi_k":     IndicatorMeta("momentum", "Stochastic RSI %K",    "随机RSI %K线",       "随机RSI快线，与%D交叉产生买卖信号",       "timing"),
    "stoch_rsi_d":     IndicatorMeta("momentum", "Stochastic RSI %D",    "随机RSI %D线",       "随机RSI慢线，用于确认%K线信号",           "timing"),
    "stoch_k":         IndicatorMeta("momentum", "Stochastic %K",        "KDJ %K线",           "随机指标快线，>80超买 <20超卖",           "timing"),
    "stoch_d":         IndicatorMeta("momentum", "Stochastic %D",        "KDJ %D线",           "随机指标慢线，与%K交叉产生金叉死叉",      "timing"),
    "tsi":             IndicatorMeta("momentum", "TSI",                   "真实强度指数",       "双重平滑动量指标，正值看涨负值看跌",       "timing"),
    "williams_r":      IndicatorMeta("momentum", "Williams %R",          "威廉指标",           ">-20超买可能回调，<-80超卖可能反弹",       "timing"),
    # ── Volatility ──
    "bb_upper":        IndicatorMeta("volatility", "Bollinger Upper",    "布林带上轨",     "价格触及上轨可能回落",                       "risk"),
    "bb_middle":       IndicatorMeta("volatility", "Bollinger Middle",   "布林带中轨",     "20日均线，布林带的中心线",                   "risk"),
    "bb_lower":        IndicatorMeta("volatility", "Bollinger Lower",    "布林带下轨",     "价格触及下轨可能反弹",                       "risk"),
    "bb_width":        IndicatorMeta("volatility", "Bollinger Width",    "布林带宽度",     "带宽越窄波动越小，可能即将变盘",             "risk"),
    "bb_pband":        IndicatorMeta("volatility", "Bollinger %B",       "布林带 %B",      "价格在布林带中的位置，>1超买 <0超卖",        "risk"),
    "atr":             IndicatorMeta("volatility", "ATR",                "平均真实波幅",   "衡量价格波动幅度，越大风险越高",             "risk"),
    "kc_upper":        IndicatorMeta("volatility", "Keltner Upper",      "肯特纳上轨",     "基于ATR的通道上沿，突破可能加速上涨",        "risk"),
    "kc_middle":       IndicatorMeta("volatility", "Keltner Middle",     "肯特纳中轨",     "指数均线，通道的中心线",                     "risk"),
    "kc_lower":        IndicatorMeta("volatility", "Keltner Lower",      "肯特纳下轨",     "基于ATR的通道下沿，跌破可能加速下跌",        "risk"),
    "dc_upper":        IndicatorMeta("volatility", "Donchian Upper",     "唐奇安上轨",     "N日最高价，突破为买入信号",                  "risk"),
    "dc_middle":       IndicatorMeta("volatility", "Donchian Middle",    "唐奇安中轨",     "N日最高最低价的中间值",                      "risk"),
    "dc_lower":        IndicatorMeta("volatility", "Donchian Lower",     "唐奇安下轨",     "N日最低价，跌破为卖出信号",                  "risk"),
    # ── Volume ──
    "obv":             IndicatorMeta("volume", "OBV",                    "能量潮 OBV",     "累计成交量判断资金流入流出方向",             "flow"),
    "mfi":             IndicatorMeta("volume", "MFI",                    "资金流量指数",   ">80资金过热，<20资金不足，类似RSI",          "flow"),
    "vwap":            IndicatorMeta("volume", "VWAP",                   "成交量加权均价", "当日平均成本线，机构常用参考价",             "flow"),
    "cmf":             IndicatorMeta("volume", "Chaikin Money Flow",     "蔡金资金流",     "正值资金流入看涨，负值资金流出看跌",         "flow"),
    "force_index":     IndicatorMeta("volume", "Force Index",            "力量指数",       "结合价格变化和成交量的动量指标",             "flow"),
}

# ---------------------------------------------------------------------------
# Preset strategy templates (方案 C)
# ---------------------------------------------------------------------------

PRESET_TEMPLATES: list[dict] = [
    {
        "key": "golden_cross",
        "name": "金叉买入",
        "description": "MACD 金叉，短期动能转强，买入信号",
        "conditions": [{"indicator": "macd_histogram", "op": "cross_above", "value": 0}],
    },
    {
        "key": "oversold_bounce",
        "name": "超卖反弹",
        "description": "RSI 低于 30 进入超卖区间，可能反弹",
        "conditions": [{"indicator": "rsi_14", "op": "<", "value": 30}],
    },
    {
        "key": "overbought_warning",
        "name": "超买预警",
        "description": "RSI 高于 70 进入超买区间，注意回调风险",
        "conditions": [{"indicator": "rsi_14", "op": ">", "value": 70}],
    },
    {
        "key": "bollinger_breakout",
        "name": "突破上轨",
        "description": "价格突破布林带上轨，可能开启上涨行情",
        "conditions": [{"indicator": "close", "op": ">", "indicator2": "bb_upper"}],
    },
    {
        "key": "trend_follow",
        "name": "趋势跟踪",
        "description": "ADX 确认趋势存在，价格站上 50 日均线",
        "conditions": [
            {"indicator": "adx", "op": ">", "value": 25},
            {"indicator": "close", "op": ">", "indicator2": "sma_50"},
        ],
    },
    {
        "key": "death_cross",
        "name": "死叉卖出",
        "description": "MACD 死叉，短期动能转弱，卖出信号",
        "conditions": [{"indicator": "macd_histogram", "op": "cross_below", "value": 0}],
    },
]


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

        for name, meta in INDICATOR_CATALOG.items():
            val = latest.get(name)
            if pd.notna(val):
                summary[meta.category][name] = {
                    "label": meta.description,
                    "value": round(float(val), 4),
                }

        return summary

    @staticmethod
    def list_indicators() -> dict[str, list[dict]]:
        """Return available indicators grouped by category (legacy format)."""
        result: dict[str, list[dict]] = {}
        for name, meta in INDICATOR_CATALOG.items():
            result.setdefault(meta.category, []).append({"name": name, "description": meta.description})
        return result

    @staticmethod
    def list_indicators_rich() -> dict[str, list[dict]]:
        """Return indicators grouped by scenario with rich metadata."""
        result: dict[str, list[dict]] = {}
        for name, meta in INDICATOR_CATALOG.items():
            result.setdefault(meta.scenario, []).append({
                "name": name,
                "cn_name": meta.cn_name,
                "cn_desc": meta.cn_desc,
                "description": meta.description,
                "category": meta.category,
            })
        return result

    @staticmethod
    def list_templates() -> list[dict]:
        """Return preset strategy templates."""
        return PRESET_TEMPLATES
