"""Buy-and-hold with a disaster trailing stop, for the cbBTC 24h race.

Protocol: agent-fun/bars-replay/v1. The harness sends one hello, then one
batch per 1-minute bar, then done; this bot answers every batch with exactly
one reply echoing its seq, carrying at most one order.

Why this shape: a full-size round trip here costs roughly 35 bps (4 bps fee,
2 bps modelled slippage and ~11 bps of constant-product impact per side at
the observed pool depth), while 1-minute closes move only ~6 bps per bar on
average. On the published dev window every active strategy I tested — Donchian
breakouts, EMA crosses, RSI and dip-buying mean reversion — lost money to
that toll in the chop, and plain buy-and-hold was the only shape that ended
above zero. So the bot holds, and only acts to survive a crash:

- ENTER: on the first batch that carries a bar (skipping any warm-up
  batches, whose orders the replay would reject), buy with all cash. If the
  order is ever rejected, keep retrying on later batches until a position
  appears: a missed entry must not strand the bot in cash for the window.
- HOLD: while long, track the highest close seen since entry. Sell everything
  only if the close falls TRAIL_BPS below that peak — a disaster stop, wide
  enough (250 bps) that ordinary chop never trips it.
- RE-ENTER: after a stop-out, buy again once the close recovers RECOVER_BPS
  above the exit close and COOLDOWN_BARS have passed, so a crash with weak
  bounces cannot churn the account through repeated round trips.

All decisions are integer arithmetic on bar closes and the account the batch
carries. No network, no wall clock, no environment reads, no randomness: two
runs on the same bars answer every batch with the same orders.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# --- Parameters: round numbers, chosen for robustness, not fitted tight. ---
TRAIL_BPS = 250        # disaster trailing stop under the peak close since entry
RECOVER_BPS = 50       # recovery above the exit close before re-entering
COOLDOWN_BARS = 30     # bars to wait after a stop-out before re-entering
MAX_SLIPPAGE_BPS = 100  # 1%: far above any 1-minute move plus fill costs


class HoldWithStop:
    """One run's state: position phase, peak since entry, exit bookkeeping."""

    def __init__(self):
        self.held_last_batch = False
        self.peak_since_entry = 0
        self.exit_close = None
        self.exit_seq = None
        self.last_close = 0

    def on_batch(self, state, batch):
        if state.warming_up:
            return []
        bar = None
        for b in batch["bars"]:
            if b["symbol"] == SYMBOL:
                bar = b
                break
        if bar is None:
            # A minute with no sample has no bar: no new information, no order.
            return []
        close = int(bar["c"])

        holding = state.positions.get(SYMBOL)
        held = holding is not None and holding.qty > 0
        if held and not self.held_last_batch:
            # A fresh position: the peak starts at this close.
            self.peak_since_entry = close
        if not held and self.held_last_batch:
            # The position just disappeared: record the exit for re-entry.
            self.exit_close = self.last_close
            self.exit_seq = state.seq - 1
        self.held_last_batch = held
        self.last_close = close

        if held:
            if close > self.peak_since_entry:
                self.peak_since_entry = close
            if close * 10000 < self.peak_since_entry * (10000 - TRAIL_BPS):
                return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            return []

        if state.cash <= 0:
            return []
        if self.exit_close is None:
            # Never held (or never stopped out): enter with all cash, retrying
            # on later batches if an order is ever rejected.
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": state.cash,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        if state.seq - self.exit_seq < COOLDOWN_BARS:
            return []
        if close * 10000 > self.exit_close * (10000 + RECOVER_BPS):
            self.exit_close = None
            self.exit_seq = None
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": state.cash,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []


def main():
    bot = HoldWithStop()
    makefun_bars.run(bot.on_batch)


if __name__ == "__main__":
    main()
