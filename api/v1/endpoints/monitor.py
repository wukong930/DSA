# -*- coding: utf-8 -*-
"""Monitor endpoints — CRUD for monitor tasks and alert history."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.services.signal_engine import SignalEngine

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_service():
    from src.services.monitor_service import MonitorService
    return MonitorService()


def _get_user_id(request: Request) -> Optional[int]:
    user = getattr(request.state, "user", None)
    if user:
        return user.get("id")
    return None


class CreateMonitorRequest(BaseModel):
    model_config = {"populate_by_name": True}

    stock_code: str = Field(alias="stockCode")
    stock_name: str | None = Field(default=None, alias="stockName")
    market: str = "cn"
    conditions: list[dict] = Field(default_factory=list)
    interval_minutes: int = Field(default=15, alias="intervalMinutes")


class UpdateMonitorRequest(BaseModel):
    model_config = {"populate_by_name": True}

    conditions: list[dict] | None = None
    is_active: bool | None = Field(default=None, alias="isActive")
    interval_minutes: int | None = Field(default=None, alias="intervalMinutes")


@router.get("", summary="List user's monitor tasks")
async def monitor_list(request: Request):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    service = _get_service()
    tasks = service.get_user_tasks(user_id)
    return {"tasks": tasks, "total": len(tasks)}


@router.post("", summary="Create a monitor task")
async def monitor_create(request: Request, body: CreateMonitorRequest):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    if not body.stock_code.strip():
        return JSONResponse(status_code=400, content={"error": "stock_code_required", "message": "请输入股票代码"})

    if not body.conditions:
        return JSONResponse(status_code=400, content={"error": "conditions_required", "message": "请设置至少一个监控条件"})

    # Validate conditions
    err = SignalEngine.validate_conditions(body.conditions)
    if err:
        return JSONResponse(status_code=400, content={"error": "invalid_conditions", "message": err})

    service = _get_service()
    task_id, error = service.create_task(
        user_id=user_id,
        stock_code=body.stock_code.strip(),
        stock_name=body.stock_name,
        market=body.market,
        conditions=body.conditions,
        interval_minutes=body.interval_minutes,
    )
    if error:
        return JSONResponse(status_code=400, content={"error": "create_failed", "message": error})
    return {"id": task_id, "message": "监控任务创建成功"}


@router.put("/{task_id}", summary="Update a monitor task")
async def monitor_update(request: Request, task_id: int, body: UpdateMonitorRequest):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    if body.conditions is not None:
        err = SignalEngine.validate_conditions(body.conditions)
        if err:
            return JSONResponse(status_code=400, content={"error": "invalid_conditions", "message": err})

    service = _get_service()
    error = service.update_task(
        task_id=task_id,
        user_id=user_id,
        conditions=body.conditions,
        is_active=body.is_active,
        interval_minutes=body.interval_minutes,
    )
    if error:
        return JSONResponse(status_code=400, content={"error": "update_failed", "message": error})
    return {"message": "监控任务已更新"}


@router.delete("/{task_id}", summary="Delete a monitor task")
async def monitor_delete(request: Request, task_id: int):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    service = _get_service()
    error = service.delete_task(task_id, user_id)
    if error:
        return JSONResponse(status_code=400, content={"error": "delete_failed", "message": error})
    return {"message": "监控任务已删除"}


@router.get("/alerts", summary="List user's alerts")
async def alert_list(request: Request, unread_only: bool = False):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    service = _get_service()
    alerts = service.get_user_alerts(user_id, unread_only=unread_only)
    return {"alerts": alerts, "total": len(alerts)}


@router.post("/alerts/{alert_id}/read", summary="Mark alert as read")
async def alert_mark_read(request: Request, alert_id: int):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    service = _get_service()
    service.mark_alert_read(alert_id, user_id)
    return {"message": "已标记为已读"}


@router.get("/indicators", summary="List available indicators for conditions")
async def list_indicators():
    from src.services.ta_indicator_service import TAIndicatorService
    return TAIndicatorService.list_indicators()
