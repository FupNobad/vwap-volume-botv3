import sqlite3
from pathlib import Path
from typing import Optional

class Store:
    def __init__(self, path: str = "vwapbot.sqlite3"):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True) if Path(path).parent != Path(".") else None
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS processed_candles (
                symbol TEXT NOT NULL, candle_ms INTEGER NOT NULL,
                PRIMARY KEY(symbol, candle_ms))""")
            con.execute("""CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL, side TEXT NOT NULL, entry_time TEXT NOT NULL,
                entry REAL NOT NULL, stop REAL NOT NULL, take_profit REAL NOT NULL,
                quantity REAL NOT NULL, exit_time TEXT, exit REAL, status TEXT NOT NULL,
                gross_pnl REAL, fees REAL, funding REAL, net_pnl REAL)""")
            con.execute("""CREATE TABLE IF NOT EXISTS bot_state (
                key TEXT PRIMARY KEY, value TEXT NOT NULL)""")

    def _connect(self):
        con = sqlite3.connect(self.path, timeout=30)
        con.row_factory = sqlite3.Row
        return con

    def is_processed(self, symbol: str, candle_ms: int) -> bool:
        with self._connect() as con:
            row = con.execute("SELECT 1 FROM processed_candles WHERE symbol=? AND candle_ms=?",
                              (symbol, candle_ms)).fetchone()
            return row is not None

    def mark_processed(self, symbol: str, candle_ms: int) -> bool:
        with self._connect() as con:
            cur = con.execute("INSERT OR IGNORE INTO processed_candles(symbol,candle_ms) VALUES(?,?)",
                              (symbol, candle_ms))
            return cur.rowcount == 1

    def get_state(self, key: str) -> Optional[str]:
        with self._connect() as con:
            row = con.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
            return row["value"] if row else None

    def set_state(self, key: str, value: str):
        with self._connect() as con:
            con.execute("INSERT INTO bot_state(key,value) VALUES(?,?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    def add_trade(self, trade: dict) -> int:
        keys = ["symbol","side","entry_time","entry","stop","take_profit","quantity","status"]
        vals = [trade[k] for k in keys]
        with self._connect() as con:
            cur = con.execute(
                "INSERT INTO paper_trades(symbol,side,entry_time,entry,stop,take_profit,quantity,status) "
                "VALUES(?,?,?,?,?,?,?,?)", vals)
            return int(cur.lastrowid)

    def close_trade(self, trade_id: int, *, exit_time: str, exit_price: float,
                    gross_pnl: float, fees: float, funding: float, net_pnl: float):
        with self._connect() as con:
            con.execute("""UPDATE paper_trades SET exit_time=?, exit=?, status='closed',
                gross_pnl=?, fees=?, funding=?, net_pnl=? WHERE id=?""",
                (exit_time, exit_price, gross_pnl, fees, funding, net_pnl, trade_id))

    def open_trade(self):
        with self._connect() as con:
            row = con.execute("SELECT * FROM paper_trades WHERE status='open' ORDER BY id LIMIT 1").fetchone()
            return dict(row) if row else None
