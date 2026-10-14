# Implementation status — v0.3.0 research alpha

| Area | Status |
|---|---|
| Volume baseline excludes current candle | Implemented |
| Daily/weekly UTC VWAP | Implemented |
| Wilder/RMA ATR | Implemented |
| Reject naive timestamps and invalid OHLCV | Implemented |
| Closed-candle helper | Implemented; data paths need careful integration |
| Hourly gap rejection in portfolio backtest | Implemented |
| One global position in portfolio backtest | Implemented |
| Deterministic simultaneous signal tie-break | Implemented |
| Optional funding-event ledger in portfolio backtest | Implemented; caller must supply actual rates |
| Daily realized loss gate before new entry | Implemented; no worst-case reservation/unrealized PnL |
| 1-minute intrabar exit engine | Not implemented |
| Automatic historical funding ingestion | Not implemented |
| Full walk-forward/placebo/parameter harness | Not implemented |
| Robust paper broker/exchange reconciliation | Not implemented |
| Live orders and protective orders | Intentionally not implemented |

This alpha is for research and paper testing only. A green test suite does not
establish a trading edge or prove production readiness.
