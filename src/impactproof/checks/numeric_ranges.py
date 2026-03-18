from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from impactproof.issues import empty_issues, issue_row


@dataclass
class NumericRangesResult:
    check: str
    status: str
    failed_rules: int
    issues_count: int
    notes: str
    issues: pd.DataFrame


def run_numeric_ranges(df: pd.DataFrame, cfg: dict[str, Any]) -> NumericRangesResult:
    rules = cfg.get("rules", []) if cfg else []
    if not rules:
        return NumericRangesResult(
            check="numeric_ranges",
            status="PASS",
            failed_rules=0,
            issues_count=0,
            notes="No numeric-range rules configured",
            issues=empty_issues(),
        )

    issues_rows: list[dict[str, Any]] = []
    failed_rules = 0

    for rule in rules:
        field = rule.get("field")
        minimum = rule.get("min")
        maximum = rule.get("max")
        allow_missing = bool(rule.get("allow_missing", True))

        if not field or field not in df.columns:
            failed_rules += 1
            issues_rows.append(
                issue_row(
                    "numeric_ranges",
                    None,
                    field,
                    "WARN",
                    f"Numeric-range rule skipped: field '{field}' is missing from the dataset",
                    "Fix the field mapping or remove this rule.",
                )
            )
            continue

        numeric = pd.to_numeric(df[field], errors="coerce")
        raw = df[field]
        candidates = raw.astype("string").str.strip()
        present_mask = raw.notna() & candidates.ne("") & ~candidates.isin(["NA", "UNKNOWN"])
        rule_failed = False

        for idx in raw[present_mask].index[numeric[present_mask].isna()]:
            rule_failed = True
            issues_rows.append(
                issue_row(
                    "numeric_ranges",
                    int(idx),
                    field,
                    "ERROR",
                    f"Value '{df.at[idx, field]}' in '{field}' is not numeric",
                    "Use a numeric value or update the rule if this field should not be numeric.",
                )
            )

        if not allow_missing:
            for idx in raw.index[~present_mask]:
                rule_failed = True
                issues_rows.append(
                    issue_row(
                        "numeric_ranges",
                        int(idx),
                        field,
                        "ERROR",
                        f"Missing numeric value in '{field}'",
                        f"Populate '{field}' with a value between {minimum} and {maximum}.",
                    )
                )

        valid_numeric_mask = present_mask & numeric.notna()

        if minimum is not None:
            below_mask = valid_numeric_mask & numeric.lt(float(minimum))
            for idx in raw.index[below_mask]:
                rule_failed = True
                issues_rows.append(
                    issue_row(
                        "numeric_ranges",
                        int(idx),
                        field,
                        "ERROR",
                        f"Value {numeric.at[idx]} in '{field}' is below the minimum of {minimum}",
                        f"Set '{field}' to a value greater than or equal to {minimum}.",
                    )
                )

        if maximum is not None:
            above_mask = valid_numeric_mask & numeric.gt(float(maximum))
            for idx in raw.index[above_mask]:
                rule_failed = True
                issues_rows.append(
                    issue_row(
                        "numeric_ranges",
                        int(idx),
                        field,
                        "ERROR",
                        f"Value {numeric.at[idx]} in '{field}' exceeds the maximum of {maximum}",
                        f"Set '{field}' to a value less than or equal to {maximum}.",
                    )
                )

        if rule_failed:
            failed_rules += 1

    issues = pd.DataFrame(issues_rows)
    status = "FAIL" if not issues.empty and issues["record_index"].notna().any() else "WARN" if not issues.empty else "PASS"
    notes = f"{len(rules)} rules evaluated; {failed_rules} produced issues; {len(issues_rows)} total issues"
    return NumericRangesResult(
        check="numeric_ranges",
        status=status,
        failed_rules=failed_rules,
        issues_count=len(issues_rows),
        notes=notes,
        issues=issues if not issues.empty else empty_issues(),
    )
