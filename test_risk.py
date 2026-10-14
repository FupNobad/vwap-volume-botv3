import pytest
from vwapbot.risk import build_trade_plan

def test_long_stop_and_target():
    p = build_trade_plan(side="long", entry=100, atr=2, equity=1000,
                         risk_fraction=.01, stop_atr_multiple=1.5, take_profit_r=2,
                         max_leverage=1)
    assert p.stop == 97
    assert p.take_profit == 106
    assert p.notional <= 1000

def test_short_stop_and_target():
    p = build_trade_plan(side="short", entry=100, atr=2, equity=1000,
                         risk_fraction=.01, stop_atr_multiple=1.5, take_profit_r=2,
                         max_leverage=1)
    assert p.stop == 103
    assert p.take_profit == 94

def test_invalid_side_raises():
    with pytest.raises(ValueError):
        build_trade_plan(side="flat", entry=100, atr=2, equity=1000)
