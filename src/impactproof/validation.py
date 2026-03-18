from __future__ import annotations

from typing import Any


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _list_value(section: dict[str, Any], key: str) -> list[Any]:
    value = section.get(key, [])
    return value if isinstance(value, list) else []


def validate_config(raw: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    input_cfg = raw.get("input", {})
    csv_file = input_cfg.get("csv", {}).get("file")
    if input_cfg.get("mode", "csv") != "csv":
        errors.append("Only input.mode='csv' is supported in the current MVP.")
    if not csv_file:
        errors.append("input.csv.file is required.")

    checks = raw.get("checks", {})

    completeness = checks.get("completeness", {})
    if "required_fields" in completeness and not isinstance(completeness.get("required_fields"), list):
        errors.append("checks.completeness.required_fields must be a list.")

    duplicates = checks.get("duplicates", {})
    if "keys" in duplicates and not isinstance(duplicates.get("keys"), list):
        errors.append("checks.duplicates.keys must be a list.")
    dup_keys = _list_value(duplicates, "keys")
    if not dup_keys:
        errors.append("checks.duplicates.keys must include at least one field.")

    drift = checks.get("drift", {})
    if drift:
        if drift.get("period", "monthly") not in {"monthly", "weekly"}:
            errors.append("checks.drift.period must be 'monthly' or 'weekly'.")
        if int(drift.get("baseline_periods", 1)) < 1:
            errors.append("checks.drift.baseline_periods must be at least 1.")

    allowed_values = checks.get("allowed_values", {})
    rules = allowed_values.get("rules", [])
    if allowed_values and not isinstance(rules, list):
        errors.append("checks.allowed_values.rules must be a list.")
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"checks.allowed_values.rules[{idx}] must be an object.")
            continue
        if not isinstance(rule.get("allowed", []), list):
            errors.append(f"checks.allowed_values.rules[{idx}].allowed must be a list.")

    date_validity = checks.get("date_validity", {})
    date_fields = date_validity.get("fields", [])
    if date_validity and not isinstance(date_fields, list):
        errors.append("checks.date_validity.fields must be a list.")

    numeric_ranges = checks.get("numeric_ranges", {})
    numeric_rules = numeric_ranges.get("rules", [])
    if numeric_ranges and not isinstance(numeric_rules, list):
        errors.append("checks.numeric_ranges.rules must be a list.")
    for idx, rule in enumerate(numeric_rules):
        if not isinstance(rule, dict):
            errors.append(f"checks.numeric_ranges.rules[{idx}] must be an object.")
            continue
        if rule.get("min") is not None and not _is_number(rule.get("min")):
            errors.append(f"checks.numeric_ranges.rules[{idx}].min must be numeric.")
        if rule.get("max") is not None and not _is_number(rule.get("max")):
            errors.append(f"checks.numeric_ranges.rules[{idx}].max must be numeric.")

    cross_field = checks.get("cross_field", {})
    cross_rules = cross_field.get("rules", [])
    if cross_field and not isinstance(cross_rules, list):
        errors.append("checks.cross_field.rules must be a list.")
    allowed_operators = {"<", "<=", ">", ">=", "==", "!="}
    allowed_compare_as = {"numeric", "date", "string"}
    for idx, rule in enumerate(cross_rules):
        if not isinstance(rule, dict):
            errors.append(f"checks.cross_field.rules[{idx}] must be an object.")
            continue
        if rule.get("operator") not in allowed_operators:
            errors.append(f"checks.cross_field.rules[{idx}].operator must be one of {sorted(allowed_operators)}.")
        if rule.get("compare_as", "string") not in allowed_compare_as:
            errors.append(f"checks.cross_field.rules[{idx}].compare_as must be one of {sorted(allowed_compare_as)}.")

    return errors
