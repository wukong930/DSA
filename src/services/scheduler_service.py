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
        self._reset_stale_running_tasks()
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

    def _reset_stale_running_tasks(self):
        """On startup, reset any tasks stuck in 'running' state from a previous crash."""
        from src.storage import ScheduledTask
        db = _get_db()
        with db.get_session() as session:
            stale = session.execute(
                select(ScheduledTask).where(ScheduledTask.run_status == 'running')
            ).scalars().all()
            for t in stale:
                logger.warning("Resetting stale running task %d to idle (crash recovery)", t.id)
                t.run_status = 'idle'
                t.run_started_at = None
            if stale:
                session.commit()

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
                    ScheduledTask.run_status != 'running',
                )
            ).scalars().all()
            task_dicts = [self._task_to_dict(t) for t in tasks]

        for task_dict in task_dicts:
            asyncio.create_task(self._execute_task_wrapper(task_dict))

    async def _execute_task_wrapper(self, task: dict):
        """Wrapper that tracks running state in DB and handles errors."""
        task_id = task["id"]
        self._set_run_status(task_id, 'running')
        error_msg = None
        try:
            failed = await self._execute_task(task)
            if failed:
                error_msg = f"Failed stocks: {', '.join(failed)}"
        except Exception as e:
            error_msg = str(e)
            logger.warning("Failed to execute scheduled task %d: %s", task_id, e)
        finally:
            self._set_run_status(task_id, 'idle')
            self._record_execution_result(task_id, error_msg)

    async def _execute_task(self, task: dict) -> list[str]:
        """Execute a scheduled task. Returns list of failed stock codes."""
        task_type = task["task_type"]
        stock_codes = task["stock_codes"]
        analysis_mode = task.get("analysis_mode", "traditional")
        failed: list[str] = []

        if task_type in ("daily_analysis", "custom_range"):
            failed = await self._run_daily_analysis(stock_codes, task, analysis_mode)
        elif task_type == "monitor":
            # Monitor tasks are handled by MonitorService
            pass

        # Update last_run_at and compute next_run_at
        self._update_after_run(task["id"], task["schedule_config"])
        return failed

    async def _run_daily_analysis(self, stock_codes: list, task: dict, analysis_mode: str = "traditional") -> list[str]:
        """Run analysis for a list of stocks with one retry for failures. Returns final failed codes."""
        from src.core.pipeline import run_analysis_pipeline
        from src.config import get_config
        config = get_config()
        per_stock_timeout = getattr(config, "agent_orchestrator_timeout_s", 600) + 60

        failed_codes: list[str] = []

        # First pass
        for code in stock_codes:
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(run_analysis_pipeline, code, analysis_mode=analysis_mode),
                    timeout=per_stock_timeout,
                )
                logger.info("Scheduled analysis completed for %s (task %d, mode=%s)", code, task["id"], analysis_mode)
            except asyncio.TimeoutError:
                logger.warning("Scheduled analysis timed out for %s (task %d, limit=%ds)", code, task["id"], per_stock_timeout)
                failed_codes.append(code)
            except Exception as e:
                logger.warning("Scheduled analysis failed for %s: %s", code, e)
                failed_codes.append(code)

        # Retry pass — one attempt for each failed stock
        if failed_codes:
            logger.info("Retrying %d failed stock(s) for task %d: %s", len(failed_codes), task["id"], failed_codes)
            still_failed: list[str] = []
            for code in failed_codes:
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(run_analysis_pipeline, code, analysis_mode=analysis_mode),
                        timeout=per_stock_timeout,
                    )
                    logger.info("Retry succeeded for %s (task %d)", code, task["id"])
                except asyncio.TimeoutError:
                    logger.warning("Retry timed out for %s (task %d), skipping until next cycle", code, task["id"])
                    still_failed.append(code)
                except Exception as e:
                    logger.warning("Retry failed for %s (task %d): %s, skipping until next cycle", code, task["id"], e)
                    still_failed.append(code)
            return still_failed

        return []

    def _set_run_status(self, task_id: int, status: str):
        """Update run_status and run_started_at in DB."""
        from src.storage import ScheduledTask
        db = _get_db()
        with db.get_session() as session:
            task = session.get(ScheduledTask, task_id)
            if task:
                task.run_status = status
                task.run_started_at = datetime.now() if status == 'running' else None
                session.commit()

    def _record_execution_result(self, task_id: int, error: Optional[str]):
        """Update failure tracking fields after task execution."""
        from src.storage import ScheduledTask
        db = _get_db()
        with db.get_session() as session:
            task = session.get(ScheduledTask, task_id)
            if not task:
                return
            if error:
                task.failure_count = (task.failure_count or 0) + 1
                task.consecutive_failures = (task.consecutive_failures or 0) + 1
                task.last_error = error[:2000]  # truncate
            else:
                task.consecutive_failures = 0
                task.last_error = None
            session.commit()

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
                    schedule_config: dict, analysis_mode: str = "traditional",
                    name: Optional[str] = None) -> tuple[Optional[int], Optional[str]]:
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
                name=name,
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
                    analysis_mode: Optional[str] = None, name: Optional[str] = None) -> Optional[str]:
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
            if name is not None:
                task.name = name
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
            "name": getattr(t, 'name', None),
            "stock_codes": stock_codes,
            "schedule_config": schedule_config,
            "analysis_mode": getattr(t, 'analysis_mode', 'traditional') or 'traditional',
            "is_active": t.is_active,
            "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None,
            "next_run_at": t.next_run_at.isoformat() if t.next_run_at else None,
            "run_status": getattr(t, 'run_status', 'idle') or 'idle',
            "failure_count": getattr(t, 'failure_count', 0) or 0,
            "consecutive_failures": getattr(t, 'consecutive_failures', 0) or 0,
            "last_error": getattr(t, 'last_error', None),
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
