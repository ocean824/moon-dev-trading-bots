"""
NOVEL DCA #8: Whale Accumulation Detector DCA
==============================================

Identifies large volume clusters that indicate whale accumulation.
Looks for abnormal volume patterns, large block trades, and accumulation footprints.
Superior because it follows the smart/big money rather than retail patterns.

Key Innovation: Detects whale accumulation through volume clustering analysis.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #8: Whale Accumulation Detector DCA 🚀")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Volume analysis for whale detection
# Volume percentiles and anomalies
data['Volume_MA'] = data['Volume'].rolling(50).mean()
data['Volume_STD'] = data['Volume'].rolling(50).std()
data['Volume_Z'] = (data['Volume'] - data['Volume_MA']) / data['Volume_STD']
data['Volume_Percentile'] = data['Volume'].rolling(100).rank(pct=True)

# Whale volume threshold (top 5%)
data['Whale_Volume'] = data['Volume_Percentile'] > 0.95
data['Large_Volume'] = data['Volume'] > data['Volume_MA'] * 3

# Price stability during high volume (accumulation pattern)
data['Price_Range'] = data['High'] - data['Low']
data['Range_MA'] = data['Price_Range'].rolling(20).mean()
data['Tight_Range'] = data['Price_Range'] < data['Range_MA']
data['Accumulation_Pattern'] = data['Large_Volume'] & data['Tight_Range']

# Volume clustering (multiple high volume bars)
data['High_Vol_Cluster'] = data['Large_Volume'].rolling(5).sum() >= 2

# Buy pressure analysis
data['Buy_Pressure'] = (data['Close'] - data['Low']) / (data['High'] - data['Low'] + 0.00001)
data['Strong_Buy'] = data['Buy_Pressure'] > 0.7
data['Whale_Buy'] = data['Whale_Volume'] & data['Strong_Buy']

# OBV trend for accumulation confirmation
data['OBV'] = ta.obv(data['Close'], data['Volume'])
data['OBV_MA'] = data['OBV'].rolling(20).mean()
data['OBV_Rising'] = data['OBV'] > data['OBV_MA']

# Composite whale score
data['Whale_Score'] = (
    data['Whale_Volume'].astype(int) +
    data['Accumulation_Pattern'].astype(int) +
    data['High_Vol_Cluster'].astype(int) +
    data['Whale_Buy'].astype(int) +
    data['OBV_Rising'].astype(int)
)

print(f"✅ Loaded {len(data):,} bars")
print(f"🐋 Whale volume bars: {data['Whale_Volume'].sum()}")
print(f"📊 Accumulation patterns: {data['Accumulation_Pattern'].sum()}")
print(f"💪 Strong whale signals (score >= 3): {(data['Whale_Score'] >= 3).sum()}")


class WhaleAccumulationDetector(Strategy):
    """
    DCA when whales are accumulating
    """

    # Whale detection parameters
    min_whale_score = 2       # Minimum whale activity score
    volume_z_threshold = 2.0  # Z-score for abnormal volume
    cluster_threshold = 2      # Min high volume bars in cluster

    # DCA parameters
    n_layers = 5
    layer_spacing = 0.005

    # Whale-based sizing
    base_size = 0.02
    whale_size_mult = 1.5     # Increase size with whale activity

    # Exit parameters
    take_profit = 0.12        # 12% TP (following whales)
    stop_loss = 0.15          # 15% SL

    max_position_pct = 0.15

    def init(self):
        self.whale_score = self.I(lambda: self.data.Whale_Score)
        self.whale_volume = self.I(lambda: self.data.Whale_Volume)
        self.volume_z = self.I(lambda: self.data.Volume_Z)
        self.accumulation = self.I(lambda: self.data.Accumulation_Pattern)
        self.obv_rising = self.I(lambda: self.data.OBV_Rising)

        # DCA state
        self.whale_entries = []
        self.whale_sizes = []
        self.avg_entry = None
        self.whale_phase = False
        self.layers_filled = 0
        self.total_whale_score = 0

    def next(self):
        if len(self.data) < 100:
            return

        price = self.data.Close[-1]
        whale_sc = self.whale_score[-1]
        is_whale = self.whale_volume[-1]
        vol_z = self.volume_z[-1]
        is_accumulation = self.accumulation[-1]
        obv_up = self.obv_rising[-1]

        if pd.isna(whale_sc) or pd.isna(vol_z):
            return

        # Exit logic
        if self.position:
            if self.avg_entry:
                pnl = (price - self.avg_entry) / self.avg_entry

                # Dynamic exit if whale activity stops
                if whale_sc == 0 and pnl > 0.03:  # Small profit if whales leave
                    self.position.close()
                    self.reset_whale()

                if pnl >= self.take_profit:
                    self.position.close()
                    self.reset_whale()
                elif pnl <= -self.stop_loss:
                    self.position.close()
                    self.reset_whale()
            return

        # Entry logic - detect whale accumulation
        if not self.position:
            # Strong whale signal
            is_whale_signal = (
                whale_sc >= self.min_whale_score or
                (vol_z >= self.volume_z_threshold and obv_up)
            )

            # Start whale accumulation phase
            if is_whale_signal and not self.whale_phase:
                self.whale_phase = True
                self.total_whale_score = whale_sc
                self.execute_whale_entry(price, whale_sc)

            # Continue accumulation during whale phase
            elif self.whale_phase and self.layers_filled < self.n_layers:
                # Add layers on continued whale activity or price dips
                if whale_sc >= 1 or is_accumulation:
                    if not self.whale_entries or price <= self.whale_entries[-1] * (1 - self.layer_spacing):
                        self.execute_whale_entry(price, whale_sc)

            # End phase if no whale activity
            elif self.whale_phase and whale_sc == 0 and vol_z < 1:
                self.whale_phase = False

    def execute_whale_entry(self, price, whale_score):
        """Execute entry based on whale activity"""
        # Size based on whale strength
        size_mult = 1 + (whale_score - 1) * 0.2
        size = self.base_size * min(size_mult, self.whale_size_mult)

        # Cap at max position
        size = min(size, self.max_position_pct / self.n_layers)

        self.buy(size=size)
        self.whale_entries.append(price)
        self.whale_sizes.append(size)
        self.layers_filled += 1
        self.total_whale_score = max(self.total_whale_score, whale_score)
        self.update_avg_entry()

    def update_avg_entry(self):
        if self.whale_entries:
            total_val = sum(e * s for e, s in zip(self.whale_entries, self.whale_sizes))
            total_size = sum(self.whale_sizes)
            self.avg_entry = total_val / total_size if total_size > 0 else None

    def reset_whale(self):
        self.whale_entries = []
        self.whale_sizes = []
        self.avg_entry = None
        self.whale_phase = False
        self.layers_filled = 0
        self.total_whale_score = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING WHALE ACCUMULATION DETECTOR BACKTEST")
print("="*70)

bt = Backtest(
    data,
    WhaleAccumulationDetector,
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
        min_whale_score=[2, 3],
        n_layers=[4, 5, 6],
        take_profit=[0.10, 0.12, 0.15],
        stop_loss=[0.12, 0.15, 0.18],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()