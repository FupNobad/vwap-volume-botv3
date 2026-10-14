import numpy as np
import pandas as pd
from vwapbot.indicators import add_signals

def frame(n=250):
    ts = pd.date_range("2025-01-01", periods=n, freq="h", tz="UTC")
    close = np.linspace(100, 110, n)
    return pd.DataFrame({
        "timestamp": ts, "open": close-0.2, "high": close+1,
        "low": close-1, "close": close, "volume": np.ones(n)*10
    })

def test_volume_baseline_excludes_current_candle():
    df = frame(200)
    df.loc[199, "volume"] = 1000
    out = add_signals(df, volume_multiple=3, volume_lookback=168, atr_period=14)
    assert out.loc[199, "avg_volume_168"] == 10
    assert bool(out.loc[199, "volume_spike"])

def test_vwap_is_inside_candle_price_range():
    out = add_signals(frame(200), volume_multiple=3, volume_lookback=168, atr_period=14)
    valid = out.dropna(subset=["daily_vwap", "weekly_vwap"])
    assert (valid["daily_vwap"] >= valid["low"] - 1e-9).all()
    assert (valid["daily_vwap"] <= valid["high"] + 1e-9).all()

def test_long_and_short_are_mutually_exclusive():
    out = add_signals(frame(200), volume_multiple=3, volume_lookback=168, atr_period=14)
    assert not (out["long_signal"] & out["short_signal"]).any()
