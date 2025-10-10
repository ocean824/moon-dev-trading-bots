"""
Moon Dev's Trend Impulse Channels Base Strategy
================================================
Implementation of the Pine Script Trend Impulse Channels indicator
using ATR-based trend stepping mechanism with dynamic channels.

Key Features:
- ATR-based trend stepping with configurable thresholds
- Dynamic channel boundaries for volatility adaptation
- Trend hold mechanism to prevent flip-flopping
- Retest signals for continuation and reversal plays
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Impulse Channels Base Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters (matching Pine Script defaults)
ATR_PERIOD = 200
TRIGGER_THRESHOLD = 2.86  # ATR multiplier for trend flips
MAX_STEP_SIZE = 0.034  # Controls maximum trend step size (negative in original, made positive)
BAND_MULTIPLIER = 2.02  # Width of volatility channels
TREND_HOLD = 0  # Bars to hold trend before allowing flip
USE_TREND_FILTER = True  # Filter retest signals based on trend

# Risk management
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendImpulseBase(Strategy):
    """
    Trend Impulse Channels Base Strategy

    Implements ATR-based trend stepping mechanism with:
    - Dynamic trigger thresholds for trend changes
    - Volatility-adaptive channel boundaries
    - Trend hold mechanism for stability
    - Multiple signal types (trend flips, retests, steps)
    """

    # Core parameters
    atr_period = ATR_PERIOD
    trigger_threshold = TRIGGER_THRESHOLD
    max_step_size = MAX_STEP_SIZE
    band_multiplier = BAND_MULTIPLIER
    trend_hold = TREND_HOLD
    use_trend_filter = USE_TREND_FILTER

    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def calculate_trend_impulse(self, close, high, low, atr):
        """
        Calculate the trend impulse channels based on ATR stepping mechanism

        Returns:
            trend: Main trend line
            upper_band: Upper channel boundary
            lower_band: Lower channel boundary
            direction: Trend direction (1 for up, -1 for down)
        """
        n = len(close)
        trend = np.full(n, np.nan)
        direction = np.zeros(n)
        trend_hold_counter = np.zeros(n)

        # Initialize with first close
        trend[0] = close[0]
        direction[0] = 1

        for i in range(1, n):
            if np.isnan(atr[i]):
                trend[i] = trend[i-1]
                direction[i] = direction[i-1]
                continue

            # Calculate trigger levels
            trigger = atr[i] * self.trigger_threshold

            # Calculate step size with max limit
            step_size = min(atr[i] * self.max_step_size, abs(close[i] - trend[i-1]) * 0.1)

            # Check for trend flip conditions
            flip_up = close[i] > trend[i-1] + trigger and direction[i-1] <= 0
            flip_down = close[i] < trend[i-1] - trigger and direction[i-1] >= 0

            # Apply trend hold logic
            if self.trend_hold > 0:
                if flip_up or flip_down:
                    trend_hold_counter[i] = trend_hold_counter[i-1] + 1
                    if trend_hold_counter[i] < self.trend_hold:
                        flip_up = False
                        flip_down = False
                    else:
                        trend_hold_counter[i] = 0
                else:
                    trend_hold_counter[i] = 0

            # Update trend and direction
            if flip_up:
                # Flip to uptrend
                direction[i] = 1
                trend[i] = close[i] - atr[i] * 0.5  # Start below current price
            elif flip_down:
                # Flip to downtrend
                direction[i] = -1
                trend[i] = close[i] + atr[i] * 0.5  # Start above current price
            else:
                # Continue current trend with stepping
                direction[i] = direction[i-1]

                if direction[i] > 0:
                    # Uptrend - step up if price is higher
                    if close[i] > trend[i-1]:
                        trend[i] = trend[i-1] + step_size
                    else:
                        trend[i] = trend[i-1]
                else:
                    # Downtrend - step down if price is lower
                    if close[i] < trend[i-1]:
                        trend[i] = trend[i-1] - step_size
                    else:
                        trend[i] = trend[i-1]

        # Calculate channel bands
        upper_band = trend + atr * self.band_multiplier
        lower_band = trend - atr * self.band_multiplier

        return trend, upper_band, lower_band, direction

    def generate_signals(self, close, high, low, trend, upper_band, lower_band, direction):
        """
        Generate trading signals based on trend impulse channels

        Signal types:
        1. Trend flip signals (strongest)
        2. Channel retest signals (continuation)
        3. Trend step signals (momentum)
        """
        n = len(close)
        long_signals = np.zeros(n)
        short_signals = np.zeros(n)

        for i in range(2, n):
            # Skip if data is invalid
            if np.isnan(trend[i]) or np.isnan(direction[i]):
                continue

            # Trend flip signals
            if direction[i] != direction[i-1]:
                if direction[i] > 0:
                    long_signals[i] = 2  # Strong long signal
                else:
                    short_signals[i] = 2  # Strong short signal

            # Channel retest signals (if trend filter is off or trend agrees)
            if not self.use_trend_filter or direction[i] > 0:
                # Bullish retest - price touches lower band in uptrend
                if low[i] <= lower_band[i] and close[i] > lower_band[i] and direction[i] > 0:
                    long_signals[i] = max(long_signals[i], 1)  # Regular long signal

            if not self.use_trend_filter or direction[i] < 0:
                # Bearish retest - price touches upper band in downtrend
                if high[i] >= upper_band[i] and close[i] < upper_band[i] and direction[i] < 0:
                    short_signals[i] = max(short_signals[i], 1)  # Regular short signal

            # Trend step signals (momentum confirmation)
            if i > 0 and trend[i] != trend[i-1]:
                step_size = abs(trend[i] - trend[i-1])
                if step_size > 0:
                    if direction[i] > 0 and close[i] > trend[i]:
                        long_signals[i] = max(long_signals[i], 0.5)  # Weak long signal
                    elif direction[i] < 0 and close[i] < trend[i]:
                        short_signals[i] = max(short_signals[i], 0.5)  # Weak short signal

        return long_signals, short_signals

    def init(self):
        """Initialize indicators and signals"""
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Calculate ATR
        atr = ta.atr(high, low, close, length=self.atr_period)

        # Ensure arrays are same length as data
        atr_full = np.full(len(close), np.nan)
        if atr is not None and len(atr) > 0:
            atr_full[-len(atr):] = atr.values

        # Calculate trend impulse channels
        trend, upper_band, lower_band, direction = self.calculate_trend_impulse(
            close.values, high.values, low.values, atr_full
        )

        # Generate trading signals
        long_signals, short_signals = self.generate_signals(
            close.values, high.values, low.values,
            trend, upper_band, lower_band, direction
        )

        # Store as indicators for backtesting
        self.trend = self.I(lambda: trend)
        self.upper_band = self.I(lambda: upper_band)
        self.lower_band = self.I(lambda: lower_band)
        self.direction = self.I(lambda: direction)
        self.long_signals = self.I(lambda: long_signals)
        self.short_signals = self.I(lambda: short_signals)
        self.atr = self.I(lambda: atr_full)

    def next(self):
        """Execute trading logic"""
        # Skip if indicators not ready
        if np.isnan(self.trend[-1]) or np.isnan(self.atr[-1]):
            return

        current_price = self.data.Close[-1]

        # Position management
        if self.position:
            # Check for trend reversal exit
            if self.position.is_long and self.direction[-1] < 0:
                self.position.close()
            elif self.position.is_short and self.direction[-1] > 0:
                self.position.close()

            # Trailing stop based on channels
            if self.position.is_long:
                trailing_stop = self.lower_band[-1]
                if current_price < trailing_stop:
                    self.position.close()
            elif self.position.is_short:
                trailing_stop = self.upper_band[-1]
                if current_price > trailing_stop:
                    self.position.close()

        else:
            # Entry signals
            if self.long_signals[-1] > 0:
                # Stronger signals get more aggressive position sizing
                signal_strength = self.long_signals[-1]

                # Calculate stops and targets
                sl_price = current_price * (1 - self.stop_loss)
                # Use lower band as alternative stop if it's tighter
                sl_price = max(sl_price, self.lower_band[-1])

                # Scale target based on signal strength
                tp_multiplier = 1 + (self.take_profit * signal_strength)
                tp_price = current_price * tp_multiplier

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            elif self.short_signals[-1] > 0:
                # Stronger signals get more aggressive position sizing
                signal_strength = self.short_signals[-1]

                # Calculate stops and targets (SL above price for shorts)
                sl_price = current_price * (1 + self.stop_loss)
                # Use upper band as alternative stop if it's wider (for shorts, use max)
                sl_price = max(sl_price, self.upper_band[-1])

                # Scale target based on signal strength (TP below price for shorts)
                tp_multiplier = 1 - (self.take_profit * signal_strength)
                tp_price = current_price * tp_multiplier

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

# Run single backtest
bt = Backtest(data, TrendImpulseBase, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND IMPULSE BASE - DEFAULT PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"Trigger Threshold: {TRIGGER_THRESHOLD}")
print(f"Max Step Size: {MAX_STEP_SIZE}")
print(f"Band Multiplier: {BAND_MULTIPLIER}")
print(f"Trend Hold: {TREND_HOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND IMPULSE BASE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendImpulseBase, 'TrendImpulseBase')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendImpulseBase.csv")