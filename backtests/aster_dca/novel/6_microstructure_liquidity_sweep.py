"""
NOVEL DCA #6: Microstructure Liquidity Sweep DCA
==================================================

Detects stop hunts and liquidity sweeps - rapid wicks that take out stops
then immediately reverse. These are the BEST entry points as weak hands exit.
Superior because it waits for the market makers to clear stops before entering.

Key Innovation: Identifies false breakdowns that sweep liquidity then reverse.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #6: Microstructure Liquidity Sweep DCA 🚀")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Liquidity sweep detection
# Find recent swing lows (liquidity levels)
data['Swing_Low'] = data['Low'].rolling(10).min()
data['Swing_Low_5'] = data['Low'].rolling(5).min()

# Wick analysis
data['Lower_Wick'] = np.minimum(data['Open'], data['Close']) - data['Low']
data['Upper_Wick'] = data['High'] - np.maximum(data['Open'], data['Close'])
data['Body'] = abs(data['Close'] - data['Open'])
data['Wick_Ratio'] = data['Lower_Wick'] / (data['Body'] + 0.00001)

# Sweep detection
data['Below_Swing'] = data['Low'] < data['Swing_Low'].shift(1)
data['Close_Above'] = data['Close'] > data['Swing_Low'].shift(1)
data['Liquidity_Sweep'] = data['Below_Swing'] & data['Close_Above'] & (data['Wick_Ratio'] > 2)

# Volume spike on sweep
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Spike'] = data['Volume'] > data['Volume_MA'] * 1.5
data['Strong_Sweep'] = data['Liquidity_Sweep'] & data['Volume_Spike']

# Rapid recovery detection
data['Recovery_Speed'] = (data['Close'] - data['Low']) / (data['High'] - data['Low'] + 0.00001)
data['Fast_Recovery'] = data['Recovery_Speed'] > 0.6

print(f"✅ Loaded {len(data):,} bars")
print(f"🎯 Liquidity sweeps detected: {data['Liquidity_Sweep'].sum()}")
print(f"💪 Strong sweeps with volume: {data['Strong_Sweep'].sum()}")


class MicrostructureLiquiditySweep(Strategy):
    """
    DCA after liquidity sweeps (stop hunts)
    """

    # Sweep parameters
    wick_ratio_min = 2.0      # Wick must be 2x body
    recovery_threshold = 0.6  # Close in upper 60% of range
    volume_mult = 1.5         # Volume spike threshold

    # DCA parameters
    n_layers = 4
    layer_spacing = 0.003

    # Exit parameters
    take_profit = 0.10        # 10% TP (good entries)
    stop_loss = 0.15          # 15% SL

    max_position_pct = 0.12

    def init(self):
        self.liquidity_sweep = self.I(lambda: self.data.Liquidity_Sweep)
        self.strong_sweep = self.I(lambda: self.data.Strong_Sweep)
        self.recovery_speed = self.I(lambda: self.data.Recovery_Speed)
        self.wick_ratio = self.I(lambda: self.data.Wick_Ratio)

        # DCA state
        self.sweep_entries = []
        self.sweep_sizes = []
        self.avg_entry = None
        self.sweep_detected = False
        self.layers_filled = 0

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        is_sweep = self.liquidity_sweep[-1]
        is_strong = self.strong_sweep[-1]
        recovery = self.recovery_speed[-1]
        wick_r = self.wick_ratio[-1]

        if pd.isna(is_sweep):
            return

        # Exit logic
        if self.position:
            if self.avg_entry:
                pnl = (price - self.avg_entry) / self.avg_entry

                if pnl >= self.take_profit:
                    self.position.close()
                    self.reset_sweep()
                elif pnl <= -self.stop_loss:
                    self.position.close()
                    self.reset_sweep()
            return

        # Entry logic - detect sweep
        if not self.position:
            # Strong sweep detected - best entry
            if is_strong and recovery >= self.recovery_threshold:
                self.sweep_detected = True
                self.execute_sweep_entry(price, premium=True)

            # Regular sweep
            elif is_sweep and wick_r >= self.wick_ratio_min:
                self.sweep_detected = True
                self.execute_sweep_entry(price, premium=False)

            # Continue DCA if sweep detected
            elif self.sweep_detected and self.layers_filled < self.n_layers:
                # Add layers on continued weakness
                if self.sweep_entries:
                    last_entry = self.sweep_entries[-1]
                    if price <= last_entry * (1 - self.layer_spacing):
                        self.execute_sweep_entry(price, premium=False)

    def execute_sweep_entry(self, price, premium=False):
        """Execute entry after sweep"""
        # Premium entries get larger size
        if premium:
            size = (self.max_position_pct / self.n_layers) * 1.5
        else:
            size = self.max_position_pct / self.n_layers

        self.buy(size=size)
        self.sweep_entries.append(price)
        self.sweep_sizes.append(size)
        self.layers_filled += 1
        self.update_avg_entry()

    def update_avg_entry(self):
        if self.sweep_entries:
            total_val = sum(e * s for e, s in zip(self.sweep_entries, self.sweep_sizes))
            total_size = sum(self.sweep_sizes)
            self.avg_entry = total_val / total_size if total_size > 0 else None

    def reset_sweep(self):
        self.sweep_entries = []
        self.sweep_sizes = []
        self.avg_entry = None
        self.sweep_detected = False
        self.layers_filled = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING MICROSTRUCTURE LIQUIDITY SWEEP BACKTEST")
print("="*70)

bt = Backtest(
    data,
    MicrostructureLiquiditySweep,
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
        wick_ratio_min=[1.5, 2.0, 2.5],
        n_layers=[3, 4, 5],
        take_profit=[0.08, 0.10, 0.12],
        stop_loss=[0.12, 0.15, 0.18],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()