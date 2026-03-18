from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from impactproof.issues import empty_issues, issue_row


@dataclass
class AllowedValuesResult:
    check: str
    status: str
    failed_rules: int
    issues_count: int
    notes: str
    issues: pd.DataFrame


def run_allowed_values(df: pd.DataFrame, cfg: dict[str, Any]) -> AllowedValuesResult:
    rules = cfg.get("rules", []) if cfg else []
    if not rules:
        return AllowedValuesResult(
            check="allowed_values",
            status="PASS",
            failed_rules=0,
            issues_count=0,
            notes="No allowed-values rules configured",
            issues=empty_issues(),
        )

    issues_rows: list[dict[str, Any]] = []
    failed_rules = 0

    for rule in rules:
        field = rule.get("field")
        allowed = {str(v).strip() for v in rule.get("allowed", [])}
        allow_missing = bool(rule.get("allow_missing", True))

        if not field or field not in df.columns:
            failed_rules += 1
            issues_rows.append(
                issue_row(
                    "allowed_values",
                    None,
                    field,
                    "WARN",
                    f"Allowed-values rule skipped: field '{field}' is missing from the dataset",
                    "Fix the field mapping or remove this rule.",
                )
            )
            continue

        rule_failed = False
        for idx, value in df[field].items():
            if pd.isna(value):
                if allow_missing:
                    continue
                actual = "NA"
            else:
                actual = str(value).strip()
                if allow_missing and actual in {"", "NA", "UNKNOWN"}:
                    continue

            if actual not in allowed:
                rule_failed = True
                issues_rows.append(
                    issue_row(
                        "allowed_values",
                        int(idx),
                        field,
                        "ERROR",
                        f"Invalid value '{actual}' for '{field}'",
                        f"Replace with one of: {sorted(allowed)}",
                    )
                )

        if rule_failed:
            failed_rules += 1

    issues = pd.DataFrame(issues_rows)
    status = "FAIL" if not issues.empty and issues["record_index"].notna().any() else "WARN" if not issues.empty else "PASS"
    notes = f"{len(rules)} rules evaluated; {failed_rules} produced issues; {len(issues_rows)} total issues"
    return AllowedValuesResult(
        check="allowed_values",
        status=status,
        failed_rules=failed_rules,
        issues_count=len(issues_rows),
        notes=notes,
        issues=issues if not issues.empty else empty_issues(),
    )
