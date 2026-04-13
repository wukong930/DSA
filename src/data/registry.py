# -*- coding: utf-8 -*-
"""Dataset registry for external market data sources."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DatasetMeta:
    """Metadata for a registered external dataset."""
    name: str
    path: str
    freq: str           # "1d" / "1min" / "5min"
    source: str          # "haitong" / "tushare" / "custom"
    date_range: tuple[str, str] = ("", "")
    code_count: int = 0


class DatasetRegistry:
    """Manage registered external datasets.

    Persists registry to a JSON file alongside the data directory.
    """

    def __init__(self, registry_path: Optional[str] = None):
        self._datasets: dict[str, DatasetMeta] = {}
        self._registry_path = Path(registry_path) if registry_path else None
        if self._registry_path and self._registry_path.exists():
            self._load()

    def register(self, meta: DatasetMeta) -> None:
        self._datasets[meta.name] = meta
        self._save()
        logger.info("Registered dataset: %s (%s, %s)", meta.name, meta.source, meta.freq)

    def unregister(self, name: str) -> bool:
        if name in self._datasets:
            del self._datasets[name]
            self._save()
            return True
        return False

    def list_datasets(self) -> list[DatasetMeta]:
        return list(self._datasets.values())

    def get(self, name: str) -> Optional[DatasetMeta]:
        return self._datasets.get(name)

    def _save(self) -> None:
        if not self._registry_path:
            return
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        data = []
        for meta in self._datasets.values():
            d = asdict(meta)
            d["date_range"] = list(d["date_range"])
            data.append(d)
        self._registry_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _load(self) -> None:
        try:
            data = json.loads(self._registry_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
            for item in data:
                item["date_range"] = tuple(item.get("date_range", ("", "")))
                self._datasets[item["name"]] = DatasetMeta(**item)
        except Exception as e:
            logger.warning("Failed to load dataset registry: %s", e)
