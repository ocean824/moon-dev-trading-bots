"""
Combined Trend Strategy - Kalman Filter Version
Adds Kalman filter for signal smoothing to reduce false signals
"""

import sys
import os
import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
import pandas_ta as ta
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data


class KalmanFilter:
    """Simple Kalman Filter implementation for price smoothing"""
    def __init__(self, process_variance=0.05, measurement_variance=0.1):
        self.q = process_variance  # Process variance
        self.r = measurement_variance  # Measurement variance
        self.x = None  # State estimate
        self.p = 1.0  # Error covariance
        self.k = 0  # Kalman gain

    def update(self, measurement):
        """Update filter with new measurement"""
        if self.x is None:
            self.x = measurement
            return self.x

        # Prediction
        self.p = self.p + self.q

        # Update
        self.k = self.p / (self.p + self.r)
        self.x = self.x + self.k * (measurement - self.x)
        self.p = (1 - self.k) * self.p

        return self.x


class CombinedTrendKalman(Strategy):
    # Target Trend parameters
    sma_length = 50
    atr_period = 14
    atr_mult = 1.5

    # Zero-Lag MA parameters
    zlma_period = 20
    ema_period = 20

    # Kalman filter parameters
    kalman_process_var = 0.05
    kalman_measurement_var = 0.1

    # Risk management
    target1_mult = 5
    target2_mult = 10
    target3_mult = 15
    stop_loss_pct = 0.03
    take_profit_pct = 0.06

    def init(self):
        # Target Trend components
        self.sma_high = self.I(ta.sma, pd.Series(self.data.High), self.sma_length)
        self.sma_low = self.I(ta.sma, pd.Series(self.data.Low), self.sma_length)

        # ATR for bands
        high_series = pd.Series(self.data.High)
        low_series = pd.Series(self.data.Low)
        close_series = pd.Series(self.data.Close)

        self.atr = self.I(ta.atr, high_series, low_series, close_series, self.atr_period)

        # Zero-Lag MA calculation
        ema_close = ta.ema(close_series, self.ema_period)
        zlma_input = close_series + (close_series - ema_close)
        self.zlma = self.I(ta.ema, zlma_input, self.zlma_period)
        self.ema = self.I(ta.ema, close_series, self.ema_period)

        # Apply Kalman filter to smooth price data
        self.kalman_prices = self.I(self.apply_kalman_filter, close_series)

        # Track position entry for targets
        self.entry_price = 0
        self.position_type = 0
        self.target1_hit = False
        self.target2_hit = False

        # Signal smoothing with Kalman
        self.trend_signal_buffer = []
        self.zlma_signal_buffer = []

    def apply_kalman_filter(self, prices):
        """Apply Kalman filter to price series"""
        kf = KalmanFilter(self.kalman_process_var, self.kalman_measurement_var)
        filtered_prices = np.zeros(len(prices))

        for i, price in enumerate(prices):
            if not pd.isna(price):
                filtered_prices[i] = kf.update(price)
            else:
                filtered_prices[i] = np.nan

        return filtered_prices

    def calculate_trend_signals_kalman(self, index):
        """Calculate Target Trend signals with Kalman smoothed prices"""
        if index < max(self.sma_length, self.atr_period):
            return 0

        # Use Kalman filtered price
        close = self.kalman_prices[index]
        sma_high = self.sma_high[index]
        sma_low = self.sma_low[index]
        atr = self.atr[index]

        # Bullish trend when close > SMA_high + ATR
        if close > sma_high + (atr * self.atr_mult):
            return 1
        # Bearish trend when close < SMA_low - ATR
        elif close < sma_low - (atr * self.atr_mult):
            return -1
        return 0

    def calculate_zlma_signals_kalman(self, index):
        """Calculate Zero-Lag MA signals with smoothing"""
        if index < max(self.zlma_period, self.ema_period) + 1:
            return 0

        # ZLMA crossover signals with Kalman smoothed confirmation
        zlma_curr = self.zlma[index]
        zlma_prev = self.zlma[index - 1]
        ema_curr = self.ema[index]
        ema_prev = self.ema[index - 1]

        # Use Kalman price for additional confirmation
        kalman_price = self.kalman_prices[index]
        kalman_prev = self.kalman_prices[index - 1] if index > 0 else kalman_price

        # Bullish crossover with Kalman confirmation
        if zlma_prev <= ema_prev and zlma_curr > ema_curr and kalman_price > kalman_prev:
            return 1
        # Bearish crossover with Kalman confirmation
        elif zlma_prev >= ema_prev and zlma_curr < ema_curr and kalman_price < kalman_prev:
            return -1
        return 0

    def smooth_signal(self, signal, buffer, window=3):
        """Smooth signals to reduce false triggers"""
        buffer.append(signal)
        if len(buffer) > window:
            buffer.pop(0)

        if len(buffer) < window:
            return 0

        # Return signal only if majority agrees
        signal_sum = sum(buffer)
        if signal_sum >= window - 1:  # At least 2 out of 3 for long
            return 1
        elif signal_sum <= -(window - 1):  # At least 2 out of 3 for short
            return -1
        return 0

    def calculate_targets(self, entry_price, is_long):
        """Calculate ATR-based target levels"""
        atr = self.atr[-1]
        if is_long:
            target1 = entry_price + (atr * self.target1_mult)
            target2 = entry_price + (atr * self.target2_mult)
            target3 = entry_price + (atr * self.target3_mult)
            stop = entry_price - (atr * self.atr_mult)
        else:
            target1 = entry_price - (atr * self.target1_mult)
            target2 = entry_price - (atr * self.target2_mult)
            target3 = entry_price - (atr * self.target3_mult)
            stop = entry_price + (atr * self.atr_mult)

        return target1, target2, target3, stop

    def next(self):
        index = len(self.data) - 1
        close = self.data.Close[-1]

        # Get raw signals
        trend_signal_raw = self.calculate_trend_signals_kalman(index)
        zlma_signal_raw = self.calculate_zlma_signals_kalman(index)

        # Apply signal smoothing to reduce noise
        trend_signal = self.smooth_signal(trend_signal_raw, self.trend_signal_buffer)
        zlma_signal = self.smooth_signal(zlma_signal_raw, self.zlma_signal_buffer)

        # Check existing position management
        if self.position:
            # Use Kalman filtered price for exits
            kalman_price = self.kalman_prices[-1]

            # Long position management
            if self.position.is_long:
                # Calculate targets
                target1, target2, target3, stop = self.calculate_targets(self.entry_price, True)

                # Progressive exit strategy using Kalman filtered price
                if not self.target1_hit and kalman_price >= target1:
                    self.position.close(0.33)
                    self.target1_hit = True
                elif self.target1_hit and not self.target2_hit and kalman_price >= target2:
                    self.position.close(0.5)
                    self.target2_hit = True
                elif self.target2_hit and kalman_price >= target3:
                    self.position.close()
                    self.reset_position_tracking()
                # Stop loss
                elif kalman_price <= stop or close <= self.entry_price * (1 - self.stop_loss_pct):
                    self.position.close()
                    self.reset_position_tracking()

            # Short position management
            elif self.position.is_short:
                # Calculate targets
                target1, target2, target3, stop = self.calculate_targets(self.entry_price, False)

                # Progressive exit strategy using Kalman filtered price
                if not self.target1_hit and kalman_price <= target1:
                    self.position.close(0.33)
                    self.target1_hit = True
                elif self.target1_hit and not self.target2_hit and kalman_price <= target2:
                    self.position.close(0.5)
                    self.target2_hit = True
                elif self.target2_hit and kalman_price <= target3:
                    self.position.close()
                    self.reset_position_tracking()
                # Stop loss
                elif kalman_price >= stop or close >= self.entry_price * (1 + self.stop_loss_pct):
                    self.position.close()
                    self.reset_position_tracking()

        # Entry logic - both smoothed signals must agree
        else:
            # Long entry: Both smoothed signals bullish
            if trend_signal == 1 and zlma_signal == 1:
                self.buy()
                self.entry_price = close
                self.position_type = 1
                self.reset_targets()

            # Short entry: Both smoothed signals bearish
            elif trend_signal == -1 and zlma_signal == -1:
                self.sell()
                self.entry_price = close
                self.position_type = -1
                self.reset_targets()

    def reset_targets(self):
        """Reset target tracking"""
        self.target1_hit = False
        self.target2_hit = False

    def reset_position_tracking(self):
        """Reset all position tracking variables"""
        self.entry_price = 0
        self.position_type = 0
        self.reset_targets()
        # Clear signal buffers
        self.trend_signal_buffer = []
        self.zlma_signal_buffer = []


