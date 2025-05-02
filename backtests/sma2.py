# /Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump-4H-30days-data.csv

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy

# Load the data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump-1D-300days-data.csv'
data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')

# Print columns to debug
print("\n🔍 Moon Dev checking data columns:", data.columns.tolist())

class SMAStrategy(Strategy):
    # Define the parameters we want to optimize 
    fast_ma = 5  # Fast moving average
    slow_ma = 10  # Slow moving average

    def init(self):
        # Calculate moving averages using pandas_ta
        self.fast = self.I(ta.sma, pd.Series(self.data.Close), length=self.fast_ma)
        self.slow = self.I(ta.sma, pd.Series(self.data.Close), length=self.slow_ma)
        print("🌙 Moon Dev SMA Strategy Initialized! Fast MA:", self.fast_ma, "Slow MA:", self.slow_ma)

    def next(self):
        # Wait for enough data to calculate moving averages
        if len(self.data) < self.slow_ma:
            return
            
        # Check for crossovers manually
        if (self.fast[-2] < self.slow[-2] and 
            self.fast[-1] > self.slow[-1] and 
            not self.position):
            # Fast MA crosses above slow MA - Buy signal
            print("🚀 Moon Dev: Buy Signal! Fast MA crossed above Slow MA")
            self.buy()
            
        elif (self.fast[-2] > self.slow[-2] and 
              self.fast[-1] < self.slow[-1] and 
              self.position):
            # Fast MA crosses below slow MA - Exit position
            print("🔻 Moon Dev: Sell Signal! Fast MA crossed below Slow MA")
            self.position.close()

# Keep only necessary columns and ensure correct names
data = data[['open', 'high', 'low', 'close', 'volume']]
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Print columns after renaming to debug
print("🔄 Moon Dev checking renamed columns:", data.columns.tolist())

# Print data info
print(f"\n🔍 Moon Dev's Dataset Info:")
print(f"Number of candles: {len(data)}")
print(f"Date range: {data.index[0]} to {data.index[-1]}")

# Create and run the backtest
bt = Backtest(data, SMAStrategy, cash=100000, commission=0.002)

# Run with default parameters first
print("\n🌙 Moon Dev's Initial Strategy Results:")
stats = bt.run()
print(stats)

# Calculate maximum MA period based on data length
max_ma = len(data) // 3  # Using 1/3 of data length as maximum
print(f"\n📊 Maximum MA period possible: {max_ma}")

# Optimize the strategy with adjusted ranges
print("\n🚀 Moon Dev's Optimization Results:")
optimization_results = bt.optimize(
    fast_ma=range(2, 10, 1),  # Smaller range for fast MA
    slow_ma=range(5, min(20, max_ma), 2),  # Adjusted range for slow MA
    maximize='Equity Final [$]',
    constraint=lambda param: param.fast_ma < param.slow_ma
)

# Print full optimization results
print("\n🎯 Moon Dev's Full Optimization Stats:")
print(optimization_results)


