"""
WORKING SUPPORT/RESISTANCE STRATEGY - NO CANDLE PATTERNS
==========================================================
Created by: Moon Dev
Date: 2025-01-30

STRATEGY OVERVIEW:
This strategy uses support/resistance with RSI only, avoiding candle patterns
since the data appears to have issues with Open values.

ENTRY RULES:
LONG:
- Price near support (within 1% above support)
- RSI < 40

SHORT:
- Price near resistance (within 1% below resistance)
- RSI > 60
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Working Support/Resistance Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
SUPPORT_PERIOD = 20
RESISTANCE_PERIOD = 20
RSI_PERIOD = 14
RSI_OVERSOLD = 40
RSI_OVERBOUGHT = 60
ZONE_PERCENT = 1.0  # 1% zone around support/resistance
STOP_LOSS_PERCENT = 2.0
TAKE_PROFIT_PERCENT = 4.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class WorkingSupportResistance(Strategy):
    # Strategy parameters
    support_period = SUPPORT_PERIOD
    resistance_period = RESISTANCE_PERIOD
    rsi_period = RSI_PERIOD
    rsi_oversold = RSI_OVERSOLD
    rsi_overbought = RSI_OVERBOUGHT
    zone_pct = ZONE_PERCENT / 100
    stop_loss_pct = STOP_LOSS_PERCENT / 100
    take_profit_pct = TAKE_PROFIT_PERCENT / 100

    def init(self):
        """Initialize indicators"""
        # Support and resistance levels
        self.support = self.I(lambda x: pd.Series(x).rolling(self.support_period).min().values,
                              self.data.Low)
        self.resistance = self.I(lambda x: pd.Series(x).rolling(self.resistance_period).max().values,
                                self.data.High)

        # RSI for momentum
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), self.rsi_period)

        print(f"✅ Moon Dev's working indicators initialized")

    def next(self):
        """Execute trading logic without candle patterns"""
        # Skip if not enough data
        if len(self.data) < self.support_period * 2:
            return

        current_price = self.data.Close[-1]

        # Get indicators
        support = self.support[-1]
        resistance = self.resistance[-1]
        rsi = self.rsi[-1]

        # Skip if indicators not ready
        if np.isnan(support) or np.isnan(resistance) or np.isnan(rsi):
            return

        if not self.position:
            # LONG ENTRY - Simple conditions without candle patterns
            # Price within 1% above support AND RSI oversold
            if (support <= current_price <= support * (1 + self.zone_pct) and
                rsi < self.rsi_oversold):

                stop_loss = current_price * (1 - self.stop_loss_pct)
                take_profit = current_price * (1 + self.take_profit_pct)
                self.buy(sl=stop_loss, tp=take_profit, size=1000000)

            # SHORT ENTRY - Simple conditions without candle patterns
            # Price within 1% below resistance AND RSI overbought
            elif (resistance * (1 - self.zone_pct) <= current_price <= resistance and
                  rsi > self.rsi_overbought):

                stop_loss = current_price * (1 + self.stop_loss_pct)
                take_profit = current_price * (1 - self.take_profit_pct)
                self.sell(sl=stop_loss, tp=take_profit, size=1000000)

# Run single backtest
bt = Backtest(data, WorkingSupportResistance, cash=10000000, commission=0.00045)

print("\n🌙 ===== WORKING SUPPORT/RESISTANCE STRATEGY ===== 🌙")
print(f"Support/Resistance Period: {SUPPORT_PERIOD}")
print(f"RSI Period: {RSI_PERIOD}")
print(f"RSI Oversold: {RSI_OVERSOLD}, RSI Overbought: {RSI_OVERBOUGHT}")
print(f"Zone: {ZONE_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%, Take Profit: {TAKE_PROFIT_PERCENT}%")

stats = bt.run()
print("\n📊 Backtest Results:")
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING WORKING SUPPORT/RESISTANCE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(WorkingSupportResistance, 'Working_SupportResistance')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/Working_SupportResistance.csv")