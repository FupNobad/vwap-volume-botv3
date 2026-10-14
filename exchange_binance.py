import ccxt
import pandas as pd

class BinancePublicData:
    """Public OHLCV/ticker adapter. Intentionally has no order-submission methods."""
    def __init__(self):
        self.exchange = ccxt.binanceusdm({"enableRateLimit": True})

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 1000) -> pd.DataFrame:
        rows = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return self._to_frame(rows, timeframe)

    def fetch_history(self, symbol: str, timeframe: str = "1h", days: int = 365) -> pd.DataFrame:
        """Paginate public candles from approximately `days` ago up to now."""
        if days <= 0:
            raise ValueError("days must be positive")
        duration_ms = {"1m":60_000, "5m":300_000, "15m":900_000, "1h":3_600_000,
                       "4h":14_400_000, "1d":86_400_000}.get(timeframe)
        if duration_ms is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        now_ms = self.exchange.milliseconds()
        since = now_ms - days * 24 * 60 * 60 * 1000
        rows_all = []
        last_seen = None
        while since < now_ms:
            batch = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
            if not batch:
                break
            for row in batch:
                if last_seen is None or row[0] > last_seen:
                    rows_all.append(row)
                    last_seen = row[0]
            next_since = batch[-1][0] + duration_ms
            if next_since <= since:
                break
            since = next_since
            if len(batch) < 2:
                break
        return self._to_frame(rows_all, timeframe)

    def _to_frame(self, rows, timeframe):
        df = pd.DataFrame(rows, columns=["timestamp_ms","open","high","low","close","volume"])
        if df.empty:
            return pd.DataFrame(columns=["timestamp","open","high","low","close","volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True)
        df = df.drop(columns=["timestamp_ms"])
        return self.drop_incomplete_last(df, timeframe)

    def ticker_price(self, symbol: str) -> float:
        return float(self.exchange.fetch_ticker(symbol)["last"])

    @staticmethod
    def drop_incomplete_last(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        if df.empty:
            return df
        seconds = {"1m":60, "5m":300, "15m":900, "1h":3600, "4h":14400, "1d":86400}
        duration = seconds.get(timeframe)
        if duration is None:
            raise ValueError(f"Unsupported timeframe for completeness check: {timeframe}")
        now = pd.Timestamp.now(tz="UTC")
        last_open = df.iloc[-1]["timestamp"]
        if last_open + pd.Timedelta(seconds=duration) > now:
            return df.iloc[:-1].reset_index(drop=True)
        return df.reset_index(drop=True)
