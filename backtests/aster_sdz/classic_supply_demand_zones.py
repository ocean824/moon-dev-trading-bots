"""
ASTER Supply & Demand Zones - Classic Strategy
==============================================

Classic supply and demand zone detection with zone strength scoring.
Trades bounces off strong zones with proper risk management.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 ASTER Supply & Demand Zones - Classic Strategy 🎯")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Supply and Demand Zone Detection
def identify_zones(df, lookback=20, min_touches=2):
    """Identify supply and demand zones"""
    zones = {'demand': [], 'supply': []}

    # Rolling highs and lows
    df['Swing_High'] = df['High'].rolling(lookback).max()
    df['Swing_Low'] = df['Low'].rolling(lookback).min()

    # Identify turning points
    df['Is_Peak'] = (df['High'] == df['Swing_High'])
    df['Is_Valley'] = (df['Low'] == df['Swing_Low'])

    # Zone strength based on volume
    df['Volume_MA'] = df['Volume'].rolling(20).mean()
    df['Strong_Volume'] = df['Volume'] > df['Volume_MA'] * 1.5

    return df

data = identify_zones(data)

# Zone scoring
data['Zone_Strength'] = 0

# Demand zone (support)
data['Near_Support'] = abs(data['Close'] - data['Swing_Low']) / data['Close'] < 0.005
data['Demand_Zone'] = data['Near_Support'] & (data['Close'] > data['Open'])

# Supply zone (resistance)
data['Near_Resistance'] = abs(data['Close'] - data['Swing_High']) / data['Close'] < 0.005
data['Supply_Zone'] = data['Near_Resistance'] & (data['Close'] < data['Open'])

# Zone strength scoring
data['Zone_Score'] = (
    data['Demand_Zone'].astype(int) * 2 +
    data['Supply_Zone'].astype(int) * -2 +
    data['Strong_Volume'].astype(int)
)

print(f"✅ Loaded {len(data):,} bars")
print(f"📊 Demand zones identified: {data['Demand_Zone'].sum()}")
print(f"📈 Supply zones identified: {data['Supply_Zone'].sum()}")


class ClassicSupplyDemandZones(Strategy):
    """
    Trade bounces off supply and demand zones
    """

    # Zone parameters
    lookback = 20
    zone_buffer = 0.003      # 0.3% buffer around zones
    min_zone_strength = 1    # Minimum strength to trade

    # Trade parameters
    take_profit = 0.015      # 1.5% TP
    stop_loss = 0.008        # 0.8% SL

    # Position sizing
    size_pct = 0.1          # 10% per trade

    def init(self):
        self.swing_high = self.I(lambda: self.data.Swing_High)
        self.swing_low = self.I(lambda: self.data.Swing_Low)
        self.demand_zone = self.I(lambda: self.data.Demand_Zone)
        self.supply_zone = self.I(lambda: self.data.Supply_Zone)
        self.zone_score = self.I(lambda: self.data.Zone_Score)

        # Track zones
        self.current_demand = None
        self.current_supply = None
        self.zone_touches = 0
        self.entry_price = None

    def next(self):
        if len(self.data) < self.lookback:
            return

        price = self.data.Close[-1]
        high = self.swing_high[-1]
        low = self.swing_low[-1]
        is_demand = self.demand_zone[-1]
        is_supply = self.supply_zone[-1]
        zone_str = self.zone_score[-1]

        if pd.isna(high) or pd.isna(low):
            return

        # Update current zones
        if is_demand:
            self.current_demand = low
            self.zone_touches = 0

        if is_supply:
            self.current_supply = high
            self.zone_touches = 0

        # Exit management
        if self.position:
            # Long exit
            if self.position.is_long and self.entry_price:
                if price >= self.entry_price * (1 + self.take_profit):
                    self.position.close()
                    self.entry_price = None
                elif price <= self.entry_price * (1 - self.stop_loss):
                    self.position.close()
                    self.entry_price = None

            # Short exit
            elif self.position.is_short and self.entry_price:
                if price <= self.entry_price * (1 - self.take_profit):
                    self.position.close()
                    self.entry_price = None
                elif price >= self.entry_price * (1 + self.stop_loss):
                    self.position.close()
                    self.entry_price = None

            return

        # Entry logic
        if not self.position:
            # Buy at demand zone
            if self.current_demand and abs(zone_str) >= self.min_zone_strength:
                if price <= self.current_demand * (1 + self.zone_buffer):
                    if price > self.current_demand:  # Bounce confirmation
                        self.buy(size=self.size_pct)
                        self.entry_price = price
                        self.zone_touches += 1

            # Sell at supply zone
            elif self.current_supply and abs(zone_str) >= self.min_zone_strength:
                if price >= self.current_supply * (1 - self.zone_buffer):
                    if price < self.current_supply:  # Rejection confirmation
                        self.sell(size=self.size_pct)
                        self.entry_price = price
                        self.zone_touches += 1


# Run backtest
print("\n" + "="*70)
print("RUNNING CLASSIC SUPPLY DEMAND ZONES BACKTEST")
print("="*70)

bt = Backtest(
    data,
    ClassicSupplyDemandZones,
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
        lookback=[15, 20, 25],
        zone_buffer=[0.002, 0.003, 0.005],
        take_profit=[0.01, 0.015, 0.02],
        stop_loss=[0.006, 0.008, 0.01],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()