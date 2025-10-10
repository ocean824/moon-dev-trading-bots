"""
ASTER DCA STRATEGY #1: SMA %-Drop Layering
==========================================

Logic: Pick a short timeframe SMA (3m or 5m). When price drops below SMA by X%, trigger DCA bids.
Layering: Split allocation into N equal parts (e.g. 5 bids). First bid at SMA*(1 - X%), then stagger every 0.5–1% lower.
Exit: TP at +10%, SL at -20 to -30% (since averaging).

Testing on ASTER token data with "unlimited bid" hypothesis.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 ASTER DCA STRATEGY #1: SMA %-Drop Layering 🎯")
print("=" * 70)

# Data source selection (comment/uncomment as needed)
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate indicators
data['SMA_5'] = data['Close'].rolling(5).mean()
data['SMA_10'] = data['Close'].rolling(10).mean()
data['Drop_from_SMA'] = (data['SMA_5'] - data['Close']) / data['SMA_5'] * 100

print(f"✅ Loaded {len(data):,} bars")
print(f"📈 Price range: ${data['Close'].min():.4f} - ${data['Close'].max():.4f}")


class SMADropLayeringDCA(Strategy):
    """
    DCA when price drops X% below SMA
    """

    # DCA parameters
    sma_drop_trigger = 2.0   # Trigger DCA when price is 2% below SMA
    n_layers = 5             # Number of DCA layers
    layer_spacing = 0.5      # 0.5% spacing between layers

    # Exit parameters
    take_profit = 0.10       # 10% TP on average entry
    stop_loss = 0.25         # 25% SL on average entry

    # Position sizing
    max_position_pct = 0.10  # Max 10% of capital per trade basket

    def init(self):
        self.sma = self.I(lambda: self.data.SMA_5)
        self.drop_from_sma = self.I(lambda: self.data.Drop_from_SMA)

        # Track DCA state
        self.dca_entries = []
        self.dca_sizes = []
        self.avg_entry = None
        self.total_position = 0
        self.in_dca = False

    def next(self):
        if len(self.data) < 20:
            return

        price = self.data.Close[-1]
        sma = self.sma[-1]
        drop_pct = self.drop_from_sma[-1]

        if pd.isna(sma):
            return

        # Exit logic for existing position
        if self.position:
            if self.avg_entry is not None:
                # Check basket TP/SL
                pnl_pct = (price - self.avg_entry) / self.avg_entry

                if pnl_pct >= self.take_profit:
                    self.position.close()
                    self.reset_dca()
                elif pnl_pct <= -self.stop_loss:
                    self.position.close()
                    self.reset_dca()
            return

        # Entry logic - trigger DCA sequence
        if not self.position and not self.in_dca:
            # Check if price dropped enough below SMA
            if drop_pct >= self.sma_drop_trigger:
                self.start_dca_sequence(price, sma)

        # Continue DCA sequence if active
        if self.in_dca and not self.position:
            self.execute_dca_layer(price)

    def start_dca_sequence(self, price, sma):
        """Initialize DCA sequence"""
        self.in_dca = True
        self.dca_entries = []
        self.dca_sizes = []

        # Calculate layer prices
        layer_size = self.max_position_pct / self.n_layers

        # Place first DCA order
        self.buy(size=layer_size)
        self.dca_entries.append(price)
        self.dca_sizes.append(layer_size)
        self.total_position = layer_size

        # Calculate average entry
        self.update_avg_entry()

    def execute_dca_layer(self, price):
        """Execute next DCA layer if conditions met"""
        if len(self.dca_entries) >= self.n_layers:
            return  # All layers executed

        # Check if price dropped enough for next layer
        last_entry = self.dca_entries[-1] if self.dca_entries else price
        drop_from_last = (last_entry - price) / last_entry * 100

        if drop_from_last >= self.layer_spacing:
            layer_size = self.max_position_pct / self.n_layers

            # Add to position
            self.buy(size=layer_size)
            self.dca_entries.append(price)
            self.dca_sizes.append(layer_size)
            self.total_position += layer_size

            # Update average entry
            self.update_avg_entry()

    def update_avg_entry(self):
        """Calculate weighted average entry price"""
        if self.dca_entries and self.dca_sizes:
            total_value = sum(e * s for e, s in zip(self.dca_entries, self.dca_sizes))
            total_size = sum(self.dca_sizes)
            self.avg_entry = total_value / total_size if total_size > 0 else None

    def reset_dca(self):
        """Reset DCA state after exit"""
        self.dca_entries = []
        self.dca_sizes = []
        self.avg_entry = None
        self.total_position = 0
        self.in_dca = False


# Run backtest
print("\n" + "="*70)
print("RUNNING SMA DROP LAYERING DCA BACKTEST")
print("="*70)

bt = Backtest(
    data,
    SMADropLayeringDCA,
    cash=10000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 BASELINE RESULTS:")
print(baseline_stats)

# Optimization
print("\n" + "="*70)
print("OPTIMIZING DCA PARAMETERS")
print("="*70)

try:
    optimization_results = bt.optimize(
        sma_drop_trigger=[1.5, 2.0, 2.5, 3.0],
        n_layers=[3, 5, 7],
        layer_spacing=[0.3, 0.5, 0.7, 1.0],
        take_profit=[0.08, 0.10, 0.12, 0.15],
        stop_loss=[0.20, 0.25, 0.30],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS:")
    print(f"SMA Drop Trigger: {optimization_results._strategy.sma_drop_trigger}%")
    print(f"Number of Layers: {optimization_results._strategy.n_layers}")
    print(f"Layer Spacing: {optimization_results._strategy.layer_spacing}%")
    print(f"Take Profit: {optimization_results._strategy.take_profit*100}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss*100}%")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()