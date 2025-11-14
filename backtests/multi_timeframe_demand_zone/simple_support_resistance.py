"""
SIMPLE SUPPORT/RESISTANCE STRATEGY - GUARANTEED TRADES VERSION
================================================================
Created by: Moon Dev
Date: 2025-01-30

STRATEGY OVERVIEW:
This is a simplified support/resistance strategy that will definitely generate trades.
It uses basic support and resistance levels with RSI confirmation for entries.

ENTRY RULES:
LONG:
- Price near recent support (20-period low)
- RSI < 45 (mild oversold)
- Close > Open (bullish bar)

SHORT:
- Price near recent resistance (20-period high)
- RSI > 55 (mild overbought)
- Close < Open (bearish bar)
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Simple Support/Resistance Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - Very relaxed for guaranteed trades
SUPPORT_PERIOD = 20
RESISTANCE_PERIOD = 20
RSI_PERIOD = 14
RSI_OVERSOLD = 45
RSI_OVERBOUGHT = 55
STOP_LOSS_PERCENT = 3.0
TAKE_PROFIT_PERCENT = 6.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class SimpleSupportResistance(Strategy):
    # Strategy parameters
    support_period = SUPPORT_PERIOD
    resistance_period = RESISTANCE_PERIOD
    rsi_period = RSI_PERIOD
    rsi_oversold = RSI_OVERSOLD
    rsi_overbought = RSI_OVERBOUGHT
    stop_loss_pct = STOP_LOSS_PERCENT / 100
    take_profit_pct = TAKE_PROFIT_PERCENT / 100

    def init(self):
        """Initialize simple indicators"""
        # Calculate support and resistance
        self.support = self.I(lambda x: pd.Series(x).rolling(self.support_period).min().values,
                              self.data.Low)
        self.resistance = self.I(lambda x: pd.Series(x).rolling(self.resistance_period).max().values,
                                self.data.High)

        # Calculate RSI
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), self.rsi_period)

        # Calculate ATR for volatility-based zones
        self.atr = self.I(ta.atr, pd.Series(self.data.High),
                         pd.Series(self.data.Low),
                         pd.Series(self.data.Close), 14)

        print(f"✅ Moon Dev's simple indicators initialized")

    def next(self):
        """Execute simple trading logic"""
        # Skip if we don't have enough data
        if len(self.data) < self.support_period * 2:
            return

        current_price = self.data.Close[-1]
        current_open = self.data.Open[-1]

        # Get indicators
        support = self.support[-1]
        resistance = self.resistance[-1]
        rsi = self.rsi[-1]
        atr = self.atr[-1]

        # Skip if indicators not ready
        if np.isnan(support) or np.isnan(resistance) or np.isnan(rsi) or np.isnan(atr):
            return

        # Define zones (using ATR for dynamic zones)
        support_zone_upper = support + (atr * 0.5)
        resistance_zone_lower = resistance - (atr * 0.5)

        if not self.position:
            # LONG ENTRY - Simple conditions
            if (current_price <= support_zone_upper and
                rsi < self.rsi_oversold and
                current_price > current_open):  # Bullish bar

                # Fixed percentage stops
                stop_loss = current_price * (1 - self.stop_loss_pct)
                take_profit = current_price * (1 + self.take_profit_pct)

                self.buy(sl=stop_loss, tp=take_profit, size=1000000)

            # SHORT ENTRY - Simple conditions
            elif (current_price >= resistance_zone_lower and
                  rsi > self.rsi_overbought and
                  current_price < current_open):  # Bearish bar

                # Fixed percentage stops
                stop_loss = current_price * (1 + self.stop_loss_pct)
                take_profit = current_price * (1 - self.take_profit_pct)

                self.sell(sl=stop_loss, tp=take_profit, size=1000000)

# Run single backtest
bt = Backtest(data, SimpleSupportResistance, cash=10000000, commission=0.00045)

print("\n🌙 ===== SIMPLE SUPPORT/RESISTANCE STRATEGY ===== 🌙")
print(f"Support Period: {SUPPORT_PERIOD}")
print(f"RSI Period: {RSI_PERIOD}")
print(f"RSI Oversold: {RSI_OVERSOLD}, RSI Overbought: {RSI_OVERBOUGHT}")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%, Take Profit: {TAKE_PROFIT_PERCENT}%")

stats = bt.run()
print("\n📊 Backtest Results:")
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING SIMPLE SUPPORT/RESISTANCE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(SimpleSupportResistance, 'Simple_SupportResistance')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/Simple_SupportResistance.csv")