import numpy as np
import pandas as pd
import pytest
from vwapbot.portfolio import run_portfolio_backtest

def candles(n=240):
    ts = pd.date_range("2025-01-01", periods=n, freq="h", tz="UTC")
    close = np.linspace(100, 110, n)
    return pd.DataFrame({"timestamp":ts, "open":close-.1, "high":close+1,
        "low":close-1, "close":close, "volume":np.full(n, 10.0)})

def test_empty_signals_produce_no_trades():
    result = run_portfolio_backtest({"BTC/USDT:USDT":candles()})
    assert result.trades == 0
    assert result.ending_equity == result.starting_equity

def test_missing_hour_is_rejected():
    d = candles()
    d = d.drop(index=50).reset_index(drop=True)
    with pytest.raises(ValueError, match="missing/non-hourly"):
        run_portfolio_backtest({"BTC/USDT:USDT":d})

def test_funding_schema_is_validated():
    with pytest.raises(ValueError, match="funding requires"):
        run_portfolio_backtest({"BTC/USDT:USDT":candles()},
            funding=pd.DataFrame({"timestamp":[]}))
