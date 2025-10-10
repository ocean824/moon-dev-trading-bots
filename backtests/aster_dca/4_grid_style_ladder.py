"""
ASTER DCA STRATEGY #4: Grid-style DCA Ladder
============================================

Logic: Always maintain a rolling ladder of bids every 0.5–1% below current price.
Layering: Continuous refresh — as price rises and fills TPs, new bids re-populate below.
Exit: TP at 5–10% above each entry, SL optional (or global kill switch if 20–30% down).

Pure "market maker" style — harvests chop if exchange props up the bid.
Works best in range-bound, mean reverting token.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 ASTER DCA STRATEGY #4: Grid-style DCA Ladder 🎯")
print("=" * 70)

# Data source selection (comment/uncomment as needed)
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate range indicators
data['High_20'] = data['High'].rolling(20).max()
data['Low_20'] = data['Low'].rolling(20).min()
data['Range_Pct'] = (data['High_20'] - data['Low_20']) / data['Low_20'] * 100
data['Position_in_Range'] = (data['Close'] - data['Low_20']) / (data['High_20'] - data['Low_20'])

print(f"✅ Loaded {len(data):,} bars")
print(f"📈 Price range: ${data['Close'].min():.4f} - ${data['Close'].max():.4f}")
print(f"📊 Average 20-bar range: {data['Range_Pct'].mean():.2f}%")


class GridStyleDCA(Strategy):
    """
    Maintain a constant grid of buy orders below price
    """

    # Grid parameters
    grid_levels = 5           # Number of grid levels
    grid_spacing = 0.007      # 0.7% spacing between levels
    grid_size = 0.02          # 2% of capital per grid level

    # Exit parameters
    take_profit = 0.08        # 8% TP per position
    global_stop = 0.30        # 30% portfolio stop loss

    # Grid management
    refresh_threshold = 0.02  # Refresh grid when price moves 2%

    def init(self):
        self.position_in_range = self.I(lambda: self.data.Position_in_Range)

        # Track grid state
        self.grid_entries = {}  # Dict of entry_price: size
        self.last_grid_price = None
        self.total_invested = 0
        self.avg_entry = None

    def next(self):
        if len(self.data) < 30:
            return

        price = self.data.Close[-1]
        pos_in_range = self.position_in_range[-1]

        # Global stop loss check
        if self.position and self.avg_entry is not None:
            portfolio_pnl = (price - self.avg_entry) / self.avg_entry
            if portfolio_pnl <= -self.global_stop:
                self.position.close()
                self.reset_grid()
                return

        # Individual position take profits
        if self.grid_entries:
            for entry_price in list(self.grid_entries.keys()):
                pnl = (price - entry_price) / entry_price
                if pnl >= self.take_profit:
                    # Take profit on this grid level
                    # In real implementation, would close specific position
                    # For backtest, we'll track it differently
                    del self.grid_entries[entry_price]
                    self.update_avg_entry()

        # Grid management
        if self.should_refresh_grid(price):
            self.setup_grid(price)

        # Execute grid orders
        self.check_grid_fills(price)

    def should_refresh_grid(self, price):
        """Check if grid needs refreshing"""
        if self.last_grid_price is None:
            return True

        price_move = abs(price - self.last_grid_price) / self.last_grid_price
        return price_move >= self.refresh_threshold

    def setup_grid(self, price):
        """Setup or refresh the grid"""
        self.last_grid_price = price

        # Don't add more if we're already heavily invested
        if self.total_invested >= self.grid_levels * self.grid_size:
            return

    def check_grid_fills(self, price):
        """Check if price hits any grid level"""
        if not self.position:
            # Place first grid order if price is in lower half of range
            pos_in_range = self.position_in_range[-1]
            if pd.notna(pos_in_range) and pos_in_range < 0.5:
                # Start grid
                for i in range(self.grid_levels):
                    grid_price = price * (1 - self.grid_spacing * i)
                    if price <= grid_price and grid_price not in self.grid_entries:
                        # Execute this grid level
                        self.buy(size=self.grid_size)
                        self.grid_entries[grid_price] = self.grid_size
                        self.total_invested += self.grid_size
                        self.update_avg_entry()
                        break  # Only one order per bar

    def update_avg_entry(self):
        """Calculate weighted average entry"""
        if self.grid_entries:
            total_value = sum(price * size for price, size in self.grid_entries.items())
            total_size = sum(self.grid_entries.values())
            self.avg_entry = total_value / total_size if total_size > 0 else None
        else:
            self.avg_entry = None

    def reset_grid(self):
        """Reset grid state"""
        self.grid_entries = {}
        self.last_grid_price = None
        self.total_invested = 0
        self.avg_entry = None


# Run backtest
print("\n" + "="*70)
print("RUNNING GRID-STYLE DCA LADDER BACKTEST")
print("="*70)

bt = Backtest(
    data,
    GridStyleDCA,
    cash=10000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 BASELINE RESULTS:")
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING GRID PARAMETERS")
print("="*70)

try:
    optimization_results = bt.optimize(
        grid_levels=[3, 5, 7],
        grid_spacing=[0.005, 0.007, 0.010],
        take_profit=[0.05, 0.08, 0.10, 0.12],
        global_stop=[0.25, 0.30, 0.35],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS:")
    print(f"Grid Levels: {optimization_results._strategy.grid_levels}")
    print(f"Grid Spacing: {optimization_results._strategy.grid_spacing*100}%")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100}%")
    print(f"Global Stop: {optimization_results._strategy.global_stop*100}%")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()