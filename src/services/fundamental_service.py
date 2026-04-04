# -*- coding: utf-8 -*-
"""
Fundamental data service — unified interface for financial statements and ratios.

Supports A-shares (via AkShare) and US stocks (via yfinance).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _detect_market(stock_code: str) -> str:
    """Detect market from stock code. Returns 'cn', 'us', or 'hk'."""
    code = str(stock_code).strip().upper()
    if code.isdigit() and len(code) == 6:
        return "cn"
    if code.endswith(".HK"):
        return "hk"
    # Assume US for alphabetic codes
    if code.isalpha():
        return "us"
    return "cn"


class FundamentalService:
    """Unified fundamental data service for A-shares and US stocks."""

    def get_income_statement(self, stock_code: str, periods: int = 4) -> dict:
        """Get income statement data for recent quarters."""
        market = _detect_market(stock_code)
        if market == "cn":
            return self._cn_income_statement(stock_code, periods)
        return self._us_income_statement(stock_code, periods)

    def get_balance_sheet(self, stock_code: str) -> dict:
        """Get latest balance sheet data."""
        market = _detect_market(stock_code)
        if market == "cn":
            return self._cn_balance_sheet(stock_code)
        return self._us_balance_sheet(stock_code)

    def get_cash_flow(self, stock_code: str, periods: int = 4) -> dict:
        """Get cash flow statement data."""
        market = _detect_market(stock_code)
        if market == "cn":
            return self._cn_cash_flow(stock_code, periods)
        return self._us_cash_flow(stock_code, periods)

    def get_key_ratios(self, stock_code: str) -> dict:
        """Get key financial ratios: PE, PB, ROE, margins, debt ratios, etc."""
        market = _detect_market(stock_code)
        if market == "cn":
            return self._cn_key_ratios(stock_code)
        return self._us_key_ratios(stock_code)

    def get_valuation_metrics(self, stock_code: str) -> dict:
        """Get valuation-specific metrics for DCF/comparable analysis."""
        market = _detect_market(stock_code)
        if market == "cn":
            return self._cn_valuation(stock_code)
        return self._us_valuation(stock_code)

    def get_comprehensive(self, stock_code: str) -> dict:
        """Get all fundamental data in one call."""
        result = {"stock_code": stock_code, "market": _detect_market(stock_code)}
        for key, method in [
            ("income_statement", self.get_income_statement),
            ("balance_sheet", self.get_balance_sheet),
            ("cash_flow", self.get_cash_flow),
            ("key_ratios", self.get_key_ratios),
            ("valuation", self.get_valuation_metrics),
        ]:
            try:
                result[key] = method(stock_code)
            except Exception as e:
                logger.warning("get_comprehensive(%s) %s failed: %s", stock_code, key, e)
                result[key] = {"error": str(e)}
        return result

    # ── A-share implementations (AkShare) ──

    def _cn_income_statement(self, stock_code: str, periods: int) -> dict:
        try:
            import akshare as ak
            df = ak.stock_financial_abstract_ths(symbol=stock_code, indicator="按报告期")
            if df is None or df.empty:
                return {"error": "No income data available"}
            df = df.head(periods)
            return self._df_to_records(df, "income_statement")
        except Exception as e:
            logger.warning("cn_income_statement(%s) failed: %s", stock_code, e)
            return {"error": str(e)}

    def _cn_balance_sheet(self, stock_code: str) -> dict:
        try:
            import akshare as ak
            df = ak.stock_financial_abstract_ths(symbol=stock_code, indicator="按报告期")
            if df is None or df.empty:
                return {"error": "No balance sheet data available"}
            return self._df_to_records(df.head(1), "balance_sheet")
        except Exception as e:
            logger.warning("cn_balance_sheet(%s) failed: %s", stock_code, e)
            return {"error": str(e)}

    def _cn_cash_flow(self, stock_code: str, periods: int) -> dict:
        try:
            import akshare as ak
            df = ak.stock_financial_abstract_ths(symbol=stock_code, indicator="按报告期")
            if df is None or df.empty:
                return {"error": "No cash flow data available"}
            return self._df_to_records(df.head(periods), "cash_flow")
        except Exception as e:
            logger.warning("cn_cash_flow(%s) failed: %s", stock_code, e)
            return {"error": str(e)}

    def _cn_key_ratios(self, stock_code: str) -> dict:
        try:
            import akshare as ak
            # Financial indicators from THS
            df = ak.stock_financial_analysis_indicator(symbol=stock_code, start_year="2023")
            if df is None or df.empty:
                return {"error": "No ratio data available"}
            latest = df.iloc[0]
            return self._extract_cn_ratios(latest)
        except Exception as e:
            logger.warning("cn_key_ratios(%s) failed: %s", stock_code, e)
            return {"error": str(e)}

    def _cn_valuation(self, stock_code: str) -> dict:
        try:
            import akshare as ak
            df = ak.stock_a_indicator_lg(symbol=stock_code)
            if df is None or df.empty:
                return {"error": "No valuation data available"}
            latest = df.iloc[-1]
            result = {}
            for col in ["pe", "pe_ttm", "pb", "ps", "ps_ttm", "dv_ratio", "dv_ttm", "total_mv"]:
                if col in latest.index:
                    val = latest[col]
                    result[col] = round(float(val), 4) if pd.notna(val) else None
            return result
        except Exception as e:
            logger.warning("cn_valuation(%s) failed: %s", stock_code, e)
            return {"error": str(e)}

    def _extract_cn_ratios(self, row) -> dict:
        """Extract key ratios from AkShare financial indicator row."""
        result = {}
        mapping = {
            "净资产收益率": "roe",
            "总资产收益率": "roa",
            "毛利率": "gross_margin",
            "净利率": "net_margin",
            "资产负债率": "debt_ratio",
            "流动比率": "current_ratio",
            "速动比率": "quick_ratio",
            "每股收益": "eps",
            "每股净资产": "bvps",
            "营业收入同比增长率": "revenue_growth",
            "净利润同比增长率": "profit_growth",
        }
        for cn_name, en_name in mapping.items():
            if cn_name in row.index:
                val = row[cn_name]
                result[en_name] = round(float(val), 4) if pd.notna(val) else None
        return result

    # ── US stock implementations (yfinance) ──

    def _us_income_statement(self, stock_code: str, periods: int) -> dict:
        try:
            import yfinance as yf
            ticker = yf.Ticker(stock_code)
            df = ticker.quarterly_income_stmt
            if df is None or df.empty:
                return {"error": "No income data available"}
            df = df.iloc[:, :periods]
            return self._yf_financial_to_dict(df, "income_statement")
        except Exception as e:
            logger.warning("us_income_statement(%s) failed: %s", stock_code, e)
            return {"error": str(e)}

    def _us_balance_sheet(self, stock_code: str) -> dict:
        try:
            import yfinance as yf
            ticker = yf.Ticker(stock_code)
            df = ticker.quarterly_balance_sheet
            if df is None or df.empty:
                return {"error": "No balance sheet data available"}
            return self._yf_financial_to_dict(df.iloc[:, :1], "balance_sheet")
        except Exception as e:
            logger.warning("us_balance_sheet(%s) failed: %s", stock_code, e)
            return {"error": str(e)}

    def _us_cash_flow(self, stock_code: str, periods: int) -> dict:
        try:
            import yfinance as yf
            ticker = yf.Ticker(stock_code)
            df = ticker.quarterly_cashflow
            if df is None or df.empty:
                return {"error": "No cash flow data available"}
            df = df.iloc[:, :periods]
            return self._yf_financial_to_dict(df, "cash_flow")
        except Exception as e:
            logger.warning("us_cash_flow(%s) failed: %s", stock_code, e)
            return {"error": str(e)}

    def _us_key_ratios(self, stock_code: str) -> dict:
        try:
            import yfinance as yf
            ticker = yf.Ticker(stock_code)
            info = ticker.info or {}
            return {
                "pe": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb": info.get("priceToBook"),
                "ps": info.get("priceToSalesTrailing12Months"),
                "roe": info.get("returnOnEquity"),
                "roa": info.get("returnOnAssets"),
                "gross_margin": info.get("grossMargins"),
                "net_margin": info.get("profitMargins"),
                "debt_to_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "eps": info.get("trailingEps"),
                "revenue_growth": info.get("revenueGrowth"),
                "earnings_growth": info.get("earningsGrowth"),
                "dividend_yield": info.get("dividendYield"),
                "market_cap": info.get("marketCap"),
            }
        except Exception as e:
            logger.warning("us_key_ratios(%s) failed: %s", stock_code, e)
            return {"error": str(e)}

    def _us_valuation(self, stock_code: str) -> dict:
        try:
            import yfinance as yf
            ticker = yf.Ticker(stock_code)
            info = ticker.info or {}
            return {
                "pe_ttm": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb": info.get("priceToBook"),
                "ps_ttm": info.get("priceToSalesTrailing12Months"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "ev_revenue": info.get("enterpriseToRevenue"),
                "market_cap": info.get("marketCap"),
                "enterprise_value": info.get("enterpriseValue"),
                "free_cash_flow": info.get("freeCashflow"),
                "operating_cash_flow": info.get("operatingCashflow"),
            }
        except Exception as e:
            logger.warning("us_valuation(%s) failed: %s", stock_code, e)
            return {"error": str(e)}

    # ── Helpers ──

    @staticmethod
    def _df_to_records(df: pd.DataFrame, label: str) -> dict:
        """Convert DataFrame to list of dicts with NaN handling."""
        records = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                if pd.notna(val):
                    record[col] = float(val) if isinstance(val, (int, float)) else str(val)
            records.append(record)
        return {"type": label, "periods": len(records), "data": records}

    @staticmethod
    def _yf_financial_to_dict(df: pd.DataFrame, label: str) -> dict:
        """Convert yfinance financial DataFrame (rows=items, cols=dates) to dict."""
        periods = []
        for col in df.columns:
            period_data = {"period": str(col.date()) if hasattr(col, "date") else str(col)}
            for idx in df.index:
                val = df.loc[idx, col]
                if pd.notna(val):
                    period_data[str(idx)] = float(val)
            periods.append(period_data)
        return {"type": label, "periods": len(periods), "data": periods}
