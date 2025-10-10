"""
ASTER DCA STRATEGY #3: Volume Spike Confirmation
================================================

Logic: Only place DCA bids when you see a downside candle with 2–3× average volume (capitulation bar).
Layering: First bid at that bar's close, then stagger below in 0.5% steps.
Exit: TP at 5–8%, SL very wide (20–30%) because it assumes exchange support comes after washouts.

Helps avoid "walking down" chop; you only buy into stress selling.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 ASTER DCA STRATEGY #3: Volume Spike Confirmation 🎯")
print("=" * 70)

# Data source selection (comment/uncomment as needed)
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate indicators
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Ratio'] = data['Volume'] / data['Volume_MA']
data['Is_Red'] = data['Close'] < data['Open']
data['Price_Drop'] = (data['Open'] - data['Close']) / data['Open'] * 100
data['Capitulation'] = (data['Volume_Ratio'] > 2.0) & data['Is_Red'] & (data['Price_Drop'] > 0.5)

print(f"✅ Loaded {len(data):,} bars")
print(f"📈 Price range: ${data['Close'].min():.4f} - ${data['Close'].max():.4f}")
print(f"🔴 Capitulation bars found: {data['Capitulation'].sum()}")


class VolumeSpikeDCA(Strategy):
    """
    DCA only on high-volume capitulation bars
    """

    # Volume parameters
    volume_spike_mult = 2.5   # Volume must be 2.5x average
    min_drop_pct = 0.5        # Minimum 0.5% red candle

    # DCA parameters
    n_layers = 5              # Number of DCA layers
    layer_spacing = 0.005     # 0.5% spacing

    # Exit parameters
    take_profit = 0.07        # 7% TP (smaller for quick pops)
    stop_loss = 0.25          # 25% SL (wide for washouts)

    # Position sizing
    max_position_pct = 0.10   # Max 10% of capital

    def init(self):
        self.volume_ratio = self.I(lambda: self.data.Volume_Ratio)
        self.is_red = self.I(lambda: self.data.Is_Red)
        self.price_drop = self.I(lambda: self.data.Price_Drop)

        # DCA tracking
        self.dca_entries = []
        self.dca_sizes = []
        self.avg_entry = None
        self.capitulation_price = None
        self.layers_filled = 0

    def next(self):
        if len(self.data) < 30:
            return

        price = self.data.Close[-1]
        vol_ratio = self.volume_ratio[-1]
        is_red = self.is_red[-1]
        drop = self.price_drop[-1]

        if pd.isna(vol_ratio):
            return

        # Exit logic
        if self.position:
            if self.avg_entry is not None:
                pnl_pct = (price - self.avg_entry) / self.avg_entry

                if pnl_pct >= self.take_profit:
                    self.position.close()
                    self.reset_dca()
                elif pnl_pct <= -self.stop_loss:
                    self.position.close()
                    self.reset_dca()
            return

        # Entry logic - look for capitulation
        if not self.position:
            # Check for volume spike capitulation
            is_capitulation = (
                vol_ratio >= self.volume_spike_mult and
                is_red and
                drop >= self.min_drop_pct
            )

            if is_capitulation and self.capitulation_price is None:
                # Start DCA sequence
                self.capitulation_price = price
                self.execute_first_layer(price)

            # Continue DCA if started
            elif self.capitulation_price is not None and self.layers_filled < self.n_layers:
                # Check if price dropped enough for next layer
                drop_from_cap = (self.capitulation_price - price) / self.capitulation_price

                if drop_from_cap >= (self.layers_filled * self.layer_spacing):
                    self.execute_next_layer(price)

    def execute_first_layer(self, price):
        """Execute first DCA layer on capitulation"""
        layer_size = self.max_position_pct / self.n_layers

        self.buy(size=layer_size)
        self.dca_entries.append(price)
        self.dca_sizes.append(layer_size)
        self.layers_filled = 1
        self.update_avg_entry()

    def execute_next_layer(self, price):
        """Execute subsequent DCA layers"""
        layer_size = self.max_position_pct / self.n_layers

        self.buy(size=layer_size)
        self.dca_entries.append(price)
        self.dca_sizes.append(layer_size)
        self.layers_filled += 1
        self.update_avg_entry()

    def update_avg_entry(self):
        """Calculate weighted average entry"""
        if self.dca_entries and self.dca_sizes:
            total_value = sum(e * s for e, s in zip(self.dca_entries, self.dca_sizes))
            total_size = sum(self.dca_sizes)
            self.avg_entry = total_value / total_size if total_size > 0 else None

    def reset_dca(self):
        """Reset DCA state"""
        self.dca_entries = []
        self.dca_sizes = []
        self.avg_entry = None
        self.capitulation_price = None
        self.layers_filled = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING VOLUME SPIKE CONFIRMATION DCA BACKTEST")
print("="*70)

bt = Backtest(
    data,
    VolumeSpikeDCA,
    cash=10000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 BASELINE RESULTS:")
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING VOLUME SPIKE PARAMETERS")
print("="*70)

try:
    optimization_results = bt.optimize(
        volume_spike_mult=[2.0, 2.5, 3.0, 3.5],
        min_drop_pct=[0.3, 0.5, 0.7, 1.0],
        n_layers=[3, 5, 7],
        take_profit=[0.05, 0.07, 0.08, 0.10],
        stop_loss=[0.20, 0.25, 0.30],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS:")
    print(f"Volume Spike Multiplier: {optimization_results._strategy.volume_spike_mult}x")
    print(f"Min Drop %: {optimization_results._strategy.min_drop_pct}%")
    print(f"Number of Layers: {optimization_results._strategy.n_layers}")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100}%")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()