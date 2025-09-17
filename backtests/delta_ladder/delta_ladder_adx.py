"""
Delta Ladder ADX Strategy

This strategy combines Delta Ladder with ADX for trend strength:
- Uses Delta Ladder for volume imbalance detection
- Adds ADX to filter for strong trending conditions
- Only trades when ADX > 25 (strong trend)
- Uses +DI/-DI for additional directional confirmation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta

class DeltaLadderADX(Strategy):
    # Parameters
    delta_rows = 10  # Number of price levels per bar
    volume_lookback = 20  # Lookback for average volume
    adx_period = 14  # ADX period
    adx_threshold = 25  # Minimum ADX for trend strength
    sl_percent = 0.03  # 3% stop loss
    tp_percent = 0.06  # 6% take profit
    min_delta_ratio = 0.3  # Minimum delta ratio for signal

    def init(self):
        # Calculate delta ladder components
        self.delta_data = self.calculate_delta_ladder()

        # Volume average for expansion detection
        self.avg_volume = ta.sma(pd.Series(self.data.Volume), length=self.volume_lookback).values

        # Calculate ADX and DI indicators
        adx_result = ta.adx(
            pd.Series(self.data.High),
            pd.Series(self.data.Low),
            pd.Series(self.data.Close),
            length=self.adx_period
        )

        # Extract ADX, +DI, -DI values
        self.adx = adx_result[f'ADX_{self.adx_period}'].values
        self.plus_di = adx_result[f'DMP_{self.adx_period}'].values
        self.minus_di = adx_result[f'DMN_{self.adx_period}'].values

        # ATR for volatility-based adjustments
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
            'delta_momentum': [],
            'volume_profile': []
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
                delta_data['delta_momentum'].append(0)
                delta_data['volume_profile'].append(0)
                continue

            # Calculate bar range and level size
            bar_range = highs[i] - lows[i]
            if bar_range == 0:
                delta_data['cumulative_delta'].append(delta_data['cumulative_delta'][-1])
                delta_data['poc_level'].append(closes[i])
                delta_data['delta_ratio'].append(0)
                delta_data['is_reversal'].append(False)
                delta_data['delta_momentum'].append(0)
                delta_data['volume_profile'].append(0)
                continue

            level_size = bar_range / self.delta_rows

            # Calculate close position within the bar
            close_position = (closes[i] - lows[i]) / bar_range

            # Determine volume distribution based on price action
            is_bullish = closes[i] > opens[i]
            body_range = abs(closes[i] - opens[i])
            body_ratio = body_range / bar_range if bar_range > 0 else 0

            # Advanced volume distribution
            if is_bullish:
                # Strong bullish bar (large body, closing near high)
                if body_ratio > 0.6 and close_position > 0.8:
                    buy_ratio = 0.75
                # Moderate bullish
                elif body_ratio > 0.3:
                    buy_ratio = 0.65
                # Weak bullish (doji-like)
                else:
                    buy_ratio = 0.55
            else:
                # Strong bearish bar (large body, closing near low)
                if body_ratio > 0.6 and close_position < 0.2:
                    buy_ratio = 0.25
                # Moderate bearish
                elif body_ratio > 0.3:
                    buy_ratio = 0.35
                # Weak bearish (doji-like)
                else:
                    buy_ratio = 0.45

            buy_volume = volumes[i] * buy_ratio
            sell_volume = volumes[i] * (1 - buy_ratio)
            bar_delta = buy_volume - sell_volume

            # Update cumulative delta
            cumulative = delta_data['cumulative_delta'][-1] + bar_delta
            delta_data['cumulative_delta'].append(cumulative)

            # Calculate POC with volume profile logic
            if close_position > 0.7:
                poc = lows[i] + (bar_range * 0.7)  # POC in upper area
            elif close_position < 0.3:
                poc = lows[i] + (bar_range * 0.3)  # POC in lower area
            else:
                # POC near the body center for balanced bars
                poc = (opens[i] + closes[i]) / 2
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

            # Delta momentum (rate of change)
            if i >= 3:
                delta_change = cumulative - delta_data['cumulative_delta'][-3]
                volume_avg = np.mean(volumes[max(0, i-3):i+1])
                if volume_avg > 0:
                    delta_momentum = delta_change / volume_avg
                else:
                    delta_momentum = 0
            else:
                delta_momentum = bar_delta / volumes[i] if volumes[i] > 0 else 0
            delta_data['delta_momentum'].append(delta_momentum)

            # Volume profile strength (how concentrated volume is)
            volume_profile = buy_ratio if bar_delta > 0 else (1 - buy_ratio)
            delta_data['volume_profile'].append(volume_profile)

        return delta_data

    def next(self):
        # Get current index
        idx = len(self.data.Close) - 1

        # Skip if not enough data
        if idx < max(self.volume_lookback, self.adx_period) or idx >= len(self.delta_data['cumulative_delta']):
            return

        # Skip if ADX is NaN
        if idx >= len(self.adx) or pd.isna(self.adx[idx]):
            return

        # Get current values
        current_delta = self.delta_data['cumulative_delta'][idx]
        previous_delta = self.delta_data['cumulative_delta'][idx-1] if idx > 0 else 0
        poc = self.delta_data['poc_level'][idx]
        delta_ratio = self.delta_data['delta_ratio'][idx]
        is_reversal = self.delta_data['is_reversal'][idx]
        delta_momentum = self.delta_data['delta_momentum'][idx]
        volume_profile = self.delta_data['volume_profile'][idx]

        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        avg_vol = self.avg_volume[idx] if idx < len(self.avg_volume) else current_volume

        # ADX values
        current_adx = self.adx[idx]
        plus_di = self.plus_di[idx]
        minus_di = self.minus_di[idx]

        # Volume expansion check
        volume_expansion = current_volume > avg_vol * 1.2

        # Long signal with ADX confirmation
        if not self.position:
            if (current_delta > 0 and  # Positive cumulative delta
                delta_ratio > self.min_delta_ratio and  # Strong delta ratio
                current_price > poc and  # Price above POC
                volume_expansion and  # Volume expansion
                current_adx > self.adx_threshold and  # Strong trend
                plus_di > minus_di and  # Bullish DI crossover
                delta_momentum > 0 and  # Positive delta momentum
                volume_profile > 0.6 and  # Strong buy volume concentration
                (is_reversal or previous_delta < current_delta)):  # Reversal or increasing delta

                # Calculate position size and stops
                stop_price = current_price * (1 - self.sl_percent)
                take_profit = current_price * (1 + self.tp_percent)

                self.buy(
                    sl=stop_price,
                    tp=take_profit
                )

        # Short signal with ADX confirmation
        elif not self.position:
            if (current_delta < 0 and  # Negative cumulative delta
                delta_ratio > self.min_delta_ratio and  # Strong delta ratio
                current_price < poc and  # Price below POC
                volume_expansion and  # Volume expansion
                current_adx > self.adx_threshold and  # Strong trend
                minus_di > plus_di and  # Bearish DI crossover
                delta_momentum < 0 and  # Negative delta momentum
                volume_profile > 0.6 and  # Strong sell volume concentration
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
        DeltaLadderADX,
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
        strategy_class=DeltaLadderADX,
        strategy_name="DeltaLadderADX",
        optimize=False,
        verbose=True
    )

    # Convert results to DataFrame if needed
    if results:
        print("\n" + "="*80)
        print(f"DELTA LADDER ADX - MULTI-DATA TEST RESULTS")
        print("="*80)
        print(f"\nAll tests completed successfully")