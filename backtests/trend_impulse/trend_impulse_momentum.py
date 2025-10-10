"""
Moon Dev's Trend Impulse Channels Momentum Strategy
====================================================
Combines Trend Impulse Channels with momentum filters (RSI, MACD)
for higher probability setups and trend confirmation.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Impulse Channels Momentum Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Trend Impulse parameters
ATR_PERIOD = 200
TRIGGER_THRESHOLD = 2.86
MAX_STEP_SIZE = 0.034
BAND_MULTIPLIER = 2.02
TREND_HOLD = 2  # Hold trend for 2 bars to confirm

# Momentum filter parameters
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Risk management
TAKE_PROFIT_PERCENT = 3.5  # Higher targets with confirmation
STOP_LOSS_PERCENT = 1.8  # Tighter stops with filters

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendImpulseMomentum(Strategy):
    """
    Trend Impulse Channels with Momentum Filters

    Enhancements:
    - RSI filter to avoid overbought/oversold extremes
    - MACD confirmation for trend direction
    - Divergence detection between price and momentum
    - Volume confirmation on breakouts
    """

    # Core parameters
    atr_period = ATR_PERIOD
    trigger_threshold = TRIGGER_THRESHOLD
    max_step_size = MAX_STEP_SIZE
    band_multiplier = BAND_MULTIPLIER
    trend_hold = TREND_HOLD

    # Momentum parameters
    rsi_period = RSI_PERIOD
    rsi_overbought = RSI_OVERBOUGHT
    rsi_oversold = RSI_OVERSOLD
    macd_fast = MACD_FAST
    macd_slow = MACD_SLOW
    macd_signal = MACD_SIGNAL

    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    # Additional filters
    volume_multiplier = 1.5
    divergence_lookback = 10

    def calculate_trend_impulse(self, close, high, low, atr):
        """Calculate trend impulse channels"""
        n = len(close)
        trend = np.full(n, np.nan)
        direction = np.zeros(n)
        trend_hold_counter = np.zeros(n)

        trend[0] = close[0]
        direction[0] = 1

        for i in range(1, n):
            if np.isnan(atr[i]):
                trend[i] = trend[i-1]
                direction[i] = direction[i-1]
                continue

            trigger = atr[i] * self.trigger_threshold
            step_size = min(atr[i] * self.max_step_size, abs(close[i] - trend[i-1]) * 0.1)

            flip_up = close[i] > trend[i-1] + trigger and direction[i-1] <= 0
            flip_down = close[i] < trend[i-1] - trigger and direction[i-1] >= 0

            # Apply trend hold with counter
            if flip_up or flip_down:
                trend_hold_counter[i] = trend_hold_counter[i-1] + 1
                if trend_hold_counter[i] < self.trend_hold:
                    flip_up = False
                    flip_down = False
                else:
                    trend_hold_counter[i] = 0
            else:
                trend_hold_counter[i] = 0

            if flip_up:
                direction[i] = 1
                trend[i] = close[i] - atr[i] * 0.5
            elif flip_down:
                direction[i] = -1
                trend[i] = close[i] + atr[i] * 0.5
            else:
                direction[i] = direction[i-1]
                if direction[i] > 0:
                    if close[i] > trend[i-1]:
                        trend[i] = trend[i-1] + step_size
                    else:
                        trend[i] = trend[i-1]
                else:
                    if close[i] < trend[i-1]:
                        trend[i] = trend[i-1] - step_size
                    else:
                        trend[i] = trend[i-1]

        upper_band = trend + atr * self.band_multiplier
        lower_band = trend - atr * self.band_multiplier

        return trend, upper_band, lower_band, direction

    def detect_divergence(self, price, indicator, lookback):
        """Detect bullish and bearish divergences"""
        n = len(price)
        bullish_div = np.zeros(n)
        bearish_div = np.zeros(n)

        for i in range(lookback * 2, n):
            # Get recent windows
            recent_price = price[i-lookback:i]
            recent_ind = indicator[i-lookback:i]
            prev_price = price[i-lookback*2:i-lookback]
            prev_ind = indicator[i-lookback*2:i-lookback]

            # Skip if any NaN values
            if np.any(np.isnan(recent_price)) or np.any(np.isnan(recent_ind)):
                continue
            if np.any(np.isnan(prev_price)) or np.any(np.isnan(prev_ind)):
                continue

            # Find peaks and troughs
            recent_price_min = np.min(recent_price)
            recent_price_max = np.max(recent_price)
            prev_price_min = np.min(prev_price)
            prev_price_max = np.max(prev_price)

            recent_ind_min = np.min(recent_ind)
            recent_ind_max = np.max(recent_ind)
            prev_ind_min = np.min(prev_ind)
            prev_ind_max = np.max(prev_ind)

            # Bullish divergence: price makes lower low, indicator makes higher low
            if recent_price_min < prev_price_min * 0.995 and recent_ind_min > prev_ind_min:
                bullish_div[i] = 1

            # Bearish divergence: price makes higher high, indicator makes lower high
            if recent_price_max > prev_price_max * 1.005 and recent_ind_max < prev_ind_max:
                bearish_div[i] = 1

        return bullish_div, bearish_div

    def generate_momentum_signals(self, close, high, low, trend, upper_band, lower_band,
                                 direction, rsi, macd_line, macd_signal, volume, volume_sma):
        """Generate signals with momentum confirmation"""
        n = len(close)
        long_signals = np.zeros(n)
        short_signals = np.zeros(n)

        # Detect RSI divergence
        rsi_bull_div, rsi_bear_div = self.detect_divergence(close, rsi, self.divergence_lookback)

        for i in range(3, n):
            if np.isnan(trend[i]) or np.isnan(rsi[i]) or np.isnan(macd_line[i]):
                continue

            # Calculate MACD histogram
            macd_hist = macd_line[i] - macd_signal[i]
            macd_hist_prev = macd_line[i-1] - macd_signal[i-1]

            # Volume confirmation
            volume_surge = volume[i] > volume_sma[i] * self.volume_multiplier if volume_sma[i] > 0 else False

            # LONG SIGNALS
            if direction[i] > 0:  # Uptrend
                # Strong signal: Trend flip with momentum confirmation
                if direction[i] != direction[i-1] and rsi[i] < 50 and macd_hist > 0:
                    long_signals[i] = 3

                # Medium signal: Oversold bounce with MACD turning up
                elif (rsi[i] < self.rsi_oversold and rsi[i] > rsi[i-1] and
                      macd_hist > macd_hist_prev):
                    long_signals[i] = max(long_signals[i], 2)

                # Divergence signal
                elif rsi_bull_div[i] == 1 and close[i] > lower_band[i]:
                    long_signals[i] = max(long_signals[i], 2)

                # Retest with momentum confirmation
                elif (low[i] <= lower_band[i] and close[i] > lower_band[i] and
                      rsi[i] > self.rsi_oversold and macd_hist > 0):
                    long_signals[i] = max(long_signals[i], 1.5)

                # Breakout with volume
                elif (close[i] > trend[i] and close[i-1] <= trend[i-1] and
                      volume_surge and rsi[i] < self.rsi_overbought - 10):
                    long_signals[i] = max(long_signals[i], 1)

            # SHORT SIGNALS
            if direction[i] < 0:  # Downtrend
                # Strong signal: Trend flip with momentum confirmation
                if direction[i] != direction[i-1] and rsi[i] > 50 and macd_hist < 0:
                    short_signals[i] = 3

                # Medium signal: Overbought reversal with MACD turning down
                elif (rsi[i] > self.rsi_overbought and rsi[i] < rsi[i-1] and
                      macd_hist < macd_hist_prev):
                    short_signals[i] = max(short_signals[i], 2)

                # Divergence signal
                elif rsi_bear_div[i] == 1 and close[i] < upper_band[i]:
                    short_signals[i] = max(short_signals[i], 2)

                # Retest with momentum confirmation
                elif (high[i] >= upper_band[i] and close[i] < upper_band[i] and
                      rsi[i] < self.rsi_overbought and macd_hist < 0):
                    short_signals[i] = max(short_signals[i], 1.5)

                # Breakdown with volume
                elif (close[i] < trend[i] and close[i-1] >= trend[i-1] and
                      volume_surge and rsi[i] > self.rsi_oversold + 10):
                    short_signals[i] = max(short_signals[i], 1)

        return long_signals, short_signals

    def init(self):
        """Initialize all indicators"""
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate ATR
        atr = ta.atr(high, low, close, length=self.atr_period)

        # Calculate RSI
        rsi = ta.rsi(close, length=self.rsi_period)

        # Calculate MACD
        macd = ta.macd(close, fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)

        # Volume SMA
        volume_sma = ta.sma(volume, length=20)

        # Ensure arrays are same length as data
        atr_full = np.full(len(close), np.nan)
        if atr is not None and len(atr) > 0:
            atr_full[-len(atr):] = atr.values

        rsi_full = np.full(len(close), np.nan)
        if rsi is not None and len(rsi) > 0:
            rsi_full[-len(rsi):] = rsi.values

        macd_line_full = np.full(len(close), np.nan)
        macd_signal_full = np.full(len(close), np.nan)
        if macd is not None and len(macd) > 0:
            macd_line_full[-len(macd):] = macd[f'MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'].values
            macd_signal_full[-len(macd):] = macd[f'MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'].values

        volume_sma_full = np.full(len(close), np.nan)
        if volume_sma is not None and len(volume_sma) > 0:
            volume_sma_full[-len(volume_sma):] = volume_sma.values

        # Calculate trend impulse channels
        trend, upper_band, lower_band, direction = self.calculate_trend_impulse(
            close.values, high.values, low.values, atr_full
        )

        # Generate momentum-filtered signals
        long_signals, short_signals = self.generate_momentum_signals(
            close.values, high.values, low.values,
            trend, upper_band, lower_band, direction,
            rsi_full, macd_line_full, macd_signal_full,
            volume.values, volume_sma_full
        )

        # Store as indicators
        self.trend = self.I(lambda: trend)
        self.upper_band = self.I(lambda: upper_band)
        self.lower_band = self.I(lambda: lower_band)
        self.direction = self.I(lambda: direction)
        self.rsi = self.I(lambda: rsi_full)
        self.macd_line = self.I(lambda: macd_line_full)
        self.macd_signal = self.I(lambda: macd_signal_full)
        self.long_signals = self.I(lambda: long_signals)
        self.short_signals = self.I(lambda: short_signals)
        self.atr = self.I(lambda: atr_full)

    def next(self):
        """Execute trading logic with momentum filters"""
        # Skip if indicators not ready
        if np.isnan(self.trend[-1]) or np.isnan(self.rsi[-1]) or np.isnan(self.macd_line[-1]):
            return

        current_price = self.data.Close[-1]
        macd_hist = self.macd_line[-1] - self.macd_signal[-1]

        # Position management
        if self.position:
            # Exit on trend reversal
            if self.position.is_long and self.direction[-1] < 0:
                self.position.close()
            elif self.position.is_short and self.direction[-1] > 0:
                self.position.close()

            # Exit on momentum exhaustion
            if self.position.is_long:
                # Exit if RSI overbought and declining
                if self.rsi[-1] > self.rsi_overbought and self.rsi[-1] < self.rsi[-2]:
                    self.position.close()
                # Exit if MACD turns negative
                elif macd_hist < 0 and self.macd_line[-1] < self.macd_line[-2]:
                    self.position.close()
                # Trailing stop at lower band
                elif current_price < self.lower_band[-1]:
                    self.position.close()

            elif self.position.is_short:
                # Exit if RSI oversold and rising
                if self.rsi[-1] < self.rsi_oversold and self.rsi[-1] > self.rsi[-2]:
                    self.position.close()
                # Exit if MACD turns positive
                elif macd_hist > 0 and self.macd_line[-1] > self.macd_line[-2]:
                    self.position.close()
                # Trailing stop at upper band
                elif current_price > self.upper_band[-1]:
                    self.position.close()

        else:
            # Entry signals with momentum confirmation
            if self.long_signals[-1] > 0:
                signal_strength = self.long_signals[-1]

                # Dynamic stops based on signal strength
                sl_multiplier = self.stop_loss * (2 - signal_strength / 3)
                sl_price = current_price * (1 - sl_multiplier)
                sl_price = max(sl_price, self.lower_band[-1])

                # Dynamic targets based on momentum
                tp_multiplier = self.take_profit * (1 + (self.rsi[-1] - 50) / 100)
                tp_price = current_price * (1 + tp_multiplier)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            elif self.short_signals[-1] > 0:
                signal_strength = self.short_signals[-1]

                # Dynamic stops based on signal strength
                sl_multiplier = self.stop_loss * (2 - signal_strength / 3)
                sl_price = current_price * (1 + sl_multiplier)
                sl_price = max(sl_price, self.upper_band[-1])  # For shorts, use max

                # Dynamic targets based on momentum
                tp_multiplier = self.take_profit * (1 + (50 - self.rsi[-1]) / 100)
                tp_price = current_price * (1 - tp_multiplier)

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

# Run single backtest
bt = Backtest(data, TrendImpulseMomentum, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND IMPULSE MOMENTUM - WITH RSI & MACD ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"Trigger Threshold: {TRIGGER_THRESHOLD}")
print(f"RSI Period: {RSI_PERIOD} (OB: {RSI_OVERBOUGHT}, OS: {RSI_OVERSOLD})")
print(f"MACD: {MACD_FAST}/{MACD_SLOW}/{MACD_SIGNAL}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND IMPULSE MOMENTUM ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendImpulseMomentum, 'TrendImpulseMomentum')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendImpulseMomentum.csv")