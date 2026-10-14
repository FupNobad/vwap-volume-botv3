import pandas as pd
from vwapbot.backtest import run_backtest

def test_empty_backtest_returns_starting_equity():
    df = pd.DataFrame(columns=["timestamp","open","high","low","close","volume"])
    result = run_backtest(df, "BTC/USDT:USDT")
    assert result.ending_equity == result.starting_equity
    assert result.trades == 0
