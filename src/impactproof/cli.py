from __future__ import annotations

import argparse
from pathlib import Path
import csv

from impactproof.config import load_config
from impactproof.profiling import profile_dataset
from impactproof.validation import validate_config
from impactproof.issues import empty_issues, ensure_issue_schema

import pandas as pd
from impactproof.checks.completeness import run_completeness
from impactproof.checks.duplicates import run_duplicates
from impactproof.standardize.missing_labels import apply_missing_labels
from impactproof.checks.consistency import run_consistency
from impactproof.checks.drift import run_drift
from impactproof.checks.allowed_values import run_allowed_values
from impactproof.checks.date_validity import run_date_validity
from impactproof.checks.numeric_ranges import run_numeric_ranges
from impactproof.checks.cross_field import run_cross_field


def write_fix_list(issues_df, output_file):
    """
    Create a grouped fix list from issues_all:
    Groups by (check, field, message), counts affected records.
    """
    import pandas as pd

    if issues_df is None or issues_df.empty:
        pd.DataFrame(columns=["check", "severity", "field", "message", "count"]).to_csv(output_file, index=False)
        return

    df = ensure_issue_schema(issues_df)

    # Normalize missing fields
    if "field" not in df.columns:
        df["field"] = ""
    if "message" not in df.columns:
        df["message"] = ""
    if "severity" not in df.columns:
        df["severity"] = "INFO"

    fix = (
        df.groupby(["check", "severity", "field", "message"], dropna=False)
          .size()
          .reset_index(name="count")
          .sort_values(["count", "severity", "check", "field"], ascending=[False, True, True, True])
    )

    fix.to_csv(output_file, index=False)


def cmd_run(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    config_errors = validate_config(cfg.raw)
    if config_errors:
        raise ValueError("Invalid configuration:\n- " + "\n- ".join(config_errors))

    output_dir = cfg.output_path
    output_dir.mkdir(parents=True, exist_ok=True)

    print("ImpactProof run started")
    print(f"Loaded config: {args.config}")

    # Load CSV
    csv_file = cfg.input_csv_file
    print(f"Reading CSV: {csv_file}")
    df = pd.read_csv(csv_file)
    profile_dataset(df).to_csv(output_dir / "dataset_profile.csv", index=False)

    # Standardize missing labels (NA/NO/UNKNOWN) before checks
    df = apply_missing_labels(df, cfg.standardization_cfg)

    # Run Checks
    comp = run_completeness(df, cfg.completeness_cfg)
    dups = run_duplicates(df, cfg.duplicates_cfg)
    cons = run_consistency(df, cfg.consistency_cfg)
    drift = run_drift(df, cfg.drift_cfg)
    allowed = run_allowed_values(df, cfg.allowed_values_cfg)
    date_validity = run_date_validity(df, cfg.date_validity_cfg)
    numeric_ranges = run_numeric_ranges(df, cfg.numeric_ranges_cfg)
    cross_field = run_cross_field(df, cfg.cross_field_cfg)

    # Write scorecard (one row per check + overall)
    scorecard_file = output_dir / "quality_scorecard.csv"
    rows = [
        {"check": comp.check, "status": comp.status, "notes": comp.notes},
        {"check": dups.check, "status": dups.status, "notes": dups.notes},
        {"check": cons.check, "status": cons.status, "notes": cons.notes},
        {"check": drift.check, "status": drift.status, "notes": drift.notes},
        {"check": allowed.check, "status": allowed.status, "notes": allowed.notes},
        {"check": date_validity.check, "status": date_validity.status, "notes": date_validity.notes},
        {"check": numeric_ranges.check, "status": numeric_ranges.status, "notes": numeric_ranges.notes},
        {"check": cross_field.check, "status": cross_field.status, "notes": cross_field.notes},
    ]

    # simple overall status (worst-of)
    order = {"PASS": 0, "WARN": 1, "FAIL": 2}
    statuses = [
        comp.status,
        dups.status,
        cons.status,
        drift.status,
        allowed.status,
        date_validity.status,
        numeric_ranges.status,
        cross_field.status,
    ]
    worst = max(statuses, key=lambda s: order.get(s, 2))
    rows.append({"check": "overall", "status": worst, "notes": "Worst-of check statuses"})

    with scorecard_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["check", "status", "notes"])
        writer.writeheader()
        writer.writerows(rows)

    # Combine issues
    issues_file = output_dir / "issues_all.csv"
    all_issues = []
    if not comp.issues.empty:
        all_issues.append(comp.issues)
    if not dups.issues.empty:
        all_issues.append(dups.issues)
    if not cons.issues.empty:
        all_issues.append(cons.issues)
    if not drift.issues.empty:
        all_issues.append(drift.issues)
    if not allowed.issues.empty:
        all_issues.append(allowed.issues)
    if not date_validity.issues.empty:
        all_issues.append(date_validity.issues)
    if not numeric_ranges.issues.empty:
        all_issues.append(numeric_ranges.issues)
    if not cross_field.issues.empty:
        all_issues.append(cross_field.issues)

    if all_issues:
        issues_combined = ensure_issue_schema(pd.concat(all_issues, ignore_index=True))
        issues_combined.to_csv(issues_file, index=False)
    else:
        issues_combined = empty_issues()
        issues_combined.to_csv(issues_file, index=False)

    fix_list_file = output_dir / "fix_list.csv"
    write_fix_list(issues_combined, fix_list_file)
    print(f"Wrote: {fix_list_file}")

    print(f"Wrote: {scorecard_file}")
    print(f"Wrote: {issues_file}")
    print(f"Wrote: {output_dir / 'dataset_profile.csv'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="impactproof")
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run ImpactProof with a config file")
    
    run_p.add_argument(
    "--config",
    default="impactproof.yaml",
    help="Path to config file (default: impactproof.yaml)",)
    run_p.set_defaults(func=cmd_run)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
