# -*- coding: utf-8 -*-
"""
Monitor Service — 15-minute interval stock monitoring engine.

Checks active monitor tasks, evaluates conditions via SignalEngine,
triggers alerts (DB + Feishu push + SSE broadcast).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


def _get_db():
    from src.storage import DatabaseManager
    return DatabaseManager.get_instance()


class MonitorService:
    """15-minute interval monitoring engine."""

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the monitoring loop."""
        if self._running:
            logger.warning("MonitorService already running")
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("MonitorService started")

    async def stop(self):
        """Stop the monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("MonitorService stopped")

    async def _loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_all_tasks()
            except Exception as e:
                logger.error("MonitorService loop error: %s", e, exc_info=True)
            await asyncio.sleep(15 * 60)  # 15 minutes

    async def _check_all_tasks(self):
        """Check all active monitor tasks."""
        tasks = self.get_active_tasks()
        if not tasks:
            return

        # Group by stock_code to batch-fetch data
        stock_codes = list({t["stock_code"] for t in tasks})
        stock_data = {}
        for code in stock_codes:
            try:
                df = await asyncio.to_thread(self._fetch_stock_data, code)
                if df is not None and not df.empty:
                    stock_data[code] = df
            except Exception as e:
                logger.warning("Failed to fetch data for %s: %s", code, e)

        # Evaluate each task
        for task in tasks:
            code = task["stock_code"]
            if code not in stock_data:
                continue
            try:
                await self._evaluate_task(task, stock_data[code])
            except Exception as e:
                logger.warning("Failed to evaluate task %d: %s", task["id"], e)

    def _fetch_stock_data(self, stock_code: str):
        """Fetch OHLCV data and compute indicators."""
        import pandas as pd
        from data_provider.base import canonical_stock_code
        from src.services.ta_indicator_service import TAIndicatorService

        code = canonical_stock_code(stock_code)
        if not code:
            return None

        # Try DB first, then DataFetcherManager
        df = None
        try:
            from datetime import date, timedelta
            db = _get_db()
            end_date = date.today()
            start_date = end_date - timedelta(days=120)
            bars = db.get_data_range(code, start_date, end_date)
            if bars and len(bars) >= 20:
                df = pd.DataFrame([b.to_dict() for b in bars])
        except Exception:
            pass

        if df is None or df.empty:
            try:
                from data_provider import DataFetcherManager
                manager = DataFetcherManager()
                df, _ = manager.get_daily_data(code, days=90)
            except Exception:
                return None

        if df is None or df.empty or len(df) < 20:
            return None

        # Compute indicators
        service = TAIndicatorService()
        return service.compute_all(df)

    async def _evaluate_task(self, task: dict, df):
        """Evaluate a single task's conditions and trigger alerts if matched."""
        from src.services.signal_engine import SignalEngine

        conditions = json.loads(task["conditions"]) if isinstance(task["conditions"], str) else task["conditions"]
        if not conditions:
            return

        engine = SignalEngine()
        signals = engine.evaluate(df, conditions)

        if signals:
            await self._trigger_alert(task, signals, df)

        # Update last_checked_at
        self._update_last_checked(task["id"])

    async def _trigger_alert(self, task: dict, signals: list, df):
        """Create alert record and send notifications."""
        from src.storage import MonitorAlert

        signal_dicts = [s.to_dict() for s in signals]

        # Get latest indicator values for context
        latest = df.iloc[-1]
        indicator_snapshot = {}
        for s in signals:
            val = latest.get(s.indicator)
            if val is not None:
                import pandas as pd
                indicator_snapshot[s.indicator] = round(float(val), 4) if pd.notna(val) else None

        db = _get_db()
        with db.get_session() as session:
            alert = MonitorAlert(
                task_id=task["id"],
                user_id=task["user_id"],
                stock_code=task["stock_code"],
                condition_matched=json.dumps(signal_dicts, ensure_ascii=False),
                indicator_values=json.dumps(indicator_snapshot, ensure_ascii=False),
                notified_via="feishu",
            )
            session.add(alert)
            session.commit()
            alert_id = alert.id

        # Update last_triggered_at
        self._update_last_triggered(task["id"])

        # Send Feishu notification
        try:
            await asyncio.to_thread(
                self._send_feishu_alert, task, signal_dicts, indicator_snapshot
            )
        except Exception as e:
            logger.warning("Feishu notification failed for alert %d: %s", alert_id, e)

        logger.info(
            "Alert triggered: task=%d stock=%s signals=%d",
            task["id"], task["stock_code"], len(signals),
        )

    def _send_feishu_alert(self, task: dict, signals: list, indicators: dict):
        """Send alert via Feishu bot."""
        try:
            from bot.feishu_bot import FeishuBot
            bot = FeishuBot()

            stock_name = task.get("stock_name") or task["stock_code"]
            signal_lines = []
            for s in signals:
                signal_lines.append(f"  • {s.get('description', s.get('indicator', ''))}")

            message = (
                f"📊 监控告警 — {stock_name} ({task['stock_code']})\n\n"
                f"触发条件:\n" + "\n".join(signal_lines) + "\n\n"
                f"指标快照: {json.dumps(indicators, ensure_ascii=False)}"
            )
            bot.send_text(message)
        except ImportError:
            logger.debug("Feishu bot not available, skipping notification")
        except Exception as e:
            logger.warning("Feishu send failed: %s", e)

    # ── CRUD operations ──

    def get_active_tasks(self) -> list[dict]:
        """Get all active monitor tasks."""
        from src.storage import MonitorTask
        db = _get_db()
        with db.get_session() as session:
            tasks = session.execute(
                select(MonitorTask).where(MonitorTask.is_active == True)
            ).scalars().all()
            return [self._task_to_dict(t) for t in tasks]

    def get_user_tasks(self, user_id: int) -> list[dict]:
        """Get all monitor tasks for a user."""
        from src.storage import MonitorTask
        db = _get_db()
        with db.get_session() as session:
            tasks = session.execute(
                select(MonitorTask).where(MonitorTask.user_id == user_id).order_by(MonitorTask.id.desc())
            ).scalars().all()
            return [self._task_to_dict(t) for t in tasks]

    def create_task(
        self,
        user_id: int,
        stock_code: str,
        conditions: list[dict],
        stock_name: str | None = None,
        market: str = "cn",
        interval_minutes: int = 15,
    ) -> tuple[int | None, str | None]:
        """Create a monitor task. Returns (task_id, error)."""
        from src.storage import MonitorTask
        from src.services.signal_engine import SignalEngine

        # Validate conditions
        err = SignalEngine.validate_conditions(conditions)
        if err:
            return None, err

        db = _get_db()
        with db.get_session() as session:
            task = MonitorTask(
                user_id=user_id,
                stock_code=stock_code,
                stock_name=stock_name,
                market=market,
                conditions=json.dumps(conditions, ensure_ascii=False),
                interval_minutes=interval_minutes,
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            return task.id, None

    def update_task(
        self,
        task_id: int,
        user_id: int,
        *,
        conditions: list[dict] | None = None,
        is_active: bool | None = None,
        interval_minutes: int | None = None,
    ) -> str | None:
        """Update a monitor task. Returns error or None."""
        from src.storage import MonitorTask
        from src.services.signal_engine import SignalEngine

        db = _get_db()
        with db.get_session() as session:
            task = session.get(MonitorTask, task_id)
            if not task:
                return "监控任务不存在"
            if task.user_id != user_id:
                return "无权修改此任务"
            if conditions is not None:
                err = SignalEngine.validate_conditions(conditions)
                if err:
                    return err
                task.conditions = json.dumps(conditions, ensure_ascii=False)
            if is_active is not None:
                task.is_active = is_active
            if interval_minutes is not None:
                task.interval_minutes = interval_minutes
            session.commit()
            return None

    def delete_task(self, task_id: int, user_id: int) -> str | None:
        """Delete a monitor task. Returns error or None."""
        from src.storage import MonitorTask, MonitorAlert
        db = _get_db()
        with db.get_session() as session:
            task = session.get(MonitorTask, task_id)
            if not task:
                return "监控任务不存在"
            if task.user_id != user_id:
                return "无权删除此任务"
            session.query(MonitorAlert).filter(MonitorAlert.task_id == task_id).delete()
            session.delete(task)
            session.commit()
            return None

    def get_user_alerts(self, user_id: int, limit: int = 50) -> list[dict]:
        """Get recent alerts for a user."""
        from src.storage import MonitorAlert
        db = _get_db()
        with db.get_session() as session:
            alerts = session.execute(
                select(MonitorAlert)
                .where(MonitorAlert.user_id == user_id)
                .order_by(MonitorAlert.created_at.desc())
                .limit(limit)
            ).scalars().all()
            return [self._alert_to_dict(a) for a in alerts]

    def mark_alert_read(self, alert_id: int, user_id: int) -> str | None:
        """Mark an alert as read."""
        from src.storage import MonitorAlert
        db = _get_db()
        with db.get_session() as session:
            alert = session.get(MonitorAlert, alert_id)
            if not alert:
                return "告警不存在"
            if alert.user_id != user_id:
                return "无权操作"
            alert.is_read = True
            session.commit()
            return None

    def _update_last_checked(self, task_id: int):
        from src.storage import MonitorTask
        db = _get_db()
        with db.get_session() as session:
            task = session.get(MonitorTask, task_id)
            if task:
                task.last_checked_at = datetime.now()
                session.commit()

    def _update_last_triggered(self, task_id: int):
        from src.storage import MonitorTask
        db = _get_db()
        with db.get_session() as session:
            task = session.get(MonitorTask, task_id)
            if task:
                task.last_triggered_at = datetime.now()
                session.commit()

    @staticmethod
    def _task_to_dict(t) -> dict:
        conditions = t.conditions
        if isinstance(conditions, str):
            try:
                conditions = json.loads(conditions)
            except (json.JSONDecodeError, TypeError):
                conditions = []
        return {
            "id": t.id,
            "user_id": t.user_id,
            "stock_code": t.stock_code,
            "stock_name": t.stock_name,
            "market": t.market,
            "conditions": conditions,
            "is_active": t.is_active,
            "interval_minutes": t.interval_minutes,
            "last_checked_at": t.last_checked_at.isoformat() if t.last_checked_at else None,
            "last_triggered_at": t.last_triggered_at.isoformat() if t.last_triggered_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }

    @staticmethod
    def _alert_to_dict(a) -> dict:
        condition_matched = a.condition_matched
        if isinstance(condition_matched, str):
            try:
                condition_matched = json.loads(condition_matched)
            except (json.JSONDecodeError, TypeError):
                pass
        indicator_values = a.indicator_values
        if isinstance(indicator_values, str):
            try:
                indicator_values = json.loads(indicator_values)
            except (json.JSONDecodeError, TypeError):
                pass
        return {
            "id": a.id,
            "task_id": a.task_id,
            "user_id": a.user_id,
            "stock_code": a.stock_code,
            "condition_matched": condition_matched,
            "indicator_values": indicator_values,
            "is_read": a.is_read,
            "notified_via": a.notified_via,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
