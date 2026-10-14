"""Data quality checks for hourly OHLCV. No live trading functionality."""
from __future__ import annotations
import pandas as pd

HOUR = pd.Timedelta(hours=1)

def closed_candles_only(df: pd.DataFrame, *, server_time) -> pd.DataFrame:
    """Keep only candles whose close time is strictly earlier than server_time.

    Expected columns: timestamp (candle open time), close_time.
    Timestamps must be timezone-aware. This utility cannot infer closure
    when close_time is missing; it intentionally fails closed.
    """
    if "timestamp" not in df.columns or "close_time" not in df.columns:
        raise ValueError("Expected timestamp and close_time columns")
    out = df.copy()
    ts = pd.to_datetime(out["timestamp"], errors="raise")
    ct = pd.to_datetime(out["close_time"], errors="raise")
    now = pd.Timestamp(server_time)
    if ts.dt.tz is None or ct.dt.tz is None or now.tzinfo is None:
        raise ValueError("All timestamps must be timezone-aware")
    out["timestamp"] = ts.dt.tz_convert("UTC")
    out["close_time"] = ct.dt.tz_convert("UTC")
    now = now.tz_convert("UTC")
    return out.loc[out["close_time"] < now].drop(columns=["close_time"]).reset_index(drop=True)

def find_hourly_gaps(timestamps) -> list[pd.Timestamp]:
    """Return expected hourly candle-open timestamps missing between first/last."""
    ts = pd.DatetimeIndex(pd.to_datetime(timestamps, errors="raise"))
    if ts.tz is None:
        raise ValueError("Timestamps must be timezone-aware")
    ts = ts.tz_convert("UTC").sort_values().unique()
    if len(ts) < 2:
        return []
    expected = pd.date_range(ts[0], ts[-1], freq="h", tz="UTC")
    present = set(ts)
    return [t for t in expected if t not in present]

def has_complete_lookback(timestamps, *, end_time, hours: int = 168) -> bool:
    """True only when the exact consecutive hourly window ending at end_time exists."""
    if hours <= 0:
        raise ValueError("hours must be positive")
    ts = pd.DatetimeIndex(pd.to_datetime(timestamps, errors="raise"))
    end = pd.Timestamp(end_time)
    if ts.tz is None or end.tzinfo is None:
        raise ValueError("Timestamps must be timezone-aware")
    ts = ts.tz_convert("UTC")
    end = end.tz_convert("UTC")
    expected = pd.date_range(end=end - HOUR, periods=hours, freq="h", tz="UTC")
    return set(expected).issubset(set(ts))
