"""
🌙 Moon Dev's Long-Only SMA Strategy 🌙
=========================================
Simple long-only strategy that buys when price crosses above SMA
and sells when price crosses below SMA.

Strategy Rules:
- LONG: When price crosses above SMA
- EXIT: When price crosses below SMA
- NO SHORTS - Long only strategy
- No TP/SL - Exit only on SMA cross

Dr. Data Dawg - this is pure trend following, long only!

HOUSE
===================================================
📊 Testing SMA 20
============================================================
Start                     2025-03-24 16:00:00
End                       2025-09-07 04:00:00
Duration                    166 days 12:00:00
Exposure Time [%]                        49.1
Equity Final [$]                153134.914401
Equity Peak [$]                1175923.805254
Return [%]                        1431.349144
Buy & Hold Return [%]           228692.326804
Return (Ann.) [%]                 37459.06942
Volatility (Ann.) [%]     5218441949286874...
Sharpe Ratio                              0.0
Sortino Ratio                      212.523464
Calmar Ratio                       426.495775
Max. Drawdown [%]                  -87.829872
Avg. Drawdown [%]                  -31.518945
Max. Drawdown Duration      129 days 08:00:00
Avg. Drawdown Duration       10 days 15:00:00
# Trades                                   62
Win Rate [%]                        22.580645
Best Trade [%]                    2869.431591
Worst Trade [%]                    -25.211749
Avg. Trade [%]                       4.499473
Max. Trade Duration           5 days 12:00:00
Avg. Trade Duration           1 days 04:00:00
Profit Factor                        8.614047
Expectancy [%]                      50.998632
SQN                                  0.184869
_strategy                 LongOnlySMAStrat...
_equity_curve                             ...
_trades                           Size  En...
dtype: object

HYPE DAILY
========================================================
✨ OPTIMIZATION COMPLETE ✨
============================================================
Best SMA Period: 11

Full Optimization Results:
Start                     2025-08-21 18:08...
End                       2025-10-20 18:08...
Duration                     60 days 00:00:00
Exposure Time [%]                   39.344262
Equity Final [$]                 12269.464276
Equity Peak [$]                  12755.097534
Return [%]                          22.694643
Buy & Hold Return [%]               -3.446741
Return (Ann.) [%]                  240.014506
Volatility (Ann.) [%]              155.123209
Sharpe Ratio                         1.547251
Sortino Ratio                       11.812066
Calmar Ratio                        31.121142
Max. Drawdown [%]                   -7.712265
Avg. Drawdown [%]                   -4.396222
Max. Drawdown Duration       32 days 00:00:00
Avg. Drawdown Duration       11 days 00:00:00
# Trades                                    2
Win Rate [%]                             50.0
Best Trade [%]                      18.017362
Worst Trade [%]                     -0.210158
Avg. Trade [%]                       8.521583
Max. Trade Duration          17 days 00:00:00
Avg. Trade Duration          11 days 00:00:00
Profit Factor                       85.732505
Expectancy [%]                       8.903602
SQN                                  0.972779
_strategy                 LongOnlySMAStrat...
_equity_curve                             ...
_trades                      Size  EntryBa...
dtype: object

HOUSE
OPTIMIZATION COMPLETE ✨
============================================================
Best SMA Period: 12

Full Optimization Results:
Start                     2025-03-24 00:00:00
End                       2025-10-20 00:00:00
Duration                    210 days 00:00:00
Exposure Time [%]                   31.753555
Equity Final [$]                 20417.748949
Equity Peak [$]                 105439.276298
Return [%]                         104.177489
Buy & Hold Return [%]           130947.830717
Return (Ann.) [%]                  243.771224
Volatility (Ann.) [%]             43570.07444
Sharpe Ratio                         0.005595
Sortino Ratio                        2.809308
Calmar Ratio                          2.98669
Max. Drawdown [%]                  -81.619195
Avg. Drawdown [%]                  -46.871303
Max. Drawdown Duration      173 days 00:00:00
Avg. Drawdown Duration       88 days 00:00:00
# Trades                                   12
Win Rate [%]                        16.666667
Best Trade [%]                      392.03029
Worst Trade [%]                    -27.869553
Avg. Trade [%]                       6.128974
Max. Trade Duration          12 days 00:00:00
Avg. Trade Duration           5 days 00:00:00
Profit Factor                        3.929201
Expectancy [%]                      26.582437
SQN                                  0.235625
_strategy                 LongOnlySMAStrat...
_equity_curve                             ...
_trades                          Size  Ent...
dtype: object

"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import matplotlib.pyplot as plt

# Four data sources ready to swap - pick one!
# 4H timeframe data:
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/HYPE_4h_20251020_130820_historical.csv'
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

class LongOnlySMAStrategy(Strategy):
    # Parameter to optimize
    sma_period = 20  # Default SMA period

    def init(self):
        # Calculate Simple Moving Average
        self.sma = self.I(talib.SMA, self.data.Close, self.sma_period)

    def next(self):
        price = self.data.Close[-1]

        # Skip if we don't have enough data
        if len(self.data) < self.sma_period:
            return

        # Get previous values for crossover detection
        if len(self.data) < 2:
            return

        prev_price = self.data.Close[-2]
        prev_sma = self.sma[-2]
        curr_sma = self.sma[-1]

        # Check for crossovers
        # Price crossed above SMA - BUY
        if prev_price <= prev_sma and price > curr_sma and not self.position:
            self.buy()

        # Price crossed below SMA - SELL (exit long)
        elif prev_price >= prev_sma and price < curr_sma and self.position:
            self.position.close()

# Run backtests for different SMA periods
print("\n" + "="*80)
print("🌙 LONG-ONLY SMA STRATEGY - TESTING MULTIPLE PERIODS 🌙")
print("="*80)

# Store results for comparison
all_results = []

# Test specific SMA periods: 10, 20, 30, 40
test_periods = [10, 20, 30, 40]

for period in test_periods:
    print(f"\n" + "="*60)
    print(f"📊 Testing SMA {period}")
    print("="*60)

    # Create backtest
    bt = Backtest(data, LongOnlySMAStrategy, cash=10000, commission=0.002)

    # Run with specific SMA period
    stats = bt.run(sma_period=period)

    # Print full stats
    print(stats)

    # Store results for comparison table
    all_results.append({
        'SMA Period': period,
        'Total Return %': round(stats['Return [%]'], 2),
        'Sharpe Ratio': round(stats['Sharpe Ratio'], 2),
        'Max Drawdown %': round(stats['Max. Drawdown [%]'], 2),
        'Win Rate %': round(stats['Win Rate [%]'], 2),
        'Total Trades': stats['# Trades'],
        'Profit Factor': round(stats['Profit Factor'], 2) if 'Profit Factor' in stats else 0
    })

    # Show plot for SMA 20 (default)
    if period == 20:
        print("\n📈 Showing plot for SMA 20 (default period)...")
        try:
            bt.plot(filename=None, superimpose=False)  # Disable superimpose to avoid HYPE data issues
        except Exception as e:
            print(f"⚠️ Could not display plot: {e}")
            print("Continuing without plot...")

# Create comparison table
print("\n" + "="*80)
print("📊 QUICK COMPARISON TABLE - ALL SMA PERIODS")
print("="*80)

df_results = pd.DataFrame(all_results)
df_results = df_results.sort_values('Total Return %', ascending=False)
print("\n" + df_results.to_string(index=False))

# Now run full optimization to find the absolute best SMA period
print("\n" + "="*80)
print("🚀 RUNNING FULL OPTIMIZATION (SMA 5-50)")
print("="*80)

bt_optimize = Backtest(data, LongOnlySMAStrategy, cash=10000, commission=0.002)

optimization_results = bt_optimize.optimize(
    sma_period=range(5, 51, 1),  # Test every period from 5 to 50
    maximize='Sharpe Ratio'
)

print("\n" + "="*60)
print("✨ OPTIMIZATION COMPLETE ✨")
print("="*60)
print(f"Best SMA Period: {optimization_results._strategy.sma_period}")
print("\nFull Optimization Results:")
print(optimization_results)

# Show optimized plot
print("\n📊 Showing optimized strategy plot...")
try:
    bt_optimize.plot(filename=None, superimpose=False)  # Disable superimpose to avoid HYPE data issues
except Exception as e:
    print(f"⚠️ Could not display plot: {e}")
    print("Continuing without plot...")

print("\n" + "="*80)
print("🏁 LONG-ONLY SMA STRATEGY COMPLETE!")
print("="*80)
print("Strategy: Buys when price crosses above SMA, sells when it crosses below")
print("No shorts, no stop loss, no take profit - pure trend following!")
print(f"\nBest SMA Period Found: {optimization_results._strategy.sma_period}")