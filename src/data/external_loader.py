# -*- coding: utf-8 -*-
"""External data loader for Parquet-partitioned market data.

Supports daily and minute-level data from external sources (e.g. Haitong Securities).
Partition layout:
  {base_dir}/daily/{code}.parquet
  {base_dir}/minute/{code}/YYYY.parquet
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ExternalDataLoader:
    """Load Parquet-partitioned OHLCV data with optional GPU acceleration."""

    def __init__(self, base_dir: str, use_gpu: bool = False):
        self.base_dir = Path(base_dir)
        self.use_gpu = use_gpu
        self._pd = self._get_dataframe_lib()

    def _get_dataframe_lib(self):
        if self.use_gpu:
            try:
                import cudf  # type: ignore
                logger.info("ExternalDataLoader: using cuDF (GPU)")
                return cudf
            except ImportError:
                logger.warning("cuDF not available, falling back to pandas")
        return pd

    # ------------------------------------------------------------------
    # Daily data
    # ------------------------------------------------------------------

    def load_daily(self, code: str, start: str, end: str) -> pd.DataFrame:
        """Load daily OHLCV for a single stock code."""
        path = self.base_dir / "daily" / f"{code}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Daily data not found: {path}")
        df = self._read_parquet(path)
        df = self._filter_date_range(df, start, end)
        return self._to_pandas(df)

    def load_batch_daily(
        self, codes: list[str], start: str, end: str
    ) -> dict[str, pd.DataFrame]:
        """Load daily data for multiple codes. Skips missing files."""
        result: dict[str, pd.DataFrame] = {}
        for code in codes:
            try:
                result[code] = self.load_daily(code, start, end)
            except FileNotFoundError:
                logger.debug("Skipping %s: no daily parquet", code)
        return result

    # ------------------------------------------------------------------
    # Minute data
    # ------------------------------------------------------------------

    def load_minute(
        self, code: str, start: str, end: str, freq: str = "1min"
    ) -> pd.DataFrame:
        """Load minute-level data for a single stock code.

        Reads yearly parquet files and concatenates the relevant range.
        """
        minute_dir = self.base_dir / "minute" / code
        if not minute_dir.exists():
            raise FileNotFoundError(f"Minute data dir not found: {minute_dir}")

        start_year = int(start[:4])
        end_year = int(end[:4])
        frames = []
        for year in range(start_year, end_year + 1):
            path = minute_dir / f"{year}.parquet"
            if path.exists():
                frames.append(self._read_parquet(path))

        # Fallback: if no files matched the date range, load all available parquets
        if not frames:
            for path in sorted(minute_dir.glob("*.parquet")):
                frames.append(self._read_parquet(path))
            if frames:
                logger.info(
                    "No minute data for %s in %d-%d, loaded all available files instead",
                    code, start_year, end_year,
                )

        if not frames:
            raise FileNotFoundError(
                f"No minute parquet files for {code} in {start_year}-{end_year}"
            )

        df = self._pd.concat(frames, ignore_index=True)
        df = self._filter_date_range(df, start, end)

        # Resample if needed (e.g. 5min from 1min)
        if freq != "1min" and "datetime" in df.columns:
            df = self._resample_minute(df, freq)

        return self._to_pandas(df)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_available_codes(self, freq: str = "1d") -> list[str]:
        """List stock codes that have data available."""
        if freq == "1d":
            daily_dir = self.base_dir / "daily"
            if not daily_dir.exists():
                return []
            return sorted(p.stem for p in daily_dir.glob("*.parquet"))
        else:
            minute_dir = self.base_dir / "minute"
            if not minute_dir.exists():
                return []
            return sorted(p.name for p in minute_dir.iterdir() if p.is_dir())

    def has_data(self, code: str, freq: str = "1d") -> bool:
        if freq == "1d":
            return (self.base_dir / "daily" / f"{code}.parquet").exists()
        return (self.base_dir / "minute" / code).exists()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_parquet(self, path: Path):
        """Read parquet using the configured library (pandas or cuDF)."""
        return self._pd.read_parquet(str(path))

    @staticmethod
    def _filter_date_range(df, start: str, end: str):
        """Filter DataFrame by date range. Tries 'date' then 'datetime' column."""
        date_col = "date" if "date" in df.columns else "datetime"
        if date_col not in df.columns:
            return df
        col = df[date_col]
        if hasattr(col, "dt"):
            mask = (col >= start) & (col <= end)
        else:
            mask = (col.astype(str) >= start) & (col.astype(str) <= end)
        return df.loc[mask].reset_index(drop=True)

    @staticmethod
    def _resample_minute(df: pd.DataFrame, freq: str) -> pd.DataFrame:
        """Resample minute data to a coarser frequency (e.g. 5min)."""
        df = df.copy()
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime")
        agg = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }
        if "volume" in df.columns:
            agg["volume"] = "sum"
        if "amount" in df.columns:
            agg["amount"] = "sum"
        resampled = df.resample(freq).agg(agg).dropna(subset=["open"])
        return resampled.reset_index()

    def _to_pandas(self, df) -> pd.DataFrame:
        """Convert cuDF DataFrame to pandas if needed."""
        if self.use_gpu and hasattr(df, "to_pandas"):
            return df.to_pandas()
        return df
