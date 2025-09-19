#!/usr/bin/env python3
"""
Smart Money Breakout + MFI Strategy - FIXED VERSION
Uses Money Flow Index for additional confirmation
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta

class SmartMoneyMFI(Strategy):
    # Channel detection parameters
    lookback_period = 20
    channel_min_bars = 10
    volatility_threshold = 2.5

    # Volume parameters
    volume_ma_period = 20
    volume_multiplier = 1.2

    # MFI parameters
    mfi_period = 14
    mfi_overbought = 70
    mfi_oversold = 30

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

        # Money Flow Index
        self.mfi = self.I(ta.mfi, pd.Series(self.data.High),
                          pd.Series(self.data.Low),
                          pd.Series(self.data.Close),
                          pd.Series(self.data.Volume),
                          length=self.mfi_period)

        # Track channel state
        self.reset_channel()

    def reset_channel(self):
        self.channel_high = 0
        self.channel_low = 0
        self.in_channel = False
        self.channel_bars = 0

    def detect_channel(self, idx):
        """Detect consolidation channels"""
        if idx < self.lookback_period:
            return False

        recent_high = max(self.data.High[-self.lookback_period:])
        recent_low = min(self.data.Low[-self.lookback_period:])
        channel_width = recent_high - recent_low

        current_atr = self.atr[-1] if self.atr[-1] > 0 else 0.001
        width_in_atr = channel_width / current_atr

        if width_in_atr <= self.volatility_threshold:
            if not self.in_channel:
                self.in_channel = True
                self.channel_high = recent_high
                self.channel_low = recent_low
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
        """Check for breakout with MFI confirmation"""
        if not self.in_channel or self.channel_bars < self.channel_min_bars:
            return None

        current_close = self.data.Close[-1]
        current_open = self.data.Open[-1]
        current_volume = self.data.Volume[-1]
        current_mfi = self.mfi[-1] if self.mfi[-1] else 50

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

        # Bullish breakout with MFI confirmation
        if current_close > self.channel_high:
            above_channel = body_low - self.channel_high
            pct_above = above_channel / body_size

            # MFI should be rising but not overbought
            if pct_above >= self.strong_breakout and \
               current_mfi > 40 and current_mfi < self.mfi_overbought:
                self.reset_channel()
                return 'long'

        # Bearish breakout with MFI confirmation
        elif current_close < self.channel_low:
            below_channel = self.channel_low - body_high
            pct_below = below_channel / body_size

            # MFI should be falling but not oversold
            if pct_below >= self.strong_breakout and \
               current_mfi < 60 and current_mfi > self.mfi_oversold:
                self.reset_channel()
                return 'short'

        return None

    def next(self):
        idx = len(self.data) - 1
        if idx < max(self.lookback_period, self.mfi_period) + 1:
            return

        # Detect channel
        self.detect_channel(idx)

        # Manage existing position
        if self.position:
            current_close = self.data.Close[-1]
            current_mfi = self.mfi[-1] if self.mfi[-1] else 50

            if self.position.is_long:
                entry = self.position.entry_price if hasattr(self.position, 'entry_price') else self.data.Close[-2]
                pnl_pct = ((current_close - entry) / entry) * 100

                # Exit on target, stop, or MFI overbought
                if pnl_pct >= self.take_profit_pct or pnl_pct <= -self.stop_loss_pct or \
                   current_mfi >= self.mfi_overbought:
                    self.position.close()

            else:  # Short
                entry = self.position.entry_price if hasattr(self.position, 'entry_price') else self.data.Close[-2]
                pnl_pct = ((entry - current_close) / entry) * 100

                # Exit on target, stop, or MFI oversold
                if pnl_pct >= self.take_profit_pct or pnl_pct <= -self.stop_loss_pct or \
                   current_mfi <= self.mfi_oversold:
                    self.position.close()

        else:
            # Check for new signal
            signal = self.check_breakout()

            if signal == 'long':
                self.buy()
            elif signal == 'short':
                self.sell()