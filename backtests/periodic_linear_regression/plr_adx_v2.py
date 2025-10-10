"""
Periodic Linear Regression Strategy with ADX - V2
==================================================

Combines linear regression with ADX for trend strength filtering.

Strategy Logic:
- Uses rolling linear regression with lookback period
- ADX confirms trend strength
- Entry: Regression crossover with strong trend (ADX > 25)
- Exit: Fixed TP/SL or trend weakness
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Periodic Linear Regression + ADX V2 Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
LOOKBACK_PERIOD = 20
STD_MULTIPLIER = 2.0
ADX_PERIOD = 14
ADX_THRESHOLD = 20  # Lowered for more signals
ADX_STRONG = 35
SLOPE_THRESHOLD = 0.0001
TAKE_PROFIT_PERCENT = 3.5
STOP_LOSS_PERCENT = 1.5

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class PeriodicLinearRegressionADXV2(Strategy):
    # Strategy parameters
    lookback_period = LOOKBACK_PERIOD
    std_multiplier = STD_MULTIPLIER
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    adx_strong = ADX_STRONG
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

        # ADX indicators for trend strength
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)

        # RSI for additional confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, 14)

    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.lookback_period, self.adx_period * 2) + 14:
            return

        # Get current values
        current_price = self.data.Close[-1]
        prev_price = self.data.Close[-2]
        regression_value = self.regression_line[-1]
        prev_regression = self.regression_line[-2]
        slope = self.regression_slope[-1]
        adx_value = self.adx[-1]
        plus_di = self.plus_di[-1]
        minus_di = self.minus_di[-1]
        rsi_value = self.rsi[-1]
        upper = self.upper_band[-1]
        lower = self.lower_band[-1]

        # Skip if values are invalid
        if (np.isnan(regression_value) or np.isnan(slope) or np.isnan(adx_value) or
            np.isnan(plus_di) or np.isnan(minus_di)):
            return

        # Entry conditions with ADX filter
        if not self.position:
            # Long entry:
            # - Price crosses above regression
            # - Positive slope
            # - ADX shows trend (>threshold)
            # - DI+ > DI- for uptrend
            # - RSI not extreme
            if (prev_price <= prev_regression and
                current_price > regression_value and
                slope > self.slope_threshold and
                adx_value > self.adx_threshold and
                plus_di > minus_di and
                rsi_value < 70):

                # Stronger signal if ADX is very strong
                signal_strength = 1.2 if adx_value > self.adx_strong else 1.0

                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit * signal_strength)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            # Short entry:
            # - Price crosses below regression
            # - Negative slope
            # - ADX shows trend (>threshold)
            # - DI- > DI+ for downtrend
            # - RSI not extreme
            elif (prev_price >= prev_regression and
                  current_price < regression_value and
                  slope < -self.slope_threshold and
                  adx_value > self.adx_threshold and
                  minus_di > plus_di and
                  rsi_value > 30):

                # Stronger signal if ADX is very strong
                signal_strength = 1.2 if adx_value > self.adx_strong else 1.0

                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit * signal_strength)

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

        # Exit conditions with ADX
        else:
            # Exit long if trend weakens or reverses
            if self.position.is_long:
                if (adx_value < 15 or  # Trend too weak
                    minus_di > plus_di * 1.2 or  # DI reversal
                    current_price >= upper or
                    slope < 0 or
                    rsi_value > 80):
                    self.position.close()

            # Exit short if trend weakens or reverses
            elif self.position.is_short:
                if (adx_value < 15 or  # Trend too weak
                    plus_di > minus_di * 1.2 or  # DI reversal
                    current_price <= lower or
                    slope > 0 or
                    rsi_value < 20):
                    self.position.close()

# Run single backtest
bt = Backtest(data, PeriodicLinearRegressionADXV2, cash=1000000, commission=0.00045)

print("\n🌙 ===== PERIODIC LINEAR REGRESSION + ADX V2 STRATEGY ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Threshold/Strong: {ADX_THRESHOLD}/{ADX_STRONG}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING PERIODIC LINEAR REGRESSION + ADX V2 ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(PeriodicLinearRegressionADXV2, 'PeriodicLinearRegressionADXV2')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/PeriodicLinearRegressionADXV2.csv")