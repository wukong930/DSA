# -*- coding: utf-8 -*-
"""Scheduler endpoints — CRUD for scheduled analysis tasks."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_service(request: Request = None):
    if request and hasattr(request.app.state, "scheduler_service"):
        return request.app.state.scheduler_service
    from src.services.scheduler_service import SchedulerService
    return SchedulerService()


def _get_user_id(request: Request) -> Optional[int]:
    user = getattr(request.state, "user", None)
    if user:
        return user.get("id")
    return None


class CreateScheduleRequest(BaseModel):
    model_config = {"populate_by_name": True}

    task_type: str = Field(default="daily_analysis", alias="taskType")
    stock_codes: list[str] = Field(alias="stockCodes")
    schedule_config: dict = Field(default_factory=dict, alias="scheduleConfig")
    analysis_mode: str = Field(default="traditional", alias="analysisMode")  # traditional / agent
    name: str | None = Field(default=None)


class UpdateScheduleRequest(BaseModel):
    model_config = {"populate_by_name": True}

    is_active: bool | None = Field(default=None, alias="isActive")
    stock_codes: list[str] | None = Field(default=None, alias="stockCodes")
    schedule_config: dict | None = Field(default=None, alias="scheduleConfig")
    analysis_mode: str | None = Field(default=None, alias="analysisMode")
    name: str | None = Field(default=None)


@router.get("", summary="List user's scheduled tasks")
async def schedule_list(request: Request):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    service = _get_service()
    tasks = service.get_user_tasks(user_id)
    return {"tasks": tasks, "total": len(tasks)}


@router.post("", summary="Create a scheduled task")
async def schedule_create(request: Request, body: CreateScheduleRequest):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    service = _get_service()
    task_id, err = service.create_task(
        user_id=user_id,
        task_type=body.task_type,
        stock_codes=body.stock_codes,
        schedule_config=body.schedule_config,
        analysis_mode=body.analysis_mode,
        name=body.name,
    )
    if err:
        return JSONResponse(status_code=400, content={"error": "create_failed", "message": err})
    return {"id": task_id, "message": "定时任务创建成功"}


@router.put("/{task_id}", summary="Update a scheduled task")
async def schedule_update(request: Request, task_id: int, body: UpdateScheduleRequest):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    service = _get_service()
    err = service.update_task(
        task_id=task_id,
        user_id=user_id,
        is_active=body.is_active,
        stock_codes=body.stock_codes,
        schedule_config=body.schedule_config,
        analysis_mode=body.analysis_mode,
        name=body.name,
    )
    if err:
        return JSONResponse(status_code=400, content={"error": "update_failed", "message": err})
    return {"message": "定时任务已更新"}


@router.delete("/{task_id}", summary="Delete a scheduled task")
async def schedule_delete(request: Request, task_id: int):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    service = _get_service()
    err = service.delete_task(task_id, user_id)
    if err:
        return JSONResponse(status_code=400, content={"error": "delete_failed", "message": err})
    return {"message": "定时任务已删除"}
