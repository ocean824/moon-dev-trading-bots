import numpy as np
from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

class LiquidationStrategy(Strategy):
    entry_liq_thresh = 5000000  # Entry liquidation threshold
    exit_liq_thresh = 2000000   # Exit liquidation threshold
    time_window_mins = 24       # Time window in minutes
    take_profit = 0.1        # Take profit percentage
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

print("🌙 Moon Dev Liquidation Strategy Backtest 🚀")
print("=" * 60)

# Load the data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_full.csv'
data = pd.read_csv(data_path)

# Convert 'datetime' column to datetime format and set as index
data['datetime'] = pd.to_datetime(data['datetime'])
data.set_index('datetime', inplace=True)

# Ensure necessary columns are present
data = data[['price', 'LIQ_SIDE', 'usd_size']]

# Create required columns for the backtest to run
data['Open'] = data['price']
data['High'] = data['price']
data['Low'] = data['price']
data['Close'] = data['price']

# Aggregate data by minute to handle duplicates
data = data.resample('T').agg({
    'price': 'mean',
    'LIQ_SIDE': 'first',
    'usd_size': 'sum',
    'Open': 'first',
    'High': 'max',
    'Low': 'min',
    'Close': 'last'
})

# Forward fill price-related columns
price_columns = ['price', 'Open', 'High', 'Low', 'Close']
data[price_columns] = data[price_columns].ffill()

# Set usd_size to 0 for missing data
data['usd_size'].fillna(0, inplace=True)

# Add a new column 'liquidations' to store preprocessed liquidations data
data['liquidations'] = data['usd_size']

# Ensure the DataFrame is sorted by the index
data.sort_index(inplace=True)

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
optimization_results = bt.optimize(
    entry_liq_thresh=range(1000000, 10000000, 1000000),  # Entry threshold from 1M to 10M
    exit_liq_thresh=range(500000, 5000000, 500000),      # Exit threshold from 500k to 5M
    time_window_mins=range(10, 60, 5),                    # Time window from 10 to 60 mins
    take_profit=[i / 100 for i in range(1, 7)],          # Take profit from 1% to 5%
    stop_loss=[i / 100 for i in range(1, 7)],            # Stop loss from 1% to 5%
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

"""
💡 About ADX and Its Potential Role in This Strategy:

The Average Directional Index (ADX) could be valuable to this liquidation strategy for several reasons:

1. Trend Strength Confirmation:
   - ADX measures trend strength regardless of direction (0-100 scale)
   - Values > 25 indicate a strong trend
   - Could help avoid false signals during choppy markets

2. Potential Implementation:
   - Primary Entry Filter: Only take liquidation signals when ADX > 25
   - Dynamic Position Sizing: Increase position size when ADX is higher
   - Exit Confirmation: Exit early if ADX weakens significantly

3. Specific Use Cases:
   - When large liquidations occur in a strong trend (high ADX), it often indicates trend continuation
   - In weak trends (low ADX), large liquidations might just be noise
   - Could help avoid getting trapped in ranging markets

4. Suggested Implementation After Testing Base Strategy:
   - Add ADX > 25 requirement for entries
   - Scale position size: 100% when ADX > 30, 50% when ADX 25-30
   - Early exit if ADX drops below 20
   - Optimize these thresholds based on historical data

5. Risk Management:
   - ADX can help avoid trading during low-conviction periods
   - Particularly useful in crypto where high volatility can create false liquidation signals

The current removal of ADX is temporary to establish a baseline for the pure liquidation strategy.
Once we see how the liquidation signals perform alone, we can add ADX back as a filter.
"""
