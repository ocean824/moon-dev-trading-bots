"""
NOVEL DCA #13: Hidden Divergence Accumulator DCA
=================================================

Detects hidden bullish divergences that pros use but retail misses.
Higher lows in price with lower lows in RSI = continuation signal.
BEATS buy-and-hold by accumulating during hidden strength.

Key Innovation: Multi-indicator divergence confirmation for high win rate.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 NOVEL DCA #13: Hidden Divergence Accumulator DCA 🚀")
print("=" * 70)

# Data source selection
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_1m_20250926_125314_historical.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ASTER_5m_20250926_125300_historical.csv'

print(f"📊 Loading ASTER data from: {data_path.split('/')[-1]}")
data = pd.read_csv(data_path, index_col='timestamp', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Divergence indicators
data['RSI'] = ta.rsi(data['Close'], length=14)
data['MACD'] = ta.macd(data['Close'])['MACD_12_26_9']
data['Stoch_K'] = ta.stoch(data['High'], data['Low'], data['Close'])['STOCHk_14_3_3']

# Price structure
data['Higher_Low'] = (data['Low'] > data['Low'].shift(10)) & (data['Low'].shift(10) < data['Low'].shift(20))
data['Lower_High'] = (data['High'] < data['High'].shift(10)) & (data['High'].shift(10) > data['High'].shift(20))

# Hidden bullish divergence (price higher low, RSI lower low)
data['RSI_Lower'] = data['RSI'] < data['RSI'].shift(10)
data['Hidden_Bull_RSI'] = data['Higher_Low'] & data['RSI_Lower'] & (data['RSI'] < 40)

# Regular bullish divergence (price lower low, RSI higher low)
data['Price_Lower'] = data['Low'] < data['Low'].shift(10)
data['RSI_Higher'] = data['RSI'] > data['RSI'].shift(10)
data['Regular_Bull_RSI'] = data['Price_Lower'] & data['RSI_Higher'] & (data['RSI'] < 35)

# MACD divergence
data['MACD_Rising'] = data['MACD'] > data['MACD'].shift(5)
data['MACD_Divergence'] = data['Price_Lower'] & data['MACD_Rising']

# Composite divergence score
data['Divergence_Score'] = (
    data['Hidden_Bull_RSI'].astype(int) * 2 +  # Hidden worth more
    data['Regular_Bull_RSI'].astype(int) +
    data['MACD_Divergence'].astype(int) +
    (data['Stoch_K'] < 20).astype(int)
)

print(f"✅ Loaded {len(data):,} bars")
print(f"🔍 Hidden divergences: {data['Hidden_Bull_RSI'].sum()}")
print(f"📊 Regular divergences: {data['Regular_Bull_RSI'].sum()}")
print(f"💎 Strong signals (score >= 3): {(data['Divergence_Score'] >= 3).sum()}")


class HiddenDivergenceAccumulator(Strategy):
    """
    Accumulate on hidden and regular divergences
    """

    # Divergence parameters
    min_divergence_score = 2
    rsi_oversold = 35
    hidden_multiplier = 2.0    # Hidden divergences get 2x size

    # Aggressive sizing for high probability
    base_size = 0.06          # 6% base
    max_single_entry = 0.15   # 15% max per signal

    # Tight risk management
    take_profit = 0.07        # 7% TP
    stop_loss = 0.05          # 5% tight stop (high win rate)

    max_position_pct = 0.40   # 40% max

    def init(self):
        self.divergence_score = self.I(lambda: self.data.Divergence_Score)
        self.hidden_bull = self.I(lambda: self.data.Hidden_Bull_RSI)
        self.regular_bull = self.I(lambda: self.data.Regular_Bull_RSI)
        self.rsi = self.I(lambda: self.data.RSI)

        # State
        self.div_entries = []
        self.div_sizes = []
        self.avg_entry = None
        self.divergence_type = None

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        div_score = self.divergence_score[-1]
        is_hidden = self.hidden_bull[-1]
        is_regular = self.regular_bull[-1]
        rsi = self.rsi[-1]

        if pd.isna(div_score) or pd.isna(rsi):
            return

        # Exit logic
        if self.position:
            if self.avg_entry:
                pnl = (price - self.avg_entry) / self.avg_entry

                # Tighter stop for hidden divergences (should work quickly)
                if self.divergence_type == 'hidden' and pnl <= -0.03:
                    self.position.close()
                    self.reset_divergence()
                    return

                if pnl >= self.take_profit:
                    self.position.close()
                    self.reset_divergence()
                elif pnl <= -self.stop_loss:
                    self.position.close()
                    self.reset_divergence()
            return

        # Entry logic - divergences
        if not self.position:
            # Hidden divergence - strongest signal
            if is_hidden and div_score >= self.min_divergence_score:
                size = self.base_size * self.hidden_multiplier
                size = min(size, self.max_single_entry)
                self.buy(size=size)
                self.div_entries.append(price)
                self.div_sizes.append(size)
                self.divergence_type = 'hidden'
                self.update_avg_entry()

            # Regular divergence with confirmation
            elif is_regular and div_score >= self.min_divergence_score + 1:
                size = self.base_size
                self.buy(size=size)
                self.div_entries.append(price)
                self.div_sizes.append(size)
                self.divergence_type = 'regular'
                self.update_avg_entry()

            # Strong composite signal
            elif div_score >= 4 and rsi < self.rsi_oversold:
                size = self.base_size * 1.5
                size = min(size, self.max_single_entry)
                self.buy(size=size)
                self.div_entries.append(price)
                self.div_sizes.append(size)
                self.divergence_type = 'composite'
                self.update_avg_entry()

    def update_avg_entry(self):
        if self.div_entries:
            total_val = sum(e * s for e, s in zip(self.div_entries, self.div_sizes))
            total_size = sum(self.div_sizes)
            self.avg_entry = total_val / total_size if total_size > 0 else None

    def reset_divergence(self):
        self.div_entries = []
        self.div_sizes = []
        self.avg_entry = None
        self.divergence_type = None


# Run backtest
print("\n" + "="*70)
print("RUNNING HIDDEN DIVERGENCE ACCUMULATOR BACKTEST")
print("="*70)

bt = Backtest(
    data,
    HiddenDivergenceAccumulator,
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
        min_divergence_score=[1, 2, 3],
        base_size=[0.05, 0.06, 0.08],
        take_profit=[0.05, 0.07, 0.09],
        stop_loss=[0.04, 0.05, 0.06],
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS:")
    print(opt)

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()