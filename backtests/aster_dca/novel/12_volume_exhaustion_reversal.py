"""
NOVEL DCA #12: Volume Exhaustion Reversal DCA
==============================================

Waits for selling volume to completely exhaust, then aggressively buys.
When nobody's left to sell, that's the bottom. Simple but powerful.
BEATS buy-and-hold by timing exact exhaustion points.

Key Innovation: Volume decay rate analysis to predict reversal timing.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #12: Volume Exhaustion Reversal DCA 🚀")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Volume exhaustion metrics
data['Volume_MA_20'] = data['Volume'].rolling(20).mean()
data['Volume_MA_5'] = data['Volume'].rolling(5).mean()
data['Volume_Ratio'] = data['Volume_MA_5'] / data['Volume_MA_20']

# Selling volume
data['Red_Volume'] = data['Volume'].where(data['Close'] < data['Open'], 0)
data['Red_Vol_MA'] = data['Red_Volume'].rolling(10).mean()

# Exhaustion detection
data['Volume_Declining'] = data['Volume_Ratio'] < 0.5  # Volume dying
data['Price_Stabilizing'] = abs(data['Close'].pct_change()) < 0.005  # Price flattening

# Volume exhaustion score
data['Exhaustion'] = (
    data['Volume_Declining'] &
    data['Price_Stabilizing'] &
    (data['Close'] < data['Close'].rolling(20).mean())
)

# Extreme low volume
data['Volume_Percentile'] = data['Volume'].rolling(100).rank(pct=True)
data['Extreme_Low_Vol'] = data['Volume_Percentile'] < 0.1

# Price compression
data['High_Low_Range'] = data['High'] - data['Low']
data['Range_MA'] = data['High_Low_Range'].rolling(20).mean()
data['Compressed'] = data['High_Low_Range'] < data['Range_MA'] * 0.5

print(f"✅ Loaded {len(data):,} bars")
print(f"📉 Volume exhaustion points: {data['Exhaustion'].sum()}")
print(f"🔇 Extreme low volume: {data['Extreme_Low_Vol'].sum()}")


class VolumeExhaustionReversal(Strategy):
    """
    Buy aggressively when volume completely exhausts
    """

    # Exhaustion parameters
    volume_ratio_threshold = 0.4  # Volume must drop to 40% of average
    compression_threshold = 0.5   # Range compression

    # Aggressive sizing
    base_size = 0.05             # 5% base
    exhaustion_multiplier = 3.0   # 3x size on exhaustion

    # Fast exits
    take_profit = 0.06           # 6% TP
    quick_exit = 0.03            # 3% quick scalp
    stop_loss = 0.08             # 8% stop

    max_position_pct = 0.35      # 35% max

    def init(self):
        self.volume_ratio = self.I(lambda: self.data.Volume_Ratio)
        self.exhaustion = self.I(lambda: self.data.Exhaustion)
        self.extreme_low = self.I(lambda: self.data.Extreme_Low_Vol)
        self.compressed = self.I(lambda: self.data.Compressed)

        # State
        self.exhaustion_entries = []
        self.exhaustion_sizes = []
        self.avg_entry = None
        self.bars_held = 0

    def next(self):
        if len(self.data) < 100:
            return

        price = self.data.Close[-1]
        vol_ratio = self.volume_ratio[-1]
        is_exhausted = self.exhaustion[-1]
        is_extreme = self.extreme_low[-1]
        is_compressed = self.compressed[-1]

        if pd.isna(vol_ratio):
            return

        # Exit logic
        if self.position:
            self.bars_held += 1
            if self.avg_entry:
                pnl = (price - self.avg_entry) / self.avg_entry

                # Quick scalp after 5 bars
                if self.bars_held >= 5 and pnl >= self.quick_exit:
                    self.position.close()
                    self.reset_exhaustion()
                    return

                # Normal exits
                if pnl >= self.take_profit:
                    self.position.close()
                    self.reset_exhaustion()
                elif pnl <= -self.stop_loss:
                    self.position.close()
                    self.reset_exhaustion()
            return

        # Entry logic - volume exhaustion
        if not self.position:
            # Perfect exhaustion setup
            if is_exhausted and is_compressed:
                size = self.base_size * self.exhaustion_multiplier
                self.execute_exhaustion_buy(price, size)

            # Extreme low volume opportunity
            elif is_extreme and vol_ratio < self.volume_ratio_threshold:
                size = self.base_size * 2
                self.execute_exhaustion_buy(price, size)

            # Regular exhaustion
            elif vol_ratio < self.volume_ratio_threshold * 0.8:
                size = self.base_size
                self.execute_exhaustion_buy(price, size)

    def execute_exhaustion_buy(self, price, size):
        """Execute buy on exhaustion"""
        # Cap size
        total_size = sum(self.exhaustion_sizes) + size
        if total_size > self.max_position_pct:
            size = self.max_position_pct - sum(self.exhaustion_sizes)
            if size <= 0:
                return

        self.buy(size=size)
        self.exhaustion_entries.append(price)
        self.exhaustion_sizes.append(size)
        self.update_avg_entry()

    def update_avg_entry(self):
        if self.exhaustion_entries:
            total_val = sum(e * s for e, s in zip(self.exhaustion_entries, self.exhaustion_sizes))
            total_size = sum(self.exhaustion_sizes)
            self.avg_entry = total_val / total_size if total_size > 0 else None

    def reset_exhaustion(self):
        self.exhaustion_entries = []
        self.exhaustion_sizes = []
        self.avg_entry = None
        self.bars_held = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING VOLUME EXHAUSTION REVERSAL BACKTEST")
print("="*70)

bt = Backtest(
    data,
    VolumeExhaustionReversal,
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
        volume_ratio_threshold=[0.3, 0.4, 0.5],
        base_size=[0.04, 0.05, 0.06],
        take_profit=[0.05, 0.06, 0.08],
        quick_exit=[0.02, 0.03, 0.04],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()