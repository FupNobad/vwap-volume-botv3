from dataclasses import dataclass, asdict
import pandas as pd
from .indicators import add_signals
from .risk import build_trade_plan

@dataclass
class BacktestResult:
    symbol: str
    starting_equity: float
    ending_equity: float
    net_pnl: float
    trades: int
    wins: int
    max_drawdown_pct: float
    trades_detail: list

def _slipped(price: float, side: str, bps: float, is_entry: bool) -> float:
    # Adverse direction: buys pay more, sells receive less.
    buy = (side == "long" and is_entry) or (side == "short" and not is_entry)
    factor = 1 + bps / 10000 if buy else 1 - bps / 10000
    return price * factor

def run_backtest(df: pd.DataFrame, symbol: str, *, starting_equity: float = 1000.0,
                 volume_multiple: float = 3.0, volume_lookback: int = 168,
                 atr_period: int = 14, risk_fraction: float = 0.0025,
                 stop_atr_multiple: float = 1.5, take_profit_r: float = 2.0,
                 max_leverage: float = 1.0, taker_fee_rate: float = 0.0005,
                 slippage_bps: float = 5.0, funding_rate_per_interval: float = 0.0001,
                 funding_interval_hours: int = 8) -> BacktestResult:
    data = add_signals(df, volume_multiple, volume_lookback, atr_period).reset_index(drop=True)
    equity = starting_equity
    peak = equity
    max_dd = 0.0
    trades = []
    position = None
    daily_start = {}
    for i in range(1, len(data)):
        row = data.iloc[i]
        prev = data.iloc[i-1]
        ts = row["timestamp"]
        day = ts.floor("D")
        daily_start.setdefault(day, equity)

        # Manage open position with this bar's OHLC. Stop wins if both levels touched.
        if position is not None:
            side = position["side"]
            stop_hit = (row["low"] <= position["stop"]) if side == "long" else (row["high"] >= position["stop"])
            tp_hit = (row["high"] >= position["tp"]) if side == "long" else (row["low"] <= position["tp"])
            exit_price = None
            reason = None
            if side == "long" and row["open"] <= position["stop"]:
                exit_price, reason = row["open"], "stop_gap"
            elif side == "short" and row["open"] >= position["stop"]:
                exit_price, reason = row["open"], "stop_gap"
            elif stop_hit:
                exit_price, reason = position["stop"], "stop"
            elif tp_hit:
                exit_price, reason = position["tp"], "take_profit"
            if exit_price is not None:
                exit_fill = _slipped(float(exit_price), side, slippage_bps, False)
                qty = position["qty"]
                gross = (exit_fill-position["entry_fill"])*qty*(1 if side=="long" else -1)
                exit_fee = abs(exit_fill*qty)*taker_fee_rate
                # Approximate funding events crossed by holding period.
                elapsed_h = max(0.0, (ts-position["entry_time"]).total_seconds()/3600)
                funding_events = int(elapsed_h // funding_interval_hours)
                funding = -1 * (1 if side=="long" else -1) * position["entry"] * qty * funding_rate_per_interval * funding_events
                fees = position["entry_fee"] + exit_fee
                net = gross - fees + funding
                equity += net
                trades.append({**position, "exit_time": ts, "exit": exit_fill, "reason": reason,
                               "gross_pnl": gross, "fees": fees, "funding": funding, "net_pnl": net})
                position = None
                peak = max(peak, equity)
                max_dd = max(max_dd, (peak-equity)/peak if peak else 0.0)

        # Entry signal on previous completed candle; enter at this candle's open.
        if position is None and not pd.isna(prev["atr"]) and equity > 0:
            side = "long" if bool(prev["long_signal"]) else ("short" if bool(prev["short_signal"]) else None)
            if side:
                entry_raw = float(row["open"])
                entry_fill = _slipped(entry_raw, side, slippage_bps, True)
                plan = build_trade_plan(side=side, entry=entry_fill, atr=float(prev["atr"]),
                    equity=equity, risk_fraction=risk_fraction, stop_atr_multiple=stop_atr_multiple,
                    take_profit_r=take_profit_r, max_leverage=max_leverage)
                entry_fee = abs(entry_fill*plan.quantity)*taker_fee_rate
                position = {"symbol":symbol, "side":side, "entry_time":ts, "entry":entry_fill,
                            "entry_fill":entry_fill, "stop":plan.stop, "tp":plan.take_profit,
                            "qty":plan.quantity, "entry_fee":entry_fee}
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak-equity)/peak if peak else 0.0)

    pnl = equity-starting_equity
    return BacktestResult(symbol, starting_equity, equity, pnl, len(trades),
                          sum(1 for t in trades if t["net_pnl"] > 0), max_dd*100, trades)
