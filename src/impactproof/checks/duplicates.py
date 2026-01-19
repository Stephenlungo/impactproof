from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import pandas as pd


@dataclass
class DuplicatesResult:
    check: str
    status: str  # PASS | WARN | FAIL
    duplicate_rows: int
    total_rows: int
    duplicate_rate: float
    notes: str
    issues: pd.DataFrame


def run_duplicates(df: pd.DataFrame, cfg: Dict[str, Any]) -> DuplicatesResult:
    keys: List[str] = cfg.get("keys", [])
    pass_thr: float = float(cfg.get("pass_threshold", 0.0))
    warn_thr: float = float(cfg.get("warn_threshold", 0.02))

    missing_cols = [c for c in keys if c not in df.columns]
    if missing_cols:
        issues = pd.DataFrame([{
            "check": "duplicates",
            "record_index": None,
            "field": None,
            "message": f"Missing key columns in dataset: {missing_cols}",
            "suggested_fix": "Update keys or add/match these columns in input/mapping.",
        }])
        return DuplicatesResult(
            check="duplicates",
            status="FAIL",
            duplicate_rows=0,
            total_rows=len(df),
            duplicate_rate=0.0,
            notes=f"Key columns missing: {missing_cols}",
            issues=issues,
        )

    total_rows = int(len(df))
    if total_rows == 0:
        return DuplicatesResult(
            check="duplicates",
            status="PASS",
            duplicate_rows=0,
            total_rows=0,
            duplicate_rate=0.0,
            notes="No rows to evaluate",
            issues=pd.DataFrame(columns=["check", "record_index", "field", "message", "suggested_fix"]),
        )

    # mark duplicates on the key set (keep all duplicates)
    dup_mask = df.duplicated(subset=keys, keep=False)
    dup_rows = int(dup_mask.sum())
    dup_rate = dup_rows / total_rows

    if dup_rate <= pass_thr:
        status = "PASS"
    elif dup_rate <= warn_thr:
        status = "WARN"
    else:
        status = "FAIL"

    # record-level issues for duplicate rows
    issues = df.loc[dup_mask, keys].copy()
    issues["check"] = "duplicates"
    issues["record_index"] = issues.index
    issues["field"] = ",".join(keys)
    issues["message"] = "Duplicate record detected for key combination"
    issues["suggested_fix"] = "De-duplicate upstream, or adjust keys if the duplication is expected."
    issues = issues[["check", "record_index", "field", "message", "suggested_fix"]]

    notes = f"{dup_rate:.1%} duplicate rows on keys {keys} ({dup_rows}/{total_rows})"
    return DuplicatesResult(
        check="duplicates",
        status=status,
        duplicate_rows=dup_rows,
        total_rows=total_rows,
        duplicate_rate=dup_rate,
        notes=notes,
        issues=issues,
    )