"""
Debug Supertrend Implementation
===============================
Let's see what's happening with the calculations.
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

# Load a small sample of data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()

# Take just last 1000 rows for debugging
data = data.tail(1000)
print(f"Debug data shape: {data.shape}")

# Calculate ATR manually
atr_period = 10
atr_multiplier = 2.0

# Calculate ATR
atr = talib.ATR(data.High.values, data.Low.values, data.Close.values, atr_period)
hl2 = (data.High + data.Low) / 2

# Basic bands
basic_upper = hl2 + (atr_multiplier * atr)
basic_lower = hl2 - (atr_multiplier * atr)

print("Sample data:")
print(data.tail().round(2))
print("\nATR values (last 10):")
print(atr[-10:])
print("\nHL2 values (last 10):")
print(hl2.tail(10).values)
print("\nBasic Upper Band (last 10):")
print(basic_upper.tail(10).values)
print("\nBasic Lower Band (last 10):")
print(basic_lower.tail(10).values)
print("\nClose vs Bands (last 10):")
for i in range(-10, 0):
    print(f"Close: {data.Close.iloc[i]:.2f}, Lower: {basic_lower.iloc[i]:.2f}, Upper: {basic_upper.iloc[i]:.2f}")

class DebugSupertrend(Strategy):
    def init(self):
        # Simple price-based trend
        close = self.data.Close
        sma_fast = self.I(talib.SMA, close, 5)
        sma_slow = self.I(talib.SMA, close, 20)

        self.trend = self.I(lambda: np.where(sma_fast > sma_slow, 1, -1))

    def next(self):
        if len(self.data) < 25:
            return

        curr_trend = self.trend[-1]
        prev_trend = self.trend[-2]

        if not self.position:
            if prev_trend == -1 and curr_trend == 1:
                self.buy(size=1000000)
        else:
            if curr_trend == -1:
                self.position.close()

# Test with simple strategy
bt = Backtest(data, DebugSupertrend, cash=10000000, commission=0.00045)
stats = bt.run()
print(f"\nNumber of trades: {stats['# Trades']}")
print(f"Return: {stats['Return [%]']:.2f}%")

if stats['# Trades'] > 0:
    print("\nStrategy is working! The issue was with Supertrend calculation.")
else:
    print("\nNo trades generated even with simple strategy.")