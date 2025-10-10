"""
NOVEL DCA #14: Market Maker Trap DCA
=====================================

Identifies when market makers are trapping retail with fake breakdowns.
Rapid spike down followed by immediate recovery = MM stop hunt.
BEATS buy-and-hold by trading alongside market makers, not against them.

Key Innovation: Detects MM manipulation patterns and trades with them.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #14: Market Maker Trap DCA 🚀")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Market maker trap detection
# Sudden spike detection
data['Range'] = data['High'] - data['Low']
data['Range_MA'] = data['Range'].rolling(20).mean()
data['Spike_Bar'] = data['Range'] > data['Range_MA'] * 2

# Fake breakdown (wick below support, close above)
data['Support'] = data['Low'].rolling(20).min()
data['Breakdown'] = data['Low'] < data['Support'].shift(1)
data['Recovery'] = data['Close'] > data['Support'].shift(1)
data['Trap_Bar'] = data['Breakdown'] & data['Recovery'] & data['Spike_Bar']

# Volume anomaly (high volume on trap)
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['High_Volume'] = data['Volume'] > data['Volume_MA'] * 2
data['MM_Trap'] = data['Trap_Bar'] & data['High_Volume']

# Quick reversal pattern
data['Hammer'] = (
    (data['Close'] > data['Open']) &
    ((data['Low'] - data['Close'].min()) > (data['High'] - data['Low']) * 0.6) &
    ((data['High'] - data['Close']) < (data['High'] - data['Low']) * 0.2)
)

# Absorption pattern (large volume, small price move)
data['Price_Change'] = abs(data['Close'] - data['Open']) / data['Open']
data['Absorption'] = (data['High_Volume']) & (data['Price_Change'] < 0.002)

# MM activity score
data['MM_Score'] = (
    data['Trap_Bar'].astype(int) * 2 +
    data['MM_Trap'].astype(int) * 3 +
    data['Hammer'].astype(int) +
    data['Absorption'].astype(int)
)

print(f"✅ Loaded {len(data):,} bars")
print(f"🪤 Market maker traps: {data['MM_Trap'].sum()}")
print(f"🔨 Hammer reversals: {data['Hammer'].sum()}")
print(f"💪 Strong MM activity (score >= 3): {(data['MM_Score'] >= 3).sum()}")


class MarketMakerTrap(Strategy):
    """
    Trade with market makers on their trap patterns
    """

    # MM detection parameters
    min_mm_score = 2
    spike_multiplier = 2.0    # Range spike detection

    # Aggressive parameters for high probability
    base_size = 0.08          # 8% base
    trap_size_mult = 2.5      # 2.5x on confirmed traps

    # Quick profits
    take_profit = 0.05        # 5% quick TP
    trailing_stop = 0.025     # 2.5% trailing
    stop_loss = 0.06          # 6% stop (tight)

    max_position_pct = 0.45   # 45% max (very aggressive)

    def init(self):
        self.mm_score = self.I(lambda: self.data.MM_Score)
        self.trap_bar = self.I(lambda: self.data.Trap_Bar)
        self.mm_trap = self.I(lambda: self.data.MM_Trap)
        self.hammer = self.I(lambda: self.data.Hammer)

        # State
        self.trap_entries = []
        self.trap_sizes = []
        self.avg_entry = None
        self.highest_price = None
        self.trap_count = 0

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        mm_sc = self.mm_score[-1]
        is_trap = self.trap_bar[-1]
        is_mm_trap = self.mm_trap[-1]
        is_hammer = self.hammer[-1]

        if pd.isna(mm_sc):
            return

        # Exit logic
        if self.position:
            if self.avg_entry:
                pnl = (price - self.avg_entry) / self.avg_entry

                # Update trailing
                if self.highest_price is None or price > self.highest_price:
                    self.highest_price = price

                # Trailing stop (tight)
                if self.highest_price and price < self.highest_price * (1 - self.trailing_stop):
                    self.position.close()
                    self.reset_trap()
                    return

                # Quick TP or stop
                if pnl >= self.take_profit:
                    self.position.close()
                    self.reset_trap()
                elif pnl <= -self.stop_loss:
                    self.position.close()
                    self.reset_trap()
            return

        # Entry logic - MM traps
        if not self.position:
            # Perfect MM trap
            if is_mm_trap:
                size = self.base_size * self.trap_size_mult
                self.execute_trap_entry(price, size, 'mm_trap')

            # Regular trap with score
            elif is_trap and mm_sc >= self.min_mm_score:
                size = self.base_size * 1.5
                self.execute_trap_entry(price, size, 'trap')

            # Hammer reversal
            elif is_hammer and mm_sc >= 1:
                size = self.base_size
                self.execute_trap_entry(price, size, 'hammer')

            # High MM activity
            elif mm_sc >= 4:
                size = self.base_size * 2
                self.execute_trap_entry(price, size, 'high_activity')

    def execute_trap_entry(self, price, size, trap_type):
        """Execute entry on MM trap"""
        # Cap size
        total_size = sum(self.trap_sizes) + size
        if total_size > self.max_position_pct:
            size = self.max_position_pct - sum(self.trap_sizes)
            if size <= 0:
                return

        self.buy(size=size)
        self.trap_entries.append(price)
        self.trap_sizes.append(size)
        self.trap_count += 1
        self.update_avg_entry()

    def update_avg_entry(self):
        if self.trap_entries:
            total_val = sum(e * s for e, s in zip(self.trap_entries, self.trap_sizes))
            total_size = sum(self.trap_sizes)
            self.avg_entry = total_val / total_size if total_size > 0 else None

    def reset_trap(self):
        self.trap_entries = []
        self.trap_sizes = []
        self.avg_entry = None
        self.highest_price = None
        self.trap_count = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING MARKET MAKER TRAP BACKTEST")
print("="*70)

bt = Backtest(
    data,
    MarketMakerTrap,
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
        min_mm_score=[1, 2, 3],
        base_size=[0.06, 0.08, 0.10],
        take_profit=[0.04, 0.05, 0.06],
        trailing_stop=[0.02, 0.025, 0.03],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()