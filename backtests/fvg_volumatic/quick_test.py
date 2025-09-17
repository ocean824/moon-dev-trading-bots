"""
Quick test of FVG strategies - no optimization, just base parameters
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import talib

# Load data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
print(f"📊 Loading data...")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index().dropna()
print(f"✅ Data loaded: {len(data)} rows\n")

# Simplified FVG Base Strategy for testing
class SimpleFVG(Strategy):
    min_gap_percent = 0.005  # 0.5%
    volume_threshold = 1.2
    take_profit = 0.03
    stop_loss = 0.02

    def init(self):
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=20)
        self.entry_price = None
        self.gap_high = None
        self.gap_low = None

    def next(self):
        if len(self.data) < 20:
            return

        idx = len(self.data) - 1
        current_price = self.data.Close[-1]

        if self.position:
            # Simple exit logic
            if self.position.is_long:
                if current_price >= self.entry_price * (1 + self.take_profit):
                    self.position.close()
                    self.entry_price = None
                elif current_price <= self.entry_price * (1 - self.stop_loss):
                    self.position.close()
                    self.entry_price = None
            elif self.position.is_short:
                if current_price <= self.entry_price * (1 - self.take_profit):
                    self.position.close()
                    self.entry_price = None
                elif current_price >= self.entry_price * (1 + self.stop_loss):
                    self.position.close()
                    self.entry_price = None
        else:
            # Check for gaps
            if idx >= 2:
                current_low = self.data.Low[idx]
                current_high = self.data.High[idx]
                two_bars_ago_high = self.data.High[idx - 2]
                two_bars_ago_low = self.data.Low[idx - 2]
                current_volume = self.data.Volume[idx]
                avg_volume = self.volume_ma[idx]

                # Bullish gap
                if (current_low > two_bars_ago_high and
                    current_volume >= avg_volume * self.volume_threshold):
                    gap_size = current_low - two_bars_ago_high
                    price_level = (current_low + two_bars_ago_high) / 2
                    if gap_size / price_level >= self.min_gap_percent:
                        self.buy()
                        self.entry_price = current_price
                        return

                # Bearish gap
                if (current_high < two_bars_ago_low and
                    current_volume >= avg_volume * self.volume_threshold):
                    gap_size = two_bars_ago_low - current_high
                    price_level = (current_high + two_bars_ago_low) / 2
                    if gap_size / price_level >= self.min_gap_percent:
                        self.sell()
                        self.entry_price = current_price

# Run test
print("="*60)
print("Testing Simplified FVG Strategy")
print("="*60)

bt = Backtest(data, SimpleFVG, cash=1000000, commission=0.00045)
stats = bt.run()

# Print results
print("\n📊 RESULTS:")
print(f"Return: {stats['Return [%]']:.2f}%")
print(f"Buy & Hold: {stats['Buy & Hold Return [%]']:.2f}%")
print(f"Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
print(f"Sortino Ratio: {stats['Sortino Ratio']:.2f}")
print(f"Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")
print(f"Win Rate: {stats['Win Rate [%]']:.1f}%")
print(f"# Trades: {stats['# Trades']}")
print(f"Avg Trade: {stats['Avg. Trade [%]']:.3f}%")
print(f"Profit Factor: {stats['Profit Factor']:.2f}")

print("\n✅ Test complete!")