"""
🌙 Moon Dev's SMA + VWAP Filter Strategy 🌙
============================================
SMA crossover with VWAP (Volume Weighted Average Price) filter.
VWAP shows the average price weighted by volume - institutional reference point.

Strategy Rules:
- LONG: Fast SMA crosses above slow SMA AND price > VWAP (bullish bias)
- SHORT: Fast SMA crosses below slow SMA AND price < VWAP (bearish bias)
- VWAP acts as dynamic support/resistance
- Exit on opposite signal or TP/SL

VWAP filter helps align with institutional flow!

HYPE
✨ OPTIMIZED RESULTS ✨
============================================================
Start                     2025-08-21 21:08...
End                       2025-10-20 17:08...
Duration                     59 days 20:00:00
Exposure Time [%]                    3.333333
Equity Final [$]                  10928.35801
Equity Peak [$]                   10928.35801
Return [%]                            9.28358
Buy & Hold Return [%]               -5.305993
Return (Ann.) [%]                   70.097306
Volatility (Ann.) [%]               15.159705
Sharpe Ratio                         4.623923
Sortino Ratio                             inf
Calmar Ratio                        51.652703
Max. Drawdown [%]                   -1.357089
Avg. Drawdown [%]                   -1.127455
Max. Drawdown Duration        0 days 08:00:00
Avg. Drawdown Duration        0 days 08:00:00
# Trades                                    5
Win Rate [%]                            100.0
Best Trade [%]                       1.803607
Worst Trade [%]                      1.785916
Avg. Trade [%]                       1.795337
Max. Trade Duration           0 days 12:00:00
Avg. Trade Duration           0 days 06:00:00
Profit Factor                             NaN
Expectancy [%]                       1.795337
SQN                                 90.138177
_strategy                 SMAwithVWAPStrat...
_equity_curve                             ...
_trades                      Size  EntryBa...
dtype: object

HOUSE POST MAY
                                                                                                                                                 
✨ OPTIMIZED RESULTS ✨
============================================================
Start                     2025-05-01 00:00:00
End                       2025-09-07 04:00:00
Duration                    129 days 04:00:00
Exposure Time [%]                    3.865979
Equity Final [$]                 12643.491988
Equity Peak [$]                  13938.382992
Return [%]                           26.43492
Buy & Hold Return [%]              -84.964778
Return (Ann.) [%]                   93.201858
Volatility (Ann.) [%]               60.278539
Sharpe Ratio                         1.546186
Sortino Ratio                        5.026746
Calmar Ratio                        10.032375
Max. Drawdown [%]                   -9.290109
Avg. Drawdown [%]                   -4.716545
Max. Drawdown Duration       17 days 16:00:00
Avg. Drawdown Duration        7 days 01:00:00
# Trades                                   25
Win Rate [%]                             60.0
Best Trade [%]                       3.807615
Worst Trade [%]                     -3.206413
Avg. Trade [%]                       0.942645
Max. Trade Duration           0 days 08:00:00
Avg. Trade Duration           0 days 01:00:00
Profit Factor                        1.782676
Expectancy [%]                       1.001428
SQN                                  1.310035
_strategy                 SMAwithVWAPStrat...
_equity_curve                             ...
_trades                         Size  Entr...
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
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/HYPE_4h_20251020_130820_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump-4H-300days-data.csv'

# 1D timeframe data:
# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/HYPE_1d_20251020_140859_historical.csv'
# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/birdeye/DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump-1D-300days-data.csv'

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

def calculate_vwap(high, low, close, volume, period=None):
    """
    Calculate VWAP (Volume Weighted Average Price)
    If period is None, uses cumulative VWAP
    Otherwise uses rolling VWAP over specified period
    """
    typical_price = (high + low + close) / 3

    if period is None:
        # Cumulative VWAP (resets each day in intraday, we'll use expanding)
        cumulative_volume = np.cumsum(volume)
        cumulative_pv = np.cumsum(typical_price * volume)
        vwap = cumulative_pv / cumulative_volume
    else:
        # Rolling VWAP over specified period
        vwap = np.zeros(len(close))
        for i in range(len(close)):
            if i < period - 1:
                # Not enough data, use what we have
                start_idx = 0
            else:
                start_idx = i - period + 1

            period_volume = volume[start_idx:i+1]
            period_tp = typical_price[start_idx:i+1]

            if np.sum(period_volume) > 0:
                vwap[i] = np.sum(period_tp * period_volume) / np.sum(period_volume)
            else:
                vwap[i] = typical_price[i]

    return vwap

class SMAwithVWAPStrategy(Strategy):
    # Parameters to optimize
    sma_fast = 10  # Fast moving average
    sma_slow = 30  # Slow moving average
    vwap_period = 20  # VWAP lookback period (None for cumulative)
    vwap_buffer = 0.002  # Buffer above/below VWAP (0.2%)
    take_profit = 0.03  # 3% take profit
    stop_loss = 0.05    # 5% stop loss

    def init(self):
        # Calculate Simple Moving Averages
        self.fast_sma = self.I(talib.SMA, self.data.Close, self.sma_fast)
        self.slow_sma = self.I(talib.SMA, self.data.Close, self.sma_slow)

        # Calculate VWAP
        vwap_values = calculate_vwap(
            np.array(self.data.High),
            np.array(self.data.Low),
            np.array(self.data.Close),
            np.array(self.data.Volume),
            self.vwap_period
        )
        self.vwap = self.I(lambda: vwap_values, name='VWAP')

        # Calculate VWAP bands for better signals
        self.vwap_upper = self.I(lambda: vwap_values * (1 + self.vwap_buffer), name='VWAP_Upper')
        self.vwap_lower = self.I(lambda: vwap_values * (1 - self.vwap_buffer), name='VWAP_Lower')

    def next(self):
        price = self.data.Close[-1]

        # Skip if we don't have enough data
        if len(self.data) < max(self.sma_slow, self.vwap_period or 1):
            return

        # Check position relative to VWAP
        above_vwap = price > self.vwap_upper[-1]
        below_vwap = price < self.vwap_lower[-1]

        # Check for crossovers with VWAP filter
        if crossover(self.fast_sma, self.slow_sma) and above_vwap:
            # Golden cross with price above VWAP - strong LONG signal
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

        elif crossover(self.slow_sma, self.fast_sma) and below_vwap:
            # Death cross with price below VWAP - strong SHORT signal
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
bt = Backtest(data, SMAwithVWAPStrategy, cash=10000, commission=0.002)

print("\n" + "="*60)
print("🌙 SMA + VWAP FILTER STRATEGY - INITIAL RESULTS 🌙")
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
    vwap_period=[10, 20, 30, 50],
    vwap_buffer=[0.001, 0.002, 0.005],
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
print(f"VWAP Period: {optimization_results._strategy.vwap_period}")
print(f"VWAP Buffer: {optimization_results._strategy.vwap_buffer:.1%}")
print(f"Take Profit: {optimization_results._strategy.take_profit:.1%}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.1%}")

# Run with optimized parameters
optimized_stats = bt.run(
    sma_fast=optimization_results._strategy.sma_fast,
    sma_slow=optimization_results._strategy.sma_slow,
    vwap_period=optimization_results._strategy.vwap_period,
    vwap_buffer=optimization_results._strategy.vwap_buffer,
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

print("\n🏁 SMA + VWAP FILTER STRATEGY COMPLETE!")
print("VWAP filter helps align trades with institutional price levels.")