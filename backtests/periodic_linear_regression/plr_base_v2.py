"""
Periodic Linear Regression Strategy - Base Implementation V2
=============================================================

Simplified and more effective implementation of periodic linear regression.
Uses simpler entry/exit conditions to ensure trades are generated.

Strategy Logic:
- Uses rolling linear regression with lookback period
- Entry: Price momentum aligns with regression slope
- Exit: Fixed take profit/stop loss or momentum reversal
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Periodic Linear Regression V2 Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
LOOKBACK_PERIOD = 20  # Shorter for more responsive signals
STD_MULTIPLIER = 1.0  # For band calculation - reduced for more signals
SLOPE_THRESHOLD = 0  # No minimum slope required
TAKE_PROFIT_PERCENT = 3.0  # Take profit
STOP_LOSS_PERCENT = 1.5  # Stop loss

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class PeriodicLinearRegressionBaseV2(Strategy):
    # Strategy parameters
    lookback_period = LOOKBACK_PERIOD
    std_multiplier = STD_MULTIPLIER
    slope_threshold = SLOPE_THRESHOLD
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        # Calculate simple linear regression using pandas_ta LINEARREG
        self.regression_line = self.I(talib.LINEARREG, self.data.Close, self.lookback_period)

        # Calculate slope using LINEARREG_SLOPE
        self.regression_slope = self.I(talib.LINEARREG_SLOPE, self.data.Close, self.lookback_period)

        # Calculate standard deviation for bands
        self.stddev = self.I(talib.STDDEV, self.data.Close, self.lookback_period)

        # Calculate upper and lower bands
        self.upper_band = self.I(lambda: self.regression_line + (self.std_multiplier * self.stddev))
        self.lower_band = self.I(lambda: self.regression_line - (self.std_multiplier * self.stddev))

        # Calculate RSI for momentum confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, 14)

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.lookback_period + 14:  # Need data for regression and RSI
            return

        # Get current values
        current_price = self.data.Close[-1]
        prev_price = self.data.Close[-2]
        regression_value = self.regression_line[-1]
        prev_regression = self.regression_line[-2]
        slope = self.regression_slope[-1]
        rsi_value = self.rsi[-1]
        upper = self.upper_band[-1]
        lower = self.lower_band[-1]

        # Skip if values are invalid
        if np.isnan(regression_value) or np.isnan(slope) or np.isnan(rsi_value):
            return

        # Entry conditions
        if not self.position:
            # Long entry conditions - very simple:
            # Price crosses above regression line from below
            if (prev_price < prev_regression and
                current_price >= regression_value):

                # Calculate stop loss and take profit
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            # Short entry conditions - very simple:
            # Price crosses below regression line from above
            elif (prev_price > prev_regression and
                  current_price <= regression_value):

                # Calculate stop loss and take profit
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

        # Additional exit conditions
        else:
            # Exit long if:
            # - Price touches upper band
            # - Slope turns strongly negative
            # - RSI becomes very overbought
            if self.position.is_long:
                if (current_price >= upper or
                    slope < -self.slope_threshold * 2 or
                    rsi_value > 85):
                    self.position.close()

            # Exit short if:
            # - Price touches lower band
            # - Slope turns strongly positive
            # - RSI becomes very oversold
            elif self.position.is_short:
                if (current_price <= lower or
                    slope > self.slope_threshold * 2 or
                    rsi_value < 15):
                    self.position.close()

# Run single backtest
bt = Backtest(data, PeriodicLinearRegressionBaseV2, cash=1000000, commission=0.00045)

print("\n🌙 ===== PERIODIC LINEAR REGRESSION V2 - BASE STRATEGY ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Std Multiplier: {STD_MULTIPLIER}")
print(f"Slope Threshold: {SLOPE_THRESHOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING PERIODIC LINEAR REGRESSION BASE V2 ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(PeriodicLinearRegressionBaseV2, 'PeriodicLinearRegressionBaseV2')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/PeriodicLinearRegressionBaseV2.csv")