"""
NOVEL DCA #3: Order Book Imbalance DCA
=======================================

Simulates order book depth by analyzing volume clusters and price rejection zones.
DCAs when "bid support" appears weak (high volume sells, price rejection at lows).
Superior to simple volume spikes because it considers buy/sell pressure imbalance.

Key Innovation: Estimates order book pressure from price/volume action patterns.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #3: Order Book Imbalance DCA 🚀")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
# data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate order book imbalance proxies
# Buy pressure: Close near high with volume
data['Buy_Pressure'] = ((data['Close'] - data['Low']) / (data['High'] - data['Low'])) * data['Volume']
data['Sell_Pressure'] = ((data['High'] - data['Close']) / (data['High'] - data['Low'])) * data['Volume']

# Rolling imbalance
data['Buy_Pressure_MA'] = data['Buy_Pressure'].rolling(10).mean()
data['Sell_Pressure_MA'] = data['Sell_Pressure'].rolling(10).mean()
data['Pressure_Ratio'] = data['Buy_Pressure_MA'] / (data['Sell_Pressure_MA'] + 1)

# Volume at price levels (simulated)
data['Volume_Profile_Low'] = data['Volume'].where(data['Close'] == data['Low'].rolling(20).min(), 0).rolling(20).sum()
data['Volume_Profile_High'] = data['Volume'].where(data['Close'] == data['High'].rolling(20).max(), 0).rolling(20).sum()

# Absorption detection (large volume, small price move)
data['Price_Change'] = data['Close'].pct_change().abs()
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Absorption'] = (data['Volume'] > data['Volume_MA'] * 1.5) & (data['Price_Change'] < 0.002)

# Weak bid detection
data['Weak_Bids'] = (data['Pressure_Ratio'] < 0.5) & (data['Sell_Pressure'] > data['Sell_Pressure_MA'])

print(f"✅ Loaded {len(data):,} bars")
print(f"🔴 Weak bid signals: {data['Weak_Bids'].sum()}")


class OrderBookImbalanceDCA(Strategy):
    """
    DCA when order book shows weak bid support
    """

    # Imbalance parameters
    pressure_ratio_threshold = 0.4  # Buy/Sell pressure ratio
    absorption_threshold = 1.5       # Volume multiplier for absorption

    # DCA parameters
    n_layers = 6
    layer_spacing = 0.004           # 0.4% spacing

    # Position sizing
    base_size = 0.02                # 2% base position
    imbalance_multiplier = 2.0      # Increase size with imbalance

    # Exit parameters
    take_profit = 0.10
    stop_loss = 0.18

    max_position_pct = 0.15

    def init(self):
        self.pressure_ratio = self.I(lambda: self.data.Pressure_Ratio)
        self.absorption = self.I(lambda: self.data.Absorption)
        self.sell_pressure = self.I(lambda: self.data.Sell_Pressure)
        self.sell_pressure_ma = self.I(lambda: self.data.Sell_Pressure_MA)

        # DCA state
        self.dca_entries = []
        self.dca_sizes = []
        self.avg_entry = None
        self.imbalance_detected = False
        self.layers_filled = 0

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        pressure = self.pressure_ratio[-1]
        is_absorption = self.absorption[-1]
        sell_p = self.sell_pressure[-1]
        sell_p_ma = self.sell_pressure_ma[-1]

        if pd.isna(pressure):
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

        # Entry logic - detect order book imbalance
        if not self.position:
            # Check for weak bid support
            weak_bids = (
                pressure < self.pressure_ratio_threshold and
                sell_p > sell_p_ma * 1.2 and
                is_absorption  # Absorption shows hidden selling
            )

            if weak_bids and not self.imbalance_detected:
                self.imbalance_detected = True
                self.execute_imbalance_layer(price, pressure)

            # Continue DCA layers
            elif self.imbalance_detected and self.layers_filled < self.n_layers:
                if price <= self.dca_entries[-1] * (1 - self.layer_spacing):
                    self.execute_imbalance_layer(price, pressure)

    def execute_imbalance_layer(self, price, pressure_ratio):
        """Execute DCA with size based on imbalance"""
        # Adjust size based on imbalance severity
        imbalance_factor = max(0.1, 1 - pressure_ratio)  # More imbalance = bigger size
        size = self.base_size * (1 + imbalance_factor * self.imbalance_multiplier)
        size = min(size, self.max_position_pct / self.n_layers)

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
        self.imbalance_detected = False
        self.layers_filled = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING ORDER BOOK IMBALANCE DCA BACKTEST")
print("="*70)

bt = Backtest(
    data,
    OrderBookImbalanceDCA,
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
        pressure_ratio_threshold=[0.3, 0.4, 0.5],
        n_layers=[4, 6, 8],
        take_profit=[0.08, 0.10, 0.12],
        stop_loss=[0.15, 0.18, 0.20],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()