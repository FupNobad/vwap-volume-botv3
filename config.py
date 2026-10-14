from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    symbols: tuple[str, ...] = ("BTC/USDT:USDT", "ETH/USDT:USDT")
    timeframe: str = "1h"
    volume_multiple: float = 3.0
    volume_lookback_bars: int = 168
    atr_period: int = 14
    stop_atr_multiple: float = 1.5
    take_profit_r: float = 2.0
    risk_fraction: float = 0.0025
    daily_loss_limit: float = 0.01
    max_leverage: float = 1.0
    taker_fee_rate: float = 0.0005
    slippage_bps: float = 5.0
    funding_rate_per_interval: float = 0.0001
    funding_interval_hours: int = 8
    db_path: str = "vwapbot.sqlite3"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        defaults = cls()
        symbols = tuple(s.strip() for s in os.getenv(
            "SYMBOLS", ",".join(defaults.symbols)).split(",") if s.strip())
        return cls(
            symbols=symbols,
            timeframe=os.getenv("TIMEFRAME", defaults.timeframe),
            volume_multiple=float(os.getenv("VOLUME_MULTIPLE", defaults.volume_multiple)),
            volume_lookback_bars=int(os.getenv("VOLUME_LOOKBACK_BARS", defaults.volume_lookback_bars)),
            atr_period=int(os.getenv("ATR_PERIOD", defaults.atr_period)),
            stop_atr_multiple=float(os.getenv("STOP_ATR_MULTIPLE", defaults.stop_atr_multiple)),
            take_profit_r=float(os.getenv("TAKE_PROFIT_R", defaults.take_profit_r)),
            risk_fraction=float(os.getenv("RISK_FRACTION", defaults.risk_fraction)),
            daily_loss_limit=float(os.getenv("DAILY_LOSS_LIMIT", defaults.daily_loss_limit)),
            max_leverage=float(os.getenv("MAX_LEVERAGE", defaults.max_leverage)),
            taker_fee_rate=float(os.getenv("TAKER_FEE_RATE", defaults.taker_fee_rate)),
            slippage_bps=float(os.getenv("SLIPPAGE_BPS", defaults.slippage_bps)),
            db_path=os.getenv("DB_PATH", defaults.db_path),
            log_level=os.getenv("LOG_LEVEL", defaults.log_level),
        )
