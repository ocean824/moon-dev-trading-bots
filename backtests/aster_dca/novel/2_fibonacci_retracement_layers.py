"""
NOVEL DCA #2: Fibonacci Retracement Layers
===========================================

Places DCA orders at natural Fibonacci support levels (23.6%, 38.2%, 50%, 61.8%, 78.6%).
Superior to fixed spacing because Fibonacci levels act as psychological support.
Dynamically calculates retracements from recent swing high to swing low.

Key Innovation: Uses market structure and golden ratio for optimal layer placement.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #2: Fibonacci Retracement Layers 🚀")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Find swing highs and lows
window = 20
data['Swing_High'] = data['High'].rolling(window).max()
data['Swing_Low'] = data['Low'].rolling(window).min()

# Calculate Fibonacci levels
def calculate_fib_levels(high, low):
    """Calculate Fibonacci retracement levels"""
    diff = high - low
    levels = {
        0.236: high - (diff * 0.236),  # 23.6%
        0.382: high - (diff * 0.382),  # 38.2%
        0.500: high - (diff * 0.500),  # 50%
        0.618: high - (diff * 0.618),  # 61.8%
        0.786: high - (diff * 0.786),  # 78.6%
    }
    return levels

# Calculate current Fib levels
data['Fib_Range'] = data['Swing_High'] - data['Swing_Low']
data['Fib_236'] = data['Swing_High'] - (data['Fib_Range'] * 0.236)
data['Fib_382'] = data['Swing_High'] - (data['Fib_Range'] * 0.382)
data['Fib_500'] = data['Swing_High'] - (data['Fib_Range'] * 0.500)
data['Fib_618'] = data['Swing_High'] - (data['Fib_Range'] * 0.618)
data['Fib_786'] = data['Swing_High'] - (data['Fib_Range'] * 0.786)

print(f"✅ Loaded {len(data):,} bars")
print(f"📈 Price range: ${data['Close'].min():.4f} - ${data['Close'].max():.4f}")


class FibonacciRetracementDCA(Strategy):
    """
    DCA at Fibonacci retracement levels
    """

    # Fib parameters
    lookback_period = 50      # Bars to find swing high/low
    min_range_pct = 0.03      # Minimum 3% range to trade

    # DCA parameters
    fib_levels = [0.236, 0.382, 0.500, 0.618, 0.786]
    layer_size_weights = [0.15, 0.20, 0.25, 0.25, 0.15]  # Heavier at 50% and 61.8%

    # Exit parameters
    take_profit = 0.15        # 15% TP
    stop_loss = 0.15          # 15% SL (tighter because better levels)

    max_position_pct = 0.15

    def init(self):
        self.swing_high = self.I(lambda: self.data.Swing_High)
        self.swing_low = self.I(lambda: self.data.Swing_Low)
        self.fib_236 = self.I(lambda: self.data.Fib_236)
        self.fib_382 = self.I(lambda: self.data.Fib_382)
        self.fib_500 = self.I(lambda: self.data.Fib_500)
        self.fib_618 = self.I(lambda: self.data.Fib_618)
        self.fib_786 = self.I(lambda: self.data.Fib_786)

        # DCA state
        self.dca_entries = []
        self.dca_sizes = []
        self.avg_entry = None
        self.fib_targets = {}
        self.levels_hit = []

    def next(self):
        if len(self.data) < self.lookback_period:
            return

        price = self.data.Close[-1]
        swing_h = self.swing_high[-1]
        swing_l = self.swing_low[-1]

        if pd.isna(swing_h) or pd.isna(swing_l):
            return

        # Exit logic
        if self.position:
            if self.avg_entry:
                pnl = (price - self.avg_entry) / self.avg_entry

                if pnl >= self.take_profit:
                    self.position.close()
                    self.reset_dca()
                elif pnl <= -self.stop_loss:
                    self.position.close()
                    self.reset_dca()
            return

        # Entry logic
        if not self.position:
            # Check if range is wide enough
            range_pct = (swing_h - swing_l) / swing_l
            if range_pct < self.min_range_pct:
                return

            # Setup Fibonacci targets if not set
            if not self.fib_targets:
                self.setup_fib_targets(swing_h, swing_l)

            # Check if price hits any Fib level
            for level, target_price in self.fib_targets.items():
                if level not in self.levels_hit:
                    # Check if price crossed this level
                    if price <= target_price:
                        self.execute_fib_layer(price, level)
                        break  # Only one layer per bar

    def setup_fib_targets(self, high, low):
        """Setup Fibonacci target prices"""
        diff = high - low
        self.fib_targets = {
            0.236: high - (diff * 0.236),
            0.382: high - (diff * 0.382),
            0.500: high - (diff * 0.500),
            0.618: high - (diff * 0.618),
            0.786: high - (diff * 0.786),
        }

    def execute_fib_layer(self, price, level):
        """Execute DCA at Fibonacci level"""
        # Find weight for this level
        idx = self.fib_levels.index(level) if level in self.fib_levels else 0
        weight = self.layer_size_weights[idx]
        size = self.max_position_pct * weight

        self.buy(size=size)
        self.dca_entries.append(price)
        self.dca_sizes.append(size)
        self.levels_hit.append(level)
        self.update_avg_entry()

    def update_avg_entry(self):
        if self.dca_entries:
            total_val = sum(e * s for e, s in zip(self.dca_entries, self.dca_sizes))
            total_size = sum(self.dca_sizes)
            self.avg_entry = total_val / total_size if total_size > 0 else None

    def reset_dca(self):
        self.dca_entries = []
        self.dca_sizes = []
        self.avg_entry = None
        self.fib_targets = {}
        self.levels_hit = []


# Run backtest
print("\n" + "="*70)
print("RUNNING FIBONACCI RETRACEMENT DCA BACKTEST")
print("="*70)

bt = Backtest(
    data,
    FibonacciRetracementDCA,
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
        lookback_period=[30, 50, 70],
        min_range_pct=[0.02, 0.03, 0.04],
        take_profit=[0.12, 0.15, 0.18],
        stop_loss=[0.12, 0.15, 0.18],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()