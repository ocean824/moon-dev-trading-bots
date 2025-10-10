"""
NOVEL DCA #15: Extreme Fear Index DCA
======================================

Composite fear index: RSI + volume + consecutive reds + volatility.
When EVERYTHING shows extreme fear, that's the absolute bottom.
BEATS buy-and-hold by only buying at maximum fear levels.

Key Innovation: Multi-factor fear scoring for perfect bottom timing.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #15: Extreme Fear Index DCA 🚀")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Fear components
# 1. RSI fear
data['RSI'] = ta.rsi(data['Close'], length=7)  # Fast RSI
data['RSI_Fear'] = 0
data.loc[data['RSI'] < 20, 'RSI_Fear'] = 3    # Extreme oversold
data.loc[(data['RSI'] >= 20) & (data['RSI'] < 30), 'RSI_Fear'] = 2
data.loc[(data['RSI'] >= 30) & (data['RSI'] < 40), 'RSI_Fear'] = 1

# 2. Consecutive red fear
data['Red'] = data['Close'] < data['Open']
data['Consecutive_Reds'] = data['Red'].rolling(10).sum()
data['Red_Fear'] = 0
data.loc[data['Consecutive_Reds'] >= 7, 'Red_Fear'] = 3
data.loc[(data['Consecutive_Reds'] >= 5) & (data['Consecutive_Reds'] < 7), 'Red_Fear'] = 2
data.loc[(data['Consecutive_Reds'] >= 3) & (data['Consecutive_Reds'] < 5), 'Red_Fear'] = 1

# 3. Volume spike fear
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Panic_Volume'] = data['Volume'] / data['Volume_MA']
data['Volume_Fear'] = 0
data.loc[(data['Panic_Volume'] > 3) & data['Red'], 'Volume_Fear'] = 3
data.loc[(data['Panic_Volume'] > 2) & data['Red'], 'Volume_Fear'] = 2
data.loc[(data['Panic_Volume'] > 1.5) & data['Red'], 'Volume_Fear'] = 1

# 4. Volatility fear
data['ATR'] = ta.atr(data['High'], data['Low'], data['Close'], length=14)
data['ATR_Pct'] = data['ATR'] / data['Close']
data['Vol_Fear'] = 0
data.loc[data['ATR_Pct'] > 0.03, 'Vol_Fear'] = 3
data.loc[(data['ATR_Pct'] > 0.02) & (data['ATR_Pct'] <= 0.03), 'Vol_Fear'] = 2
data.loc[(data['ATR_Pct'] > 0.015) & (data['ATR_Pct'] <= 0.02), 'Vol_Fear'] = 1

# 5. Price drop fear
data['Drop_5bar'] = (data['Close'] - data['Close'].shift(5)) / data['Close'].shift(5)
data['Drop_Fear'] = 0
data.loc[data['Drop_5bar'] < -0.05, 'Drop_Fear'] = 3    # >5% drop
data.loc[(data['Drop_5bar'] < -0.03) & (data['Drop_5bar'] >= -0.05), 'Drop_Fear'] = 2
data.loc[(data['Drop_5bar'] < -0.02) & (data['Drop_5bar'] >= -0.03), 'Drop_Fear'] = 1

# Composite Fear Index (0-15 scale)
data['Fear_Index'] = (
    data['RSI_Fear'] +
    data['Red_Fear'] +
    data['Volume_Fear'] +
    data['Vol_Fear'] +
    data['Drop_Fear']
)

# Fear levels
data['Extreme_Fear'] = data['Fear_Index'] >= 10
data['High_Fear'] = data['Fear_Index'] >= 7
data['Max_Fear'] = data['Fear_Index'] >= 12

print(f"✅ Loaded {len(data):,} bars")
print(f"😱 Extreme fear (10+): {data['Extreme_Fear'].sum()}")
print(f"🔥 Maximum fear (12+): {data['Max_Fear'].sum()}")
print(f"📊 Average fear index: {data['Fear_Index'].mean():.2f}")


class ExtremeFearIndex(Strategy):
    """
    Buy aggressively at maximum fear levels
    """

    # Fear parameters
    fear_threshold = 7        # Minimum fear to start buying
    extreme_fear_level = 10   # Extreme fear for larger sizes
    max_fear_level = 12       # Maximum fear for biggest size

    # Aggressive sizing based on fear
    base_size = 0.05          # 5% base
    fear_multiplier = 0.5     # +50% size per fear point above threshold

    # Quick exits from fear bounces
    take_profit = 0.04        # 4% quick TP
    fear_bounce_tp = 0.08     # 8% TP from extreme fear
    stop_loss = 0.07          # 7% stop

    max_position_pct = 0.50   # 50% max (most aggressive)

    def init(self):
        self.fear_index = self.I(lambda: self.data.Fear_Index)
        self.extreme_fear = self.I(lambda: self.data.Extreme_Fear)
        self.max_fear = self.I(lambda: self.data.Max_Fear)
        self.rsi = self.I(lambda: self.data.RSI)

        # State
        self.fear_entries = []
        self.fear_sizes = []
        self.avg_entry = None
        self.max_fear_seen = 0
        self.entry_fear = 0

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        fear = self.fear_index[-1]
        is_extreme = self.extreme_fear[-1]
        is_max = self.max_fear[-1]
        rsi = self.rsi[-1]

        if pd.isna(fear) or pd.isna(rsi):
            return

        # Exit logic
        if self.position:
            if self.avg_entry:
                pnl = (price - self.avg_entry) / self.avg_entry

                # Dynamic TP based on entry fear level
                if self.entry_fear >= self.max_fear_level:
                    tp = self.fear_bounce_tp
                else:
                    tp = self.take_profit

                # Exit on fear reduction
                if fear < 3 and pnl > 0:  # Fear gone, take any profit
                    self.position.close()
                    self.reset_fear()
                    return

                if pnl >= tp:
                    self.position.close()
                    self.reset_fear()
                elif pnl <= -self.stop_loss:
                    self.position.close()
                    self.reset_fear()
            return

        # Entry logic - fear-based
        if not self.position:
            if fear >= self.fear_threshold:
                # Calculate size based on fear level
                fear_excess = fear - self.fear_threshold
                size_mult = 1 + (fear_excess * self.fear_multiplier)

                # Maximum fear = maximum size
                if is_max:
                    size = self.base_size * 3
                # Extreme fear = large size
                elif is_extreme:
                    size = self.base_size * 2
                # High fear = multiplied size
                else:
                    size = self.base_size * size_mult

                # Cap at max
                total_size = sum(self.fear_sizes) + size
                if total_size > self.max_position_pct:
                    size = self.max_position_pct - sum(self.fear_sizes)
                    if size <= 0:
                        return

                self.buy(size=size)
                self.fear_entries.append(price)
                self.fear_sizes.append(size)
                self.max_fear_seen = max(self.max_fear_seen, fear)
                self.entry_fear = fear
                self.update_avg_entry()

    def update_avg_entry(self):
        if self.fear_entries:
            total_val = sum(e * s for e, s in zip(self.fear_entries, self.fear_sizes))
            total_size = sum(self.fear_sizes)
            self.avg_entry = total_val / total_size if total_size > 0 else None

    def reset_fear(self):
        self.fear_entries = []
        self.fear_sizes = []
        self.avg_entry = None
        self.max_fear_seen = 0
        self.entry_fear = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING EXTREME FEAR INDEX BACKTEST")
print("="*70)

bt = Backtest(
    data,
    ExtremeFearIndex,
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
        fear_threshold=[6, 7, 8],
        base_size=[0.04, 0.05, 0.06],
        take_profit=[0.03, 0.04, 0.05],
        fear_bounce_tp=[0.06, 0.08, 0.10],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()