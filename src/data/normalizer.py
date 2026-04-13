# -*- coding: utf-8 -*-
"""行情数据列名标准化 + 多格式文件读取。

支持 MetaTrader、通达信、同花顺等常见导出格式，自动映射列名为引擎标准格式：
date, open, high, low, close, volume, amount(可选)
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# 列名映射：key 为标准化后的小写（去除 <>），value 为目标列名
_COLUMN_MAP: dict[str, str] = {
    # date
    "date": "date", "日期": "date",
    # time (辅助列，合并后丢弃)
    "time": "time", "时间": "time",
    # OHLC
    "open": "open", "开盘": "open", "开盘价": "open",
    "high": "high", "最高": "high", "最高价": "high",
    "low": "low", "最低": "low", "最低价": "low",
    "close": "close", "收盘": "close", "收盘价": "close",
    # volume
    "vol": "volume", "volume": "volume", "成交量": "volume",
    "tickvol": "volume",  # MetaTrader tick volume fallback
    # amount
    "amount": "amount", "成交额": "amount",
    # spread (丢弃)
    "spread": "_drop",
}

# 支持读取的表格文件扩展名
TABULAR_EXTENSIONS = {".xlsx", ".xls", ".csv"}


def _normalize_col_name(col: str) -> str:
    """去除空格、<> 包裹和 BOM，转小写。"""
    return col.strip().strip("\ufeff").strip("<>").strip().lower()


def normalize_market_df(df: pd.DataFrame) -> pd.DataFrame:
    """将任意列名的行情 DataFrame 标准化为引擎格式。

    Returns:
        标准化后的 DataFrame，列名为 date, open, high, low, close, volume[, amount]

    Raises:
        ValueError: 缺少必要列（至少需要 close）
    """
    # 1. 标准化列名
    rename_map: dict[str, str] = {}
    mapped_targets: set[str] = set()

    for orig_col in df.columns:
        normalized = _normalize_col_name(str(orig_col))
        target = _COLUMN_MAP.get(normalized)
        if target and target != "_drop" and target not in mapped_targets:
            rename_map[orig_col] = target
            mapped_targets.add(target)

    df = df.rename(columns=rename_map)

    # 丢弃标记为 _drop 的列和未映射的原始列
    keep_cols = [c for c in df.columns if c in {"date", "time", "open", "high", "low", "close", "volume", "amount"}]
    df = df[keep_cols].copy()

    # 2. 必要列检查
    if "close" not in df.columns:
        raise ValueError("缺少必要列: close（收盘价）")

    # 3. 合并 date + time
    if "date" in df.columns and "time" in df.columns:
        df["date"] = df["date"].astype(str).str.strip() + " " + df["time"].astype(str).str.strip()
        df = df.drop(columns=["time"])
    elif "time" in df.columns:
        df = df.rename(columns={"time": "date"})

    # 4. date 转 datetime
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # 5. 数值类型
    for col in ("open", "high", "low", "close"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "volume" not in df.columns:
        df["volume"] = 0
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)

    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    # 6. 填充缺失的 OHLC 列
    for col in ("open", "high", "low"):
        if col not in df.columns:
            df[col] = df["close"]

    # 7. 排序
    if "date" in df.columns:
        df = df.sort_values("date").reset_index(drop=True)

    return df


def read_tabular_file(path: Path) -> pd.DataFrame:
    """根据扩展名读取表格文件，返回原始 DataFrame。

    Raises:
        ValueError: 不支持的文件格式或读取失败
    """
    suffix = path.suffix.lower()
    try:
        if suffix in (".xlsx", ".xls"):
            return pd.read_excel(path)
        if suffix == ".csv":
            return pd.read_csv(path, sep=None, engine="python")
        if suffix == ".parquet":
            return pd.read_parquet(path)
    except Exception as e:
        raise ValueError(f"读取文件失败 ({path.name}): {e}") from e

    raise ValueError(f"不支持的文件格式: {suffix}")


def convert_to_parquet(src: Path, dst: Path) -> None:
    """读取表格文件 → 标准化列名 → 保存为 Parquet。

    Raises:
        ValueError: 读取或转换失败
    """
    df = read_tabular_file(src)
    df = normalize_market_df(df)
    dst.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(str(dst), index=False)
    logger.info("Converted %s → %s (%d rows)", src.name, dst.name, len(df))


def aggregate_minute_to_daily(df: pd.DataFrame) -> pd.DataFrame:
    """将分钟级 DataFrame 聚合为日线 DataFrame。

    Args:
        df: 标准化后的分钟数据，必须包含 date, open, high, low, close, volume 列

    Returns:
        日线 DataFrame
    """
    if "date" not in df.columns or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["_trade_date"] = df["date"].dt.date

    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    if "amount" in df.columns:
        agg["amount"] = "sum"

    daily = df.groupby("_trade_date").agg(agg).reset_index()
    daily = daily.rename(columns={"_trade_date": "date"})
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date").reset_index(drop=True)
    return daily


def convert_to_minute_parquets(src: Path, code: str, minute_dir: Path) -> int:
    """读取表格文件 → 标准化 → 按年拆分保存到 minute/{code}/{year}.parquet。

    同时自动聚合生成日线数据到 minute_dir 的兄弟目录 daily/{code}.parquet。

    Returns:
        写入的文件数量

    Raises:
        ValueError: 读取或转换失败
    """
    df = read_tabular_file(src)
    df = normalize_market_df(df)

    if "date" not in df.columns or df["date"].isna().all():
        raise ValueError(f"无法提取日期信息: {src.name}")

    code_dir = minute_dir / code
    code_dir.mkdir(parents=True, exist_ok=True)

    df["_year"] = df["date"].dt.year
    count = 0
    for year, group in df.groupby("_year"):
        out = group.drop(columns=["_year"])
        out_path = code_dir / f"{year}.parquet"
        out.to_parquet(str(out_path), index=False)
        logger.info("Wrote %s (%d rows)", out_path, len(out))
        count += 1

    # Auto-generate daily aggregation from minute data
    try:
        daily_dir = minute_dir.parent / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)
        daily_df = aggregate_minute_to_daily(df.drop(columns=["_year"]))
        if not daily_df.empty:
            daily_path = daily_dir / f"{code}.parquet"
            daily_df.to_parquet(str(daily_path), index=False)
            logger.info("Auto-aggregated daily: %s (%d rows)", daily_path, len(daily_df))
    except Exception as e:
        logger.warning("Failed to auto-aggregate daily for %s: %s", code, e)

    return count
