# -*- coding: utf-8 -*-
"""User management endpoints (admin-only)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.middlewares.auth import require_role
from src.user_auth import (
    create_user,
    list_users,
    update_user,
    delete_user,
    change_user_password,
    get_user_count,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _require_admin(request: Request):
    """Return error response if not admin, else None."""
    if not require_role(request, "admin"):
        return JSONResponse(
            status_code=403,
            content={"error": "forbidden", "message": "需要管理员权限"},
        )
    return None


class CreateUserRequest(BaseModel):
    model_config = {"populate_by_name": True}

    username: str
    password: str
    role: str = "analyst"
    display_name: str | None = Field(default=None, alias="displayName")


class UpdateUserRequest(BaseModel):
    model_config = {"populate_by_name": True}

    display_name: str | None = Field(default=None, alias="displayName")
    role: str | None = None
    is_active: bool | None = Field(default=None, alias="isActive")
    new_password: str | None = Field(default=None, alias="newPassword")


class ChangePasswordRequest(BaseModel):
    model_config = {"populate_by_name": True}

    current_password: str = Field(alias="currentPassword")
    new_password: str = Field(alias="newPassword")


@router.get("", summary="List all users")
async def user_list(request: Request):
    err_resp = _require_admin(request)
    if err_resp:
        return err_resp
    return {"users": list_users(), "total": get_user_count()}


@router.post("", summary="Create a new user")
async def user_create(request: Request, body: CreateUserRequest):
    err_resp = _require_admin(request)
    if err_resp:
        return err_resp

    user_id, err = create_user(
        username=body.username,
        password=body.password,
        role=body.role,
        display_name=body.display_name,
    )
    if err:
        return JSONResponse(
            status_code=400,
            content={"error": "create_failed", "message": err},
        )
    return {"id": user_id, "message": "用户创建成功"}


@router.put("/{user_id}", summary="Update a user")
async def user_update(request: Request, user_id: int, body: UpdateUserRequest):
    err_resp = _require_admin(request)
    if err_resp:
        return err_resp

    err = update_user(
        user_id,
        display_name=body.display_name,
        role=body.role,
        is_active=body.is_active,
        new_password=body.new_password,
    )
    if err:
        return JSONResponse(
            status_code=400,
            content={"error": "update_failed", "message": err},
        )
    return {"message": "用户更新成功"}


@router.delete("/{user_id}", summary="Delete a user")
async def user_delete(request: Request, user_id: int):
    err_resp = _require_admin(request)
    if err_resp:
        return err_resp

    err = delete_user(user_id)
    if err:
        return JSONResponse(
            status_code=400,
            content={"error": "delete_failed", "message": err},
        )
    return {"message": "用户已删除"}


@router.get("/me", summary="Get current user info")
async def user_me(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "message": "未登录"},
        )
    return {"user": user}


@router.post("/me/password", summary="Change own password")
async def user_change_password(request: Request, body: ChangePasswordRequest):
    user = getattr(request.state, "user", None)
    if not user or not user.get("id"):
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "message": "未登录"},
        )

    err = change_user_password(user["id"], body.current_password, body.new_password)
    if err:
        return JSONResponse(
            status_code=400,
            content={"error": "password_change_failed", "message": err},
        )
    return {"message": "密码修改成功"}
