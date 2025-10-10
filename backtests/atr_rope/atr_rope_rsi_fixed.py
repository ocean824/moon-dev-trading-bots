#!/usr/bin/env python3
"""
ATR Rope + RSI Strategy - FIXED VERSION
Combines ATR Rope with RSI for confirmation
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta

class ATRRopeRSI(Strategy):
    # Parameters
    atr_len = 14
    atr_multi = 1.5
    rsi_period = 14
    rsi_overbought = 70
    rsi_oversold = 30
    take_profit_pct = 3.0
    stop_loss_pct = 1.5

    def init(self):
        # Calculate ATR
        self.atr = self.I(ta.atr, pd.Series(self.data.High),
                         pd.Series(self.data.Low),
                         pd.Series(self.data.Close), length=self.atr_len)

        # Calculate RSI
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), length=self.rsi_period)

        # Implement rope smoother
        self.rope = self.I(self.rope_smoother, pd.Series(self.data.Close))

        # Direction detection
        self.direction = self.I(self.detect_direction)

        # Bands
        self.upper = self.I(lambda: self.rope + self.atr * self.atr_multi)
        self.lower = self.I(lambda: self.rope - self.atr * self.atr_multi)

    def rope_smoother(self, prices):
        """Rope smoothing algorithm"""
        if len(prices) < self.atr_len:
            return prices

        rope = np.zeros(len(prices))
        rope[0] = prices[0]

        for i in range(1, len(prices)):
            if i < self.atr_len:
                rope[i] = prices[i]
            else:
                atr_val = self.atr[i] if self.atr[i] else 0.001
                threshold = atr_val * self.atr_multi
                move = prices[i] - rope[i-1]

                if abs(move) > threshold:
                    rope[i] = rope[i-1] + np.sign(move) * (abs(move) - threshold)
                else:
                    rope[i] = rope[i-1]

        return rope

    def detect_direction(self):
        """Detect rope direction"""
        if len(self.rope) < 2:
            return np.zeros(len(self.rope))

        direction = np.zeros(len(self.rope))

        for i in range(1, len(self.rope)):
            if self.rope[i] > self.rope[i-1]:
                direction[i] = 1
            elif self.rope[i] < self.rope[i-1]:
                direction[i] = -1
            else:
                if i > 0 and ((self.data.Close[i-1] <= self.rope[i-1] and self.data.Close[i] > self.rope[i]) or
                             (self.data.Close[i-1] >= self.rope[i-1] and self.data.Close[i] < self.rope[i])):
                    direction[i] = 0
                else:
                    direction[i] = direction[i-1] if i > 0 else 0

        return direction

    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.atr_len, self.rsi_period) + 2:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_rope = self.rope[-1]
        current_dir = self.direction[-1]
        prev_dir = self.direction[-2]
        current_rsi = self.rsi[-1] if self.rsi[-1] else 50

        # Entry logic with RSI confirmation
        if not self.position:
            # Direction change with RSI confirmation
            if prev_dir != current_dir and current_dir != 0:
                if current_dir == 1 and current_rsi < self.rsi_overbought:
                    self.buy()
                elif current_dir == -1 and current_rsi > self.rsi_oversold:
                    self.sell()

            # Consolidation breakout with RSI
            elif prev_dir == 0 and current_dir != 0:
                if current_dir == 1 and current_rsi > 40 and current_rsi < self.rsi_overbought:
                    self.buy()
                elif current_dir == -1 and current_rsi < 60 and current_rsi > self.rsi_oversold:
                    self.sell()

            # RSI divergence signals
            elif current_rsi < self.rsi_oversold and current_dir >= 0:
                # Oversold bounce
                self.buy()
            elif current_rsi > self.rsi_overbought and current_dir <= 0:
                # Overbought reversal
                self.sell()

        # Exit logic
        else:
            if self.position.is_long:
                entry_price = self.position.entry_price if hasattr(self.position, 'entry_price') else self.data.Close[-2]
                pnl_pct = ((current_price - entry_price) / entry_price) * 100

                if pnl_pct >= self.take_profit_pct or pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                elif current_dir == -1 or current_rsi >= self.rsi_overbought:
                    self.position.close()

            else:  # Short
                entry_price = self.position.entry_price if hasattr(self.position, 'entry_price') else self.data.Close[-2]
                pnl_pct = ((entry_price - current_price) / entry_price) * 100

                if pnl_pct >= self.take_profit_pct or pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                elif current_dir == 1 or current_rsi <= self.rsi_oversold:
                    self.position.close()