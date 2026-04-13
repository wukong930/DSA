# -*- coding: utf-8 -*-
"""Backtest orchestrator — transparent pipeline from screening to reporting.

Users don't need to manually switch between vectorbt and backtrader.
The orchestrator decides the execution path based on the request.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from src.backtest_bt.engine import BacktestConfig, StrategyBacktestEngine
from src.backtest_bt.factors.base import BaseFactor, FactorRegistry
from src.backtest_bt.metrics import BacktestReport, compute_metrics
from src.backtest_bt.report_generator import generate_text_report
from src.backtest_bt.screener import VectorbtScreener
from src.data.external_loader import ExternalDataLoader

logger = logging.getLogger(__name__)


@dataclass
class StrategyBtRequest:
    """User-facing request for a strategy backtest."""
    strategy_name: str = "ma_crossover"
    strategy_params: dict = field(default_factory=dict)
    codes: list[str] = field(default_factory=list)
    start_date: str = ""
    end_date: str = ""
    freq: str = "1d"
    initial_cash: float = 1_000_000
    commission: float = 0.001
    slippage: float = 0.001
    benchmark: str = "000300"

    # Screening options (optional)
    screen_universe: bool = False       # If True, screen full market first
    screen_factors: list[str] = field(default_factory=list)
    screen_top_n: int = 50
    screen_lookback_days: int = 60      # Use data before start_date for screening
    rebalance_days: int = 0             # 0 = no rebalance; >0 = rebalance every N days

    # Risk management
    stop_loss_pct: Optional[float] = None   # e.g. 5.0 = 5% stop loss
    take_profit_pct: Optional[float] = None # e.g. 10.0 = 10% take profit
    allow_short: bool = False               # Allow short selling


class BacktestOrchestrator:
    """Orchestrate screening + backtesting transparently."""

    def __init__(self, config):
        from src.config import Config
        self._config: Config = config

        mode = config.strategy_bt_runtime_mode
        if mode == "auto":
            mode = "full" if self._detect_gpu() else "lite"
        self.mode = mode

        use_gpu = config.strategy_bt_gpu_enabled and mode == "full"
        self.loader = ExternalDataLoader(config.strategy_bt_data_dir, use_gpu=use_gpu)
        self.screener = VectorbtScreener(self.loader, mode)
        self.engine = StrategyBacktestEngine(self.loader)

        logger.info("BacktestOrchestrator initialized (mode=%s, gpu=%s)", mode, use_gpu)

    async def run_full_pipeline(self, request: StrategyBtRequest) -> BacktestReport:
        """Full pipeline: optional screening → backtest → report."""
        needs_screening = request.screen_universe or request.screen_factors

        if needs_screening and request.rebalance_days > 0:
            return await self._run_with_rebalance(request)

        codes = request.codes
        factor_data = None
        fallback_warnings: list[str] = []

        # Step 1: Screen if requested (using lookback data before start_date)
        if needs_screening:
            screened_codes, factor_data = await self._screen(request, request.start_date)
            if not screened_codes:
                # Screening returned no candidates — if user provided specific codes,
                # fallback to them; otherwise report the failure.
                if request.codes:
                    logger.warning(
                        "Screening returned no candidates, falling back to user-provided codes: %s",
                        request.codes,
                    )
                    codes = request.codes
                    fallback_warnings.append(
                        f"筛选期无数据（回看期早于数据起始日期），已使用用户指定的股票: {request.codes}"
                    )
                else:
                    logger.warning("Screening returned no candidates and no codes provided")
                    report = BacktestReport()
                    report.benchmark_warning = "筛选未返回任何候选股票，且未指定股票代码"
                    report.text_report = generate_text_report(report)
                    return report
            else:
                codes = screened_codes

        # Step 2: Backtest
        config = BacktestConfig(
            strategy_name=request.strategy_name,
            strategy_params=request.strategy_params,
            codes=codes,
            start_date=request.start_date,
            end_date=request.end_date,
            freq=request.freq,
            initial_cash=request.initial_cash,
            commission=request.commission,
            slippage=request.slippage,
            benchmark=request.benchmark,
            stop_loss_pct=request.stop_loss_pct,
            take_profit_pct=request.take_profit_pct,
            allow_short=request.allow_short,
            factor_data=factor_data,
        )

        report = await asyncio.to_thread(self.engine.run, config)

        # Append screening fallback warnings
        if fallback_warnings:
            report.warnings.extend(fallback_warnings)
            report.text_report = generate_text_report(report)

        return report

    async def _run_with_rebalance(self, request: StrategyBtRequest) -> BacktestReport:
        """Run backtest with periodic rebalancing.

        Splits the backtest period into windows of `rebalance_days`.
        Before each window, re-screens the universe and runs backtest
        for that window. Chains equity curves together.
        """
        start = datetime.strptime(request.start_date, "%Y-%m-%d")
        end = datetime.strptime(request.end_date, "%Y-%m-%d")
        rebalance_days = request.rebalance_days

        # Build window boundaries
        windows = []
        win_start = start
        while win_start < end:
            win_end = min(win_start + timedelta(days=rebalance_days), end)
            windows.append((win_start, win_end))
            win_start = win_end

        if not windows:
            return BacktestReport()

        logger.info(
            "Rebalance mode: %d windows of %d days each",
            len(windows), rebalance_days,
        )

        all_equity = []
        all_trades = []
        all_warnings = []
        rebalance_history = []
        current_cash = request.initial_cash

        for i, (win_start, win_end) in enumerate(windows):
            win_start_str = win_start.strftime("%Y-%m-%d")
            win_end_str = win_end.strftime("%Y-%m-%d")

            # Screen using data before this window's start
            codes, factor_data = await self._screen(request, win_start_str)
            if not codes:
                logger.warning("Window %d: screening returned no candidates, skipping", i + 1)
                all_warnings.append(f"窗口{i+1} ({win_start_str}~{win_end_str}): 筛选无候选股")
                continue

            rebalance_history.append({
                "window": i + 1,
                "start": win_start_str,
                "end": win_end_str,
                "codes": codes[:10],  # Top 10 for display
                "total_codes": len(codes),
            })

            config = BacktestConfig(
                strategy_name=request.strategy_name,
                strategy_params=request.strategy_params,
                codes=codes,
                start_date=win_start_str,
                end_date=win_end_str,
                freq=request.freq,
                initial_cash=current_cash,
                commission=request.commission,
                slippage=request.slippage,
                benchmark=request.benchmark,
                stop_loss_pct=request.stop_loss_pct,
                take_profit_pct=request.take_profit_pct,
                allow_short=request.allow_short,
                factor_data=factor_data,
            )

            window_report = await asyncio.to_thread(self.engine.run, config)

            # Collect equity curve
            if window_report.equity_curve:
                all_equity.extend(window_report.equity_curve)
                # Update cash for next window from last equity value
                last_point = window_report.equity_curve[-1]
                current_cash = last_point.get("value", current_cash)

            if window_report.trade_list:
                all_trades.extend(window_report.trade_list)

            all_warnings.extend(window_report.warnings)

        if not all_equity:
            report = BacktestReport()
            report.benchmark_warning = "所有再平衡窗口均无有效数据"
            report.warnings = all_warnings
            report.text_report = generate_text_report(report)
            return report

        # Build combined equity series for final metrics
        equity_series = pd.Series(
            [p["value"] for p in all_equity],
            index=pd.DatetimeIndex([p["date"] for p in all_equity]),
        )

        # Load benchmark for full period
        benchmark_series = None
        try:
            bench_df = self.loader.load_daily(
                request.benchmark, request.start_date, request.end_date
            )
            if bench_df is not None and not bench_df.empty:
                date_col = "date" if "date" in bench_df.columns else "datetime"
                bench_df[date_col] = pd.to_datetime(bench_df[date_col])
                benchmark_series = bench_df.set_index(date_col)["close"]
                benchmark_series = benchmark_series / benchmark_series.iloc[0] * request.initial_cash
        except Exception as e:
            all_warnings.append(f"基准 {request.benchmark} 加载失败: {e}")

        report = compute_metrics(equity_series, benchmark_series, all_trades)
        report.warnings = all_warnings
        report.rebalance_history = rebalance_history
        report.text_report = generate_text_report(report)
        return report

    async def run_screen_only(self, request: StrategyBtRequest) -> pd.DataFrame:
        """Run screening only, return candidate stocks."""
        codes, _ = await self._screen(request, request.start_date)
        return codes

    async def run_backtest_only(self, config: BacktestConfig) -> BacktestReport:
        """Run backtest only (user already specified stocks)."""
        return await asyncio.to_thread(self.engine.run, config)

    async def _screen(
        self, request: StrategyBtRequest, ref_date: str,
    ) -> tuple[list[str], Optional[dict[str, dict[str, pd.Series]]]]:
        """Screen universe using data BEFORE ref_date (no look-ahead bias).

        Args:
            request: The backtest request.
            ref_date: Reference date — screening uses data ending the day before this.

        Returns:
            (codes, factor_data) where factor_data maps {code: {factor_name: Series}}.
        """
        factors = self._resolve_factors(request.screen_factors)
        if not factors:
            logger.warning("No valid factors for screening")
            return request.codes, None

        universe = request.codes or self.loader.list_available_codes()

        # Fix 1: Use lookback window BEFORE ref_date to avoid look-ahead bias
        ref_dt = datetime.strptime(ref_date, "%Y-%m-%d")
        screen_end = (ref_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        screen_start = (ref_dt - timedelta(days=request.screen_lookback_days)).strftime("%Y-%m-%d")

        logger.info(
            "Screening with lookback data: %s ~ %s (ref_date=%s)",
            screen_start, screen_end, ref_date,
        )

        result_df, factor_data = await asyncio.to_thread(
            self.screener.screen_with_factors,
            universe, factors, screen_start, screen_end,
            request.screen_top_n,
        )

        if result_df.empty:
            return [], None
        return result_df["code"].tolist(), factor_data

    @staticmethod
    def _resolve_factors(factor_names: list[str]) -> list[BaseFactor]:
        """Resolve factor names to instances."""
        # Ensure builtins are loaded
        import src.backtest_bt.factors.builtin  # noqa: F401

        factors = []
        for name in factor_names:
            cls = FactorRegistry.get(name)
            if cls:
                factors.append(cls())
            else:
                logger.warning("Unknown factor: %s", name)
        return factors

    @staticmethod
    def _detect_gpu() -> bool:
        """Check if NVIDIA GPU with cuDF is available."""
        try:
            import cudf  # type: ignore  # noqa: F401
            return True
        except ImportError:
            return False
