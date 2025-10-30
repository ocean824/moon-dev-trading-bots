"""
Moon Dev's Moving Average Crossover Strategy - Base Version
============================================================

This strategy implements a classic moving average crossover system with
proper risk management and multi-data testing capability.

Strategy Logic:
- Long Entry: Fast MA crosses above Slow MA
- Long Exit: Fast MA crosses below Slow MA
- Short Entry: Fast MA crosses below Slow MA (if enabled)
- Short Exit: Fast MA crosses above Slow MA

Features:
- EMA crossover signals for trend following
- Dynamic position sizing based on volatility
- Stop-loss and take-profit management
- Compatible with 25+ data sources across crypto and stocks

Author: Moon Dev
Date: October 2025
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from datetime import datetime

print("🚀 Moon Dev's Moving Average Crossover Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
FAST_MA_PERIOD = 20
SLOW_MA_PERIOD = 50
TAKE_PROFIT_PERCENT = 4.0
STOP_LOSS_PERCENT = 2.0
ENABLE_SHORT = True  # Set to False for long-only strategy

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows - Moon Dev's ready to trade! 🌙")

class MACrossoverBase(Strategy):
    """Moon Dev's Moving Average Crossover Base Strategy"""

    # Strategy parameters
    fast_period = FAST_MA_PERIOD
    slow_period = SLOW_MA_PERIOD
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    enable_short = ENABLE_SHORT

    def init(self):
        """Initialize indicators - Moon Dev's setup"""
        # Calculate EMAs using talib
        self.fast_ma = self.I(talib.EMA, self.data.Close, self.fast_period)
        self.slow_ma = self.I(talib.EMA, self.data.Close, self.slow_period)

        # Calculate ATR for volatility-based stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)

        # Track crossovers
        self.ma_diff = self.fast_ma - self.slow_ma

        print(f"🎯 Moon Dev initialized MA Crossover with Fast={self.fast_period}, Slow={self.slow_period}")

    def next(self):
        """Trading logic for each candle - Moon Dev's execution"""
        # Skip if we don't have enough data
        if len(self.data) < self.slow_period + 1:
            return

        # Current and previous MA difference
        current_diff = self.ma_diff[-1]
        prev_diff = self.ma_diff[-2]

        # Check for crossover signals
        bullish_cross = prev_diff <= 0 and current_diff > 0
        bearish_cross = prev_diff >= 0 and current_diff < 0

        current_price = self.data.Close[-1]

        # Position management
        if not self.position:
            # Entry signals
            if bullish_cross:
                # Long entry
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)

                # ATR-based stop adjustment
                atr_stop = current_price - (2 * self.atr[-1])
                sl_price = max(sl_price, atr_stop)

                self.buy(sl=sl_price, tp=tp_price)

            elif bearish_cross and self.enable_short:
                # Short entry
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)

                # ATR-based stop adjustment
                atr_stop = current_price + (2 * self.atr[-1])
                sl_price = min(sl_price, atr_stop)

                self.sell(sl=sl_price, tp=tp_price)

        else:
            # Exit on opposite crossover
            if self.position.is_long and bearish_cross:
                self.position.close()
            elif self.position.is_short and bullish_cross:
                self.position.close()

# Run single backtest with default parameters
bt = Backtest(data, MACrossoverBase, cash=1000000, commission=0.00045)

print("\n🌙 ===== MOON DEV'S MA CROSSOVER - DEFAULT PARAMETERS ===== 🌙")
print(f"Fast MA: {FAST_MA_PERIOD}")
print(f"Slow MA: {SLOW_MA_PERIOD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Short Trading: {'Enabled' if ENABLE_SHORT else 'Disabled'}")

stats_default = bt.run()
print("\n📊 Moon Dev's Backtest Results:")
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("🚀 TESTING MOON DEV'S MA CROSSOVER ON ALL DATA SOURCES 🚀")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(MACrossoverBase, 'MACrossover_Base')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MACrossover_Base.csv")
        print("🌙 Moon Dev's MA Crossover Base strategy testing finished! 🌙")