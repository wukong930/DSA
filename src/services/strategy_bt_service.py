# -*- coding: utf-8 -*-
"""Strategy backtest service — orchestrates backtest runs with DB persistence."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import select

logger = logging.getLogger(__name__)


def _get_db():
    from src.storage import DatabaseManager
    return DatabaseManager.get_instance()


class StrategyBtService:
    """Service layer for strategy backtesting."""

    _running_counts: dict[int, int] = {}  # user_id -> concurrent run count

    def __init__(self):
        self._orchestrator = None

    def _get_orchestrator(self):
        if self._orchestrator is None:
            from src.config import get_config
            from src.backtest_bt.orchestrator import BacktestOrchestrator
            self._orchestrator = BacktestOrchestrator(get_config())
        return self._orchestrator

    async def submit_backtest(
        self,
        user_id: int,
        strategy_name: str,
        strategy_params: dict,
        codes: list[str],
        start_date: str,
        end_date: str,
        freq: str = "1d",
        initial_cash: float = 1_000_000,
        commission: float = 0.001,
        slippage: float = 0.001,
        benchmark: str = "000300",
        screen_universe: bool = False,
        screen_factors: Optional[list[str]] = None,
        screen_top_n: int = 50,
        screen_lookback_days: int = 60,
        rebalance_days: int = 0,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        allow_short: bool = False,
    ) -> int:
        """Create a backtest run record and start execution in background.

        Returns the run ID.
        """
        from src.config import get_config
        config = get_config()

        # Rate limiting: check concurrent runs per user
        max_concurrent = config.strategy_bt_max_concurrent_per_user
        current = self._running_counts.get(user_id, 0)
        if current >= max_concurrent:
            raise ValueError(f"最多同时运行 {max_concurrent} 个回测，请等待当前回测完成")

        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        if start > end:
            raise ValueError("开始日期不能晚于结束日期")
        if not codes and not screen_universe:
            raise ValueError("股票代码列表不能为空（或开启全市场筛选）")
        from src.storage import StrategyBacktestRun

        db = _get_db()
        with db.get_session() as session:
            run = StrategyBacktestRun(
                user_id=user_id,
                strategy_name=strategy_name,
                strategy_params=json.dumps(strategy_params, ensure_ascii=False),
                codes=json.dumps(codes, ensure_ascii=False),
                start_date=start,
                end_date=end,
                freq=freq,
                initial_cash=initial_cash,
                commission=commission,
                slippage=slippage,
                benchmark=benchmark,
                status="pending",
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            run_id = run.id

        # Fire and forget with timeout and rate tracking
        self._running_counts[user_id] = self._running_counts.get(user_id, 0) + 1
        timeout = config.strategy_bt_timeout
        asyncio.create_task(self._execute_run_with_timeout(
            run_id, strategy_name, strategy_params, codes,
            start_date, end_date, freq, initial_cash, commission,
            slippage, benchmark, screen_universe, screen_factors or [], screen_top_n,
            screen_lookback_days, rebalance_days,
            stop_loss_pct, take_profit_pct, allow_short,
            timeout_seconds=timeout, user_id=user_id,
        ))

        return run_id

    async def _execute_run(
        self,
        run_id: int,
        strategy_name: str,
        strategy_params: dict,
        codes: list[str],
        start_date: str,
        end_date: str,
        freq: str,
        initial_cash: float,
        commission: float,
        slippage: float,
        benchmark: str,
        screen_universe: bool,
        screen_factors: list[str],
        screen_top_n: int,
        screen_lookback_days: int = 60,
        rebalance_days: int = 0,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        allow_short: bool = False,
    ) -> None:
        """Execute backtest and update DB with results."""
        from src.storage import StrategyBacktestRun
        from src.backtest_bt.orchestrator import StrategyBtRequest

        self._update_status(run_id, "running", progress="准备回测参数...")

        try:
            request = StrategyBtRequest(
                strategy_name=strategy_name,
                strategy_params=strategy_params,
                codes=codes,
                start_date=start_date,
                end_date=end_date,
                freq=freq,
                initial_cash=initial_cash,
                commission=commission,
                slippage=slippage,
                benchmark=benchmark,
                screen_universe=screen_universe,
                screen_factors=screen_factors,
                screen_top_n=screen_top_n,
                screen_lookback_days=screen_lookback_days,
                rebalance_days=rebalance_days,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
                allow_short=allow_short,
            )

            self._update_status(run_id, "running", progress="执行回测中...")
            orchestrator = self._get_orchestrator()
            report = await orchestrator.run_full_pipeline(request)

            self._update_status(run_id, "running", progress="保存结果...")

            # Persist result
            db = _get_db()
            with db.get_session() as session:
                run = session.get(StrategyBacktestRun, run_id)
                if run:
                    run.status = "completed"
                    run.completed_at = datetime.now()
                    run.result_json = json.dumps(report.to_dict(), ensure_ascii=False, default=str)
                    run.total_return_pct = report.total_return_pct
                    run.sharpe_ratio = report.sharpe_ratio
                    run.max_drawdown_pct = report.max_drawdown_pct
                    run.win_rate_pct = report.win_rate_pct
                    run.total_trades = report.total_trades
                    if hasattr(run, 'warnings') and report.warnings:
                        run.warnings = json.dumps(report.warnings, ensure_ascii=False)
                    session.commit()

            logger.info("Strategy backtest run %d completed", run_id)

        except Exception as e:
            logger.error("Strategy backtest run %d failed: %s", run_id, e, exc_info=True)
            db = _get_db()
            with db.get_session() as session:
                run = session.get(StrategyBacktestRun, run_id)
                if run:
                    run.status = "failed"
                    run.completed_at = datetime.now()
                    run.error_message = str(e)[:2000]
                    session.commit()

    def _update_status(self, run_id: int, status: str, progress: Optional[str] = None) -> None:
        from src.storage import StrategyBacktestRun
        db = _get_db()
        with db.get_session() as session:
            run = session.get(StrategyBacktestRun, run_id)
            if run:
                run.status = status
                if status == "running":
                    if not run.started_at:
                        run.started_at = datetime.now()
                if progress is not None and hasattr(run, 'progress'):
                    run.progress = progress
                session.commit()

    async def get_run(self, run_id: int) -> Optional[dict]:
        """Get a single backtest run with full results."""
        from src.storage import StrategyBacktestRun
        db = _get_db()
        with db.get_session() as session:
            run = session.get(StrategyBacktestRun, run_id)
            if not run:
                return None
            return self._run_to_dict(run, include_result=True)

    async def list_runs(self, user_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
        """List backtest runs for a user (without full result JSON)."""
        from src.storage import StrategyBacktestRun
        db = _get_db()
        with db.get_session() as session:
            runs = session.execute(
                select(StrategyBacktestRun)
                .where(StrategyBacktestRun.user_id == user_id)
                .order_by(StrategyBacktestRun.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).scalars().all()
            return [self._run_to_dict(r, include_result=False) for r in runs]

    async def get_available_strategies(self) -> list[dict]:
        """Return list of available backtest strategies (builtin + custom)."""
        from src.backtest_bt.engine import _get_builtin_strategies
        from src.backtest_bt.strategies.expression import StrategyRegistry

        strategies = _get_builtin_strategies()
        result = [
            {"name": name, "description": name.replace("_", " ").title()}
            for name in sorted(strategies.keys())
        ]
        for s in StrategyRegistry.list_all():
            result.append({
                "name": s["name"],
                "description": f"[自定义] {s['description']}",
            })
        return result

    async def create_custom_strategy(
        self, name: str, buy_expression: str, sell_expression: str, description: str = ""
    ) -> str | None:
        """Create a custom expression strategy. Returns error message or None."""
        from src.backtest_bt.strategies.expression import StrategyRegistry
        from src.backtest_bt.engine import _get_builtin_strategies

        if name in _get_builtin_strategies():
            return f"策略名 '{name}' 与内置策略冲突"
        error = StrategyRegistry.register(name, buy_expression, sell_expression, description)
        if error:
            return error
        # Persist to DB
        self._persist_custom_strategy(name, buy_expression, sell_expression, description)
        return None

    async def delete_custom_strategy(self, name: str) -> bool:
        """Delete a custom strategy. Returns True if deleted."""
        from src.backtest_bt.strategies.expression import StrategyRegistry
        ok = StrategyRegistry.remove(name)
        if ok:
            self._remove_persisted_custom_strategy(name)
        return ok

    async def list_custom_strategies(self) -> list[dict]:
        """Return list of custom expression strategies."""
        from src.backtest_bt.strategies.expression import StrategyRegistry
        return StrategyRegistry.list_all()

    async def get_available_factors(self) -> list[dict]:
        """Return list of available factors."""
        import src.backtest_bt.factors.builtin  # noqa: F401
        from src.backtest_bt.factors.base import FactorRegistry
        factors = FactorRegistry.get_all()
        return [
            {"name": name, "description": cls.description}
            for name, cls in sorted(factors.items())
        ]

    async def get_datasets(self) -> list[dict]:
        """Return registered external datasets."""
        from src.config import get_config
        from src.data.registry import DatasetRegistry
        config = get_config()
        registry_path = f"{config.strategy_bt_data_dir}/registry.json"
        registry = DatasetRegistry(registry_path)
        return [
            {
                "name": ds.name,
                "freq": ds.freq,
                "source": ds.source,
                "date_range": list(ds.date_range),
                "code_count": ds.code_count,
            }
            for ds in registry.list_datasets()
        ]

    async def delete_run(self, run_id: int) -> bool:
        """Delete a backtest run by ID. Returns True if deleted."""
        from src.storage import StrategyBacktestRun
        db = _get_db()
        with db.get_session() as session:
            run = session.get(StrategyBacktestRun, run_id)
            if not run:
                return False
            session.delete(run)
            session.commit()
            return True

    async def delete_dataset(self, name: str) -> bool:
        """Delete a dataset: remove files + unregister. Returns True if deleted."""
        import shutil
        from src.config import get_config
        from src.data.registry import DatasetRegistry

        config = get_config()
        base_dir = Path(config.strategy_bt_data_dir)
        registry_path = f"{config.strategy_bt_data_dir}/registry.json"
        registry = DatasetRegistry(registry_path)

        meta = registry.get(name)
        if not meta:
            return False

        # Remove filesystem data
        # Daily: scan for parquet files in daily/
        daily_dir = base_dir / "daily"
        if daily_dir.exists():
            for f in daily_dir.glob("*.parquet"):
                if f.stem == name:
                    if not f.resolve().is_relative_to(daily_dir.resolve()):
                        logger.error("Path traversal attempt in daily delete: %s", f)
                        continue
                    f.unlink()
                    logger.info("Deleted daily file: %s", f)

        # Minute: remove minute/{code}/ directories
        minute_dir = base_dir / "minute"
        if minute_dir.exists():
            code_dir = minute_dir / name
            if code_dir.exists() and code_dir.is_dir():
                if not code_dir.resolve().is_relative_to(minute_dir.resolve()):
                    logger.error("Path traversal attempt in minute delete: %s", code_dir)
                    return False
                shutil.rmtree(code_dir)
                logger.info("Deleted minute dir: %s", code_dir)

        registry.unregister(name)
        logger.info("Unregistered dataset: %s", name)
        return True

    async def _execute_run_with_timeout(self, *args, timeout_seconds: int = 600, user_id: int = 0) -> None:
        """Wrap _execute_run with a timeout (default 10 min)."""
        run_id = args[0]
        try:
            await asyncio.wait_for(self._execute_run(*args), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.error("Strategy backtest run %d timed out after %ds", run_id, timeout_seconds)
            from src.storage import StrategyBacktestRun
            db = _get_db()
            with db.get_session() as session:
                run = session.get(StrategyBacktestRun, run_id)
                if run and run.status in ("pending", "running"):
                    run.status = "failed"
                    run.completed_at = datetime.now()
                    run.error_message = f"回测超时（{timeout_seconds}秒）"
                    session.commit()
        finally:
            # Decrement running count
            current = self._running_counts.get(user_id, 1)
            if current <= 1:
                self._running_counts.pop(user_id, None)
            else:
                self._running_counts[user_id] = current - 1

    @staticmethod
    def _persist_custom_strategy(name: str, buy_expr: str, sell_expr: str, description: str) -> None:
        from src.storage import CustomExpressionStrategy
        db = _get_db()
        with db.get_session() as session:
            existing = session.query(CustomExpressionStrategy).filter_by(name=name).first()
            if existing:
                existing.buy_expression = buy_expr
                existing.sell_expression = sell_expr
                existing.description = description
            else:
                session.add(CustomExpressionStrategy(
                    name=name, buy_expression=buy_expr,
                    sell_expression=sell_expr, description=description,
                ))
            session.commit()

    @staticmethod
    def _remove_persisted_custom_strategy(name: str) -> None:
        from src.storage import CustomExpressionStrategy
        db = _get_db()
        with db.get_session() as session:
            session.query(CustomExpressionStrategy).filter_by(name=name).delete()
            session.commit()

    @staticmethod
    def _persist_custom_factor(name: str, expression: str, description: str) -> None:
        from src.storage import CustomExpressionFactor
        db = _get_db()
        with db.get_session() as session:
            existing = session.query(CustomExpressionFactor).filter_by(name=name).first()
            if existing:
                existing.expression = expression
                existing.description = description
            else:
                session.add(CustomExpressionFactor(
                    name=name, expression=expression, description=description,
                ))
            session.commit()

    @staticmethod
    def _remove_persisted_custom_factor(name: str) -> None:
        from src.storage import CustomExpressionFactor
        db = _get_db()
        with db.get_session() as session:
            session.query(CustomExpressionFactor).filter_by(name=name).delete()
            session.commit()

    @staticmethod
    def load_persisted_custom_data() -> None:
        """Load custom factors and strategies from DB into in-memory registries."""
        from src.storage import CustomExpressionFactor, CustomExpressionStrategy
        from src.backtest_bt.factors.expression import register_expression_factor
        from src.backtest_bt.strategies.expression import StrategyRegistry

        db = _get_db()
        try:
            with db.get_session() as session:
                for f in session.query(CustomExpressionFactor).all():
                    register_expression_factor(f.name, f.expression, f.description or "")
                    logger.info("Loaded persisted custom factor: %s", f.name)

                for s in session.query(CustomExpressionStrategy).all():
                    StrategyRegistry.register(
                        s.name, s.buy_expression, s.sell_expression, s.description or ""
                    )
                    logger.info("Loaded persisted custom strategy: %s", s.name)
        except Exception as e:
            logger.warning("Failed to load persisted custom data: %s", e)

    @staticmethod
    def recover_stale_runs() -> None:
        """Mark any pending/running runs as failed on startup (they were interrupted)."""
        from src.storage import StrategyBacktestRun
        db = _get_db()
        try:
            with db.get_session() as session:
                stale = session.query(StrategyBacktestRun).filter(
                    StrategyBacktestRun.status.in_(["pending", "running"])
                ).all()
                for run in stale:
                    run.status = "failed"
                    run.completed_at = datetime.now()
                    run.error_message = "服务重启，任务中断"
                    logger.info("Recovered stale run %d -> failed", run.id)
                if stale:
                    session.commit()
        except Exception as e:
            logger.warning("Failed to recover stale runs: %s", e)

    @staticmethod
    def _run_to_dict(run, include_result: bool = False) -> dict:
        codes = run.codes
        if isinstance(codes, str):
            try:
                codes = json.loads(codes)
            except (json.JSONDecodeError, TypeError):
                codes = []

        params = run.strategy_params
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except (json.JSONDecodeError, TypeError):
                params = {}

        d = {
            "id": run.id,
            "user_id": run.user_id,
            "strategy_name": run.strategy_name,
            "strategy_params": params,
            "codes": codes,
            "start_date": run.start_date.isoformat() if run.start_date else None,
            "end_date": run.end_date.isoformat() if run.end_date else None,
            "freq": run.freq,
            "initial_cash": run.initial_cash,
            "commission": run.commission,
            "slippage": getattr(run, 'slippage', 0.001),
            "benchmark": run.benchmark,
            "status": run.status,
            "progress": getattr(run, 'progress', None),
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "error_message": run.error_message,
            "total_return_pct": run.total_return_pct,
            "sharpe_ratio": run.sharpe_ratio,
            "max_drawdown_pct": run.max_drawdown_pct,
            "win_rate_pct": run.win_rate_pct,
            "total_trades": run.total_trades,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }

        if include_result and run.result_json:
            try:
                d["result"] = json.loads(run.result_json)
            except (json.JSONDecodeError, TypeError):
                d["result"] = None
        elif include_result:
            d["result"] = None

        return d
