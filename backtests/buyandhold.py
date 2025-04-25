'''
🌙 Moon Dev's Buy & Hold Strategy 🚀
Simple strategy that:
- Buys on the first day of data
- Holds forever
- Used to compare drawdown and other metrics against active strategies
'''

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import matplotlib.pyplot as plt

# Load the data (using same data as MA Reversal strategy)
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-1000wks-data.csv'
data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')

class BuyAndHoldStrategy(Strategy):
    def init(self):
        # No indicators needed for buy & hold
        pass

    def next(self):
        # Buy on the first day if we're not in a position
        if len(self.data.Close) > 0 and not self.position:
            self.buy()

# Rename columns to match Backtest.py requirements
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Sort index in ascending order to fix the warning
data = data.sort_index(ascending=True)

# Create and run the backtest with same initial capital as MA Reversal
bt = Backtest(data, BuyAndHoldStrategy, cash=1000000, commission=0.002)

# Run backtest
print("\n🌙 Moon Dev's Buy & Hold Results 🌙")
print("=" * 50)
stats = bt.run()
print(stats)

# Plot the results
print("\n📊 Showing Buy & Hold Strategy Plot...")
bt.plot(filename=None)
plt.show()

# Print key comparison metrics
print("\n🔍 Key Metrics for Comparison:")
print("=" * 50)
print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")
print(f"Average Drawdown: {stats['Avg. Drawdown [%]']:.2f}%")
print(f"Buy & Hold Return: {stats['Return [%]']:.2f}%")
print(f"Annualized Return: {stats['Return (Ann.) [%]']:.2f}%")
print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
print(f"Sortino Ratio: {stats['Sortino Ratio']:.2f}")
print(f"Calmar Ratio: {stats['Calmar Ratio']:.2f}")
print(f"Exposure Time: {stats['Exposure Time [%]']:.2f}%")
