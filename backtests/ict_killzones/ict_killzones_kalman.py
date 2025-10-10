"""
ICT Killzones & Pivots Strategy - Kalman Filter Enhanced Version
================================================================
Combines ICT killzone concepts with Kalman Filter for noise reduction
and better trend estimation within session boundaries.
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from datetime import time

print("🚀 Moon Dev's ICT Killzones + Kalman Filter Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 1.4
SESSION_BREAKOUT_THRESHOLD = 0.45
PIVOT_RANGE_PERCENT = 0.35
KALMAN_GAIN = 0.1  # Process noise / measurement noise ratio
KALMAN_SMOOTHING = 0.05  # Additional smoothing factor
DIVERGENCE_THRESHOLD = 0.5  # % divergence between price and Kalman

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ICTKillzonesKalman(Strategy):
    # Strategy parameters
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    session_threshold = SESSION_BREAKOUT_THRESHOLD / 100
    pivot_range = PIVOT_RANGE_PERCENT / 100
    kalman_gain = KALMAN_GAIN
    kalman_smooth = KALMAN_SMOOTHING
    divergence_thresh = DIVERGENCE_THRESHOLD / 100

    def kalman_filter(self, prices, gain=0.1, smooth=0.05):
        """Apply Kalman filter to price series"""
        n = len(prices)
        kalman = np.zeros(n)

        # Initialize
        kalman[0] = prices[0]
        error_est = 1.0

        for i in range(1, n):
            # Prediction
            prediction = kalman[i-1]

            # Update based on new measurement
            error = prices[i] - prediction

            # Kalman gain calculation
            k_gain = error_est / (error_est + gain)

            # Correction
            kalman[i] = prediction + k_gain * error

            # Update error estimate
            error_est = (1 - k_gain) * error_est + smooth

        return kalman

    def init(self):
        """Initialize indicators and session tracking"""
        # Calculate pivot points (standard pivots)
        high = self.data.High
        low = self.data.Low
        close = self.data.Close
        volume = self.data.Volume

        # Daily pivot calculations
        self.pivot_point = self.I(lambda: (high + low + close) / 3)
        self.resistance1 = self.I(lambda: 2 * self.pivot_point - low)
        self.resistance2 = self.I(lambda: self.pivot_point + (high - low))
        self.resistance3 = self.I(lambda: high + 2 * (self.pivot_point - low))
        self.support1 = self.I(lambda: 2 * self.pivot_point - high)
        self.support2 = self.I(lambda: self.pivot_point - (high - low))
        self.support3 = self.I(lambda: low - 2 * (high - self.pivot_point))

        # Kalman filtered prices
        close_array = close.values if hasattr(close, 'values') else close
        self.kalman_close = self.I(lambda: self.kalman_filter(close_array, self.kalman_gain, self.kalman_smooth))

        # Kalman filtered high/low for better extremes
        high_array = high.values if hasattr(high, 'values') else high
        low_array = low.values if hasattr(low, 'values') else low
        self.kalman_high = self.I(lambda: self.kalman_filter(high_array, self.kalman_gain * 0.5, self.kalman_smooth * 0.5))
        self.kalman_low = self.I(lambda: self.kalman_filter(low_array, self.kalman_gain * 0.5, self.kalman_smooth * 0.5))

        # Kalman trend (difference between fast and slow Kalman)
        self.kalman_fast = self.I(lambda: self.kalman_filter(close_array, self.kalman_gain * 2, self.kalman_smooth))
        self.kalman_slow = self.I(lambda: self.kalman_filter(close_array, self.kalman_gain * 0.5, self.kalman_smooth * 2))

        # Standard indicators for confirmation
        self.rsi = self.I(talib.RSI, close, 14)
        self.bb_upper = self.I(lambda: talib.BBANDS(close, 20, 2.0, 2.0)[0])
        self.bb_middle = self.I(lambda: talib.BBANDS(close, 20, 2.0, 2.0)[1])
        self.bb_lower = self.I(lambda: talib.BBANDS(close, 20, 2.0, 2.0)[2])

        # Volume indicators
        self.volume_sma = self.I(talib.SMA, volume, 20)
        self.volume_std = self.I(talib.STDDEV, volume, 20)

        # ATR for dynamic stops
        self.atr = self.I(talib.ATR, high, low, close, 14)

        # MACD for momentum
        self.macd = self.I(lambda: talib.MACD(close, 12, 26, 9)[0])
        self.macd_signal = self.I(lambda: talib.MACD(close, 12, 26, 9)[1])

        # Track session highs and lows
        self.session_highs = []
        self.session_lows = []
        self.current_session = None
        self.session_high = 0
        self.session_low = float('inf')
        self.session_kalman_high = 0
        self.session_kalman_low = float('inf')

    def get_killzone(self, current_time):
        """Determine which killzone we're in based on time"""
        hour = current_time.hour

        # Killzone definitions (simplified for hourly data)
        if 0 <= hour < 4:
            return 'ASIA'
        elif 7 <= hour < 10:
            return 'LONDON'
        elif 12 <= hour < 15:
            return 'NY_AM'
        elif 15 <= hour < 17:
            return 'NY_LUNCH'
        elif 17 <= hour < 20:
            return 'NY_PM'
        else:
            return None

    def calculate_divergence(self, price, kalman):
        """Calculate divergence between price and Kalman filter"""
        if kalman == 0:
            return 0
        return (price - kalman) / kalman

    def next(self):
        """Trading logic based on ICT concepts with Kalman Filter enhancement"""
        # Get current time and killzone
        current_time = self.data.index[-1]
        killzone = self.get_killzone(current_time)

        # Track session highs and lows
        if killzone != self.current_session:
            # New session started
            if self.current_session is not None:
                # Store previous session's high/low
                self.session_highs.append(self.session_high)
                self.session_lows.append(self.session_low)

            # Reset for new session
            self.current_session = killzone
            self.session_high = self.data.High[-1]
            self.session_low = self.data.Low[-1]
            if len(self.kalman_high) > 0:
                self.session_kalman_high = self.kalman_high[-1]
                self.session_kalman_low = self.kalman_low[-1]
        else:
            # Update current session high/low
            if killzone is not None:
                self.session_high = max(self.session_high, self.data.High[-1])
                self.session_low = min(self.session_low, self.data.Low[-1])
                if len(self.kalman_high) > 0:
                    self.session_kalman_high = max(self.session_kalman_high, self.kalman_high[-1])
                    self.session_kalman_low = min(self.session_kalman_low, self.kalman_low[-1])

        # Skip if not in a killzone
        if killzone is None:
            return

        # Get current price and indicators
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]

        # Check if we have enough data
        if len(self.kalman_close) < 20 or len(self.atr) < 14:
            return

        kalman_price = self.kalman_close[-1]
        kalman_high_val = self.kalman_high[-1]
        kalman_low_val = self.kalman_low[-1]
        kalman_fast_val = self.kalman_fast[-1]
        kalman_slow_val = self.kalman_slow[-1]

        atr_value = self.atr[-1]
        volume_avg = self.volume_sma[-1]
        volume_std_val = self.volume_std[-1] if len(self.volume_std) > 0 else 0

        rsi_value = self.rsi[-1] if len(self.rsi) > 13 else 50
        bb_upper_val = self.bb_upper[-1] if len(self.bb_upper) > 0 else current_price * 1.02
        bb_lower_val = self.bb_lower[-1] if len(self.bb_lower) > 0 else current_price * 0.98
        bb_middle_val = self.bb_middle[-1] if len(self.bb_middle) > 0 else current_price

        macd_val = self.macd[-1] if len(self.macd) > 0 else 0
        macd_sig = self.macd_signal[-1] if len(self.macd_signal) > 0 else 0

        pivot = self.pivot_point[-1]
        r1 = self.resistance1[-1]
        r2 = self.resistance2[-1]
        r3 = self.resistance3[-1]
        s1 = self.support1[-1]
        s2 = self.support2[-1]
        s3 = self.support3[-1]

        # Calculate divergences and trends
        price_divergence = self.calculate_divergence(current_price, kalman_price)
        kalman_trend = kalman_fast_val - kalman_slow_val
        kalman_momentum = kalman_price - self.kalman_close[-2] if len(self.kalman_close) > 1 else 0

        # Check for Kalman trend changes
        kalman_turning_up = kalman_momentum > 0 and kalman_trend > 0
        kalman_turning_down = kalman_momentum < 0 and kalman_trend < 0

        # Entry logic with Kalman Filter confirmation
        if not self.position:
            # Market state analysis
            above_pivot = current_price > pivot
            above_kalman = current_price > kalman_price
            kalman_bullish = kalman_fast_val > kalman_slow_val
            kalman_bearish = kalman_fast_val < kalman_slow_val
            macd_bullish = macd_val > macd_sig
            macd_bearish = macd_val < macd_sig

            # Volume anomaly detection
            volume_spike = current_volume > volume_avg + (1.5 * volume_std_val) if volume_std_val > 0 else False

            # Long conditions
            long_signal = False

            # 1. Kalman breakout with session high
            if self.session_high > 0 and current_price > self.session_high * (1 + self.session_threshold):
                if kalman_bullish and price_divergence < self.divergence_thresh:
                    if current_volume > volume_avg * 1.2 or volume_spike:
                        long_signal = True

            # 2. Kalman reversal at support with convergence
            elif killzone in ['LONDON', 'NY_AM'] and above_pivot:
                support_touch = abs(current_price - s1) / s1 < self.pivot_range
                if support_touch and kalman_turning_up:
                    if price_divergence < -self.divergence_thresh:  # Oversold divergence
                        if rsi_value < 40:
                            long_signal = True

            # 3. Kalman trend continuation after pullback
            elif kalman_bullish and killzone == 'NY_AM':
                if current_price > kalman_price and kalman_momentum > 0:
                    if current_price < bb_middle_val and current_price > bb_lower_val:
                        if macd_bullish:
                            long_signal = True

            # 4. Asia range breakout with Kalman confirmation
            elif killzone == 'LONDON' and len(self.session_highs) > 0:
                asia_high = self.session_highs[-1] if self.session_highs else self.session_high
                if current_price > asia_high:
                    if kalman_price > self.session_kalman_high:
                        if kalman_trend > 0:
                            long_signal = True

            # 5. Kalman squeeze breakout
            elif abs(price_divergence) < 0.001:  # Price and Kalman converged
                if kalman_turning_up and current_volume > volume_avg:
                    if current_price > pivot:
                        long_signal = True

            # Short conditions
            short_signal = False

            # 1. Kalman breakdown with session low
            if self.session_low < float('inf') and current_price < self.session_low * (1 - self.session_threshold):
                if kalman_bearish and price_divergence > -self.divergence_thresh:
                    if current_volume > volume_avg * 1.2 or volume_spike:
                        short_signal = True

            # 2. Kalman reversal at resistance with divergence
            elif killzone in ['LONDON', 'NY_AM'] and not above_pivot:
                resistance_touch = abs(current_price - r1) / r1 < self.pivot_range
                if resistance_touch and kalman_turning_down:
                    if price_divergence > self.divergence_thresh:  # Overbought divergence
                        if rsi_value > 60:
                            short_signal = True

            # 3. Kalman trend continuation after rally
            elif kalman_bearish and killzone == 'NY_AM':
                if current_price < kalman_price and kalman_momentum < 0:
                    if current_price > bb_middle_val and current_price < bb_upper_val:
                        if macd_bearish:
                            short_signal = True

            # 4. NY PM exhaustion with Kalman divergence
            elif killzone == 'NY_PM':
                if price_divergence > self.divergence_thresh and current_price > r2:
                    if kalman_turning_down:
                        if volume_spike:  # Climax volume
                            short_signal = True
                elif price_divergence < -self.divergence_thresh and current_price < s2:
                    if kalman_turning_up:  # Potential reversal
                        long_signal = True

            # 5. Kalman mean reversion
            elif abs(price_divergence) > self.divergence_thresh * 2:
                if price_divergence > 0 and kalman_trend < 0:  # Price too high
                    if current_price > bb_upper_val:
                        short_signal = True
                elif price_divergence < 0 and kalman_trend > 0:  # Price too low
                    if current_price < bb_lower_val:
                        long_signal = True

            # Execute trades with Kalman-adjusted stops
            if long_signal:
                # Simple ATR-based stops
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)

                # Ensure proper order: SL < Entry < TP for longs
                if sl_price >= current_price or tp_price <= current_price:
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            elif short_signal:
                # Simple percentage-based stops
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)

                # Ensure proper order: TP < Entry < SL for shorts
                if tp_price >= current_price or sl_price <= current_price:
                    tp_price = current_price * (1 - self.take_profit)
                    sl_price = current_price * (1 + self.stop_loss)

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

# Run single backtest (default behavior)
bt = Backtest(data, ICTKillzonesKalman, cash=10000000, commission=0.00045)

print("\n🌙 ===== ICT KILLZONES + KALMAN - DEFAULT PARAMETERS ===== 🌙")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Session Breakout Threshold: {SESSION_BREAKOUT_THRESHOLD}%")
print(f"Kalman Gain: {KALMAN_GAIN}")
print(f"Kalman Smoothing: {KALMAN_SMOOTHING}")
print(f"Divergence Threshold: {DIVERGENCE_THRESHOLD}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ICT KILLZONES + KALMAN ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(ICTKillzonesKalman, 'ICTKillzonesKalman')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ICTKillzonesKalman.csv")