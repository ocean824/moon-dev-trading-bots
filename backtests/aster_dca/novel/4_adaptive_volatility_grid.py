"""
NOVEL DCA #4: Adaptive Volatility Grid
=======================================

Grid that dynamically adjusts spacing based on realized volatility.
Tighter grid in low volatility (accumulation), wider in high volatility (panic).
Superior to fixed grid because it adapts to market conditions.

Key Innovation: Uses rolling volatility to optimize grid density in real-time.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #4: Adaptive Volatility Grid 🚀")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate volatility metrics
data['Returns'] = data['Close'].pct_change()
data['Volatility'] = data['Returns'].rolling(20).std()
data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=14)
data['ATR_Pct'] = data['ATR'] / data['Close']

# Volatility regimes
data['Vol_Percentile'] = data['Volatility'].rolling(100).rank(pct=True)
data['Low_Vol'] = data['Vol_Percentile'] < 0.3
data['High_Vol'] = data['Vol_Percentile'] > 0.7

# Price position in range
data['High_20'] = data['High'].rolling(20).max()
data['Low_20'] = data['Low'].rolling(20).min()
data['Position_in_Range'] = (data['Close'] - data['Low_20']) / (data['High_20'] - data['Low_20'])

print(f"✅ Loaded {len(data):,} bars")
print(f"📊 Avg volatility: {data['Volatility'].mean():.4%}")
print(f"📉 Low vol periods: {data['Low_Vol'].sum()} bars")
print(f"📈 High vol periods: {data['High_Vol'].sum()} bars")


class AdaptiveVolatilityGrid(Strategy):
    """
    Grid that adapts spacing to volatility
    """

    # Grid parameters
    base_grid_levels = 5
    base_spacing_pct = 0.005    # 0.5% base spacing

    # Volatility adjustments
    low_vol_multiplier = 0.5    # Tighter grid in low vol (0.25% spacing)
    high_vol_multiplier = 2.0   # Wider grid in high vol (1% spacing)

    # Dynamic sizing
    base_size = 0.02             # 2% base position
    vol_size_adjust = True       # Larger positions in low vol

    # Exit parameters
    take_profit = 0.08
    stop_loss = 0.20

    max_position_pct = 0.15

    def init(self):
        self.volatility = self.I(lambda: self.data.Volatility)
        self.vol_percentile = self.I(lambda: self.data.Vol_Percentile)
        self.atr_pct = self.I(lambda: self.data.ATR_Pct)
        self.position_in_range = self.I(lambda: self.data.Position_in_Range)

        # Grid state
        self.grid_levels = []
        self.grid_entries = {}
        self.avg_entry = None
        self.last_grid_update = None
        self.current_spacing = self.base_spacing_pct

    def next(self):
        if len(self.data) < 100:
            return

        price = self.data.Close[-1]
        vol = self.volatility[-1]
        vol_pct = self.vol_percentile[-1]
        atr_pct = self.atr_pct[-1]
        pos_in_range = self.position_in_range[-1]

        if pd.isna(vol) or pd.isna(vol_pct):
            return

        # Exit logic
        if self.position:
            if self.avg_entry:
                pnl = (price - self.avg_entry) / self.avg_entry

                if pnl >= self.take_profit:
                    self.position.close()
                    self.reset_grid()
                elif pnl <= -self.stop_loss:
                    self.position.close()
                    self.reset_grid()
            return

        # Update grid spacing based on volatility
        self.update_grid_spacing(vol_pct, atr_pct)

        # Grid management
        if not self.position:
            # Only trade in lower half of range
            if pd.notna(pos_in_range) and pos_in_range < 0.5:
                # Setup or update grid
                if not self.grid_levels or self.should_update_grid(price):
                    self.setup_adaptive_grid(price, vol_pct)

                # Check for grid fills
                self.check_grid_fills(price, vol_pct)

    def update_grid_spacing(self, vol_percentile, atr_pct):
        """Adjust grid spacing based on volatility"""
        if vol_percentile < 0.3:
            # Low volatility - tighter grid
            self.current_spacing = self.base_spacing_pct * self.low_vol_multiplier
        elif vol_percentile > 0.7:
            # High volatility - wider grid
            self.current_spacing = self.base_spacing_pct * self.high_vol_multiplier
        else:
            # Normal volatility
            self.current_spacing = self.base_spacing_pct

        # Additional ATR adjustment
        if pd.notna(atr_pct):
            self.current_spacing = max(self.current_spacing, atr_pct * 0.5)

    def setup_adaptive_grid(self, price, vol_percentile):
        """Setup grid with adaptive spacing"""
        self.grid_levels = []
        self.last_grid_update = price

        for i in range(self.base_grid_levels):
            level_price = price * (1 - self.current_spacing * (i + 1))
            self.grid_levels.append(level_price)

    def should_update_grid(self, price):
        """Check if grid needs updating"""
        if self.last_grid_update is None:
            return True

        price_move = abs(price - self.last_grid_update) / self.last_grid_update
        return price_move > self.current_spacing * 2

    def check_grid_fills(self, price, vol_percentile):
        """Check if price hits grid levels"""
        for level_price in self.grid_levels:
            if level_price not in self.grid_entries:
                if price <= level_price:
                    # Adjust size based on volatility
                    if self.vol_size_adjust:
                        if vol_percentile < 0.3:
                            size = self.base_size * 1.5  # Larger in low vol
                        elif vol_percentile > 0.7:
                            size = self.base_size * 0.7  # Smaller in high vol
                        else:
                            size = self.base_size
                    else:
                        size = self.base_size

                    self.buy(size=size)
                    self.grid_entries[level_price] = size
                    self.update_avg_entry()
                    break  # One fill per bar

    def update_avg_entry(self):
        if self.grid_entries:
            total_val = sum(p * s for p, s in self.grid_entries.items())
            total_size = sum(self.grid_entries.values())
            self.avg_entry = total_val / total_size if total_size > 0 else None

    def reset_grid(self):
        self.grid_levels = []
        self.grid_entries = {}
        self.avg_entry = None
        self.last_grid_update = None


# Run backtest
print("\n" + "="*70)
print("RUNNING ADAPTIVE VOLATILITY GRID BACKTEST")
print("="*70)

bt = Backtest(
    data,
    AdaptiveVolatilityGrid,
    cash=10000,
    commission=0.001,
    exclusive_orders=True
)

stats = bt.run()
print(f"\n📊 RESULTS:")
print(stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING PARAMETERS")
print("="*70)

try:
    opt = bt.optimize(
        base_grid_levels=[3, 5, 7],
        base_spacing_pct=[0.003, 0.005, 0.007],
        take_profit=[0.06, 0.08, 0.10],
        stop_loss=[0.15, 0.20, 0.25],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()