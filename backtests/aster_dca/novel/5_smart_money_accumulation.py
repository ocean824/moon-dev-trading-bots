"""
NOVEL DCA #5: Smart Money Accumulation
=======================================

Tracks institutional accumulation patterns: higher lows, volume on up moves,
absorption at support, and Wyckoff accumulation phases.
Superior to time-based DCA because it follows "smart money" footprints.

Key Innovation: Identifies accumulation phases using multiple confluence factors.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #5: Smart Money Accumulation 🚀")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Smart money indicators
# 1. Higher lows pattern
data['Low_5'] = data['Low'].rolling(5).min()
data['Higher_Low'] = data['Low_5'] > data['Low_5'].shift(5)

# 2. Volume analysis
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Up_Move'] = data['Close'] > data['Open']
data['Volume_on_Up'] = data['Volume'].where(data['Up_Move'], 0)
data['Volume_on_Down'] = data['Volume'].where(~data['Up_Move'], 0)
data['Vol_Ratio_Up_Down'] = data['Volume_on_Up'].rolling(10).sum() / (data['Volume_on_Down'].rolling(10).sum() + 1)

# 3. Accumulation/Distribution
data['AD'] = ta.ad(data['High'], data['Low'], data['Close'], data['Volume'])
data['AD_MA'] = data['AD'].rolling(20).mean()
data['AD_Rising'] = data['AD'] > data['AD_MA']

# 4. Spring detection (false breakdown)
data['Support'] = data['Low'].rolling(50).min()
data['Below_Support'] = data['Low'] < data['Support']
data['Spring'] = data['Below_Support'] & (data['Close'] > data['Support'])

# 5. Composite accumulation score
data['Accumulation_Score'] = (
    data['Higher_Low'].astype(int) +
    (data['Vol_Ratio_Up_Down'] > 1.2).astype(int) +
    data['AD_Rising'].astype(int) +
    data['Spring'].astype(int)
)

print(f"✅ Loaded {len(data):,} bars")
print(f"🎯 Strong accumulation signals (score >= 3): {(data['Accumulation_Score'] >= 3).sum()}")


class SmartMoneyAccumulation(Strategy):
    """
    DCA during smart money accumulation phases
    """

    # Accumulation parameters
    min_accumulation_score = 2   # Minimum score to start DCA
    spring_bonus_weight = 2.0     # Extra weight for spring patterns

    # DCA parameters
    n_layers = 7
    layer_spacing = 0.004

    # Progressive sizing
    base_size = 0.015
    accumulation_size_mult = 1.5  # Increase size with stronger signals

    # Exit parameters
    take_profit = 0.15            # 15% TP (smart money targets)
    stop_loss = 0.12              # 12% SL (tighter due to quality)

    max_position_pct = 0.20

    def init(self):
        self.accumulation_score = self.I(lambda: self.data.Accumulation_Score)
        self.higher_low = self.I(lambda: self.data.Higher_Low)
        self.vol_ratio = self.I(lambda: self.data.Vol_Ratio_Up_Down)
        self.ad_rising = self.I(lambda: self.data.AD_Rising)
        self.spring = self.I(lambda: self.data.Spring)

        # DCA state
        self.dca_entries = []
        self.dca_sizes = []
        self.avg_entry = None
        self.accumulation_phase = False
        self.phase_start_price = None
        self.layers_filled = 0
        self.total_score = 0

    def next(self):
        if len(self.data) < 100:
            return

        price = self.data.Close[-1]
        acc_score = self.accumulation_score[-1]
        is_spring = self.spring[-1]

        if pd.isna(acc_score):
            return

        # Exit logic
        if self.position:
            if self.avg_entry:
                pnl = (price - self.avg_entry) / self.avg_entry

                # Dynamic exit based on accumulation strength
                if self.total_score >= 4:  # Strong accumulation
                    tp_mult = 1.2
                else:
                    tp_mult = 1.0

                if pnl >= self.take_profit * tp_mult:
                    self.position.close()
                    self.reset_accumulation()
                elif pnl <= -self.stop_loss:
                    self.position.close()
                    self.reset_accumulation()
            return

        # Entry logic - detect accumulation
        if not self.position:
            # Start accumulation phase
            if acc_score >= self.min_accumulation_score and not self.accumulation_phase:
                self.accumulation_phase = True
                self.phase_start_price = price
                self.total_score = acc_score
                self.execute_smart_layer(price, acc_score, is_spring)

            # Continue accumulation
            elif self.accumulation_phase and self.layers_filled < self.n_layers:
                # Add layers on continued accumulation or price dips
                if acc_score >= self.min_accumulation_score or \
                   price <= self.phase_start_price * (1 - self.layer_spacing * self.layers_filled):
                    self.execute_smart_layer(price, acc_score, is_spring)

            # End accumulation if score drops
            elif self.accumulation_phase and acc_score < 1:
                self.accumulation_phase = False

    def execute_smart_layer(self, price, acc_score, is_spring):
        """Execute DCA with smart money sizing"""
        # Base size adjusted by accumulation strength
        size_mult = 1 + (acc_score - 2) * 0.2  # More size with stronger signals

        # Spring pattern gets bonus size
        if is_spring:
            size_mult *= self.spring_bonus_weight

        size = self.base_size * size_mult
        size = min(size, self.max_position_pct / self.n_layers)

        self.buy(size=size)
        self.dca_entries.append(price)
        self.dca_sizes.append(size)
        self.layers_filled += 1
        self.total_score = max(self.total_score, acc_score)
        self.update_avg_entry()

    def update_avg_entry(self):
        if self.dca_entries:
            total_val = sum(e * s for e, s in zip(self.dca_entries, self.dca_sizes))
            total_size = sum(self.dca_sizes)
            self.avg_entry = total_val / total_size if total_size > 0 else None

    def reset_accumulation(self):
        self.dca_entries = []
        self.dca_sizes = []
        self.avg_entry = None
        self.accumulation_phase = False
        self.phase_start_price = None
        self.layers_filled = 0
        self.total_score = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING SMART MONEY ACCUMULATION BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SmartMoneyAccumulation,
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
        min_accumulation_score=[2, 3],
        n_layers=[5, 7, 9],
        take_profit=[0.12, 0.15, 0.18],
        stop_loss=[0.10, 0.12, 0.15],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()