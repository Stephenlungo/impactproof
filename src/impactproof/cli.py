from __future__ import annotations

import argparse
from pathlib import Path
import csv

from impactproof.config import load_config


def write_dummy_scorecard(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "quality_scorecard.csv"

    rows = [
        {"check": "completeness", "status": "PASS", "notes": "dummy"},
        {"check": "duplicates", "status": "PASS", "notes": "dummy"},
        {"check": "overall", "status": "PASS", "notes": "Session 2 skeleton run"},
    ]

    with out_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["check", "status", "notes"])
        writer.writeheader()
        writer.writerows(rows)

    return out_file


def cmd_run(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    output_dir = cfg.output_path

    print("ImpactProof run started")
    print(f"Loaded config: {args.config}")
    print(f"Output path: {output_dir}")

    out_file = write_dummy_scorecard(output_dir)
    print(f"Wrote: {out_file}")

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