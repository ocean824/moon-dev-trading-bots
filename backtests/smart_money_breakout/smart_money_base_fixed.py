#!/usr/bin/env python3
"""
Smart Money Breakout Base Strategy - FIXED VERSION
Detects consolidation channels and trades breakouts with volume confirmation
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta

class SmartMoneyBase(Strategy):
    # Channel detection parameters
    lookback_period = 20
    channel_min_bars = 10
    volatility_threshold = 2.5  # Channel width in ATRs

    # Volume parameters
    volume_ma_period = 20
    volume_multiplier = 1.2

    # Trade parameters
    strong_breakout = 0.5  # 50% of candle body must be outside channel
    take_profit_pct = 3.0
    stop_loss_pct = 1.5

    def init(self):
        # Calculate indicators
        self.atr = self.I(ta.atr, pd.Series(self.data.High),
                         pd.Series(self.data.Low),
                         pd.Series(self.data.Close), length=14)

        self.volume_ma = self.I(ta.sma, pd.Series(self.data.Volume), length=self.volume_ma_period)

        # RSI for filtering
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), length=14)

        # Track channel state
        self.reset_channel()

    def reset_channel(self):
        self.channel_high = 0
        self.channel_low = 0
        self.in_channel = False
        self.channel_bars = 0
        self.channel_start = -1

    def detect_channel(self, idx):
        """Detect consolidation channels"""
        if idx < self.lookback_period:
            return False

        # Get recent price range
        recent_high = max(self.data.High[-self.lookback_period:])
        recent_low = min(self.data.Low[-self.lookback_period:])
        channel_width = recent_high - recent_low

        # Check if range is narrow enough (consolidation)
        current_atr = self.atr[-1] if self.atr[-1] > 0 else 0.001
        width_in_atr = channel_width / current_atr

        if width_in_atr <= self.volatility_threshold:
            if not self.in_channel:
                # New channel detected
                self.in_channel = True
                self.channel_high = recent_high
                self.channel_low = recent_low
                self.channel_bars = 0
                self.channel_start = idx
                return True
            else:
                # Update existing channel
                self.channel_bars += 1
                # Check if price still in channel
                if self.data.High[-1] <= self.channel_high * 1.01 and \
                   self.data.Low[-1] >= self.channel_low * 0.99:
                    return True
                else:
                    # Channel broken
                    self.reset_channel()
                    return False
        else:
            # No consolidation
            if self.in_channel:
                self.reset_channel()
            return False

    def check_breakout(self):
        """Check for channel breakout with volume confirmation"""
        if not self.in_channel or self.channel_bars < self.channel_min_bars:
            return None

        current_close = self.data.Close[-1]
        current_open = self.data.Open[-1]
        current_volume = self.data.Volume[-1]

        # Volume check
        if self.volume_ma[-1] > 0:
            volume_ratio = current_volume / self.volume_ma[-1]
        else:
            volume_ratio = 1.0

        if volume_ratio < self.volume_multiplier:
            return None

        # Calculate candle body
        body_high = max(current_close, current_open)
        body_low = min(current_close, current_open)
        body_size = body_high - body_low

        if body_size <= 0:
            return None

        # Check for bullish breakout
        if current_close > self.channel_high:
            above_channel = body_low - self.channel_high
            pct_above = above_channel / body_size if body_size > 0 else 0

            if pct_above >= self.strong_breakout:
                self.reset_channel()
                return 'long'

        # Check for bearish breakout
        elif current_close < self.channel_low:
            below_channel = self.channel_low - body_high
            pct_below = below_channel / body_size if body_size > 0 else 0

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
            # Check for new breakout signal
            signal = self.check_breakout()

            if signal == 'long':
                # Additional filter: RSI not overbought
                if self.rsi[-1] < 70:
                    self.buy()

            elif signal == 'short':
                # Additional filter: RSI not oversold
                if self.rsi[-1] > 30:
                    self.sell()