# -*- coding: utf-8 -*-
"""Strategy backtest API endpoints."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form

from api.v1.schemas.strategy_bt import (
    AvailableCodesResponse,
    CustomFactorRequest,
    CustomFactorResponse,
    CustomStrategyInfo,
    CustomStrategyRequest,
    CustomStrategyResponse,
    DatasetInfo,
    DataUploadResponse,
    ExprParseRequest,
    ExprParseResponse,
    ExprValidateRequest,
    ExprValidateResponse,
    FactorInfo,
    StrategyBtRunDetail,
    StrategyBtRunRequest,
    StrategyBtRunResponse,
    StrategyBtRunSummary,
    StrategyInfo,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_service = None


def _get_service():
    global _service
    if _service is None:
        from src.services.strategy_bt_service import StrategyBtService
        _service = StrategyBtService()
    return _service


@router.post("/run", response_model=StrategyBtRunResponse)
async def submit_backtest(req: StrategyBtRunRequest):
    """Submit a strategy backtest run."""
    service = _get_service()
    try:
        run_id = await service.submit_backtest(
            user_id=0,
            strategy_name=req.strategy_name,
            strategy_params=req.strategy_params,
            codes=req.codes,
            start_date=req.start_date,
            end_date=req.end_date,
            freq=req.freq,
            initial_cash=req.initial_cash,
            commission=req.commission,
            slippage=req.slippage,
            benchmark=req.benchmark,
            screen_universe=req.screen_universe,
            screen_factors=req.screen_factors,
            screen_top_n=req.screen_top_n,
            screen_lookback_days=req.screen_lookback_days,
            rebalance_days=req.rebalance_days,
            stop_loss_pct=req.stop_loss_pct,
            take_profit_pct=req.take_profit_pct,
            allow_short=req.allow_short,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return StrategyBtRunResponse(run_id=run_id)


@router.get("/runs", response_model=list[StrategyBtRunSummary])
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List strategy backtest runs."""
    service = _get_service()
    runs = await service.list_runs(user_id=0, limit=limit, offset=offset)
    return runs


@router.get("/runs/{run_id}", response_model=StrategyBtRunDetail)
async def get_run(run_id: int):
    """Get a single strategy backtest run with full results."""
    service = _get_service()
    run = await service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/strategies", response_model=list[StrategyInfo])
async def list_strategies():
    """List available backtest strategies."""
    service = _get_service()
    return await service.get_available_strategies()


@router.get("/factors", response_model=list[FactorInfo])
async def list_factors():
    """List available factors (built-in + custom expression)."""
    service = _get_service()
    return await service.get_available_factors()


@router.get("/datasets", response_model=list[DatasetInfo])
async def list_datasets():
    """List registered external datasets."""
    service = _get_service()
    return await service.get_datasets()


# ------------------------------------------------------------------
# Data upload
# ------------------------------------------------------------------

_ALLOWED_UPLOAD_EXT = {".parquet", ".zip", ".xlsx", ".xls", ".csv"}
_TABULAR_EXT = {".xlsx", ".xls", ".csv"}


