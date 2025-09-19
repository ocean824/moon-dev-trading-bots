#!/usr/bin/env python3
"""
Smart Money Breakout + Kalman Filter Strategy - FIXED VERSION
Uses Kalman filter for noise reduction in channel detection
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta

class SmartMoneyKalman(Strategy):
    # Channel detection parameters
    lookback_period = 20
    channel_min_bars = 10
    volatility_threshold = 2.5

    # Volume parameters
    volume_ma_period = 20
    volume_multiplier = 1.2

    # Kalman filter parameters
    kalman_gain = 0.02
    kalman_covariance = 0.0001

    # Trade parameters
    strong_breakout = 0.5
    take_profit_pct = 3.0
    stop_loss_pct = 1.5

    def init(self):
        # Calculate indicators
        self.atr = self.I(ta.atr, pd.Series(self.data.High),
                         pd.Series(self.data.Low),
                         pd.Series(self.data.Close), length=14)

        self.volume_ma = self.I(ta.sma, pd.Series(self.data.Volume), length=self.volume_ma_period)

        # Apply Kalman filter to price
        self.kalman_price = self.I(self.kalman_filter, pd.Series(self.data.Close))

        # Track channel state
        self.reset_channel()

    def kalman_filter(self, prices):
        """Apply Kalman filter to smooth price data"""
        filtered = np.zeros(len(prices))
        if len(prices) == 0:
            return filtered

        # Initialize
        filtered[0] = prices[0]
        error_cov = self.kalman_covariance

        for i in range(1, len(prices)):
            # Predict
            pred = filtered[i-1]
            pred_error = error_cov + self.kalman_covariance

            # Update
            gain = pred_error / (pred_error + self.kalman_gain)
            filtered[i] = pred + gain * (prices[i] - pred)
            error_cov = (1 - gain) * pred_error

        return filtered

    def reset_channel(self):
        self.channel_high = 0
        self.channel_low = 0
        self.in_channel = False
        self.channel_bars = 0

    def detect_channel(self, idx):
        """Detect consolidation channels using filtered price"""
        if idx < self.lookback_period:
            return False

        # Use Kalman filtered prices for smoother channel detection
        recent_prices = self.kalman_price[-self.lookback_period:]
        recent_high = max(recent_prices) if len(recent_prices) > 0 else self.data.High[-1]
        recent_low = min(recent_prices) if len(recent_prices) > 0 else self.data.Low[-1]
        channel_width = recent_high - recent_low

        current_atr = self.atr[-1] if self.atr[-1] > 0 else 0.001
        width_in_atr = channel_width / current_atr

        if width_in_atr <= self.volatility_threshold:
            if not self.in_channel:
                # Use actual highs/lows for channel boundaries
                self.in_channel = True
                self.channel_high = max(self.data.High[-self.lookback_period:])
                self.channel_low = min(self.data.Low[-self.lookback_period:])
                self.channel_bars = 0
                return True
            else:
                self.channel_bars += 1
                if self.data.High[-1] <= self.channel_high * 1.01 and \
                   self.data.Low[-1] >= self.channel_low * 0.99:
                    return True
                else:
                    self.reset_channel()
                    return False
        else:
            if self.in_channel:
                self.reset_channel()
            return False

    def check_breakout(self):
        """Check for breakout using filtered price confirmation"""
        if not self.in_channel or self.channel_bars < self.channel_min_bars:
            return None

        current_close = self.data.Close[-1]
        current_open = self.data.Open[-1]
        current_volume = self.data.Volume[-1]
        filtered_price = self.kalman_price[-1] if len(self.kalman_price) > 0 else current_close

        # Volume check
        volume_ratio = current_volume / self.volume_ma[-1] if self.volume_ma[-1] > 0 else 1.0

        if volume_ratio < self.volume_multiplier:
            return None

        # Candle body analysis
        body_high = max(current_close, current_open)
        body_low = min(current_close, current_open)
        body_size = body_high - body_low

        if body_size <= 0:
            return None

        # Bullish breakout - both actual and filtered price confirm
        if current_close > self.channel_high and filtered_price > self.channel_high:
            above_channel = body_low - self.channel_high
            pct_above = above_channel / body_size

            if pct_above >= self.strong_breakout:
                self.reset_channel()
                return 'long'

        # Bearish breakout - both actual and filtered price confirm
        elif current_close < self.channel_low and filtered_price < self.channel_low:
            below_channel = self.channel_low - body_high
            pct_below = below_channel / body_size

            if pct_below >= self.strong_breakout:
                self.reset_channel()
                return 'short'

        return None

    def next(self):
        idx = len(self.data) - 1
        if idx < self.lookback_period + 1:
            return

        # Detect channel
        self.detect_channel(idx)

        # Manage existing position
        if self.position:
            current_close = self.data.Close[-1]

            if self.position.is_long:
                entry = self.position.entry_price if hasattr(self.position, 'entry_price') else self.data.Close[-2]
                pnl_pct = ((current_close - entry) / entry) * 100

                if pnl_pct >= self.take_profit_pct or pnl_pct <= -self.stop_loss_pct:
                    self.position.close()

            else:  # Short
                entry = self.position.entry_price if hasattr(self.position, 'entry_price') else self.data.Close[-2]
                pnl_pct = ((entry - current_close) / entry) * 100

                if pnl_pct >= self.take_profit_pct or pnl_pct <= -self.stop_loss_pct:
                    self.position.close()

        else:
            # Check for new signal
            signal = self.check_breakout()

            if signal == 'long':
                self.buy()
            elif signal == 'short':
                self.sell()