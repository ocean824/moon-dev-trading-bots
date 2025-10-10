"""
Ichimoku Theories Trading Strategy - Kalman Filter Enhanced Version
====================================================================
Combines Ichimoku Cloud with Kalman Filter for noise reduction and trend extraction.

Enhancements:
- Kalman Filter for price smoothing and trend detection
- Reduced false signals through noise filtering
- Better trend estimation and prediction
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Ichimoku + Kalman Filter Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Ichimoku parameters
TENKAN_PERIOD = 9
KIJUN_PERIOD = 26
SENKOU_SPAN_B_PERIOD = 52
CHIKOU_PERIOD = 26

# Kalman Filter parameters
KALMAN_GAIN = 0.05  # Process noise covariance
KALMAN_SMOOTH = 0.01  # Measurement noise covariance

# Risk management
TAKE_PROFIT_PERCENT = 6.0
STOP_LOSS_PERCENT = 3.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

def kalman_filter(prices, process_variance=0.05, measurement_variance=0.01):
    """
    Simple 1D Kalman filter for price smoothing
    """
    n = len(prices)
    filtered = np.zeros(n)

    # Initial estimates
    estimate = prices[0]
    error_estimate = 1.0

    for i in range(n):
        # Prediction step
        prediction = estimate
        error_prediction = error_estimate + process_variance

        # Update step
        kalman_gain = error_prediction / (error_prediction + measurement_variance)
        estimate = prediction + kalman_gain * (prices[i] - prediction)
        error_estimate = (1 - kalman_gain) * error_prediction

        filtered[i] = estimate

    return pd.Series(filtered, index=prices.index)

def adaptive_kalman_filter(prices, high, low, volume):
    """
    Adaptive Kalman filter that adjusts based on market volatility
    """
    n = len(prices)
    filtered = np.zeros(n)

    # Calculate volatility for adaptive parameters
    atr = ta.atr(high, low, prices, length=14)
    if atr is None or atr.isna().all():
        atr = pd.Series([1.0] * n)

    # Normalize ATR for adaptive parameters
    atr_normalized = atr / atr.rolling(50).mean()
    atr_normalized = atr_normalized.fillna(1.0)

    # Initial estimates
    estimate = prices.iloc[0]
    error_estimate = 1.0

    for i in range(n):
        # Adaptive parameters based on volatility
        process_variance = 0.05 * atr_normalized.iloc[i] if i < len(atr_normalized) else 0.05
        measurement_variance = 0.01 / max(atr_normalized.iloc[i], 0.1) if i < len(atr_normalized) else 0.01

        # Prediction step
        prediction = estimate
        error_prediction = error_estimate + process_variance

        # Update step
        kalman_gain = error_prediction / (error_prediction + measurement_variance)
        estimate = prediction + kalman_gain * (prices.iloc[i] - prediction)
        error_estimate = (1 - kalman_gain) * error_prediction

        filtered[i] = estimate

    return pd.Series(filtered, index=prices.index)

class IchimokuKalman(Strategy):
    # Ichimoku parameters
    tenkan_period = TENKAN_PERIOD
    kijun_period = KIJUN_PERIOD
    senkou_span_b_period = SENKOU_SPAN_B_PERIOD
    chikou_period = CHIKOU_PERIOD

    # Kalman parameters
    kalman_gain = KALMAN_GAIN
    kalman_smooth = KALMAN_SMOOTH

    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        # Calculate Ichimoku Cloud components
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Apply Kalman filter to price data for smoother signals
        close_filtered = kalman_filter(close, self.kalman_gain, self.kalman_smooth)
        high_filtered = kalman_filter(high, self.kalman_gain, self.kalman_smooth)
        low_filtered = kalman_filter(low, self.kalman_gain, self.kalman_smooth)

        # Tenkan-sen using filtered data
        self.tenkan_sen = self.I(lambda: (
            high_filtered.rolling(self.tenkan_period).max() +
            low_filtered.rolling(self.tenkan_period).min()
        ) / 2)

        # Kijun-sen using filtered data
        self.kijun_sen = self.I(lambda: (
            high_filtered.rolling(self.kijun_period).max() +
            low_filtered.rolling(self.kijun_period).min()
        ) / 2)

        # Original Ichimoku components for comparison
        self.tenkan_sen_raw = self.I(lambda: (
            high.rolling(self.tenkan_period).max() +
            low.rolling(self.tenkan_period).min()
        ) / 2)

        self.kijun_sen_raw = self.I(lambda: (
            high.rolling(self.kijun_period).max() +
            low.rolling(self.kijun_period).min()
        ) / 2)

        # Senkou Span A (using filtered values)
        senkou_span_a_raw = (
            (high_filtered.rolling(self.tenkan_period).max() + low_filtered.rolling(self.tenkan_period).min()) / 2 +
            (high_filtered.rolling(self.kijun_period).max() + low_filtered.rolling(self.kijun_period).min()) / 2
        ) / 2
        self.senkou_span_a = self.I(lambda: senkou_span_a_raw.shift(-self.kijun_period))

        # Senkou Span B (using filtered values)
        senkou_span_b_raw = (
            high_filtered.rolling(self.senkou_span_b_period).max() +
            low_filtered.rolling(self.senkou_span_b_period).min()
        ) / 2
        self.senkou_span_b = self.I(lambda: senkou_span_b_raw.shift(-self.kijun_period))

        # Chikou Span (using actual close, not filtered)
        self.chikou_span = self.I(lambda: close.shift(self.chikou_period))

        # Cloud boundaries (current, using filtered data)
        self.cloud_top = self.I(lambda: np.maximum(
            (high_filtered.rolling(self.tenkan_period).max() + low_filtered.rolling(self.tenkan_period).min()) / 2,
            (high_filtered.rolling(self.senkou_span_b_period).max() + low_filtered.rolling(self.senkou_span_b_period).min()) / 2
        ))

        self.cloud_bottom = self.I(lambda: np.minimum(
            (high_filtered.rolling(self.tenkan_period).max() + low_filtered.rolling(self.tenkan_period).min()) / 2,
            (high_filtered.rolling(self.senkou_span_b_period).max() + low_filtered.rolling(self.senkou_span_b_period).min()) / 2
        ))

        # Kalman filtered price for signals
        self.price_kalman = self.I(lambda: close_filtered)

        # Adaptive Kalman filter for trend detection
        self.price_adaptive_kalman = self.I(lambda: adaptive_kalman_filter(close, high, low, volume))

        # Kalman trend (difference between fast and slow Kalman filters)
        fast_kalman = kalman_filter(close, 0.1, 0.01)
        slow_kalman = kalman_filter(close, 0.01, 0.01)
        self.kalman_trend = self.I(lambda: fast_kalman - slow_kalman)

        # Velocity and acceleration of Kalman filtered price
        self.kalman_velocity = self.I(lambda: close_filtered.diff())
        self.kalman_acceleration = self.I(lambda: close_filtered.diff().diff())

        # Additional indicators
        self.rsi = self.I(ta.rsi, close, 14)
        self.atr = self.I(ta.atr, high, low, close, 14)

        # Volume analysis with Kalman smoothing
        self.volume_kalman = self.I(lambda: kalman_filter(volume, 0.05, 0.01))
        self.volume_sma = self.I(ta.sma, volume, 20)

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < 52:  # Reduced from 200
            return

        # Current values
        current_price = self.data.Close[-1]
        price_kalman = self.price_kalman[-1]
        price_adaptive = self.price_adaptive_kalman[-1]
        tenkan = self.tenkan_sen[-1]
        kijun = self.kijun_sen[-1]
        tenkan_raw = self.tenkan_sen_raw[-1]
        kijun_raw = self.kijun_sen_raw[-1]
        cloud_top = self.cloud_top[-1]
        cloud_bottom = self.cloud_bottom[-1]
        kalman_trend = self.kalman_trend[-1]
        kalman_velocity = self.kalman_velocity[-1]
        kalman_acceleration = self.kalman_acceleration[-1]
        rsi = self.rsi[-1]
        atr = self.atr[-1]

        # Skip if any critical values are NaN
        if pd.isna(tenkan) or pd.isna(kijun) or pd.isna(cloud_top) or pd.isna(cloud_bottom) or pd.isna(price_kalman):
            return

        # Determine cloud characteristics
        cloud_is_bullish = cloud_top > cloud_bottom
        cloud_thickness = abs(cloud_top - cloud_bottom)

        # Price position relative to cloud (using Kalman filtered price)
        price_above_cloud = price_kalman > cloud_top
        price_below_cloud = price_kalman < cloud_bottom
        price_in_cloud = not price_above_cloud and not price_below_cloud

        # Kalman trend signals
        kalman_bullish = kalman_trend > 0 if not pd.isna(kalman_trend) else False
        kalman_accelerating = kalman_acceleration > 0 if not pd.isna(kalman_acceleration) else False
        kalman_momentum = kalman_velocity > 0 if not pd.isna(kalman_velocity) else False

        # Volume confirmation
        volume = self.data.Volume[-1]
        volume_kalman = self.volume_kalman[-1]
        volume_avg = self.volume_sma[-1]
        high_volume = volume_kalman > volume_avg * 1.1 if not pd.isna(volume_kalman) and not pd.isna(volume_avg) else False

        # Entry logic
        if not self.position:
            bullish_signal = False

            if len(self.data) > 3:
                tenkan_prev = self.tenkan_sen[-2]
                kijun_prev = self.kijun_sen[-2]
                price_kalman_prev = self.price_kalman[-2]
                kalman_trend_prev = self.kalman_trend[-2] if not pd.isna(self.kalman_trend[-2]) else 0

                if not pd.isna(tenkan_prev) and not pd.isna(kijun_prev) and not pd.isna(price_kalman_prev):
                    # TK Cross signals with Kalman confirmation
                    tk_cross_up = tenkan_prev <= kijun_prev and tenkan > kijun
                    tk_cross_down = tenkan_prev >= kijun_prev and tenkan < kijun

                    # Kalman trend reversal
                    kalman_trend_reversal = kalman_trend_prev <= 0 and kalman_trend > 0

                    # ULTRA RELAXED signals for maximum trades
                    # Signal 1: Any TK Cross
                    if tk_cross_up:
                        bullish_signal = True

                    # Signal 2: Kalman is positive
                    elif kalman_trend > 0:
                        bullish_signal = True

                    # Signal 3: Simple Tenkan > Kijun
                    elif tenkan > kijun:
                        bullish_signal = True

                    # Signal 4: Price above cloud bottom
                    elif current_price > cloud_bottom:
                        bullish_signal = True

                    # Signal 5: Kalman momentum
                    elif kalman_momentum:
                        bullish_signal = True

                    # Signal 6: Price above Kalman filter
                    elif current_price > price_kalman:
                        bullish_signal = True

                    # Signal 7: Simple price increase
                    elif current_price > self.data.Close[-2]:
                        bullish_signal = True

                    # Signal 8: Price above Kijun
                    elif current_price > kijun:
                        bullish_signal = True

            # Execute trades with Kalman-based stops
            if bullish_signal:
                # Use current price for entries, not Kalman filtered price
                if not pd.isna(atr) and atr > 0:
                    # Dynamic stops based on filtered volatility
                    volatility_mult = min(abs(kalman_velocity / atr), 3.0) if not pd.isna(kalman_velocity) else 1.0
                    sl_multiplier = 2.0 / max(volatility_mult, 0.5)
                    tp_multiplier = 3.0 * max(volatility_mult, 1.0)

                    # Use current_price for orders, not price_kalman
                    sl_price = current_price - (atr * sl_multiplier)
                    tp_price = current_price + (atr * tp_multiplier)
                else:
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)

                # Make sure SL is below current price
                if sl_price >= current_price:
                    sl_price = current_price * (1 - self.stop_loss)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

        # Exit logic for existing positions
        else:
            if self.position.is_long:
                should_exit = False

                # TK cross down with Kalman confirmation
                if tenkan < kijun and self.tenkan_sen[-2] >= self.kijun_sen[-2] and not kalman_bullish:
                    should_exit = True

                # Kalman trend reversal to bearish
                elif kalman_trend < 0 and self.kalman_trend[-2] >= 0 and kalman_velocity < 0:
                    should_exit = True

                # Kalman deceleration in uptrend (momentum loss)
                elif kalman_acceleration < -atr * 0.1 and kalman_velocity < 0:
                    should_exit = True

                # Price falls below Kalman filter with cloud weakness
                elif current_price < price_kalman * 0.98 and price_in_cloud:
                    should_exit = True

                # Cloud turned bearish with Kalman weakness
                elif not cloud_is_bullish and kalman_trend < 0:
                    should_exit = True

                # Divergence between actual and filtered price (high noise)
                price_diff = abs(current_price - price_kalman) / current_price
                if price_diff > 0.03 and not kalman_bullish:
                    should_exit = True

                if should_exit:
                    self.position.close()

# Run single backtest
bt = Backtest(data, IchimokuKalman, cash=1000000, commission=0.00045)

print("\n🌙 ===== ICHIMOKU + KALMAN FILTER STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Tenkan Period: {TENKAN_PERIOD}")
print(f"Kijun Period: {KIJUN_PERIOD}")
print(f"Kalman Gain: {KALMAN_GAIN}")
print(f"Kalman Smoothing: {KALMAN_SMOOTH}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ICHIMOKU + KALMAN FILTER STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(IchimokuKalman, 'IchimokuKalman')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/IchimokuKalman.csv")