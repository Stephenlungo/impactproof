from __future__ import annotations

import io
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from impactproof.issues import empty_issues, ensure_issue_schema
from impactproof.profiling import profile_dataset
from impactproof.validation import validate_config
from impactproof.standardize.missing_labels import apply_missing_labels
from impactproof.checks.completeness import run_completeness
from impactproof.checks.duplicates import run_duplicates
from impactproof.checks.consistency import run_consistency
from impactproof.checks.drift import run_drift
from impactproof.checks.allowed_values import run_allowed_values
from impactproof.checks.date_validity import run_date_validity
from impactproof.checks.numeric_ranges import run_numeric_ranges
from impactproof.checks.cross_field import run_cross_field


st.set_page_config(page_title="ImpactProof Pilot UI", layout="wide")
st.title("ImpactProof — Pilot v0.5.0")
st.caption("Upload a CSV, configure checks, run, and review outputs.")


# ---------------------------
# Helpers
# ---------------------------
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def build_zip(outputs: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in outputs.items():
            z.writestr(name, content)
    return buf.getvalue()


def safe_list(cols) -> list[str]:
    return list(cols) if cols is not None else []


def parse_list(s: str) -> list[str]:
    # keep empty string token if user includes it
    items = [x.strip() for x in s.split(",")]
    # Remove duplicates but preserve order
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def parse_optional_float(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


# ---------------------------
# Upload
# ---------------------------
uploaded = st.file_uploader("Upload CSV", type=["csv"])
if not uploaded:
    st.info("Upload a CSV to begin.")
    st.stop()

df = pd.read_csv(uploaded)
cols = safe_list(df.columns)

st.subheader("Preview")
st.dataframe(df.head(20), use_container_width=True)

st.subheader("Dataset profile")
profile_df = profile_dataset(df)
st.dataframe(profile_df, use_container_width=True, height=260)

# ---------------------------
# Config UI
# ---------------------------
st.subheader("Configuration")

c1, c2, c3 = st.columns(3)
with c1:
    entity_id = st.selectbox("Entity ID field (recommended)", options=["(none)"] + cols, index=0)
with c2:
    date_field = st.selectbox("Date field (required for drift)", options=["(none)"] + cols, index=0)
with c3:
    required_fields = st.multiselect("Required fields (completeness)", options=cols, default=[])

st.markdown("### Missing value standardization (NA / NO / UNKNOWN)")
na_values = st.text_input("NA values (comma-separated)", value=", ,N/A,NA,na,n/a")
no_values = st.text_input("NO values (comma-separated)", value="NO,No,no,FALSE,False,false,0")
unknown_values = st.text_input("UNKNOWN values (comma-separated)", value="UNKNOWN,Unknown,unknown,Not sure,NOT_SURE")

st.markdown("### Duplicates")
dup_keys_default = []
if entity_id != "(none)":
    dup_keys_default.append(entity_id)
if date_field != "(none)" and date_field not in dup_keys_default:
    dup_keys_default.append(date_field)

dup_keys = st.multiselect("Duplicate keys", options=cols, default=dup_keys_default)
dup_warn = st.number_input("Duplicates WARN threshold (rate)", min_value=0.0, max_value=1.0, value=0.02, step=0.01)
dup_fail = st.number_input("Duplicates FAIL threshold (rate) — optional", min_value=0.0, max_value=1.0, value=0.10, step=0.01)

st.markdown("### Consistency rules (simple when/then)")
st.caption("Define rules like: IF field == value THEN required fields must be present; or THEN another field must equal a value.")

if "rules" not in st.session_state:
    st.session_state.rules = []

add_rule = st.button("➕ Add consistency rule")
if add_rule:
    st.session_state.rules.append({
        "name": f"Rule{len(st.session_state.rules)+1}",
        "when_field": cols[0] if cols else "",
        "when_equals": "",
        "then_required": [],
        "then_equals_field": "",
        "then_equals_value": "",
    })

for i, r in enumerate(st.session_state.rules):
    with st.expander(f"Rule {i+1}: {r['name']}", expanded=True):
        r["name"] = st.text_input("Rule name", value=r["name"], key=f"rname{i}")
        r["when_field"] = st.selectbox("WHEN field", options=cols, index=cols.index(r["when_field"]) if r["when_field"] in cols else 0, key=f"whenf{i}")
        r["when_equals"] = st.text_input("WHEN equals", value=r["when_equals"], key=f"whene{i}")

        r["then_required"] = st.multiselect("THEN required fields", options=cols, default=r["then_required"], key=f"thenreq{i}")

        st.markdown("Optional THEN equals constraint")
        r["then_equals_field"] = st.selectbox("Field", options=["(none)"] + cols, index=0, key=f"theneqf{i}")
        r["then_equals_value"] = st.text_input("Expected value", value=r["then_equals_value"], key=f"theneqv{i}")

        remove = st.button("Remove this rule", key=f"remove{i}")
        if remove:
            st.session_state.rules.pop(i)
            st.rerun()

st.markdown("### Drift")
drift_period = st.selectbox("Period", options=["monthly", "weekly"], index=0)
baseline_periods = st.number_input("Baseline periods", min_value=1, max_value=12, value=2, step=1)
warn_pct = st.number_input("WARN % change (absolute)", min_value=0.0, max_value=1.0, value=0.30, step=0.05)
fail_pct = st.number_input("FAIL % change (absolute)", min_value=0.0, max_value=1.0, value=0.50, step=0.05)

st.markdown("### Allowed values")
allowed_values_fields = st.multiselect("Fields with constrained values", options=cols, default=[])
allowed_values_rules = []
for field in allowed_values_fields:
    allowed_values_rules.append(
        {
            "field": field,
            "allowed": parse_list(
                st.text_input(
                    f"Allowed values for {field}",
                    value="",
                    key=f"allowed_{field}",
                )
            ),
            "allow_missing": st.checkbox(f"Allow missing values for {field}", value=True, key=f"allow_missing_{field}"),
        }
    )

st.markdown("### Date validity")
date_validity_fields = st.multiselect("Fields that should parse as dates", options=cols, default=[date_field] if date_field != "(none)" else [])

st.markdown("### Numeric ranges")
numeric_range_fields = st.multiselect("Fields with numeric range checks", options=cols, default=[])
numeric_range_rules = []
numeric_range_input_errors: list[str] = []
for field in numeric_range_fields:
    min_col, max_col, allow_missing_col = st.columns(3)
    with min_col:
        min_raw = st.text_input(f"Minimum for {field}", value="", key=f"min_{field}")
    with max_col:
        max_raw = st.text_input(f"Maximum for {field}", value="", key=f"max_{field}")
    with allow_missing_col:
        allow_missing = st.checkbox(f"Allow missing for {field}", value=True, key=f"numeric_allow_missing_{field}")
    numeric_range_rules.append(
        {
            "field": field,
            "min": parse_optional_float(min_raw),
            "max": parse_optional_float(max_raw),
            "allow_missing": allow_missing,
        }
    )
    if min_raw.strip() and parse_optional_float(min_raw) is None:
        numeric_range_input_errors.append(f"Minimum for {field} must be numeric.")
    if max_raw.strip() and parse_optional_float(max_raw) is None:
        numeric_range_input_errors.append(f"Maximum for {field} must be numeric.")

st.markdown("### Cross-field validation")
st.caption("Compare two fields in the same row, for example followup_date >= encounter_date.")
if "cross_field_rules" not in st.session_state:
    st.session_state.cross_field_rules = []

add_cross_rule = st.button("Add cross-field rule")
if add_cross_rule:
    st.session_state.cross_field_rules.append(
        {
            "name": f"CrossRule{len(st.session_state.cross_field_rules) + 1}",
            "left_field": cols[0] if cols else "",
            "operator": ">=",
            "right_field": cols[0] if cols else "",
            "compare_as": "date",
            "allow_missing": True,
        }
    )

for i, r in enumerate(st.session_state.cross_field_rules):
    with st.expander(f"Cross-field rule {i+1}: {r['name']}", expanded=True):
        r["name"] = st.text_input("Rule name", value=r["name"], key=f"cf_name_{i}")
        c1, c2, c3 = st.columns(3)
        with c1:
            r["left_field"] = st.selectbox("Left field", options=cols, index=cols.index(r["left_field"]) if r["left_field"] in cols else 0, key=f"cf_left_{i}")
        with c2:
            r["operator"] = st.selectbox("Operator", options=["<", "<=", ">", ">=", "==", "!="], index=["<", "<=", ">", ">=", "==", "!="].index(r["operator"]) if r["operator"] in ["<", "<=", ">", ">=", "==", "!="] else 3, key=f"cf_op_{i}")
        with c3:
            r["right_field"] = st.selectbox("Right field", options=cols, index=cols.index(r["right_field"]) if r["right_field"] in cols else 0, key=f"cf_right_{i}")
        c4, c5 = st.columns(2)
        with c4:
            r["compare_as"] = st.selectbox("Compare as", options=["date", "numeric", "string"], index=["date", "numeric", "string"].index(r["compare_as"]) if r["compare_as"] in ["date", "numeric", "string"] else 0, key=f"cf_type_{i}")
        with c5:
            r["allow_missing"] = st.checkbox("Allow missing values", value=r["allow_missing"], key=f"cf_missing_{i}")
        remove_cross = st.button("Remove cross-field rule", key=f"remove_cf_{i}")
        if remove_cross:
            st.session_state.cross_field_rules.pop(i)
            st.rerun()

st.markdown("---")

# ---------------------------
# Build config dict
# ---------------------------
def build_cfg() -> dict:
    rules = []
    for r in st.session_state.rules:
        rule = {
            "name": r["name"],
            "when": {"field": r["when_field"], "equals": r["when_equals"]},
        }
        if r["then_required"]:
            rule["then_required"] = r["then_required"]
        if r["then_equals_field"] and r["then_equals_field"] != "(none)":
            rule["then_equals"] = {r["then_equals_field"]: r["then_equals_value"]}
        rules.append(rule)

    cfg = {
        "standardization": {
            "id_fields": {"entity_id": entity_id} if entity_id != "(none)" else {},
            "date_field": date_field if date_field != "(none)" else None,
            "missing_labels": {
                "na_values": parse_list(na_values) + [None],
                "no_values": parse_list(no_values),
                "unknown_values": parse_list(unknown_values),
            },
        },
        "checks": {
            "completeness": {
                "required_fields": required_fields,
                "pass_threshold": 0.95,
                "warn_threshold": 0.85,
            },
            "duplicates": {
                "keys": dup_keys,
                # We treat pass_threshold as "allowed duplicate rate for PASS"
                "pass_threshold": 0.00,
                "warn_threshold": dup_warn,
                # optional fail threshold handled in UI scoring below if you want later
            },
            "consistency": {"rules": rules},
            "drift": {
                "date_field": date_field if date_field != "(none)" else None,
                "period": drift_period,
                "baseline_periods": int(baseline_periods),
                "warn_pct_change": float(warn_pct),
                "fail_pct_change": float(fail_pct),
            },
            "allowed_values": {
                "rules": [rule for rule in allowed_values_rules if rule["field"] and rule["allowed"]],
            },
            "date_validity": {
                "fields": date_validity_fields,
            },
            "numeric_ranges": {
                "rules": numeric_range_rules,
            },
            "cross_field": {
                "rules": st.session_state.cross_field_rules,
            },
        },
    }
    return cfg


cfg = build_cfg()
config_errors = validate_config(
    {
        "input": {"mode": "csv", "csv": {"file": "uploaded.csv"}},
        "checks": cfg["checks"],
    }
)
config_errors.extend(numeric_range_input_errors)
if config_errors:
    st.error("Configuration issues:\n- " + "\n- ".join(config_errors))

# ---------------------------
# Run
# ---------------------------
run = st.button("▶ Run checks", type="primary")

if not run or config_errors:
    st.stop()

st.subheader("Results")

# Apply standardization
df_std = apply_missing_labels(df, cfg.get("standardization", {}))

# Run checks
comp = run_completeness(df_std, cfg["checks"]["completeness"])
dups = run_duplicates(df_std, cfg["checks"]["duplicates"])
cons = run_consistency(df_std, cfg["checks"]["consistency"])
drift = run_drift(df_std, cfg["checks"]["drift"])
allowed = run_allowed_values(df_std, cfg["checks"]["allowed_values"])
date_validity = run_date_validity(df_std, cfg["checks"]["date_validity"])
numeric_ranges = run_numeric_ranges(df_std, cfg["checks"]["numeric_ranges"])
cross_field = run_cross_field(df_std, cfg["checks"]["cross_field"])

# Scorecard (minimal schema)
scorecard_rows = [
    {"check": comp.check, "status": comp.status, "notes": comp.notes},
    {"check": dups.check, "status": dups.status, "notes": dups.notes},
    {"check": cons.check, "status": cons.status, "notes": cons.notes},
    {"check": drift.check, "status": drift.status, "notes": drift.notes},
    {"check": allowed.check, "status": allowed.status, "notes": allowed.notes},
    {"check": date_validity.check, "status": date_validity.status, "notes": date_validity.notes},
    {"check": numeric_ranges.check, "status": numeric_ranges.status, "notes": numeric_ranges.notes},
    {"check": cross_field.check, "status": cross_field.status, "notes": cross_field.notes},
]

order = {"PASS": 0, "WARN": 1, "FAIL": 2}
worst = max(
    [
        comp.status,
        dups.status,
        cons.status,
        drift.status,
        allowed.status,
        date_validity.status,
        numeric_ranges.status,
        cross_field.status,
    ],
    key=lambda s: order.get(s, 2),
)
scorecard_rows.append({"check": "overall", "status": worst, "notes": "Worst-of check statuses"})
scorecard_df = pd.DataFrame(scorecard_rows)

# Combine issues
issues_list = []
for r in [comp.issues, dups.issues, cons.issues, drift.issues, allowed.issues, date_validity.issues, numeric_ranges.issues, cross_field.issues]:
    if isinstance(r, pd.DataFrame) and not r.empty:
        issues_list.append(r)

if issues_list:
    issues_all = ensure_issue_schema(pd.concat(issues_list, ignore_index=True))
else:
    issues_all = empty_issues()

# Fix list
if issues_all.empty:
    fix_list = pd.DataFrame(columns=["check", "severity", "field", "message", "count"])
else:
    fix_list = (
        issues_all.groupby(["check", "severity", "field", "message"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["count", "severity", "check", "field"], ascending=[False, True, True, True])
    )

# Display
a, b = st.columns([1, 2])
with a:
    st.markdown("### Scorecard")
    st.dataframe(scorecard_df, use_container_width=True)
with b:
    st.markdown("### Fix list (ranked)")
    st.dataframe(fix_list, use_container_width=True)

st.markdown("### Issues (record-level)")
st.dataframe(issues_all, use_container_width=True, height=420)

# Downloads
st.markdown("---")
st.subheader("Download outputs")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
outputs = {
    "quality_scorecard.csv": to_csv_bytes(scorecard_df),
    "fix_list.csv": to_csv_bytes(fix_list),
    "issues_all.csv": to_csv_bytes(issues_all),
    "dataset_profile.csv": to_csv_bytes(profile_df),
}

zip_bytes = build_zip(outputs)

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.download_button("Download scorecard.csv", data=outputs["quality_scorecard.csv"], file_name="quality_scorecard.csv")
with c2:
    st.download_button("Download fix_list.csv", data=outputs["fix_list.csv"], file_name="fix_list.csv")
with c3:
    st.download_button("Download issues_all.csv", data=outputs["issues_all.csv"], file_name="issues_all.csv")
with c4:
    st.download_button("Download dataset_profile.csv", data=outputs["dataset_profile.csv"], file_name="dataset_profile.csv")
with c5:
    st.download_button("Download outputs.zip", data=zip_bytes, file_name=f"impactproof_outputs_{timestamp}.zip")
