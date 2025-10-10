"""
ASTER Supply & Demand Zones - Dynamic Zone Breakout Strategy
=============================================================

Trades breakouts from consolidation zones with dynamic zone adjustment.
Zones expand/contract based on volatility. Breakouts with volume = strong moves.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 ASTER Supply & Demand Zones - Dynamic Zone Breakout Strategy 🎯")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Dynamic zone detection
# ATR for volatility-based zones
data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=14)

# Dynamic support/resistance zones
data['Upper_Zone'] = data['High'].rolling(10).max()
data['Lower_Zone'] = data['Low'].rolling(10).min()
data['Zone_Width'] = data['Upper_Zone'] - data['Lower_Zone']

# Consolidation detection
data['Consolidating'] = data['Zone_Width'] < data['ATR'] * 2
data['Bars_In_Zone'] = data['Consolidating'].rolling(20).sum()

# Breakout signals
data['Breakout_Up'] = (data['Close'] > data['Upper_Zone'].shift(1)) & (data['Bars_In_Zone'] > 5)
data['Breakout_Down'] = (data['Close'] < data['Lower_Zone'].shift(1)) & (data['Bars_In_Zone'] > 5)

# Volume confirmation
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Surge'] = data['Volume'] > data['Volume_MA'] * 1.5

# Breakout strength
data['Breakout_Strength_Up'] = data['Breakout_Up'] & data['Volume_Surge']
data['Breakout_Strength_Down'] = data['Breakout_Down'] & data['Volume_Surge']

# False breakout detection
data['Failed_Breakout_Up'] = (data['High'] > data['Upper_Zone'].shift(1)) & (data['Close'] < data['Upper_Zone'].shift(1))
data['Failed_Breakout_Down'] = (data['Low'] < data['Lower_Zone'].shift(1)) & (data['Close'] > data['Lower_Zone'].shift(1))

# Zone expansion/contraction
data['Zone_Expanding'] = data['Zone_Width'] > data['Zone_Width'].shift(5)
data['Zone_Contracting'] = data['Zone_Width'] < data['Zone_Width'].shift(5)

print(f"✅ Loaded {len(data):,} bars")
print(f"📊 Consolidation periods: {(data['Bars_In_Zone'] > 10).sum()}")
print(f"🚀 Strong breakouts up: {data['Breakout_Strength_Up'].sum()}")
print(f"📉 Strong breakouts down: {data['Breakout_Strength_Down'].sum()}")


class DynamicZoneBreakout(Strategy):
    """
    Trade breakouts from dynamic supply/demand zones
    """

    # Zone parameters
    min_consolidation = 5    # Minimum bars in zone
    atr_multiplier = 2.0     # Zone width relative to ATR
    volume_surge = 1.5       # Volume multiplier for confirmation

    # Trade parameters
    take_profit = 0.025      # 2.5% TP
    stop_loss = 0.01         # 1% SL
    breakout_hold = 3        # Hold for N bars minimum

    # Position sizing
    size_pct = 0.2           # 20% per trade

    def init(self):
        self.upper_zone = self.I(lambda: self.data.Upper_Zone)
        self.lower_zone = self.I(lambda: self.data.Lower_Zone)
        self.zone_width = self.I(lambda: self.data.Zone_Width)
        self.bars_in_zone = self.I(lambda: self.data.Bars_In_Zone)
        self.breakout_up = self.I(lambda: self.data.Breakout_Strength_Up)
        self.breakout_down = self.I(lambda: self.data.Breakout_Strength_Down)
        self.failed_up = self.I(lambda: self.data.Failed_Breakout_Up)
        self.failed_down = self.I(lambda: self.data.Failed_Breakout_Down)
        self.atr = self.I(lambda: self.data.ATR)

        # Track breakout
        self.bars_since_entry = 0
        self.breakout_type = None
        self.entry_price = None

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        upper = self.upper_zone[-1]
        lower = self.lower_zone[-1]
        width = self.zone_width[-1]
        bars_consol = self.bars_in_zone[-1]
        is_breakout_up = self.breakout_up[-1]
        is_breakout_down = self.breakout_down[-1]
        is_failed_up = self.failed_up[-1]
        is_failed_down = self.failed_down[-1]
        atr = self.atr[-1]

        if pd.isna(upper) or pd.isna(atr):
            return

        # Exit management
        if self.position:
            self.bars_since_entry += 1

            # Long position
            if self.position.is_long:
                # Hold for minimum bars
                if self.bars_since_entry < self.breakout_hold:
                    return

                # Exit on target or stop
                if self.entry_price and price >= self.entry_price * (1 + self.take_profit):
                    self.position.close()
                    self.reset_breakout()
                elif self.entry_price and price <= self.entry_price * (1 - self.stop_loss):
                    self.position.close()
                    self.reset_breakout()
                # Exit on failed breakout
                elif is_failed_up:
                    self.position.close()
                    self.reset_breakout()

            # Short position
            elif self.position.is_short:
                # Hold for minimum bars
                if self.bars_since_entry < self.breakout_hold:
                    return

                # Exit on target or stop
                if self.entry_price and price <= self.entry_price * (1 - self.take_profit):
                    self.position.close()
                    self.reset_breakout()
                elif self.entry_price and price >= self.entry_price * (1 + self.stop_loss):
                    self.position.close()
                    self.reset_breakout()
                # Exit on failed breakout
                elif is_failed_down:
                    self.position.close()
                    self.reset_breakout()

            return

        # Entry logic
        if not self.position:
            # Breakout up with volume
            if is_breakout_up and bars_consol >= self.min_consolidation:
                if width < atr * self.atr_multiplier:  # Tight consolidation
                    self.buy(size=self.size_pct)
                    self.entry_price = price
                    self.breakout_type = 'up'
                    self.bars_since_entry = 0

            # Breakout down with volume
            elif is_breakout_down and bars_consol >= self.min_consolidation:
                if width < atr * self.atr_multiplier:  # Tight consolidation
                    self.sell(size=self.size_pct)
                    self.entry_price = price
                    self.breakout_type = 'down'
                    self.bars_since_entry = 0

            # Fade failed breakouts
            elif is_failed_up and bars_consol >= self.min_consolidation:
                self.sell(size=self.size_pct * 0.5)  # Smaller size for fades
                self.entry_price = price
                self.breakout_type = 'fade_up'
                self.bars_since_entry = 0

            elif is_failed_down and bars_consol >= self.min_consolidation:
                self.buy(size=self.size_pct * 0.5)  # Smaller size for fades
                self.entry_price = price
                self.breakout_type = 'fade_down'
                self.bars_since_entry = 0

    def reset_breakout(self):
        self.bars_since_entry = 0
        self.breakout_type = None
        self.entry_price = None


# Run backtest
print("\n" + "="*70)
print("RUNNING DYNAMIC ZONE BREAKOUT BACKTEST")
print("="*70)

bt = Backtest(
    data,
    DynamicZoneBreakout,
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
        min_consolidation=[3, 5, 7],
        atr_multiplier=[1.5, 2.0, 2.5],
        take_profit=[0.02, 0.025, 0.03],
        stop_loss=[0.008, 0.01, 0.012],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()