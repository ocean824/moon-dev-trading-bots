"""
Moon Dev's Moving Average Crossover Strategy - MFI Enhanced Version
===================================================================

This strategy combines moving average crossovers with Money Flow Index (MFI)
for improved entry confirmation and overbought/oversold filtering.

Strategy Logic:
- Long Entry: Fast MA crosses above Slow MA AND MFI < 70 (not overbought)
- Long Exit: Fast MA crosses below Slow MA OR MFI > 80
- Short Entry: Fast MA crosses below Slow MA AND MFI > 30 (not oversold)
- Short Exit: Fast MA crosses above Slow MA OR MFI < 20

Features:
- EMA crossover signals for trend following
- MFI confirmation to avoid overbought/oversold entries
- Volume-weighted momentum analysis
- Compatible with 25+ data sources across crypto and stocks

Author: Moon Dev
Date: October 2025
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from datetime import datetime

print("🚀 Moon Dev's Moving Average Crossover + MFI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
FAST_MA_PERIOD = 20
SLOW_MA_PERIOD = 50
MFI_PERIOD = 14
MFI_OVERBOUGHT = 70
MFI_OVERSOLD = 30
MFI_EXIT_OVERBOUGHT = 80
MFI_EXIT_OVERSOLD = 20
TAKE_PROFIT_PERCENT = 5.0
STOP_LOSS_PERCENT = 2.5
ENABLE_SHORT = True

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows - Moon Dev's MFI enhancement ready! 🌙")

class MACrossoverMFI(Strategy):
    """Moon Dev's Moving Average Crossover + MFI Strategy"""

    # Strategy parameters
    fast_period = FAST_MA_PERIOD
    slow_period = SLOW_MA_PERIOD
    mfi_period = MFI_PERIOD
    mfi_overbought = MFI_OVERBOUGHT
    mfi_oversold = MFI_OVERSOLD
    mfi_exit_ob = MFI_EXIT_OVERBOUGHT
    mfi_exit_os = MFI_EXIT_OVERSOLD
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    enable_short = ENABLE_SHORT

    def init(self):
        """Initialize indicators - Moon Dev's enhanced setup"""
        # Calculate EMAs using talib
        self.fast_ma = self.I(talib.EMA, self.data.Close, self.fast_period)
        self.slow_ma = self.I(talib.EMA, self.data.Close, self.slow_period)

        # Calculate MFI for volume-weighted momentum
        self.mfi = self.I(talib.MFI, self.data.High, self.data.Low,
                          self.data.Close, self.data.Volume, self.mfi_period)

        # Calculate ATR for volatility-based stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)

        # Track crossovers
        self.ma_diff = self.fast_ma - self.slow_ma

        # Calculate RSI for additional confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, 14)

        print(f"🎯 Moon Dev initialized MA+MFI with Fast={self.fast_period}, Slow={self.slow_period}, MFI={self.mfi_period}")

    def next(self):
        """Trading logic for each candle - Moon Dev's MFI-enhanced execution"""
        # Skip if we don't have enough data
        if len(self.data) < max(self.slow_period, self.mfi_period) + 1:
            return

        # Current and previous MA difference
        current_diff = self.ma_diff[-1]
        prev_diff = self.ma_diff[-2]

        # Check for crossover signals
        bullish_cross = prev_diff <= 0 and current_diff > 0
        bearish_cross = prev_diff >= 0 and current_diff < 0

        current_price = self.data.Close[-1]
        current_mfi = self.mfi[-1]
        current_rsi = self.rsi[-1]

        # Position management
        if not self.position:
            # Long entry with MFI confirmation
            if bullish_cross and current_mfi < self.mfi_overbought:
                # Additional RSI confirmation for stronger signals
                if current_rsi > 30 and current_rsi < 70:
                    # Long entry
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)

                    # ATR-based stop adjustment
                    atr_stop = current_price - (2 * self.atr[-1])
                    sl_price = max(sl_price, atr_stop)

                    # Adjust position size based on MFI strength
                    if current_mfi < 40:  # Strong momentum opportunity
                        size = 1.0  # Full position
                    else:
                        size = 0.8  # Reduced position

                    self.buy(sl=sl_price, tp=tp_price, size=size)

            # Short entry with MFI confirmation
            elif bearish_cross and self.enable_short and current_mfi > self.mfi_oversold:
                # Additional RSI confirmation for stronger signals
                if current_rsi > 30 and current_rsi < 70:
                    # Short entry
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)

                    # ATR-based stop adjustment
                    atr_stop = current_price + (2 * self.atr[-1])
                    sl_price = min(sl_price, atr_stop)

                    # Adjust position size based on MFI strength
                    if current_mfi > 60:  # Strong momentum opportunity
                        size = 1.0  # Full position
                    else:
                        size = 0.8  # Reduced position

                    self.sell(sl=sl_price, tp=tp_price, size=size)

        else:
            # Exit management with MFI extreme levels
            if self.position.is_long:
                # Exit long on bearish cross OR extreme overbought MFI
                if bearish_cross or current_mfi > self.mfi_exit_ob:
                    self.position.close()

            elif self.position.is_short:
                # Exit short on bullish cross OR extreme oversold MFI
                if bullish_cross or current_mfi < self.mfi_exit_os:
                    self.position.close()

# Run single backtest with default parameters
bt = Backtest(data, MACrossoverMFI, cash=1000000, commission=0.00045)

print("\n🌙 ===== MOON DEV'S MA CROSSOVER + MFI - DEFAULT PARAMETERS ===== 🌙")
print(f"Fast MA: {FAST_MA_PERIOD}")
print(f"Slow MA: {SLOW_MA_PERIOD}")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Overbought: {MFI_OVERBOUGHT}, Exit: {MFI_EXIT_OVERBOUGHT}")
print(f"MFI Oversold: {MFI_OVERSOLD}, Exit: {MFI_EXIT_OVERSOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Short Trading: {'Enabled' if ENABLE_SHORT else 'Disabled'}")

stats_default = bt.run()
print("\n📊 Moon Dev's MFI-Enhanced Backtest Results:")
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("🚀 TESTING MOON DEV'S MA CROSSOVER + MFI ON ALL DATA SOURCES 🚀")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(MACrossoverMFI, 'MACrossover_MFI')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MACrossover_MFI.csv")
        print("🌙 Moon Dev's MA Crossover + MFI strategy testing finished! 🌙")