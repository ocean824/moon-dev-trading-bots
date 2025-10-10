"""
NOVEL DCA #10: Support Cluster Confluence DCA
==============================================

Identifies areas where multiple support levels converge - pivot points, moving
averages, previous lows, Fibonacci levels all clustering together.
Superior because confluence zones have the highest probability of holding.

Key Innovation: Scores support strength by counting overlapping technical levels.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #10: Support Cluster Confluence DCA 🚀")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Multiple support calculations
# 1. Moving averages as support
data['MA_10'] = data['Close'].rolling(10).mean()
data['MA_20'] = data['Close'].rolling(20).mean()
data['MA_50'] = data['Close'].rolling(50).mean()
data['EMA_20'] = ta.ema(data['Close'], length=20)

# 2. Previous lows as support
data['Low_5'] = data['Low'].rolling(5).min()
data['Low_10'] = data['Low'].rolling(10).min()
data['Low_20'] = data['Low'].rolling(20).min()

# 3. Pivot points
data['Pivot'] = (data['High'].shift(1) + data['Low'].shift(1) + data['Close'].shift(1)) / 3
data['S1'] = 2 * data['Pivot'] - data['High'].shift(1)
data['S2'] = data['Pivot'] - (data['High'].shift(1) - data['Low'].shift(1))

# 4. VWAP as support
data['VWAP'] = ta.vwap(data['High'], data['Low'], data['Close'], data['Volume'])

# 5. Bollinger lower band
bb = ta.bbands(data['Close'], length=20, std=2)
data['BB_Lower'] = bb['BBL_20_2.0']

# Support confluence scoring
def count_nearby_supports(row, price, threshold=0.01):
    """Count how many support levels are within threshold of price"""
    supports = [
        row['MA_10'], row['MA_20'], row['MA_50'], row['EMA_20'],
        row['Low_5'], row['Low_10'], row['Low_20'],
        row['Pivot'], row['S1'], row['S2'],
        row['VWAP'], row['BB_Lower']
    ]
    count = 0
    for sup in supports:
        if pd.notna(sup) and abs(price - sup) / price <= threshold:
            count += 1
    return count

# Calculate confluence score for each bar
data['Support_Count'] = data.apply(lambda row: count_nearby_supports(row, row['Close']), axis=1)

# Near support detection
data['Near_MA'] = abs(data['Close'] - data['MA_20']) / data['MA_20'] < 0.01
data['Near_Low'] = abs(data['Close'] - data['Low_10']) / data['Low_10'] < 0.01
data['Near_Pivot'] = abs(data['Close'] - data['S1']) / data['S1'] < 0.01

# Strong confluence zones
data['Strong_Confluence'] = data['Support_Count'] >= 3
data['Mega_Confluence'] = data['Support_Count'] >= 5

# Volume confirmation at support
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_At_Support'] = data['Strong_Confluence'] & (data['Volume'] > data['Volume_MA'])

print(f"✅ Loaded {len(data):,} bars")
print(f"📊 Strong confluence zones (3+): {data['Strong_Confluence'].sum()}")
print(f"💎 Mega confluence zones (5+): {data['Mega_Confluence'].sum()}")


class SupportClusterConfluence(Strategy):
    """
    DCA at multiple support confluence zones
    """

    # Confluence parameters
    min_support_count = 3     # Minimum overlapping supports
    confluence_threshold = 0.01  # 1% proximity for confluence
    mega_confluence = 5       # Extra strong signal

    # DCA parameters
    n_layers = 5
    layer_spacing = 0.004

    # Confluence-based sizing
    base_size = 0.02
    confluence_mult = 1.5     # Size multiplier for strong confluence

    # Exit parameters
    take_profit = 0.11        # 11% TP
    stop_loss = 0.14          # 14% SL

    max_position_pct = 0.15

    def init(self):
        self.support_count = self.I(lambda: self.data.Support_Count)
        self.strong_confluence = self.I(lambda: self.data.Strong_Confluence)
        self.mega_confluence = self.I(lambda: self.data.Mega_Confluence)
        self.volume_at_support = self.I(lambda: self.data.Volume_At_Support)

        # Support levels for reference
        self.ma_20 = self.I(lambda: self.data.MA_20)
        self.low_10 = self.I(lambda: self.data.Low_10)
        self.s1 = self.I(lambda: self.data.S1)

        # DCA state
        self.confluence_entries = []
        self.confluence_sizes = []
        self.avg_entry = None
        self.confluence_phase = False
        self.strongest_confluence = 0
        self.layers_filled = 0

    def next(self):
        if len(self.data) < 100:
            return

        price = self.data.Close[-1]
        support_cnt = self.support_count[-1]
        is_strong = self.strong_confluence[-1]
        is_mega = self.mega_confluence[-1]
        vol_support = self.volume_at_support[-1]

        if pd.isna(support_cnt):
            return

        # Exit logic
        if self.position:
            if self.avg_entry:
                pnl = (price - self.avg_entry) / self.avg_entry

                # Dynamic exit based on confluence strength
                if self.strongest_confluence >= self.mega_confluence:
                    tp_mult = 1.2  # Higher target for mega confluence
                else:
                    tp_mult = 1.0

                if pnl >= self.take_profit * tp_mult:
                    self.position.close()
                    self.reset_confluence()
                elif pnl <= -self.stop_loss:
                    self.position.close()
                    self.reset_confluence()
            return

        # Entry logic - detect confluence
        if not self.position:
            # Check for support confluence
            has_confluence = support_cnt >= self.min_support_count

            # Mega confluence - immediate strong entry
            if is_mega and vol_support:
                self.confluence_phase = True
                self.strongest_confluence = support_cnt
                self.execute_confluence_entry(price, support_cnt, mega=True)

            # Regular confluence
            elif has_confluence and not self.confluence_phase:
                self.confluence_phase = True
                self.strongest_confluence = support_cnt
                self.execute_confluence_entry(price, support_cnt, mega=False)

            # Continue layering at confluence zones
            elif self.confluence_phase and self.layers_filled < self.n_layers:
                # Add layers if still near confluence or price drops
                if support_cnt >= 2:
                    if not self.confluence_entries or price <= self.confluence_entries[-1] * (1 - self.layer_spacing):
                        self.execute_confluence_entry(price, support_cnt, mega=False)

            # End phase if away from all supports
            elif self.confluence_phase and support_cnt < 2:
                self.confluence_phase = False

    def execute_confluence_entry(self, price, support_count, mega=False):
        """Execute entry at confluence zone"""
        # Size based on confluence strength
        if mega:
            size = self.base_size * self.confluence_mult * 1.5
        else:
            confluence_factor = 1 + (support_count - 3) * 0.15
            size = self.base_size * min(confluence_factor, self.confluence_mult)

        # Cap at max position
        size = min(size, self.max_position_pct / self.n_layers)

        self.buy(size=size)
        self.confluence_entries.append(price)
        self.confluence_sizes.append(size)
        self.layers_filled += 1
        self.strongest_confluence = max(self.strongest_confluence, support_count)
        self.update_avg_entry()

    def update_avg_entry(self):
        if self.confluence_entries:
            total_val = sum(e * s for e, s in zip(self.confluence_entries, self.confluence_sizes))
            total_size = sum(self.confluence_sizes)
            self.avg_entry = total_val / total_size if total_size > 0 else None

    def reset_confluence(self):
        self.confluence_entries = []
        self.confluence_sizes = []
        self.avg_entry = None
        self.confluence_phase = False
        self.strongest_confluence = 0
        self.layers_filled = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING SUPPORT CLUSTER CONFLUENCE BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SupportClusterConfluence,
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
        min_support_count=[2, 3, 4],
        n_layers=[4, 5, 6],
        take_profit=[0.09, 0.11, 0.13],
        stop_loss=[0.12, 0.14, 0.16],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()