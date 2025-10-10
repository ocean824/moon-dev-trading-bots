"""
Moon Dev's Trend Impulse + Kalman Filter Combination Strategy
=============================================================
Combines Trend Impulse Channels with Kalman Filter for smoothed signals.
Uses Kalman velocity for momentum and uncertainty bands for dynamic stops.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Impulse + Kalman Filter Combo Strategy Loading... 🌙")

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ATR_PERIOD = 14
EMA_FAST = 12
EMA_SLOW = 26
ATR_CHANNEL = 2.0

# Kalman Filter parameters
KALMAN_GAIN = 0.05  # Process noise (higher = more responsive)
MEASUREMENT_NOISE = 0.5  # Measurement noise

# Risk management
TAKE_PROFIT_PERCENT = 3.5
STOP_LOSS_PERCENT = 1.5

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

def kalman_filter(prices, process_noise=0.01, measurement_noise=1.0):
    """
    Apply Kalman filter to price series
    Returns: filtered prices, velocity, and uncertainty
    """
    n = len(prices)
    filtered = np.zeros(n)
    velocity = np.zeros(n)
    uncertainty = np.zeros(n)

    # Initial state
    x = np.array([prices[0], 0])  # [position, velocity]
    P = np.eye(2) * 1000  # Initial uncertainty

    # Process and measurement matrices
    F = np.array([[1, 1], [0, 1]])  # State transition
    H = np.array([[1, 0]])  # Measurement matrix
    Q = np.eye(2) * process_noise  # Process noise
    R = np.array([[measurement_noise]])  # Measurement noise

    for i in range(n):
        # Predict
        x = F @ x
        P = F @ P @ F.T + Q

        # Update
        y = prices[i] - H @ x  # Innovation
        S = H @ P @ H.T + R  # Innovation covariance
        K = P @ H.T @ np.linalg.inv(S)  # Kalman gain

        x = x + K @ y
        P = (np.eye(2) - K @ H) @ P

        # Store results
        filtered[i] = x[0]
        velocity[i] = x[1]
        uncertainty[i] = np.sqrt(P[0, 0])

    return filtered, velocity, uncertainty

class TrendImpulseKalmanCombo(Strategy):
    """
    Trend Impulse + Kalman Filter Combination Strategy

    Entry Conditions:
    - Long: Trend Impulse bullish + Kalman velocity positive + low uncertainty
    - Short: Trend Impulse bearish + Kalman velocity negative + low uncertainty

    Uses uncertainty bands for dynamic stop losses.
    """

    # Parameters
    atr_period = ATR_PERIOD
    ema_fast = EMA_FAST
    ema_slow = EMA_SLOW
    atr_channel = ATR_CHANNEL
    kalman_gain = KALMAN_GAIN
    measurement_noise = MEASUREMENT_NOISE
    take_profit_pct = TAKE_PROFIT_PERCENT / 100
    stop_loss_pct = STOP_LOSS_PERCENT / 100

    def init(self):
        """Initialize indicators"""
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Calculate EMAs for Trend Impulse
        ema_fast = ta.ema(close, length=self.ema_fast)
        ema_slow = ta.ema(close, length=self.ema_slow)

        # Calculate ATR for channels
        atr = ta.atr(high, low, close, length=self.atr_period)

        # Apply Kalman filter to prices
        kalman_price, kalman_velocity, kalman_uncertainty = kalman_filter(
            close.values,
            process_noise=self.kalman_gain,
            measurement_noise=self.measurement_noise
        )

        # Smooth the Kalman velocity for better signals
        kalman_velocity_smooth = pd.Series(kalman_velocity).rolling(window=5, min_periods=1).mean().values

        # Calculate confidence based on uncertainty (lower uncertainty = higher confidence)
        max_uncertainty = np.nanmax(kalman_uncertainty)
        kalman_confidence = 1 - (kalman_uncertainty / max_uncertainty)

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

        # Store Kalman results
        self.kalman_price = kalman_price
        self.kalman_velocity = kalman_velocity_smooth
        self.kalman_uncertainty = kalman_uncertainty
        self.kalman_confidence = kalman_confidence

        # Calculate trend direction
        self.trend = np.where(self.ema_fast_full > self.ema_slow_full, 1, -1)

        # Calculate ATR channels
        self.upper_channel = self.ema_slow_full + (self.atr_full * self.atr_channel)
        self.lower_channel = self.ema_slow_full - (self.atr_full * self.atr_channel)

        # Calculate Kalman-based dynamic channels (uncertainty bands)
        self.kalman_upper = self.kalman_price + (self.kalman_uncertainty * 2)
        self.kalman_lower = self.kalman_price - (self.kalman_uncertainty * 2)

        # Store as indicators
        self.I_ema_fast = self.I(lambda: self.ema_fast_full)
        self.I_ema_slow = self.I(lambda: self.ema_slow_full)
        self.I_atr = self.I(lambda: self.atr_full)
        self.I_upper = self.I(lambda: self.upper_channel)
        self.I_lower = self.I(lambda: self.lower_channel)
        self.I_trend = self.I(lambda: self.trend)
        self.I_kalman = self.I(lambda: self.kalman_price)
        self.I_kalman_vel = self.I(lambda: self.kalman_velocity)
        self.I_kalman_conf = self.I(lambda: self.kalman_confidence)

    def next(self):
        """Trading logic with Kalman filtering"""
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

        # Get Kalman values
        kalman_vel = self.kalman_velocity[idx]
        kalman_conf = self.kalman_confidence[idx]
        kalman_unc = self.kalman_uncertainty[idx]

        # Skip if any indicator is NaN
        if np.isnan(self.ema_fast_full[idx]) or np.isnan(self.atr_full[idx]) or np.isnan(kalman_vel):
            return

        # Position management
        if not self.position:
            # Long entry conditions with Kalman confirmation
            if current_trend > 0:
                enter_long = False

                # Strong trend change signal
                if prev_trend <= 0:
                    enter_long = True

                # Channel bounce with positive Kalman velocity
                if (self.data.Low[-1] <= self.lower_channel[idx] and
                    current_price > self.lower_channel[idx] and
                    kalman_vel > 0):
                    enter_long = True

                # Breakout signal
                if (idx > 1 and current_price > self.upper_channel[idx] and
                    self.data.Close[-2] <= self.upper_channel[idx-1]):
                    enter_long = True

                # Strong positive Kalman velocity
                if kalman_vel > np.percentile(self.kalman_velocity[:idx+1], 80):
                    enter_long = True

                if enter_long:
                    # Dynamic stop loss based on Kalman uncertainty
                    uncertainty_stop = kalman_unc * 2.5
                    atr_stop = self.atr_full[idx] * 2.0

                    # Use the tighter of the two stops
                    stop_distance = min(uncertainty_stop, atr_stop)
                    sl = max(current_price - stop_distance, current_price * (1 - self.stop_loss_pct))

                    # Adjust take profit based on confidence
                    tp_multiplier = 1 + (kalman_conf * 0.5)  # Higher confidence = larger targets
                    tp = current_price * (1 + self.take_profit_pct * tp_multiplier)

                    self.buy(size=0.95, sl=sl, tp=tp)

            # Short entry conditions with Kalman confirmation
            elif current_trend < 0:
                enter_short = False

                # Strong trend change signal
                if prev_trend >= 0:
                    enter_short = True

                # Channel rejection with negative Kalman velocity
                if (self.data.High[-1] >= self.upper_channel[idx] and
                    current_price < self.upper_channel[idx] and
                    kalman_vel < 0):
                    enter_short = True

                # Breakdown signal
                if (idx > 1 and current_price < self.lower_channel[idx] and
                    self.data.Close[-2] >= self.lower_channel[idx-1]):
                    enter_short = True

                # Strong negative Kalman velocity
                if kalman_vel < np.percentile(self.kalman_velocity[:idx+1], 20):
                    enter_short = True

                if enter_short:
                    # Dynamic stop loss based on Kalman uncertainty
                    uncertainty_stop = kalman_unc * 2.5
                    atr_stop = self.atr_full[idx] * 2.0

                    stop_distance = min(uncertainty_stop, atr_stop)
                    sl = min(current_price + stop_distance, current_price * (1 + self.stop_loss_pct))

                    # Adjust take profit based on confidence
                    tp_multiplier = 1 + (kalman_conf * 0.5)
                    tp = current_price * (1 - self.take_profit_pct * tp_multiplier)

                    self.sell(size=0.95, sl=sl, tp=tp)

        else:
            # Exit management with Kalman
            if self.position.is_long:
                # Exit if trend turns bearish
                if current_trend < 0:
                    self.position.close()
                # Exit if Kalman velocity turns strongly negative
                elif kalman_vel < -abs(np.percentile(self.kalman_velocity[:idx+1], 20)):
                    self.position.close()
                # Exit if confidence drops too low
                elif kalman_conf < 0.3:
                    self.position.close()
                # Exit if price closes below lower channel
                elif current_price < self.lower_channel[idx]:
                    self.position.close()

            else:  # Short position
                # Exit if trend turns bullish
                if current_trend > 0:
                    self.position.close()
                # Exit if Kalman velocity turns strongly positive
                elif kalman_vel > abs(np.percentile(self.kalman_velocity[:idx+1], 80)):
                    self.position.close()
                # Exit if confidence drops too low
                elif kalman_conf < 0.3:
                    self.position.close()
                # Exit if price closes above upper channel
                elif current_price > self.upper_channel[idx]:
                    self.position.close()

# Run single backtest
bt = Backtest(data, TrendImpulseKalmanCombo, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND IMPULSE + KALMAN FILTER - PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"Fast EMA: {EMA_FAST}")
print(f"Slow EMA: {EMA_SLOW}")
print(f"ATR Channel: {ATR_CHANNEL}x")
print(f"Kalman Gain: {KALMAN_GAIN}")
print(f"Measurement Noise: {MEASUREMENT_NOISE}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND IMPULSE + KALMAN FILTER ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendImpulseKalmanCombo, 'TrendImpulseKalmanCombo')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendImpulseKalmanCombo.csv")