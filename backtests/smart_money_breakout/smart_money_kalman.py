"""
Smart Money Breakout Channels Strategy - Kalman Filter Enhanced
================================================================

Combines Smart Money channel breakouts with Kalman Filter for
noise reduction and improved signal quality.

Enhancements:
- Kalman filtered price for smoother channel detection
- Reduced false breakouts through noise filtering
- Trend prediction using Kalman state estimation
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Smart Money Breakout + Kalman Filter Strategy Loading... 🌙")

# Data configuration for single test
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
CHANNEL_LOOKBACK = 20          # Period for channel detection
VOLATILITY_THRESHOLD = 0.02    # Threshold for consolidation detection
VOLUME_LOOKBACK = 20           # Period for volume analysis
BREAKOUT_STRENGTH = 0.6        # Strong close requirement
ATR_PERIOD = 14                # ATR for stop loss
ATR_MULTIPLIER = 2.0           # Stop loss distance
TAKE_PROFIT_RATIO = 2.0        # Risk/Reward ratio
KALMAN_GAIN = 0.02             # Kalman filter gain (lower = smoother)
KALMAN_COVARIANCE = 0.0001    # Initial covariance

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

def kalman_filter(prices, kalman_gain=0.02, initial_covariance=0.0001):
    """
    Apply Kalman filter to price series for noise reduction
    """
    n = len(prices)
    filtered = np.zeros(n)

    # Initialize
    x_est = prices[0]  # Initial estimate
    p_est = initial_covariance  # Initial error covariance

    # Process noise and measurement noise
    q = kalman_gain  # Process noise covariance
    r = kalman_gain * 10  # Measurement noise covariance (higher = trust measurements less)

    for i in range(n):
        # Prediction step
        x_pred = x_est  # State prediction (assuming constant model)
        p_pred = p_est + q  # Error covariance prediction

        # Update step
        k_gain = p_pred / (p_pred + r)  # Kalman gain
        x_est = x_pred + k_gain * (prices[i] - x_pred)  # State update
        p_est = (1 - k_gain) * p_pred  # Error covariance update

        filtered[i] = x_est

    return filtered

class SmartMoneyKalman(Strategy):
    # Strategy parameters
    channel_lookback = CHANNEL_LOOKBACK
    volatility_threshold = VOLATILITY_THRESHOLD
    volume_lookback = VOLUME_LOOKBACK
    breakout_strength = BREAKOUT_STRENGTH
    atr_period = ATR_PERIOD
    atr_multiplier = ATR_MULTIPLIER
    take_profit_ratio = TAKE_PROFIT_RATIO
    kalman_gain = KALMAN_GAIN
    kalman_covariance = KALMAN_COVARIANCE

    def init(self):
        # Price and volatility calculations
        close = self.data.Close
        high = self.data.High
        low = self.data.Low
        volume = self.data.Volume

        # ATR for position sizing and stops
        self.atr = self.I(talib.ATR, high, low, close, self.atr_period)

        # Apply Kalman filter to prices
        self.kalman_close = self.I(kalman_filter, close, self.kalman_gain, self.kalman_covariance)
        self.kalman_high = self.I(kalman_filter, high, self.kalman_gain, self.kalman_covariance)
        self.kalman_low = self.I(kalman_filter, low, self.kalman_gain, self.kalman_covariance)

        # Kalman price velocity (rate of change)
        self.kalman_velocity = self.I(lambda: pd.Series(self.kalman_close).diff().values)

        # Kalman price acceleration (rate of velocity change)
        self.kalman_acceleration = self.I(lambda: pd.Series(self.kalman_velocity).diff().values)

        # Normalized volatility using Kalman filtered prices
        kalman_typical = (self.kalman_high + self.kalman_low + self.kalman_close) / 3
        kalman_range = self.kalman_high - self.kalman_low
        self.volatility = self.I(lambda: kalman_range / kalman_typical)

        # Volatility bands
        volatility_sma = self.I(talib.SMA, self.volatility, self.channel_lookback)
        volatility_std = self.I(lambda: pd.Series(self.volatility).rolling(self.channel_lookback).std().values)

        self.upper_vol_band = self.I(lambda: volatility_sma + (volatility_std * 1.5))
        self.lower_vol_band = self.I(lambda: volatility_sma - (volatility_std * 1.5))

        # Channel boundaries using Kalman filtered prices
        self.channel_high = self.I(talib.MAX, self.kalman_high, self.channel_lookback)
        self.channel_low = self.I(talib.MIN, self.kalman_low, self.channel_lookback)

        # Raw price channels for comparison
        self.raw_channel_high = self.I(talib.MAX, high, self.channel_lookback)
        self.raw_channel_low = self.I(talib.MIN, low, self.channel_lookback)

        # Volume analysis
        self.volume_sma = self.I(talib.SMA, volume, self.volume_lookback)
        self.volume_ratio = self.I(lambda: volume / self.volume_sma)

        # Up/Down volume
        close_diff = self.I(lambda: pd.Series(close).diff().values)
        self.up_volume = self.I(lambda: np.where(close_diff > 0, volume, 0))
        self.down_volume = self.I(lambda: np.where(close_diff < 0, volume, 0))

        # Volume delta
        self.volume_delta = self.I(lambda: self.up_volume - self.down_volume)

        # Noise level estimation (difference between raw and filtered)
        self.noise_level = self.I(lambda: np.abs(close - self.kalman_close) / close)
        self.avg_noise = self.I(talib.SMA, self.noise_level, 20)

    def predict_future_price(self, steps=1):
        """Use Kalman velocity and acceleration to predict future price"""
        if len(self.data) < 10:
            return self.kalman_close[-1]

        current_price = self.kalman_close[-1]
        current_velocity = self.kalman_velocity[-1] if self.kalman_velocity[-1] is not None else 0
        current_acceleration = self.kalman_acceleration[-1] if self.kalman_acceleration[-1] is not None else 0

        # Simple physics-based prediction
        predicted_price = current_price + (current_velocity * steps) + (0.5 * current_acceleration * steps**2)

        return predicted_price

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.channel_lookback * 2:
            return

        # Current values
        current_close = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        current_open = self.data.Open[-1]

        # Kalman filtered values
        kalman_close = self.kalman_close[-1]
        kalman_velocity = self.kalman_velocity[-1] if self.kalman_velocity[-1] is not None else 0

        # Channel values (Kalman filtered)
        channel_high = self.channel_high[-1]
        channel_low = self.channel_low[-1]
        channel_width = channel_high - channel_low

        # Raw channels for confirmation
        raw_channel_high = self.raw_channel_high[-1]
        raw_channel_low = self.raw_channel_low[-1]

        # Skip if channel is too narrow
        if channel_width < self.atr[-1] * 0.5:
            return

        # Get future price prediction
        predicted_price = self.predict_future_price(steps=3)

        # Noise level check - skip if market is too noisy
        current_noise = self.avg_noise[-1]
        if current_noise > 0.05:  # More than 5% noise
            return

        # Breakout detection using both raw and filtered prices
        body_size = abs(current_close - current_open)

        # Bullish breakout - use Kalman for signal, raw for confirmation
        kalman_bullish_breakout = kalman_close > channel_high
        raw_bullish_confirm = current_close > raw_channel_high * 0.99  # Small buffer

        bullish_breakout = kalman_bullish_breakout and raw_bullish_confirm

        if bullish_breakout and self.breakout_strength > 0:
            body_above = max(0, min(current_close, current_high) - raw_channel_high)
            strong_close = (body_above / body_size) > self.breakout_strength if body_size > 0 else False
            bullish_breakout = bullish_breakout and strong_close

        # Bearish breakout - use Kalman for signal, raw for confirmation
        kalman_bearish_breakout = kalman_close < channel_low
        raw_bearish_confirm = current_close < raw_channel_low * 1.01  # Small buffer

        bearish_breakout = kalman_bearish_breakout and raw_bearish_confirm

        if bearish_breakout and self.breakout_strength > 0:
            body_below = max(0, raw_channel_low - max(current_close, current_low))
            strong_close = (body_below / body_size) > self.breakout_strength if body_size > 0 else False
            bearish_breakout = bearish_breakout and strong_close

        # Volume confirmation
        volume_confirmation = self.volume_ratio[-1] > 1.2

        # Kalman trend confirmation
        kalman_trending_up = kalman_velocity > 0 and predicted_price > kalman_close
        kalman_trending_down = kalman_velocity < 0 and predicted_price < kalman_close

        # Position management
        if not self.position:
            # Long entry with Kalman confirmation
            if bullish_breakout and volume_confirmation:
                # Kalman filter conditions
                kalman_long_signal = (
                    kalman_trending_up and  # Positive velocity
                    current_noise < 0.03 and  # Low noise environment
                    predicted_price > channel_high  # Predicted continuation
                )

                if kalman_long_signal and self.volume_delta[-1] > 0:
                    # Adjust stops based on noise level
                    noise_adjustment = 1.0 + (current_noise * 2)  # Wider stops in noisy markets
                    stop_distance = self.atr[-1] * self.atr_multiplier * noise_adjustment
                    stop_price = current_close - stop_distance

                    # Dynamic take profit based on Kalman prediction
                    if predicted_price > current_close * 1.02:  # Strong prediction
                        tp_ratio = self.take_profit_ratio * 1.5
                    else:
                        tp_ratio = self.take_profit_ratio

                    target_price = current_close + (stop_distance * tp_ratio)

                    # Position size based on noise level
                    if current_noise < 0.02:  # Very clean signal
                        position_size = 1200000
                    else:
                        position_size = 1000000

                    self.buy(size=position_size, sl=stop_price, tp=target_price)

            # Short entry with Kalman confirmation
            elif bearish_breakout and volume_confirmation:
                # Kalman filter conditions
                kalman_short_signal = (
                    kalman_trending_down and  # Negative velocity
                    current_noise < 0.03 and  # Low noise environment
                    predicted_price < channel_low  # Predicted continuation
                )

                if kalman_short_signal and self.volume_delta[-1] < 0:
                    # Adjust stops based on noise level
                    noise_adjustment = 1.0 + (current_noise * 2)
                    stop_distance = self.atr[-1] * self.atr_multiplier * noise_adjustment
                    stop_price = current_close + stop_distance

                    # Dynamic take profit based on Kalman prediction
                    if predicted_price < current_close * 0.98:  # Strong prediction
                        tp_ratio = self.take_profit_ratio * 1.5
                    else:
                        tp_ratio = self.take_profit_ratio

                    target_price = current_close - (stop_distance * tp_ratio)

                    # Position size based on noise level
                    if current_noise < 0.02:  # Very clean signal
                        position_size = 1200000
                    else:
                        position_size = 1000000

                    self.sell(size=position_size, sl=stop_price, tp=target_price)

        else:
            # Enhanced exit with Kalman prediction
            if self.position.is_long:
                # Exit if Kalman predicts reversal or noise increases
                exit_signal = (
                    kalman_velocity < 0 or  # Velocity turned negative
                    predicted_price < kalman_close or  # Predicting downturn
                    current_noise > 0.04 or  # Noise increased
                    current_close < channel_high * 0.99  # Price rejection
                )
                if exit_signal:
                    self.position.close()

            elif self.position.is_short:
                # Exit if Kalman predicts reversal or noise increases
                exit_signal = (
                    kalman_velocity > 0 or  # Velocity turned positive
                    predicted_price > kalman_close or  # Predicting upturn
                    current_noise > 0.04 or  # Noise increased
                    current_close > channel_low * 1.01  # Price rejection
                )
                if exit_signal:
                    self.position.close()

# Run single backtest
bt = Backtest(data, SmartMoneyKalman, cash=10000000, commission=0.00045)

print("\n🌙 ===== SMART MONEY BREAKOUT + KALMAN FILTER ===== 🌙")
print(f"Channel Lookback: {CHANNEL_LOOKBACK}")
print(f"Kalman Gain: {KALMAN_GAIN}")
print(f"Kalman Covariance: {KALMAN_COVARIANCE}")

stats_default = bt.run()
print(stats_default)

# Optimization
print("\n🚀 Optimizing Smart Money + Kalman Strategy...")
# Optimization removed

print("\n✅ Smart Money + Kalman Strategy Test Complete")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING SMART MONEY + KALMAN FILTER ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(SmartMoneyKalman, 'smart_money_kalman')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/smart_money_kalman.csv")