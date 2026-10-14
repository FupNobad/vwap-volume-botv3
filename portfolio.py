"""Conservative portfolio-level hourly backtester.

One global position across all symbols. This is a research engine, not a
tick-accurate simulator. Stops win when stop and target are both touched
in a candle. Funding is charged only from supplied actual funding events.
"""
from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from .indicators import add_signals
from .risk import build_trade_plan

@dataclass
class PortfolioResult:
    starting_equity: float
    ending_equity: float
    net_pnl: float
    trades: int
    wins: int
    max_drawdown_pct: float
    daily_loss_blocks: int
    simultaneous_signal_skips: int
    funding_pnl: float
    trades_detail: list

def _slip(price: float, side: str, bps: float, entry: bool) -> float:
    is_buy = (side == "long" and entry) or (side == "short" and not entry)
    return price * (1 + bps / 10000 if is_buy else 1 - bps / 10000)

def run_portfolio_backtest(data_by_symbol: dict[str, pd.DataFrame], *,
        funding: pd.DataFrame | None = None, starting_equity: float = 1000.0,
        volume_multiple: float = 3.0, volume_lookback: int = 168,
        atr_period: int = 14, risk_fraction: float = 0.0025,
        stop_atr_multiple: float = 1.5, take_profit_r: float = 2.0,
        max_leverage: float = 1.0, taker_fee_rate: float = 0.0005,
        slippage_bps: float = 5.0, daily_loss_limit: float = 0.01,
        symbol_priority: tuple[str, ...] | None = None) -> PortfolioResult:
    if not data_by_symbol:
        raise ValueError("data_by_symbol cannot be empty")
    if starting_equity <= 0 or not 0 < daily_loss_limit < 1:
        raise ValueError("Invalid equity or daily loss limit")
    symbols = list(data_by_symbol)
    priority = list(symbol_priority or sorted(symbols))
    priority += [s for s in sorted(symbols) if s not in priority]
    rank = {s:i for i,s in enumerate(priority)}
    prepared = {}
    for sym, frame in data_by_symbol.items():
        d = add_signals(frame, volume_multiple, volume_lookback, atr_period).set_index("timestamp")
        if d.index.has_duplicates:
            raise ValueError(f"{sym}: duplicate timestamps")
        # Refuse gaps instead of silently treating a row-count window as a time window.
        if len(d) > 1:
            expected = pd.date_range(d.index[0], d.index[-1], freq="h", tz="UTC")
            if not d.index.equals(expected):
                raise ValueError(f"{sym}: missing/non-hourly candles; repair data before backtest")
        prepared[sym] = d
    if funding is None:
        fund = pd.DataFrame(columns=["timestamp", "symbol", "rate"])
    else:
        if not {"timestamp","symbol","rate"}.issubset(funding.columns):
            raise ValueError("funding requires timestamp, symbol, rate columns")
        fund = funding.copy()
        fund["timestamp"] = pd.to_datetime(fund["timestamp"], utc=True, errors="raise")
        fund["rate"] = pd.to_numeric(fund["rate"], errors="raise")
        fund = fund.sort_values("timestamp")
    fund_at = {}
    for row in fund.itertuples(index=False):
        fund_at.setdefault(row.timestamp, []).append((row.symbol, float(row.rate)))

    timeline = sorted(set().union(*(set(d.index) for d in prepared.values())))
    equity = float(starting_equity)
    peak = equity
    max_dd = 0.0
    position = None
    trades = []
    day_start = {}
    daily_loss_blocks = 0
    simultaneous_skips = 0
    total_funding = 0.0

    for ts in timeline:
        day = ts.floor("D")
        day_start.setdefault(day, equity)
        # Apply funding at the event timestamp only if the matching position
        # was already open before the timestamp and has not exited earlier.
        if position is not None:
            for sym, rate in fund_at.get(ts, []):
                if sym == position["symbol"] and position["entry_time"] < ts:
                    # Positive rate means longs pay shorts (standard convention).
                    cashflow = -position["side_sign"] * position["entry"] * position["qty"] * rate
                    position["funding"] += cashflow
                    total_funding += cashflow

        # Manage the current position only when its market has a bar.
        if position is not None and ts in prepared[position["symbol"]].index:
            bar = prepared[position["symbol"]].loc[ts]
            side = position["side"]
            stop_hit = bar["low"] <= position["stop"] if side == "long" else bar["high"] >= position["stop"]
            tp_hit = bar["high"] >= position["tp"] if side == "long" else bar["low"] <= position["tp"]
            exit_raw, reason = None, None
            if side == "long" and bar["open"] <= position["stop"]:
                exit_raw, reason = float(bar["open"]), "stop_gap"
            elif side == "short" and bar["open"] >= position["stop"]:
                exit_raw, reason = float(bar["open"]), "stop_gap"
            elif stop_hit:
                exit_raw, reason = position["stop"], "stop"
            elif tp_hit:
                exit_raw, reason = position["tp"], "take_profit"
            if exit_raw is not None:
                exit_fill = _slip(float(exit_raw), side, slippage_bps, False)
                qty = position["qty"]
                gross = (exit_fill-position["entry"])*qty*position["side_sign"]
                exit_fee = abs(exit_fill*qty)*taker_fee_rate
                fees = position["entry_fee"] + exit_fee
                net = gross - fees + position["funding"]
                equity += net
                trades.append({**position, "exit_time":ts, "exit":exit_fill, "reason":reason,
                               "gross_pnl":gross, "fees":fees, "net_pnl":net})
                position = None
                peak = max(peak, equity)
                max_dd = max(max_dd, (peak-equity)/peak if peak else 0.0)

        # Daily limit blocks new risk after realized loss reaches threshold.
        if position is None and equity > 0:
            if equity <= day_start[day] * (1 - daily_loss_limit):
                daily_loss_blocks += 1
                continue
            candidates = []
            for sym, d in prepared.items():
                if ts not in d.index:
                    continue
                idx = d.index.get_loc(ts)
                if idx == 0:
                    continue
                prev = d.iloc[idx-1]
                if pd.isna(prev["atr"]):
                    continue
                side = "long" if bool(prev["long_signal"]) else ("short" if bool(prev["short_signal"]) else None)
                if side:
                    ratio = float(prev["volume"] / prev["avg_volume_168"]) if prev["avg_volume_168"] else 0
                    candidates.append((rank.get(sym, 999), -ratio, sym, side, prev))
            if candidates:
                candidates.sort(key=lambda x:(x[0],x[1],x[2]))
                if len(candidates) > 1:
                    simultaneous_skips += len(candidates)-1
                _, _, sym, side, prev = candidates[0]
                bar = prepared[sym].loc[ts]
                entry = _slip(float(bar["open"]), side, slippage_bps, True)
                plan = build_trade_plan(side=side, entry=entry, atr=float(prev["atr"]),
                    equity=equity, risk_fraction=risk_fraction, stop_atr_multiple=stop_atr_multiple,
                    take_profit_r=take_profit_r, max_leverage=max_leverage)
                entry_fee = abs(entry*plan.quantity)*taker_fee_rate
                position = {"symbol":sym, "side":side, "side_sign":1 if side=="long" else -1,
                    "entry_time":ts, "entry":entry, "stop":plan.stop, "tp":plan.take_profit,
                    "qty":plan.quantity, "entry_fee":entry_fee, "funding":0.0,
                    "risk_budget":plan.risk_budget}
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak-equity)/peak if peak else 0.0)

    # Mark-to-market/open-position liquidation is deliberately not fabricated:
    # an unfinished position is reported as open and not included in closed-trade PnL.
    pnl = equity - starting_equity
    return PortfolioResult(starting_equity, equity, pnl, len(trades),
        sum(1 for t in trades if t["net_pnl"] > 0), max_dd*100,
        daily_loss_blocks, simultaneous_skips, total_funding, trades)
