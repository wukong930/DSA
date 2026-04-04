# -*- coding: utf-8 -*-
"""Watchlist endpoints — manage user's stock watchlist and filter by conditions."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_user_id(request: Request) -> Optional[int]:
    user = getattr(request.state, "user", None)
    if user:
        return user.get("id")
    return None


class AddWatchlistRequest(BaseModel):
    model_config = {"populate_by_name": True}

    stock_code: str = Field(alias="stockCode")
    stock_name: str | None = Field(default=None, alias="stockName")
    market: str = "cn"
    tags: list[str] | None = None
    notes: str | None = None


class UpdateWatchlistRequest(BaseModel):
    tags: list[str] | None = None
    notes: str | None = None


class FilterRequest(BaseModel):
    conditions: list[dict]


@router.get("", summary="List user's watchlist")
async def watchlist_list(request: Request):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    from src.services.filter_service import get_user_watchlist
    items = get_user_watchlist(user_id)
    return {"items": items, "total": len(items)}


@router.post("", summary="Add stock to watchlist")
async def watchlist_add(request: Request, body: AddWatchlistRequest):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    from src.services.filter_service import add_to_watchlist
    item_id, err = add_to_watchlist(
        user_id=user_id,
        stock_code=body.stock_code,
        stock_name=body.stock_name,
        market=body.market,
        tags=body.tags,
        notes=body.notes,
    )
    if err:
        return JSONResponse(status_code=400, content={"error": "add_failed", "message": err})
    return {"id": item_id, "message": "已添加到自选股"}


@router.put("/{item_id}", summary="Update watchlist item")
async def watchlist_update(request: Request, item_id: int, body: UpdateWatchlistRequest):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    from src.services.filter_service import update_watchlist_item
    err = update_watchlist_item(user_id, item_id, tags=body.tags, notes=body.notes)
    if err:
        return JSONResponse(status_code=400, content={"error": "update_failed", "message": err})
    return {"message": "自选股已更新"}


@router.delete("/{item_id}", summary="Remove from watchlist")
async def watchlist_remove(request: Request, item_id: int):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    from src.services.filter_service import remove_from_watchlist
    err = remove_from_watchlist(user_id, item_id)
    if err:
        return JSONResponse(status_code=400, content={"error": "remove_failed", "message": err})
    return {"message": "已从自选股移除"}


@router.post("/filter", summary="Filter watchlist by conditions")
async def watchlist_filter(request: Request, body: FilterRequest):
    user_id = _get_user_id(request)
    if user_id is None:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    from src.services.signal_engine import SignalEngine
    err = SignalEngine.validate_conditions(body.conditions)
    if err:
        return JSONResponse(status_code=400, content={"error": "invalid_conditions", "message": err})

    from src.services.filter_service import FilterService
    service = FilterService()
    results = service.filter_watchlist(user_id, body.conditions)
    return {
        "results": [r.to_dict() for r in results],
        "matched": len(results),
    }