@router.post("/datasets/upload", response_model=DataUploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    freq: str = Form(default="1d"),
    source: str = Form(default="custom"),
):
    """Upload market data files to data/external/.

    Supported formats:
    - .parquet → saved directly
    - .xlsx / .xls / .csv → auto-converted to Parquet
    - .zip → extracted; inner Excel/CSV files auto-converted to Parquet
    """
    from src.config import get_config
    from src.data.normalizer import convert_to_parquet, convert_to_minute_parquets, TABULAR_EXTENSIONS

    config = get_config()
    base_dir = Path(config.strategy_bt_data_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    is_minute = freq != "1d"

    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()

    if suffix not in _ALLOWED_UPLOAD_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式，仅支持: {', '.join(sorted(_ALLOWED_UPLOAD_EXT))}",
        )

    # Size check (max 2GB)
    max_size = 2 * 1024 * 1024 * 1024
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="文件大小超过 2GB 限制")

    target_dir = base_dir / ("minute" if is_minute else "daily")
    target_dir.mkdir(parents=True, exist_ok=True)

    files_count = 0
    failed_files: list[str] = []

    if suffix == ".parquet":
        if is_minute:
            # For minute parquet, save to minute/{name}/{name}.parquet
            code_dir = target_dir / name
            code_dir.mkdir(parents=True, exist_ok=True)
            target_path = code_dir / f"{name}.parquet"
        else:
            target_path = target_dir / f"{name}.parquet"
        target_path.write_bytes(content)
        files_count = 1
        logger.info("Uploaded parquet: %s (%d bytes)", target_path, len(content))

    elif suffix in _TABULAR_EXT:
        # Single Excel/CSV → convert to Parquet
        # Use first part before '.' as stock code (e.g. "000002.SZSE.xlsx" → "000002")
        code = filename.split(".")[0]
        with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            if is_minute:
                convert_to_minute_parquets(Path(tmp_path), code, target_dir)
            else:
                convert_to_parquet(Path(tmp_path), target_dir / f"{code}.parquet")
            files_count = 1
        except Exception as e:
            logger.warning("Failed to convert %s: %s", filename, e)
            failed_files.append(filename)
        finally:
            os.unlink(tmp_path)

    elif suffix == ".zip":
        # Extract ZIP to temp dir, convert each file
        with NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        tmp_extract = tempfile.mkdtemp(prefix="dsa_upload_")
        try:
            with zipfile.ZipFile(tmp_path, "r") as zf:
                # Security: validate all paths and check for zip bomb
                tmp_resolved = Path(tmp_extract).resolve()
                total_decompressed = 0
                file_count = 0
                max_decompressed = 10 * 1024 * 1024 * 1024  # 10GB
                max_files = 5000
                for member in zf.infolist():
                    target = (Path(tmp_extract) / member.filename).resolve()
                    if not target.is_relative_to(tmp_resolved):
                        raise HTTPException(status_code=400, detail=f"不安全的文件路径: {member.filename}")
                    total_decompressed += member.file_size
                    file_count += 1
                    if total_decompressed > max_decompressed:
                        raise HTTPException(status_code=400, detail="ZIP 解压后总大小超过 10GB 限制")
                    if file_count > max_files:
                        raise HTTPException(status_code=400, detail="ZIP 内文件数量超过 5000 限制")
                zf.extractall(tmp_extract)

            # Walk extracted files and convert
            for fpath in Path(tmp_extract).rglob("*"):
                if not fpath.is_file():
                    continue
                # Skip macOS/system junk
                if fpath.name.startswith(".") or "__MACOSX" in str(fpath):
                    continue

                fsuffix = fpath.suffix.lower()
                code = fpath.name.split(".")[0]  # "000002.SZSE.xlsx" → "000002"

                if fsuffix == ".parquet":
                    if is_minute:
                        code_dir = target_dir / code
                        code_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(str(fpath), str(code_dir / fpath.name))
                    else:
                        shutil.copy2(str(fpath), str(target_dir / fpath.name))
                    files_count += 1
                elif fsuffix in TABULAR_EXTENSIONS:
                    try:
                        if is_minute:
                            convert_to_minute_parquets(fpath, code, target_dir)
                        else:
                            convert_to_parquet(fpath, target_dir / f"{code}.parquet")
                        files_count += 1
                    except Exception as e:
                        logger.warning("Failed to convert %s: %s", fpath.name, e)
                        failed_files.append(fpath.name)
                # else: skip unknown file types silently

            logger.info(
                "Processed ZIP: %d files converted, %d failed", files_count, len(failed_files)
            )
        finally:
            os.unlink(tmp_path)
            shutil.rmtree(tmp_extract, ignore_errors=True)

    # Auto-register dataset — extract date range from data
    from src.data.registry import DatasetRegistry, DatasetMeta
    registry = DatasetRegistry(str(base_dir / "registry.json"))
    from src.data.external_loader import ExternalDataLoader
    loader = ExternalDataLoader(str(base_dir))
    code_count = len(loader.list_available_codes(freq))

    # Scan parquet files to find actual date range
    date_min, date_max = "", ""
    try:
        import pandas as pd
        if is_minute:
            minute_dir = base_dir / "minute"
            for pf in minute_dir.rglob("*.parquet"):
                df = pd.read_parquet(str(pf), columns=["date"])
                if "date" in df.columns and len(df) > 0:
                    d_min = str(df["date"].min())[:10]
                    d_max = str(df["date"].max())[:10]
                    date_min = d_min if not date_min else min(date_min, d_min)
                    date_max = d_max if not date_max else max(date_max, d_max)
        else:
            daily_dir = base_dir / "daily"
            for pf in daily_dir.glob("*.parquet"):
                df = pd.read_parquet(str(pf), columns=["date"])
                if "date" in df.columns and len(df) > 0:
                    d_min = str(df["date"].min())[:10]
                    d_max = str(df["date"].max())[:10]
                    date_min = d_min if not date_min else min(date_min, d_min)
                    date_max = d_max if not date_max else max(date_max, d_max)
    except Exception as e:
        logger.warning("Failed to extract date range: %s", e)

    registry.register(DatasetMeta(
        name=name,
        path=str(base_dir),
        freq=freq,
        source=source,
        date_range=(date_min, date_max),
        code_count=code_count,
    ))

    msg = f"上传成功，{files_count} 个文件已转换"
    if failed_files:
        msg += f"，{len(failed_files)} 个文件转换失败"

    return DataUploadResponse(
        message=msg,
        files_count=files_count,
        dataset_name=name,
        failed_files=failed_files,
    )


