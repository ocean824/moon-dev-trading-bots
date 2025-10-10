"""
NOVEL DCA #1: Momentum Exhaustion DCA
======================================

Superior to basic SMA drops because it waits for selling momentum to actually exhaust.
Uses RSI divergence, MACD histogram, and volume decline to identify exhaustion points.
Only DCAs when sellers are truly exhausted, not just at arbitrary price levels.

Key Innovation: Combines multiple momentum indicators to find true capitulation.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #1: Momentum Exhaustion DCA 🚀")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate momentum indicators
data['RSI'] = ta.rsi(data['Close'], length=14)
macd = ta.macd(data['Close'], fast=12, slow=26, signal=9)
data['MACD'] = macd['MACD_12_26_9']
data['MACD_Signal'] = macd['MACDs_12_26_9']
data['MACD_Hist'] = macd['MACDh_12_26_9']

# Volume analysis
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Declining'] = data['Volume'] < data['Volume_MA']

# Price action
data['Lower_Low'] = data['Low'] < data['Low'].shift(1)
data['RSI_Higher'] = data['RSI'] > data['RSI'].shift(1)

# Momentum exhaustion detection
data['Bullish_Divergence'] = data['Lower_Low'] & data['RSI_Higher']
data['MACD_Turning'] = data['MACD_Hist'] > data['MACD_Hist'].shift(1)
data['Exhaustion_Signal'] = (
    (data['RSI'] < 35) &
    data['Volume_Declining'] &
    (data['Bullish_Divergence'] | data['MACD_Turning'])
)

print(f"✅ Loaded {len(data):,} bars")
print(f"🎯 Exhaustion signals found: {data['Exhaustion_Signal'].sum()}")


class MomentumExhaustionDCA(Strategy):
    """
    DCA when momentum shows exhaustion
    """

    # Exhaustion parameters
    rsi_exhaustion = 35       # RSI level for exhaustion
    volume_decline_pct = 0.8  # Volume must be < 80% of average

    # DCA parameters
    n_layers = 5
    layer_spacing = 0.005

    # Exit parameters
    take_profit = 0.12        # 12% TP (higher because better entries)
    stop_loss = 0.20          # 20% SL

    max_position_pct = 0.15   # 15% max position

    def init(self):
        self.rsi = self.I(lambda: self.data.RSI)
        self.macd_hist = self.I(lambda: self.data.MACD_Hist)
        self.volume_ratio = self.I(lambda: self.data.Volume / self.data.Volume_MA)

        # DCA state
        self.dca_entries = []
        self.dca_sizes = []
        self.avg_entry = None
        self.exhaustion_price = None
        self.layers_filled = 0

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        rsi = self.rsi[-1]
        macd_h = self.macd_hist[-1]
        macd_h_prev = self.macd_hist[-2] if len(self.macd_hist) > 1 else macd_h
        vol_ratio = self.volume_ratio[-1]

        if pd.isna(rsi) or pd.isna(macd_h):
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

        # Entry logic - detect exhaustion
        if not self.position:
            # Check for momentum exhaustion
            is_exhausted = (
                rsi < self.rsi_exhaustion and
                vol_ratio < self.volume_decline_pct and
                macd_h > macd_h_prev  # MACD starting to turn
            )

            if is_exhausted and not self.exhaustion_price:
                self.exhaustion_price = price
                self.execute_layer(price)

            # Continue DCA if started
            elif self.exhaustion_price and self.layers_filled < self.n_layers:
                if price <= self.exhaustion_price * (1 - self.layer_spacing * self.layers_filled):
                    self.execute_layer(price)

    def execute_layer(self, price):
        """Execute DCA layer"""
        size = self.max_position_pct / self.n_layers
        self.buy(size=size)
        self.dca_entries.append(price)
        self.dca_sizes.append(size)
        self.layers_filled += 1
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
        self.exhaustion_price = None
        self.layers_filled = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING MOMENTUM EXHAUSTION DCA BACKTEST")
print("="*70)

bt = Backtest(
    data,
    MomentumExhaustionDCA,
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
        rsi_exhaustion=[30, 35, 40],
        n_layers=[3, 5, 7],
        take_profit=[0.10, 0.12, 0.15],
        stop_loss=[0.15, 0.20, 0.25],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()