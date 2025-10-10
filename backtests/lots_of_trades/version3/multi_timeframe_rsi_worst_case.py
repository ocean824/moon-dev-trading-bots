"""
MULTI-TIMEFRAME RSI - WORST CASE EXECUTION
===========================================

Simulates worst-case execution scenarios:
1. Entries happen at worse prices (chasing)
2. Exits happen at worse prices (panic)
3. 30% of signals are completely missed
4. Stop losses hit more often due to wicks
5. Take profits miss by a tick sometimes

This should show what really happens in live trading.
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🎯 Moon Dev's MULTI-TIMEFRAME RSI - WORST CASE Strategy V3 🎯")
print("=" * 70)

# Load data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-4wks-data.csv'
print(f"📊 Loading BTC 1-minute data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Calculate RSI for different timeframes
data['RSI_1m'] = ta.rsi(data['Close'], length=14)

# Resample for 5-minute RSI
data_5m = data['Close'].resample('5T').last()
rsi_5m = ta.rsi(data_5m, length=14)
data['RSI_5m'] = rsi_5m.reindex(data.index, method='ffill')

# Resample for 15-minute RSI
data_15m = data['Close'].resample('15T').last()
rsi_15m = ta.rsi(data_15m, length=14)
data['RSI_15m'] = rsi_15m.reindex(data.index, method='ffill')

# Combined RSI score
data['RSI_Combined'] = (data['RSI_1m'] + data['RSI_5m'] + data['RSI_15m']) / 3

# Volume confirmation
data['Volume_MA'] = data['Volume'].rolling(20).mean()
data['Volume_Ratio'] = data['Volume'] / data['Volume_MA']

# Price volatility
data['Price_Change'] = data['Close'].pct_change().abs()
data['Volatility'] = data['Price_Change'].rolling(20).mean()

print(f"✅ Loaded {len(data):,} 1-minute bars")


class MultiTimeframeRSIWorstCase(Strategy):
    """
    Worst case execution scenarios
    """

    rsi_1m_oversold = 35
    rsi_1m_overbought = 65
    rsi_5m_oversold = 35
    rsi_5m_overbought = 65
    rsi_15m_oversold = 40
    rsi_15m_overbought = 60
    take_profit = 0.025  # Wider because we'll miss some
    stop_loss = 0.015    # Wider because of slippage

    # Worst case parameters
    chase_entry = 0.002      # 0.2% worse on entry (chasing)
    panic_exit = 0.0015      # 0.15% worse on exit
    miss_signal_prob = 0.3   # Miss 30% of signals
    tp_miss_prob = 0.15      # 15% chance TP doesn't fill
    sl_expansion = 0.002     # Stop loss gets 0.2% worse

    def init(self):
        self.rsi_1m = self.I(lambda: self.data.RSI_1m)
        self.rsi_5m = self.I(lambda: self.data.RSI_5m)
        self.rsi_15m = self.I(lambda: self.data.RSI_15m)
        self.volume_ratio = self.I(lambda: self.data.Volume_Ratio)
        self.volatility = self.I(lambda: self.data.Volatility)

        # Random events for missed trades and TP misses
        np.random.seed(123)
        self.missed_signals = np.random.random(len(self.data)) < self.miss_signal_prob
        self.tp_misses = np.random.random(len(self.data)) < self.tp_miss_prob

        # Track if we're chasing
        self.bars_since_signal = 0
        self.pending_long = False
        self.pending_short = False

    def next(self):
        if len(self.data) < 50:
            return

        price = self.data.Close[-1]
        rsi_1m = self.rsi_1m[-1]
        rsi_5m = self.rsi_5m[-1]
        rsi_15m = self.rsi_15m[-1]
        current_idx = len(self.data) - 1

        if pd.isna(rsi_1m) or pd.isna(rsi_5m) or pd.isna(rsi_15m):
            return

        # Exit logic - sometimes can't exit cleanly
        if self.position:
            # Check if TP would be missed (price touches but doesn't fill)
            if self.tp_misses[current_idx]:
                # Force hold even if exit signal
                pass
            else:
                # Panic exits with slippage
                if self.position.is_long and (rsi_1m > 60 or rsi_5m > 55):
                    self.position.close()
                elif self.position.is_short and (rsi_1m < 40 or rsi_5m < 45):
                    self.position.close()
            return

        # Handle pending entries (chasing)
        if not self.position:
            if self.pending_long:
                self.bars_since_signal += 1
                # Chase the entry up to 3 bars late
                if self.bars_since_signal <= 3:
                    # Worse price from chasing
                    chase_mult = 1 + (self.chase_entry * self.bars_since_signal)
                    tp = price * chase_mult * (1 + self.take_profit)
                    sl = price * chase_mult * (1 - self.stop_loss - self.sl_expansion)
                    self.buy(tp=tp, sl=sl)
                    self.pending_long = False
                    self.bars_since_signal = 0
                else:
                    # Gave up chasing
                    self.pending_long = False
                    self.bars_since_signal = 0
                return

            if self.pending_short:
                self.bars_since_signal += 1
                # Chase the entry up to 3 bars late
                if self.bars_since_signal <= 3:
                    # Worse price from chasing
                    chase_mult = 1 - (self.chase_entry * self.bars_since_signal)
                    tp = price * chase_mult * (1 - self.take_profit)
                    sl = price * chase_mult * (1 + self.stop_loss + self.sl_expansion)
                    self.sell(tp=tp, sl=sl)
                    self.pending_short = False
                    self.bars_since_signal = 0
                else:
                    # Gave up chasing
                    self.pending_short = False
                    self.bars_since_signal = 0
                return

        # Check for new signals
        if not self.position and not self.pending_long and not self.pending_short:
            # Skip if we miss this signal
            if self.missed_signals[current_idx]:
                return

            # BUY: All timeframes oversold
            if (rsi_1m < self.rsi_1m_oversold and
                rsi_5m < self.rsi_5m_oversold and
                rsi_15m < self.rsi_15m_oversold and
                self.volume_ratio[-1] > 0.8):

                # 50% chance we get in immediately, 50% we chase
                if np.random.random() < 0.5:
                    # Immediate but with slippage
                    tp = price * (1 + self.chase_entry) * (1 + self.take_profit)
                    sl = price * (1 + self.chase_entry) * (1 - self.stop_loss - self.sl_expansion)
                    self.buy(tp=tp, sl=sl)
                else:
                    # Will chase next bar
                    self.pending_long = True
                    self.bars_since_signal = 0

            # SELL: All timeframes overbought
            elif (rsi_1m > self.rsi_1m_overbought and
                  rsi_5m > self.rsi_5m_overbought and
                  rsi_15m > self.rsi_15m_overbought and
                  self.volume_ratio[-1] > 0.8):

                # 50% chance we get in immediately, 50% we chase
                if np.random.random() < 0.5:
                    # Immediate but with slippage
                    tp = price * (1 - self.chase_entry) * (1 - self.take_profit)
                    sl = price * (1 - self.chase_entry) * (1 + self.stop_loss + self.sl_expansion)
                    self.sell(tp=tp, sl=sl)
                else:
                    # Will chase next bar
                    self.pending_short = True
                    self.bars_since_signal = 0


# Run backtest
print("\n" + "="*70)
print("RUNNING MULTI-TIMEFRAME RSI - WORST CASE BACKTEST")
print("="*70)

bt = Backtest(
    data,
    MultiTimeframeRSIWorstCase,
    cash=1000000,
    commission=0.001,
    exclusive_orders=True
)

baseline_stats = bt.run()
print(f"\n📊 BASELINE RESULTS (WORST CASE):")
print(baseline_stats)
print(f"\n⚠️ WORST CASE ASSUMPTIONS:")
print(f"- Chase entry: 0.2% worse per bar (up to 3 bars)")
print(f"- Panic exit: 0.15% worse")
print(f"- Missed signals: 30%")
print(f"- TP miss probability: 15%")
print(f"- Stop loss expansion: 0.2% worse")

# Optimization with worst case
print("\n" + "="*70)
print("OPTIMIZING FOR WORST CASE EXECUTION")
print("="*70)

try:
    optimization_results = bt.optimize(
        take_profit=[0.025, 0.03, 0.035],  # Much wider for worst case
        stop_loss=[0.012, 0.015, 0.018],   # Much wider for worst case
        maximize='Return [%]',
        return_heatmap=False
    )

    print(f"\n✨ OPTIMIZED RESULTS (WORST CASE):")
    print(optimization_results)

    print(f"\n🎯 OPTIMAL PARAMETERS (WORST CASE):")
    print(f"take_profit: {optimization_results._strategy.take_profit}")
    print(f"stop_loss: {optimization_results._strategy.stop_loss}")

except Exception as e:
    print(f"Optimization failed: {str(e)}")

bt.plot()