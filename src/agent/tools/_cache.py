# -*- coding: utf-8 -*-
"""Process-wide cache for pre-fetched tool data.

The orchestrator / executor calls ``set_tool_context(data)`` before running
an agent loop so that tool handlers can check for pre-fetched results
instead of re-fetching from external APIs.

Cache is keyed by canonical stock code so that concurrent agent runs
(e.g. multiple stocks analyzed in parallel via ThreadPoolExecutor) each
have their own isolated namespace.  A threading.Lock guards mutations.

Tool handlers execute in ThreadPoolExecutor worker threads, so we cannot
use threading.local — workers wouldn't inherit the parent's state.

Usage in tool handlers::

    from src.agent.tools._cache import get_cached

    def _handle_get_realtime_quote(stock_code: str) -> dict:
        cached = get_cached("realtime_quote", stock_code)
        if cached:
            return cached
        ...  # normal fetch
"""

import threading
from typing import Any, Optional

_lock = threading.Lock()
# {canonical_stock_code: {data_key: value, ...}}
_cache_store: dict[str, dict] = {}


def _canonical(code: str) -> str:
    """Resolve canonical stock code, falling back to upper-cased input."""
    if not code:
        return ""
    try:
        from data_provider.base import canonical_stock_code
        return canonical_stock_code(code) or code.upper()
    except Exception:
        return code.upper()


def set_tool_context(data: dict) -> None:
    """Inject pre-fetched data dict into cache, keyed by stock_code."""
    if not data:
        return
    code = _canonical(str(data.get("stock_code", "")))
    if not code:
        return
    with _lock:
        _cache_store[code] = dict(data)


def clear_tool_context(stock_code: str = "") -> None:
    """Remove cached data for *stock_code* (or all if empty)."""
    with _lock:
        if stock_code:
            _cache_store.pop(_canonical(stock_code), None)
        else:
            _cache_store.clear()


def get_cached(key: str, stock_code: str = "") -> Optional[Any]:
    """Return cached value for *key*, or None if not available.

    *stock_code* is required to look up the correct namespace.
    """
    if not stock_code:
        return None
    code = _canonical(stock_code)
    if not code:
        return None
    with _lock:
        bucket = _cache_store.get(code)
        if bucket is None:
            return None
        return bucket.get(key)
