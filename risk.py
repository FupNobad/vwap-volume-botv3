from dataclasses import dataclass

@dataclass(frozen=True)
class TradePlan:
    side: str
    entry: float
    stop: float
    take_profit: float
    quantity: float
    risk_budget: float
    notional: float

def build_trade_plan(*, side: str, entry: float, atr: float, equity: float,
                     risk_fraction: float = 0.0025, stop_atr_multiple: float = 1.5,
                     take_profit_r: float = 2.0, max_leverage: float = 1.0) -> TradePlan:
    if side not in ("long", "short"):
        raise ValueError("side must be long or short")
    if min(entry, atr, equity, risk_fraction, stop_atr_multiple, take_profit_r, max_leverage) <= 0:
        raise ValueError("All numeric inputs must be positive")
    stop_distance = atr * stop_atr_multiple
    risk_budget = equity * risk_fraction
    qty_by_risk = risk_budget / stop_distance
    qty_by_notional = equity * max_leverage / entry
    qty = min(qty_by_risk, qty_by_notional)
    if qty <= 0:
        raise ValueError("Calculated quantity is not positive")
    if side == "long":
        stop, tp = entry - stop_distance, entry + stop_distance * take_profit_r
    else:
        stop, tp = entry + stop_distance, entry - stop_distance * take_profit_r
    if min(stop, tp) <= 0:
        raise ValueError("Stop or target price is invalid")
    return TradePlan(side, entry, stop, tp, qty, risk_budget, qty * entry)
