# -*- coding: utf-8 -*-
"""Subprocess-based analysis worker for OOM isolation.

When enabled via ANALYSIS_SUBPROCESS_ENABLED=true, analysis batches run in a
child process.  If the child OOMs, the parent (API server) survives.
"""

from __future__ import annotations

import json
import logging
import multiprocessing
import os
import sys
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Worker entry — runs inside the child process
# ---------------------------------------------------------------------------

def _worker_entry(args_json: str, result_queue: multiprocessing.Queue) -> None:
    """Child-process entry point.  Imports are local to avoid polluting parent."""
    try:
        # Re-initialise logging in child
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        )
        args = json.loads(args_json)
        stock_codes: list[str] = args["stock_codes"]
        analysis_mode: str = args.get("analysis_mode", "traditional")

        from src.core.pipeline import run_batch_analysis_pipeline
        failed = run_batch_analysis_pipeline(stock_codes, analysis_mode)

        result_queue.put(json.dumps({
            "status": "ok",
            "failed_codes": failed,
        }))
    except Exception as e:
        logger.error("Worker process failed: %s", e, exc_info=True)
        result_queue.put(json.dumps({
            "status": "error",
            "error": str(e),
            "failed_codes": json.loads(args_json).get("stock_codes", []),
        }))


# ---------------------------------------------------------------------------
# Parent-side runner
# ---------------------------------------------------------------------------

class SubprocessAnalysisRunner:
    """Launch analysis in a child process so OOM kills only the worker."""

    def __init__(self, timeout_s: int = 1200):
        self.timeout_s = timeout_s

    def run_batch(
        self,
        stock_codes: list[str],
        analysis_mode: str = "traditional",
        batch_size: int = 20,
    ) -> list[str]:
        """Split stock_codes into batches, run each in a subprocess.

        Returns:
            List of stock codes that failed across all batches.
        """
        from src.utils.memory_utils import log_memory

        batches = [stock_codes[i:i + batch_size] for i in range(0, len(stock_codes), batch_size)]
        all_failed: list[str] = []

        for idx, batch in enumerate(batches, 1):
            logger.info(
                "Subprocess batch %d/%d: %d stocks %s",
                idx, len(batches), len(batch), batch,
            )
            failed = self._run_worker(batch, analysis_mode)
            all_failed.extend(failed)
            log_memory(f"parent after subprocess batch {idx}/{len(batches)}")

        return all_failed

    def _run_worker(self, codes: list[str], analysis_mode: str) -> list[str]:
        """Spawn one child process for a batch of codes."""
        ctx = multiprocessing.get_context("spawn")
        result_queue: multiprocessing.Queue = ctx.Queue()

        args_json = json.dumps({
            "stock_codes": codes,
            "analysis_mode": analysis_mode,
        })

        proc = ctx.Process(
            target=_worker_entry,
            args=(args_json, result_queue),
            daemon=True,
        )
        proc.start()
        proc.join(timeout=self.timeout_s)

        if proc.is_alive():
            logger.warning("Worker timed out after %ds, killing", self.timeout_s)
            proc.kill()
            proc.join(timeout=10)
            return codes  # all failed

        if proc.exitcode != 0:
            logger.warning("Worker exited with code %d (OOM or crash)", proc.exitcode)
            # Try to read partial results
            if not result_queue.empty():
                try:
                    result = json.loads(result_queue.get_nowait())
                    return result.get("failed_codes", codes)
                except Exception:
                    pass
            return codes

        # Normal exit — read result
        try:
            result = json.loads(result_queue.get_nowait())
            return result.get("failed_codes", [])
        except Exception as e:
            logger.warning("Failed to read worker result: %s", e)
            return codes
