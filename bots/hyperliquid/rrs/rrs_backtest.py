#!/usr/bin/env python3
"""
raw_rrs_backtest.py

Backtests the raw Real Relative Strength (RRS) strategy using backtesting.py.
Includes debug prints of the RRS series, dynamic percentile-based thresholds,
and prints each signal to verify when entries/exits fire.
"""

import pandas as pd
from backtesting import Backtest, Strategy

# === CONFIGURATION ===
DATA_PATH  = (
    "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/"
    "bots/hyperliquid/rrs/results/FETUSD_6h_rrs.csv"
)
CASH       = 100_000
COMMISSION = 0.002

# === LOAD & PREPARE DATA ===
df = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
df = df.rename(columns={
    'open':  'Open',
    'high':  'High',
    'low':   'Low',
    'close': 'Close',
    'volume':'Volume',
    'rrs':   'RRS'
})
df = df[['Open','High','Low','Close','Volume','RRS']].dropna()

# Debug: print RRS head and summary
print("First 10 raw RRS values:", df.RRS.head(10).tolist())
print("RRS summary stats:\n", df.RRS.describe())

# === STRATEGY ===
class RawRRSDebug(Strategy):
    def init(self):
        # alias raw RRS series
        self.rrs = self.data.RRS

        # compute dynamic thresholds
        series = pd.Series(self.rrs)
        self.entry_level = float(series.quantile(0.80))
        self.exit_level  = float(series.quantile(0.50))

        print(f"Entry level (80th pct): {self.entry_level:.4f}")
        print(f"Exit level  (50th pct): {self.exit_level:.4f}")

    def next(self):
        if len(self.rrs) < 2:
            return

        prev, curr = self.rrs[-2], self.rrs[-1]
        dt = self.data.index[-1]

        # Entry: crossover above entry_level
        if not self.position and prev <= self.entry_level < curr:
            print(f"BUY  {dt}  RRS {prev:.4f}→{curr:.4f} > {self.entry_level:.4f}")
            self.buy()
        # Exit: crossover below exit_level
        elif self.position and prev >= self.exit_level > curr:
            print(f"SELL {dt}  RRS {prev:.4f}→{curr:.4f} < {self.exit_level:.4f}")
            self.position.close()

# === RUN BACKTEST ===
bt = Backtest(df, RawRRSDebug, cash=CASH, commission=COMMISSION)
print("=== BACKTEST RESULTS ===")
stats = bt.run()
print(stats)
