"""
Moon Dev's Trend Impulse Channels Final Working Version
========================================================
Final implementation with proper signal generation and trade execution.
Based on ATR channels with trend-following logic.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Impulse Channels Final Strategy Loading... 🌙")

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ATR_PERIOD = 14
EMA_FAST = 12
EMA_SLOW = 26
ATR_CHANNEL = 2.0  # ATR multiplier for channel width

# Risk management
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 1.5

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendImpulseFinal(Strategy):
    """
    Final Trend Impulse Strategy

    Uses dual EMA crossover for trend direction and
    ATR channels for entry/exit timing.
    """

    # Parameters
    atr_period = ATR_PERIOD
    ema_fast = EMA_FAST
    ema_slow = EMA_SLOW
    atr_channel = ATR_CHANNEL
    take_profit_pct = TAKE_PROFIT_PERCENT / 100
    stop_loss_pct = STOP_LOSS_PERCENT / 100

    def init(self):
        """Initialize indicators"""
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Calculate EMAs
        ema_fast = ta.ema(close, length=self.ema_fast)
        ema_slow = ta.ema(close, length=self.ema_slow)

        # Calculate ATR
        atr = ta.atr(high, low, close, length=self.atr_period)

        # Ensure arrays match data length
        self.ema_fast_full = np.full(len(close), np.nan)
        if ema_fast is not None:
            self.ema_fast_full[-len(ema_fast):] = ema_fast.values

        self.ema_slow_full = np.full(len(close), np.nan)
        if ema_slow is not None:
            self.ema_slow_full[-len(ema_slow):] = ema_slow.values

        self.atr_full = np.full(len(close), np.nan)
        if atr is not None:
            self.atr_full[-len(atr):] = atr.values

        # Calculate trend direction (1 = up, -1 = down)
        self.trend = np.where(self.ema_fast_full > self.ema_slow_full, 1, -1)

        # Calculate ATR channels based on the slow EMA
        self.upper_channel = self.ema_slow_full + (self.atr_full * self.atr_channel)
        self.lower_channel = self.ema_slow_full - (self.atr_full * self.atr_channel)

        # Store as indicators for backtesting
        self.I_ema_fast = self.I(lambda: self.ema_fast_full)
        self.I_ema_slow = self.I(lambda: self.ema_slow_full)
        self.I_atr = self.I(lambda: self.atr_full)
        self.I_upper = self.I(lambda: self.upper_channel)
        self.I_lower = self.I(lambda: self.lower_channel)
        self.I_trend = self.I(lambda: self.trend)

    def next(self):
        """Trading logic"""
        # Skip if not enough data
        if len(self.data) < self.ema_slow + 10:
            return

        # Get current values
        idx = len(self.data) - 1
        if idx < 0 or idx >= len(self.ema_fast_full):
            return

        current_price = self.data.Close[-1]
        current_trend = self.trend[idx]
        prev_trend = self.trend[idx-1] if idx > 0 else 0

        # Skip if any indicator is NaN
        if np.isnan(self.ema_fast_full[idx]) or np.isnan(self.atr_full[idx]):
            return

        # Position management
        if not self.position:
            # Long entry conditions:
            # 1. Trend just turned bullish (fast EMA crosses above slow EMA)
            # 2. OR price bounces from lower channel in uptrend
            if current_trend > 0:  # Bullish trend
                enter_long = False

                # Trend change signal
                if prev_trend <= 0:
                    enter_long = True

                # Channel bounce signal
                if (self.data.Low[-1] <= self.lower_channel[idx] and
                    current_price > self.lower_channel[idx]):
                    enter_long = True

                # Breakout signal
                if (idx > 1 and current_price > self.upper_channel[idx] and
                    self.data.Close[-2] <= self.upper_channel[idx-1]):
                    enter_long = True

                if enter_long:
                    # Calculate stops
                    atr_stop = self.atr_full[idx] * 2 if not np.isnan(self.atr_full[idx]) else current_price * self.stop_loss_pct
                    sl = max(current_price - atr_stop, current_price * (1 - self.stop_loss_pct))
                    tp = current_price * (1 + self.take_profit_pct)
                    self.buy(sl=sl, tp=tp)

            # Short entry conditions:
            # 1. Trend just turned bearish (fast EMA crosses below slow EMA)
            # 2. OR price rejects from upper channel in downtrend
            elif current_trend < 0:  # Bearish trend
                enter_short = False

                # Trend change signal
                if prev_trend >= 0:
                    enter_short = True

                # Channel rejection signal
                if (self.data.High[-1] >= self.upper_channel[idx] and
                    current_price < self.upper_channel[idx]):
                    enter_short = True

                # Breakdown signal
                if (idx > 1 and current_price < self.lower_channel[idx] and
                    self.data.Close[-2] >= self.lower_channel[idx-1]):
                    enter_short = True

                if enter_short:
                    # Calculate stops
                    atr_stop = self.atr_full[idx] * 2 if not np.isnan(self.atr_full[idx]) else current_price * self.stop_loss_pct
                    sl = min(current_price + atr_stop, current_price * (1 + self.stop_loss_pct))
                    tp = current_price * (1 - self.take_profit_pct)
                    self.sell(sl=sl, tp=tp)

        else:
            # Exit management
            if self.position.is_long:
                # Exit if trend turns bearish
                if current_trend < 0:
                    self.position.close()
                # Exit if price closes below lower channel
                elif current_price < self.lower_channel[idx]:
                    self.position.close()

            else:  # Short position
                # Exit if trend turns bullish
                if current_trend > 0:
                    self.position.close()
                # Exit if price closes above upper channel
                elif current_price > self.upper_channel[idx]:
                    self.position.close()

# Run single backtest
bt = Backtest(data, TrendImpulseFinal, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND IMPULSE FINAL - PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"Fast EMA: {EMA_FAST}")
print(f"Slow EMA: {EMA_SLOW}")
print(f"ATR Channel: {ATR_CHANNEL}x")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND IMPULSE FINAL ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendImpulseFinal, 'TrendImpulseFinal')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendImpulseFinal.csv")