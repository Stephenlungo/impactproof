from __future__ import annotations

import pandas as pd


def profile_dataset(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    total_rows = len(df)

    for col in df.columns:
        series = df[col]
        missing_count = int(series.isna().sum())
        non_null = series.dropna()
        sample_values = ", ".join(str(v) for v in non_null.astype(str).head(3).tolist())

        rows.append(
            {
                "field": col,
                "dtype": str(series.dtype),
                "non_null_count": int(series.notna().sum()),
                "missing_count": missing_count,
                "missing_rate": (missing_count / total_rows) if total_rows else 0.0,
                "unique_count": int(non_null.nunique(dropna=True)),
                "sample_values": sample_values,
            }
        )

    return pd.DataFrame(rows)
