"""
BE-Indicator Aggregator Toolkit - Kalman Filter Strategy
========================================================

This strategy enhances the BE-Indicator with Kalman filtering for noise reduction
and trend extraction. The Kalman filter provides smoother signals and better
trend detection by reducing market noise.

Key Enhancements:
- Kalman filtered price for smooth trend detection
- Reduced false signals from market noise
- Dynamic variance estimation for adaptive filtering
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta
import talib
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's BE-Indicator Kalman Filter Strategy Loading... 🌙")

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
TAKE_PROFIT_PERCENT = 3.2  # Moderate TP with smooth signals
STOP_LOSS_PERCENT = 1.6    # Tighter stop with cleaner signals
KALMAN_GAIN = 0.01         # Kalman filter gain parameter

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")


class BEIndicatorKalman(Strategy):
    """
    Kalman Filter enhanced implementation of BE-Indicator Aggregator

    Key features:
    1. Kalman filtered price series for all indicators
    2. Velocity estimation for momentum
    3. Uncertainty bands for dynamic thresholds
    4. Reduced noise in signal generation
    """

    # Strategy parameters
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    kalman_gain = KALMAN_GAIN

    # Indicator periods
    es1_period = 14  # RSI
    es2_period = 20  # SMA
    es3_period = 50  # EMA
    es4_period = 12  # MACD fast
    es5_period = 26  # MACD slow
    es6_period = 9   # MACD signal
    es7_period = 20  # BB period
    es8_period = 14  # Stochastic
    es9_period = 10  # CCI
    es10_period = 14 # ATR

    def kalman_filter(self, data, process_variance=1e-5, measurement_variance=1e-1):
        """
        Apply Kalman filter to reduce noise in price data

        Args:
            data: Input price series
            process_variance: Process noise covariance
            measurement_variance: Measurement noise covariance

        Returns:
            filtered: Kalman filtered prices
            velocity: Price velocity (rate of change)
            uncertainty: Estimation uncertainty
        """
        n = len(data)
        filtered = np.zeros(n)
        velocity = np.zeros(n)
        uncertainty = np.zeros(n)

        # Initial estimates
        x = np.array([[data[0]], [0]])  # [position, velocity]
        P = np.eye(2) * 1000  # Initial uncertainty

        # State transition matrix
        F = np.array([[1, 1], [0, 1]])

        # Measurement matrix
        H = np.array([[1, 0]])

        # Process noise covariance
        Q = np.array([[process_variance/4, process_variance/2],
                      [process_variance/2, process_variance]])

        # Measurement noise covariance
        R = np.array([[measurement_variance]])

        for i in range(n):
            # Prediction step
            x = F @ x
            P = F @ P @ F.T + Q

            # Update step
            z = np.array([[data[i]]])
            y = z - H @ x
            S = H @ P @ H.T + R
            K = P @ H.T @ np.linalg.inv(S)

            x = x + K @ y
            P = (np.eye(2) - K @ H) @ P

            # Store results
            filtered[i] = x[0, 0]
            velocity[i] = x[1, 0]
            uncertainty[i] = np.sqrt(P[0, 0])

        return filtered, velocity, uncertainty

    def init(self):
        """Initialize indicators with Kalman filtering"""

        # Prepare data series
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Apply Kalman filter to price
        close_array = close.values
        filtered_close, price_velocity, price_uncertainty = self.kalman_filter(close_array)

        # Create filtered series
        filtered_close = pd.Series(filtered_close, index=close.index)
        price_velocity = pd.Series(price_velocity, index=close.index)
        price_uncertainty = pd.Series(price_uncertainty, index=close.index)

        # Calculate uncertainty bands
        upper_band = filtered_close + 2 * price_uncertainty
        lower_band = filtered_close - 2 * price_uncertainty

        # ES1: RSI on filtered price
        self.es1_rsi = ta.rsi(filtered_close, length=self.es1_period)
        self.es1_rsi = self.es1_rsi.fillna(50).reindex(close.index, fill_value=50)

        # ES2: Kalman trend (filtered price vs original)
        self.es2_kalman_diff = ((close - filtered_close) / filtered_close * 100)
        self.es2_kalman_diff = self.es2_kalman_diff.fillna(0).reindex(close.index, fill_value=0)

        # ES3: Price velocity normalized
        velocity_ma = price_velocity.rolling(window=20).mean()
        velocity_std = price_velocity.rolling(window=20).std()
        self.es3_velocity_z = ((price_velocity - velocity_ma) / (velocity_std + 0.0001))
        self.es3_velocity = (self.es3_velocity_z * 20 + 50).clip(0, 100)
        self.es3_velocity = self.es3_velocity.fillna(50).reindex(close.index, fill_value=50)

        # ES4-ES5: MACD on filtered price
        macd_result = ta.macd(filtered_close, fast=self.es4_period, slow=self.es5_period, signal=self.es6_period)
        if macd_result is not None and len(macd_result.columns) >= 3:
            macd_line = macd_result.iloc[:, 0]
            macd_signal = macd_result.iloc[:, 2]
            self.es4_macd = ((macd_line - macd_line.min()) / (macd_line.max() - macd_line.min() + 0.0001) * 100)
            self.es4_macd = self.es4_macd.fillna(50).reindex(close.index, fill_value=50)
            self.es5_macd_signal = ((macd_signal - macd_signal.min()) / (macd_signal.max() - macd_signal.min() + 0.0001) * 100)
            self.es5_macd_signal = self.es5_macd_signal.fillna(50).reindex(close.index, fill_value=50)
        else:
            self.es4_macd = pd.Series(50, index=close.index)
            self.es5_macd_signal = pd.Series(50, index=close.index)

        # ES6: Position within uncertainty bands
        band_width = upper_band - lower_band
        self.es6_band_position = ((close - lower_band) / (band_width + 0.0001) * 100).clip(0, 100)
        self.es6_band_position = self.es6_band_position.fillna(50).reindex(close.index, fill_value=50)

        # ES7: Uncertainty level (normalized)
        uncertainty_ma = price_uncertainty.rolling(window=50).mean()
        self.es7_uncertainty = ((price_uncertainty / (uncertainty_ma + 0.0001)) * 50).clip(0, 100)
        self.es7_uncertainty = self.es7_uncertainty.fillna(50).reindex(close.index, fill_value=50)

        # ES8: Stochastic on filtered price
        # Create synthetic high/low based on filtered price
        filtered_high = filtered_close.rolling(window=self.es8_period).max()
        filtered_low = filtered_close.rolling(window=self.es8_period).min()
        stoch_result = ta.stoch(filtered_high, filtered_low, filtered_close, k=self.es8_period, d=3)
        if stoch_result is not None and len(stoch_result.columns) >= 1:
            self.es8_stoch = stoch_result.iloc[:, 0]
            self.es8_stoch = self.es8_stoch.fillna(50).reindex(close.index, fill_value=50)
        else:
            self.es8_stoch = pd.Series(50, index=close.index)

        # ES9: Acceleration (second derivative of Kalman filter)
        acceleration = price_velocity.diff()
        accel_ma = acceleration.rolling(window=20).mean()
        accel_std = acceleration.rolling(window=20).std()
        accel_z = ((acceleration - accel_ma) / (accel_std + 0.0001))
        self.es9_acceleration = (accel_z * 20 + 50).clip(0, 100)
        self.es9_acceleration = self.es9_acceleration.fillna(50).reindex(close.index, fill_value=50)

        # ES10: Volume-price divergence with Kalman
        volume_ma = volume.rolling(window=20).mean()
        volume_ratio = volume / (volume_ma + 1)
        # Check if volume confirms Kalman trend
        price_change = filtered_close.pct_change()
        volume_confirmation = pd.Series(np.where(
            (price_change > 0) & (volume_ratio > 1), 75,  # Bullish with volume
            np.where((price_change < 0) & (volume_ratio > 1), 25, 50)  # Bearish with volume
        ), index=close.index)
        self.es10_volume_confirm = ta.ema(volume_confirmation, length=5)
        self.es10_volume_confirm = self.es10_volume_confirm.fillna(50).reindex(close.index, fill_value=50)

        # Additional Kalman-specific indicators
        self.kalman_trend = pd.Series(np.where(
            price_velocity > price_velocity.rolling(window=10).mean(), 1,
            np.where(price_velocity < -price_velocity.rolling(window=10).mean(), -1, 0)
        ), index=close.index)

        # Signal quality based on uncertainty
        self.signal_quality = pd.Series(np.where(
            price_uncertainty < price_uncertainty.rolling(window=50).quantile(0.3), 100,  # High quality
            np.where(price_uncertainty > price_uncertainty.rolling(window=50).quantile(0.7), 0,  # Low quality
            50)  # Medium quality
        ), index=close.index)

        # Convert to numpy arrays
        self.es1 = self.I(lambda: self.es1_rsi.values)
        self.es2 = self.I(lambda: self.es2_kalman_diff.values)
        self.es3 = self.I(lambda: self.es3_velocity.values)
        self.es4 = self.I(lambda: self.es4_macd.values)
        self.es5 = self.I(lambda: self.es5_macd_signal.values)
        self.es6 = self.I(lambda: self.es6_band_position.values)
        self.es7 = self.I(lambda: self.es7_uncertainty.values)
        self.es8 = self.I(lambda: self.es8_stoch.values)
        self.es9 = self.I(lambda: self.es9_acceleration.values)
        self.es10 = self.I(lambda: self.es10_volume_confirm.values)

        # Kalman specific
        self.filtered_price = self.I(lambda: filtered_close.values)
        self.velocity = self.I(lambda: price_velocity.values)
        self.trend = self.I(lambda: self.kalman_trend.values)
        self.quality = self.I(lambda: self.signal_quality.values)

    def check_condition(self, source, operator, threshold):
        """Check a single condition"""
        if operator == 'G':
            return source > threshold
        elif operator == 'L':
            return source < threshold
        elif operator == 'E':
            return abs(source - threshold) < 1
        return False

    def evaluate_conditions(self, condition_type, conditions):
        """Evaluate complex condition logic"""
        results = [self.check_condition(src, op, thresh) for src, op, thresh in conditions]

        if condition_type == 'OR':
            return any(results)
        elif condition_type == 'AND':
            return all(results)
        elif condition_type.startswith('ATLEAST'):
            required = int(condition_type.replace('ATLEAST', ''))
            return sum(results) >= required
        return False

    def next(self):
        """
        Kalman-enhanced trading logic

        Rules:
        1. Use filtered signals for cleaner entries
        2. Require high signal quality (low uncertainty)
        3. Confirm with velocity and acceleration
        4. Dynamic thresholds based on uncertainty
        """

        if len(self.data) < 50:
            return

        # Get current values
        current_rsi = self.es1[-1]
        current_kalman_diff = self.es2[-1]
        current_velocity = self.es3[-1]
        current_macd = self.es4[-1]
        current_macd_signal = self.es5[-1]
        current_band_pos = self.es6[-1]
        current_uncertainty = self.es7[-1]
        current_stoch = self.es8[-1]
        current_acceleration = self.es9[-1]
        current_volume = self.es10[-1]

        # Kalman specific
        current_trend = self.trend[-1]
        current_quality = self.quality[-1]
        current_velocity_raw = self.velocity[-1]

        # Skip if indicators invalid or signal quality too low
        if any(pd.isna([current_rsi, current_velocity, current_macd])):
            return

        # Only trade with decent signal quality
        if current_quality < 25:
            return

        if not self.position:
            # LONG CONDITIONS with Kalman filtering
            long_conditions = [
                # Primary: Positive velocity with low uncertainty
                [(current_velocity, 'G', 55),
                 (current_uncertainty, 'L', 50),
                 (current_trend, 'E', 1),
                 (current_quality, 'G', 50)],

                # Oversold bounce with acceleration
                [(current_rsi, 'L', 35),
                 (current_acceleration, 'G', 55),
                 (current_band_pos, 'L', 30),
                 (current_velocity, 'G', 45)],

                # Strong momentum with MACD confirmation
                [(current_velocity, 'G', 60),
                 (current_macd, 'G', current_macd_signal),
                 (current_volume, 'G', 60),
                 (current_kalman_diff, 'L', 2)],  # Price near Kalman line

                # High quality reversal signal
                [(current_quality, 'G', 75),
                 (current_stoch, 'L', 25),
                 (current_acceleration, 'G', 60),
                 (current_trend, 'E', 1)]
            ]

            long_signal = False
            for condition_group in long_conditions:
                if self.evaluate_conditions('AND', condition_group):
                    long_signal = True
                    break

            # Alternative: Multiple Kalman confirmations
            kalman_bullish = [
                (current_velocity, 'G', 50),
                (current_acceleration, 'G', 50),
                (current_trend, 'E', 1),
                (current_band_pos, 'L', 40),
                (current_quality, 'G', 40),
                (current_macd, 'G', current_macd_signal)
            ]

            if not long_signal:
                long_signal = self.evaluate_conditions('ATLEAST3', kalman_bullish)

            # SHORT CONDITIONS with Kalman filtering
            short_conditions = [
                # Primary: Negative velocity with low uncertainty
                [(current_velocity, 'L', 45),
                 (current_uncertainty, 'L', 50),
                 (current_trend, 'E', -1),
                 (current_quality, 'G', 50)],

                # Overbought reversal with deceleration
                [(current_rsi, 'G', 65),
                 (current_acceleration, 'L', 45),
                 (current_band_pos, 'G', 70),
                 (current_velocity, 'L', 55)],

                # Weak momentum with MACD confirmation
                [(current_velocity, 'L', 40),
                 (current_macd, 'L', current_macd_signal),
                 (current_volume, 'G', 60),
                 (current_kalman_diff, 'G', -2)],  # Price away from Kalman line

                # High quality reversal signal
                [(current_quality, 'G', 75),
                 (current_stoch, 'G', 75),
                 (current_acceleration, 'L', 40),
                 (current_trend, 'E', -1)]
            ]

            short_signal = False
            for condition_group in short_conditions:
                if self.evaluate_conditions('AND', condition_group):
                    short_signal = True
                    break

            # Alternative: Multiple Kalman confirmations
            kalman_bearish = [
                (current_velocity, 'L', 50),
                (current_acceleration, 'L', 50),
                (current_trend, 'E', -1),
                (current_band_pos, 'G', 60),
                (current_quality, 'G', 40),
                (current_macd, 'L', current_macd_signal)
            ]

            if not short_signal:
                short_signal = self.evaluate_conditions('ATLEAST3', kalman_bearish)

            # Execute trades with dynamic adjustments
            current_price = self.data.Close[-1]
            filtered_price = self.filtered_price[-1]

            # Adjust stops based on uncertainty
            uncertainty_factor = 1 + (current_uncertainty / 100)

            if long_signal:
                # Use filtered price for better levels
                sl_price = min(current_price, filtered_price) * (1 - self.stop_loss * uncertainty_factor)
                tp_price = max(current_price, filtered_price) * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price, size=0.95)

            elif short_signal:
                # Use filtered price for better levels
                sl_price = max(current_price, filtered_price) * (1 + self.stop_loss * uncertainty_factor)
                tp_price = min(current_price, filtered_price) * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price, size=0.95)


# Run single backtest
bt = Backtest(data, BEIndicatorKalman, cash=10000000, commission=0.00045)

print("\n🌙 ===== BE-INDICATOR KALMAN FILTER STRATEGY ===== 🌙")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Kalman Gain: {KALMAN_GAIN}")
print("Noise reduction with Kalman filtering, velocity and acceleration analysis")

stats = bt.run()
print("\n" + "="*80)
print("BACKTEST RESULTS:")
print("="*80)
print(stats)
print("="*80)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING BE-INDICATOR KALMAN ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(BEIndicatorKalman, 'BEIndicatorKalman')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/BEIndicatorKalman.csv")