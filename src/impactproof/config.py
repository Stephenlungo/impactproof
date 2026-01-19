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


def load_config(path: str | Path) -> ImpactProofConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    return ImpactProofConfig(raw=raw)