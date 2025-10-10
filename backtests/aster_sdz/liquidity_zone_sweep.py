"""
ASTER Supply & Demand Zones - Liquidity Zone Sweep Strategy
============================================================

Identifies liquidity zones where stops are hunted, then trades the reversal.
Stop hunts create the best risk/reward opportunities.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 ASTER Supply & Demand Zones - Liquidity Zone Sweep Strategy 🎯")
print("=" * 70)

# Data source selection
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Liquidity zones identification
# Recent highs/lows where stops likely sit
data['Recent_High'] = data['High'].rolling(20).max()
data['Recent_Low'] = data['Low'].rolling(20).min()

# Liquidity sweep detection
data['Sweep_High'] = (data['High'] > data['Recent_High'].shift(1)) & (data['Close'] < data['Recent_High'].shift(1))
data['Sweep_Low'] = (data['Low'] < data['Recent_Low'].shift(1)) & (data['Close'] > data['Recent_Low'].shift(1))

# Wick analysis for sweeps
data['Upper_Wick'] = data['High'] - np.maximum(data['Open'], data['Close'])
data['Lower_Wick'] = np.minimum(data['Open'], data['Close']) - data['Low']
data['Body'] = abs(data['Close'] - data['Open'])

# Strong sweep = long wick, small body
data['Upper_Wick_Ratio'] = data['Upper_Wick'] / (data['Body'] + 0.00001)
data['Lower_Wick_Ratio'] = data['Lower_Wick'] / (data['Body'] + 0.00001)

data['Strong_Sweep_High'] = data['Sweep_High'] & (data['Upper_Wick_Ratio'] > 2)
data['Strong_Sweep_Low'] = data['Sweep_Low'] & (data['Lower_Wick_Ratio'] > 2)

# Volume spike on sweep (stop hunt volume)
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Spike'] = data['Volume'] > data['Volume_MA'] * 2

data['Liquidity_Grab_High'] = data['Strong_Sweep_High'] & data['Volume_Spike']
data['Liquidity_Grab_Low'] = data['Strong_Sweep_Low'] & data['Volume_Spike']

# Recovery speed after sweep
data['Recovery_Up'] = (data['Close'] - data['Low']) / (data['High'] - data['Low'] + 0.00001)
data['Recovery_Down'] = (data['High'] - data['Close']) / (data['High'] - data['Low'] + 0.00001)

# Zone strength based on multiple sweeps
data['Sweep_Count_High'] = data['Sweep_High'].rolling(10).sum()
data['Sweep_Count_Low'] = data['Sweep_Low'].rolling(10).sum()

print(f"✅ Loaded {len(data):,} bars")
print(f"🎣 Liquidity sweeps high: {data['Sweep_High'].sum()}")
print(f"🎣 Liquidity sweeps low: {data['Sweep_Low'].sum()}")
print(f"💪 Strong liquidity grabs: {(data['Liquidity_Grab_High'] | data['Liquidity_Grab_Low']).sum()}")


class LiquidityZoneSweep(Strategy):
    """
    Trade reversals after liquidity sweeps
    """

    # Sweep parameters
    wick_ratio_min = 2.0     # Minimum wick/body ratio
    recovery_threshold = 0.6  # Recovery in candle range
    volume_spike = 2.0        # Volume multiplier

    # Trade parameters
    take_profit = 0.02        # 2% TP
    stop_loss = 0.008         # 0.8% SL (tight)
    trail_after = 0.01        # Start trailing after 1%

    # Position sizing
    size_pct = 0.25           # 25% per trade (aggressive)

    def init(self):
        self.sweep_high = self.I(lambda: self.data.Strong_Sweep_High)
        self.sweep_low = self.I(lambda: self.data.Strong_Sweep_Low)
        self.liquidity_high = self.I(lambda: self.data.Liquidity_Grab_High)
        self.liquidity_low = self.I(lambda: self.data.Liquidity_Grab_Low)
        self.recovery_up = self.I(lambda: self.data.Recovery_Up)
        self.recovery_down = self.I(lambda: self.data.Recovery_Down)
        self.recent_high = self.I(lambda: self.data.Recent_High)
        self.recent_low = self.I(lambda: self.data.Recent_Low)

        # Track for trailing
        self.highest_price = None
        self.lowest_price = None
        self.entry_type = None
        self.entry_price = None

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        is_sweep_high = self.sweep_high[-1]
        is_sweep_low = self.sweep_low[-1]
        is_liquidity_high = self.liquidity_high[-1]
        is_liquidity_low = self.liquidity_low[-1]
        recovery_up = self.recovery_up[-1]
        recovery_down = self.recovery_down[-1]

        if pd.isna(recovery_up):
            return

        # Exit management
        if self.position:
            # Long position
            if self.position.is_long:
                # Update highest
                if self.highest_price is None or price > self.highest_price:
                    self.highest_price = price

                # Trailing after initial move
                if self.entry_price and price > self.entry_price * (1 + self.trail_after):
                    trail_stop = self.highest_price * (1 - self.stop_loss)
                    if price < trail_stop:
                        self.position.close()
                        self.reset_sweep()
                        return

                # Fixed exits
                if self.entry_price and price >= self.entry_price * (1 + self.take_profit):
                    self.position.close()
                    self.reset_sweep()
                elif self.entry_price and price <= self.entry_price * (1 - self.stop_loss):
                    self.position.close()
                    self.reset_sweep()

            # Short position
            elif self.position.is_short:
                # Update lowest
                if self.lowest_price is None or price < self.lowest_price:
                    self.lowest_price = price

                # Trailing after initial move
                if self.entry_price and price < self.entry_price * (1 - self.trail_after):
                    trail_stop = self.lowest_price * (1 + self.stop_loss)
                    if price > trail_stop:
                        self.position.close()
                        self.reset_sweep()
                        return

                # Fixed exits
                if self.entry_price and price <= self.entry_price * (1 - self.take_profit):
                    self.position.close()
                    self.reset_sweep()
                elif self.entry_price and price >= self.entry_price * (1 + self.stop_loss):
                    self.position.close()
                    self.reset_sweep()

            return

        # Entry logic - fade liquidity sweeps
        if not self.position:
            # Strong liquidity grab low - buy the sweep
            if is_liquidity_low:
                if recovery_up > self.recovery_threshold:
                    self.buy(size=self.size_pct)
                    self.entry_price = price
                    self.entry_type = 'liquidity_low'

            # Strong liquidity grab high - sell the sweep
            elif is_liquidity_high:
                if recovery_down > self.recovery_threshold:
                    self.sell(size=self.size_pct)
                    self.entry_price = price
                    self.entry_type = 'liquidity_high'

            # Regular sweep low with recovery
            elif is_sweep_low:
                if recovery_up > self.recovery_threshold:
                    self.buy(size=self.size_pct * 0.75)  # Smaller on regular sweeps
                    self.entry_price = price
                    self.entry_type = 'sweep_low'

            # Regular sweep high with recovery
            elif is_sweep_high:
                if recovery_down > self.recovery_threshold:
                    self.sell(size=self.size_pct * 0.75)  # Smaller on regular sweeps
                    self.entry_price = price
                    self.entry_type = 'sweep_high'

    def reset_sweep(self):
        self.highest_price = None
        self.lowest_price = None
        self.entry_type = None
        self.entry_price = None


# Run backtest
print("\n" + "="*70)
print("RUNNING LIQUIDITY ZONE SWEEP BACKTEST")
print("="*70)

bt = Backtest(
    data,
    LiquidityZoneSweep,
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
        recovery_threshold=[0.5, 0.6, 0.7],
        take_profit=[0.015, 0.02, 0.025],
        stop_loss=[0.006, 0.008, 0.01],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()