# Independent review prompts

## Claude — code-level adversarial review
Inspect the actual repository and identify only reproducible implementation
defects or clearly labeled design risks. For each finding provide severity,
exact file/function, a minimal reproduction or failing test, and a proposed
fix. Specifically inspect candle closure, timezone handling, data gaps,
look-ahead, portfolio-level position limits, daily loss enforcement, funding,
ATR definition, intrabar stop/target ambiguity, and restart/idempotency.
Do not claim you ran tests or backtests unless you actually ran them. Do not
change the strategy rules silently. No live trading.

## Xynth — independent quantitative review
Challenge the signal rather than endorse it. Compare the full rule against
volume-only and candle-direction baselines; test signal clustering and
hour-of-day effects; use Binance USDⓈ-M perpetual data and historical funding;
run walk-forward/out-of-sample validation and cost stress. List data sources,
code, exact assumptions, sample sizes, and uncertainty. Clearly distinguish
verified results from hypotheses. Do not invent results. Do not recommend
live trading without execution safeguards and independently validated evidence.

## Reconciliation format
For every disagreement, record:
- Claim A and claim B
- Evidence each claim relies on
- Minimal test/data needed to decide
- Test result
- Decision and follow-up
