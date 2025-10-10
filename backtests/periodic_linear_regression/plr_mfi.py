"""
Periodic Linear Regression Strategy with MFI Filter
====================================================

This strategy combines periodic linear regression with Money Flow Index (MFI)
to filter trades based on volume-weighted momentum. MFI helps identify
overbought/oversold conditions and confirms trend strength.

Strategy Logic:
- Uses rolling linear regression with periodic anchors
- MFI filter: Only enter longs when MFI < 80, shorts when MFI > 20
- MFI divergence detection for stronger signals
- Exit: Price touches opposite band or regression line reversal
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from scipy import stats
from datetime import datetime

print("🚀 Moon Dev's Periodic Linear Regression + MFI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
PERIOD_TYPE = 'weekly'
LOOKBACK_PERIOD = 50
BAND_MULTIPLIER = 1.5
USE_BANDS = True
METHOD = 'rolling'
MFI_PERIOD = 14
MFI_OVERBOUGHT = 80
MFI_OVERSOLD = 20
TAKE_PROFIT_PERCENT = 3.5
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class PeriodicLinearRegressionMFI(Strategy):
    # Strategy parameters
    period_type = PERIOD_TYPE
    lookback_period = LOOKBACK_PERIOD
    band_multiplier = BAND_MULTIPLIER
    use_bands = USE_BANDS
    method = METHOD
    mfi_period = MFI_PERIOD
    mfi_overbought = MFI_OVERBOUGHT
    mfi_oversold = MFI_OVERSOLD
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        # Calculate periodic anchors based on time
        self.anchor_points = self.I(self._calculate_anchors, self.data.Close, name='Anchors')

        # Calculate linear regression line
        self.regression_line = self.I(self._calculate_regression, self.data.Close, name='RegressionLine')

        # Calculate slope for trend detection
        self.regression_slope = self.I(self._calculate_slope, self.data.Close, name='Slope')

        # Calculate regression bands if enabled
        if self.use_bands:
            self.upper_band = self.I(self._calculate_upper_band, self.data.Close, name='UpperBand')
            self.lower_band = self.I(self._calculate_lower_band, self.data.Close, name='LowerBand')

        # Calculate correlation coefficient for signal strength
        self.correlation = self.I(self._calculate_correlation, self.data.Close, name='Correlation')

        # Add MFI indicator
        self.mfi = self.I(talib.MFI, self.data.High, self.data.Low, self.data.Close, self.data.Volume, self.mfi_period)

        # Calculate MFI divergence
        self.mfi_divergence = self.I(self._calculate_mfi_divergence, self.data.Close, name='MFIDivergence')

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

    def _calculate_upper_band(self, prices):
        """Calculate upper regression band"""
        upper_band = np.full(len(prices), np.nan)
        regression_line = self._calculate_regression(prices)
        prices_array = np.array(prices)

        for i in range(len(prices)):
            if i < self.lookback_period or np.isnan(regression_line[i]):
                continue

            start_idx = max(0, i - self.lookback_period + 1)

            y = prices_array[start_idx:i + 1]
            reg_values = regression_line[start_idx:i + 1]

            valid_mask = ~(np.isnan(y) | np.isnan(reg_values))
            if np.sum(valid_mask) >= 2:
                residuals = y[valid_mask] - reg_values[valid_mask]
                std_dev = np.std(residuals)
                upper_band[i] = regression_line[i] + (self.band_multiplier * std_dev)

        return upper_band

    def _calculate_lower_band(self, prices):
        """Calculate lower regression band"""
        lower_band = np.full(len(prices), np.nan)
        regression_line = self._calculate_regression(prices)
        prices_array = np.array(prices)

        for i in range(len(prices)):
            if i < self.lookback_period or np.isnan(regression_line[i]):
                continue

            start_idx = max(0, i - self.lookback_period + 1)

            y = prices_array[start_idx:i + 1]
            reg_values = regression_line[start_idx:i + 1]

            valid_mask = ~(np.isnan(y) | np.isnan(reg_values))
            if np.sum(valid_mask) >= 2:
                residuals = y[valid_mask] - reg_values[valid_mask]
                std_dev = np.std(residuals)
                lower_band[i] = regression_line[i] - (self.band_multiplier * std_dev)

        return lower_band

    def _calculate_mfi_divergence(self, prices):
        """Detect MFI divergence with price"""
        divergence = np.zeros(len(prices))

        if len(prices) < self.mfi_period * 2:
            return divergence

        mfi_values = talib.MFI(self.data.High, self.data.Low, self.data.Close, self.data.Volume, self.mfi_period)

        for i in range(self.mfi_period * 2, len(prices)):
            # Look back for divergence
            lookback = min(20, i - self.mfi_period)

            # Find local highs and lows in price
            price_segment = prices[i-lookback:i+1]
            mfi_segment = mfi_values[i-lookback:i+1]

            if not np.any(np.isnan(mfi_segment)):
                # Bullish divergence: price makes lower low, MFI makes higher low
                if (prices[i] < np.min(price_segment[:-1]) and
                    mfi_values[i] > np.min(mfi_segment[:-1])):
                    divergence[i] = 1

                # Bearish divergence: price makes higher high, MFI makes lower high
                elif (prices[i] > np.max(price_segment[:-1]) and
                      mfi_values[i] < np.max(mfi_segment[:-1])):
                    divergence[i] = -1

        return divergence

    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.lookback_period, self.mfi_period * 2):
            return

        # Get current values
        current_price = self.data.Close[-1]
        regression_value = self.regression_line[-1]
        slope = self.regression_slope[-1]
        correlation = self.correlation[-1]
        mfi_value = self.mfi[-1]
        mfi_divergence = self.mfi_divergence[-1]

        # Skip if values are invalid
        if np.isnan(regression_value) or np.isnan(slope) or np.isnan(correlation) or np.isnan(mfi_value):
            return

        # Entry conditions with MFI filter
        if not self.position:
            # Strong correlation indicates reliable trend
            if abs(correlation) > 0.7:
                # Long entry: Price crosses above regression + MFI conditions
                if (self.data.Close[-2] <= self.regression_line[-2] and
                    current_price > regression_value and
                    slope > 0):

                    # MFI filter: Not overbought and preferably oversold or bullish divergence
                    if mfi_value < self.mfi_overbought:
                        # Extra confirmation with oversold or divergence
                        signal_strength = 1.0
                        if mfi_value < self.mfi_oversold:
                            signal_strength = 1.2
                        elif mfi_divergence > 0:
                            signal_strength = 1.15

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

                # Short entry: Price crosses below regression + MFI conditions
                elif (self.data.Close[-2] >= self.regression_line[-2] and
                      current_price < regression_value and
                      slope < 0):

                    # MFI filter: Not oversold and preferably overbought or bearish divergence
                    if mfi_value > self.mfi_oversold:
                        # Extra confirmation with overbought or divergence
                        signal_strength = 1.0
                        if mfi_value > self.mfi_overbought:
                            signal_strength = 1.2
                        elif mfi_divergence < 0:
                            signal_strength = 1.15

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

        # Exit conditions with MFI
        else:
            # Exit long if slope turns negative, correlation weakens, or MFI overbought
            if self.position.is_long:
                if slope < 0 or abs(correlation) < 0.3 or mfi_value > 85:
                    self.position.close()

            # Exit short if slope turns positive, correlation weakens, or MFI oversold
            elif self.position.is_short:
                if slope > 0 or abs(correlation) < 0.3 or mfi_value < 15:
                    self.position.close()

# Run single backtest
bt = Backtest(data, PeriodicLinearRegressionMFI, cash=1000000, commission=0.00045)

print("\n🌙 ===== PERIODIC LINEAR REGRESSION + MFI STRATEGY ===== 🌙")
print(f"Period Type: {PERIOD_TYPE}")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Band Multiplier: {BAND_MULTIPLIER}")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Overbought/Oversold: {MFI_OVERBOUGHT}/{MFI_OVERSOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING PERIODIC LINEAR REGRESSION + MFI ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(PeriodicLinearRegressionMFI, 'PeriodicLinearRegressionMFI')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/PeriodicLinearRegressionMFI.csv")