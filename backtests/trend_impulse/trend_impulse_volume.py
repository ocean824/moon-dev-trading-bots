"""
Moon Dev's Trend Impulse Channels Volume Strategy
==================================================
Volume-weighted step sizes and VWAP integration for institutional flow tracking.
Adapts channel width and step size based on volume patterns.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Impulse Channels Volume Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Trend Impulse parameters
ATR_PERIOD = 200
TRIGGER_THRESHOLD = 2.86
MAX_STEP_SIZE = 0.034
BAND_MULTIPLIER = 2.02
TREND_HOLD = 1

# Volume parameters
VOLUME_PERIOD = 20
VOLUME_THRESHOLD = 1.5  # Volume spike threshold
VWAP_PERIOD = 24  # Rolling VWAP period
OBV_SMOOTHING = 5  # OBV smoothing period

# Risk management
TAKE_PROFIT_PERCENT = 3.2
STOP_LOSS_PERCENT = 1.6

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendImpulseVolume(Strategy):
    """
    Trend Impulse Channels with Volume Analysis

    Enhancements:
    - Volume-weighted step sizes (larger steps on high volume)
    - VWAP as dynamic support/resistance
    - OBV trend confirmation
    - Volume profile analysis for key levels
    - Adaptive channel width based on volume volatility
    """

    # Core parameters
    atr_period = ATR_PERIOD
    trigger_threshold = TRIGGER_THRESHOLD
    max_step_size = MAX_STEP_SIZE
    band_multiplier = BAND_MULTIPLIER
    trend_hold = TREND_HOLD

    # Volume parameters
    volume_period = VOLUME_PERIOD
    volume_threshold = VOLUME_THRESHOLD
    vwap_period = VWAP_PERIOD
    obv_smoothing = OBV_SMOOTHING

    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def calculate_volume_metrics(self, close, volume, high, low):
        """Calculate volume-based indicators"""
        n = len(close)

        # Volume SMA and ratio
        volume_sma = np.full(n, np.nan)
        volume_ratio = np.ones(n)
        for i in range(self.volume_period, n):
            vol_window = volume[i-self.volume_period:i]
            if len(vol_window) > 0 and np.sum(vol_window) > 0:
                volume_sma[i] = np.mean(vol_window)
                if volume_sma[i] > 0:
                    volume_ratio[i] = volume[i] / volume_sma[i]

        # Calculate rolling VWAP
        vwap = np.full(n, np.nan)
        typical_price = (high + low + close) / 3
        for i in range(self.vwap_period, n):
            window_volume = volume[i-self.vwap_period:i]
            window_tp = typical_price[i-self.vwap_period:i]
            if np.sum(window_volume) > 0:
                vwap[i] = np.sum(window_tp * window_volume) / np.sum(window_volume)

        # Calculate OBV
        obv = np.zeros(n)
        obv[0] = volume[0]
        for i in range(1, n):
            if close[i] > close[i-1]:
                obv[i] = obv[i-1] + volume[i]
            elif close[i] < close[i-1]:
                obv[i] = obv[i-1] - volume[i]
            else:
                obv[i] = obv[i-1]

        # Smooth OBV
        obv_smooth = np.full(n, np.nan)
        for i in range(self.obv_smoothing, n):
            obv_smooth[i] = np.mean(obv[i-self.obv_smoothing:i])

        # OBV trend (positive = accumulation, negative = distribution)
        obv_trend = np.zeros(n)
        for i in range(1, n):
            if not np.isnan(obv_smooth[i]) and not np.isnan(obv_smooth[i-1]):
                obv_trend[i] = 1 if obv_smooth[i] > obv_smooth[i-1] else -1

        return volume_sma, volume_ratio, vwap, obv_smooth, obv_trend

    def calculate_volume_weighted_trend(self, close, high, low, atr, volume_ratio, obv_trend):
        """Calculate trend impulse with volume weighting"""
        n = len(close)
        trend = np.full(n, np.nan)
        direction = np.zeros(n)
        trend_hold_counter = np.zeros(n)
        volume_factor = np.ones(n)

        trend[0] = close[0]
        direction[0] = 1

        for i in range(1, n):
            if np.isnan(atr[i]):
                trend[i] = trend[i-1]
                direction[i] = direction[i-1]
                continue

            # Adjust trigger and step size based on volume
            volume_factor[i] = min(2.0, max(0.5, volume_ratio[i]))  # Cap between 0.5x and 2x

            # Volume-adjusted parameters
            trigger = atr[i] * self.trigger_threshold / volume_factor[i]  # Lower trigger on high volume
            step_size = min(atr[i] * self.max_step_size * volume_factor[i],  # Larger steps on high volume
                          abs(close[i] - trend[i-1]) * 0.15)

            # Check for trend flips with OBV confirmation
            flip_up = (close[i] > trend[i-1] + trigger and
                      direction[i-1] <= 0 and
                      obv_trend[i] > 0)  # Require positive OBV
            flip_down = (close[i] < trend[i-1] - trigger and
                        direction[i-1] >= 0 and
                        obv_trend[i] < 0)  # Require negative OBV

            # Apply trend hold
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
                direction[i] = 1
                trend[i] = close[i] - atr[i] * 0.5
            elif flip_down:
                direction[i] = -1
                trend[i] = close[i] + atr[i] * 0.5
            else:
                direction[i] = direction[i-1]

                # Volume-weighted stepping
                if direction[i] > 0:
                    if close[i] > trend[i-1]:
                        # Accelerate on volume surges
                        if volume_ratio[i] > self.volume_threshold:
                            trend[i] = trend[i-1] + (step_size * 1.5)
                        else:
                            trend[i] = trend[i-1] + step_size
                    else:
                        trend[i] = trend[i-1]
                else:
                    if close[i] < trend[i-1]:
                        # Accelerate on volume surges
                        if volume_ratio[i] > self.volume_threshold:
                            trend[i] = trend[i-1] - (step_size * 1.5)
                        else:
                            trend[i] = trend[i-1] - step_size
                    else:
                        trend[i] = trend[i-1]

        # Volume-adaptive channel bands
        upper_band = np.full(n, np.nan)
        lower_band = np.full(n, np.nan)
        for i in range(n):
            if not np.isnan(trend[i]) and not np.isnan(atr[i]):
                # Wider bands on high volume (institutional activity)
                band_adjust = 1.0 + (volume_factor[i] - 1.0) * 0.3
                upper_band[i] = trend[i] + atr[i] * self.band_multiplier * band_adjust
                lower_band[i] = trend[i] - atr[i] * self.band_multiplier * band_adjust

        return trend, upper_band, lower_band, direction, volume_factor

    def generate_volume_signals(self, close, high, low, trend, upper_band, lower_band,
                               direction, volume_ratio, vwap, obv_trend):
        """Generate signals with volume confirmation"""
        n = len(close)
        long_signals = np.zeros(n)
        short_signals = np.zeros(n)

        for i in range(3, n):
            if np.isnan(trend[i]) or np.isnan(vwap[i]):
                continue

            # Volume spike detection
            volume_spike = volume_ratio[i] > self.volume_threshold
            volume_dry = volume_ratio[i] < 0.7  # Low volume

            # VWAP position
            above_vwap = close[i] > vwap[i]
            below_vwap = close[i] < vwap[i]

            # LONG SIGNALS
            if direction[i] > 0:  # Uptrend
                # Strong: Trend flip with volume surge and OBV confirmation
                if direction[i] != direction[i-1] and volume_spike and obv_trend[i] > 0:
                    long_signals[i] = 3

                # Medium: VWAP reclaim with volume
                elif (close[i] > vwap[i] and close[i-1] <= vwap[i-1] and
                      volume_ratio[i] > 1.0 and obv_trend[i] > 0):
                    long_signals[i] = max(long_signals[i], 2.5)

                # Channel bounce with volume confirmation
                elif (low[i] <= lower_band[i] and close[i] > lower_band[i] and
                      volume_spike and above_vwap):
                    long_signals[i] = max(long_signals[i], 2)

                # Accumulation pattern (rising price on steady volume)
                elif (close[i] > trend[i] and obv_trend[i] > 0 and
                      volume_ratio[i] > 0.8 and volume_ratio[i] < 1.5):
                    long_signals[i] = max(long_signals[i], 1.5)

                # Breakout on volume
                elif (close[i] > upper_band[i-1] and volume_spike):
                    long_signals[i] = max(long_signals[i], 1)

            # SHORT SIGNALS
            if direction[i] < 0:  # Downtrend
                # Strong: Trend flip with volume surge and OBV confirmation
                if direction[i] != direction[i-1] and volume_spike and obv_trend[i] < 0:
                    short_signals[i] = 3

                # Medium: VWAP rejection with volume
                elif (close[i] < vwap[i] and close[i-1] >= vwap[i-1] and
                      volume_ratio[i] > 1.0 and obv_trend[i] < 0):
                    short_signals[i] = max(short_signals[i], 2.5)

                # Channel rejection with volume confirmation
                elif (high[i] >= upper_band[i] and close[i] < upper_band[i] and
                      volume_spike and below_vwap):
                    short_signals[i] = max(short_signals[i], 2)

                # Distribution pattern (falling price on steady volume)
                elif (close[i] < trend[i] and obv_trend[i] < 0 and
                      volume_ratio[i] > 0.8 and volume_ratio[i] < 1.5):
                    short_signals[i] = max(short_signals[i], 1.5)

                # Breakdown on volume
                elif (close[i] < lower_band[i-1] and volume_spike):
                    short_signals[i] = max(short_signals[i], 1)

            # Avoid signals on extremely low volume (likely false moves)
            if volume_dry:
                long_signals[i] = 0
                short_signals[i] = 0

        return long_signals, short_signals

    def init(self):
        """Initialize all indicators"""
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate ATR
        atr = ta.atr(high, low, close, length=self.atr_period)

        # Ensure arrays are same length as data
        atr_full = np.full(len(close), np.nan)
        if atr is not None and len(atr) > 0:
            atr_full[-len(atr):] = atr.values

        # Calculate volume metrics
        volume_sma, volume_ratio, vwap, obv_smooth, obv_trend = self.calculate_volume_metrics(
            close.values, volume.values, high.values, low.values
        )

        # Calculate volume-weighted trend impulse
        trend, upper_band, lower_band, direction, volume_factor = self.calculate_volume_weighted_trend(
            close.values, high.values, low.values, atr_full, volume_ratio, obv_trend
        )

        # Generate volume-confirmed signals
        long_signals, short_signals = self.generate_volume_signals(
            close.values, high.values, low.values,
            trend, upper_band, lower_band, direction,
            volume_ratio, vwap, obv_trend
        )

        # Store as indicators
        self.trend = self.I(lambda: trend)
        self.upper_band = self.I(lambda: upper_band)
        self.lower_band = self.I(lambda: lower_band)
        self.direction = self.I(lambda: direction)
        self.volume_ratio = self.I(lambda: volume_ratio)
        self.vwap = self.I(lambda: vwap)
        self.obv_trend = self.I(lambda: obv_trend)
        self.long_signals = self.I(lambda: long_signals)
        self.short_signals = self.I(lambda: short_signals)
        self.atr = self.I(lambda: atr_full)

    def next(self):
        """Execute trading logic with volume confirmation"""
        # Skip if indicators not ready
        if np.isnan(self.trend[-1]) or np.isnan(self.vwap[-1]):
            return

        current_price = self.data.Close[-1]

        # Position management
        if self.position:
            # Exit on trend reversal
            if self.position.is_long and self.direction[-1] < 0:
                self.position.close()
            elif self.position.is_short and self.direction[-1] > 0:
                self.position.close()

            # Volume-based exits
            if self.position.is_long:
                # Exit on distribution (negative OBV with price rise)
                if self.obv_trend[-1] < 0 and current_price > self.position.entry_price:
                    self.position.close()
                # Exit below VWAP and lower band
                elif current_price < self.vwap[-1] and current_price < self.lower_band[-1]:
                    self.position.close()
                # Trailing stop at lower band
                elif current_price < self.lower_band[-1]:
                    self.position.close()

            elif self.position.is_short:
                # Exit on accumulation (positive OBV with price fall)
                if self.obv_trend[-1] > 0 and current_price < self.position.entry_price:
                    self.position.close()
                # Exit above VWAP and upper band
                elif current_price > self.vwap[-1] and current_price > self.upper_band[-1]:
                    self.position.close()
                # Trailing stop at upper band
                elif current_price > self.upper_band[-1]:
                    self.position.close()

        else:
            # Entry signals with volume confirmation
            if self.long_signals[-1] > 0 and self.volume_ratio[-1] > 0.8:  # Require decent volume
                signal_strength = self.long_signals[-1]

                # Dynamic stops based on volume and signal
                sl_multiplier = self.stop_loss * (2 - min(1.5, self.volume_ratio[-1]))
                sl_price = current_price * (1 - sl_multiplier)
                # Use VWAP or lower band as stop if better
                sl_price = max(sl_price, min(self.vwap[-1] * 0.98, self.lower_band[-1]))

                # Scale targets with volume momentum
                tp_multiplier = self.take_profit * (1 + (self.volume_ratio[-1] - 1) * 0.3)
                tp_price = current_price * (1 + tp_multiplier)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            elif self.short_signals[-1] > 0 and self.volume_ratio[-1] > 0.8:  # Require decent volume
                signal_strength = self.short_signals[-1]

                # Dynamic stops based on volume and signal
                sl_multiplier = self.stop_loss * (2 - min(1.5, self.volume_ratio[-1]))
                sl_price = current_price * (1 + sl_multiplier)
                # Use VWAP or upper band as stop if wider (for shorts)
                sl_price = max(sl_price, max(self.vwap[-1] * 1.02, self.upper_band[-1]))

                # Scale targets with volume momentum
                tp_multiplier = self.take_profit * (1 + (self.volume_ratio[-1] - 1) * 0.3)
                tp_price = current_price * (1 - tp_multiplier)

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

# Run single backtest
bt = Backtest(data, TrendImpulseVolume, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND IMPULSE VOLUME - WITH VWAP & OBV ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"Volume Period: {VOLUME_PERIOD}")
print(f"Volume Threshold: {VOLUME_THRESHOLD}x")
print(f"VWAP Period: {VWAP_PERIOD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND IMPULSE VOLUME ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendImpulseVolume, 'TrendImpulseVolume')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendImpulseVolume.csv")