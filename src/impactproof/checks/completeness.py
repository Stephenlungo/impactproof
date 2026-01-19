from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import pandas as pd


@dataclass
class CompletenessResult:
    check: str
    status: str  # PASS | WARN | FAIL
    completeness_rate: float
    missing_cells: int
    total_required_cells: int
    notes: str
    issues: pd.DataFrame  # record-level issues


def run_completeness(df: pd.DataFrame, cfg: Dict[str, Any]) -> CompletenessResult:
    required_fields: List[str] = cfg.get("required_fields", [])
    pass_thr: float = float(cfg.get("pass_threshold", 0.95))
    warn_thr: float = float(cfg.get("warn_threshold", 0.85))

    # Validate required fields exist in df
    missing_cols = [c for c in required_fields if c not in df.columns]
    if missing_cols:
        issues = pd.DataFrame([{
            "check": "completeness",
            "record_index": None,
            "field": None,
            "message": f"Missing required columns in dataset: {missing_cols}",
            "suggested_fix": "Update field mapping or provide these columns in the input.",
        }])
        return CompletenessResult(
            check="completeness",
            status="FAIL",
            completeness_rate=0.0,
            missing_cells=0,
            total_required_cells=max(len(required_fields) * max(len(df), 1), 1),
            notes=f"Required columns missing: {missing_cols}",
            issues=issues,
        )

    # Compute completeness over required cells (row x required_fields)
    required = df[required_fields]

    # Treat NA/UNKNOWN as missing; NO is allowed as a real value
    norm = required.astype(str).apply(lambda s: s.str.strip())
    is_missing = required.isna() | norm.eq("") | norm.eq("NA") | norm.eq("UNKNOWN")
    is_present = ~is_missing

    total_required_cells = int(is_present.size)
    present_cells = int(is_present.values.sum())
    missing_cells = total_required_cells - present_cells
    completeness_rate = present_cells / total_required_cells if total_required_cells else 0.0

    # Status logic
    if completeness_rate >= pass_thr:
        status = "PASS"
    elif completeness_rate >= warn_thr:
        status = "WARN"
    else:
        status = "FAIL"

    # Record-level issues: one row per missing required field per record
    issues_rows = []
    missing_tokens = {"", "NA", "UNKNOWN"}

    for idx, row in required.iterrows():
        for col in required_fields:
            val = row[col]
            s = "" if pd.isna(val) else str(val).strip()
            if pd.isna(val) or s in missing_tokens:
                issues_rows.append({
                    "check": "completeness",
                    "record_index": idx,
                    "field": col,
                    "message": f"Missing required value for '{col}'",
                    "suggested_fix": f"Populate '{col}' or mark explicitly (NA/UNKNOWN) where appropriate.",
                })
    issues = pd.DataFrame(issues_rows)

    notes = f"{completeness_rate:.1%} required cells present ({missing_cells} missing of {total_required_cells})"
    return CompletenessResult(
        check="completeness",
        status=status,
        completeness_rate=completeness_rate,
        missing_cells=missing_cells,
        total_required_cells=total_required_cells,
        notes=notes,
        issues=issues,
    )