"""
ASTER Supply & Demand Zones - Volume Weighted Strategy
=======================================================

Uses volume profile to identify high-volume nodes as strong zones.
Zones with highest volume are strongest support/resistance.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 ASTER Supply & Demand Zones - Volume Weighted Strategy 🎯")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Volume Profile Analysis
def calculate_volume_profile(df, window=50, bins=10):
    """Calculate volume profile for price zones"""
    df['Price_Bin'] = pd.cut(df['Close'], bins=bins, labels=False)
    df['Volume_Profile'] = df.groupby('Price_Bin')['Volume'].transform('sum')
    df['Volume_Node'] = df['Volume_Profile'] / df['Volume_Profile'].rolling(window).mean()
    return df

data = calculate_volume_profile(data)

# High Volume Nodes (HVN) as support/resistance
data['HVN'] = data['Volume_Node'] > 1.5  # High volume node
data['LVN'] = data['Volume_Node'] < 0.5  # Low volume node (fast move areas)

# Price levels
data['Resistance'] = data['High'].rolling(20).max()
data['Support'] = data['Low'].rolling(20).min()
data['Mid_Point'] = (data['Resistance'] + data['Support']) / 2

# Volume-weighted zones
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Heavy_Volume'] = data['Volume'] > data['Volume_MA'] * 2

# Zone strength based on volume accumulation
data['Buying_Volume'] = data['Volume'].where(data['Close'] > data['Open'], 0)
data['Selling_Volume'] = data['Volume'].where(data['Close'] < data['Open'], 0)
data['Buy_Sell_Ratio'] = data['Buying_Volume'].rolling(10).sum() / (data['Selling_Volume'].rolling(10).sum() + 1)

# Demand zones (high volume buying)
data['Strong_Demand'] = (data['Buy_Sell_Ratio'] > 2) & data['HVN'] & (data['Close'] < data['Mid_Point'])

# Supply zones (high volume selling)
data['Strong_Supply'] = (data['Buy_Sell_Ratio'] < 0.5) & data['HVN'] & (data['Close'] > data['Mid_Point'])

print(f"✅ Loaded {len(data):,} bars")
print(f"📊 High volume nodes: {data['HVN'].sum()}")
print(f"🔥 Strong demand zones: {data['Strong_Demand'].sum()}")
print(f"❄️ Strong supply zones: {data['Strong_Supply'].sum()}")


class VolumeWeightedZones(Strategy):
    """
    Trade volume-weighted supply and demand zones
    """

    # Volume parameters
    volume_threshold = 1.5   # Minimum volume node strength
    buy_sell_ratio = 2.0     # Minimum ratio for demand zones

    # Trade parameters
    take_profit = 0.018      # 1.8% TP
    stop_loss = 0.007        # 0.7% SL
    trailing_stop = 0.01     # 1% trailing

    # Position sizing
    size_pct = 0.15          # 15% per trade

    def init(self):
        self.hvn = self.I(lambda: self.data.HVN)
        self.volume_node = self.I(lambda: self.data.Volume_Node)
        self.strong_demand = self.I(lambda: self.data.Strong_Demand)
        self.strong_supply = self.I(lambda: self.data.Strong_Supply)
        self.buy_sell_ratio = self.I(lambda: self.data.Buy_Sell_Ratio)
        self.resistance = self.I(lambda: self.data.Resistance)
        self.support = self.I(lambda: self.data.Support)

        # Track highest price for trailing stop
        self.highest_price = None
        self.lowest_price = None
        self.entry_price = None

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        is_hvn = self.hvn[-1]
        vol_node = self.volume_node[-1]
        is_demand = self.strong_demand[-1]
        is_supply = self.strong_supply[-1]
        ratio = self.buy_sell_ratio[-1]
        resist = self.resistance[-1]
        supp = self.support[-1]

        if pd.isna(vol_node) or pd.isna(ratio):
            return

        # Exit management with trailing stop
        if self.position:
            # Long position
            if self.position.is_long:
                # Update highest price
                if self.highest_price is None or price > self.highest_price:
                    self.highest_price = price

                # Trailing stop
                if price < self.highest_price * (1 - self.trailing_stop):
                    self.position.close()
                    self.highest_price = None
                # Fixed TP/SL
                elif self.entry_price and price >= self.entry_price * (1 + self.take_profit):
                    self.position.close()
                    self.highest_price = None
                    self.entry_price = None
                elif self.entry_price and price <= self.entry_price * (1 - self.stop_loss):
                    self.position.close()
                    self.highest_price = None
                    self.entry_price = None

            # Short position
            elif self.position.is_short:
                # Update lowest price
                if self.lowest_price is None or price < self.lowest_price:
                    self.lowest_price = price

                # Trailing stop
                if price > self.lowest_price * (1 + self.trailing_stop):
                    self.position.close()
                    self.lowest_price = None
                # Fixed TP/SL
                elif self.entry_price and price <= self.entry_price * (1 - self.take_profit):
                    self.position.close()
                    self.lowest_price = None
                    self.entry_price = None
                elif self.entry_price and price >= self.entry_price * (1 + self.stop_loss):
                    self.position.close()
                    self.lowest_price = None
                    self.entry_price = None

            return

        # Entry logic
        if not self.position:
            # Strong demand zone entry
            if is_demand and vol_node >= self.volume_threshold:
                if price > supp and price < supp * 1.01:  # Near support
                    self.buy(size=self.size_pct)
                    self.entry_price = price

            # Strong supply zone entry
            elif is_supply and vol_node >= self.volume_threshold:
                if price < resist and price > resist * 0.99:  # Near resistance
                    self.sell(size=self.size_pct)
                    self.entry_price = price

            # High volume node bounce
            elif is_hvn and ratio > self.buy_sell_ratio:
                if price < supp * 1.005:  # Very close to support
                    self.buy(size=self.size_pct)
                    self.entry_price = price

            # High volume node rejection
            elif is_hvn and ratio < (1 / self.buy_sell_ratio):
                if price > resist * 0.995:  # Very close to resistance
                    self.sell(size=self.size_pct)
                    self.entry_price = price


# Run backtest
print("\n" + "="*70)
print("RUNNING VOLUME WEIGHTED ZONES BACKTEST")
print("="*70)

bt = Backtest(
    data,
    VolumeWeightedZones,
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
        volume_threshold=[1.2, 1.5, 1.8],
        take_profit=[0.015, 0.018, 0.022],
        stop_loss=[0.005, 0.007, 0.009],
        trailing_stop=[0.008, 0.01, 0.012],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()