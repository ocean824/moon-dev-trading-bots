"""
ASTER Supply & Demand Zones - Wick Range Strategy (Long/Short)
===============================================================

Supply zone: From close to top of wick (or bottom to top of wick)
Demand zone: From close to bottom of wick
Trades within these precise wick-defined zones.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 ASTER Supply & Demand Zones - Wick Range Strategy 🎯")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate wick zones
# Upper wick (supply zone)
data['Upper_Wick_Top'] = data['High']
data['Upper_Wick_Bottom'] = np.maximum(data['Open'], data['Close'])
data['Upper_Wick_Size'] = data['Upper_Wick_Top'] - data['Upper_Wick_Bottom']

# Lower wick (demand zone)
data['Lower_Wick_Bottom'] = data['Low']
data['Lower_Wick_Top'] = np.minimum(data['Open'], data['Close'])
data['Lower_Wick_Size'] = data['Lower_Wick_Top'] - data['Lower_Wick_Bottom']

# Body size
data['Body_Size'] = abs(data['Close'] - data['Open'])

# Significant wicks (wick > body)
data['Significant_Upper_Wick'] = data['Upper_Wick_Size'] > data['Body_Size']
data['Significant_Lower_Wick'] = data['Lower_Wick_Size'] > data['Body_Size']

# Supply zone: Close to High (for red candles) or full upper wick
data['Supply_Zone_Top'] = data['High']
data['Supply_Zone_Bottom'] = np.where(
    data['Close'] < data['Open'],  # Red candle
    data['Close'],  # Use close as bottom
    data['Upper_Wick_Bottom']  # Green candle, use top of body
)

# Demand zone: Close to Low (for green candles) or full lower wick
data['Demand_Zone_Top'] = np.where(
    data['Close'] > data['Open'],  # Green candle
    data['Close'],  # Use close as top
    data['Lower_Wick_Top']  # Red candle, use bottom of body
)
data['Demand_Zone_Bottom'] = data['Low']

# Zone strength based on wick ratio
data['Upper_Wick_Ratio'] = data['Upper_Wick_Size'] / (data['Body_Size'] + 0.00001)
data['Lower_Wick_Ratio'] = data['Lower_Wick_Size'] / (data['Body_Size'] + 0.00001)

# Strong zones have big wicks
data['Strong_Supply_Zone'] = (data['Upper_Wick_Ratio'] > 2) & (data['Upper_Wick_Size'] > 0)
data['Strong_Demand_Zone'] = (data['Lower_Wick_Ratio'] > 2) & (data['Lower_Wick_Size'] > 0)

# Track recent strong zones
data['Recent_Supply_Top'] = data['Supply_Zone_Top'].where(data['Strong_Supply_Zone']).fillna(method='ffill')
data['Recent_Supply_Bottom'] = data['Supply_Zone_Bottom'].where(data['Strong_Supply_Zone']).fillna(method='ffill')
data['Recent_Demand_Top'] = data['Demand_Zone_Top'].where(data['Strong_Demand_Zone']).fillna(method='ffill')
data['Recent_Demand_Bottom'] = data['Demand_Zone_Bottom'].where(data['Strong_Demand_Zone']).fillna(method='ffill')

print(f"✅ Loaded {len(data):,} bars")
print(f"📊 Strong supply zones: {data['Strong_Supply_Zone'].sum()}")
print(f"📈 Strong demand zones: {data['Strong_Demand_Zone'].sum()}")
print(f"🔥 Significant upper wicks: {data['Significant_Upper_Wick'].sum()}")
print(f"💧 Significant lower wicks: {data['Significant_Lower_Wick'].sum()}")


class WickRangeZones(Strategy):
    """
    Trade within wick-defined supply and demand zones
    """

    # Zone parameters
    min_wick_ratio = 1.5     # Minimum wick/body ratio for valid zone
    zone_validity_bars = 20  # How long a zone remains valid

    # Entry parameters
    entry_pct_in_zone = 0.5  # Enter at 50% of zone range

    # Trade parameters
    take_profit = 0.02       # 2% TP
    stop_loss = 0.008        # 0.8% SL

    # Position sizing
    size_pct = 0.2           # 20% per trade

    def init(self):
        self.strong_supply = self.I(lambda: self.data.Strong_Supply_Zone)
        self.strong_demand = self.I(lambda: self.data.Strong_Demand_Zone)

        self.recent_supply_top = self.I(lambda: self.data.Recent_Supply_Top)
        self.recent_supply_bottom = self.I(lambda: self.data.Recent_Supply_Bottom)
        self.recent_demand_top = self.I(lambda: self.data.Recent_Demand_Top)
        self.recent_demand_bottom = self.I(lambda: self.data.Recent_Demand_Bottom)

        self.upper_wick_ratio = self.I(lambda: self.data.Upper_Wick_Ratio)
        self.lower_wick_ratio = self.I(lambda: self.data.Lower_Wick_Ratio)

        # Track active zones
        self.active_supply_zone = None
        self.active_demand_zone = None
        self.zone_age = 0
        self.entry_price = None

    def next(self):
        if len(self.data) < 20:
            return

        price = self.data.Close[-1]

        # Update zone tracking
        if self.strong_supply[-1]:
            self.active_supply_zone = (self.recent_supply_bottom[-1], self.recent_supply_top[-1])
            self.zone_age = 0

        if self.strong_demand[-1]:
            self.active_demand_zone = (self.recent_demand_bottom[-1], self.recent_demand_top[-1])
            self.zone_age = 0

        self.zone_age += 1

        # Exit management
        if self.position:
            if self.entry_price:
                # Long exit
                if self.position.is_long:
                    if price >= self.entry_price * (1 + self.take_profit):
                        self.position.close()
                        self.entry_price = None
                    elif price <= self.entry_price * (1 - self.stop_loss):
                        self.position.close()
                        self.entry_price = None

                # Short exit
                elif self.position.is_short:
                    if price <= self.entry_price * (1 - self.take_profit):
                        self.position.close()
                        self.entry_price = None
                    elif price >= self.entry_price * (1 + self.stop_loss):
                        self.position.close()
                        self.entry_price = None
            return

        # Entry logic - trade within zones
        if not self.position:
            # Check if price is in active supply zone (sell zone)
            if (self.active_supply_zone and
                self.zone_age < self.zone_validity_bars and
                pd.notna(self.active_supply_zone[0])):

                supply_bottom, supply_top = self.active_supply_zone

                # Price entering supply zone from below
                if supply_bottom <= price <= supply_top:
                    # Calculate entry point within zone
                    zone_range = supply_top - supply_bottom
                    if zone_range > 0:
                        entry_level = supply_bottom + (zone_range * self.entry_pct_in_zone)

                        # Enter short if price is at or above entry level
                        if price >= entry_level:
                            self.sell(size=self.size_pct)
                            self.entry_price = price

            # Check if price is in active demand zone (buy zone)
            elif (self.active_demand_zone and
                  self.zone_age < self.zone_validity_bars and
                  pd.notna(self.active_demand_zone[0])):

                demand_bottom, demand_top = self.active_demand_zone

                # Price entering demand zone from above
                if demand_bottom <= price <= demand_top:
                    # Calculate entry point within zone
                    zone_range = demand_top - demand_bottom
                    if zone_range > 0:
                        entry_level = demand_top - (zone_range * self.entry_pct_in_zone)

                        # Enter long if price is at or below entry level
                        if price <= entry_level:
                            self.buy(size=self.size_pct)
                            self.entry_price = price


# Run backtest
print("\n" + "="*70)
print("RUNNING WICK RANGE ZONES BACKTEST")
print("="*70)

bt = Backtest(
    data,
    WickRangeZones,
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
        min_wick_ratio=[1.0, 1.5, 2.0],
        entry_pct_in_zone=[0.3, 0.5, 0.7],
        take_profit=[0.015, 0.02, 0.025],
        stop_loss=[0.006, 0.008, 0.01],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()