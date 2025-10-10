"""
Ultra Simple Debug Strategy
===========================
Testing basic buy/sell logic.
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

# Load data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()

# Take recent data
data = data.tail(2000)
print(f"Data shape: {data.shape}")
print(f"Price range: ${data.Close.min():.2f} - ${data.Close.max():.2f}")

class UltraSimple(Strategy):
    def init(self):
        # Simple moving average crossover
        self.sma_short = self.I(talib.SMA, self.data.Close, 5)
        self.sma_long = self.I(talib.SMA, self.data.Close, 20)

    def next(self):
        if len(self.data) < 25:
            return

        # Force a buy on the 50th bar for testing
        if len(self.data) == 50 and not self.position:
            print(f"Forcing buy at bar 50, price: {self.data.Close[-1]}")
            self.buy()
            return

        # Force a sell on the 60th bar
        if len(self.data) == 60 and self.position:
            print(f"Forcing sell at bar 60, price: {self.data.Close[-1]}")
            self.position.close()
            return

        # Normal crossover logic
        if (self.sma_short[-1] > self.sma_long[-1] and
            self.sma_short[-2] <= self.sma_long[-2] and
            not self.position):
            print(f"Buy signal at {self.data.index[-1]}, price: {self.data.Close[-1]}")
            self.buy()

        if (self.sma_short[-1] < self.sma_long[-1] and
            self.sma_short[-2] >= self.sma_long[-2] and
            self.position):
            print(f"Sell signal at {self.data.index[-1]}, price: {self.data.Close[-1]}")
            self.position.close()

# Test with different cash amounts
for cash in [10000, 100000, 1000000, 10000000]:
    print(f"\n--- Testing with ${cash:,} cash ---")
    bt = Backtest(data, UltraSimple, cash=cash, commission=0.0001)
    try:
        stats = bt.run()
        print(f"Trades: {stats['# Trades']}")
        print(f"Return: {stats['Return [%]']:.2f}%")
        if stats['# Trades'] > 0:
            print("SUCCESS! Strategy working.")
            break
    except Exception as e:
        print(f"Error: {e}")

print(f"\nFinal test - checking if we can afford Bitcoin at current prices:")
current_price = data.Close.iloc[-1]
print(f"Current BTC price: ${current_price:,.2f}")
print(f"With $10M cash, we can buy: {10000000/current_price:.4f} BTC")