def run_backtest(data, strategy_class=CombinedTrendKalman, cash=10000, commission=0.002):
    """Run backtest with the strategy"""
    bt = Backtest(data, strategy_class, cash=cash, commission=commission)
    stats = bt.run()
    return stats, bt


def main():
    """Run strategy on multiple datasets"""
    strategy_name = "CombinedTrendKalman"

    # Run backtests on all datasets
    results_df = test_on_all_data(
        strategy_class=CombinedTrendKalman,
        strategy_name=strategy_name,
        optimize=False,
        cash=10000,
        commission=0.002
    )

    # Print aggregate statistics
    print("\n" + "="*80)
    print(f"AGGREGATE RESULTS FOR {strategy_name}")
    print("="*80)

    if results_df is not None and not results_df.empty:
        print("\nSummary Statistics:")
        print(f"Total Datasets Tested: {len(results_df)}")
        print(f"Profitable Strategies: {(results_df['Return_%'] > 0).sum()}")
        print(f"Average Return: {results_df['Return_%'].mean():.2f}%")
        print(f"Best Return: {results_df['Return_%'].max():.2f}%")
        print(f"Worst Return: {results_df['Return_%'].min():.2f}%")
        print(f"Average Sharpe Ratio: {results_df['Sharpe'].mean():.2f}")
        print(f"Average Max Drawdown: {results_df['Max_DD_%'].mean():.2f}%")
        print(f"Average Win Rate: {results_df['Win_Rate_%'].mean():.2f}%")
    else:
        print("No results generated")


if __name__ == "__main__":
    main()