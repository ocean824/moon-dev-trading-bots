#!/usr/bin/env python3
"""
EMA 50/200 crossover with ADX trend‑strength gate (long‑only)
and ATR‑scaled exits on BTC‑USD 1‑hour data.

CSV required:
    /Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/
        BTC-USD-1h-2018-1-01T00_00.csv
"""

# ───────────────────────── Imports ──────────────────────────
import pandas as pd
import pandas_ta as ta
from backtesting import Backtest, Strategy

# ──────────────────────── Settings ──────────────────────────
CSV_PATH   = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/" \
             "BTC-USD-1h-2018-1-01T00_00.csv"

CASH       = 100_000
COMMISSION = 0.0007     # 0.07 % per side
RISK_PCT   = 0.10       # risk 10 % equity per trade

# default parameters (optimised later)
DEFAULTS = dict(
    ema_fast  = 50,
    ema_slow  = 200,
    adx_len   = 14,
    adx_thr   = 20,
    sl_atr    = 1.2,
    trail_atr = 0.8,
)

# ─────────────────────── Load Data ──────────────────────────
df_raw = (
    pd.read_csv(CSV_PATH, parse_dates=["datetime"])
      .set_index("datetime")
      .rename(columns=str.title)            # Open High Low Close Volume
)

# ───────────────────── Strategy Class ───────────────────────
class EMATrend(Strategy):
    """
    Long‑only EMA crossover strategy with ADX filter and ATR exits.
    """

    # class‑level placeholders
    ema_fast  = DEFAULTS["ema_fast"]
    ema_slow  = DEFAULTS["ema_slow"]
    adx_len   = DEFAULTS["adx_len"]
    adx_thr   = DEFAULTS["adx_thr"]
    sl_atr    = DEFAULTS["sl_atr"]
    trail_atr = DEFAULTS["trail_atr"]

    # ------------------- indicators -------------------------
    def init(self):
        d = self.data.df

        ema_fast = d["Close"].ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = d["Close"].ewm(span=self.ema_slow, adjust=False).mean()

        adx_series = ta.adx(
            d["High"], d["Low"], d["Close"],
            length=self.adx_len, mamode="ema"
        )[f"ADX_{self.adx_len}"]

        atr = ta.atr(d["High"], d["Low"], d["Close"], length=14)

        self.ema_fast = self.I(lambda x: x, ema_fast)
        self.ema_slow = self.I(lambda x: x, ema_slow)
        self.adx      = self.I(lambda x: x, adx_series)
        self.atr      = self.I(lambda x: x, atr)

        # trailing helpers
        self.entry_price = None
        self.peak        = None

    # ------------------- helpers ----------------------------
    def _units(self, price):                # integer whole‑lot sizing
        return max(1, int((RISK_PCT * self.equity) // price))

    # ------------------- strategy logic ---------------------
    def next(self):
        price = self.data.Close[-1]
        atr   = self.atr[-1]

        # long‑only signal
        long_sig = (
            self.ema_fast[-1] > self.ema_slow[-1] and            # golden cross
            self.ema_fast[-2] <= self.ema_slow[-2] and           # crossed this bar
            self.adx[-1] > self.adx_thr                          # strong trend
        )
        exit_sig = (
            self.ema_fast[-1] < self.ema_slow[-1] or             # trend flips
            self.adx[-1] < self.adx_thr / 2                      # trend fizzles
        )

        # -------- entry --------
        if long_sig and not self.position:
            self.buy(size=self._units(price),
                     sl=price - self.sl_atr * atr,
                     tp=None)           # take‑profit handled by trailing
            self.entry_price = price
            self.peak        = price

        # -------- trailing exit --------
        if self.position:
            self.peak = max(self.peak, price)
            if (self.peak - self.entry_price >= atr) and \
               (price <= self.peak - self.trail_atr * atr):
                self.position.close()
                self.entry_price = self.peak = None
            elif exit_sig:
                self.position.close()
                self.entry_price = self.peak = None

# ─────────────────── Back‑test & Optimise ───────────────────
bt = Backtest(
    df_raw,
    EMATrend,
    cash=CASH,
    commission=COMMISSION,
    trade_on_close=True,
)

print("=== Baseline (defaults) ===")
print(bt.run())      # full stats

# ───────────── Optimisation (~6 k configs) ──────────────────
print("\nOptimising (~6 k configs)…")

best = bt.optimize(
    ema_fast  = [30, 40, 50, 60, 80],
    ema_slow  = [150, 200, 250, 300],
    adx_thr   = [15, 20, 25, 30],
    sl_atr    = [1.0, 1.2, 1.5],
    trail_atr = [0.6, 0.8, 1.0],
    maximize  = "Expectancy [%]",
    constraint=lambda p: p.ema_fast < p.ema_slow,  # make sense
    return_heatmap=False,
    random_state=42,
)

print("\n=== Optimised parameters ===")
for k in ["ema_fast", "ema_slow", "adx_thr", "sl_atr", "trail_atr"]:
    print(f"{k:8}: {getattr(best._strategy, k)}")

print("\n=== Optimised performance ===")
print(best)         # full stats

bt.plot()
