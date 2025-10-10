"""
Periodic Linear Regression Strategy with Kalman Filter - V2
============================================================

Combines linear regression with Kalman filtering for smoothed predictions.

Strategy Logic:
- Uses rolling linear regression with Kalman smoothing
- Kalman filter reduces noise while maintaining responsiveness
- Entry: Smoothed regression crossover with momentum confirmation
- Exit: Fixed TP/SL or signal reversal
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Periodic Linear Regression + Kalman Filter V2 Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
LOOKBACK_PERIOD = 20
STD_MULTIPLIER = 2.0
KALMAN_Q = 0.005  # Process noise
KALMAN_R = 0.05   # Measurement noise
SLOPE_THRESHOLD = 0.0001
TAKE_PROFIT_PERCENT = 3.5
STOP_LOSS_PERCENT = 1.5

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class PeriodicLinearRegressionKalmanV2(Strategy):
    # Strategy parameters
    lookback_period = LOOKBACK_PERIOD
    std_multiplier = STD_MULTIPLIER
    kalman_q = KALMAN_Q
    kalman_r = KALMAN_R
    slope_threshold = SLOPE_THRESHOLD
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        # Linear regression indicators
        self.regression_line = self.I(talib.LINEARREG, self.data.Close, self.lookback_period)
        self.regression_slope = self.I(talib.LINEARREG_SLOPE, self.data.Close, self.lookback_period)
        self.stddev = self.I(talib.STDDEV, self.data.Close, self.lookback_period)

        # Apply Kalman filter to regression line
        self.kalman_regression = self.I(self._apply_kalman_filter, self.regression_line)

        # Calculate Kalman slope
        self.kalman_slope = self.I(self._calculate_kalman_slope, self.kalman_regression)

        # Bands based on Kalman-filtered regression
        self.upper_band = self.I(lambda: self.kalman_regression + (self.std_multiplier * self.stddev))
        self.lower_band = self.I(lambda: self.kalman_regression - (self.std_multiplier * self.stddev))

        # RSI for momentum
        self.rsi = self.I(talib.RSI, self.data.Close, 14)

        # MACD for trend confirmation
        macd, signal, hist = talib.MACD(self.data.Close.values)
        self.macd_hist = self.I(lambda: hist)

    def _apply_kalman_filter(self, values):
        """Simple Kalman filter implementation"""
        filtered = np.full(len(values), np.nan)

        # Initialize state
        x_hat = None
        P = None

        for i in range(len(values)):
            if np.isnan(values[i]):
                continue

            if x_hat is None:
                # Initialize with first valid value
                x_hat = values[i]
                P = 1.0

            # Prediction
            x_hat_minus = x_hat
            P_minus = P + self.kalman_q

            # Update
            K = P_minus / (P_minus + self.kalman_r)
            x_hat = x_hat_minus + K * (values[i] - x_hat_minus)
            P = (1 - K) * P_minus

            filtered[i] = x_hat

        return filtered

    def _calculate_kalman_slope(self, kalman_values):
        """Calculate slope from Kalman-filtered values"""
        slopes = np.full(len(kalman_values), np.nan)

        for i in range(5, len(kalman_values)):
            if not np.isnan(kalman_values[i]) and not np.isnan(kalman_values[i-5]):
                slopes[i] = (kalman_values[i] - kalman_values[i-5]) / (5 * kalman_values[i-5])

        return slopes

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.lookback_period + 26:  # Need data for MACD
            return

        # Get current values
        current_price = self.data.Close[-1]
        prev_price = self.data.Close[-2]
        kalman_value = self.kalman_regression[-1]
        prev_kalman = self.kalman_regression[-2]
        kalman_slope = self.kalman_slope[-1]
        rsi_value = self.rsi[-1]
        macd_hist = self.macd_hist[-1]
        upper = self.upper_band[-1]
        lower = self.lower_band[-1]

        # Skip if values are invalid
        if np.isnan(kalman_value) or np.isnan(kalman_slope) or np.isnan(rsi_value):
            return

        # Entry conditions with Kalman filter
        if not self.position:
            # Long entry:
            # - Price crosses above Kalman regression
            # - Positive Kalman slope
            # - MACD histogram positive (if available)
            # - RSI not overbought
            if (prev_price <= prev_kalman and
                current_price > kalman_value and
                kalman_slope > self.slope_threshold and
                (np.isnan(macd_hist) or macd_hist > 0) and
                rsi_value < 70):

                # Stronger signal if far from upper band
                distance_to_upper = (upper - current_price) / current_price
                signal_strength = 1.15 if distance_to_upper > 0.02 else 1.0

                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit * signal_strength)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            # Short entry:
            # - Price crosses below Kalman regression
            # - Negative Kalman slope
            # - MACD histogram negative (if available)
            # - RSI not oversold
            elif (prev_price >= prev_kalman and
                  current_price < kalman_value and
                  kalman_slope < -self.slope_threshold and
                  (np.isnan(macd_hist) or macd_hist < 0) and
                  rsi_value > 30):

                # Stronger signal if far from lower band
                distance_to_lower = (current_price - lower) / current_price
                signal_strength = 1.15 if distance_to_lower > 0.02 else 1.0

                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit * signal_strength)

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

        # Exit conditions with Kalman filter
        else:
            # Exit long if signal reverses
            if self.position.is_long:
                if (kalman_slope < 0 or
                    current_price >= upper or
                    (not np.isnan(macd_hist) and macd_hist < -abs(macd_hist) * 0.2) or
                    rsi_value > 80):
                    self.position.close()

            # Exit short if signal reverses
            elif self.position.is_short:
                if (kalman_slope > 0 or
                    current_price <= lower or
                    (not np.isnan(macd_hist) and macd_hist > abs(macd_hist) * 0.2) or
                    rsi_value < 20):
                    self.position.close()

# Run single backtest
bt = Backtest(data, PeriodicLinearRegressionKalmanV2, cash=1000000, commission=0.00045)

print("\n🌙 ===== PERIODIC LINEAR REGRESSION + KALMAN FILTER V2 STRATEGY ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Kalman Q/R: {KALMAN_Q}/{KALMAN_R}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING PERIODIC LINEAR REGRESSION + KALMAN FILTER V2 ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(PeriodicLinearRegressionKalmanV2, 'PeriodicLinearRegressionKalmanV2')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/PeriodicLinearRegressionKalmanV2.csv")