from __future__ import annotations

import argparse
from pathlib import Path
import csv

from impactproof.config import load_config

import pandas as pd
from impactproof.checks.completeness import run_completeness

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

    # Run Completeness
    comp = run_completeness(df, cfg.completeness_cfg)

    # Write scorecard
    scorecard_file = output_dir / "quality_scorecard.csv"
    with scorecard_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["check", "status", "notes"])
        writer.writeheader()
        writer.writerow({"check": comp.check, "status": comp.status, "notes": comp.notes})

    # Write issues
    issues_file = output_dir / "issues_all.csv"
    comp.issues.to_csv(issues_file, index=False)

    print(f"Wrote: {scorecard_file}")
    print(f"Wrote: {issues_file}")
    print("ImpactProof run finished")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="impactproof")
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run ImpactProof with a config file")
    run_p.add_argument("--config", required=True, help="Path to impactproof.yaml")
    run_p.set_defaults(func=cmd_run)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())