# ------------------------------------------------------------------
# Custom expression factors
# ------------------------------------------------------------------

@router.post("/factors/custom", response_model=CustomFactorResponse)
async def create_custom_factor(req: CustomFactorRequest):
    """Create a custom factor from a Python expression."""
    from src.backtest_bt.factors.expression import register_expression_factor
    error = register_expression_factor(req.name, req.expression, req.description)
    if error:
        raise HTTPException(status_code=400, detail=error)
    # Persist to DB
    from src.services.strategy_bt_service import StrategyBtService
    StrategyBtService._persist_custom_factor(req.name, req.expression, req.description)
    return CustomFactorResponse(name=req.name, message="因子创建成功")


@router.get("/factors/custom", response_model=list[FactorInfo])
async def list_custom_factors():
    """List user-defined expression factors."""
    from src.backtest_bt.factors.expression import list_custom_expression_factors
    return [
        FactorInfo(name=f["name"], description=f.get("description", f.get("expression", "")))
        for f in list_custom_expression_factors()
    ]


@router.delete("/factors/custom/{factor_name}")
async def delete_custom_factor(factor_name: str):
    """Delete a custom expression factor."""
    from src.backtest_bt.factors.expression import remove_expression_factor
    if not remove_expression_factor(factor_name):
        raise HTTPException(status_code=404, detail="因子不存在")
    from src.services.strategy_bt_service import StrategyBtService
    StrategyBtService._remove_persisted_custom_factor(factor_name)
    return {"message": "因子已删除"}


# ------------------------------------------------------------------
# Custom expression strategies
# ------------------------------------------------------------------

@router.post("/strategies/custom/validate", response_model=ExprValidateResponse)
async def validate_expression(req: ExprValidateRequest):
    """Validate a strategy/factor expression and return translated form."""
    from src.backtest_bt.formula_translator import translate_formula, is_tdx_formula
    from src.backtest_bt.strategies.expression import validate_strategy_expression

    try:
        validate_strategy_expression(req.expression)
        translated = translate_formula(req.expression) if is_tdx_formula(req.expression) else None
        return ExprValidateResponse(valid=True, translated=translated)
    except ValueError as e:
        return ExprValidateResponse(valid=False, error=str(e))


@router.post("/strategies/custom/parse", response_model=ExprParseResponse)
async def parse_expression(req: ExprParseRequest):
    """Parse a full strategy expression into buy/sell conditions."""
    from src.backtest_bt.formula_parser import parse_strategy_expression

    result = parse_strategy_expression(req.expression)
    return ExprParseResponse(**result)


@router.post("/strategies/custom", response_model=CustomStrategyResponse)
async def create_custom_strategy(req: CustomStrategyRequest):
    """Create a custom strategy from buy/sell expressions."""
    service = _get_service()
    error = await service.create_custom_strategy(
        req.name, req.buy_expression, req.sell_expression, req.description
    )
    if error:
        raise HTTPException(status_code=400, detail=error)
    return CustomStrategyResponse(name=req.name, message="策略创建成功")


@router.get("/strategies/custom", response_model=list[CustomStrategyInfo])
async def list_custom_strategies():
    """List user-defined expression strategies."""
    service = _get_service()
    return await service.list_custom_strategies()


@router.delete("/strategies/custom/{strategy_name}")
async def delete_custom_strategy(strategy_name: str):
    """Delete a custom expression strategy."""
    service = _get_service()
    if not await service.delete_custom_strategy(strategy_name):
        raise HTTPException(status_code=404, detail="策略不存在")
    return {"message": "策略已删除"}


@router.delete("/runs/{run_id}")
async def delete_run(run_id: int):
    """Delete a backtest run by ID."""
    service = _get_service()
    if not await service.delete_run(run_id):
        raise HTTPException(status_code=404, detail="回测记录不存在")
    return {"message": "回测记录已删除"}


@router.delete("/datasets/{dataset_name}")
async def delete_dataset(dataset_name: str):
    """Delete a registered dataset and its files."""
    service = _get_service()
    if not await service.delete_dataset(dataset_name):
        raise HTTPException(status_code=404, detail="数据集不存在")
    return {"message": "数据集已删除"}


# ------------------------------------------------------------------
# Available codes from datasets
# ------------------------------------------------------------------

@router.get("/codes", response_model=AvailableCodesResponse)
async def list_available_codes(freq: str = Query(default="1d")):
    """List all available stock codes from uploaded datasets."""
    from src.config import get_config
    from src.data.external_loader import ExternalDataLoader

    config = get_config()
    loader = ExternalDataLoader(config.data_dir)
    codes = loader.list_available_codes(freq=freq)
    return AvailableCodesResponse(codes=sorted(codes), count=len(codes))
