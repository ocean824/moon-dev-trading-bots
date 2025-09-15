"""
Simple volume test to diagnose trading issues
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta

class SimpleVolumeStrategy(Strategy):
    # Simple parameters
    volume_threshold = 1.1

    def init(self):
        # Simple volume ratio using rolling mean
        volume = pd.Series(self.data.Volume)
        volume_ma = volume.rolling(20).mean()
        self.volume_ratio = self.I(lambda: (volume / volume_ma).fillna(1).values)

        # Simple SMA
        close = pd.Series(self.data.Close)
        self.sma = self.I(ta.sma, close, 20)

    def next(self):
        # Skip if no SMA yet
        if pd.isna(self.sma[-1]):
            return

        # Simple long only strategy
        if not self.position:
            # Buy if volume spike and price above SMA
            if self.volume_ratio[-1] > self.volume_threshold and self.data.Close[-1] > self.sma[-1]:
                self.buy()
        else:
            # Sell if price drops below SMA
            if self.data.Close[-1] < self.sma[-1]:
                self.position.close()

# Load data
data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-100wks-data.csv"
data = pd.read_csv(data_path, index_col=0, parse_dates=True)

# Rename columns
if 'open' in data.columns:
    data = data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low',
                               'close': 'Close', 'volume': 'Volume'})

print(f"Data shape: {data.shape}")
print(f"Data columns: {data.columns.tolist()}")
print(f"Date range: {data.index[0]} to {data.index[-1]}")
print(f"Data index type: {type(data.index)}")

# Run backtest
bt = Backtest(data, SimpleVolumeStrategy, cash=10000, commission=0.002)
stats = bt.run()

print("\n" + "="*60)
print("BACKTEST RESULTS")
print("="*60)
print(stats)

# Check if trades were made
print("\n" + "="*60)
print("TRADE ANALYSIS")
print("="*60)
print(f"Number of trades: {stats['# Trades']}")
if stats['# Trades'] > 0:
    print(f"Win Rate: {stats['Win Rate [%]']:.2f}%")
    print(f"Total Return: {stats['Return [%]']:.2f}%")
else:
    print("No trades were executed. Checking why...")

    # Manual check
    volume = data['Volume']
    volume_ma = volume.rolling(20).mean()
    volume_ratio = volume / volume_ma
    sma = data['Close'].rolling(20).mean()

    potential_signals = (volume_ratio > 1.1) & (data['Close'] > sma)
    print(f"Potential buy signals found: {potential_signals.sum()}")

    if potential_signals.sum() > 0:
        print("\nFirst few potential buy signals:")
        signal_dates = data[potential_signals].index[:5]
        for date in signal_dates:
            print(f"  {date}: Close={data.loc[date, 'Close']:.2f}, Volume Ratio={volume_ratio.loc[date]:.2f}")

# Show plot
bt.plot()