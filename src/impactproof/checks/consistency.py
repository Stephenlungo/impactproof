from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import pandas as pd


@dataclass
class ConsistencyResult:
    check: str
    status: str  # PASS | WARN | FAIL
    failed_rules: int
    issues_count: int
    notes: str
    issues: pd.DataFrame


def _is_missing(val: Any) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return True
    s = str(val).strip()
    return s == "" or s in {"NA", "UNKNOWN"}


def run_consistency(df: pd.DataFrame, cfg: Dict[str, Any]) -> ConsistencyResult:
    rules: List[Dict[str, Any]] = cfg.get("rules", []) if cfg else []

    if not rules:
        return ConsistencyResult(
            check="consistency",
            status="PASS",
            failed_rules=0,
            issues_count=0,
            notes="No rules configured",
            issues=pd.DataFrame(columns=["check", "record_index", "field", "message", "suggested_fix"]),
        )

    issues_rows: List[Dict[str, Any]] = []
    failed_rule_names = set()

    for rule in rules:
        name = rule.get("name", "UnnamedRule")

        when = rule.get("when", {})
        when_field = when.get("field")
        when_equals = when.get("equals")

        if not when_field or when_field not in df.columns:
            issues_rows.append({
                "check": "consistency",
                "record_index": None,
                "field": None,
                "message": f"Rule '{name}' skipped: missing when.field '{when_field}' in dataset",
                "suggested_fix": "Fix field mapping or adjust rule configuration.",
            })
            failed_rule_names.add(name)
            continue

        # Rows where the condition applies
        mask = df[when_field].astype(str).str.strip().eq(str(when_equals).strip())

        # THEN: required fields must be present
        then_required = rule.get("then_required", [])
        for req_field in then_required:
            if req_field not in df.columns:
                issues_rows.append({
                    "check": "consistency",
                    "record_index": None,
                    "field": None,
                    "message": f"Rule '{name}' failed: required field '{req_field}' not in dataset",
                    "suggested_fix": "Fix field mapping or adjust rule configuration.",
                })
                failed_rule_names.add(name)
                continue

            for idx in df.index[mask]:
                val = df.at[idx, req_field]
                if _is_missing(val):
                    issues_rows.append({
                        "check": "consistency",
                        "record_index": int(idx),
                        "field": req_field,
                        "message": f"Rule '{name}': '{when_field}' is '{when_equals}' so '{req_field}' is required",
                        "suggested_fix": f"Populate '{req_field}' for this record, or correct '{when_field}' if misclassified.",
                    })
                    failed_rule_names.add(name)

        # THEN: specific fields must equal given values
        then_equals = rule.get("then_equals", {}) or {}
        for field, expected in then_equals.items():
            if field not in df.columns:
                issues_rows.append({
                    "check": "consistency",
                    "record_index": None,
                    "field": None,
                    "message": f"Rule '{name}' failed: field '{field}' not in dataset",
                    "suggested_fix": "Fix field mapping or adjust rule configuration.",
                })
                failed_rule_names.add(name)
                continue

            for idx in df.index[mask]:
                actual = "" if pd.isna(df.at[idx, field]) else str(df.at[idx, field]).strip()
                exp = str(expected).strip()
                if actual != exp:
                    issues_rows.append({
                        "check": "consistency",
                        "record_index": int(idx),
                        "field": field,
                        "message": f"Rule '{name}': expected '{field}' == '{exp}' when '{when_field}' == '{when_equals}' (got '{actual}')",
                        "suggested_fix": f"Set '{field}' to '{exp}' or correct '{when_field}'.",
                    })
                    failed_rule_names.add(name)

    issues = pd.DataFrame(issues_rows, columns=["check", "record_index", "field", "message", "suggested_fix"])

    # Simple status: any real record issues => FAIL, config problems => WARN
    record_issue_count = issues["record_index"].notna().sum() if not issues.empty else 0
    config_issue_count = issues["record_index"].isna().sum() if not issues.empty else 0

    if record_issue_count > 0:
        status = "FAIL"
    elif config_issue_count > 0:
        status = "WARN"
    else:
        status = "PASS"

    notes = f"{len(failed_rule_names)} rule(s) triggered; {len(issues)} issue(s)"
    return ConsistencyResult(
        check="consistency",
        status=status,
        failed_rules=len(failed_rule_names),
        issues_count=int(len(issues)),
        notes=notes,
        issues=issues,
    )