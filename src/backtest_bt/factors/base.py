# -*- coding: utf-8 -*-
"""Factor system — base classes and registry."""

from __future__ import annotations

import importlib
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class BaseFactor(ABC):
    """Abstract base class for all factors.

    Subclasses must set ``name`` and ``description`` as class attributes
    and implement ``compute()``.
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.Series:
        """Compute factor values from an OHLCV DataFrame.

        Args:
            df: DataFrame with at least columns: open, high, low, close, volume.

        Returns:
            A Series of factor values aligned with df's index.
        """

    def __repr__(self) -> str:
        return f"<Factor: {self.name}>"


class FactorRegistry:
    """Global registry for factor classes."""

    _factors: dict[str, type[BaseFactor]] = {}

    @classmethod
    def register(cls, factor_cls: type[BaseFactor]) -> type[BaseFactor]:
        """Register a factor class. Can be used as a decorator."""
        if not factor_cls.name:
            raise ValueError(f"Factor class {factor_cls.__name__} must define a 'name' attribute")
        cls._factors[factor_cls.name] = factor_cls
        logger.debug("Registered factor: %s", factor_cls.name)
        return factor_cls

    @classmethod
    def get(cls, name: str) -> Optional[type[BaseFactor]]:
        return cls._factors.get(name)

    @classmethod
    def list_all(cls) -> list[str]:
        return sorted(cls._factors.keys())

    @classmethod
    def get_all(cls) -> dict[str, type[BaseFactor]]:
        return dict(cls._factors)

    @classmethod
    def load_custom_factors(cls, directory: str) -> int:
        """Scan a directory for .py files and import them to trigger registration.

        Returns the number of newly registered factors.
        """
        before = len(cls._factors)
        factor_dir = Path(directory)
        if not factor_dir.is_dir():
            logger.warning("Custom factor directory not found: %s", directory)
            return 0

        for py_file in sorted(factor_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = f"custom_factors.{py_file.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)  # type: ignore[union-attr]
            except Exception as e:
                logger.warning("Failed to load custom factor %s: %s", py_file.name, e)

        added = len(cls._factors) - before
        if added:
            logger.info("Loaded %d custom factor(s) from %s", added, directory)
        return added
