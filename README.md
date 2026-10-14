# BTC/ETH VWAP-volume futures bot

> **Audit-informed research alpha (v0.3.0). Research/paper only; no live orders.**
> See [`AUDIT_AFTER_XYNTH.md`](AUDIT_AFTER_XYNTH.md) and
> [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) before relying on results.

An open-source Python starter project for researching a 1-hour BTC/ETH perpetual-futures strategy. It includes exact closed-candle signal rules, a simple backtest, a live-data paper loop, SQLite persistence, risk sizing, logging, and tests.

**Live order execution is intentionally not implemented.** The Binance adapter reads public market data only. Do not add real trading credentials or enable real orders without independently reviewing the exchange API behavior, contract sizing, protective-order semantics, failure handling, and legal/tax requirements.

## Strategy specification

For each symbol, on a completed 1-hour candle `t`:

- Volume condition: `volume[t] >= 3 * mean(volume[t-168:t])`. The current candle is excluded from the baseline; the previous 168 completed candles cover seven complete days.
- Daily VWAP: volume-weighted typical price `(high + low + close) / 3` from 00:00 UTC through the current completed candle.
- Weekly VWAP: same calculation from Monday 00:00 UTC through the current completed candle.
- Long: volume condition and close strictly above both daily and weekly VWAP.
- Short: volume condition and close strictly below both daily and weekly VWAP.
- Otherwise: no signal.
- Signals are evaluated only after candle close. Backtests enter at the next candle's open with adverse slippage. Paper mode uses the current ticker price after the closed-candle signal is detected, with adverse slippage.
- One position maximum across both symbols; no pyramiding or automatic reversal.

## Initial risk assumptions (must be validated)

- Risk budget: 0.25% of starting/current paper equity per trade.
- Daily loss limit: 1% of starting equity for the UTC day; new entries halt after it is breached.
- Stop distance: 1.5 × ATR(14), using completed candles at signal time.
- Take-profit distance: 2 × initial stop distance (2R).
- Leverage target: 1x notional to equity in this starter implementation. Real exchange margin/contract rules are not implemented.
- Fees and slippage are estimates and must be replaced with the fee tier and execution assumptions applicable to the actual account.
- Funding is charged/credited in backtests only when a position spans a funding timestamp. Default assumption is a configurable 8-hour schedule and rate; this is an approximation, not a live funding feed.

This is a strategy hypothesis, not a claim of profitability. Candle OHLCV backtests cannot reconstruct queue position, order-book impact, or actual stop fills.

## Setup

Python 3.10+ recommended.

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1

pip install -e ".[dev]"
cp .env.example .env
pytest
```

## Commands

Download public OHLCV and paper-simulate the latest closed candle (one pass):

```bash
vwapbot paper-once --symbol BTC/USDT:USDT
vwapbot paper-once --symbol ETH/USDT:USDT
```

Run the historical backtest against public Binance futures OHLCV:

```bash
vwapbot backtest --symbol BTC/USDT:USDT --days 365
vwapbot backtest --symbol ETH/USDT:USDT --days 365
```

Run live-data paper polling (Ctrl+C to stop):

```bash
vwapbot paper-loop
```

SQLite state and trades are stored in `vwapbot.sqlite3` by default. Logs go to the console and `vwapbot.log`.

## Backtest caveats

- The engine uses next-bar open entries and conservative stop-first handling if both stop and target are touched in the same candle.
- If a candle gaps beyond a stop, it models the fill at the open (plus adverse slippage), not at the stop price.
- A stop/target touched on the same bar as entry is handled conservatively.
- Funding is an approximation; provide historical funding data for a serious study.
- Use chronological train/validation/test segments. Do not tune parameters on the final test period.
- Evaluate net expectancy, drawdown, number of trades, sensitivity, and performance by market regime—not win rate alone.

## Safety and exchange notes

This starter project does not send orders, change leverage, or place Binance stop/TP orders. The paper broker simulates exits locally and therefore cannot protect a real exchange position. Before any live deployment, implement and independently verify Binance USDⓈ-M Futures conditional-order parameters and close-position/reduce-only semantics against current official documentation, add order-state reconciliation, testnet integration tests, and a hard kill switch. Never assume an API acknowledgment means an order is active; query the exchange and verify status.

Use API keys with no withdrawal permission if you later implement trading. Keep secrets out of source control. This software is provided for educational research with no guarantee of performance.


## Audit-informed update

This release adds strict timestamp/OHLCV validation, reusable candle-close and gap-check helpers, audit findings, review prompts for Claude/Xynth, and an explicit implementation-status matrix. Some audit items remain open; see `IMPLEMENTATION_STATUS.md`. This is not production-ready and makes no profitability claim.


## Portfolio alpha (v0.3.0)

Run the combined BTC/ETH portfolio engine (one global position, deterministic
signal priority, gap rejection, optional funding ledger):

```bash
vwapbot portfolio-backtest --days 365
```

This command currently does **not** fetch historical funding automatically.
Do not interpret its output as a complete perpetual-futures result until funding
is supplied and the documented limitations in `ALPHA_RELEASE_NOTES.md` are
addressed.
