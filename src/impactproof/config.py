from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import yaml


@dataclass
class ImpactProofConfig:
    raw: Dict[str, Any]

    @property
    def output_path(self) -> Path:
        out = self.raw.get("output", {}).get("path", "outputs/")
        return Path(out)

    @property
    def input_csv_file(self) -> Path:
        file = self.raw.get("input", {}).get("csv", {}).get("file")
        if not file:
            raise ValueError("input.csv.file is required for csv mode")
        return Path(file)

    @property
    def completeness_cfg(self) -> dict:
        return self.raw.get("checks", {}).get("completeness", {})
    
    @property
    def duplicates_cfg(self) -> dict:
        return self.raw.get("checks", {}).get("duplicates", {})


def load_config(path: str | Path) -> ImpactProofConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return ImpactProofConfig(raw=raw)