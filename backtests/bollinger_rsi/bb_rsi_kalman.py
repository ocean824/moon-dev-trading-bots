"""
Bollinger Bands + RSI + Kalman Filter Strategy
===============================================

Enhanced version of the base strategy adding Kalman Filter for noise reduction:
- Entry: RSI signal + BB signal + Kalman smoothed price confirms direction
- Kalman filter reduces market noise and false signals

Kalman Parameters:
- Process noise: 0.01
- Measurement noise: 0.1
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Bollinger + RSI + Kalman Filter Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
RSI_PERIOD = 6  # Very short RSI period (from Pine Script)
BB_PERIOD = 200  # Long-term Bollinger Bands
BB_STD = 2.0  # Standard deviations
RSI_OVERSOLD = 50  # Using 50 as both oversold/overbought
RSI_OVERBOUGHT = 50

# Kalman Filter parameters
KALMAN_PROCESS_NOISE = 0.01
KALMAN_MEASUREMENT_NOISE = 0.1

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")


def kalman_filter(prices, process_noise=0.01, measurement_noise=0.1):
    """
    Apply Kalman filter to price series for noise reduction
    """
    n = len(prices)
    filtered = np.zeros(n)

    # Initialize
    x = prices[0]  # Initial state
    p = 1.0  # Initial error covariance

    for i in range(n):
        # Prediction
        x_pred = x
        p_pred = p + process_noise

        # Update
        k = p_pred / (p_pred + measurement_noise)  # Kalman gain
        x = x_pred + k * (prices[i] - x_pred)
        p = (1 - k) * p_pred

        filtered[i] = x

    return filtered


class BollingerRSIKalman(Strategy):
    # Strategy parameters
    rsi_period = RSI_PERIOD
    bb_period = BB_PERIOD
    bb_std = BB_STD
    rsi_oversold = RSI_OVERSOLD
    rsi_overbought = RSI_OVERBOUGHT
    kalman_process = KALMAN_PROCESS_NOISE
    kalman_measurement = KALMAN_MEASUREMENT_NOISE

    def init(self):
        """Initialize indicators using talib and Kalman filter"""
        # Calculate RSI
        self.rsi = self.I(talib.RSI, self.data.Close, self.rsi_period)

        # Calculate Bollinger Bands
        bb_result = talib.BBANDS(
            self.data.Close.s,  # Use .s to get numpy array
            timeperiod=self.bb_period,
            nbdevup=self.bb_std,
            nbdevdn=self.bb_std,
            matype=0
        )
        self.bb_upper = self.I(lambda: bb_result[0])
        self.bb_middle = self.I(lambda: bb_result[1])
        self.bb_lower = self.I(lambda: bb_result[2])

        # Apply Kalman filter to price
        self.kalman_price = self.I(
            lambda: kalman_filter(
                self.data.Close.s,
                self.kalman_process,
                self.kalman_measurement
            )
        )

        # Calculate Kalman filter slope (trend direction)
        # Using simple difference for trend detection
        self.kalman_slope = self.I(
            lambda: np.concatenate([[0], np.diff(self.kalman_price)])
        )

        # Smooth the slope with SMA for stability
        self.kalman_slope_smooth = self.I(talib.SMA, self.kalman_slope, 5)

    def next(self):
        """Trading logic - combining RSI, BB, and Kalman filter signals"""
        if len(self.data) < max(self.rsi_period, self.bb_period) + 10:
            return

        # Get current and previous values
        current_price = self.data.Close[-1]
        prev_price = self.data.Close[-2]

        current_rsi = self.rsi[-1]
        prev_rsi = self.rsi[-2]

        current_kalman = self.kalman_price[-1]
        prev_kalman = self.kalman_price[-2]
        kalman_trend = self.kalman_slope_smooth[-1]

        current_bb_upper = self.bb_upper[-1]
        current_bb_lower = self.bb_lower[-1]
        current_bb_middle = self.bb_middle[-1]
        prev_bb_lower = self.bb_lower[-2]
        prev_bb_upper = self.bb_upper[-2]

        # Skip if we don't have valid values
        if pd.isna(current_bb_upper) or pd.isna(current_bb_lower) or pd.isna(current_rsi) or pd.isna(kalman_trend):
            return

        # Base conditions - Modified for better signal generation
        # RSI crosses above 50 OR price near lower BB with RSI below 50
        rsi_cross_up = prev_rsi <= self.rsi_oversold and current_rsi > self.rsi_oversold
        price_near_lower = current_price <= current_bb_lower * 1.01  # Within 1% of lower BB
        rsi_oversold_zone = current_rsi < 45  # Slightly below 50

        # RSI crosses below 50 OR price near upper BB with RSI above 50
        rsi_cross_down = prev_rsi >= self.rsi_overbought and current_rsi < self.rsi_overbought
        price_near_upper = current_price >= current_bb_upper * 0.99  # Within 1% of upper BB
        rsi_overbought_zone = current_rsi > 55  # Slightly above 50

        # Kalman filter confirmation conditions
        kalman_bullish = kalman_trend > 0 and current_kalman > prev_kalman  # Upward trend
        kalman_bearish = kalman_trend < 0 and current_kalman < prev_kalman  # Downward trend

        # Additional Kalman noise filter
        # Price should be relatively close to Kalman filtered value (not too noisy)
        price_kalman_ratio = abs(current_price - current_kalman) / current_kalman
        low_noise = price_kalman_ratio < 0.02  # Price within 2% of Kalman value

        # Position management with Kalman filter confirmation - simplified
        if not self.position:
            # LONG ENTRY: Price near lower BB AND RSI oversold AND Kalman confirms bullish trend
            if (current_price <= current_bb_lower * 1.02 and current_rsi <= 30 and
                kalman_bullish and low_noise):
                self.buy()

            # SHORT ENTRY: Price near upper BB AND RSI overbought AND Kalman confirms bearish trend
            elif (current_price >= current_bb_upper * 0.98 and current_rsi >= 70 and
                  kalman_bearish and low_noise):
                self.sell()

        else:
            # Exit conditions with Kalman filter confirmation
            if self.position.is_long:
                # Exit long when price reaches middle band OR RSI overbought OR Kalman trend reverses
                if (current_price >= current_bb_middle or current_rsi >= 70 or
                    (kalman_trend < -0.0001 and current_kalman < prev_kalman)):
                    self.position.close()

            elif self.position.is_short:
                # Exit short when price reaches middle band OR RSI oversold OR Kalman trend reverses
                if (current_price <= current_bb_middle or current_rsi <= 30 or
                    (kalman_trend > 0.0001 and current_kalman > prev_kalman)):
                    self.position.close()


# Run single backtest (default behavior)
bt = Backtest(data, BollingerRSIKalman, cash=1000000, commission=0.00045)

print("\n🌙 ===== BOLLINGER + RSI + KALMAN FILTER STRATEGY ===== 🌙")
print(f"RSI Period: {RSI_PERIOD}")
print(f"Bollinger Period: {BB_PERIOD}")
print(f"Bollinger Std Dev: {BB_STD}")
print(f"Kalman Process Noise: {KALMAN_PROCESS_NOISE}")
print(f"Kalman Measurement Noise: {KALMAN_MEASUREMENT_NOISE}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING BOLLINGER + RSI + KALMAN ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(BollingerRSIKalman, 'BollingerRSIKalman')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/BollingerRSIKalman.csv")