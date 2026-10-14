import argparse
import logging
import json
from dataclasses import asdict
from .config import Config
from .exchange_binance import BinancePublicData
from .backtest import run_backtest\nfrom .portfolio import run_portfolio_backtest
from .paper import PaperTrader

def main():
    cfg = Config.from_env()
    logging.basicConfig(level=getattr(logging, cfg.log_level.upper(), logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler("vwapbot.log")])
    parser = argparse.ArgumentParser(prog="vwapbot")
    sub = parser.add_subparsers(dest="command", required=True)
    pbt = sub.add_parser("backtest")
    pbt.add_argument("--symbol", default=cfg.symbols[0])
    pbt.add_argument("--days", type=int, default=365)
    pp = sub.add_parser("portfolio-backtest")
    pp.add_argument("--days", type=int, default=365)
    ponce = sub.add_parser("paper-once")
    ponce.add_argument("--symbol", default=cfg.symbols[0])
    sub.add_parser("paper-loop")
    args = parser.parse_args()

    if args.command == "backtest":
        df = BinancePublicData().fetch_history(args.symbol, cfg.timeframe, days=args.days)
        result = run_backtest(df, args.symbol, volume_multiple=cfg.volume_multiple,
            volume_lookback=cfg.volume_lookback_bars, atr_period=cfg.atr_period,
            risk_fraction=cfg.risk_fraction, stop_atr_multiple=cfg.stop_atr_multiple,
            take_profit_r=cfg.take_profit_r, max_leverage=cfg.max_leverage,
            taker_fee_rate=cfg.taker_fee_rate, slippage_bps=cfg.slippage_bps,
            funding_rate_per_interval=cfg.funding_rate_per_interval,
            funding_interval_hours=cfg.funding_interval_hours)
        print(json.dumps({k:v for k,v in asdict(result).items() if k != "trades_detail"}, indent=2))
        print(f"Trade detail count: {len(result.trades_detail)}")
    elif args.command == "portfolio-backtest":
        provider = BinancePublicData()
        data = {sym: provider.fetch_history(sym, cfg.timeframe, days=args.days) for sym in cfg.symbols}
        result = run_portfolio_backtest(data, volume_multiple=cfg.volume_multiple,
            volume_lookback=cfg.volume_lookback_bars, atr_period=cfg.atr_period,
            risk_fraction=cfg.risk_fraction, stop_atr_multiple=cfg.stop_atr_multiple,
            take_profit_r=cfg.take_profit_r, max_leverage=cfg.max_leverage,
            taker_fee_rate=cfg.taker_fee_rate, slippage_bps=cfg.slippage_bps,
            daily_loss_limit=cfg.daily_loss_limit)
        summary = {k:v for k,v in result.__dict__.items() if k != "trades_detail"}
        summary["trades_detail_count"] = len(result.trades_detail)
        print(json.dumps(summary, indent=2, default=str))
    elif args.command == "paper-once":
        PaperTrader(cfg).process_symbol_once(args.symbol)
    elif args.command == "paper-loop":
        PaperTrader(cfg).loop()
