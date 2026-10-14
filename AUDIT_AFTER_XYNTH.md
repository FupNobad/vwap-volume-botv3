# Independent Audit Notes — After Xynth Review

This file records review findings and the intended remediation plan. It does
**not** claim the strategy has an edge, and it does not claim all findings are
already fixed in code.

## Strategy definition (preserve as baseline)
- Binance USDⓈ-M BTCUSDT and ETHUSDT perpetuals; 1-hour candles.
- Signal candle must be closed.
- Volume >= 3x mean volume of the prior 168 completed candles; signal candle
  excluded from the baseline.
- Typical-price VWAP: (H+L+C)/3 weighted by base volume.
- Daily VWAP resets 00:00 UTC; weekly VWAP resets Monday 00:00 UTC.
- Long only if close is strictly above both VWAPs; short only if strictly
  below both.
- Backtest entry at next candle open; paper fill uses observed market price
  with configurable adverse slippage.
- Risk budget 0.25% equity; stop 1.5x ATR(14); target 2R; 1x notional/equity
  cap; 1% UTC-day loss limit; one global position; no pyramiding/reversal.
- Live exchange order placement remains disabled.

## Confirmed code limitations to address
1. `normalize_ohlcv` now rejects timezone-naive timestamps, duplicate
   timestamps, null values, non-positive prices, negative volume, and
   malformed OHLC ranges.
2. New `data_quality.py` helpers filter rows by close time and detect hourly
   gaps. The existing CLI/data flow must still be wired to call these checks
   before signal evaluation; helpers alone do not guarantee production safety.
3. Backtest still operates on hourly bars and cannot reliably resolve
   intrabar stop/target order. Implement 1-minute event simulation; where
   ambiguous, assume stop first.
4. Backtest funding is an approximation, not a historical funding ledger.
   Fetch actual funding timestamps/rates and apply only when a position is
   open at the event time.
5. Existing backtest is per-symbol, not a portfolio engine enforcing one
   global BTC/ETH position. Implement a deterministic tie-break for
   simultaneous signals and test invariance to symbol loop order.
6. Daily loss limit needs enforcement before every new entry and must include
   realized PnL, fees, funding, and a conservative new-trade stop/slippage
   allowance.
7. ATR currently uses a simple rolling true-range average, not Wilder's ATR.
   Choose and document the definition; if using Wilder's ATR, test parity.
8. Paper mode is a simulator, not exchange-protected risk. It does not prove
   stop/target order placement, partial-fill handling, or real fill quality.
9. Validate Binance conditional/algo order endpoints, trigger price semantics,
   reduce-only/close-position rules, one-way/hedge mode, precision filters,
   and order-status uncertainty against current official docs before any
   live implementation.

## Research questions (hypotheses, not conclusions)
- Does the VWAP filter add value beyond volume spike + candle direction?
- Does time-of-day-adjusted volume or log-volume z-score improve robustness?
- Do signals cluster into the same underlying market events?
- Are BTC and ETH signals sufficiently correlated that they represent one
  shared risk event?
- Is the 00:00 UTC VWAP comparison useful or nearly degenerate?
- Does any apparent edge survive historical funding, realistic fees/slippage,
  parameter sensitivity, and out-of-sample evaluation?

## Required validation protocol
- Use Binance USDⓈ-M perpetual data, not aggregated spot data, for final claims.
- Validate candle completeness, UTC anchors, duplicate timestamps, and gaps.
- Use next-bar entries and finer-grained exit data; document all fill assumptions.
- Include historical funding at actual funding timestamps, plus taker/maker fee
  scenarios and slippage stress.
- Enforce one global position and daily risk limits.
- Compare against volume-only, candle-body-direction, and matched-hour random
  entry placebos.
- Use chronological holdout and walk-forward windows. Freeze the final holdout.
- Report all tested variants, net expectancy in R, drawdown, exposure, trade
  clustering, confidence intervals, regime breakdowns, and 2x cost stress.
- Do not optimize acceptance thresholds after seeing holdout results.

## Immediate implementation order
1. Wire data-quality checks into every entry point; add regression/property tests.
2. Build a portfolio-level event-driven backtester with historical funding and
   intrabar exit handling.
3. Build the validation harness and compare the original baseline with
   preregistered variants/placebos.
4. Only after those pass, run a paper-trading pilot with reconciliation and
   persistent state. Live trading is out of scope for this release.

## Safety status
Research and paper trading only. No live orders are implemented. Never put
exchange secrets in this repository. No profitability claim is made.
