"""
Periodic Linear Regression Strategy with MFI - V2
==================================================

Combines linear regression with Money Flow Index for volume-weighted signals.

Strategy Logic:
- Uses rolling linear regression with lookback period
- MFI confirms money flow direction
- Entry: Regression crossover with MFI confirmation
- Exit: Fixed TP/SL or MFI extremes
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Periodic Linear Regression + MFI V2 Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
LOOKBACK_PERIOD = 20
STD_MULTIPLIER = 2.0
MFI_PERIOD = 14
MFI_OVERBOUGHT = 75
MFI_OVERSOLD = 25
SLOPE_THRESHOLD = 0.0001
TAKE_PROFIT_PERCENT = 3.5
STOP_LOSS_PERCENT = 1.5

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class PeriodicLinearRegressionMFIV2(Strategy):
    # Strategy parameters
    lookback_period = LOOKBACK_PERIOD
    std_multiplier = STD_MULTIPLIER
    mfi_period = MFI_PERIOD
    mfi_overbought = MFI_OVERBOUGHT
    mfi_oversold = MFI_OVERSOLD
    slope_threshold = SLOPE_THRESHOLD
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        # Linear regression indicators
        self.regression_line = self.I(talib.LINEARREG, self.data.Close, self.lookback_period)
        self.regression_slope = self.I(talib.LINEARREG_SLOPE, self.data.Close, self.lookback_period)
        self.stddev = self.I(talib.STDDEV, self.data.Close, self.lookback_period)

        # Bands
        self.upper_band = self.I(lambda: self.regression_line + (self.std_multiplier * self.stddev))
        self.lower_band = self.I(lambda: self.regression_line - (self.std_multiplier * self.stddev))

        # MFI for volume confirmation
        self.mfi = self.I(talib.MFI, self.data.High, self.data.Low, self.data.Close, self.data.Volume, self.mfi_period)

        # RSI for additional confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, 14)

    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.lookback_period, self.mfi_period) + 14:
            return

        # Get current values
        current_price = self.data.Close[-1]
        prev_price = self.data.Close[-2]
        regression_value = self.regression_line[-1]
        prev_regression = self.regression_line[-2]
        slope = self.regression_slope[-1]
        mfi_value = self.mfi[-1]
        rsi_value = self.rsi[-1]
        upper = self.upper_band[-1]
        lower = self.lower_band[-1]

        # Skip if values are invalid
        if np.isnan(regression_value) or np.isnan(slope) or np.isnan(mfi_value):
            return

        # Entry conditions with MFI filter
        if not self.position:
            # Long entry:
            # - Price crosses above regression
            # - Positive slope
            # - MFI shows buying pressure (>50 but not overbought)
            # - RSI not extreme
            if (prev_price <= prev_regression and
                current_price > regression_value and
                slope > self.slope_threshold and
                mfi_value > 50 and mfi_value < self.mfi_overbought and
                rsi_value < 70):

                # Stronger signal if MFI is oversold
                signal_strength = 1.15 if mfi_value < self.mfi_oversold else 1.0

                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit * signal_strength)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            # Short entry:
            # - Price crosses below regression
            # - Negative slope
            # - MFI shows selling pressure (<50 but not oversold)
            # - RSI not extreme
            elif (prev_price >= prev_regression and
                  current_price < regression_value and
                  slope < -self.slope_threshold and
                  mfi_value < 50 and mfi_value > self.mfi_oversold and
                  rsi_value > 30):

                # Stronger signal if MFI is overbought
                signal_strength = 1.15 if mfi_value > self.mfi_overbought else 1.0

                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit * signal_strength)

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

        # Exit conditions with MFI
        else:
            # Exit long if MFI overbought or trend reversal
            if self.position.is_long:
                if (mfi_value > 85 or
                    current_price >= upper or
                    slope < 0 or
                    (mfi_value > self.mfi_overbought and rsi_value > 75)):
                    self.position.close()

            # Exit short if MFI oversold or trend reversal
            elif self.position.is_short:
                if (mfi_value < 15 or
                    current_price <= lower or
                    slope > 0 or
                    (mfi_value < self.mfi_oversold and rsi_value < 25)):
                    self.position.close()

# Run single backtest
bt = Backtest(data, PeriodicLinearRegressionMFIV2, cash=1000000, commission=0.00045)

print("\n🌙 ===== PERIODIC LINEAR REGRESSION + MFI V2 STRATEGY ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI OB/OS: {MFI_OVERBOUGHT}/{MFI_OVERSOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING PERIODIC LINEAR REGRESSION + MFI V2 ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(PeriodicLinearRegressionMFIV2, 'PeriodicLinearRegressionMFIV2')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/PeriodicLinearRegressionMFIV2.csv")