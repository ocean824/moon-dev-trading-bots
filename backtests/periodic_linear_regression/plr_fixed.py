"""
Periodic Linear Regression Strategy - FIXED VERSION
=====================================================
Using TALIB LINEARREG with simplified entry logic to ensure trades.
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Periodic Linear Regression - FIXED VERSION 🌙")

# Load data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
# Use only recent data for faster testing
data = data[-10000:]
print(f"✅ Data loaded! {len(data)} rows (last 10k hours)")

class PLRFixed(Strategy):
    lookback = 20
    band_mult = 1.5

    def init(self):
        # Linear regression
        self.linreg = self.I(talib.LINEARREG, self.data.Close, self.lookback)

        # Standard deviation for bands
        self.std = self.I(talib.STDDEV, self.data.Close, self.lookback)

        # Upper and lower bands
        self.upper = self.I(lambda: self.linreg + self.band_mult * self.std)
        self.lower = self.I(lambda: self.linreg - self.band_mult * self.std)

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.lookback + 1:
            return

        # Current values
        price = self.data.Close[-1]
        reg = self.linreg[-1]
        upper = self.upper[-1]
        lower = self.lower[-1]

        # Skip NaN
        if np.isnan(reg):
            return

        # Entry logic
        if not self.position:
            # Buy when price bounces off lower band
            if price < reg and price > lower:
                self.buy(size=1000000)

            # Sell when price bounces off upper band
            elif price > reg and price < upper:
                self.sell(size=1000000)

        # Exit logic
        else:
            if self.position.is_long:
                # Exit long on upper band or stop at lower band
                if price >= upper or price <= lower:
                    self.position.close()

            elif self.position.is_short:
                # Exit short on lower band or stop at upper band
                if price <= lower or price >= upper:
                    self.position.close()

# Run backtest
bt = Backtest(data, PLRFixed, cash=1000000, commission=0.00045)

print("\n🌙 ===== RESULTS ===== 🌙")
stats = bt.run()
print(f"Total Trades: {stats['# Trades']}")
print(f"Win Rate: {stats['Win Rate [%]']:.2f}%" if not np.isnan(stats['Win Rate [%]']) else "Win Rate: N/A")
print(f"Return: {stats['Return [%]']:.2f}%")
print(f"Sharpe: {stats['Sharpe Ratio']:.2f}" if not np.isnan(stats['Sharpe Ratio']) else "Sharpe: N/A")
print(f"Max DD: {stats['Max. Drawdown [%]']:.2f}%")
print(f"Exposure: {stats['Exposure Time [%]']:.2f}%")

if stats['# Trades'] > 0:
    print("\n✅ SUCCESS! Trades generated!")
    print("\nFull Stats:")
    print(stats)
else:
    print("\n❌ Still no trades - need different approach")