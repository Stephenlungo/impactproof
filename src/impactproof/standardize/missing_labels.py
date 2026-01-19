from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd


def _to_set(values: List[Any]) -> set:
    # normalize strings, keep None as None
    out = set()
    for v in values:
        if v is None:
            out.add(None)
        elif isinstance(v, str):
            out.add(v.strip())
        else:
            out.add(v)
    return out


def apply_missing_labels(df: pd.DataFrame, cfg: Dict[str, Any]) -> pd.DataFrame:
    """
    Standardize missing-like values into explicit labels:
      - NA
      - NO
      - UNKNOWN

    Notes:
    - We do NOT convert everything to strings.
    - We only operate on object/string columns by default to avoid breaking numeric fields.
    """
    ml = cfg.get("missing_labels", {}) if cfg else {}
    na_values = _to_set(ml.get("na_values", []))
    no_values = _to_set(ml.get("no_values", []))
    unknown_values = _to_set(ml.get("unknown_values", []))

    df2 = df.copy()

    # Only clean object columns (safe for MVP)
    obj_cols = [c for c in df2.columns if df2[c].dtype == "object"]

    for col in obj_cols:
        s = df2[col]

        # Normalize whitespace-only to empty string
        s = s.apply(lambda x: x.strip() if isinstance(x, str) else x)

        # Apply mappings in a stable order
        # 1) UNKNOWN
        s = s.apply(lambda x: "UNKNOWN" if (x in unknown_values) else x)
        # 2) NO
        s = s.apply(lambda x: "NO" if (x in no_values) else x)
        # 3) NA (includes blanks/None if configured)
        s = s.apply(lambda x: "NA" if (x in na_values) else x)

        df2[col] = s

    return df2