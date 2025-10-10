"""
Moon Dev's Trend Impulse Channels Tight Strategy
=================================================
Tighter channels and faster reactions for more frequent trading.
Uses smaller ATR multipliers and shorter lookback periods.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Impulse Channels Tight Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - TIGHTER settings for more responsive trading
ATR_PERIOD = 50  # Shorter ATR period for faster adaptation
TRIGGER_THRESHOLD = 1.5  # Lower threshold for quicker trend flips
MAX_STEP_SIZE = 0.05  # Larger steps for faster trend following
BAND_MULTIPLIER = 1.0  # Tighter channels
TREND_HOLD = 0  # No trend hold for immediate reactions

# Risk management - tighter stops for scalping
TAKE_PROFIT_PERCENT = 1.5
STOP_LOSS_PERCENT = 1.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendImpulseTight(Strategy):
    """
    Trend Impulse Channels Tight Strategy

    Modifications for tighter trading:
    - Shorter ATR period (50 vs 200)
    - Lower trigger threshold (1.5 vs 2.86)
    - Tighter bands (1.0 vs 2.02)
    - More aggressive step sizing
    - Quicker exits on channel breaks
    """

    # Core parameters - TIGHTER
    atr_period = ATR_PERIOD
    trigger_threshold = TRIGGER_THRESHOLD
    max_step_size = MAX_STEP_SIZE
    band_multiplier = BAND_MULTIPLIER
    trend_hold = TREND_HOLD
    use_trend_filter = False  # Disabled for more signals

    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    # Additional tight parameters
    quick_exit_multiplier = 0.5  # Exit at half band distance
    momentum_threshold = 0.002  # 0.2% momentum required

    def calculate_trend_impulse(self, close, high, low, atr):
        """
        Calculate trend impulse with tighter parameters
        """
        n = len(close)
        trend = np.full(n, np.nan)
        direction = np.zeros(n)
        momentum = np.zeros(n)

        # Initialize
        trend[0] = close[0]
        direction[0] = 1

        for i in range(1, n):
            if np.isnan(atr[i]):
                trend[i] = trend[i-1]
                direction[i] = direction[i-1]
                continue

            # Calculate momentum
            if i > 1:
                momentum[i] = (close[i] - close[i-1]) / close[i-1]

            # Tighter trigger levels
            trigger = atr[i] * self.trigger_threshold

            # More aggressive step size
            step_size = min(atr[i] * self.max_step_size, abs(close[i] - trend[i-1]) * 0.2)

            # Check for trend flips with momentum confirmation
            flip_up = (close[i] > trend[i-1] + trigger and
                      direction[i-1] <= 0 and
                      momentum[i] > self.momentum_threshold)
            flip_down = (close[i] < trend[i-1] - trigger and
                        direction[i-1] >= 0 and
                        momentum[i] < -self.momentum_threshold)

            # Update trend and direction
            if flip_up:
                direction[i] = 1
                trend[i] = close[i] - atr[i] * 0.3  # Tighter initial placement
            elif flip_down:
                direction[i] = -1
                trend[i] = close[i] + atr[i] * 0.3
            else:
                direction[i] = direction[i-1]

                # Aggressive stepping
                if direction[i] > 0:
                    if close[i] > trend[i-1]:
                        # Accelerate stepping when momentum is strong
                        accel_factor = 1.0 + abs(momentum[i]) * 10
                        trend[i] = trend[i-1] + (step_size * accel_factor)
                    else:
                        trend[i] = trend[i-1]
                else:
                    if close[i] < trend[i-1]:
                        # Accelerate stepping when momentum is strong
                        accel_factor = 1.0 + abs(momentum[i]) * 10
                        trend[i] = trend[i-1] - (step_size * accel_factor)
                    else:
                        trend[i] = trend[i-1]

        # Tighter channel bands
        upper_band = trend + atr * self.band_multiplier
        lower_band = trend - atr * self.band_multiplier

        return trend, upper_band, lower_band, direction, momentum

    def generate_signals(self, close, high, low, trend, upper_band, lower_band, direction, momentum):
        """
        Generate more frequent signals with tighter criteria
        """
        n = len(close)
        long_signals = np.zeros(n)
        short_signals = np.zeros(n)

        for i in range(3, n):
            if np.isnan(trend[i]) or np.isnan(direction[i]):
                continue

            # Trend flip signals
            if direction[i] != direction[i-1]:
                if direction[i] > 0:
                    long_signals[i] = 3  # Strongest signal
                else:
                    short_signals[i] = 3

            # Quick retest signals (no trend filter)
            # Buy on any touch of lower band
            if low[i] <= lower_band[i] and close[i] > lower_band[i]:
                long_signals[i] = max(long_signals[i], 2)

            # Sell on any touch of upper band
            if high[i] >= upper_band[i] and close[i] < upper_band[i]:
                short_signals[i] = max(short_signals[i], 2)

            # Momentum burst signals
            if abs(momentum[i]) > self.momentum_threshold * 2:
                if momentum[i] > 0 and direction[i] > 0:
                    long_signals[i] = max(long_signals[i], 1.5)
                elif momentum[i] < 0 and direction[i] < 0:
                    short_signals[i] = max(short_signals[i], 1.5)

            # Trend continuation signals (more aggressive)
            if direction[i] > 0 and close[i] > trend[i] and close[i-1] <= trend[i-1]:
                long_signals[i] = max(long_signals[i], 1)
            elif direction[i] < 0 and close[i] < trend[i] and close[i-1] >= trend[i-1]:
                short_signals[i] = max(short_signals[i], 1)

        return long_signals, short_signals

    def init(self):
        """Initialize indicators"""
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Calculate ATR
        atr = ta.atr(high, low, close, length=self.atr_period)

        # Ensure arrays are same length as data
        atr_full = np.full(len(close), np.nan)
        if atr is not None and len(atr) > 0:
            atr_full[-len(atr):] = atr.values

        # Calculate trend impulse channels with momentum
        trend, upper_band, lower_band, direction, momentum = self.calculate_trend_impulse(
            close.values, high.values, low.values, atr_full
        )

        # Generate trading signals
        long_signals, short_signals = self.generate_signals(
            close.values, high.values, low.values,
            trend, upper_band, lower_band, direction, momentum
        )

        # Store as indicators
        self.trend = self.I(lambda: trend)
        self.upper_band = self.I(lambda: upper_band)
        self.lower_band = self.I(lambda: lower_band)
        self.direction = self.I(lambda: direction)
        self.momentum = self.I(lambda: momentum)
        self.long_signals = self.I(lambda: long_signals)
        self.short_signals = self.I(lambda: short_signals)
        self.atr = self.I(lambda: atr_full)

    def next(self):
        """Execute tight trading logic with quick exits"""
        # Skip if indicators not ready
        if np.isnan(self.trend[-1]) or np.isnan(self.atr[-1]):
            return

        current_price = self.data.Close[-1]

        # Position management with tighter exits
        if self.position:
            # Quick exit on trend reversal
            if self.position.is_long and self.direction[-1] < 0:
                self.position.close()
            elif self.position.is_short and self.direction[-1] > 0:
                self.position.close()

            # Tighter trailing stops
            if self.position.is_long:
                # Use tighter stop - halfway to lower band
                quick_stop = self.trend[-1] - (self.atr[-1] * self.band_multiplier * self.quick_exit_multiplier)
                if current_price < quick_stop:
                    self.position.close()

                # Take quick profit on momentum exhaustion
                if self.momentum[-1] < -self.momentum_threshold:
                    self.position.close()

            elif self.position.is_short:
                # Use tighter stop - halfway to upper band
                quick_stop = self.trend[-1] + (self.atr[-1] * self.band_multiplier * self.quick_exit_multiplier)
                if current_price > quick_stop:
                    self.position.close()

                # Take quick profit on momentum exhaustion
                if self.momentum[-1] > self.momentum_threshold:
                    self.position.close()

        else:
            # Entry signals with scaled sizing based on signal strength
            if self.long_signals[-1] > 0:
                signal_strength = min(3, self.long_signals[-1])  # Cap signal strength

                # Tighter stops for scalping
                sl_adjustment = self.stop_loss / max(1, signal_strength)
                sl_price = current_price * (1 - sl_adjustment)

                # Use halfway point as stop only if it's below current price
                alt_stop = self.trend[-1] - (self.atr[-1] * self.band_multiplier * 0.5)
                if not np.isnan(alt_stop) and alt_stop < current_price:
                    sl_price = max(sl_price, alt_stop)

                # Ensure stop is below current price
                sl_price = min(sl_price, current_price * 0.99)

                # Smaller targets for quicker profits
                tp_adjustment = self.take_profit * min(1.5, signal_strength / 2)
                tp_price = current_price * (1 + tp_adjustment)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            elif self.short_signals[-1] > 0:
                signal_strength = min(3, self.short_signals[-1])  # Cap signal strength

                # Tighter stops for scalping (SL above current price for shorts)
                sl_adjustment = self.stop_loss / max(1, signal_strength)
                sl_price = current_price * (1 + sl_adjustment)

                # Use halfway point as stop only if it's above current price
                alt_stop = self.trend[-1] + (self.atr[-1] * self.band_multiplier * 0.5)
                if not np.isnan(alt_stop) and alt_stop > current_price:
                    sl_price = max(sl_price, alt_stop)

                # Ensure stop is above current price
                sl_price = max(sl_price, current_price * 1.01)

                # Smaller targets for quicker profits (TP below current price for shorts)
                tp_adjustment = self.take_profit * min(1.5, signal_strength / 2)
                tp_price = current_price * (1 - tp_adjustment)

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

# Run single backtest
bt = Backtest(data, TrendImpulseTight, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND IMPULSE TIGHT - SCALPING PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD} (Shorter for responsiveness)")
print(f"Trigger Threshold: {TRIGGER_THRESHOLD} (Lower for more signals)")
print(f"Max Step Size: {MAX_STEP_SIZE} (Larger for faster following)")
print(f"Band Multiplier: {BAND_MULTIPLIER} (Tighter channels)")
print(f"Trend Hold: {TREND_HOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND IMPULSE TIGHT ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendImpulseTight, 'TrendImpulseTight')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendImpulseTight.csv")