"""
SIMPLE RSI STRATEGY - GUARANTEED TRADES
=========================================
Created by: Moon Dev
Date: 2025-01-30

STRATEGY OVERVIEW:
Ultra-simple RSI strategy that will definitely generate trades.
Uses only RSI for entry and exit signals.

ENTRY RULES:
LONG: RSI < 30
SHORT: RSI > 70
EXIT: Fixed stop loss and take profit percentages
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Simple RSI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
STOP_LOSS_PERCENT = 5.0
TAKE_PROFIT_PERCENT = 10.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class SimpleRSI(Strategy):
    # Strategy parameters
    rsi_period = RSI_PERIOD
    rsi_oversold = RSI_OVERSOLD
    rsi_overbought = RSI_OVERBOUGHT
    stop_loss_pct = STOP_LOSS_PERCENT / 100
    take_profit_pct = TAKE_PROFIT_PERCENT / 100

    def init(self):
        """Initialize RSI indicator"""
        # Calculate RSI
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), self.rsi_period)
        print(f"✅ Moon Dev's RSI indicator initialized")

    def next(self):
        """Execute simple RSI trading logic"""
        # Skip if not enough data
        if len(self.data) < self.rsi_period + 1:
            return

        current_price = self.data.Close[-1]
        rsi = self.rsi[-1]

        # Skip if RSI not ready
        if np.isnan(rsi):
            return

        if not self.position:
            # LONG ENTRY - RSI oversold
            if rsi < self.rsi_oversold:
                stop_loss = current_price * (1 - self.stop_loss_pct)
                take_profit = current_price * (1 + self.take_profit_pct)
                self.buy(sl=stop_loss, tp=take_profit, size=1000000)

            # SHORT ENTRY - RSI overbought
            elif rsi > self.rsi_overbought:
                stop_loss = current_price * (1 + self.stop_loss_pct)
                take_profit = current_price * (1 - self.take_profit_pct)
                self.sell(sl=stop_loss, tp=take_profit, size=1000000)

# Run single backtest
bt = Backtest(data, SimpleRSI, cash=10000000, commission=0.00045)

print("\n🌙 ===== SIMPLE RSI STRATEGY ===== 🌙")
print(f"RSI Period: {RSI_PERIOD}")
print(f"RSI Oversold: {RSI_OVERSOLD}, RSI Overbought: {RSI_OVERBOUGHT}")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%, Take Profit: {TAKE_PROFIT_PERCENT}%")

stats = bt.run()
print("\n📊 Backtest Results:")
print(stats)

# Show if any trades happened
if hasattr(stats, '_trades'):
    print(f"\n📈 Total trades executed: {len(stats._trades) if stats._trades is not None else 0}")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING SIMPLE RSI ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(SimpleRSI, 'Simple_RSI')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/Simple_RSI.csv")