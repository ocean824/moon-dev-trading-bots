"""
Delta Ladder Simple Strategy

A simplified version of Delta Ladder that focuses on core concepts:
- Uses volume imbalance between buy and sell pressure
- Tracks cumulative delta for trend direction
- Simpler POC calculation
- More reliable signal generation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta

class DeltaLadderSimple(Strategy):
    # Parameters
    volume_lookback = 14  # Lookback for volume analysis
    delta_lookback = 10  # Lookback for delta smoothing
    sl_percent = 0.02  # 2% stop loss
    tp_percent = 0.04  # 4% take profit
    min_volume_ratio = 1.0  # Minimum volume ratio vs average

    def init(self):
        # Calculate volume delta
        self.volume_delta = self.calculate_volume_delta()

        # Calculate cumulative delta with smoothing
        cumulative = np.cumsum(self.volume_delta)
        self.cumulative_delta = ta.sma(pd.Series(cumulative), length=self.delta_lookback).values

        # Volume average
        self.avg_volume = ta.sma(pd.Series(self.data.Volume), length=self.volume_lookback).values

        # ATR for volatility reference
        self.atr = ta.atr(
            pd.Series(self.data.High),
            pd.Series(self.data.Low),
            pd.Series(self.data.Close),
            length=14
        ).values

    def calculate_volume_delta(self):
        """Calculate volume delta for each bar"""
        delta = np.zeros(len(self.data.Close))

        for i in range(len(self.data.Close)):
            # Price action analysis
            close = self.data.Close[i]
            open_price = self.data.Open[i]
            high = self.data.High[i]
            low = self.data.Low[i]
            volume = self.data.Volume[i]

            # Calculate price position within bar
            if high - low > 0:
                close_position = (close - low) / (high - low)
            else:
                close_position = 0.5

            # Determine buy/sell pressure
            if close > open_price:
                # Bullish bar
                buy_pressure = 0.5 + (close_position * 0.4)
            elif close < open_price:
                # Bearish bar
                buy_pressure = 0.5 - ((1 - close_position) * 0.4)
            else:
                # Doji
                buy_pressure = 0.5

            # Calculate delta
            buy_volume = volume * buy_pressure
            sell_volume = volume * (1 - buy_pressure)
            delta[i] = buy_volume - sell_volume

        return delta

    def next(self):
        # Get current index
        idx = len(self.data.Close) - 1

        # Skip if not enough data
        if idx < max(self.volume_lookback, self.delta_lookback) + 1:
            return

        if idx >= len(self.cumulative_delta) or pd.isna(self.cumulative_delta[idx]):
            return

        # Current values
        current_delta = self.cumulative_delta[idx]
        prev_delta = self.cumulative_delta[idx-1] if idx > 0 else 0
        delta_change = current_delta - prev_delta

        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        avg_vol = self.avg_volume[idx] if idx < len(self.avg_volume) else current_volume

        # Volume condition
        if avg_vol == 0:
            return
        volume_ratio = current_volume / avg_vol

        # Long signal
        if not self.position:
            if (current_delta > 0 and  # Positive delta
                delta_change > 0 and  # Increasing delta
                volume_ratio >= self.min_volume_ratio):  # Sufficient volume

                # Calculate stops
                stop_price = current_price * (1 - self.sl_percent)
                take_profit = current_price * (1 + self.tp_percent)

                self.buy(sl=stop_price, tp=take_profit)

        # Short signal
        if not self.position:
            if (current_delta < 0 and  # Negative delta
                delta_change < 0 and  # Decreasing delta
                volume_ratio >= self.min_volume_ratio):  # Sufficient volume

                # Calculate stops
                stop_price = current_price * (1 + self.sl_percent)
                take_profit = current_price * (1 - self.tp_percent)

                self.sell(sl=stop_price, tp=take_profit)

def run_backtest(data, cash=10000, commission=0.002):
    """Run backtest on provided data"""
    bt = Backtest(
        data,
        DeltaLadderSimple,
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
        strategy_class=DeltaLadderSimple,
        strategy_name="DeltaLadderSimple",
        optimize=False,
        verbose=True
    )

    # Print completion message
    print("\n" + "="*80)
    print(f"DELTA LADDER SIMPLE - MULTI-DATA TEST RESULTS")
    print("="*80)
    print(f"\nAll tests completed successfully")