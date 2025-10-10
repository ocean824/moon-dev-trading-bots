"""
Moon Dev Liquidation ADX Strategy v2 - Combined Liquidations
============================================================
Uses Moon Dev API liquidation data with proper column headers
Combines all liquidations (both long and short) for signals
"""

import numpy as np
from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

class LiquidationStrategy(Strategy):
    entry_liq_thresh = 2000000  # Entry liquidation threshold
    exit_liq_thresh = 200000   # Exit liquidation threshold
    time_window_mins = 24       # Time window in minutes
    take_profit = 0.03        # Take profit percentage
    stop_loss = 0.05        # Stop loss percentage
    adx_period = 14           # ADX period
    adx_thresh = None         # ADX threshold, None to disable

    def init(self):
        self.liquidations = self.data.liquidations

        # Calculate ADX if threshold is set
        if self.adx_thresh is not None:
            # Calculate ADX using pandas_ta
            df = pd.DataFrame({
                'high': self.data.High,
                'low': self.data.Low,
                'close': self.data.Close
            })
            adx = df.ta.adx(length=self.adx_period)
            self.adx = self.I(lambda x: adx['ADX_14'], 'ADX')

    def next(self):
        current_idx = len(self.data.Close) - 1
        current_time = self.data.index[current_idx]

        # Define the start time of the window
        start_time = current_time - pd.Timedelta(minutes=self.time_window_mins)

        # Find indices for slicing
        start_idx = np.searchsorted(self.data.index, start_time, side='left')

        # Sum liquidations within the time window
        recent_liquidations = self.liquidations[start_idx:current_idx + 1].sum()

        # Check if ADX condition is met or ADX is disabled
        adx_condition = True if self.adx_thresh is None else self.adx[-1] > self.adx_thresh

        # Entry logic - if no position and conditions are met
        if not self.position and recent_liquidations >= self.entry_liq_thresh and adx_condition:
            self.buy(sl=self.data.Close[-1] * (1 - self.stop_loss),
                    tp=self.data.Close[-1] * (1 + self.take_profit))

        # Exit logic - if in position and liquidations exceed exit threshold
        elif self.position and recent_liquidations >= self.exit_liq_thresh:
            self.position.close()

print("🌙 Moon Dev Liquidation Strategy v2 (Moon Dev API Data) 🚀")
print("=" * 60)

# Load preprocessed BTC data - choose between 1-minute and 5-minute
# Just comment/uncomment to switch between timeframes

# Option 1: 1-minute data (currently active)
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_1m_ohlcv.csv'
timeframe = '1-minute'

# Option 2: 5-minute data
# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
# timeframe = '5-minute'

print(f"\n📊 Loading preprocessed {timeframe} Moon Dev liquidation data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

print(f"✅ Loaded {len(data):,} {timeframe} bars")
print("\n📊 Data Sample:")
print(data.head())

# The preprocessed data already has these columns:
# - Open, High, Low, Close (OHLCV data)
# - total_liquidations (sum of all liquidations)
# - long_liquidations (long position liquidations)
# - short_liquidations (short position liquidations)
# - liquidation_count (number of liquidations in that bar)

# For this strategy, we use combined liquidations
data['liquidations'] = data['total_liquidations']

print("\n📈 Data Statistics:")
print(f"Total bars: {len(data):,}")
print(f"Total Liquidations: ${data['liquidations'].sum():,.2f}")
print(f"Max Liquidation per bar: ${data['liquidations'].max():,.2f}")
print(f"Average Liquidation per bar: ${data['liquidations'].mean():,.2f}")
print(f"\nDate Range: {data.index[0]} to {data.index[-1]}")
print(f"Starting Price: ${data['Close'].iloc[0]:,.2f}")
print(f"Ending Price: ${data['Close'].iloc[-1]:,.2f}")

# Create and configure the backtest
bt = Backtest(data, LiquidationStrategy, cash=100000, commission=0.002)

# First run without ADX
print("\n🚀 Running backtest without ADX filter...")
stats_no_adx = bt.run()
print("\n📊 Results without ADX:")
print(stats_no_adx)

# Run with ADX
print("\n🚀 Running backtest with ADX filter (threshold=25)...")
stats_with_adx = bt.run(adx_thresh=25)
print("\n📊 Results with ADX:")
print(stats_with_adx)

# Optimization
print("\n⚡ Running optimization...")
print("This may take several minutes due to large parameter space...")

optimization_results = bt.optimize(
    entry_liq_thresh=range(1000000, 10000000, 1000000),  # Entry threshold from 1M to 10M
    exit_liq_thresh=range(500000, 5000000, 500000),      # Exit threshold from 500k to 5M
    time_window_mins=range(10, 60, 5),                    # Time window from 10 to 60 mins
    take_profit=[i / 100 for i in range(1, 7)],          # Take profit from 1% to 6%
    stop_loss=[i / 100 for i in range(1, 7)],            # Stop loss from 1% to 6%
    adx_thresh=[None, 20, 25, 30, 35],                   # Test different ADX thresholds including None
    maximize='Equity Final [$]',
    constraint=lambda p: p.exit_liq_thresh <= p.entry_liq_thresh  # Exit threshold must be <= Entry threshold
)

# Print the optimization results
print("\n🏆 Optimization Results:")
print(optimization_results)

print("\n✨ Best Parameters:")
print(f"Entry Liquidation Threshold: ${optimization_results._strategy.entry_liq_thresh:,}")
print(f"Exit Liquidation Threshold: ${optimization_results._strategy.exit_liq_thresh:,}")
print(f"Time Window (minutes): {optimization_results._strategy.time_window_mins}")
print(f"Take Profit: {optimization_results._strategy.take_profit:.2%}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.2%}")
print(f"ADX Threshold: {optimization_results._strategy.adx_thresh}")

# Plot the results
bt.plot(filename=None)  # Don't save the plot, just display it
print("\n📈 Backtest plot displayed")