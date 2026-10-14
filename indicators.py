import numpy as np
import pandas as pd

REQUIRED = {"timestamp", "open", "high", "low", "close", "volume"}

def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")
    out = df.copy()
    # Do not silently interpret timezone-naive timestamps as UTC: callers must
    # explicitly identify the time zone to prevent session-boundary mistakes.
    parsed = pd.to_datetime(out["timestamp"], errors="raise")
    if out.empty:
        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
        for col in ("open", "high", "low", "close", "volume"):
            out[col] = pd.to_numeric(out[col], errors="raise")
        return out
    if getattr(parsed.dt, "tz", None) is None:
        raise ValueError("Timestamps must be timezone-aware; normalize to UTC upstream")
    out["timestamp"] = parsed.dt.tz_convert("UTC")
    out = out.sort_values("timestamp").reset_index(drop=True)
    if out["timestamp"].duplicated().any():
        raise ValueError("Duplicate candle timestamps are not allowed")
    for col in ("open", "high", "low", "close", "volume"):
        out[col] = pd.to_numeric(out[col], errors="raise")
    if out[list(("open", "high", "low", "close", "volume"))].isna().any().any():
        raise ValueError("OHLCV values cannot be null")
    if not (out[["open", "high", "low", "close"]] > 0).all().all():
        raise ValueError("OHLC prices must be positive")
    if (out["volume"] < 0).any():
        raise ValueError("Volume cannot be negative")
    invalid_range = (
        (out["high"] < out[["open", "close", "low"]].max(axis=1))
        | (out["low"] > out[["open", "close", "high"]].min(axis=1))
    )
    if invalid_range.any():
        raise ValueError("Invalid OHLC candle: high/low inconsistent with open/close")
    return out

def add_indicators(df: pd.DataFrame, volume_lookback: int = 168, atr_period: int = 14) -> pd.DataFrame:
    """Indicators use only current/past candles. Input candles should be completed."""
    out = normalize_ohlcv(df)
    ts = out["timestamp"]
    out["typical_price"] = (out["high"] + out["low"] + out["close"]) / 3.0
    out["utc_day"] = ts.dt.floor("D")
    # Monday 00:00 UTC anchor
    out["utc_week"] = (ts - pd.to_timedelta(ts.dt.weekday, unit="D")).dt.floor("D")

    weighted = out["typical_price"] * out["volume"]
    out["_weighted"] = weighted
    out["_volume"] = out["volume"]
    out["daily_vwap"] = (
        out.groupby("utc_day")["_weighted"].cumsum()
        / out.groupby("utc_day")["_volume"].cumsum().replace(0, np.nan)
    )
    out["weekly_vwap"] = (
        out.groupby("utc_week")["_weighted"].cumsum()
        / out.groupby("utc_week")["_volume"].cumsum().replace(0, np.nan)
    )
    # Shift first: current candle is excluded from the preceding 168-candle volume baseline.
    out["avg_volume_168"] = out["volume"].shift(1).rolling(volume_lookback, min_periods=volume_lookback).mean()

    prev_close = out["close"].shift(1)
    tr = pd.concat([
        out["high"] - out["low"],
        (out["high"] - prev_close).abs(),
        (out["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    # Wilder ATR (RMA): alpha=1/n, seeded by the first n-period simple mean.
    atr = pd.Series(index=out.index, dtype="float64")
    if len(tr) >= atr_period:
        atr.iloc[atr_period - 1] = tr.iloc[:atr_period].mean()
        for j in range(atr_period, len(tr)):
            atr.iloc[j] = (atr.iloc[j - 1] * (atr_period - 1) + tr.iloc[j]) / atr_period
    out["atr"] = atr
    out["volume_spike"] = out["volume"] >= 3.0 * out["avg_volume_168"]
    out["long_signal"] = (
        out["volume_spike"] & (out["close"] > out["daily_vwap"])
        & (out["close"] > out["weekly_vwap"])
    )
    out["short_signal"] = (
        out["volume_spike"] & (out["close"] < out["daily_vwap"])
        & (out["close"] < out["weekly_vwap"])
    )
    return out.drop(columns=["_weighted", "_volume"])

def add_signals(df: pd.DataFrame, volume_multiple: float = 3.0,
                volume_lookback: int = 168, atr_period: int = 14) -> pd.DataFrame:
    out = add_indicators(df, volume_lookback, atr_period)
    out["volume_spike"] = out["volume"] >= volume_multiple * out["avg_volume_168"]
    out["long_signal"] = (
        out["volume_spike"] & (out["close"] > out["daily_vwap"])
        & (out["close"] > out["weekly_vwap"])
    )
    out["short_signal"] = (
        out["volume_spike"] & (out["close"] < out["daily_vwap"])
        & (out["close"] < out["weekly_vwap"])
    )
    return out
