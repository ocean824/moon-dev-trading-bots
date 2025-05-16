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
print("🌙 Moon Dev Long-Only Liquidation Strategy Backtest 🚀")
print("=" * 60)

# Load the data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/bots/hyperliquid/data/liqs/BTC_liquidations_20250516_085538.csv'
data = pd.read_csv(data_path)

print("\n📊 Raw Data Sample:")
print(data.head())

# Convert 'datetime' column to datetime format and set as index
data['datetime'] = pd.to_datetime(data['datetime'])
data.set_index('datetime', inplace=True)

# Create separate columns for long and short liquidations
data['long_liquidations'] = np.where(data['LIQ_SIDE'] == 'SELL', data['usd_size'], 0)  # When longs get liquidated
data['short_liquidations'] = np.where(data['LIQ_SIDE'] == 'BUY', data['usd_size'], 0)  # When shorts get liquidated

print("\n💰 Liquidation Stats Before Resampling:")
print(f"Total Long Liquidations: ${data['long_liquidations'].sum():,.2f}")
print(f"Total Short Liquidations: ${data['short_liquidations'].sum():,.2f}")
print(f"Max Single Long Liquidation: ${data['long_liquidations'].max():,.2f}")
print(f"Max Single Short Liquidation: ${data['short_liquidations'].max():,.2f}")

# Ensure necessary columns are present
data = data[['price', 'long_liquidations', 'short_liquidations']]

# Create required columns for the backtest
data['Open'] = data['price']
data['High'] = data['price']
data['Low'] = data['price']
data['Close'] = data['price']

# Remove any rows with prices below minimum threshold
min_price = 100
data = data[data['price'] >= min_price]

# Aggregate data by minute
data = data.resample('T').agg({
    'price': 'mean',
    'long_liquidations': 'sum',
    'short_liquidations': 'sum',
    'Open': 'first',
    'High': 'max',
    'Low': 'min',
    'Close': 'last'
})

print("\n📈 Data Stats After Resampling:")
print(f"Total Minutes: {len(data)}")
print(f"Total Long Liquidations: ${data['long_liquidations'].sum():,.2f}")
print(f"Total Short Liquidations: ${data['short_liquidations'].sum():,.2f}")
print(f"Max Long Liquidation per Minute: ${data['long_liquidations'].max():,.2f}")
print(f"Max Short Liquidation per Minute: ${data['short_liquidations'].max():,.2f}")
print(f"Average Long Liquidation per Minute: ${data['long_liquidations'].mean():,.2f}")
print(f"Average Short Liquidation per Minute: ${data['short_liquidations'].mean():,.2f}")
print(f"\nDate Range: {data.index[0]} to {data.index[-1]}")
print(f"Starting Price: ${data['Close'][0]:,.2f}")
print(f"Ending Price: ${data['Close'][-1]:,.2f}")

# Forward fill price-related columns
price_columns = ['price', 'Open', 'High', 'Low', 'Close']
data[price_columns] = data[price_columns].ffill()

# Fill NaN liquidations with 0
data['long_liquidations'].fillna(0, inplace=True)
data['short_liquidations'].fillna(0, inplace=True)

# Check for any remaining NaN values
nan_check = data.isna().sum()
if nan_check.sum() > 0:
    print("\n⚠️ Warning: NaN values found:")
    print(nan_check[nan_check > 0])

# Ensure the DataFrame is sorted by the index
data.sort_index(inplace=True)

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
