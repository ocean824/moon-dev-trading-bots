'''
🌙 MOON DEV Intraday Short Selling Parabolic Moves Strategy 🚀
Looking for parabolic upside moves to short back down


🔥TESTS 
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-5wks-data.csv'
                                                                      
🌙 MOON DEV Optimization Complete! Final Results:
============================================================
Start                     2025-01-19 13:43:00
End                       2025-02-23 13:42:00
Duration                     34 days 23:59:00
Exposure Time [%]                   54.801587
Equity Final [$]                  111486.6449
Equity Peak [$]                   112493.9349
Return [%]                          11.486645
Buy & Hold Return [%]               -8.677571
Return (Ann.) [%]                  201.152996
Volatility (Ann.) [%]               71.334361
Sharpe Ratio                         2.819861
Sortino Ratio                       20.766399
Calmar Ratio                        47.389025
Max. Drawdown [%]                   -4.244717
Avg. Drawdown [%]                    -0.68436
Max. Drawdown Duration        6 days 03:59:00
Avg. Drawdown Duration        0 days 07:02:00
# Trades                                    6
Win Rate [%]                        66.666667
Best Trade [%]                       5.654863
Worst Trade [%]                     -3.248873
Avg. Trade [%]                       1.817985
Max. Trade Duration          13 days 16:56:00
Avg. Trade Duration           3 days 04:43:00
Profit Factor                          2.7548
Expectancy [%]                       1.887957
SQN                                  1.173152
_strategy                 ParabolicMoveSho...
_equity_curve                             ...
_trades                      Size  EntryBa...
dtype: object
============================================================

🎯 MOON DEV Best Optimized Parameters:
🔍 Lookback Window: 20
📊 Standard Deviations: 3.0
🎯 Take Profit: 5.0%
🛡️ Stop Loss: 3.0%
🌙 MOON DEV Strategy Complete! 🚀




data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/TRUMP_5m_20250604_130211_historical.csv'
MOON DEV Optimization Complete! Final Results:
============================================================
Start                     2025-05-18 08:27...
End                       2025-06-04 17:02...
Duration                     17 days 08:35:00
Exposure Time [%]                        87.4
Equity Final [$]                150835.090888
Equity Peak [$]                 150835.090888
Return [%]                          50.835091
Buy & Hold Return [%]              -13.295571
Return (Ann.) [%]               296315.614002
Volatility (Ann.) [%]           473439.071455
Sharpe Ratio                         0.625879
Sortino Ratio                     9035.422363
Calmar Ratio                     21662.006628
Max. Drawdown [%]                  -13.679047
Avg. Drawdown [%]                   -1.175765
Max. Drawdown Duration        4 days 07:35:00
Avg. Drawdown Duration        0 days 06:45:00
# Trades                                   25
Win Rate [%]                             44.0
Best Trade [%]                       6.955021
Worst Trade [%]                     -2.327919
Avg. Trade [%]                        1.65771
Max. Trade Duration           3 days 01:10:00
Avg. Trade Duration           0 days 14:29:00
Profit Factor                        2.414938
Expectancy [%]                       1.755742
SQN                                   1.96466
_strategy                 ParabolicMoveSho...
_equity_curve                             ...
_trades                        Size  Entry...
dtype: object
============================================================

🎯 MOON DEV Best Optimized Parameters:
🔍 Lookback Window: 10
📊 Standard Deviations: 2.2
🎯 Take Profit: 7.0%
🛡️ Stop Loss: 2.0%
🌙 MOON DEV Strategy Complete! 🚀
'''

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

# Load the TRUMP data
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-5wks-data.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-10wks-data.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/TRUMP_5m_20250604_130211_historical.csv'

# 🌙 MOON DEV Adaptive header detection for different data sources
# First, peek at the headers to determine format
sample_df = pd.read_csv(data_path, nrows=1)
headers = sample_df.columns.tolist()

# Determine which datetime column to use
if 'timestamp' in headers:
    datetime_col = 'timestamp'
elif 'datetime' in headers:
    datetime_col = 'datetime'
else:
    raise ValueError("🌙 MOON DEV Error: No 'timestamp' or 'datetime' column found!")

# Load data with the correct datetime column
data = pd.read_csv(data_path, parse_dates=[datetime_col], index_col=datetime_col)

# Parabolic Move Short Strategy
class ParabolicMoveShort(Strategy):
    # Strategy Constants - MOON DEV Style! 🌙
    lookback_window = 20        # Window for mean calculation
    std_dev_multiplier = 2.0    # Standard deviations from mean
    take_profit = 0.04          # 4% take profit
    stop_loss = 0.02            # 2% stop loss
    
    def init(self):
        # Calculate rolling mean and standard deviation
        self.rolling_mean = self.I(talib.SMA, self.data.Close, self.lookback_window)
        self.rolling_std = self.I(talib.STDDEV, self.data.Close, self.lookback_window)
        # Calculate upper threshold (mean + std_dev * std)
        self.upper_threshold = self.I(lambda: self.rolling_mean + (self.std_dev_multiplier * self.rolling_std))

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.lookback_window:
            return
            
        current_price = self.data.Close[-1]
        threshold = self.upper_threshold[-1]
        
        # Short when price breaks above the parabolic threshold
        if current_price > threshold and not self.position:
            # MOON DEV going short on parabolic move! 🌙📉
            self.sell(
                sl=current_price * (1 + self.stop_loss),  # Stop loss above entry
                tp=current_price * (1 - self.take_profit)  # Take profit below entry
            )

# Prepare data - convert lowercase columns to uppercase for backtesting.py
# Convert column names to title case for backtesting.py compatibility
data.columns = [col.title() for col in data.columns]

# Create and configure the backtest
bt = Backtest(data, ParabolicMoveShort, cash=100000, commission=0.002)

# Run the backtest with default parameters
stats_default = bt.run()
print("\n🌙 MOON DEV Default Parameters Results:")
print("=" * 60)
print(stats_default)
print("=" * 60)

# Optimization parameters
optimization_results = bt.optimize(
    lookback_window=range(10, 31, 5),                          # 10, 15, 20, 25, 30
    std_dev_multiplier=[round(i, 1) for i in np.arange(1.0, 3.1, 0.2)],  # 1.0 to 3.0
    take_profit=[i / 100 for i in range(2, 8, 1)],            # 2% to 7%
    stop_loss=[i / 100 for i in range(1, 6, 1)],              # 1% to 5%
    maximize='Equity Final [$]',
    constraint=lambda param: param.lookback_window > 0 and param.std_dev_multiplier > 0
)

print("\n🌙 MOON DEV Optimization Complete! Final Results:")
print("=" * 60)
print(optimization_results)
print("=" * 60)

print("\n🎯 MOON DEV Best Optimized Parameters:")
print(f"🔍 Lookback Window: {optimization_results._strategy.lookback_window}")
print(f"📊 Standard Deviations: {optimization_results._strategy.std_dev_multiplier}")
print(f"🎯 Take Profit: {optimization_results._strategy.take_profit:.1%}")
print(f"🛡️ Stop Loss: {optimization_results._strategy.stop_loss:.1%}")
print("🌙 MOON DEV Strategy Complete! 🚀")