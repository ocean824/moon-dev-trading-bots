"""
Delta Ladder Base Strategy

This strategy implements the Delta Ladder concept:
- Divides each bar into price levels (default 10)
- Calculates buy/sell volume delta at each level
- Uses cumulative delta and POC for trading signals
- Trades when delta imbalances indicate directional pressure
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta

class DeltaLadderBase(Strategy):
    # Parameters
    delta_rows = 10  # Number of price levels per bar
    volume_lookback = 20  # Lookback for average volume
    sl_percent = 0.03  # 3% stop loss
    tp_percent = 0.06  # 6% take profit
    min_delta_ratio = 0.2  # Minimum delta ratio for signal

    def init(self):
        # Calculate delta ladder components
        self.delta_data = self.calculate_delta_ladder()

        # Volume average for expansion detection
        self.avg_volume = ta.sma(pd.Series(self.data.Volume), length=self.volume_lookback).values

        # ATR for dynamic stops (optional usage)
        self.atr = ta.atr(
            pd.Series(self.data.High),
            pd.Series(self.data.Low),
            pd.Series(self.data.Close),
            length=14
        ).values

    def calculate_delta_ladder(self):
        """Calculate delta ladder components for each bar"""
        delta_data = {
            'cumulative_delta': [],
            'poc_level': [],
            'delta_ratio': [],
            'is_reversal': []
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
                continue

            # Calculate bar range and level size
            bar_range = highs[i] - lows[i]
            if bar_range == 0:
                delta_data['cumulative_delta'].append(delta_data['cumulative_delta'][-1])
                delta_data['poc_level'].append(closes[i])
                delta_data['delta_ratio'].append(0)
                delta_data['is_reversal'].append(False)
                continue

            level_size = bar_range / self.delta_rows

            # Simplified delta calculation
            # In real implementation, we'd distribute volume across levels
            # For backtesting, we'll use a simplified approach

            # Determine if bar is bullish or bearish
            is_bullish = closes[i] > opens[i]

            # Calculate delta (simplified)
            if is_bullish:
                buy_volume = volumes[i] * 0.6  # Assume 60% buy on bullish bars
                sell_volume = volumes[i] * 0.4
            else:
                buy_volume = volumes[i] * 0.4
                sell_volume = volumes[i] * 0.6

            bar_delta = buy_volume - sell_volume

            # Update cumulative delta
            cumulative = delta_data['cumulative_delta'][-1] + bar_delta
            delta_data['cumulative_delta'].append(cumulative)

            # POC calculation (simplified - use mid-price weighted by volume)
            # In full implementation, track volume at each level
            poc = (highs[i] + lows[i]) / 2
            if is_bullish:
                poc = poc + (bar_range * 0.25)  # POC tends higher on bullish bars
            else:
                poc = poc - (bar_range * 0.25)  # POC tends lower on bearish bars
            delta_data['poc_level'].append(poc)

            # Delta ratio (current delta vs average volume)
            if volumes[i] > 0:
                delta_ratio = abs(bar_delta) / volumes[i]
            else:
                delta_ratio = 0
            delta_data['delta_ratio'].append(delta_ratio)

            # Check for reversal (delta flipped from previous bar)
            prev_delta = delta_data['cumulative_delta'][-2] if i > 1 else 0
            curr_delta = delta_data['cumulative_delta'][-1]
            is_reversal = (prev_delta > 0 and curr_delta < 0) or (prev_delta < 0 and curr_delta > 0)
            delta_data['is_reversal'].append(is_reversal)

        return delta_data

    def next(self):
        # Get current index
        idx = len(self.data.Close) - 1

        # Skip if not enough data
        if idx < self.volume_lookback or idx >= len(self.delta_data['cumulative_delta']):
            return

        # Get current values
        current_delta = self.delta_data['cumulative_delta'][idx]
        previous_delta = self.delta_data['cumulative_delta'][idx-1] if idx > 0 else 0
        poc = self.delta_data['poc_level'][idx]
        delta_ratio = self.delta_data['delta_ratio'][idx]
        is_reversal = self.delta_data['is_reversal'][idx]

        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        avg_vol = self.avg_volume[idx] if idx < len(self.avg_volume) else current_volume

        # Volume expansion check (relaxed)
        volume_expansion = current_volume > avg_vol * 1.1

        # Long signal
        if not self.position:
            if (current_delta > 0 and  # Positive cumulative delta
                delta_ratio > self.min_delta_ratio and  # Strong delta ratio
                current_price > poc):  # Price above POC

                # Calculate position size and stops
                stop_price = current_price * (1 - self.sl_percent)
                take_profit = current_price * (1 + self.tp_percent)

                self.buy(
                    sl=stop_price,
                    tp=take_profit
                )

        # Short signal (separate condition, not elif)
        if not self.position:
            if (current_delta < 0 and  # Negative cumulative delta
                delta_ratio > self.min_delta_ratio and  # Strong delta ratio
                current_price < poc):  # Price below POC

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
        DeltaLadderBase,
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
        strategy_class=DeltaLadderBase,
        strategy_name="DeltaLadderBase",
        optimize=False,
        verbose=True
    )

    # Print completion message
    print("\n" + "="*80)
    print(f"DELTA LADDER BASE - MULTI-DATA TEST RESULTS")
    print("="*80)
    print(f"\nAll tests completed successfully")