# Alpha release notes — v0.3.0

This is a research alpha, not production trading software. No live order path
exists. It makes no profitability claim.

## Added in this release
- Portfolio-level hourly backtester with one global BTC/ETH position.
- Deterministic simultaneous-signal selection (symbol priority first; then
  volume ratio; then symbol name).
- Optional actual funding events supplied as `timestamp,symbol,rate` rows.
- Funding cashflow is applied only if the matching position was already open
  at the event timestamp.
- UTC-hour gap rejection in the portfolio backtester.
- Daily realized-equity loss gate before new entries.
- Wilder/RMA ATR implementation.
- Tests for portfolio empty case, gap rejection, and funding schema.

## Known limitations — do not ignore
- The portfolio backtester uses hourly OHLC and stop-first collision handling;
  it is not tick/1-minute execution simulation.
- Funding data must be supplied by the caller; the CLI currently does not
  automatically download historical funding data. Results without funding
  are incomplete.
- Daily loss gate uses realized equity and is checked before entries; it does
  not reserve the next trade's worst-case loss or include unrealized PnL.
- Open positions at the end of the data are not force-closed or marked to
  market in reported closed-trade equity.
- It does not model liquidation, maintenance margin tiers, exchange lot-size
  rounding, maker fills, partial fills, queue position, or real order-book
  slippage.
- Single-symbol legacy backtest remains for compatibility and is less realistic
  than the portfolio engine.
- Paper mode remains a local simulation and its local stop logic is not an
  exchange-side protective order. Polling may miss fast moves.
- Candle-close/gap helper functions must be used correctly by callers; the
  portfolio backtester rejects gaps, but all ingestion paths are not yet
  production-hardened.
- Binance market-data behavior and funding semantics must be checked against
  current official documentation before relying on them.

## Run
`pip install -e ".[dev]"`
`pytest`
`vwapbot portfolio-backtest --days 365`

For an honest research report, archive the exact data files, config, commit
hash, dependency versions, and all parameter variants tested. Use an untouched
chronological holdout and compare against preregistered placebos.
