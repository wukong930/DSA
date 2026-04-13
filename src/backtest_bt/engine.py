# -*- coding: utf-8 -*-
"""Backtrader-based event-driven backtest engine.

Provides precise backtesting with realistic order execution, commission,
slippage, and position sizing.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd

from src.backtest_bt.metrics import BacktestReport, compute_metrics
from src.data.external_loader import ExternalDataLoader

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Configuration for a single backtest run."""
    strategy_name: str = ""
    strategy_params: dict = field(default_factory=dict)
    codes: list[str] = field(default_factory=list)
    start_date: str = ""
    end_date: str = ""
    freq: str = "1d"                    # "1d" / "1min"
    initial_cash: float = 1_000_000
    commission: float = 0.001           # 0.1%
    slippage: float = 0.001             # 0.1%
    benchmark: str = "000300"           # CSI 300
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    allow_short: bool = False
    factor_data: Optional[dict] = None  # {code: {factor_name: pd.Series}} from screener


class StrategyBacktestEngine:
    """Event-driven backtest engine powered by backtrader."""

    def __init__(self, loader: ExternalDataLoader):
        self.loader = loader

    def run(self, config: BacktestConfig) -> BacktestReport:
        """Execute a single backtest run."""
        try:
            import backtrader as bt
        except ImportError:
            logger.error("backtrader not installed")
            raise ImportError("backtrader2 is required: pip install backtrader2")

        # Import here to avoid circular imports and keep backtrader lazy
        from src.backtest_bt.report_generator import generate_text_report

        cerebro = bt.Cerebro()
        cerebro.broker.setcash(config.initial_cash)
        cerebro.broker.setcommission(commission=config.commission)

        if config.slippage > 0:
            cerebro.broker.set_slippage_perc(config.slippage)

        # Minimum bars needed for indicator warmup.
        # Built-in strategies use SMA(5) fast / SMA(20) slow; use 5 as the floor.
        # Backtrader's minperiod mechanism ensures strategy only starts when
        # sufficient bars are available; this guard prevents obvious crashes.
        MIN_BARS = 5
        skipped_codes = []
        fallback_warnings = []
        data_by_code = {}
        for code in config.codes:
            df, fallback_warn = self._load_data(code, config)
            if df is None or df.empty:
                logger.warning("No data for %s, skipping", code)
                skipped_codes.append(code)
                continue
            # Check if data has enough bars for indicator warmup
            if len(df) < MIN_BARS:
                logger.warning(
                    "Insufficient data for %s: %d bars (need >= %d), skipping",
                    code, len(df), MIN_BARS,
                )
                skipped_codes.append(code)
                fallback_warnings.append(
                    f"{code}: 数据不足 {len(df)} 条（需要 {MIN_BARS}+ 条）"
                )
                continue
            if fallback_warn:
                fallback_warnings.append(fallback_warn)
            data_by_code[code] = df
            data_feed = self._df_to_feed(bt, df, code)
            cerebro.adddata(data_feed, name=code)

        # Guard: no data feeds loaded
        if len(config.codes) > 0 and len(config.codes) == len(skipped_codes):
            report = BacktestReport()
            report.benchmark_warning = "所有股票均无数据，无法执行回测"
            report.skipped_codes = skipped_codes
            report.text_report = generate_text_report(report)
            return report

        # Add strategy
        strategy_cls = self._resolve_strategy(config.strategy_name, config.factor_data)
        params = {**config.strategy_params}
        if config.stop_loss_pct is not None:
            params["stop_loss_pct"] = config.stop_loss_pct
        if config.take_profit_pct is not None:
            params["take_profit_pct"] = config.take_profit_pct
        if config.allow_short:
            params["allow_short"] = config.allow_short
        cerebro.addstrategy(strategy_cls, **params)

        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.02/244)
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name="time_return")

        # Run
        try:
            results = cerebro.run()
        except IndexError as e:
            logger.error("Backtest engine IndexError (insufficient data bars): %s", e)
            report = BacktestReport()
            report.benchmark_warning = (
                f"数据条数不足无法运行策略（{MIN_BARS}+ 条所需）：{e}"
            )
            report.skipped_codes = skipped_codes
            report.text_report = generate_text_report(report)
            return report
        except Exception as e:
            logger.error("Backtest engine error: %s", e)
            report = BacktestReport()
            report.benchmark_warning = f"回测引擎异常：{e}"
            report.skipped_codes = skipped_codes
            report.text_report = generate_text_report(report)
            return report
        if not results:
            report = BacktestReport()
            report.benchmark_warning = "回测引擎未返回结果，请检查数据和策略配置"
            report.skipped_codes = skipped_codes
            return report

        strat = results[0]
        report = self._build_report(strat, config, data_by_code, fallback_warnings, skipped_codes)

        # Distinguish no-signal from data failure
        if report.total_trades == 0 and len(report.equity_curve) > 0:
            report.benchmark_warning = (report.benchmark_warning or "") + \
                ("；" if report.benchmark_warning else "") + \
                "策略在回测期间未产生任何交易信号"

        # Regenerate text report with final state (includes benchmark_warning, rebalance_history, etc.)
        report.text_report = generate_text_report(report)

        return report

    def run_batch(self, configs: list[BacktestConfig]) -> list[BacktestReport]:
        """Run multiple backtest configurations sequentially."""
        reports = []
        for i, config in enumerate(configs, 1):
            logger.info("Running backtest %d/%d: %s", i, len(configs), config.strategy_name)
            try:
                report = self.run(config)
                reports.append(report)
            except Exception as e:
                logger.warning("Backtest %d failed: %s", i, e)
                reports.append(BacktestReport())
        return reports

    # Extra lookback days for indicator warmup (SMA(20) needs 20 bars minimum)
    _WARMUP_DAYS = 60

    def _load_data(self, code: str, config: BacktestConfig) -> tuple[Optional[pd.DataFrame], Optional[str]]:
        """Load data for a stock code based on frequency, with fallback.

        The loaded data includes extra lookback bars (before start_date) for
        indicator warmup. Backtrader's minperiod ensures the strategy only
        starts when sufficient bars are available.

        Returns (dataframe, fallback_warning). fallback_warning is set when
        the requested frequency was unavailable and a different one was used.
        """
        # Extend start date for indicator warmup
        from datetime import datetime
        warmup_start = (datetime.strptime(config.start_date, "%Y-%m-%d") - timedelta(days=self._WARMUP_DAYS)).strftime("%Y-%m-%d")

        try:
            if config.freq == "1d":
                return self.loader.load_daily(code, warmup_start, config.end_date), None
            else:
                return self.loader.load_minute(
                    code, warmup_start, config.end_date, config.freq
                ), None
        except FileNotFoundError:
            pass

        # Fallback: try the other source
        try:
            if config.freq == "1d":
                logger.info("Daily data not found for %s, trying minute data", code)
                df = self.loader.load_minute(
                    code, warmup_start, config.end_date, "1min"
                )
                return df, f"{code}: 日线数据不可用，已回退至分钟线"
            else:
                logger.info("Minute data not found for %s, trying daily data", code)
                df = self.loader.load_daily(code, warmup_start, config.end_date)
                return df, f"{code}: {config.freq}数据不可用，已回退至日线"
        except FileNotFoundError:
            return None, None

    @staticmethod
    def _df_to_feed(bt, df: pd.DataFrame, code: str):
        """Convert a pandas DataFrame to a backtrader data feed."""
        df = df.copy()

        # Normalize date column
        date_col = "date" if "date" in df.columns else "datetime"
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.set_index(date_col)

        # Ensure required columns
        for col in ("open", "high", "low", "close", "volume"):
            if col not in df.columns:
                if col == "volume":
                    df[col] = 0
                else:
                    df[col] = df.get("close", 0)

        df = df.sort_index()

        return bt.feeds.PandasData(
            dataname=df,
            name=code,
            openinterest=None,
        )

    # Map of known index codes to akshare symbols
    _INDEX_MAP = {
        "000300": "sh000300",  # 沪深300
        "000001": "sh000001",  # 上证指数
        "399001": "sz399001",  # 深证成指
        "399006": "sz399006",  # 创业板指
        "000016": "sh000016",  # 上证50
        "000688": "sh000688",  # 科创50
        "000905": "sh000905",  # 中证500
        "000852": "sh000852",  # 中证1000
    }

    def _load_index_from_akshare(
        self, code: str, start_date: str, end_date: str
    ) -> Optional[pd.DataFrame]:
        """Download historical index data from akshare as a fallback.

        Handles common A-share index codes (000300, 000001, etc.) by mapping
        them to the format expected by akshare (sh000300, etc.).

        Saves the downloaded data to local storage for future use.
        """
        akshare_symbol = self._INDEX_MAP.get(code)
        if not akshare_symbol:
            # Try treating the code directly (e.g., user passed "sh000300")
            if code.startswith(("sh", "sz")):
                akshare_symbol = code
            else:
                logger.debug("No akshare mapping for benchmark code: %s", code)
                return None

        try:
            import akshare as ak
        except ImportError:
            logger.warning("akshare not installed, cannot download index data")
            return None

        try:
            df = ak.stock_zh_index_daily(symbol=akshare_symbol)
            if df is None or df.empty:
                return None

            # Rename columns to match expected format
            df = df.rename(columns={
                "date": "date",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
            })

            # Filter to requested date range
            df["date"] = pd.to_datetime(df["date"])
            mask = (df["date"] >= start_date) & (df["date"] <= end_date)
            df = df[mask].reset_index(drop=True)

            if df.empty:
                return None

            # Save to local storage for caching
            self._save_index_cache(code, df)
            logger.info(
                "Auto-downloaded %s index data (%d rows) from akshare, cached locally",
                code, len(df),
            )
            return df

        except Exception as e:
            logger.warning("Failed to download index %s from akshare: %s", code, e)
            return None

    def _save_index_cache(self, code: str, df: pd.DataFrame) -> None:
        """Save downloaded index data to local parquet for caching."""
        try:
            daily_dir = self.loader.base_dir / "daily"
            daily_dir.mkdir(parents=True, exist_ok=True)
            cache_path = daily_dir / f"{code}.parquet"
            df.to_parquet(cache_path, index=False)
            logger.debug("Cached index data to %s", cache_path)
        except Exception as e:
            logger.warning("Failed to cache index %s: %s", code, e)

    def _resolve_strategy(self, name: str, factor_data=None):
        """Resolve strategy name to a backtrader Strategy class."""
        import backtrader as bt

        builtin = _get_builtin_strategies()
        if name in builtin:
            return builtin[name]

        # Check custom expression strategies
        from src.backtest_bt.strategies.expression import StrategyRegistry, build_expression_strategy_class

        custom = StrategyRegistry.get(name)
        if custom:
            return build_expression_strategy_class(
                custom["name"], custom["buy_expression"], custom["sell_expression"],
                factor_data=factor_data,
            )

        # Default: simple MA crossover
        logger.warning("Strategy '%s' not found, using default MACrossover", name)
        return builtin["ma_crossover"]

    def _build_report(
        self,
        strat,
        config: BacktestConfig,
        data_by_code: dict,
        fallback_warnings: list[str],
        skipped_codes: list[str],
    ) -> BacktestReport:
        """Extract metrics from backtrader strategy result."""
        from src.backtest_bt.trade_enricher import enrich_trades
        from src.backtest_bt.report_generator import generate_text_report

        # Build equity curve from time returns
        time_return = strat.analyzers.time_return.get_analysis()
        if not time_return:
            return BacktestReport()

        dates = sorted(time_return.keys())
        equity = [config.initial_cash]
        for d in dates:
            equity.append(equity[-1] * (1 + time_return[d]))

        equity_series = pd.Series(
            equity[1:],
            index=pd.DatetimeIndex(dates),
        )

        # Load benchmark (try local first, then akshare for known index codes)
        benchmark_series = None
        benchmark_df = None
        benchmark_warning = None
        try:
            bench_df = self.loader.load_daily(
                config.benchmark, config.start_date, config.end_date
            )
            if bench_df is not None and not bench_df.empty:
                date_col = "date" if "date" in bench_df.columns else "datetime"
                bench_df = bench_df.copy()
                bench_df[date_col] = pd.to_datetime(bench_df[date_col])
                benchmark_series = bench_df.set_index(date_col)["close"]
                # Normalize to same starting value
                benchmark_series = benchmark_series / benchmark_series.iloc[0] * config.initial_cash
                benchmark_df = bench_df
            else:
                bench_df = None
        except FileNotFoundError:
            bench_df = None

        # Fallback: try to download index data from akshare
        if bench_df is None:
            bench_df = self._load_index_from_akshare(
                config.benchmark, config.start_date, config.end_date
            )
            if bench_df is not None and not bench_df.empty:
                date_col = "date" if "date" in bench_df.columns else "datetime"
                bench_df[date_col] = pd.to_datetime(bench_df[date_col])
                benchmark_series = bench_df.set_index(date_col)["close"]
                benchmark_series = benchmark_series / benchmark_series.iloc[0] * config.initial_cash
                benchmark_df = bench_df

        if benchmark_series is None:
            benchmark_warning = f"基准 {config.benchmark} 无本地数据且自动下载失败，相对指标不可用"
            logger.warning("Benchmark %s not found locally and akshare download failed", config.benchmark)

        # Extract and enrich trades
        trades = self._extract_trades(strat)
        enriched_trades = enrich_trades(trades, data_by_code, benchmark_df)

        report = compute_metrics(equity_series, benchmark_series, enriched_trades)
        if benchmark_warning:
            report.benchmark_warning = benchmark_warning
        report.warnings.extend(fallback_warnings)
        report.skipped_codes = skipped_codes

        # Generate initial text report; will be regenerated after all modifications
        report.text_report = generate_text_report(report)

        return report

    @staticmethod
    def _extract_trades(strat) -> list[dict]:
        """Extract trade list from backtrader TradeAnalyzer."""
        trades = []
        try:
            ta = strat.analyzers.trades.get_analysis()
            # backtrader TradeAnalyzer doesn't give individual trades easily,
            # so we use the strategy's _trades if available
            if hasattr(strat, '_completed_trades'):
                trades = strat._completed_trades
        except Exception:
            pass
        return trades


