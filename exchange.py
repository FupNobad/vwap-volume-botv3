import ccxt
import pandas as pd

def make_exchange(sandbox: bool = False):
    ex = ccxt.binanceusdm({"enableRateLimit": True, "timeout": 20000})
    if sandbox:
        # Must be called before other exchange calls. Paper mode itself uses public data only.
        ex.set_sandbox_mode(True)
    return ex

def fetch_history(symbol: str, timeframe: str, days: int, out: str, sandbox: bool = False):
    ex = make_exchange(sandbox=sandbox)
    ex.load_markets()
    since = ex.milliseconds() - days * 24 * 60 * 60 * 1000
    rows = []
    while since < ex.milliseconds():
        batch = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
        if not batch:
            break
        rows.extend(batch)
        next_since = batch[-1][0] + 1
        if next_since <= since:
            break
        since = next_since
        if len(batch) < 2:
            break
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    if df.empty:
        raise RuntimeError("No candles returned; check symbol, timeframe, connectivity, and exchange availability")
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    # Exclude current unfinished candle.
    interval_ms = ex.parse_timeframe(timeframe) * 1000
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(milliseconds=interval_ms)
    df = df[df["timestamp"] <= cutoff]
    from pathlib import Path
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return len(df)
