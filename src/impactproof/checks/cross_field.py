from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from impactproof.issues import empty_issues, issue_row


@dataclass
class CrossFieldResult:
    check: str
    status: str
    failed_rules: int
    issues_count: int
    notes: str
    issues: pd.DataFrame


def _coerce_pair(left: Any, right: Any, compare_as: str) -> tuple[Any, Any, bool]:
    if compare_as == "numeric":
        left_num = pd.to_numeric(pd.Series([left]), errors="coerce").iloc[0]
        right_num = pd.to_numeric(pd.Series([right]), errors="coerce").iloc[0]
        return left_num, right_num, pd.notna(left_num) and pd.notna(right_num)

    if compare_as == "date":
        left_date = pd.to_datetime(pd.Series([left]), errors="coerce").iloc[0]
        right_date = pd.to_datetime(pd.Series([right]), errors="coerce").iloc[0]
        return left_date, right_date, pd.notna(left_date) and pd.notna(right_date)

    return str(left).strip(), str(right).strip(), True


def _compare(left: Any, operator: str, right: Any) -> bool:
    if operator == "<":
        return left < right
    if operator == "<=":
        return left <= right
    if operator == ">":
        return left > right
    if operator == ">=":
        return left >= right
    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    raise ValueError(f"Unsupported operator: {operator}")


def run_cross_field(df: pd.DataFrame, cfg: dict[str, Any]) -> CrossFieldResult:
    rules = cfg.get("rules", []) if cfg else []
    if not rules:
        return CrossFieldResult(
            check="cross_field",
            status="PASS",
            failed_rules=0,
            issues_count=0,
            notes="No cross-field rules configured",
            issues=empty_issues(),
        )

    issues_rows: list[dict[str, Any]] = []
    failed_rules = 0

    for rule in rules:
        name = rule.get("name", "UnnamedCrossFieldRule")
        left_field = rule.get("left_field")
        right_field = rule.get("right_field")
        operator = rule.get("operator")
        compare_as = rule.get("compare_as", "string")
        allow_missing = bool(rule.get("allow_missing", True))

        missing_fields = [field for field in [left_field, right_field] if not field or field not in df.columns]
        if missing_fields:
            failed_rules += 1
            issues_rows.append(
                issue_row(
                    "cross_field",
                    None,
                    ",".join(missing_fields),
                    "WARN",
                    f"Cross-field rule '{name}' skipped: missing field(s) {missing_fields}",
                    "Fix the field mapping or remove this rule.",
                )
            )
            continue

        rule_failed = False

        for idx in df.index:
            left_raw = df.at[idx, left_field]
            right_raw = df.at[idx, right_field]

            left_missing = pd.isna(left_raw) or str(left_raw).strip() in {"", "NA", "UNKNOWN"}
            right_missing = pd.isna(right_raw) or str(right_raw).strip() in {"", "NA", "UNKNOWN"}

            if left_missing or right_missing:
                if allow_missing:
                    continue
                rule_failed = True
                issues_rows.append(
                    issue_row(
                        "cross_field",
                        int(idx),
                        f"{left_field},{right_field}",
                        "ERROR",
                        f"Rule '{name}' requires both '{left_field}' and '{right_field}' to be present",
                        "Populate both fields or allow missing values in the rule.",
                    )
                )
                continue

            left_value, right_value, valid = _coerce_pair(left_raw, right_raw, compare_as)
            if not valid:
                rule_failed = True
                issues_rows.append(
                    issue_row(
                        "cross_field",
                        int(idx),
                        f"{left_field},{right_field}",
                        "ERROR",
                        f"Rule '{name}' could not compare '{left_field}' and '{right_field}' as {compare_as}",
                        f"Ensure both fields contain valid {compare_as} values.",
                    )
                )
                continue

            if not _compare(left_value, operator, right_value):
                rule_failed = True
                issues_rows.append(
                    issue_row(
                        "cross_field",
                        int(idx),
                        f"{left_field},{right_field}",
                        "ERROR",
                        f"Rule '{name}' failed: expected '{left_field}' {operator} '{right_field}'",
                        f"Correct '{left_field}' or '{right_field}' so the relationship holds.",
                    )
                )

        if rule_failed:
            failed_rules += 1

    issues = pd.DataFrame(issues_rows)
    status = "FAIL" if not issues.empty and issues["record_index"].notna().any() else "WARN" if not issues.empty else "PASS"
    notes = f"{len(rules)} rules evaluated; {failed_rules} produced issues; {len(issues_rows)} total issues"
    return CrossFieldResult(
        check="cross_field",
        status=status,
        failed_rules=failed_rules,
        issues_count=len(issues_rows),
        notes=notes,
        issues=issues if not issues.empty else empty_issues(),
    )
