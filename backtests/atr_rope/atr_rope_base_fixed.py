#!/usr/bin/env python3
"""
ATR Rope Base Strategy - FIXED VERSION
Based on the ATR Rope indicator logic
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta

class ATRRopeBase(Strategy):
    # Parameters matching the indicator
    atr_len = 14
    atr_multi = 1.5  # Default from indicator (was too low at 0.5)
    take_profit_pct = 3.0
    stop_loss_pct = 1.5

    def init(self):
        # Calculate ATR
        self.atr = self.I(ta.atr, pd.Series(self.data.High),
                         pd.Series(self.data.Low),
                         pd.Series(self.data.Close), length=self.atr_len)

        # Implement rope smoother
        self.rope = self.I(self.rope_smoother, pd.Series(self.data.Close))

        # Direction detection
        self.direction = self.I(self.detect_direction)

        # Upper and lower bands
        self.upper = self.I(lambda: self.rope + self.atr * self.atr_multi)
        self.lower = self.I(lambda: self.rope - self.atr * self.atr_multi)

    def rope_smoother(self, prices):
        """Rope smoothing algorithm from indicator"""
        if len(prices) < self.atr_len:
            return prices

        rope = np.zeros(len(prices))
        rope[0] = prices[0]

        for i in range(1, len(prices)):
            if i < self.atr_len:
                rope[i] = prices[i]
            else:
                # Get ATR threshold
                atr_val = self.atr[i] if self.atr[i] else 0.001
                threshold = atr_val * self.atr_multi

                # Movement from rope
                move = prices[i] - rope[i-1]

                # Directional movement beyond threshold
                if abs(move) > threshold:
                    rope[i] = rope[i-1] + np.sign(move) * (abs(move) - threshold)
                else:
                    rope[i] = rope[i-1]

        return rope

    def detect_direction(self):
        """Detect rope direction: 1=up, -1=down, 0=flat"""
        if len(self.rope) < 2:
            return np.zeros(len(self.rope))

        direction = np.zeros(len(self.rope))

        for i in range(1, len(self.rope)):
            if self.rope[i] > self.rope[i-1]:
                direction[i] = 1
            elif self.rope[i] < self.rope[i-1]:
                direction[i] = -1
            else:
                # Check for cross - if price crosses rope, direction becomes flat
                if i > 0 and ((self.data.Close[i-1] <= self.rope[i-1] and self.data.Close[i] > self.rope[i]) or
                             (self.data.Close[i-1] >= self.rope[i-1] and self.data.Close[i] < self.rope[i])):
                    direction[i] = 0
                else:
                    direction[i] = direction[i-1] if i > 0 else 0

        return direction

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.atr_len + 2:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_rope = self.rope[-1]
        prev_rope = self.rope[-2]
        current_dir = self.direction[-1]
        prev_dir = self.direction[-2]
        current_atr = self.atr[-1] if self.atr[-1] else 0.001

        # Entry logic
        if not self.position:
            # Trade on direction changes
            if prev_dir != current_dir and current_dir != 0:
                if current_dir == 1:  # Turned bullish
                    self.buy()
                elif current_dir == -1:  # Turned bearish
                    self.sell()

            # Trade on consolidation breakouts (direction was 0, now it's not)
            elif prev_dir == 0 and current_dir != 0:
                if current_dir == 1 and current_price > current_rope:
                    self.buy()
                elif current_dir == -1 and current_price < current_rope:
                    self.sell()

            # Trend following when rope is moving
            elif current_dir == 1 and current_price > current_rope and current_price > self.upper[-1]:
                # Strong bullish breakout above upper band
                self.buy()
            elif current_dir == -1 and current_price < current_rope and current_price < self.lower[-1]:
                # Strong bearish breakout below lower band
                self.sell()

        # Exit logic
        else:
            if self.position.is_long:
                entry_price = self.position.entry_price if hasattr(self.position, 'entry_price') else self.data.Close[-2]
                pnl_pct = ((current_price - entry_price) / entry_price) * 100

                # Exit on profit target, stop loss, or direction change
                if pnl_pct >= self.take_profit_pct or pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                elif current_dir == -1:  # Direction turned bearish
                    self.position.close()
                elif current_price < self.rope[-1] - current_atr:  # Price broke below rope
                    self.position.close()

            else:  # Short position
                entry_price = self.position.entry_price if hasattr(self.position, 'entry_price') else self.data.Close[-2]
                pnl_pct = ((entry_price - current_price) / entry_price) * 100

                # Exit on profit target, stop loss, or direction change
                if pnl_pct >= self.take_profit_pct or pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                elif current_dir == 1:  # Direction turned bullish
                    self.position.close()
                elif current_price > self.rope[-1] + current_atr:  # Price broke above rope
                    self.position.close()