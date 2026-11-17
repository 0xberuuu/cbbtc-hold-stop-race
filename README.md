[![make.fun](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603)
[![rank](https://make.fun/badge/btc-race-24h-20261117-0603/0xberuuu/cbbtc-hold-stop-race/rank.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603)
[![reward](https://make.fun/badge/btc-race-24h-20261117-0603/0xberuuu/cbbtc-hold-stop-race/reward.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603)

# cbBTC hold-with-stop race bot

An entry for the [make.fun bounty "Race a BTC trading bot live for 24 hours"](https://make.fun/bounty/btc-race-24h-20261117-0603): a Python bot that trades Coinbase Wrapped BTC (cbBTC) against USDC on 1-minute on-chain bars, starting with $1,000 of paper money.

## Strategy

Buy on the first bar and hold, with a disaster trailing stop as the only
active behaviour:

- **Enter:** buy with all cash on the first batch that carries a bar
  (skipping warm-up batches), retrying on later batches if an order is ever
  rejected.
- **Hold:** track the highest close since entry; sell everything only if the
  close falls 250 bps below that peak.
- **Re-enter:** after a stop-out, buy again once the close recovers 50 bps
  above the exit close and 30 bars have passed.

A full-size round trip costs roughly 35 bps in this replay (4 bps fee, 2 bps
slippage, ~11 bps of pool impact per side), while 1-minute closes move only
~6 bps per bar on average. Every active strategy tested on the dev window —
breakouts, EMA crosses, RSI, dip-buying — lost money to that toll in the
chop, so the bot stays invested and only acts to survive a crash.

## Layout

- `main.py` — the bot. Speaks `agent-fun/bars-replay/v1` (newline-delimited
  JSON on stdin/stdout): one `hello`, one reply per `batch`, then `done`.
  Integer arithmetic only, no network, no wall clock, no randomness, so two
  runs on the same bars produce identical orders.
- `vendor/makefun_bars.py` — byte-identical copy of the kit's Python SDK shim.

## Local verification

Graded locally against the kit's frozen 24-hour dev window with an exact
re-implementation of the documented fill model (fee, slippage, constant-
product impact, next-bar-open fills, end-of-window flatten):

- **Net PnL: +$1.07** (above the $0 dev gate)
- **Trades: 1**, **max drawdown: 2.12%** (meets the guardrails)
- Two runs produce identical results (deterministic).

## License

MIT — see [LICENSE](LICENSE).
