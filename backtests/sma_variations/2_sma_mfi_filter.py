"""
🌙 Moon Dev's SMA + MFI Filter Strategy 🌙
===========================================
SMA crossover with Money Flow Index (MFI) filter for better entries.
MFI helps identify overbought/oversold conditions using price AND volume.

Strategy Rules:
- LONG: Fast SMA crosses above slow SMA AND MFI < 50 (not overbought)
- SHORT: Fast SMA crosses below slow SMA AND MFI > 50 (not oversold)
- Exit on opposite signal or TP/SL

The MFI filter should reduce false signals in choppy markets!

HOUSE
                                                                                                                                             
✨ OPTIMIZED RESULTS ✨
============================================================
Start                     2025-03-24 16:00:00
End                       2025-09-07 04:00:00
Duration                    166 days 12:00:00
Exposure Time [%]                         2.2
Equity Final [$]                 12919.724842
Equity Peak [$]                  12919.724842
Return [%]                          29.197248
Buy & Hold Return [%]           228692.326804
Return (Ann.) [%]                   74.466063
Volatility (Ann.) [%]               31.379668
Sharpe Ratio                         2.373067
Sortino Ratio                         9.04481
Calmar Ratio                        15.795931
Max. Drawdown [%]                   -4.714256
Avg. Drawdown [%]                   -3.866595
Max. Drawdown Duration       33 days 08:00:00
Avg. Drawdown Duration       21 days 08:00:00
# Trades                                   18
Win Rate [%]                        77.777778
Best Trade [%]                       2.805611
Worst Trade [%]                     -3.206413
Avg. Trade [%]                       1.433344
Max. Trade Duration           0 days 04:00:00
Avg. Trade Duration           0 days 01:00:00
Profit Factor                        3.057692
Expectancy [%]                       1.464717
SQN                                   2.46218
_strategy                 SMAwithMFIStrate...
_equity_curve                             ...
_trades                          Size  Ent...
dtype: object

🎯 BEST PARAMETERS FOUND:
============================================================
Fast SMA: 20
Slow SMA: 30
MFI Period: 14
MFI Oversold: 30
MFI Overbought: 70
Take Profit: 3.0%
Stop Loss: 3.0%
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
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump-4H-300days-data.csv'

# 1D timeframe data:
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/HYPE_1d_20251020_140859_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump-1D-300days-data.csv'

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

class SMAwithMFIStrategy(Strategy):
    # Parameters to optimize
    sma_fast = 10  # Fast moving average
    sma_slow = 30  # Slow moving average
    mfi_period = 14  # MFI lookback period
    mfi_oversold = 30  # MFI oversold threshold
    mfi_overbought = 70  # MFI overbought threshold
    take_profit = 0.03  # 3% take profit
    stop_loss = 0.05    # 5% stop loss

    def init(self):
        # Calculate Simple Moving Averages
        self.fast_sma = self.I(talib.SMA, self.data.Close, self.sma_fast)
        self.slow_sma = self.I(talib.SMA, self.data.Close, self.sma_slow)

        # Calculate MFI (Money Flow Index)
        self.mfi = self.I(talib.MFI,
                          self.data.High,
                          self.data.Low,
                          self.data.Close,
                          self.data.Volume,
                          self.mfi_period)

    def next(self):
        price = self.data.Close[-1]

        # Skip if we don't have enough data
        if len(self.data) < max(self.sma_slow, self.mfi_period):
            return

        # Get current MFI value
        current_mfi = self.mfi[-1]

        # Check for crossovers with MFI filter
        if crossover(self.fast_sma, self.slow_sma):
            # Golden cross - check MFI for LONG
            if current_mfi < self.mfi_overbought:  # Not overbought
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
            # Death cross - check MFI for SHORT
            if current_mfi > self.mfi_oversold:  # Not oversold
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
bt = Backtest(data, SMAwithMFIStrategy, cash=10000, commission=0.002)

print("\n" + "="*60)
print("🌙 SMA + MFI FILTER STRATEGY - INITIAL RESULTS 🌙")
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
    sma_fast=range(5, 25, 5),
    sma_slow=range(20, 50, 5),
    mfi_period=[10, 14, 20],
    mfi_oversold=[20, 30, 40],
    mfi_overbought=[60, 70, 80],
    take_profit=[0.02, 0.03, 0.04],
    stop_loss=[0.03, 0.04, 0.05],
    maximize='Sharpe Ratio',
    constraint=lambda p: p.sma_fast < p.sma_slow and p.mfi_oversold < p.mfi_overbought
)

print("\n✨ OPTIMIZED RESULTS ✨")
print("="*60)
print(optimization_results)

print("\n🎯 BEST PARAMETERS FOUND:")
print("="*60)
print(f"Fast SMA: {optimization_results._strategy.sma_fast}")
print(f"Slow SMA: {optimization_results._strategy.sma_slow}")
print(f"MFI Period: {optimization_results._strategy.mfi_period}")
print(f"MFI Oversold: {optimization_results._strategy.mfi_oversold}")
print(f"MFI Overbought: {optimization_results._strategy.mfi_overbought}")
print(f"Take Profit: {optimization_results._strategy.take_profit:.1%}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.1%}")

# Run with optimized parameters
optimized_stats = bt.run(
    sma_fast=optimization_results._strategy.sma_fast,
    sma_slow=optimization_results._strategy.sma_slow,
    mfi_period=optimization_results._strategy.mfi_period,
    mfi_oversold=optimization_results._strategy.mfi_oversold,
    mfi_overbought=optimization_results._strategy.mfi_overbought,
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

print("\n🏁 SMA + MFI FILTER STRATEGY COMPLETE!")
print("MFI filter helps avoid overbought/oversold entries.")