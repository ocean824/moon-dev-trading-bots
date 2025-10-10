"""
NOVEL DCA #9: Momentum Fade Time Decay DCA
===========================================

Tracks momentum decay over time - as selling momentum fades, probability of
reversal increases. Uses time-weighted momentum decay to optimize entries.
Superior because it combines both price momentum AND time decay factors.

Key Innovation: Time decay function that increases DCA aggression as momentum fades.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #9: Momentum Fade Time Decay DCA 🚀")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Momentum calculations
# Rate of change
data['ROC_5'] = ta.roc(data['Close'], length=5)
data['ROC_10'] = ta.roc(data['Close'], length=10)
data['ROC_20'] = ta.roc(data['Close'], length=20)

# Momentum decay tracking
data['Negative_Momentum'] = data['ROC_10'] < 0
data['Bars_Negative'] = data['Negative_Momentum'].rolling(20).sum()

# Momentum fade detection
data['ROC_Improving'] = data['ROC_5'] > data['ROC_5'].shift(1)
data['ROC_Less_Negative'] = (data['ROC_10'] < 0) & (data['ROC_10'] > data['ROC_10'].shift(1))
data['Momentum_Fading'] = data['ROC_Less_Negative'] & (data['Bars_Negative'] >= 5)

# Time decay factor
data['Downtrend_Duration'] = 0
downtrend_count = 0
for i in range(len(data)):
    if i > 0:
        if data['Close'].iloc[i] < data['Close'].iloc[i-1]:
            downtrend_count += 1
        else:
            downtrend_count = 0
        data.loc[data.index[i], 'Downtrend_Duration'] = downtrend_count

# Decay function: stronger signal with longer downtrend
data['Time_Decay_Factor'] = 1 - np.exp(-data['Downtrend_Duration'] / 10)

# Volume confirmation of momentum fade
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Declining'] = data['Volume'] < data['Volume_MA'] * 0.8
data['Exhaustion_Volume'] = data['Volume_Declining'] & data['Momentum_Fading']

# Composite momentum fade score
data['Fade_Score'] = (
    data['Momentum_Fading'].astype(int) +
    data['ROC_Improving'].astype(int) +
    data['Volume_Declining'].astype(int) +
    (data['Time_Decay_Factor'] > 0.3).astype(int) +
    (data['Bars_Negative'] >= 10).astype(int)
)

print(f"✅ Loaded {len(data):,} bars")
print(f"📉 Momentum fading signals: {data['Momentum_Fading'].sum()}")
print(f"⏰ Extended downtrends (>10 bars): {(data['Downtrend_Duration'] > 10).sum()}")
print(f"💫 Strong fade signals (score >= 3): {(data['Fade_Score'] >= 3).sum()}")


class MomentumFadeTimeDecay(Strategy):
    """
    DCA as momentum fades with time decay
    """

    # Momentum parameters
    min_fade_score = 2        # Minimum fade score to start
    roc_threshold = -5        # ROC threshold for negative momentum
    time_decay_min = 0.2      # Minimum time decay factor

    # DCA parameters
    n_layers = 6
    layer_spacing = 0.004

    # Time-based sizing
    base_size = 0.015
    time_decay_mult = 2.0     # Max multiplier for extended fades

    # Exit parameters
    take_profit = 0.09        # 9% TP
    stop_loss = 0.16          # 16% SL

    max_position_pct = 0.15

    def init(self):
        self.fade_score = self.I(lambda: self.data.Fade_Score)
        self.momentum_fading = self.I(lambda: self.data.Momentum_Fading)
        self.time_decay = self.I(lambda: self.data.Time_Decay_Factor)
        self.roc_10 = self.I(lambda: self.data.ROC_10)
        self.bars_negative = self.I(lambda: self.data.Bars_Negative)

        # DCA state
        self.fade_entries = []
        self.fade_sizes = []
        self.avg_entry = None
        self.fade_phase = False
        self.phase_start_time = None
        self.layers_filled = 0

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        fade_sc = self.fade_score[-1]
        is_fading = self.momentum_fading[-1]
        time_factor = self.time_decay[-1]
        roc = self.roc_10[-1]
        bars_neg = self.bars_negative[-1]

        if pd.isna(fade_sc) or pd.isna(roc):
            return

        # Exit logic
        if self.position:
            if self.avg_entry:
                pnl = (price - self.avg_entry) / self.avg_entry

                # Exit on momentum reversal
                if roc > 5 and pnl > 0:  # Strong positive momentum
                    self.position.close()
                    self.reset_fade()

                if pnl >= self.take_profit:
                    self.position.close()
                    self.reset_fade()
                elif pnl <= -self.stop_loss:
                    self.position.close()
                    self.reset_fade()
            return

        # Entry logic - detect momentum fade
        if not self.position:
            # Check for momentum fade conditions
            fade_conditions = (
                fade_sc >= self.min_fade_score and
                roc < self.roc_threshold and
                time_factor >= self.time_decay_min
            )

            # Start fade phase
            if fade_conditions and not self.fade_phase:
                self.fade_phase = True
                self.phase_start_time = len(self.data)
                self.execute_fade_entry(price, time_factor)

            # Continue fade phase
            elif self.fade_phase and self.layers_filled < self.n_layers:
                # Time-based decay increases aggression
                bars_since_start = len(self.data) - self.phase_start_time if self.phase_start_time else 0
                decay_boost = min(bars_since_start / 20, 1.0)  # Max boost after 20 bars

                # Add layers with increasing aggression
                if is_fading or fade_sc >= 1:
                    if not self.fade_entries or price <= self.fade_entries[-1] * (1 - self.layer_spacing * (1 - decay_boost * 0.5)):
                        self.execute_fade_entry(price, time_factor + decay_boost)

            # End phase if momentum turns positive
            elif self.fade_phase and roc > 0:
                self.fade_phase = False

    def execute_fade_entry(self, price, time_factor):
        """Execute entry with time decay sizing"""
        # Size increases with time decay
        decay_mult = 1 + (time_factor * (self.time_decay_mult - 1))
        size = self.base_size * decay_mult

        # Cap at max position
        size = min(size, self.max_position_pct / self.n_layers)

        self.buy(size=size)
        self.fade_entries.append(price)
        self.fade_sizes.append(size)
        self.layers_filled += 1
        self.update_avg_entry()

    def update_avg_entry(self):
        if self.fade_entries:
            total_val = sum(e * s for e, s in zip(self.fade_entries, self.fade_sizes))
            total_size = sum(self.fade_sizes)
            self.avg_entry = total_val / total_size if total_size > 0 else None

    def reset_fade(self):
        self.fade_entries = []
        self.fade_sizes = []
        self.avg_entry = None
        self.fade_phase = False
        self.phase_start_time = None
        self.layers_filled = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING MOMENTUM FADE TIME DECAY BACKTEST")
print("="*70)

bt = Backtest(
    data,
    MomentumFadeTimeDecay,
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
        min_fade_score=[2, 3],
        n_layers=[4, 6, 8],
        take_profit=[0.07, 0.09, 0.11],
        stop_loss=[0.14, 0.16, 0.18],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()