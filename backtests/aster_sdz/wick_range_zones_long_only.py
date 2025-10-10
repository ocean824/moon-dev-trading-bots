"""
ASTER Supply & Demand Zones - Wick Range Strategy (LONG ONLY)
==============================================================

Only buys at demand zones defined by lower wicks.
Demand zone: From close to bottom of wick
Never shorts, only accumulates at strong demand zones.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 ASTER Supply & Demand Zones - Wick Range LONG ONLY Strategy 🎯")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate demand zones from lower wicks
# Lower wick (demand zone)
data['Lower_Wick_Bottom'] = data['Low']
data['Lower_Wick_Top'] = np.minimum(data['Open'], data['Close'])
data['Lower_Wick_Size'] = data['Lower_Wick_Top'] - data['Lower_Wick_Bottom']

# Body size
data['Body_Size'] = abs(data['Close'] - data['Open'])

# Demand zone: Close to Low (best for green candles)
data['Demand_Zone_Top'] = np.where(
    data['Close'] > data['Open'],  # Green candle (bullish)
    data['Close'],  # Use close as top of demand zone
    data['Lower_Wick_Top']  # Red candle, use bottom of body
)
data['Demand_Zone_Bottom'] = data['Low']
data['Demand_Zone_Size'] = data['Demand_Zone_Top'] - data['Demand_Zone_Bottom']

# Zone strength metrics
data['Lower_Wick_Ratio'] = data['Lower_Wick_Size'] / (data['Body_Size'] + 0.00001)

# Strong demand zones criteria:
# 1. Large wick relative to body
# 2. Green candle with lower wick (hammer pattern)
# 3. Volume spike
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Spike'] = data['Volume'] > data['Volume_MA'] * 1.5

data['Hammer_Pattern'] = (
    (data['Close'] > data['Open']) &  # Green candle
    (data['Lower_Wick_Size'] > data['Body_Size'] * 2) &  # Long lower wick
    (data['Lower_Wick_Size'] > 0)
)

data['Strong_Demand_Zone'] = (
    (data['Lower_Wick_Ratio'] > 1.5) |  # Big wick ratio
    data['Hammer_Pattern'] |  # Hammer pattern
    (data['Volume_Spike'] & (data['Lower_Wick_Size'] > 0))  # Volume with wick
)

# Track recent strong demand zones
data['Recent_Demand_Top'] = data['Demand_Zone_Top'].where(data['Strong_Demand_Zone']).fillna(method='ffill')
data['Recent_Demand_Bottom'] = data['Demand_Zone_Bottom'].where(data['Strong_Demand_Zone']).fillna(method='ffill')

# Multiple demand zone levels for scaling in
data['Demand_Level_1'] = data['Recent_Demand_Top']  # Top of zone (conservative entry)
data['Demand_Level_2'] = data['Recent_Demand_Bottom'] + (data['Demand_Zone_Size'] * 0.5)  # Mid zone
data['Demand_Level_3'] = data['Recent_Demand_Bottom'] + (data['Demand_Zone_Size'] * 0.25)  # Deep in zone

# RSI for additional confirmation
data['RSI'] = ta.rsi(data['Close'], length=14)
data['Oversold'] = data['RSI'] < 35

print(f"✅ Loaded {len(data):,} bars")
print(f"📈 Strong demand zones: {data['Strong_Demand_Zone'].sum()}")
print(f"🔨 Hammer patterns: {data['Hammer_Pattern'].sum()}")
print(f"📊 Volume spikes with wicks: {(data['Volume_Spike'] & (data['Lower_Wick_Size'] > 0)).sum()}")
print(f"💧 Significant lower wicks: {(data['Lower_Wick_Ratio'] > 2).sum()}")


class WickRangeZonesLongOnly(Strategy):
    """
    LONG ONLY - Buy at demand zones defined by lower wicks
    """

    # Zone parameters
    min_wick_ratio = 1.0     # Minimum wick/body ratio for valid zone
    zone_validity_bars = 30  # How long a zone remains valid (longer for long-only)

    # Entry parameters
    scale_in = True          # Scale into positions
    max_entries = 3          # Maximum entries in one zone

    # Trade parameters
    take_profit = 0.025      # 2.5% TP
    stop_loss = 0.01         # 1% SL
    trailing_stop = 0.015    # 1.5% trailing

    # Position sizing
    base_size = 0.1          # 10% base size
    max_position = 0.3       # 30% max position

    def init(self):
        self.strong_demand = self.I(lambda: self.data.Strong_Demand_Zone)
        self.hammer = self.I(lambda: self.data.Hammer_Pattern)

        self.demand_top = self.I(lambda: self.data.Recent_Demand_Top)
        self.demand_bottom = self.I(lambda: self.data.Recent_Demand_Bottom)
        self.demand_level_1 = self.I(lambda: self.data.Demand_Level_1)
        self.demand_level_2 = self.I(lambda: self.data.Demand_Level_2)
        self.demand_level_3 = self.I(lambda: self.data.Demand_Level_3)

        self.lower_wick_ratio = self.I(lambda: self.data.Lower_Wick_Ratio)
        self.rsi = self.I(lambda: self.data.RSI)
        self.oversold = self.I(lambda: self.data.Oversold)

        # Track active zones and entries
        self.active_demand_zone = None
        self.zone_age = 0
        self.entries = []
        self.entry_prices = []
        self.avg_entry = None
        self.highest_price = None

    def next(self):
        if len(self.data) < 30:
            return

        price = self.data.Close[-1]

        # Update zone tracking
        if self.strong_demand[-1]:
            self.active_demand_zone = (
                self.demand_bottom[-1],
                self.demand_top[-1],
                self.demand_level_1[-1],
                self.demand_level_2[-1],
                self.demand_level_3[-1]
            )
            self.zone_age = 0
        else:
            self.zone_age += 1

        # Exit management (LONG ONLY)
        if self.position:
            # Update highest price for trailing
            if self.highest_price is None or price > self.highest_price:
                self.highest_price = price

            if self.avg_entry:
                pnl = (price - self.avg_entry) / self.avg_entry

                # Trailing stop
                if self.highest_price and price < self.highest_price * (1 - self.trailing_stop):
                    self.position.close()
                    self.reset_position()
                # Take profit
                elif pnl >= self.take_profit:
                    self.position.close()
                    self.reset_position()
                # Stop loss
                elif pnl <= -self.stop_loss:
                    self.position.close()
                    self.reset_position()

            return

        # Entry logic - LONG ONLY at demand zones
        if not self.position:
            # Check if we have an active valid demand zone
            if (self.active_demand_zone and
                self.zone_age < self.zone_validity_bars and
                pd.notna(self.active_demand_zone[0])):

                demand_bottom, demand_top, level_1, level_2, level_3 = self.active_demand_zone

                # Price must be within or near the demand zone
                if demand_bottom <= price <= demand_top * 1.02:  # Allow 2% above zone

                    # Determine entry size based on conditions
                    size = self.base_size

                    # Bonus size for special conditions
                    if self.hammer[-1]:
                        size *= 1.5  # 50% larger for hammer patterns

                    if self.oversold[-1]:
                        size *= 1.2  # 20% larger if oversold

                    if self.lower_wick_ratio[-1] > 3:
                        size *= 1.3  # 30% larger for huge wicks

                    # Cap at max position
                    size = min(size, self.max_position)

                    # Level-based entry (scale in at different levels)
                    entry_triggered = False

                    # First entry at top of zone (conservative)
                    if len(self.entries) == 0 and price <= level_1:
                        entry_triggered = True

                    # Second entry at mid zone
                    elif len(self.entries) == 1 and price <= level_2:
                        entry_triggered = True
                        size *= 0.75  # Smaller for second entry

                    # Third entry deep in zone
                    elif len(self.entries) == 2 and price <= level_3:
                        entry_triggered = True
                        size *= 0.5  # Even smaller for third entry

                    # Execute entry
                    if entry_triggered and len(self.entries) < self.max_entries:
                        # Check total position size
                        total_size = sum([e[1] for e in self.entries]) + size
                        if total_size <= self.max_position:
                            self.buy(size=size)
                            self.entries.append((price, size))
                            self.entry_prices.append(price)
                            self.update_avg_entry()

    def update_avg_entry(self):
        """Calculate weighted average entry price"""
        if self.entries:
            total_value = sum(price * size for price, size in self.entries)
            total_size = sum(size for _, size in self.entries)
            self.avg_entry = total_value / total_size if total_size > 0 else None

    def reset_position(self):
        """Reset all position tracking"""
        self.entries = []
        self.entry_prices = []
        self.avg_entry = None
        self.highest_price = None
        self.zone_age = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING WICK RANGE ZONES LONG ONLY BACKTEST")
print("="*70)

bt = Backtest(
    data,
    WickRangeZonesLongOnly,
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
        min_wick_ratio=[0.5, 1.0, 1.5],
        take_profit=[0.02, 0.025, 0.03],
        stop_loss=[0.008, 0.01, 0.012],
        trailing_stop=[0.01, 0.015, 0.02],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()