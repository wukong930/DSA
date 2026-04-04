# -*- coding: utf-8 -*-
"""
Filter Service — filter watchlist stocks by technical/fundamental conditions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _get_db():
    from src.storage import DatabaseManager
    return DatabaseManager.get_instance()


@dataclass
class FilterResult:
    stock_code: str
    stock_name: Optional[str]
    signals: list
    indicator_snapshot: dict

    def to_dict(self) -> dict:
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "signals": [s.to_dict() for s in self.signals],
            "indicator_snapshot": self.indicator_snapshot,
        }


class FilterService:
    """Filter watchlist stocks by technical indicator conditions."""

    def filter_watchlist(
        self,
        user_id: int,
        conditions: list[dict],
    ) -> list[FilterResult]:
        """Filter user's watchlist by conditions. Returns matching stocks."""
        from src.storage import WatchlistItem
        from src.services.ta_indicator_service import TAIndicatorService
        from src.services.signal_engine import SignalEngine
        from sqlalchemy import select

        db = _get_db()
        with db.get_session() as session:
            items = session.execute(
                select(WatchlistItem).where(WatchlistItem.user_id == user_id)
            ).scalars().all()
            watchlist = [
                {"stock_code": w.stock_code, "stock_name": w.stock_name, "market": w.market}
                for w in items
            ]

        if not watchlist:
            return []

        ta_service = TAIndicatorService()
        engine = SignalEngine()
        results = []

        for item in watchlist:
            try:
                df = self._fetch_ohlcv(item["stock_code"])
                if df is None or df.empty or len(df) < 20:
                    continue
                df = ta_service.compute_all(df)
                signals = engine.evaluate(df, conditions)
                if signals:
                    latest = df.iloc[-1]
                    snapshot = {}
                    for s in signals:
                        val = latest.get(s.indicator)
                        if val is not None and pd.notna(val):
                            snapshot[s.indicator] = round(float(val), 4)
                    results.append(FilterResult(
                        stock_code=item["stock_code"],
                        stock_name=item["stock_name"],
                        signals=signals,
                        indicator_snapshot=snapshot,
                    ))
            except Exception as e:
                logger.warning("Filter failed for %s: %s", item["stock_code"], e)

        return results

    def _fetch_ohlcv(self, stock_code: str):
        """Fetch OHLCV data for a stock."""
        from datetime import date, timedelta
        from data_provider.base import canonical_stock_code

        code = canonical_stock_code(stock_code)
        if not code:
            return None

        try:
            db = _get_db()
            end_date = date.today()
            start_date = end_date - timedelta(days=120)
            bars = db.get_data_range(code, start_date, end_date)
            if bars and len(bars) >= 20:
                return pd.DataFrame([b.to_dict() for b in bars])
        except Exception:
            pass

        try:
            from data_provider import DataFetcherManager
            manager = DataFetcherManager()
            df, _ = manager.get_daily_data(code, days=90)
            return df
        except Exception:
            return None


# ── Watchlist CRUD ──

def get_user_watchlist(user_id: int) -> list[dict]:
    from src.storage import WatchlistItem
    from sqlalchemy import select
    db = _get_db()
    with db.get_session() as session:
        items = session.execute(
            select(WatchlistItem).where(WatchlistItem.user_id == user_id).order_by(WatchlistItem.added_at.desc())
        ).scalars().all()
        return [_item_to_dict(w) for w in items]


def add_to_watchlist(user_id: int, stock_code: str, stock_name: Optional[str] = None,
                     market: str = "cn", tags: Optional[list] = None, notes: Optional[str] = None) -> tuple[Optional[int], Optional[str]]:
    from src.storage import WatchlistItem
    from sqlalchemy import select

    stock_code = stock_code.strip()
    if not stock_code:
        return None, "股票代码不能为空"

    db = _get_db()
    with db.get_session() as session:
        existing = session.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id,
                WatchlistItem.stock_code == stock_code,
            )
        ).scalar_one_or_none()
        if existing:
            return None, f"'{stock_code}' 已在自选股中"

        item = WatchlistItem(
            user_id=user_id,
            stock_code=stock_code,
            stock_name=stock_name,
            market=market,
            tags=json.dumps(tags or [], ensure_ascii=False),
            notes=notes,
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return item.id, None


def remove_from_watchlist(user_id: int, item_id: int) -> Optional[str]:
    from src.storage import WatchlistItem
    db = _get_db()
    with db.get_session() as session:
        item = session.get(WatchlistItem, item_id)
        if not item:
            return "自选股不存在"
        if item.user_id != user_id:
            return "无权操作"
        session.delete(item)
        session.commit()
        return None


def update_watchlist_item(user_id: int, item_id: int, tags: Optional[list] = None,
                          notes: Optional[str] = None) -> Optional[str]:
    from src.storage import WatchlistItem
    db = _get_db()
    with db.get_session() as session:
        item = session.get(WatchlistItem, item_id)
        if not item:
            return "自选股不存在"
        if item.user_id != user_id:
            return "无权操作"
        if tags is not None:
            item.tags = json.dumps(tags, ensure_ascii=False)
        if notes is not None:
            item.notes = notes
        session.commit()
        return None


def _item_to_dict(w) -> dict:
    tags = w.tags
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except (json.JSONDecodeError, TypeError):
            tags = []
    return {
        "id": w.id,
        "user_id": w.user_id,
        "stock_code": w.stock_code,
        "stock_name": w.stock_name,
        "market": w.market,
        "tags": tags,
        "notes": w.notes,
        "added_at": w.added_at.isoformat() if w.added_at else None,
    }
