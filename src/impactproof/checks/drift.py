from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import pandas as pd


@dataclass
class DriftResult:
    check: str
    status: str  # PASS | WARN | FAIL
    latest_period: str
    baseline_avg: float
    latest_count: int
    pct_change: float
    notes: str
    issues: pd.DataFrame


def run_drift(df: pd.DataFrame, cfg: Dict[str, Any]) -> DriftResult:
    date_field = cfg.get("date_field")
    period = cfg.get("period", "monthly")
    baseline_n = int(cfg.get("baseline_periods", 2))
    warn_thr = float(cfg.get("warn_pct_change", 0.30))
    fail_thr = float(cfg.get("fail_pct_change", 0.50))

    if not date_field or date_field not in df.columns:
        return DriftResult(
            check="drift",
            status="WARN",
            latest_period="N/A",
            baseline_avg=0,
            latest_count=0,
            pct_change=0.0,
            notes=f"Date field '{date_field}' missing; drift skipped",
            issues=pd.DataFrame(),
        )

    # Parse dates safely
    dates = pd.to_datetime(df[date_field], errors="coerce")
    valid = dates.notna()
    df2 = df.loc[valid].copy()
    df2["_period"] = dates[valid].dt.to_period("M" if period == "monthly" else "W")

    counts = df2.groupby("_period").size().sort_index()

    if len(counts) <= baseline_n:
        return DriftResult(
            check="drift",
            status="PASS",
            latest_period=str(counts.index.max()),
            baseline_avg=float(counts.mean()),
            latest_count=int(counts.iloc[-1]),
            pct_change=0.0,
            notes="Not enough historical periods to evaluate drift",
            issues=pd.DataFrame(),
        )

    latest_period = counts.index[-1]
    latest_count = int(counts.iloc[-1])
    baseline = counts.iloc[-(baseline_n + 1):-1]
    baseline_avg = float(baseline.mean())

    if baseline_avg == 0:
        pct_change = 1.0
    else:
        pct_change = (latest_count - baseline_avg) / baseline_avg

    abs_change = abs(pct_change)

    if abs_change >= fail_thr:
        status = "FAIL"
    elif abs_change >= warn_thr:
        status = "WARN"
    else:
        status = "PASS"

    issues = pd.DataFrame([{
        "check": "drift",
        "record_index": None,
        "field": date_field,
        "message": (
            f"Volume drift detected for {latest_period}: "
            f"{pct_change:.1%} change vs baseline avg ({baseline_avg:.1f})"
        ),
        "suggested_fix": (
            "Verify reporting completeness, backlogs, or duplicate submissions "
            "for this period."
        ),
    }]) if status != "PASS" else pd.DataFrame()

    notes = (
        f"{latest_period}: {latest_count} records vs baseline avg "
        f"{baseline_avg:.1f} ({pct_change:.1%})"
    )

    return DriftResult(
        check="drift",
        status=status,
        latest_period=str(latest_period),
        baseline_avg=baseline_avg,
        latest_count=latest_count,
        pct_change=pct_change,
        notes=notes,
        issues=issues,
    )