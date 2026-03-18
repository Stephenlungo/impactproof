from __future__ import annotations

from typing import Any

import pandas as pd


ISSUE_COLUMNS = ["check", "record_index", "field", "severity", "message", "suggested_fix"]


def empty_issues() -> pd.DataFrame:
    return pd.DataFrame(columns=ISSUE_COLUMNS)


def issue_row(
    check: str,
    record_index: Any,
    field: Any,
    severity: str,
    message: str,
    suggested_fix: str,
) -> dict[str, Any]:
    return {
        "check": check,
        "record_index": record_index,
        "field": field,
        "severity": severity,
        "message": message,
        "suggested_fix": suggested_fix,
    }


def ensure_issue_schema(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return empty_issues()

    out = df.copy()
    for col in ISSUE_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    return out[ISSUE_COLUMNS]
