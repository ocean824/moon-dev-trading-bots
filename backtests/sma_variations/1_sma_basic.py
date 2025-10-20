"""
🌙 Moon Dev's Basic SMA Crossover Strategy 🌙
=============================================
Simple Moving Average crossover strategy - the foundation for all variations.
Uses fast SMA crossing above/below slow SMA for entry signals.

Strategy Rules:
- LONG: When fast SMA crosses above slow SMA
- SHORT: When fast SMA crosses below slow SMA
- Exit on opposite signal or TP/SL

Dr. Data Dawg - this is the baseline to compare all filters against!


HOUSECOIN
s.warn("For multiprocessing support in `Backtest.optimize()` "
                                                                                                                                                      
✨ OPTIMIZED RESULTS ✨
============================================================
Start                     2025-03-24 16:00:00
End                       2025-09-07 04:00:00
Duration                    166 days 12:00:00
Exposure Time [%]                         2.9
Equity Final [$]                   14421.0808
Equity Peak [$]                  17777.280425
Return [%]                          44.210808
Buy & Hold Return [%]           228692.326804
Return (Ann.) [%]                  121.534654
Volatility (Ann.) [%]               81.311582
Sharpe Ratio                         1.494678
Sortino Ratio                         5.56611
Calmar Ratio                         6.437506
Max. Drawdown [%]                  -18.879151
Avg. Drawdown [%]                   -7.858574
Max. Drawdown Duration       38 days 16:00:00
Avg. Drawdown Duration       17 days 00:00:00
# Trades                                   22
Win Rate [%]                        72.727273
Best Trade [%]                       4.809619
Worst Trade [%]                     -6.212425
Avg. Trade [%]                       1.678045
Max. Trade Duration           0 days 08:00:00
Avg. Trade Duration           0 days 02:00:00
Profit Factor                        2.064516
Expectancy [%]                       1.800007
SQN                                  1.324757
_strategy                 BasicSMAStrategy...
_equity_curve                             ...
_trades                          Size  Ent...
dtype: object

🎯 BEST PARAMETERS FOUND:
============================================================
Fast SMA: 20
Slow SMA: 50
Take Profit: 5.0%
Stop Loss: 6.0%

HYPE DAILt
IZED RESULTS ✨
============================================================
Start                     2025-08-21 18:08...
End                       2025-10-20 18:08...
Duration                     60 days 00:00:00
Exposure Time [%]                    4.918033
Equity Final [$]                 10523.874924
Equity Peak [$]                  10523.874924
Return [%]                           5.238749
Buy & Hold Return [%]               -3.446741
Return (Ann.) [%]                   35.734589
Volatility (Ann.) [%]                9.814593
Sharpe Ratio                         3.640965
Sortino Ratio                             inf
Calmar Ratio                              NaN
Max. Drawdown [%]                        -0.0
Avg. Drawdown [%]                         NaN
Max. Drawdown Duration                    NaN
Avg. Drawdown Duration                    NaN
# Trades                                    3
Win Rate [%]                            100.0
Best Trade [%]                        1.81675
Worst Trade [%]                      1.546387
Avg. Trade [%]                       1.720512
Max. Trade Duration           0 days 00:00:00
Avg. Trade Duration           0 days 00:00:00
Profit Factor                             NaN
Expectancy [%]                       1.720587
SQN                                 19.962736
_strategy                 BasicSMAStrategy...
_equity_curve                             ...
_trades                      Size  EntryBa...
dtype: object

🎯 BEST PARAMETERS FOUND:
============================================================
Fast SMA: 15
Slow SMA: 20
Take Profit: 2.0%
Stop Loss: 6.0%

HOUSE CHOPPED AFTER MAY 1 DAILY

✨ OPTIMIZED RESULTS ✨
============================================================
Start                     2025-05-01 00:00:00
End                       2025-10-20 00:00:00
Duration                    172 days 00:00:00
Exposure Time [%]                    1.156069
Equity Final [$]                 10363.240984
Equity Peak [$]                  10363.240984
Return [%]                            3.63241
Buy & Hold Return [%]              -94.296794
Return (Ann.) [%]                    7.818435
Volatility (Ann.) [%]                3.987031
Sharpe Ratio                         1.960967
Sortino Ratio                             inf
Calmar Ratio                              NaN
Max. Drawdown [%]                        -0.0
Avg. Drawdown [%]                         NaN
Max. Drawdown Duration                    NaN
Avg. Drawdown Duration                    NaN
# Trades                                    2
Win Rate [%]                            100.0
Best Trade [%]                       1.803607
Worst Trade [%]                      1.796407
Avg. Trade [%]                       1.800007
Max. Trade Duration           0 days 00:00:00
Avg. Trade Duration           0 days 00:00:00
Profit Factor                             NaN
Expectancy [%]                       1.800007
SQN                                 91.729316
_strategy                 BasicSMAStrategy...
_equity_curve                             ...
_trades                        Size  Entry...
dtype: object

🎯 BEST PARAMETERS FOUND:
============================================================
Fast SMA: 5
Slow SMA: 45
Take Profit: 2.0%
Stop Loss: 5.0%

HOUSE PREMAY 4HOUR
ings.warn("For multiprocessing support in `Backtest.optimize()` "
                                                                                                                                                            
✨ OPTIMIZED RESULTS ✨
============================================================
Start                     2025-05-01 00:00:00
End                       2025-09-07 04:00:00
Duration                    129 days 04:00:00
Exposure Time [%]                    6.958763
Equity Final [$]                 17845.811654
Equity Peak [$]                  17845.811654
Return [%]                          78.458117
Buy & Hold Return [%]              -84.964778
Return (Ann.) [%]                  408.436299
Volatility (Ann.) [%]              270.655703
Sharpe Ratio                         1.509062
Sortino Ratio                       13.010285
Calmar Ratio                        23.540785
Max. Drawdown [%]                  -17.350156
Avg. Drawdown [%]                   -5.556593
Max. Drawdown Duration       22 days 04:00:00
Avg. Drawdown Duration        6 days 15:00:00
# Trades                                   37
Win Rate [%]                         70.27027
Best Trade [%]                       4.809619
Worst Trade [%]                     -6.212425
Avg. Trade [%]                       1.577678
Max. Trade Duration           0 days 12:00:00
Avg. Trade Duration           0 days 02:00:00
Profit Factor                        2.013363
Expectancy [%]                       1.697948
SQN                                  1.945906
_strategy                 BasicSMAStrategy...
_equity_curve                             ...
_trades                          Size  Ent...
dtype: object

🎯 BEST PARAMETERS FOUND:
============================================================
Fast SMA: 5
Slow SMA: 35
Take Profit: 5.0%
Stop Loss: 6.0%
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import matplotlib.pyplot as plt

# Four data sources ready to swap - pick one!
# 4H timeframe data:
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/HYPE_4h_20251020_130820_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump-4H-300days-data.csv'

# 1D timeframe data:
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/HYPE_1d_20251020_140859_historical.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump-1D-300days-data.csv'

# Load data
data = pd.read_csv(data_path)

# Standardize column names
if 'timestamp' in data.columns:
    data = data.rename(columns={'timestamp': 'datetime'})
if 'date' in data.columns:
    data = data.rename(columns={'date': 'datetime'})

# Parse datetime and set as index
data['datetime'] = pd.to_datetime(data['datetime'])
data = data.set_index('datetime')

# Ensure we have the right column names
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Sort index
data = data.sort_index(ascending=True)

class BasicSMAStrategy(Strategy):
    # Parameters to optimize
    sma_fast = 10  # Fast moving average
    sma_slow = 30  # Slow moving average
    take_profit = 0.03  # 3% take profit
    stop_loss = 0.05    # 5% stop loss

    def init(self):
        # Calculate Simple Moving Averages
        self.fast_sma = self.I(talib.SMA, self.data.Close, self.sma_fast)
        self.slow_sma = self.I(talib.SMA, self.data.Close, self.sma_slow)

    def next(self):
        price = self.data.Close[-1]

        # Skip if we don't have enough data
        if len(self.data) < self.sma_slow:
            return

        # Check for crossovers
        if crossover(self.fast_sma, self.slow_sma):
            # Golden cross - go LONG
            if not self.position:
                self.buy(
                    sl=price * (1 - self.stop_loss),
                    tp=price * (1 + self.take_profit)
                )
            elif self.position.is_short:
                self.position.close()
                self.buy(
                    sl=price * (1 - self.stop_loss),
                    tp=price * (1 + self.take_profit)
                )

        elif crossover(self.slow_sma, self.fast_sma):
            # Death cross - go SHORT
            if not self.position:
                self.sell(
                    sl=price * (1 + self.stop_loss),
                    tp=price * (1 - self.take_profit)
                )
            elif self.position.is_long:
                self.position.close()
                self.sell(
                    sl=price * (1 + self.stop_loss),
                    tp=price * (1 - self.take_profit)
                )

# Run backtest with initial parameters
bt = Backtest(data, BasicSMAStrategy, cash=10000, commission=0.002)

print("\n" + "="*60)
print("🌙 BASIC SMA CROSSOVER STRATEGY - INITIAL RESULTS 🌙")
print("="*60)
initial_stats = bt.run()
print(initial_stats)

# Show plot
try:
    bt.plot(filename=None, superimpose=False)  # Disable superimpose to avoid HYPE data issues
except Exception as e:
    print(f"⚠️ Could not display plot: {e}")
    print("Continuing without plot...")

# Optimize parameters
print("\n" + "="*60)
print("🚀 OPTIMIZING PARAMETERS...")
print("="*60)

optimization_results = bt.optimize(
    sma_fast=range(5, 30, 5),
    sma_slow=range(20, 60, 5),
    take_profit=[0.02, 0.03, 0.04, 0.05],
    stop_loss=[0.03, 0.04, 0.05, 0.06],
    maximize='Sharpe Ratio',
    constraint=lambda p: p.sma_fast < p.sma_slow
)

print("\n✨ OPTIMIZED RESULTS ✨")
print("="*60)
print(optimization_results)

print("\n🎯 BEST PARAMETERS FOUND:")
print("="*60)
print(f"Fast SMA: {optimization_results._strategy.sma_fast}")
print(f"Slow SMA: {optimization_results._strategy.sma_slow}")
print(f"Take Profit: {optimization_results._strategy.take_profit:.1%}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.1%}")

# Run with optimized parameters
optimized_stats = bt.run(
    sma_fast=optimization_results._strategy.sma_fast,
    sma_slow=optimization_results._strategy.sma_slow,
    take_profit=optimization_results._strategy.take_profit,
    stop_loss=optimization_results._strategy.stop_loss
)

# Show optimized plot
print("\n📊 Showing optimized strategy plot...")
try:
    bt.plot(filename=None, superimpose=False)  # Disable superimpose to avoid HYPE data issues
except Exception as e:
    print(f"⚠️ Could not display plot: {e}")
    print("Continuing without plot...")

print("\n🏁 BASIC SMA STRATEGY COMPLETE!")
print("This is your baseline - compare all filtered versions to this.")