# -*- coding: utf-8 -*-
"""
Scheduler Service — enhanced task scheduling with three modes.

Modes:
- daily_analysis: run analysis at a fixed time each trading day
- custom_range: run at user-defined intervals (e.g., every 30 min during market hours)
- monitor: delegate to MonitorService for condition-based monitoring
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select

logger = logging.getLogger(__name__)


def _get_db():
    from src.storage import DatabaseManager
    return DatabaseManager.get_instance()


class SchedulerService:
    """Enhanced scheduler supporting three scheduling modes."""

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("SchedulerService started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("SchedulerService stopped")

    async def _loop(self):
        """Check every 60 seconds for tasks that need to run."""
        while self._running:
            try:
                await self._check_due_tasks()
            except Exception as e:
                logger.error("SchedulerService loop error: %s", e, exc_info=True)
            await asyncio.sleep(60)

    async def _check_due_tasks(self):
        """Find and execute tasks whose next_run_at has passed."""
        from src.storage import ScheduledTask
        now = datetime.now()
        db = _get_db()
        with db.get_session() as session:
            tasks = session.execute(
                select(ScheduledTask).where(
                    ScheduledTask.is_active == True,
                    ScheduledTask.next_run_at <= now,
                )
            ).scalars().all()
            task_dicts = [self._task_to_dict(t) for t in tasks]

        for task_dict in task_dicts:
            try:
                await self._execute_task(task_dict)
            except Exception as e:
                logger.warning("Failed to execute scheduled task %d: %s", task_dict["id"], e)

    async def _execute_task(self, task: dict):
        """Execute a scheduled task based on its type."""
        task_type = task["task_type"]
        stock_codes = task["stock_codes"]
        analysis_mode = task.get("analysis_mode", "traditional")

        if task_type == "daily_analysis":
            await self._run_daily_analysis(stock_codes, task, analysis_mode)
        elif task_type == "custom_range":
            await self._run_daily_analysis(stock_codes, task, analysis_mode)
        elif task_type == "monitor":
            # Monitor tasks are handled by MonitorService
            pass

        # Update last_run_at and compute next_run_at
        self._update_after_run(task["id"], task["schedule_config"])

    async def _run_daily_analysis(self, stock_codes: list, task: dict, analysis_mode: str = "traditional"):
        """Run analysis for a list of stocks."""
        from src.core.pipeline import run_analysis_pipeline

        for code in stock_codes:
            try:
                await asyncio.to_thread(run_analysis_pipeline, code, analysis_mode=analysis_mode)
                logger.info("Scheduled analysis completed for %s (task %d, mode=%s)", code, task["id"], analysis_mode)
            except Exception as e:
                logger.warning("Scheduled analysis failed for %s: %s", code, e)

    def _update_after_run(self, task_id: int, schedule_config: dict):
        """Update last_run_at and compute next_run_at."""
        from src.storage import ScheduledTask
        now = datetime.now()
        next_run = self._compute_next_run(schedule_config, now)

        db = _get_db()
        with db.get_session() as session:
            task = session.get(ScheduledTask, task_id)
            if task:
                task.last_run_at = now
                task.next_run_at = next_run
                session.commit()

    @staticmethod
    def _compute_next_run(config: dict, from_time: datetime) -> datetime:
        """Compute next run time from schedule config."""
        task_type = config.get("type", "daily")

        if task_type == "daily":
            # Run at a fixed time each day
            hour = config.get("hour", 18)
            minute = config.get("minute", 0)
            next_run = from_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= from_time:
                next_run += timedelta(days=1)
            return next_run

        elif task_type == "interval":
            # Run every N minutes
            interval = config.get("interval_minutes", 60)
            return from_time + timedelta(minutes=interval)

        elif task_type == "cron":
            # Simple cron-like: weekdays only
            hour = config.get("hour", 18)
            minute = config.get("minute", 0)
            next_run = from_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= from_time:
                next_run += timedelta(days=1)
            # Skip weekends
            while next_run.weekday() >= 5:
                next_run += timedelta(days=1)
            return next_run

        # Fallback: 1 hour
        return from_time + timedelta(hours=1)

    # ── CRUD ──

    def get_user_tasks(self, user_id: int) -> list[dict]:
        from src.storage import ScheduledTask
        db = _get_db()
        with db.get_session() as session:
            tasks = session.execute(
                select(ScheduledTask).where(ScheduledTask.user_id == user_id)
                .order_by(ScheduledTask.created_at.desc())
            ).scalars().all()
            return [self._task_to_dict(t) for t in tasks]

    def create_task(self, user_id: int, task_type: str, stock_codes: list[str],
                    schedule_config: dict, analysis_mode: str = "traditional") -> tuple[Optional[int], Optional[str]]:
        from src.storage import ScheduledTask

        if task_type not in ("daily_analysis", "custom_range", "monitor"):
            return None, f"Invalid task_type: {task_type}"
        if not stock_codes:
            return None, "至少需要一个股票代码"
        if analysis_mode not in ("traditional", "agent"):
            return None, f"Invalid analysis_mode: {analysis_mode}"

        now = datetime.now()
        next_run = self._compute_next_run(schedule_config, now)

        db = _get_db()
        with db.get_session() as session:
            task = ScheduledTask(
                user_id=user_id,
                task_type=task_type,
                stock_codes=json.dumps(stock_codes, ensure_ascii=False),
                schedule_config=json.dumps(schedule_config, ensure_ascii=False),
                analysis_mode=analysis_mode,
                next_run_at=next_run,
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            return task.id, None

    def update_task(self, task_id: int, user_id: int, is_active: Optional[bool] = None,
                    stock_codes: Optional[list] = None, schedule_config: Optional[dict] = None,
                    analysis_mode: Optional[str] = None) -> Optional[str]:
        from src.storage import ScheduledTask
        db = _get_db()
        with db.get_session() as session:
            task = session.get(ScheduledTask, task_id)
            if not task:
                return "任务不存在"
            if task.user_id != user_id:
                return "无权操作"
            if is_active is not None:
                task.is_active = is_active
            if stock_codes is not None:
                task.stock_codes = json.dumps(stock_codes, ensure_ascii=False)
            if schedule_config is not None:
                task.schedule_config = json.dumps(schedule_config, ensure_ascii=False)
                task.next_run_at = self._compute_next_run(schedule_config, datetime.now())
            if analysis_mode is not None:
                task.analysis_mode = analysis_mode
            session.commit()
            return None

    def delete_task(self, task_id: int, user_id: int) -> Optional[str]:
        from src.storage import ScheduledTask
        db = _get_db()
        with db.get_session() as session:
            task = session.get(ScheduledTask, task_id)
            if not task:
                return "任务不存在"
            if task.user_id != user_id:
                return "无权操作"
            session.delete(task)
            session.commit()
            return None

    @staticmethod
    def _task_to_dict(t) -> dict:
        stock_codes = t.stock_codes
        if isinstance(stock_codes, str):
            try:
                stock_codes = json.loads(stock_codes)
            except (json.JSONDecodeError, TypeError):
                stock_codes = []
        schedule_config = t.schedule_config
        if isinstance(schedule_config, str):
            try:
                schedule_config = json.loads(schedule_config)
            except (json.JSONDecodeError, TypeError):
                schedule_config = {}
        return {
            "id": t.id,
            "user_id": t.user_id,
            "task_type": t.task_type,
            "stock_codes": stock_codes,
            "schedule_config": schedule_config,
            "analysis_mode": getattr(t, 'analysis_mode', 'traditional') or 'traditional',
            "is_active": t.is_active,
            "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None,
            "next_run_at": t.next_run_at.isoformat() if t.next_run_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
