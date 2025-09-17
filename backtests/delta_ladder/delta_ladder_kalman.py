"""
Delta Ladder Kalman Strategy

This strategy combines Delta Ladder with Kalman filtering:
- Uses Delta Ladder for volume imbalance detection
- Applies Kalman filter to smooth delta values and reduce noise
- Provides cleaner signals with reduced whipsaws
- Better trend detection through filtered delta
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta

class DeltaLadderKalman(Strategy):
    # Parameters
    delta_rows = 10  # Number of price levels per bar
    volume_lookback = 20  # Lookback for average volume
    kalman_gain = 0.01  # Kalman filter gain (lower = smoother)
    process_variance = 0.01  # Process variance for Kalman
    sl_percent = 0.03  # 3% stop loss
    tp_percent = 0.06  # 6% take profit
    min_delta_ratio = 0.25  # Minimum delta ratio for signal (lower due to smoothing)

    def init(self):
        # Calculate delta ladder components
        self.delta_data = self.calculate_delta_ladder()

        # Apply Kalman filter to delta values
        self.filtered_delta = self.apply_kalman_filter(self.delta_data['cumulative_delta'])
        self.filtered_poc = self.apply_kalman_filter(self.delta_data['poc_level'])

        # Volume average for expansion detection
        self.avg_volume = ta.sma(pd.Series(self.data.Volume), length=self.volume_lookback).values

        # ATR for volatility-based adjustments
        self.atr = ta.atr(
            pd.Series(self.data.High),
            pd.Series(self.data.Low),
            pd.Series(self.data.Close),
            length=14
        ).values

        # Calculate delta velocity (rate of change of filtered delta)
        self.delta_velocity = self.calculate_velocity(self.filtered_delta)

    def apply_kalman_filter(self, data):
        """Apply Kalman filter to smooth the data"""
        filtered = np.zeros(len(data))

        # Initialize Kalman filter parameters
        x_estimate = data[0] if len(data) > 0 else 0  # Initial state estimate
        p_estimate = 1.0  # Initial estimation error covariance

        # Kalman filter parameters
        q = self.process_variance  # Process variance
        r = 0.1  # Measurement variance

        for i in range(len(data)):
            # Prediction step
            x_predict = x_estimate
            p_predict = p_estimate + q

            # Update step
            k_gain = p_predict / (p_predict + r)  # Kalman gain
            x_estimate = x_predict + k_gain * (data[i] - x_predict)
            p_estimate = (1 - k_gain) * p_predict

            filtered[i] = x_estimate

        return filtered

    def calculate_velocity(self, data):
        """Calculate the rate of change (velocity) of the data"""
        velocity = np.zeros(len(data))
        for i in range(1, len(data)):
            velocity[i] = data[i] - data[i-1]
        return velocity

    def calculate_delta_ladder(self):
        """Calculate delta ladder components for each bar"""
        delta_data = {
            'cumulative_delta': [],
            'poc_level': [],
            'delta_ratio': [],
            'is_reversal': [],
            'delta_acceleration': [],
            'volume_concentration': []
        }

        closes = self.data.Close
        opens = self.data.Open
        highs = self.data.High
        lows = self.data.Low
        volumes = self.data.Volume

        for i in range(len(closes)):
            if i == 0:
                delta_data['cumulative_delta'].append(0)
                delta_data['poc_level'].append(closes[i])
                delta_data['delta_ratio'].append(0)
                delta_data['is_reversal'].append(False)
                delta_data['delta_acceleration'].append(0)
                delta_data['volume_concentration'].append(0)
                continue

            # Calculate bar range and level size
            bar_range = highs[i] - lows[i]
            if bar_range == 0:
                delta_data['cumulative_delta'].append(delta_data['cumulative_delta'][-1])
                delta_data['poc_level'].append(closes[i])
                delta_data['delta_ratio'].append(0)
                delta_data['is_reversal'].append(False)
                delta_data['delta_acceleration'].append(0)
                delta_data['volume_concentration'].append(0)
                continue

            level_size = bar_range / self.delta_rows

            # Price action analysis
            close_position = (closes[i] - lows[i]) / bar_range
            open_position = (opens[i] - lows[i]) / bar_range
            body_size = abs(closes[i] - opens[i]) / bar_range

            # Sophisticated volume distribution model
            is_bullish = closes[i] > opens[i]

            # Calculate volume distribution across levels
            if is_bullish:
                # Bullish bar - more buying pressure
                if close_position > 0.8 and body_size > 0.5:
                    # Strong bullish momentum
                    buy_ratio = 0.8
                elif close_position > 0.6:
                    # Moderate bullish
                    buy_ratio = 0.65
                else:
                    # Weak bullish
                    buy_ratio = 0.55

                # Adjust for wicks (rejection levels)
                upper_wick = (highs[i] - closes[i]) / bar_range if bar_range > 0 else 0
                if upper_wick > 0.3:  # Large upper wick suggests selling
                    buy_ratio *= 0.9
            else:
                # Bearish bar - more selling pressure
                if close_position < 0.2 and body_size > 0.5:
                    # Strong bearish momentum
                    buy_ratio = 0.2
                elif close_position < 0.4:
                    # Moderate bearish
                    buy_ratio = 0.35
                else:
                    # Weak bearish
                    buy_ratio = 0.45

                # Adjust for wicks
                lower_wick = (closes[i] - lows[i]) / bar_range if bar_range > 0 else 0
                if lower_wick > 0.3:  # Large lower wick suggests buying
                    buy_ratio *= 1.1
                    buy_ratio = min(buy_ratio, 0.5)  # Cap at 0.5

            buy_volume = volumes[i] * buy_ratio
            sell_volume = volumes[i] * (1 - buy_ratio)
            bar_delta = buy_volume - sell_volume

            # Update cumulative delta
            cumulative = delta_data['cumulative_delta'][-1] + bar_delta
            delta_data['cumulative_delta'].append(cumulative)

            # Dynamic POC calculation
            # POC shifts based on volume concentration
            if is_bullish:
                if close_position > 0.7:
                    poc = lows[i] + (bar_range * (0.6 + close_position * 0.2))
                else:
                    poc = (highs[i] + lows[i]) / 2 + (bar_range * 0.1)
            else:
                if close_position < 0.3:
                    poc = lows[i] + (bar_range * (0.4 - close_position * 0.2))
                else:
                    poc = (highs[i] + lows[i]) / 2 - (bar_range * 0.1)
            delta_data['poc_level'].append(poc)

            # Delta ratio
            if volumes[i] > 0:
                delta_ratio = abs(bar_delta) / volumes[i]
            else:
                delta_ratio = 0
            delta_data['delta_ratio'].append(delta_ratio)

            # Check for reversal
            prev_delta = delta_data['cumulative_delta'][-2] if i > 1 else 0
            curr_delta = delta_data['cumulative_delta'][-1]
            is_reversal = (prev_delta > 0 and curr_delta < 0) or (prev_delta < 0 and curr_delta > 0)
            delta_data['is_reversal'].append(is_reversal)

            # Delta acceleration (second derivative)
            if i >= 2:
                curr_change = cumulative - delta_data['cumulative_delta'][-2]
                prev_change = delta_data['cumulative_delta'][-2] - delta_data['cumulative_delta'][-3]
                acceleration = curr_change - prev_change
                volume_norm = np.mean(volumes[max(0, i-2):i+1])
                if volume_norm > 0:
                    delta_acceleration = acceleration / volume_norm
                else:
                    delta_acceleration = 0
            else:
                delta_acceleration = 0
            delta_data['delta_acceleration'].append(delta_acceleration)

            # Volume concentration (how focused the volume is)
            concentration = max(buy_ratio, 1 - buy_ratio)  # Higher when more one-sided
            delta_data['volume_concentration'].append(concentration)

        return delta_data

    def next(self):
        # Get current index
        idx = len(self.data.Close) - 1

        # Skip if not enough data
        if idx < self.volume_lookback or idx >= len(self.filtered_delta):
            return

        # Get current values
        current_delta = self.filtered_delta[idx]
        previous_delta = self.filtered_delta[idx-1] if idx > 0 else 0
        poc = self.filtered_poc[idx]
        raw_delta = self.delta_data['cumulative_delta'][idx]
        delta_ratio = self.delta_data['delta_ratio'][idx]
        is_reversal = self.delta_data['is_reversal'][idx]
        delta_acceleration = self.delta_data['delta_acceleration'][idx]
        volume_concentration = self.delta_data['volume_concentration'][idx]
        delta_vel = self.delta_velocity[idx]

        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        avg_vol = self.avg_volume[idx] if idx < len(self.avg_volume) else current_volume

        # Volume expansion check
        volume_expansion = current_volume > avg_vol * 1.2

        # Calculate signal strength using Kalman-filtered values
        delta_trend = current_delta - previous_delta
        delta_strength = abs(current_delta) / (avg_vol * 10) if avg_vol > 0 else 0

        # Long signal with Kalman-filtered delta
        if not self.position:
            if (current_delta > 0 and  # Positive filtered delta
                delta_vel > 0 and  # Positive delta velocity
                delta_ratio > self.min_delta_ratio and  # Strong delta ratio
                current_price > poc and  # Price above filtered POC
                volume_expansion and  # Volume expansion
                delta_strength > 0.1 and  # Sufficient delta strength
                volume_concentration > 0.6 and  # Concentrated volume
                (delta_acceleration > 0 or is_reversal)):  # Accelerating or reversal

                # Calculate position size and stops
                stop_price = current_price * (1 - self.sl_percent)
                take_profit = current_price * (1 + self.tp_percent)

                self.buy(
                    sl=stop_price,
                    tp=take_profit
                )

        # Short signal with Kalman-filtered delta
        elif not self.position:
            if (current_delta < 0 and  # Negative filtered delta
                delta_vel < 0 and  # Negative delta velocity
                delta_ratio > self.min_delta_ratio and  # Strong delta ratio
                current_price < poc and  # Price below filtered POC
                volume_expansion and  # Volume expansion
                delta_strength > 0.1 and  # Sufficient delta strength
                volume_concentration > 0.6 and  # Concentrated volume
                (delta_acceleration < 0 or is_reversal)):  # Decelerating or reversal

                # Calculate position size and stops
                stop_price = current_price * (1 + self.sl_percent)
                take_profit = current_price * (1 - self.tp_percent)

                self.sell(
                    sl=stop_price,
                    tp=take_profit
                )

def run_backtest(data, cash=10000, commission=0.002):
    """Run backtest on provided data"""
    bt = Backtest(
        data,
        DeltaLadderKalman,
        cash=cash,
        commission=commission,
        exclusive_orders=True
    )

    stats = bt.run()
    return stats, bt

if __name__ == "__main__":
    # Import multi_data_tester from parent directory
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Run tests on all available datasets
    results = test_on_all_data(
        strategy_class=DeltaLadderKalman,
        strategy_name="DeltaLadderKalman",
        optimize=False,
        verbose=True
    )

    # Convert results to DataFrame if needed
    if results:
        print("\n" + "="*80)
        print(f"DELTA LADDER KALMAN - MULTI-DATA TEST RESULTS")
        print("="*80)
        print(f"\nAll tests completed successfully")