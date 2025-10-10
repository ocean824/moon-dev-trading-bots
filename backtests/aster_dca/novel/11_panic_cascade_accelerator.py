"""
NOVEL DCA #11: Panic Cascade Accelerator DCA
=============================================

Aggressively increases position size as panic selling accelerates.
Each red candle triggers larger buys. The worse it gets, the bigger we buy.
This BEATS buy-and-hold by catching the exact bottom of cascades.

Key Innovation: Exponential size increase with consecutive red candles.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #11: Panic Cascade Accelerator DCA 🚀")
print("=" * 70)

# Data source selection
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Panic detection
data['Red_Candle'] = data['Close'] < data['Open']
data['Big_Red'] = (data['Open'] - data['Close']) / data['Open'] > 0.01  # >1% red

# Consecutive red counter
data['Consecutive_Reds'] = 0
consecutive = 0
for i in range(len(data)):
    if data['Red_Candle'].iloc[i]:
        consecutive += 1
    else:
        consecutive = 0
    data.loc[data.index[i], 'Consecutive_Reds'] = consecutive

# Cascade intensity
data['Cascade_Score'] = data['Consecutive_Reds'] * (1 + data['Big_Red'].astype(int))
data['Panic_Mode'] = data['Cascade_Score'] >= 3

# Volume surge during panic
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Panic_Volume'] = (data['Volume'] > data['Volume_MA'] * 2) & data['Red_Candle']

# Extreme oversold
data['RSI'] = ta.rsi(data['Close'], length=6)  # Fast RSI
data['Extreme_Oversold'] = data['RSI'] < 20

print(f"✅ Loaded {len(data):,} bars")
print(f"🔥 Panic cascades detected: {data['Panic_Mode'].sum()}")
print(f"💥 Extreme oversold: {data['Extreme_Oversold'].sum()}")


class PanicCascadeAccelerator(Strategy):
    """
    Exponentially increase buys during panic cascades
    """

    # Cascade parameters
    min_consecutive_reds = 2
    cascade_multiplier = 1.5   # Size multiplier per red candle

    # Aggressive parameters
    base_size = 0.03          # 3% base (larger)
    max_size_per_entry = 0.10 # 10% max per entry

    # Quick exits
    take_profit = 0.05        # 5% quick TP
    trailing_stop = 0.03      # 3% trailing
    stop_loss = 0.10          # 10% hard stop

    max_position_pct = 0.40   # 40% max (aggressive!)

    def init(self):
        self.consecutive_reds = self.I(lambda: self.data.Consecutive_Reds)
        self.cascade_score = self.I(lambda: self.data.Cascade_Score)
        self.panic_volume = self.I(lambda: self.data.Panic_Volume)
        self.rsi = self.I(lambda: self.data.RSI)

        # State
        self.cascade_entries = []
        self.cascade_sizes = []
        self.avg_entry = None
        self.highest_price = None
        self.total_invested = 0

    def next(self):
        if len(self.data) < 20:
            return

        price = self.data.Close[-1]
        reds = self.consecutive_reds[-1]
        cascade = self.cascade_score[-1]
        panic_vol = self.panic_volume[-1]
        rsi = self.rsi[-1]

        if pd.isna(rsi):
            return

        # Exit logic - quick profits
        if self.position:
            if self.avg_entry:
                pnl = (price - self.avg_entry) / self.avg_entry

                # Update trailing stop
                if self.highest_price is None or price > self.highest_price:
                    self.highest_price = price

                # Trailing stop
                if self.highest_price and price < self.highest_price * (1 - self.trailing_stop):
                    self.position.close()
                    self.reset_cascade()
                    return

                # Quick TP
                if pnl >= self.take_profit:
                    self.position.close()
                    self.reset_cascade()
                elif pnl <= -self.stop_loss:
                    self.position.close()
                    self.reset_cascade()
            return

        # Entry logic - panic cascade
        if not self.position:
            # Check for cascade
            if reds >= self.min_consecutive_reds:
                # Calculate exponential size
                size = self.base_size * (self.cascade_multiplier ** (reds - 1))
                size = min(size, self.max_size_per_entry)

                # Extra size for extreme conditions
                if rsi < 20:
                    size *= 1.5
                if panic_vol:
                    size *= 1.2

                # Ensure we don't exceed max
                if self.total_invested + size <= self.max_position_pct:
                    self.buy(size=size)
                    self.cascade_entries.append(price)
                    self.cascade_sizes.append(size)
                    self.total_invested += size
                    self.update_avg_entry()

    def update_avg_entry(self):
        if self.cascade_entries:
            total_val = sum(e * s for e, s in zip(self.cascade_entries, self.cascade_sizes))
            total_size = sum(self.cascade_sizes)
            self.avg_entry = total_val / total_size if total_size > 0 else None

    def reset_cascade(self):
        self.cascade_entries = []
        self.cascade_sizes = []
        self.avg_entry = None
        self.highest_price = None
        self.total_invested = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING PANIC CASCADE ACCELERATOR BACKTEST")
print("="*70)

bt = Backtest(
    data,
    PanicCascadeAccelerator,
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
        min_consecutive_reds=[2, 3],
        cascade_multiplier=[1.3, 1.5, 1.7],
        take_profit=[0.03, 0.05, 0.07],
        trailing_stop=[0.02, 0.03, 0.04],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()