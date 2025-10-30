"""
Moon Dev's Moving Average Crossover Strategy - ADX Enhanced Version
===================================================================

This strategy combines moving average crossovers with Average Directional Index (ADX)
to filter out choppy markets and only trade in strong trending conditions.

Strategy Logic:
- Long Entry: Fast MA crosses above Slow MA AND ADX > 25 (trending) AND +DI > -DI
- Long Exit: Fast MA crosses below Slow MA OR ADX < 20 (weakening trend)
- Short Entry: Fast MA crosses below Slow MA AND ADX > 25 AND -DI > +DI
- Short Exit: Fast MA crosses above Slow MA OR ADX < 20

Features:
- EMA crossover signals for trend following
- ADX filter to avoid choppy/ranging markets
- Directional Index confirmation for trend direction
- Compatible with 25+ data sources across crypto and stocks

Author: Moon Dev
Date: October 2025
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from datetime import datetime

print("🚀 Moon Dev's Moving Average Crossover + ADX Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
FAST_MA_PERIOD = 20
SLOW_MA_PERIOD = 50
ADX_PERIOD = 14
ADX_THRESHOLD = 25  # Minimum ADX for trend strength
ADX_EXIT_THRESHOLD = 20  # Exit when trend weakens
DI_DIFF_THRESHOLD = 5  # Minimum difference between DI+ and DI-
TAKE_PROFIT_PERCENT = 5.0
STOP_LOSS_PERCENT = 2.0
ENABLE_SHORT = True

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows - Moon Dev's ADX enhancement ready! 🌙")

class MACrossoverADX(Strategy):
    """Moon Dev's Moving Average Crossover + ADX Strategy"""

    # Strategy parameters
    fast_period = FAST_MA_PERIOD
    slow_period = SLOW_MA_PERIOD
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    adx_exit = ADX_EXIT_THRESHOLD
    di_diff_threshold = DI_DIFF_THRESHOLD
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    enable_short = ENABLE_SHORT

    def init(self):
        """Initialize indicators - Moon Dev's ADX-enhanced setup"""
        # Calculate EMAs using talib
        self.fast_ma = self.I(talib.EMA, self.data.Close, self.fast_period)
        self.slow_ma = self.I(talib.EMA, self.data.Close, self.slow_period)

        # Calculate ADX and Directional Indicators
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)

        # Calculate ATR for volatility-based stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)

        # Track crossovers
        self.ma_diff = self.fast_ma - self.slow_ma

        # Calculate MACD for additional trend confirmation
        macd, signal, hist = talib.MACD(self.data.Close.values, fastperiod=12, slowperiod=26, signalperiod=9)
        self.macd_hist = self.I(lambda: hist)

        # Calculate RSI for momentum confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, 14)

        print(f"🎯 Moon Dev initialized MA+ADX with Fast={self.fast_period}, Slow={self.slow_period}, ADX={self.adx_period}")

    def next(self):
        """Trading logic for each candle - Moon Dev's ADX-enhanced execution"""
        # Skip if we don't have enough data
        if len(self.data) < max(self.slow_period, self.adx_period) + 1:
            return

        # Current and previous MA difference
        current_diff = self.ma_diff[-1]
        prev_diff = self.ma_diff[-2]

        # Check for crossover signals
        bullish_cross = prev_diff <= 0 and current_diff > 0
        bearish_cross = prev_diff >= 0 and current_diff < 0

        current_price = self.data.Close[-1]
        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]
        di_difference = current_plus_di - current_minus_di
        current_rsi = self.rsi[-1]

        # Check trend strength
        trending_market = current_adx > self.adx_threshold
        bullish_trend = di_difference > self.di_diff_threshold
        bearish_trend = di_difference < -self.di_diff_threshold

        # Position management
        if not self.position:
            # Long entry with ADX confirmation
            if bullish_cross and trending_market and bullish_trend:
                # Additional confirmations for stronger signals
                macd_bullish = self.macd_hist[-1] > 0 and self.macd_hist[-1] > self.macd_hist[-2]
                rsi_ok = current_rsi > 40 and current_rsi < 70

                if macd_bullish or rsi_ok:
                    # Long entry
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)

                    # ATR-based stop adjustment
                    atr_stop = current_price - (2 * self.atr[-1])
                    sl_price = max(sl_price, atr_stop)

                    # Adjust position size based on ADX strength
                    if current_adx > 40:  # Very strong trend
                        size = 1.0  # Full position
                    elif current_adx > 30:  # Strong trend
                        size = 0.9
                    else:  # Moderate trend
                        size = 0.7

                    self.buy(sl=sl_price, tp=tp_price, size=size)

            # Short entry with ADX confirmation
            elif bearish_cross and self.enable_short and trending_market and bearish_trend:
                # Additional confirmations for stronger signals
                macd_bearish = self.macd_hist[-1] < 0 and self.macd_hist[-1] < self.macd_hist[-2]
                rsi_ok = current_rsi > 30 and current_rsi < 60

                if macd_bearish or rsi_ok:
                    # Short entry
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)

                    # ATR-based stop adjustment
                    atr_stop = current_price + (2 * self.atr[-1])
                    sl_price = min(sl_price, atr_stop)

                    # Adjust position size based on ADX strength
                    if current_adx > 40:  # Very strong trend
                        size = 1.0  # Full position
                    elif current_adx > 30:  # Strong trend
                        size = 0.9
                    else:  # Moderate trend
                        size = 0.7

                    self.sell(sl=sl_price, tp=tp_price, size=size)

        else:
            # Exit management with ADX weakening
            weakening_trend = current_adx < self.adx_exit

            if self.position.is_long:
                # Exit long on bearish cross OR weakening trend OR DI reversal
                di_reversal = current_minus_di > current_plus_di + self.di_diff_threshold
                if bearish_cross or weakening_trend or di_reversal:
                    self.position.close()

            elif self.position.is_short:
                # Exit short on bullish cross OR weakening trend OR DI reversal
                di_reversal = current_plus_di > current_minus_di + self.di_diff_threshold
                if bullish_cross or weakening_trend or di_reversal:
                    self.position.close()

# Run single backtest with default parameters
bt = Backtest(data, MACrossoverADX, cash=1000000, commission=0.00045)

print("\n🌙 ===== MOON DEV'S MA CROSSOVER + ADX - DEFAULT PARAMETERS ===== 🌙")
print(f"Fast MA: {FAST_MA_PERIOD}")
print(f"Slow MA: {SLOW_MA_PERIOD}")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Threshold: {ADX_THRESHOLD} (Entry), {ADX_EXIT_THRESHOLD} (Exit)")
print(f"DI Difference Threshold: {DI_DIFF_THRESHOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Short Trading: {'Enabled' if ENABLE_SHORT else 'Disabled'}")

stats_default = bt.run()
print("\n📊 Moon Dev's ADX-Enhanced Backtest Results:")
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("🚀 TESTING MOON DEV'S MA CROSSOVER + ADX ON ALL DATA SOURCES 🚀")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(MACrossoverADX, 'MACrossover_ADX')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MACrossover_ADX.csv")
        print("🌙 Moon Dev's MA Crossover + ADX strategy testing finished! 🌙")