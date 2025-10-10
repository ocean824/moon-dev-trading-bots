"""
Periodic Linear Regression Strategy with Kalman Filter
=======================================================

This strategy combines periodic linear regression with a Kalman Filter
for smoothing and prediction. The Kalman filter provides optimal state
estimation, reducing noise while maintaining responsiveness to trend changes.

Strategy Logic:
- Uses rolling linear regression with periodic anchors
- Kalman filter smooths regression line and provides uncertainty estimates
- Entry: Price crosses Kalman-filtered regression with low uncertainty
- Exit: Price touches opposite band or Kalman prediction reverses
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from scipy import stats
from datetime import datetime

print("🚀 Moon Dev's Periodic Linear Regression + Kalman Filter Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
PERIOD_TYPE = 'weekly'
LOOKBACK_PERIOD = 50
BAND_MULTIPLIER = 1.5
USE_BANDS = True
METHOD = 'rolling'
KALMAN_Q = 0.01  # Process noise (how much we expect the state to change)
KALMAN_R = 0.1   # Measurement noise (how much we trust observations)
UNCERTAINTY_THRESHOLD = 0.5  # Max uncertainty for trade entry
TAKE_PROFIT_PERCENT = 3.5
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class PeriodicLinearRegressionKalman(Strategy):
    # Strategy parameters
    period_type = PERIOD_TYPE
    lookback_period = LOOKBACK_PERIOD
    band_multiplier = BAND_MULTIPLIER
    use_bands = USE_BANDS
    method = METHOD
    kalman_q = KALMAN_Q
    kalman_r = KALMAN_R
    uncertainty_threshold = UNCERTAINTY_THRESHOLD
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        # Calculate periodic anchors based on time
        self.anchor_points = self.I(self._calculate_anchors, self.data.Close, name='Anchors')

        # Calculate linear regression line
        self.regression_line = self.I(self._calculate_regression, self.data.Close, name='RegressionLine')

        # Calculate slope for trend detection
        self.regression_slope = self.I(self._calculate_slope, self.data.Close, name='Slope')

        # Apply Kalman filter to regression line
        self.kalman_regression, self.kalman_uncertainty = self._apply_kalman_filter()
        self.kalman_regression = self.I(lambda: self.kalman_regression, name='KalmanRegression')
        self.kalman_uncertainty = self.I(lambda: self.kalman_uncertainty, name='KalmanUncertainty')

        # Calculate Kalman-filtered slope
        self.kalman_slope = self.I(self._calculate_kalman_slope, name='KalmanSlope')

        # Calculate regression bands if enabled (using Kalman-filtered values)
        if self.use_bands:
            self.upper_band = self.I(self._calculate_kalman_upper_band, self.data.Close, name='UpperBand')
            self.lower_band = self.I(self._calculate_kalman_lower_band, self.data.Close, name='LowerBand')

        # Calculate correlation coefficient for signal strength
        self.correlation = self.I(self._calculate_correlation, self.data.Close, name='Correlation')

        # Calculate prediction confidence
        self.prediction_confidence = self.I(self._calculate_prediction_confidence, name='PredictionConfidence')

    def _calculate_anchors(self, prices):
        """Identify anchor points based on period type"""
        anchors = np.zeros(len(prices))

        # Create datetime index from data
        dates = pd.DatetimeIndex(self.data.index)

        if self.period_type == 'hourly':
            hour_changes = dates.hour.to_numpy()
            for i in range(1, len(hour_changes)):
                if hour_changes[i] != hour_changes[i-1]:
                    anchors[i] = 1
        elif self.period_type == 'daily':
            day_changes = dates.day.to_numpy()
            for i in range(1, len(day_changes)):
                if day_changes[i] != day_changes[i-1]:
                    anchors[i] = 1
        elif self.period_type == 'weekly':
            week_changes = dates.isocalendar().week.to_numpy()
            for i in range(1, len(week_changes)):
                if week_changes[i] != week_changes[i-1]:
                    anchors[i] = 1
        elif self.period_type == 'monthly':
            month_changes = dates.month.to_numpy()
            for i in range(1, len(month_changes)):
                if month_changes[i] != month_changes[i-1]:
                    anchors[i] = 1

        return anchors

    def _calculate_regression(self, prices):
        """Calculate linear regression line"""
        regression_values = np.full(len(prices), np.nan)
        prices_array = np.array(prices)

        anchor_indices = np.where(self._calculate_anchors(prices) == 1)[0]
        if len(anchor_indices) == 0:
            anchor_indices = [0]

        for i in range(len(prices)):
            if i < self.lookback_period:
                continue

            recent_anchors = anchor_indices[anchor_indices <= i]
            if len(recent_anchors) > 0:
                if self.method == 'rolling':
                    start_idx = max(0, i - self.lookback_period + 1)
                else:
                    start_idx = recent_anchors[-1]
            else:
                start_idx = max(0, i - self.lookback_period + 1)

            if i - start_idx >= 2:
                x = np.arange(start_idx, i + 1)
                y = prices_array[start_idx:i + 1]

                valid_mask = ~np.isnan(y)
                if np.sum(valid_mask) >= 2:
                    x_valid = x[valid_mask]
                    y_valid = y[valid_mask]

                    slope, intercept = np.polyfit(x_valid - x_valid[0], y_valid, 1)
                    regression_values[i] = slope * (i - x_valid[0]) + intercept

        return regression_values

    def _apply_kalman_filter(self):
        """Apply Kalman filter to smooth regression line"""
        regression_values = self._calculate_regression(self.data.Close)
        kalman_filtered = np.full(len(regression_values), np.nan)
        uncertainty = np.full(len(regression_values), np.nan)

        # Initialize Kalman filter state
        x_hat = None  # State estimate
        P = None      # Error covariance

        for i in range(len(regression_values)):
            if np.isnan(regression_values[i]):
                continue

            if x_hat is None:
                # Initialize with first valid regression value
                x_hat = regression_values[i]
                P = 1.0

            # Prediction step
            x_hat_minus = x_hat  # State prediction
            P_minus = P + self.kalman_q  # Error covariance prediction

            # Update step
            K = P_minus / (P_minus + self.kalman_r)  # Kalman gain
            x_hat = x_hat_minus + K * (regression_values[i] - x_hat_minus)  # Updated state
            P = (1 - K) * P_minus  # Updated error covariance

            kalman_filtered[i] = x_hat
            uncertainty[i] = np.sqrt(P)

        return kalman_filtered, uncertainty

    def _calculate_slope(self, prices):
        """Calculate regression slope for trend detection"""
        slopes = np.full(len(prices), np.nan)
        prices_array = np.array(prices)

        for i in range(len(prices)):
            if i < self.lookback_period:
                continue

            start_idx = max(0, i - self.lookback_period + 1)

            if i - start_idx >= 2:
                x = np.arange(start_idx, i + 1)
                y = prices_array[start_idx:i + 1]

                valid_mask = ~np.isnan(y)
                if np.sum(valid_mask) >= 2:
                    x_valid = x[valid_mask]
                    y_valid = y[valid_mask]

                    slope, _ = np.polyfit(x_valid - x_valid[0], y_valid, 1)
                    slopes[i] = slope

        return slopes

    def _calculate_kalman_slope(self):
        """Calculate slope from Kalman-filtered regression"""
        kalman_slopes = np.full(len(self.kalman_regression), np.nan)

        for i in range(5, len(self.kalman_regression)):
            if not np.isnan(self.kalman_regression[i]) and not np.isnan(self.kalman_regression[i-5]):
                # Calculate slope over last 5 periods
                kalman_slopes[i] = (self.kalman_regression[i] - self.kalman_regression[i-5]) / 5

        return kalman_slopes

    def _calculate_correlation(self, prices):
        """Calculate correlation coefficient"""
        correlations = np.full(len(prices), np.nan)
        prices_array = np.array(prices)

        for i in range(len(prices)):
            if i < self.lookback_period:
                continue

            start_idx = max(0, i - self.lookback_period + 1)

            if i - start_idx >= 2:
                x = np.arange(start_idx, i + 1)
                y = prices_array[start_idx:i + 1]

                valid_mask = ~np.isnan(y)
                if np.sum(valid_mask) >= 2:
                    x_valid = x[valid_mask] - x[valid_mask].mean()
                    y_valid = y[valid_mask]

                    if len(x_valid) > 1:
                        correlations[i] = np.corrcoef(x_valid, y_valid)[0, 1]

        return correlations

    def _calculate_kalman_upper_band(self, prices):
        """Calculate upper band using Kalman-filtered regression"""
        upper_band = np.full(len(prices), np.nan)
        prices_array = np.array(prices)

        for i in range(len(prices)):
            if i < self.lookback_period or np.isnan(self.kalman_regression[i]):
                continue

            start_idx = max(0, i - self.lookback_period + 1)

            # Calculate standard deviation of residuals from Kalman line
            y = prices_array[start_idx:i + 1]
            kalman_values = self.kalman_regression[start_idx:i + 1]

            valid_mask = ~(np.isnan(y) | np.isnan(kalman_values))
            if np.sum(valid_mask) >= 2:
                residuals = y[valid_mask] - kalman_values[valid_mask]
                std_dev = np.std(residuals)
                # Adjust band width by uncertainty
                uncertainty_adjustment = 1 + self.kalman_uncertainty[i]
                upper_band[i] = self.kalman_regression[i] + (self.band_multiplier * std_dev * uncertainty_adjustment)

        return upper_band

    def _calculate_kalman_lower_band(self, prices):
        """Calculate lower band using Kalman-filtered regression"""
        lower_band = np.full(len(prices), np.nan)
        prices_array = np.array(prices)

        for i in range(len(prices)):
            if i < self.lookback_period or np.isnan(self.kalman_regression[i]):
                continue

            start_idx = max(0, i - self.lookback_period + 1)

            # Calculate standard deviation of residuals from Kalman line
            y = prices_array[start_idx:i + 1]
            kalman_values = self.kalman_regression[start_idx:i + 1]

            valid_mask = ~(np.isnan(y) | np.isnan(kalman_values))
            if np.sum(valid_mask) >= 2:
                residuals = y[valid_mask] - kalman_values[valid_mask]
                std_dev = np.std(residuals)
                # Adjust band width by uncertainty
                uncertainty_adjustment = 1 + self.kalman_uncertainty[i]
                lower_band[i] = self.kalman_regression[i] - (self.band_multiplier * std_dev * uncertainty_adjustment)

        return lower_band

    def _calculate_prediction_confidence(self):
        """Calculate confidence in Kalman filter predictions"""
        confidence = np.zeros(len(self.kalman_uncertainty))

        for i in range(len(self.kalman_uncertainty)):
            if not np.isnan(self.kalman_uncertainty[i]):
                # Convert uncertainty to confidence (inverse relationship)
                # Lower uncertainty = higher confidence
                confidence[i] = 1.0 / (1.0 + self.kalman_uncertainty[i])

        return confidence

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.lookback_period:
            return

        # Get current values
        current_price = self.data.Close[-1]
        kalman_value = self.kalman_regression[-1]
        kalman_slope = self.kalman_slope[-1]
        uncertainty = self.kalman_uncertainty[-1]
        correlation = self.correlation[-1]
        confidence = self.prediction_confidence[-1]

        # Skip if values are invalid
        if (np.isnan(kalman_value) or np.isnan(kalman_slope) or
            np.isnan(uncertainty) or np.isnan(correlation)):
            return

        # Entry conditions with Kalman filter
        if not self.position:
            # Only trade when uncertainty is low and correlation is strong
            if uncertainty < self.uncertainty_threshold and abs(correlation) > 0.7:
                # Long entry: Price crosses above Kalman regression with positive slope
                if (self.data.Close[-2] <= self.kalman_regression[-2] and
                    current_price > kalman_value and
                    kalman_slope > 0):

                    # Adjust signal strength based on confidence
                    signal_strength = confidence
                    if confidence > 0.8:
                        signal_strength = 1.2
                    elif confidence > 0.6:
                        signal_strength = 1.1

                    # Set stop loss and take profit
                    if self.use_bands and not np.isnan(self.lower_band[-1]):
                        sl_price = min(self.lower_band[-1], current_price * (1 - self.stop_loss))
                    else:
                        sl_price = current_price * (1 - self.stop_loss)

                    if self.use_bands and not np.isnan(self.upper_band[-1]):
                        tp_price = max(self.upper_band[-1] * signal_strength, current_price * (1 + self.take_profit * signal_strength))
                    else:
                        tp_price = current_price * (1 + self.take_profit * signal_strength)

                    # Ensure valid SL/TP relationship
                    if sl_price < current_price < tp_price:
                        self.buy(sl=sl_price, tp=tp_price, size=1000000)

                # Short entry: Price crosses below Kalman regression with negative slope
                elif (self.data.Close[-2] >= self.kalman_regression[-2] and
                      current_price < kalman_value and
                      kalman_slope < 0):

                    # Adjust signal strength based on confidence
                    signal_strength = confidence
                    if confidence > 0.8:
                        signal_strength = 1.2
                    elif confidence > 0.6:
                        signal_strength = 1.1

                    # Set stop loss and take profit
                    if self.use_bands and not np.isnan(self.upper_band[-1]):
                        sl_price = max(self.upper_band[-1], current_price * (1 + self.stop_loss))
                    else:
                        sl_price = current_price * (1 + self.stop_loss)

                    if self.use_bands and not np.isnan(self.lower_band[-1]):
                        tp_price = min(self.lower_band[-1] / signal_strength, current_price * (1 - self.take_profit * signal_strength))
                    else:
                        tp_price = current_price * (1 - self.take_profit * signal_strength)

                    # Ensure valid SL/TP relationship
                    if tp_price < current_price < sl_price:
                        self.sell(sl=sl_price, tp=tp_price, size=1000000)

        # Exit conditions with Kalman filter
        else:
            # Exit long if Kalman slope reverses, uncertainty increases, or correlation weakens
            if self.position.is_long:
                if (kalman_slope < 0 or uncertainty > self.uncertainty_threshold * 2 or
                    abs(correlation) < 0.3 or confidence < 0.3):
                    self.position.close()

            # Exit short if Kalman slope reverses, uncertainty increases, or correlation weakens
            elif self.position.is_short:
                if (kalman_slope > 0 or uncertainty > self.uncertainty_threshold * 2 or
                    abs(correlation) < 0.3 or confidence < 0.3):
                    self.position.close()

# Run single backtest
bt = Backtest(data, PeriodicLinearRegressionKalman, cash=1000000, commission=0.00045)

print("\n🌙 ===== PERIODIC LINEAR REGRESSION + KALMAN FILTER STRATEGY ===== 🌙")
print(f"Period Type: {PERIOD_TYPE}")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Band Multiplier: {BAND_MULTIPLIER}")
print(f"Kalman Q/R: {KALMAN_Q}/{KALMAN_R}")
print(f"Uncertainty Threshold: {UNCERTAINTY_THRESHOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING PERIODIC LINEAR REGRESSION + KALMAN FILTER ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(PeriodicLinearRegressionKalman, 'PeriodicLinearRegressionKalman')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/PeriodicLinearRegressionKalman.csv")