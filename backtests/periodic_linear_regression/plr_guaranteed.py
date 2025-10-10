"""
Periodic Linear Regression - GUARANTEED TO TRADE VERSION
=========================================================
Super simple logic to ensure trades happen.
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 GUARANTEED TRADES VERSION 🌙")

# Load data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
# Use recent subset for testing
data = data[-5000:]
print(f"✅ Data loaded! {len(data)} rows")

class PLRGuaranteed(Strategy):
    def init(self):
        # Simple 20-period linear regression
        self.linreg = self.I(talib.LINEARREG, self.data.Close, 20)
        # Add slope for direction
        self.slope = self.I(talib.LINEARREG_SLOPE, self.data.Close, 20)
        # Track trade count
        self.trade_count = 0

    def next(self):
        # Skip initial period
        if len(self.data) < 21:
            return

        price = self.data.Close[-1]
        reg = self.linreg[-1]
        slope = self.slope[-1]

        # Skip NaN
        if np.isnan(reg) or np.isnan(slope):
            return

        # Ultra simple: trade every N bars if no position
        if not self.position:
            # Trade based on position relative to regression + slope direction
            if price > reg and slope > 0:
                # Bullish - buy
                self.buy()
                self.trade_count += 1
            elif price < reg and slope < 0:
                # Bearish - sell
                self.sell()
                self.trade_count += 1

        # Exit after holding for some bars or on reversal
        else:
            bars_held = len(self.data) - self.trades[-1].entry_bar

            if self.position.is_long:
                # Exit if held for 20+ bars or price drops below regression
                if bars_held >= 20 or price < reg:
                    self.position.close()
            else:
                # Exit if held for 20+ bars or price rises above regression
                if bars_held >= 20 or price > reg:
                    self.position.close()

# Run backtest
bt = Backtest(data, PLRGuaranteed, cash=10000, commission=0.002)

print("\n🌙 ===== RUNNING BACKTEST ===== 🌙")
stats = bt.run()

print(f"\n📊 RESULTS:")
print(f"Total Trades: {stats['# Trades']}")
print(f"Win Rate: {stats['Win Rate [%]']:.2f}%" if stats['# Trades'] > 0 else "No trades")
print(f"Return: {stats['Return [%]']:.2f}%")
print(f"Exposure: {stats['Exposure Time [%]']:.2f}%")

if stats['# Trades'] > 0:
    print("\n✅ TRADES GENERATED SUCCESSFULLY!")
    print("\n" + "="*50)
    print("FULL STATISTICS:")
    print("="*50)
    print(stats)