"""
Moon Dev Liquidation ADX Strategy - Long Only
==============================================
Uses Moon Dev API liquidation data with proper column headers

 Running backtest without ADX filter...

📊 Base Strategy Results:
Start                     2024-06-04 12:50:00
End                       2025-09-22 14:25:00
Duration                    475 days 01:35:00
Exposure Time [%]                    7.489402
Equity Final [$]                 116824.96842
Equity Peak [$]                  139302.17992
Return [%]                          16.824968
Buy & Hold Return [%]               65.820151
Return (Ann.) [%]                   12.664426
Volatility (Ann.) [%]               26.818024
Sharpe Ratio                         0.472236
Sortino Ratio                        1.310891
Calmar Ratio                         0.784876
Max. Drawdown [%]                  -16.135578
Avg. Drawdown [%]                     -1.7965
Max. Drawdown Duration      203 days 15:15:00
Avg. Drawdown Duration       10 days 08:05:00
# Trades                                   42
Win Rate [%]                        38.095238
Best Trade [%]                      28.346216
Worst Trade [%]                     -4.274145
Avg. Trade [%]                       0.637951
Max. Trade Duration           4 days 14:35:00
Avg. Trade Duration           0 days 20:15:00
Profit Factor                        1.532897
Expectancy [%]                       0.815399
SQN                                  0.605715
_strategy                 LiquidationStrategy
_equity_curve                             ...
_trades                       Size  EntryB...
dtype: object

📈 Base strategy backtest plot displayed

🚀 Moon Dev Strategy Optimization:
                                                                                                                                                                      
🏆 Best Parameters Found:
Start                     2024-06-04 12:50:00
End                       2025-09-22 14:25:00
Duration                    475 days 01:35:00
Exposure Time [%]                    5.233884
Equity Final [$]                 119633.08352
Equity Peak [$]                  143603.37398
Return [%]                          19.633084
Buy & Hold Return [%]               65.820151
Return (Ann.) [%]                   14.735258
Volatility (Ann.) [%]               25.391792
Sharpe Ratio                         0.580316
Sortino Ratio                        1.702202
Calmar Ratio                         0.882773
Max. Drawdown [%]                  -16.692011
Avg. Drawdown [%]                   -1.499901
Max. Drawdown Duration      296 days 23:05:00
Avg. Drawdown Duration       10 days 13:04:00
# Trades                                   38
Win Rate [%]                        36.842105
Best Trade [%]                      28.346216
Worst Trade [%]                      -3.59483
Avg. Trade [%]                       0.875679
Max. Trade Duration           4 days 14:35:00
Avg. Trade Duration           0 days 15:38:00
Profit Factor                        1.740128
Expectancy [%]                       1.061575
SQN                                  0.733916
_strategy                 LiquidationStrat...
_equity_curve                             ...
_trades                       Size  EntryB...
dtype: object

🎯 Moon Dev's Optimized Parameters:
ADX Threshold: 15
"""

import numpy as np
from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

class LiquidationStrategy(Strategy):
    # Strategy Parameters
    entry_liq_thresh = 5000000  # Entry liquidation threshold ($5M)
    exit_liq_thresh = 2000000   # Exit liquidation threshold ($2M)
    time_window_mins = 24       # Time window in minutes
    take_profit = 0.05         # Take profit percentage
    stop_loss = 0.03          # Stop loss percentage
    adx_period = 14           # ADX period
    adx_thresh = None         # ADX threshold, None to disable
    min_price = 100          # Minimum valid price to trade

    def init(self):
        # Split liquidations into long and short
        self.long_liqs = self.data.long_liquidations
        self.short_liqs = self.data.short_liquidations

        # Calculate ADX if threshold is set
        if self.adx_thresh is not None:
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

        # Calculate the 24-minute lookback window
        start_time = current_time - pd.Timedelta(minutes=self.time_window_mins)
        start_idx = np.searchsorted(self.data.index, start_time, side='left')

        # Verify window size
        window_size = current_idx - start_idx + 1
        if window_size > self.time_window_mins:
            start_idx = current_idx - self.time_window_mins + 1

        # Sum liquidations within window
        window_long_liqs = self.long_liqs[start_idx:current_idx + 1].sum()
        window_short_liqs = self.short_liqs[start_idx:current_idx + 1].sum()

        # Check if ADX condition is met
        adx_condition = True if self.adx_thresh is None else self.adx[-1] > self.adx_thresh

        price = self.data.Close[-1]

        # Skip if price too low
        if price < self.min_price:
            if self.position:
                self.position.close()
            return

        # Entry logic
        if not self.position:
            if window_long_liqs >= self.entry_liq_thresh and adx_condition:
                sl_price = price * (1 - self.stop_loss)
                tp_price = price * (1 + self.take_profit)
                self.buy(size=1, sl=sl_price, tp=tp_price)

        # Exit logic
        elif self.position and window_short_liqs >= self.exit_liq_thresh:
            self.position.close()

# Load and prepare data
print("🌙 Moon Dev Long-Only Liquidation Strategy (Moon Dev API Data) 🚀")
print("=" * 60)

# Load preprocessed BTC data - choose between 1-minute and 5-minute
# Just comment/uncomment to switch between timeframes

# Option 1: 1-minute data
# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_1m_ohlcv.csv'
# timeframe = '1-minute'

# Option 2: 5-minute data (currently active)
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
timeframe = '5-minute'

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

# No need for resampling - data is already in the correct format!

print("\n📈 Data Statistics:")
print(f"Total bars: {len(data):,}")
print(f"Total Long Liquidations: ${data['long_liquidations'].sum():,.2f}")
print(f"Total Short Liquidations: ${data['short_liquidations'].sum():,.2f}")
print(f"Max Long Liquidation per bar: ${data['long_liquidations'].max():,.2f}")
print(f"Max Short Liquidation per bar: ${data['short_liquidations'].max():,.2f}")
print(f"\nDate Range: {data.index[0]} to {data.index[-1]}")
print(f"Starting Price: ${data['Close'].iloc[0]:,.2f}")
print(f"Ending Price: ${data['Close'].iloc[-1]:,.2f}")

print(f"\n📊 Final data shape: {data.shape}")
print(f"Data ready for backtesting!")

# Create and configure the backtest
bt = Backtest(data, LiquidationStrategy, cash=100000, commission=0.002)

# First run without ADX
print("\n🚀 Running backtest without ADX filter...")
stats_no_adx = bt.run()
print("\n📊 Base Strategy Results:")
print(stats_no_adx)

# Plot the base results
bt.plot(filename=None)
print("\n📈 Base strategy backtest plot displayed")

# Run optimization
print("\n🚀 Moon Dev Strategy Optimization:")
stats_optimized = bt.optimize(
    adx_thresh=range(15, 36, 5),  # 15 to 35 step 5
    stop_loss=[i/100 for i in range(1, 6)],  # 1% to 5%
    take_profit=[i/100 for i in range(2, 12)],  # 2% to 11%
    maximize='Equity Final [$]',  # Changed from Sharpe Ratio to Equity Final
    constraint=lambda p: p.take_profit > p.stop_loss  # Ensure TP > SL
)

print("\n🏆 Best Parameters Found:")
print(stats_optimized)

# Print the optimized parameters in a clear format
print("\n🎯 Moon Dev's Optimized Parameters:")
print(f"ADX Threshold: {stats_optimized._strategy.adx_thresh}")
print(f"Stop Loss: {stats_optimized._strategy.stop_loss:.2%}")
print(f"Take Profit: {stats_optimized._strategy.take_profit:.2%}")

# Run and plot the optimized strategy
bt.plot(filename=None)