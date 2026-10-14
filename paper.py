import json
import logging
import time
import pandas as pd
from .config import Config
from .exchange_binance import BinancePublicData
from .storage import Store
from .strategy import latest_signal
from .risk import build_trade_plan

log = logging.getLogger(__name__)

class PaperTrader:
    """Live market data, simulated positions only; no exchange orders are sent."""
    def __init__(self, config: Config):
        self.cfg = config
        self.data = BinancePublicData()
        self.store = Store(config.db_path)
        self.equity = float(self.store.get_state("paper_equity") or "1000")
        self.starting_equity = float(self.store.get_state("paper_starting_equity") or self.equity)
        self.store.set_state("paper_equity", str(self.equity))
        self.store.set_state("paper_starting_equity", str(self.starting_equity))

    def process_symbol_once(self, symbol: str):
        candles = self.data.fetch_ohlcv(symbol, self.cfg.timeframe, limit=max(300, self.cfg.volume_lookback_bars + 50))
        if len(candles) < self.cfg.volume_lookback_bars + self.cfg.atr_period + 5:
            log.warning("%s insufficient candles: %s", symbol, len(candles))
            return
        candle = candles.iloc[-1]
        candle_ms = int(candle["timestamp"].timestamp() * 1000)
        if self.store.is_processed(symbol, candle_ms):
            return
        signal = latest_signal(symbol, candles, volume_multiple=self.cfg.volume_multiple,
                               volume_lookback=self.cfg.volume_lookback_bars, atr_period=self.cfg.atr_period)
        # Mark every completed candle processed to prevent reprocessing after restart.
        self.store.mark_processed(symbol, candle_ms)
        if signal is None:
            log.info("%s %s: no signal", symbol, candle["timestamp"])
            return
        if self.store.open_trade():
            log.info("%s signal skipped: global position already open", symbol)
            return
        day_key = "daily_start_" + pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
        daily_start = float(self.store.get_state(day_key) or self.equity)
        self.store.set_state(day_key, str(daily_start))
        if self.equity <= daily_start * (1 - self.cfg.daily_loss_limit):
            log.warning("Daily loss limit reached; no new entries")
            return

        # Simulate market entry after signal detection, with adverse slippage.
        ticker = self.data.ticker_price(symbol)
        buy = signal.side == "long"
        entry = ticker * (1 + self.cfg.slippage_bps/10000 if buy else 1 - self.cfg.slippage_bps/10000)
        plan = build_trade_plan(side=signal.side, entry=entry, atr=signal.atr, equity=self.equity,
            risk_fraction=self.cfg.risk_fraction, stop_atr_multiple=self.cfg.stop_atr_multiple,
            take_profit_r=self.cfg.take_profit_r, max_leverage=self.cfg.max_leverage)
        trade_id = self.store.add_trade({
            "symbol":symbol, "side":signal.side, "entry_time":pd.Timestamp.now(tz="UTC").isoformat(),
            "entry":entry, "stop":plan.stop, "take_profit":plan.take_profit,
            "quantity":plan.quantity, "status":"open"
        })
        log.warning("PAPER trade opened id=%s symbol=%s side=%s entry=%.4f stop=%.4f tp=%.4f qty=%.8f",
                    trade_id, symbol, signal.side, entry, plan.stop, plan.take_profit, plan.quantity)

    def poll_open_position(self):
        trade = self.store.open_trade()
        if not trade:
            return
        ticker = self.data.ticker_price(trade["symbol"])
        side = trade["side"]
        stop_hit = ticker <= trade["stop"] if side == "long" else ticker >= trade["stop"]
        tp_hit = ticker >= trade["take_profit"] if side == "long" else ticker <= trade["take_profit"]
        if not (stop_hit or tp_hit):
            return
        # If both conditions appear possible in a price jump, stop gets priority.
        reason = "stop" if stop_hit else "take_profit"
        raw_exit = float(trade["stop"] if stop_hit else trade["take_profit"])
        exit_price = raw_exit * (1 - self.cfg.slippage_bps/10000 if side == "long" else 1 + self.cfg.slippage_bps/10000)
        qty = float(trade["quantity"])
        gross = (exit_price-float(trade["entry"]))*qty*(1 if side=="long" else -1)
        fees = (abs(float(trade["entry"])*qty)+abs(exit_price*qty))*self.cfg.taker_fee_rate
        net = gross - fees
        self.equity += net
        now = pd.Timestamp.now(tz="UTC")
        self.store.close_trade(trade["id"], exit_time=now.isoformat(), exit_price=exit_price,
            gross_pnl=gross, fees=fees, funding=0.0, net_pnl=net)
        self.store.set_state("paper_equity", str(self.equity))
        log.warning("PAPER trade closed id=%s reason=%s gross=%.4f fees=%.4f net=%.4f equity=%.2f",
                    trade["id"], reason, gross, fees, net, self.equity)

    def loop(self, poll_seconds: int = 20):
        log.info("Starting paper loop. LIVE ORDER EXECUTION IS DISABLED.")
        while True:
            try:
                self.poll_open_position()
                for symbol in self.cfg.symbols:
                    self.process_symbol_once(symbol)
            except KeyboardInterrupt:
                raise
            except Exception:
                log.exception("Paper loop iteration failed")
            time.sleep(poll_seconds)
