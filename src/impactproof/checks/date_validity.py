from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from impactproof.issues import empty_issues, issue_row


@dataclass
class DateValidityResult:
    check: str
    status: str
    invalid_count: int
    notes: str
    issues: pd.DataFrame


def run_date_validity(df: pd.DataFrame, cfg: dict[str, Any]) -> DateValidityResult:
    fields = cfg.get("fields", []) if cfg else []
    if not fields:
        return DateValidityResult(
            check="date_validity",
            status="PASS",
            invalid_count=0,
            notes="No date-validity fields configured",
            issues=empty_issues(),
        )

    issues_rows: list[dict[str, Any]] = []

    for field in fields:
        if field not in df.columns:
            issues_rows.append(
                issue_row(
                    "date_validity",
                    None,
                    field,
                    "WARN",
                    f"Date-validity rule skipped: field '{field}' is missing from the dataset",
                    "Fix the field mapping or remove this field from the configuration.",
                )
            )
            continue

        raw = df[field]
        candidates = raw.astype("string").str.strip()
        present_mask = raw.notna() & candidates.ne("") & ~candidates.isin(["NA", "UNKNOWN"])
        parsed = pd.to_datetime(raw[present_mask], errors="coerce")

        for idx in raw[present_mask].index[parsed.isna()]:
            issues_rows.append(
                issue_row(
                    "date_validity",
                    int(idx),
                    field,
                    "ERROR",
                    f"Invalid date value '{df.at[idx, field]}' in '{field}'",
                    "Use a parseable date format such as YYYY-MM-DD.",
                )
            )

    issues = pd.DataFrame(issues_rows)
    record_issue_count = int(issues["record_index"].notna().sum()) if not issues.empty else 0
    config_issue_count = int(issues["record_index"].isna().sum()) if not issues.empty else 0
    status = "FAIL" if record_issue_count else "WARN" if config_issue_count else "PASS"
    notes = f"{len(fields)} fields evaluated; {record_issue_count} invalid date values"
    return DateValidityResult(
        check="date_validity",
        status=status,
        invalid_count=record_issue_count,
        notes=notes,
        issues=issues if not issues.empty else empty_issues(),
    )
