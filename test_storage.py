from vwapbot.storage import Store

def test_processed_candle_is_idempotent(tmp_path):
    s = Store(str(tmp_path / "state.sqlite"))
    assert s.mark_processed("BTC/USDT:USDT", 123)
    assert not s.mark_processed("BTC/USDT:USDT", 123)
    assert s.is_processed("BTC/USDT:USDT", 123)
