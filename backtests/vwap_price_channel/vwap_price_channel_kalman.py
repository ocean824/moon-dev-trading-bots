"""
Moon Dev's VWAP Price Channel Kalman Strategy
==============================================
VWAP Price Channel with Kalman filter for noise reduction
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class KalmanFilter:
    """Simple Kalman filter implementation for price smoothing"""
    def __init__(self, process_variance=1e-5, measurement_variance=1e-1):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.posteri_estimate = None
        self.posteri_error_estimate = None

    def update(self, measurement):
        if self.posteri_estimate is None:
            self.posteri_estimate = measurement
            self.posteri_error_estimate = 1.0

        priori_estimate = self.posteri_estimate
        priori_error_estimate = self.posteri_error_estimate + self.process_variance

        blending_factor = priori_error_estimate / (priori_error_estimate + self.measurement_variance)
        self.posteri_estimate = priori_estimate + blending_factor * (measurement - priori_estimate)
        self.posteri_error_estimate = (1 - blending_factor) * priori_error_estimate

        return self.posteri_estimate

class VWAPPriceChannelKalman(Strategy):
    """
    VWAP Price Channel Strategy with Kalman Filter
    - Uses VWAP-based dynamic price channels
    - Applies Kalman filter to smooth channel lines and reduce noise
    - Cleaner signals with less whipsaws
    """

    # Strategy parameters
    length = 20  # Lookback period for highest/lowest
    kalman_process_var = 1e-5  # Process variance for Kalman filter
    kalman_measure_var = 1e-1  # Measurement variance for Kalman filter
    atr_multiplier = 2.0  # For stop loss
    take_profit_ratio = 2.5  # Risk/reward ratio

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate highest and lowest over period
        highest = high.rolling(window=self.length, min_periods=1).max()
        lowest = low.rolling(window=self.length, min_periods=1).min()

        # Detect new highs and lows
        new_high = (high == highest).astype(float)
        new_low = (low == lowest).astype(float)

        # Calculate VWAP for highs and lows
        # High VWAP calculation
        high_vwap_values = []
        cumulative_high_vol = 0
        cumulative_high_pv = 0

        for i in range(len(high)):
            if new_high.iloc[i] == 1:
                cumulative_high_vol = volume.iloc[i]
                cumulative_high_pv = high.iloc[i] * volume.iloc[i]
            else:
                cumulative_high_vol += volume.iloc[i]
                cumulative_high_pv += high.iloc[i] * volume.iloc[i]

            if cumulative_high_vol > 0:
                high_vwap_values.append(cumulative_high_pv / cumulative_high_vol)
            else:
                high_vwap_values.append(high.iloc[i])

        # Low VWAP calculation
        low_vwap_values = []
        cumulative_low_vol = 0
        cumulative_low_pv = 0

        for i in range(len(low)):
            if new_low.iloc[i] == 1:
                cumulative_low_vol = volume.iloc[i]
                cumulative_low_pv = low.iloc[i] * volume.iloc[i]
            else:
                cumulative_low_vol += volume.iloc[i]
                cumulative_low_pv += low.iloc[i] * volume.iloc[i]

            if cumulative_low_vol > 0:
                low_vwap_values.append(cumulative_low_pv / cumulative_low_vol)
            else:
                low_vwap_values.append(low.iloc[i])

        high_vwap = pd.Series(high_vwap_values, index=high.index)
        low_vwap = pd.Series(low_vwap_values, index=low.index)

        # Calculate channel bounds
        upper_channel = []
        lower_channel = []

        for i in range(len(close)):
            if i == 0:
                upper_channel.append(highest.iloc[i])
                lower_channel.append(lowest.iloc[i])
            else:
                # Upper channel logic
                if new_high.iloc[i] == 1:
                    upper_channel.append(highest.iloc[i])
                else:
                    h_change = high_vwap.iloc[i] - high_vwap.iloc[i-1] if i > 0 else 0
                    if highest.iloc[i] == highest.iloc[i-1]:
                        upper_channel.append(upper_channel[-1] + h_change)
                    else:
                        upper_channel.append(min(highest.iloc[i], upper_channel[-1] + h_change))

                # Lower channel logic
                if new_low.iloc[i] == 1:
                    lower_channel.append(lowest.iloc[i])
                else:
                    l_change = low_vwap.iloc[i] - low_vwap.iloc[i-1] if i > 0 else 0
                    if lowest.iloc[i] == lowest.iloc[i-1]:
                        lower_channel.append(lower_channel[-1] + l_change)
                    else:
                        lower_channel.append(max(lowest.iloc[i], lower_channel[-1] + l_change))

        upper_channel = pd.Series(upper_channel, index=close.index)
        lower_channel = pd.Series(lower_channel, index=close.index)

        # Apply Kalman filter to smooth the channels
        upper_kalman = KalmanFilter(self.kalman_process_var, self.kalman_measure_var)
        lower_kalman = KalmanFilter(self.kalman_process_var, self.kalman_measure_var)

        upper_filtered = []
        lower_filtered = []

        for i in range(len(upper_channel)):
            upper_filtered.append(upper_kalman.update(upper_channel.iloc[i]))
            lower_filtered.append(lower_kalman.update(lower_channel.iloc[i]))

        upper_channel_smooth = pd.Series(upper_filtered, index=close.index)
        lower_channel_smooth = pd.Series(lower_filtered, index=close.index)

        # Calculate middle channel
        middle_channel = (upper_channel_smooth + lower_channel_smooth) / 2

        # Apply Kalman filter to close price for cleaner signals
        price_kalman = KalmanFilter(self.kalman_process_var, self.kalman_measure_var)
        close_filtered = []
        for i in range(len(close)):
            close_filtered.append(price_kalman.update(close.iloc[i]))

        close_smooth = pd.Series(close_filtered, index=close.index)

        # Trend detection
        dir_values = []
        dir2_values = []
        current_dir2 = 0

        for i in range(len(close)):
            if new_high.iloc[i] == 1:
                dir_values.append(1)
                current_dir2 = 1
            elif new_low.iloc[i] == 1:
                dir_values.append(-1)
                current_dir2 = -1
            else:
                dir_values.append(0)

            dir2_values.append(current_dir2)

        # Store as indicators
        self.upper_channel = self.I(lambda: upper_channel_smooth.ffill().values, name='Upper_Channel_Kalman')
        self.lower_channel = self.I(lambda: lower_channel_smooth.ffill().values, name='Lower_Channel_Kalman')
        self.middle_channel = self.I(lambda: middle_channel.ffill().values, name='Middle_Channel_Kalman')
        self.close_smooth = self.I(lambda: close_smooth.values, name='Close_Kalman')
        self.trend_direction = self.I(lambda: np.array(dir2_values), name='Trend_Direction')

        # ATR for risk management
        self.atr = self.I(ta.atr, high, low, close, 14)

    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < self.length + 5:
            return

        # Get current values
        price = self.data.Close[-1]
        price_smooth = self.close_smooth[-1]

        upper = self.upper_channel[-1]
        lower = self.lower_channel[-1]
        middle = self.middle_channel[-1]
        trend = self.trend_direction[-1]
        atr_value = self.atr[-1]

        # Previous values for crossover detection (using smoothed values)
        if len(self.data.Close) > 1:
            prev_smooth = self.close_smooth[-2]
            prev_upper = self.upper_channel[-2]
            prev_lower = self.lower_channel[-2]
        else:
            return

        # Check for valid values
        if pd.isna(upper) or pd.isna(lower) or pd.isna(price_smooth) or pd.isna(atr_value) or atr_value <= 0:
            return

        # Entry logic using Kalman-filtered signals
        if not self.position:
            # Long signal: Smoothed price crosses above lower channel and trend is bullish
            if prev_smooth <= prev_lower and price_smooth > lower and trend == 1:
                stop_loss = price - (atr_value * self.atr_multiplier)
                take_profit = price + (atr_value * self.atr_multiplier * self.take_profit_ratio)
                self.buy(sl=stop_loss, tp=take_profit, size=0.95)

            # Short signal: Smoothed price crosses below upper channel and trend is bearish
            elif prev_smooth >= prev_upper and price_smooth < upper and trend == -1:
                stop_loss = price + (atr_value * self.atr_multiplier)
                take_profit = price - (atr_value * self.atr_multiplier * self.take_profit_ratio)
                self.sell(sl=stop_loss, tp=take_profit, size=0.95)

        # Exit logic - Exit on opposite signal or middle channel cross
        else:
            # Exit long
            if self.position.is_long:
                # Exit on bearish reversal or middle channel break
                if (price_smooth < middle) or \
                   (prev_smooth >= prev_upper and price_smooth < upper and trend == -1):
                    self.position.close()

            # Exit short
            elif self.position.is_short:
                # Exit on bullish reversal or middle channel break
                if (price_smooth > middle) or \
                   (prev_smooth <= prev_lower and price_smooth > lower and trend == 1):
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S VWAP PRICE CHANNEL KALMAN STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing VWAP Price Channel with Kalman filter across all datasets...")
    print("="*80)

    # Run tests on all data sources without optimization
    results = test_on_all_data(
        VWAPPriceChannelKalman,
        'VWAPPriceChannelKalman',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )

    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/VWAPPriceChannelKalman.csv")
        print("="*80)

if __name__ == "__main__":
    main()