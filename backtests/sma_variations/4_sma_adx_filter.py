"""
🌙 Moon Dev's SMA + ADX Filter Strategy 🌙
===========================================
SMA crossover with ADX (Average Directional Index) filter for trend strength.
ADX measures the strength of a trend regardless of direction.

Strategy Rules:
- LONG: Fast SMA crosses above slow SMA AND ADX > threshold (strong trend)
- SHORT: Fast SMA crosses below slow SMA AND ADX > threshold (strong trend)
- No trades when ADX < threshold (weak/no trend - avoid choppy markets)
- Exit on opposite signal or TP/SL

ADX filter helps avoid whipsaws in ranging markets!
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

class SMAwithADXStrategy(Strategy):
    # Parameters to optimize
    sma_fast = 10  # Fast moving average
    sma_slow = 30  # Slow moving average
    adx_period = 14  # ADX lookback period
    adx_threshold = 25  # Minimum ADX for trend strength
    take_profit = 0.03  # 3% take profit
    stop_loss = 0.05    # 5% stop loss

    def init(self):
        # Calculate Simple Moving Averages
        self.fast_sma = self.I(talib.SMA, self.data.Close, self.sma_fast)
        self.slow_sma = self.I(talib.SMA, self.data.Close, self.sma_slow)

        # Calculate ADX for trend strength
        self.adx = self.I(talib.ADX,
                          self.data.High,
                          self.data.Low,
                          self.data.Close,
                          self.adx_period)

        # Also calculate +DI and -DI for additional trend direction info
        self.plus_di = self.I(talib.PLUS_DI,
                              self.data.High,
                              self.data.Low,
                              self.data.Close,
                              self.adx_period)

        self.minus_di = self.I(talib.MINUS_DI,
                               self.data.High,
                               self.data.Low,
                               self.data.Close,
                               self.adx_period)

    def next(self):
        price = self.data.Close[-1]

        # Skip if we don't have enough data
        if len(self.data) < max(self.sma_slow, self.adx_period * 2):
            return

        # Get current ADX value
        current_adx = self.adx[-1]

        # Only trade when trend is strong enough
        if current_adx < self.adx_threshold:
            return  # Skip weak trends

        # Check for crossovers with ADX filter
        if crossover(self.fast_sma, self.slow_sma):
            # Golden cross with strong trend - go LONG
            # Optional: Can also check if +DI > -DI for additional confirmation
            if self.plus_di[-1] > self.minus_di[-1]:  # Bullish momentum
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
            # Death cross with strong trend - go SHORT
            # Optional: Can also check if -DI > +DI for additional confirmation
            if self.minus_di[-1] > self.plus_di[-1]:  # Bearish momentum
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
bt = Backtest(data, SMAwithADXStrategy, cash=10000, commission=0.002)

print("\n" + "="*60)
print("🌙 SMA + ADX FILTER STRATEGY - INITIAL RESULTS 🌙")
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
    sma_slow=range(20, 50, 10),
    adx_period=[10, 14, 20],
    adx_threshold=[20, 25, 30, 35],
    take_profit=[0.02, 0.03, 0.04],
    stop_loss=[0.03, 0.04, 0.05],
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
print(f"ADX Period: {optimization_results._strategy.adx_period}")
print(f"ADX Threshold: {optimization_results._strategy.adx_threshold}")
print(f"Take Profit: {optimization_results._strategy.take_profit:.1%}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.1%}")

# Run with optimized parameters
optimized_stats = bt.run(
    sma_fast=optimization_results._strategy.sma_fast,
    sma_slow=optimization_results._strategy.sma_slow,
    adx_period=optimization_results._strategy.adx_period,
    adx_threshold=optimization_results._strategy.adx_threshold,
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

print("\n🏁 SMA + ADX FILTER STRATEGY COMPLETE!")
print("ADX filter ensures we only trade in strong trends, avoiding choppy markets.")