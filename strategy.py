from dataclasses import dataclass
from typing import Optional
import pandas as pd
from .indicators import add_signals

@dataclass(frozen=True)
class Signal:
    symbol: str
    candle_time: pd.Timestamp
    side: str  # "long" or "short"
    signal_close: float
    atr: float
    volume: float
    average_volume: float
    daily_vwap: float
    weekly_vwap: float

def latest_signal(symbol: str, candles: pd.DataFrame, *, volume_multiple: float = 3.0,
                  volume_lookback: int = 168, atr_period: int = 14) -> Optional[Signal]:
    """Input must contain completed candles only; returns at most one signal."""
    data = add_signals(candles, volume_multiple, volume_lookback, atr_period)
    if data.empty:
        return None
    row = data.iloc[-1]
    required = ["avg_volume_168", "atr", "daily_vwap", "weekly_vwap"]
    if any(pd.isna(row[k]) for k in required):
        return None
    side = "long" if bool(row["long_signal"]) else ("short" if bool(row["short_signal"]) else None)
    if side is None:
        return None
    return Signal(
        symbol=symbol,
        candle_time=row["timestamp"],
        side=side,
        signal_close=float(row["close"]),
        atr=float(row["atr"]),
        volume=float(row["volume"]),
        average_volume=float(row["avg_volume_168"]),
        daily_vwap=float(row["daily_vwap"]),
        weekly_vwap=float(row["weekly_vwap"]),
    )
