import pandas as pd
import pytest
from vwapbot.data_quality import closed_candles_only, find_hourly_gaps, has_complete_lookback
from vwapbot.indicators import normalize_ohlcv

def test_closed_candles_only_excludes_forming_candle():
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(["2025-01-01T00:00:00Z", "2025-01-01T01:00:00Z"]),
        "close_time": pd.to_datetime(["2025-01-01T00:59:59Z", "2025-01-01T01:59:59Z"]),
        "close": [100, 200],
    })
    out = closed_candles_only(df, server_time="2025-01-01T01:30:00Z")
    assert out["close"].tolist() == [100]

def test_hourly_gap_detection():
    ts = pd.to_datetime(["2025-01-01T00:00:00Z", "2025-01-01T02:00:00Z"])
    assert find_hourly_gaps(ts) == [pd.Timestamp("2025-01-01T01:00:00Z")]

def test_naive_timestamps_rejected_by_normalizer():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=2, freq="h"),
        "open": [100, 101], "high": [102, 103], "low": [99, 100],
        "close": [101, 102], "volume": [10, 11],
    })
    with pytest.raises(ValueError, match="timezone-aware"):
        normalize_ohlcv(df)

def test_complete_lookback_requires_exact_hours():
    ts = pd.date_range("2025-01-01T00:00:00Z", periods=169, freq="h")
    assert has_complete_lookback(ts, end_time=ts[-1], hours=168)
    assert not has_complete_lookback(ts.delete(10), end_time=ts[-1], hours=168)
