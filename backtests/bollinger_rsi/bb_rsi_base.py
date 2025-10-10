"""
Bollinger Bands + RSI Double Strategy - Base Implementation
===========================================================

This strategy combines RSI and Bollinger Bands for confirmation signals:
- Entry: RSI crosses above oversold (50) AND price crosses above lower BB
- Exit: RSI crosses below overbought (50) AND price crosses below upper BB

Based on TradingView Pine Script parameters:
- RSI Period: 6 (very short)
- Bollinger Period: 200 (long-term)
- Bollinger Bands Standard Deviation: 2
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Bollinger + RSI Base Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters (from Pine Script)
RSI_PERIOD = 6  # Very short RSI period
BB_PERIOD = 200  # Long-term Bollinger Bands
BB_STD = 2.0  # Standard deviations
RSI_OVERSOLD = 50  # Using 50 as both oversold/overbought (middle line)
RSI_OVERBOUGHT = 50

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class BollingerRSIBase(Strategy):
    # Strategy parameters
    rsi_period = RSI_PERIOD
    bb_period = BB_PERIOD
    bb_std = BB_STD
    rsi_oversold = RSI_OVERSOLD
    rsi_overbought = RSI_OVERBOUGHT

    def init(self):
        """Initialize indicators using talib"""
        # Calculate RSI
        self.rsi = self.I(talib.RSI, self.data.Close, self.rsi_period)

        # Calculate Bollinger Bands
        bb_result = talib.BBANDS(
            self.data.Close.s,  # Use .s to get numpy array
            timeperiod=self.bb_period,
            nbdevup=self.bb_std,
            nbdevdn=self.bb_std,
            matype=0
        )
        self.bb_upper = self.I(lambda: bb_result[0])
        self.bb_middle = self.I(lambda: bb_result[1])
        self.bb_lower = self.I(lambda: bb_result[2])

    def next(self):
        """Trading logic - simplified Bollinger + RSI strategy"""
        if len(self.data) < max(self.rsi_period, self.bb_period) + 1:
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_rsi = self.rsi[-1]
        current_bb_upper = self.bb_upper[-1]
        current_bb_lower = self.bb_lower[-1]
        current_bb_middle = self.bb_middle[-1]

        # Skip if we don't have valid values
        if pd.isna(current_bb_upper) or pd.isna(current_bb_lower) or pd.isna(current_rsi):
            return

        # Position management - simplified without TP/SL for now
        if not self.position:
            # LONG ENTRY: Price near lower BB AND RSI oversold
            if current_price <= current_bb_lower * 1.02 and current_rsi <= 30:
                self.buy()

            # SHORT ENTRY: Price near upper BB AND RSI overbought
            elif current_price >= current_bb_upper * 0.98 and current_rsi >= 70:
                self.sell()

        else:
            # Exit conditions
            if self.position.is_long:
                # Exit long when price reaches middle band or RSI becomes overbought
                if current_price >= current_bb_middle or current_rsi >= 70:
                    self.position.close()

            elif self.position.is_short:
                # Exit short when price reaches middle band or RSI becomes oversold
                if current_price <= current_bb_middle or current_rsi <= 30:
                    self.position.close()


# Run single backtest (default behavior)
bt = Backtest(data, BollingerRSIBase, cash=1000000, commission=0.00045)

print("\n🌙 ===== BOLLINGER + RSI BASE STRATEGY ===== 🌙")
print(f"RSI Period: {RSI_PERIOD}")
print(f"Bollinger Period: {BB_PERIOD}")
print(f"Bollinger Std Dev: {BB_STD}")
print(f"RSI Oversold/Overbought: {RSI_OVERSOLD}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING BOLLINGER + RSI BASE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(BollingerRSIBase, 'BollingerRSIBase')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/BollingerRSIBase.csv")