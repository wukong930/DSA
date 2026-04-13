# -*- coding: utf-8 -*-
"""Memory monitoring and GC utilities for long-running analysis batches."""

from __future__ import annotations

import gc
import logging
import os

logger = logging.getLogger(__name__)


def get_rss_mb() -> float:
    """Return current process RSS in MB (Linux/macOS)."""
    try:
        import resource
        # ru_maxrss is in KB on Linux, bytes on macOS
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        rss_kb = rusage.ru_maxrss
        if os.uname().sysname == "Darwin":
            return rss_kb / (1024 * 1024)  # bytes -> MB
        return rss_kb / 1024  # KB -> MB
    except Exception:
        return 0.0


def log_memory(label: str = "") -> float:
    """Log current RSS and return value in MB."""
    rss = get_rss_mb()
    logger.info("[Memory] %s RSS=%.1fMB", label, rss)
    return rss


def force_gc(label: str = "") -> None:
    """Run gc.collect() and log freed objects."""
    collected = gc.collect()
    rss = get_rss_mb()
    logger.info("[GC] %s collected=%d objects, RSS=%.1fMB", label, collected, rss)
