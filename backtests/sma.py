# /Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump-4H-30days-data.csv

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy

# Load the data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm-4H-300days-data.csv'
data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')

# Print columns to debug
print("\n🔍 Moon Dev checking data columns:", data.columns.tolist())

class SMAStrategy(Strategy):
    # Define the parameters we want to optimize 
    fast_ma = 5  # Fast moving average
    slow_ma = 10  # Slow moving average
    stop_loss = 0.15    # 3%
    take_profit = 0.30 # 5%

    def init(self):
        # Calculate moving averages using pandas_ta
        self.fast = self.I(ta.sma, pd.Series(self.data.Close), length=self.fast_ma)
        self.slow = self.I(ta.sma, pd.Series(self.data.Close), length=self.slow_ma)

    def next(self):
        # Wait for enough data to calculate moving averages
        if len(self.data) < self.slow_ma:
            return
            
        # Check for crossovers manually
        if (self.fast[-2] < self.slow[-2] and 
            self.fast[-1] > self.slow[-1] and 
            not self.position):
            # Fast MA crosses above slow MA - Buy signal
            self.buy(sl=self.data.Close[-1] * (1 - self.stop_loss),
                    tp=self.data.Close[-1] * (1 + self.take_profit))
            
        elif (self.fast[-2] > self.slow[-2] and 
              self.fast[-1] < self.slow[-1] and 
              not self.position):
            # Fast MA crosses below slow MA - Sell signal
            self.sell(sl=self.data.Close[-1] * (1 + self.stop_loss),
                     tp=self.data.Close[-1] * (1 - self.take_profit))

# Keep only necessary columns and ensure correct names
data = data[['open', 'high', 'low', 'close', 'volume']]
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Print columns after renaming to debug
print("🔄 Moon Dev checking renamed columns:", data.columns.tolist())

# Create and run the backtest
bt = Backtest(data, SMAStrategy, cash=100000, commission=0.002)

# Run with default parameters first
print("\n🌙 Moon Dev's SMA Strategy Results:")
stats = bt.run()
print(stats)

# Optimize the strategy
print("\n🚀 Moon Dev is optimizing the strategy...")
optimization_results = bt.optimize(
    fast_ma=range(5, 30, 5),
    slow_ma=range(10, 50, 5),
    stop_loss=[i / 100 for i in range(7, 40, 2)],
    take_profit=[i / 100 for i in range(30, 70, 5)],
    maximize='Equity Final [$]',
    constraint=lambda param: param.fast_ma < param.slow_ma
)

print("\n🎯 Moon Dev's Best Parameters:")
print(f"Fast MA: {optimization_results._strategy.fast_ma}")
print(f"Slow MA: {optimization_results._strategy.slow_ma}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.1%}")
print(f"Take Profit: {optimization_results._strategy.take_profit:.1%}")


