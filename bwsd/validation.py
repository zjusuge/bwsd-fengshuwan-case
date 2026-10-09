"""Reject ambiguous dates, invalid units, and malformed evidence flags."""

import numpy as np
import pandas as pd

REQUIRED = [
    "Date",
    "Precipitation_mm",
    "Evapotranspiration_mm",
    "Water_level_m",
    "Runoff_mm",
]


def parse_boolean(values, n):
    if np.isscalar(values):
        values = [values] * n
    items = pd.Series(values).reset_index(drop=True)
    mapping = {
        "true": True,
        "false": False,
        "1": True,
        "0": False,
        "1.0": True,
        "0.0": False,
    }
    result = items.astype(str).str.lower().map(mapping)
    if len(items) != n or result.isna().any():
        raise ValueError(
            "Evidence flags must contain explicit true/false or 1/0 values"
        )
    return result.astype(bool)


def validate_daily_hydrology(frame):
    if any(c not in frame for c in REQUIRED):
        raise ValueError(
            "Missing required fields: "
            + ", ".join(c for c in REQUIRED if c not in frame)
        )
    df = frame.copy().reset_index(drop=True)
    if df.empty:
        raise ValueError("Daily input cannot be empty")
    df["Date"] = pd.to_datetime(df["Date"], errors="raise").dt.normalize()
    if df["Date"].dt.tz is not None:
        raise ValueError("Daily dates must be timezone-naive")
    if df["Date"].isna().any() or df["Date"].duplicated().any():
        raise ValueError("Dates must be valid and unique")
    if not df["Date"].is_monotonic_increasing:
        raise ValueError("Daily dates must be ordered chronologically")
    if not df["Date"].diff().dropna().eq(pd.Timedelta(days=1)).all():
        raise ValueError(
            "Daily dates must be contiguous; insert missing dates with explicit NaN fluxes"
        )
    for col in REQUIRED[1:]:
        df[col] = pd.to_numeric(df[col], errors="raise")
        values = df[col].to_numpy(dtype=float)
        if np.isinf(values).any() or np.any(values[np.isfinite(values)] < 0):
            raise ValueError(
                col + " must be non-negative and finite, or explicitly missing"
            )
    return df
