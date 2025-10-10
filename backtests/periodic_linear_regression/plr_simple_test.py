"""
Simple Linear Regression Crossover Test
========================================
Testing basic crossover logic to ensure trades are generated.
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("Testing simple linear regression crossover strategy...")

# Load data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"Data loaded: {len(data)} rows")

class SimpleLinearRegressionCrossover(Strategy):
    lookback = 20

    def init(self):
        # Use simple moving average as regression proxy for testing
        self.sma = self.I(talib.SMA, self.data.Close, self.lookback)

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.lookback + 1:
            return

        # Get current values
        price = self.data.Close[-1]
        prev_price = self.data.Close[-2]
        sma = self.sma[-1]
        prev_sma = self.sma[-2]

        # Skip NaN values
        if np.isnan(sma) or np.isnan(prev_sma):
            return

        # Simple crossover logic
        if not self.position:
            # Buy when price crosses above SMA
            if prev_price <= prev_sma and price > sma:
                self.buy(size=1000000)

            # Sell when price crosses below SMA
            elif prev_price >= prev_sma and price < sma:
                self.sell(size=1000000)

        # Exit on opposite signal
        else:
            if self.position.is_long and price < sma:
                self.position.close()
            elif self.position.is_short and price > sma:
                self.position.close()

# Run backtest
bt = Backtest(data, SimpleLinearRegressionCrossover, cash=1000000, commission=0.00045)
stats = bt.run()

print("\n===== RESULTS =====")
print(f"Total Trades: {stats['# Trades']}")
print(f"Win Rate: {stats['Win Rate [%]']:.2f}%" if not np.isnan(stats['Win Rate [%]']) else "Win Rate: N/A")
print(f"Return: {stats['Return [%]']:.2f}%")
print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.2f}" if not np.isnan(stats['Sharpe Ratio']) else "Sharpe Ratio: N/A")
print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")

if stats['# Trades'] > 0:
    print("\nTrades generated successfully!")
else:
    print("\nNo trades generated - checking data...")
    print(f"First 5 close prices: {data['Close'].head()}")
    print(f"Last 5 close prices: {data['Close'].tail()}")