"""
FINAL WORKING RSI STRATEGY - TESTED PATTERN
============================================
Created by: Moon Dev
Date: 2025-01-30

STRATEGY OVERVIEW:
Simple RSI strategy following the proven pattern from other working backtests.
Uses RSI extremes for entry signals.

ENTRY RULES:
LONG: RSI crosses below 30
SHORT: RSI crosses above 70
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Final Working Strategy Loading... 🌙")

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RISK_MULTIPLIER = 2
MIN_STOP_DISTANCE = 0.05  # 5% minimum stop

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class FinalRSIStrategy(Strategy):
    """Final working RSI strategy using proven patterns"""
    rsi_period = RSI_PERIOD
    rsi_oversold = RSI_OVERSOLD
    rsi_overbought = RSI_OVERBOUGHT
    risk_multiplier = RISK_MULTIPLIER
    min_stop_distance = MIN_STOP_DISTANCE

    def init(self):
        """Initialize RSI using talib like working examples"""
        print("🎯 Moon Dev's Strategy Initialization")
        # Use talib RSI
        self.rsi = self.I(talib.RSI, self.data.Close, self.rsi_period)
        print("✨ RSI Indicator Created Successfully!")

    def next(self):
        """Execute trading logic"""
        price = self.data.Close[-1]

        if price <= 0:
            return

        # Calculate stop and target distances
        sl_distance = self.min_stop_distance * price
        tp_distance = sl_distance * self.risk_multiplier

        # Entry conditions - simple RSI extremes
        if not self.position:
            # LONG when RSI is oversold
            if self.rsi[-1] < self.rsi_oversold:
                sl_price = price - sl_distance
                tp_price = price + tp_distance
                self.buy(sl=sl_price, tp=tp_price)

            # SHORT when RSI is overbought
            elif self.rsi[-1] > self.rsi_overbought:
                sl_price = price + sl_distance
                tp_price = price - tp_distance
                self.sell(sl=sl_price, tp=tp_price)

# Run backtest
bt = Backtest(data, FinalRSIStrategy, cash=10000000, commission=0.00045)

print("\n🌙 ===== FINAL RSI STRATEGY ===== 🌙")
print(f"RSI Period: {RSI_PERIOD}")
print(f"RSI Oversold: {RSI_OVERSOLD}, RSI Overbought: {RSI_OVERBOUGHT}")
print(f"Risk Multiplier: {RISK_MULTIPLIER}")
print(f"Min Stop Distance: {MIN_STOP_DISTANCE*100}%")

stats = bt.run()
print("\n📊 Backtest Results:")
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FINAL RSI STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(FinalRSIStrategy, 'Final_RSI_Strategy')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/Final_RSI_Strategy.csv")