# ---------------------------------------------------------------------------
# Built-in backtrader strategies
# ---------------------------------------------------------------------------

def _get_builtin_strategies() -> dict:
    """Return dict of built-in strategy name -> class.

    Uses lazy factory functions so backtrader is only imported when needed.
    Each factory returns a proper bt.Strategy subclass that backtrader can
    instantiate normally.
    """
    import backtrader as bt

    def _check_risk_exit(strategy, data, pos):
        """Check stop-loss and take-profit for a position.

        Returns (closed: bool, reason: str or None).
        Records exit reason in strategy._exit_reasons so notify_trade can read it.
        """
        if not pos.size:
            return False, None
        sl = getattr(strategy.p, 'stop_loss_pct', None)
        tp = getattr(strategy.p, 'take_profit_pct', None)
        if sl is None and tp is None:
            return False, None
        pnl_pct = (data.close[0] - pos.price) / pos.price * 100 if pos.price else 0
        if pos.size < 0:
            pnl_pct = -pnl_pct
        if sl is not None and pnl_pct <= -sl:
            strategy.close(data=data)
            if not hasattr(strategy, '_exit_reasons'):
                strategy._exit_reasons = {}
            strategy._exit_reasons[data] = "stop_loss"
            return True, "stop_loss"
        if tp is not None and pnl_pct >= tp:
            strategy.close(data=data)
            if not hasattr(strategy, '_exit_reasons'):
                strategy._exit_reasons = {}
            strategy._exit_reasons[data] = "take_profit"
            return True, "take_profit"
        return False, None

    def _notify_trade_mixin(self, trade):
        if trade.isclosed:
            open_size = getattr(self, '_open_sizes', {}).pop(trade.ref, 0)
            cost = abs(trade.price * open_size) if open_size else 0.0

            # Retrieve captured entry signal
            entry_signal = getattr(self, '_entry_signals', {}).pop(trade.data, None)
            # Retrieve exit reason (set by _check_risk_exit or next())
            exit_reason = getattr(self, '_exit_reasons', {}).pop(trade.data, None)

            self._completed_trades.append({
                "code": trade.data._name,
                "entry_date": str(bt.num2date(trade.dtopen).date()),
                "exit_date": str(bt.num2date(trade.dtclose).date()),
                "return_pct": round(trade.pnlcomm / cost * 100, 2) if cost > 1e-9 else 0.0,
                "holding_days": (bt.num2date(trade.dtclose) - bt.num2date(trade.dtopen)).days,
                "pnl": round(trade.pnlcomm, 2),
                "entry_signal": entry_signal,
                "exit_reason": exit_reason,
            })
        elif trade.isopen:
            if not hasattr(self, '_open_sizes'):
                self._open_sizes = {}
            self._open_sizes[trade.ref] = abs(trade.size)

    class MACrossover(bt.Strategy):
        params = (
            ("fast_period", 5),
            ("slow_period", 20),
            ("stop_loss_pct", None),
            ("take_profit_pct", None),
            ("allow_short", False),
        )

        def __init__(self):
            self._completed_trades = []
            self._entry_signals = {}   # {data: entry_signal_str}
            self._crossovers = {}
            for d in self.datas:
                fast = bt.indicators.SMA(d.close, period=self.p.fast_period)
                slow = bt.indicators.SMA(d.close, period=self.p.slow_period)
                self._crossovers[d] = bt.indicators.CrossOver(fast, slow)

        def next(self):
            for d in self.datas:
                pos = self.getposition(d)
                closed, reason = _check_risk_exit(self, d, pos)
                if closed:
                    continue
                crossover = self._crossovers[d]
                if not pos.size and crossover[0] > 0:
                    size = self._calculate_size(d)
                    if size >= 100:
                        self._entry_signals[d] = "ma_golden_cross"
                        self.buy(data=d, size=size)
                elif pos.size > 0 and crossover[0] < 0:
                    if not hasattr(self, '_exit_reasons'):
                        self._exit_reasons = {}
                    self._exit_reasons[d] = "ma_death_cross"
                    self.close(data=d)
                elif not pos.size and crossover[0] < 0 and self.p.allow_short:
                    size = self._calculate_size(d)
                    if size >= 100:
                        self._entry_signals[d] = "ma_death_cross_short"
                        self.sell(data=d, size=size)
                elif pos.size < 0 and crossover[0] > 0:
                    if not hasattr(self, '_exit_reasons'):
                        self._exit_reasons = {}
                    self._exit_reasons[d] = "ma_golden_cross"
                    self.close(data=d)

        def _calculate_size(self, data):
            available = self.broker.getcash() * 0.95
            price = data.close[0]
            if price > 0:
                return int(available / len(self.datas) / price / 100) * 100
            return 0

        notify_trade = _notify_trade_mixin

    class DualMA(bt.Strategy):
        params = (
            ("fast_period", 10),
            ("slow_period", 30),
            ("stop_loss_pct", None),
            ("take_profit_pct", None),
            ("allow_short", False),
        )

        def __init__(self):
            self._completed_trades = []
            self._entry_signals = {}
            self._indicators = {}
            for d in self.datas:
                fast = bt.indicators.SMA(d.close, period=self.p.fast_period)
                slow = bt.indicators.SMA(d.close, period=self.p.slow_period)
                self._indicators[d] = (fast, slow)

        def next(self):
            for d in self.datas:
                fast, slow = self._indicators[d]
                pos = self.getposition(d)
                closed, reason = _check_risk_exit(self, d, pos)
                if closed:
                    continue
                if not pos.size:
                    if fast[0] > slow[0] and fast[-1] <= slow[-1]:
                        price = d.close[0]
                        if price > 0:
                            size = int(self.broker.getcash() * 0.95 / len(self.datas) / price / 100) * 100
                            if size >= 100:
                                self._entry_signals[d] = "ma_bullish_cross"
                                self.buy(data=d, size=size)
                    elif fast[0] < slow[0] and fast[-1] >= slow[-1] and self.p.allow_short:
                        price = d.close[0]
                        if price > 0:
                            size = int(self.broker.getcash() * 0.95 / len(self.datas) / price / 100) * 100
                            if size >= 100:
                                self._entry_signals[d] = "ma_bearish_cross"
                                self.sell(data=d, size=size)
                elif pos.size > 0 and fast[0] < slow[0]:
                    if not hasattr(self, '_exit_reasons'):
                        self._exit_reasons = {}
                    self._exit_reasons[d] = "ma_death_cross"
                    self.close(data=d)
                elif pos.size < 0 and fast[0] > slow[0]:
                    if not hasattr(self, '_exit_reasons'):
                        self._exit_reasons = {}
                    self._exit_reasons[d] = "ma_golden_cross"
                    self.close(data=d)

        notify_trade = _notify_trade_mixin

    class RSIMeanReversion(bt.Strategy):
        params = (
            ("rsi_period", 14),
            ("oversold", 30),
            ("overbought", 70),
            ("stop_loss_pct", None),
            ("take_profit_pct", None),
            ("allow_short", False),
        )

        def __init__(self):
            self._completed_trades = []
            self._entry_signals = {}
            self._indicators = {}
            for d in self.datas:
                rsi = bt.indicators.RSI(d.close, period=self.p.rsi_period)
                self._indicators[d] = rsi

        def next(self):
            for d in self.datas:
                rsi = self._indicators[d]
                pos = self.getposition(d)
                closed, reason = _check_risk_exit(self, d, pos)
                if closed:
                    continue
                if not pos.size:
                    if rsi[0] < self.p.oversold:
                        price = d.close[0]
                        if price > 0:
                            size = int(self.broker.getcash() * 0.95 / len(self.datas) / price / 100) * 100
                            if size >= 100:
                                self._entry_signals[d] = "rsi_oversold"
                                self.buy(data=d, size=size)
                    elif rsi[0] > self.p.overbought and self.p.allow_short:
                        price = d.close[0]
                        if price > 0:
                            size = int(self.broker.getcash() * 0.95 / len(self.datas) / price / 100) * 100
                            if size >= 100:
                                self._entry_signals[d] = "rsi_overbought_short"
                                self.sell(data=d, size=size)
                elif pos.size > 0 and rsi[0] > self.p.overbought:
                    if not hasattr(self, '_exit_reasons'):
                        self._exit_reasons = {}
                    self._exit_reasons[d] = "rsi_exit_overbought"
                    self.close(data=d)
                elif pos.size < 0 and rsi[0] < self.p.oversold:
                    if not hasattr(self, '_exit_reasons'):
                        self._exit_reasons = {}
                    self._exit_reasons[d] = "rsi_exit_oversold"
                    self.close(data=d)

        notify_trade = _notify_trade_mixin

    return {
        "ma_crossover": MACrossover,
        "dual_ma": DualMA,
        "rsi_mean_reversion": RSIMeanReversion,
    }
