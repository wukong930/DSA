# -*- coding: utf-8 -*-
"""
Fundamental analysis tools — wraps FundamentalService as agent-callable tools.

Tools:
- get_fundamentals: comprehensive fundamental data (financials + ratios)
- get_financial_ratios: key financial ratios only
- get_valuation_data: valuation metrics for comparable/DCF analysis
"""

import logging

from src.agent.tools.registry import ToolParameter, ToolDefinition

logger = logging.getLogger(__name__)


def _get_service():
    from src.services.fundamental_service import FundamentalService
    return FundamentalService()


def _handle_get_fundamentals(stock_code: str) -> dict:
    """Get comprehensive fundamental data for a stock."""
    if not (stock_code and str(stock_code).strip()):
        return {"error": "stock_code is required"}
    try:
        return _get_service().get_comprehensive(stock_code)
    except Exception as e:
        logger.warning("get_fundamentals(%s) failed: %s", stock_code, e, exc_info=True)
        return {"error": f"Failed to get fundamentals: {e}"}


def _handle_get_financial_ratios(stock_code: str) -> dict:
    """Get key financial ratios for a stock."""
    if not (stock_code and str(stock_code).strip()):
        return {"error": "stock_code is required"}
    try:
        ratios = _get_service().get_key_ratios(stock_code)
        return {"stock_code": stock_code, "ratios": ratios}
    except Exception as e:
        logger.warning("get_financial_ratios(%s) failed: %s", stock_code, e, exc_info=True)
        return {"error": f"Failed to get ratios: {e}"}


def _handle_get_valuation_data(stock_code: str) -> dict:
    """Get valuation metrics for a stock."""
    if not (stock_code and str(stock_code).strip()):
        return {"error": "stock_code is required"}
    try:
        valuation = _get_service().get_valuation_metrics(stock_code)
        return {"stock_code": stock_code, "valuation": valuation}
    except Exception as e:
        logger.warning("get_valuation_data(%s) failed: %s", stock_code, e, exc_info=True)
        return {"error": f"Failed to get valuation: {e}"}


def _handle_dcf_estimate(stock_code: str, growth_rate: float = 0.1, discount_rate: float = 0.1, terminal_growth: float = 0.03, years: int = 5) -> dict:
    """Simple DCF valuation estimate based on free cash flow."""
    if not (stock_code and str(stock_code).strip()):
        return {"error": "stock_code is required"}
    try:
        service = _get_service()
        valuation = service.get_valuation_metrics(stock_code)
        if "error" in valuation:
            return valuation

        # Try to get FCF from valuation data
        fcf = valuation.get("free_cash_flow")
        market_cap = valuation.get("market_cap") or valuation.get("total_mv")

        if not fcf:
            # Fallback: try cash flow statement
            cf = service.get_cash_flow(stock_code, periods=1)
            if "error" not in cf and cf.get("data"):
                latest = cf["data"][0]
                fcf = latest.get("Free Cash Flow") or latest.get("经营活动产生的现金流量净额")

        if not fcf:
            return {"error": "Cannot determine free cash flow for DCF calculation"}

        fcf = float(fcf)
        # Project future FCFs
        projected_fcfs = []
        for year in range(1, years + 1):
            projected = fcf * ((1 + growth_rate) ** year)
            discounted = projected / ((1 + discount_rate) ** year)
            projected_fcfs.append({
                "year": year,
                "projected_fcf": round(projected, 2),
                "discounted_fcf": round(discounted, 2),
            })

        # Terminal value
        terminal_fcf = fcf * ((1 + growth_rate) ** years) * (1 + terminal_growth)
        terminal_value = terminal_fcf / (discount_rate - terminal_growth)
        discounted_terminal = terminal_value / ((1 + discount_rate) ** years)

        total_pv = sum(p["discounted_fcf"] for p in projected_fcfs) + discounted_terminal

        result = {
            "stock_code": stock_code,
            "base_fcf": round(fcf, 2),
            "assumptions": {
                "growth_rate": growth_rate,
                "discount_rate": discount_rate,
                "terminal_growth": terminal_growth,
                "projection_years": years,
            },
            "projected_fcfs": projected_fcfs,
            "terminal_value": round(terminal_value, 2),
            "discounted_terminal": round(discounted_terminal, 2),
            "intrinsic_value": round(total_pv, 2),
        }
        if market_cap:
            market_cap = float(market_cap)
            result["market_cap"] = round(market_cap, 2)
            result["upside_pct"] = round((total_pv / market_cap - 1) * 100, 2) if market_cap > 0 else None

        return result
    except Exception as e:
        logger.warning("dcf_estimate(%s) failed: %s", stock_code, e, exc_info=True)
        return {"error": f"DCF calculation failed: {e}"}


get_fundamentals_tool = ToolDefinition(
    name="get_fundamentals",
    description="Get comprehensive fundamental data for a stock: income statement, "
                "balance sheet, cash flow, key ratios (ROE, margins, debt), and valuation. "
                "Supports A-shares (AkShare) and US stocks (yfinance).",
    parameters=[
        ToolParameter(
            name="stock_code",
            type="string",
            description="Stock code, e.g., '600519' for A-shares or 'AAPL' for US stocks",
        ),
    ],
    handler=_handle_get_fundamentals,
    category="data",
)

get_financial_ratios_tool = ToolDefinition(
    name="get_financial_ratios",
    description="Get key financial ratios: PE, PB, ROE, ROA, gross/net margin, "
                "debt ratio, current ratio, EPS, revenue/profit growth.",
    parameters=[
        ToolParameter(
            name="stock_code",
            type="string",
            description="Stock code, e.g., '600519' or 'AAPL'",
        ),
    ],
    handler=_handle_get_financial_ratios,
    category="data",
)

get_valuation_data_tool = ToolDefinition(
    name="get_valuation_data",
    description="Get valuation metrics: PE/PB/PS (TTM), EV/EBITDA, market cap, "
                "enterprise value, dividend yield. For comparable analysis.",
    parameters=[
        ToolParameter(
            name="stock_code",
            type="string",
            description="Stock code, e.g., '600519' or 'AAPL'",
        ),
    ],
    handler=_handle_get_valuation_data,
    category="data",
)

dcf_estimate_tool = ToolDefinition(
    name="dcf_estimate",
    description="Simple DCF (Discounted Cash Flow) valuation estimate. "
                "Projects future free cash flows and calculates intrinsic value. "
                "Returns projected FCFs, terminal value, and upside/downside vs market cap.",
    parameters=[
        ToolParameter(
            name="stock_code",
            type="string",
            description="Stock code, e.g., '600519' or 'AAPL'",
        ),
        ToolParameter(
            name="growth_rate",
            type="number",
            description="Expected annual FCF growth rate (default: 0.1 = 10%)",
            required=False,
            default=0.1,
        ),
        ToolParameter(
            name="discount_rate",
            type="number",
            description="Discount rate / WACC (default: 0.1 = 10%)",
            required=False,
            default=0.1,
        ),
        ToolParameter(
            name="terminal_growth",
            type="number",
            description="Terminal growth rate (default: 0.03 = 3%)",
            required=False,
            default=0.03,
        ),
        ToolParameter(
            name="years",
            type="integer",
            description="Projection years (default: 5)",
            required=False,
            default=5,
        ),
    ],
    handler=_handle_dcf_estimate,
    category="analysis",
)

ALL_FUNDAMENTAL_TOOLS = [
    get_fundamentals_tool,
    get_financial_ratios_tool,
    get_valuation_data_tool,
    dcf_estimate_tool,
]
