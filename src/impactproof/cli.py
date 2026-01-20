from __future__ import annotations

import argparse
from pathlib import Path
import csv

from impactproof.config import load_config

import pandas as pd
from impactproof.checks.completeness import run_completeness
from impactproof.checks.duplicates import run_duplicates
from impactproof.standardize.missing_labels import apply_missing_labels
from impactproof.checks.consistency import run_consistency
from impactproof.checks.drift import run_drift


def write_fix_list(issues_df, output_file):
    """
    Create a grouped fix list from issues_all:
    Groups by (check, field, message), counts affected records.
    """
    import pandas as pd

    if issues_df is None or issues_df.empty:
        pd.DataFrame(columns=["check", "field", "message", "count"]).to_csv(output_file, index=False)
        return

    df = issues_df.copy()

    # Normalize missing fields
    if "field" not in df.columns:
        df["field"] = ""
    if "message" not in df.columns:
        df["message"] = ""

    fix = (
        df.groupby(["check", "field", "message"], dropna=False)
          .size()
          .reset_index(name="count")
          .sort_values(["count", "check", "field"], ascending=[False, True, True])
    )

    fix.to_csv(output_file, index=False)


def cmd_run(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    output_dir = cfg.output_path
    output_dir.mkdir(parents=True, exist_ok=True)

    print("ImpactProof run started")
    print(f"Loaded config: {args.config}")

    # Load CSV
    csv_file = cfg.input_csv_file
    print(f"Reading CSV: {csv_file}")
    df = pd.read_csv(csv_file)

    # Standardize missing labels (NA/NO/UNKNOWN) before checks
    df = apply_missing_labels(df, cfg.standardization_cfg)

    # Run Checks
    comp = run_completeness(df, cfg.completeness_cfg)
    dups = run_duplicates(df, cfg.duplicates_cfg)
    cons = run_consistency(df, cfg.consistency_cfg)
    drift = run_drift(df, cfg.drift_cfg)

    # Write scorecard (one row per check + overall)
    scorecard_file = output_dir / "quality_scorecard.csv"
    rows = [
        {"check": comp.check, "status": comp.status, "notes": comp.notes},
        {"check": dups.check, "status": dups.status, "notes": dups.notes},
        {"check": cons.check, "status": cons.status, "notes": cons.notes},
        {"check": drift.check, "status": drift.status, "notes": drift.notes},
    ]

    # simple overall status (worst-of)
    order = {"PASS": 0, "WARN": 1, "FAIL": 2}
    worst = max([comp.status, dups.status, cons.status, drift.status], key=lambda s: order.get(s, 2))
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

    if all_issues:
        issues_combined = pd.concat(all_issues, ignore_index=True)
        issues_combined.to_csv(issues_file, index=False)
    else:
        issues_combined = pd.DataFrame(columns=["check", "record_index", "field", "message", "suggested_fix"])
        issues_combined.to_csv(issues_file, index=False)

    fix_list_file = output_dir / "fix_list.csv"
    write_fix_list(issues_combined, fix_list_file)
    print(f"Wrote: {fix_list_file}")

    print(f"Wrote: {scorecard_file}")
    print(f"Wrote: {issues_file}")
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