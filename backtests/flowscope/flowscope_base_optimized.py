import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's FlowScope Base Optimized Strategy Loading... 🌙")

class FlowScopeBaseOptimized(Strategy):
    """
    FlowScope Base Optimized Strategy - Simplified Volume Profile with POC Analysis

    This is an optimized version of the FlowScope strategy with simplified
    calculations for faster backtesting across multiple datasets.
    """

    # Parameters
    profile_period = 10  # Reduced for faster calculation
    imbalance_threshold = 0.65  # 65% buy volume for long, 35% for short
    take_profit = 0.03
    stop_loss = 0.02

    def init(self):
        # Initialize volume moving average for filtering
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.profile_period)

        # Calculate simplified volume profile and POC
        def calculate_simple_poc(high, low, close, volume, period):
            """
            Simplified POC calculation - uses VWAP as POC proxy
            and volume-weighted close position for buy/sell ratio
            """
            poc_price = np.zeros(len(high))
            buy_percentage = np.zeros(len(high))

            for i in range(period, len(high)):
                # Get period data
                period_high = high[i-period+1:i+1]
                period_low = low[i-period+1:i+1]
                period_close = close[i-period+1:i+1]
                period_volume = volume[i-period+1:i+1]

                # Calculate VWAP as POC proxy
                typical_price = (period_high + period_low + period_close) / 3
                total_volume = np.sum(period_volume)

                if total_volume > 0:
                    poc_price[i] = np.sum(typical_price * period_volume) / total_volume

                    # Calculate buy/sell percentage based on close position
                    ranges = period_high - period_low
                    buy_ratios = np.where(ranges > 0,
                                         (period_close - period_low) / ranges,
                                         0.5)

                    # Volume-weighted buy percentage
                    buy_percentage[i] = np.sum(buy_ratios * period_volume) / total_volume
                else:
                    poc_price[i] = close[i]
                    buy_percentage[i] = 0.5

            return poc_price, buy_percentage

        # Calculate POC and buy percentage
        poc, buy_pct = calculate_simple_poc(
            self.data.High, self.data.Low, self.data.Close,
            self.data.Volume, self.profile_period
        )

        self.poc_price = self.I(lambda: poc)
        self.poc_buy_percentage = self.I(lambda: buy_pct)

        # RSI for additional confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, timeperiod=14)

        # Track entry price for exits
        self.entry_price = None

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.profile_period * 2:
            return

        # Current values
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        poc_price = self.poc_price[-1]
        buy_percentage = self.poc_buy_percentage[-1]
        volume_avg = self.volume_ma[-1]
        current_rsi = self.rsi[-1]

        # Check if we have a position
        if self.position:
            # Exit logic
            if self.position.is_long:
                # Take profit for long
                if current_price >= self.entry_price * (1 + self.take_profit):
                    self.position.close()
                    self.entry_price = None
                # Stop loss for long
                elif current_price <= self.entry_price * (1 - self.stop_loss):
                    self.position.close()
                    self.entry_price = None

            elif self.position.is_short:
                # Take profit for short
                if current_price <= self.entry_price * (1 - self.take_profit):
                    self.position.close()
                    self.entry_price = None
                # Stop loss for short
                elif current_price >= self.entry_price * (1 + self.stop_loss):
                    self.position.close()
                    self.entry_price = None

        else:
            # Entry logic - Volume imbalance signals

            # Check if current volume is significant
            volume_condition = current_volume >= volume_avg * 0.75

            # Price relationship to POC
            price_above_poc = current_price > poc_price
            price_below_poc = current_price < poc_price
            near_poc = abs(current_price - poc_price) / poc_price <= 0.01

            if volume_condition:
                # Long signal: Strong buy volume imbalance
                if buy_percentage >= self.imbalance_threshold:
                    # Best setup: price below POC with buy pressure (bounce)
                    if price_below_poc and current_rsi < 50:
                        self.buy()
                        self.entry_price = current_price
                    # Alternative: near POC with strong buy pressure
                    elif near_poc and buy_percentage >= 0.70:
                        self.buy()
                        self.entry_price = current_price

                # Short signal: Strong sell volume imbalance
                elif buy_percentage <= (1 - self.imbalance_threshold):
                    # Best setup: price above POC with sell pressure (rejection)
                    if price_above_poc and current_rsi > 50:
                        self.sell()
                        self.entry_price = current_price
                    # Alternative: near POC with strong sell pressure
                    elif near_poc and buy_percentage <= 0.30:
                        self.sell()
                        self.entry_price = current_price


# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FLOWSCOPE BASE OPTIMIZED STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    results = test_on_all_data(FlowScopeBaseOptimized, 'FlowScopeBaseOptimized')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FlowScopeBaseOptimized.csv")