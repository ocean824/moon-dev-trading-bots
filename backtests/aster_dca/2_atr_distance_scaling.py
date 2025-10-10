"""
ASTER DCA STRATEGY #2: ATR-Distance Scaling
============================================

Logic: Instead of raw % under SMA, use volatility. Buy if price < SMA - 1×ATR.
Layering: First bid at 1 ATR below, then additional at 1.5 ATR, 2 ATR, etc.
Exit: Small TP (5–10%) because these are mean reversion pops.

ATR scales entries based on regime — wider orders in high vol, tighter in low vol.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 ASTER DCA STRATEGY #2: ATR-Distance Scaling 🎯")
print("=" * 70)

# Data source selection (comment/uncomment as needed)
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate indicators
data['SMA_10'] = data['Close'].rolling(10).mean()
data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=14)
data['ATR_Distance'] = (data['SMA_10'] - data['Close']) / data['ATR']  # How many ATRs below SMA

print(f"✅ Loaded {len(data):,} bars")
print(f"📈 Price range: ${data['Close'].min():.4f} - ${data['Close'].max():.4f}")
print(f"📊 Average ATR: ${data['ATR'].mean():.6f}")


class ATRDistanceScalingDCA(Strategy):
    """
    DCA based on ATR distance from SMA
    """

    # DCA parameters
    atr_trigger = 1.0        # Trigger at 1 ATR below SMA
    atr_layer_mult = 0.5     # Add 0.5 ATR for each layer
    n_layers = 5             # Number of DCA layers

    # Exit parameters (smaller for mean reversion)
    take_profit = 0.08       # 8% TP
    stop_loss = 0.25         # 25% SL (wide for DCA)

    # Position sizing
    max_position_pct = 0.10  # Max 10% of capital

    def init(self):
        self.sma = self.I(lambda: self.data.SMA_10)
        self.atr = self.I(lambda: self.data.ATR)
        self.atr_distance = self.I(lambda: self.data.ATR_Distance)

        # Track DCA state
        self.dca_entries = []
        self.dca_sizes = []
        self.avg_entry = None
        self.layer_targets = []
        self.current_layer = 0

    def next(self):
        if len(self.data) < 30:
            return

        price = self.data.Close[-1]
        sma = self.sma[-1]
        atr = self.atr[-1]
        atr_dist = self.atr_distance[-1]

        if pd.isna(sma) or pd.isna(atr) or atr == 0:
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

        # Entry logic - check ATR distance
        if not self.position:
            # Initialize DCA if price is far enough below SMA
            if atr_dist >= self.atr_trigger and not self.layer_targets:
                self.setup_atr_layers(price, sma, atr)

            # Execute layers if setup
            if self.layer_targets and self.current_layer < len(self.layer_targets):
                target_price = self.layer_targets[self.current_layer]

                if price <= target_price:
                    self.execute_dca_layer(price)

    def setup_atr_layers(self, price, sma, atr):
        """Setup ATR-based layer targets"""
        self.layer_targets = []
        self.current_layer = 0

        for i in range(self.n_layers):
            # Each layer is progressively further in ATR terms
            atr_mult = self.atr_trigger + (i * self.atr_layer_mult)
            target = sma - (atr * atr_mult)
            self.layer_targets.append(target)

    def execute_dca_layer(self, price):
        """Execute DCA layer"""
        layer_size = self.max_position_pct / self.n_layers

        # Add to position
        self.buy(size=layer_size)
        self.dca_entries.append(price)
        self.dca_sizes.append(layer_size)
        self.current_layer += 1

        # Update average entry
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
        self.layer_targets = []
        self.current_layer = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING ATR-DISTANCE SCALING DCA BACKTEST")
print("="*70)

bt = Backtest(
    data,
    ATRDistanceScalingDCA,
    cash=10000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 BASELINE RESULTS:")
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING ATR PARAMETERS")
print("="*70)

try:
    optimization_results = bt.optimize(
        atr_trigger=[0.5, 0.75, 1.0, 1.25, 1.5],
        atr_layer_mult=[0.3, 0.5, 0.7],
        n_layers=[3, 5, 7],
        take_profit=[0.05, 0.08, 0.10],
        stop_loss=[0.20, 0.25, 0.30],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS:")
    print(f"ATR Trigger: {optimization_results._strategy.atr_trigger} ATR")
    print(f"ATR Layer Multiplier: {optimization_results._strategy.atr_layer_mult}")
    print(f"Number of Layers: {optimization_results._strategy.n_layers}")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100}%")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()