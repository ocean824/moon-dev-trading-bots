"""
Delta Ladder MFI Strategy

This strategy combines Delta Ladder with Money Flow Index (MFI):
- Uses Delta Ladder for volume imbalance detection
- Adds MFI for volume-weighted momentum confirmation
- MFI > 50 for longs, MFI < 50 for shorts
- Enhances signal quality with volume flow confirmation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta

class DeltaLadderMFI(Strategy):
    # Parameters
    delta_rows = 10  # Number of price levels per bar
    volume_lookback = 20  # Lookback for average volume
    mfi_period = 14  # MFI period
    mfi_overbought = 70  # MFI overbought level
    mfi_oversold = 30  # MFI oversold level
    sl_percent = 0.03  # 3% stop loss
    tp_percent = 0.06  # 6% take profit
    min_delta_ratio = 0.3  # Minimum delta ratio for signal

    def init(self):
        # Calculate delta ladder components
        self.delta_data = self.calculate_delta_ladder()

        # Volume average for expansion detection
        self.avg_volume = ta.sma(pd.Series(self.data.Volume), length=self.volume_lookback).values

        # Calculate MFI
        self.mfi = ta.mfi(
            pd.Series(self.data.High),
            pd.Series(self.data.Low),
            pd.Series(self.data.Close),
            pd.Series(self.data.Volume),
            length=self.mfi_period
        ).values

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
            'is_reversal': [],
            'delta_strength': []
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
                delta_data['delta_strength'].append(0)
                continue

            # Calculate bar range and level size
            bar_range = highs[i] - lows[i]
            if bar_range == 0:
                delta_data['cumulative_delta'].append(delta_data['cumulative_delta'][-1])
                delta_data['poc_level'].append(closes[i])
                delta_data['delta_ratio'].append(0)
                delta_data['is_reversal'].append(False)
                delta_data['delta_strength'].append(0)
                continue

            level_size = bar_range / self.delta_rows

            # Enhanced delta calculation with close position consideration
            close_position = (closes[i] - lows[i]) / bar_range if bar_range > 0 else 0.5

            # Determine buy/sell volume based on price action
            is_bullish = closes[i] > opens[i]

            # More sophisticated volume distribution
            if is_bullish:
                buy_ratio = 0.5 + (close_position * 0.3)  # 50-80% buy on bullish bars
                sell_ratio = 1 - buy_ratio
            else:
                sell_ratio = 0.5 + ((1 - close_position) * 0.3)  # 50-80% sell on bearish bars
                buy_ratio = 1 - sell_ratio

            buy_volume = volumes[i] * buy_ratio
            sell_volume = volumes[i] * sell_ratio
            bar_delta = buy_volume - sell_volume

            # Update cumulative delta
            cumulative = delta_data['cumulative_delta'][-1] + bar_delta
            delta_data['cumulative_delta'].append(cumulative)

            # POC calculation with volume weighting
            if close_position > 0.7:
                poc = lows[i] + (bar_range * 0.75)  # POC in upper quartile
            elif close_position < 0.3:
                poc = lows[i] + (bar_range * 0.25)  # POC in lower quartile
            else:
                poc = (highs[i] + lows[i]) / 2  # POC at midpoint
            delta_data['poc_level'].append(poc)

            # Delta ratio (current delta vs average volume)
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

            # Delta strength (normalized cumulative delta)
            if i >= 10:
                recent_volume_avg = np.mean(volumes[max(0, i-10):i+1])
                if recent_volume_avg > 0:
                    delta_strength = abs(cumulative) / recent_volume_avg
                else:
                    delta_strength = 0
            else:
                delta_strength = abs(bar_delta) / volumes[i] if volumes[i] > 0 else 0
            delta_data['delta_strength'].append(delta_strength)

        return delta_data

    def next(self):
        # Get current index
        idx = len(self.data.Close) - 1

        # Skip if not enough data
        if idx < max(self.volume_lookback, self.mfi_period) or idx >= len(self.delta_data['cumulative_delta']):
            return

        # Skip if MFI is NaN
        if idx >= len(self.mfi) or pd.isna(self.mfi[idx]):
            return

        # Get current values
        current_delta = self.delta_data['cumulative_delta'][idx]
        previous_delta = self.delta_data['cumulative_delta'][idx-1] if idx > 0 else 0
        poc = self.delta_data['poc_level'][idx]
        delta_ratio = self.delta_data['delta_ratio'][idx]
        is_reversal = self.delta_data['is_reversal'][idx]
        delta_strength = self.delta_data['delta_strength'][idx]

        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        avg_vol = self.avg_volume[idx] if idx < len(self.avg_volume) else current_volume
        current_mfi = self.mfi[idx]

        # Volume expansion check
        volume_expansion = current_volume > avg_vol * 1.2

        # Long signal with MFI confirmation
        if not self.position:
            if (current_delta > 0 and  # Positive cumulative delta
                delta_ratio > self.min_delta_ratio and  # Strong delta ratio
                current_price > poc and  # Price above POC
                volume_expansion and  # Volume expansion
                current_mfi > 50 and  # MFI bullish
                current_mfi < self.mfi_overbought and  # Not overbought
                delta_strength > 0.5 and  # Strong delta
                (is_reversal or previous_delta < current_delta)):  # Reversal or increasing delta

                # Calculate position size and stops
                stop_price = current_price * (1 - self.sl_percent)
                take_profit = current_price * (1 + self.tp_percent)

                self.buy(
                    sl=stop_price,
                    tp=take_profit
                )

        # Short signal with MFI confirmation
        elif not self.position:
            if (current_delta < 0 and  # Negative cumulative delta
                delta_ratio > self.min_delta_ratio and  # Strong delta ratio
                current_price < poc and  # Price below POC
                volume_expansion and  # Volume expansion
                current_mfi < 50 and  # MFI bearish
                current_mfi > self.mfi_oversold and  # Not oversold
                delta_strength > 0.5 and  # Strong delta
                (is_reversal or previous_delta > current_delta)):  # Reversal or decreasing delta

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
        DeltaLadderMFI,
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
        strategy_class=DeltaLadderMFI,
        strategy_name="DeltaLadderMFI",
        optimize=False,
        verbose=True
    )

    # Convert results to DataFrame if needed
    if results:
        print("\n" + "="*80)
        print(f"DELTA LADDER MFI - MULTI-DATA TEST RESULTS")
        print("="*80)
        print(f"\nAll tests completed successfully")