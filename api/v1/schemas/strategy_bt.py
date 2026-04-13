# -*- coding: utf-8 -*-
"""Pydantic schemas for strategy backtest API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# --- Request ---

class StrategyBtRunRequest(BaseModel):
    strategy_name: str = Field(default="ma_crossover", description="策略名称")
    strategy_params: dict[str, Any] = Field(default_factory=dict, description="策略参数")
    codes: list[str] = Field(default_factory=list, max_length=500, description="股票代码列表（最多500只）")
    start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    freq: str = Field(default="1d", description="数据频率: 1d / 1min / 5min")
    initial_cash: float = Field(default=1_000_000, ge=1000, le=100_000_000, description="初始资金")
    commission: float = Field(default=0.001, ge=0, le=0.1, description="手续费率")
    slippage: float = Field(default=0.001, ge=0, le=0.1, description="滑点率")
    benchmark: str = Field(default="000300", description="基准指数代码")
    screen_universe: bool = Field(default=False, description="是否先做全市场筛选")
    screen_factors: list[str] = Field(default_factory=list, description="筛选因子列表")
    screen_top_n: int = Field(default=50, ge=1, le=500, description="筛选 Top N")
    screen_lookback_days: int = Field(default=60, ge=10, le=365, description="筛选回看天数（用 start_date 之前的数据）")
    rebalance_days: int = Field(default=0, ge=0, le=365, description="再平衡周期（天），0=不再平衡")
    stop_loss_pct: Optional[float] = Field(default=None, ge=0, le=50, description="止损百分比")
    take_profit_pct: Optional[float] = Field(default=None, ge=0, le=200, description="止盈百分比")
    allow_short: bool = Field(default=False, description="是否允许做空")


# --- Response ---

class StrategyBtRunResponse(BaseModel):
    run_id: int
    status: str = "pending"


class StrategyBtRunSummary(BaseModel):
    id: int
    user_id: int
    strategy_name: str
    codes: list[str]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    freq: str = "1d"
    status: str = "pending"
    progress: Optional[str] = None
    total_return_pct: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    win_rate_pct: Optional[float] = None
    total_trades: Optional[int] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class StrategyBtRunDetail(StrategyBtRunSummary):
    strategy_params: dict[str, Any] = {}
    initial_cash: float = 1_000_000
    commission: float = 0.001
    benchmark: str = "000300"
    result: Optional[dict[str, Any]] = None


class StrategyInfo(BaseModel):
    name: str
    description: str


class FactorInfo(BaseModel):
    name: str
    description: str


class DatasetInfo(BaseModel):
    name: str
    freq: str
    source: str
    date_range: list[str] = []
    code_count: int = 0


class DataUploadResponse(BaseModel):
    message: str
    files_count: int
    dataset_name: str
    failed_files: list[str] = []


class CustomFactorRequest(BaseModel):
    name: str = Field(..., description="因子名称（字母/数字/下划线）")
    expression: str = Field(..., description="Python 表达式，可用变量: close, open, high, low, volume")
    description: str = Field(default="", description="因子描述")


class CustomFactorResponse(BaseModel):
    name: str
    message: str


class CustomStrategyRequest(BaseModel):
    name: str = Field(..., description="策略名称（字母/数字/下划线）")
    buy_expression: str = Field(..., description="买入条件表达式，如 rsi_14 < 30")
    sell_expression: str = Field(..., description="卖出条件表达式，如 rsi_14 > 70")
    description: str = Field(default="", description="策略描述")


class CustomStrategyResponse(BaseModel):
    name: str
    message: str


class CustomStrategyInfo(BaseModel):
    name: str
    buy_expression: str
    sell_expression: str
    description: str = ""


class AvailableCodesResponse(BaseModel):
    codes: list[str]
    count: int


class ExprValidateRequest(BaseModel):
    expression: str = Field(..., description="待验证的表达式")


class ExprValidateResponse(BaseModel):
    valid: bool
    error: Optional[str] = None
    translated: Optional[str] = None


class ExprParseRequest(BaseModel):
    expression: str = Field(..., description="完整策略表达式，自动拆分为买入/卖出")


class ExprParseResponse(BaseModel):
    buy_expression: str
    sell_expression: str
    translated: Optional[str] = None
