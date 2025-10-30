"""
Moon Dev's Moving Average Crossover Strategy - Kalman Filter Enhanced Version
=============================================================================

This strategy combines moving average crossovers with Kalman Filter smoothing
to reduce noise and provide cleaner signals with less whipsaws.

Strategy Logic:
- Long Entry: Kalman-filtered Fast MA crosses above Kalman-filtered Slow MA
- Long Exit: Kalman-filtered Fast MA crosses below Kalman-filtered Slow MA
- Short Entry: Kalman-filtered Fast MA crosses below Kalman-filtered Slow MA
- Short Exit: Kalman-filtered Fast MA crosses above Kalman-filtered Slow MA

Features:
- Kalman Filter for noise reduction and signal smoothing
- Adaptive filtering based on market volatility
- Reduced false signals and whipsaws
- Compatible with 25+ data sources across crypto and stocks

Author: Moon Dev
Date: October 2025
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from datetime import datetime

print("🚀 Moon Dev's Moving Average Crossover + Kalman Filter Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
FAST_MA_PERIOD = 20
SLOW_MA_PERIOD = 50
KALMAN_GAIN = 0.01  # Higher = more responsive, Lower = more smooth
KALMAN_COVARIANCE = 0.1
VOLATILITY_LOOKBACK = 20
TAKE_PROFIT_PERCENT = 4.5
STOP_LOSS_PERCENT = 2.0
ENABLE_SHORT = True

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows - Moon Dev's Kalman enhancement ready! 🌙")


def kalman_filter(prices, kalman_gain=0.01, initial_covariance=0.1):
    """
    Moon Dev's Kalman Filter implementation for price smoothing
    """
    n = len(prices)
    filtered_values = np.zeros(n)

    # Initialize
    filtered_values[0] = prices[0]
    error_covariance = initial_covariance

    for i in range(1, n):
        # Prediction
        predicted_value = filtered_values[i-1]
        predicted_error_covariance = error_covariance + kalman_gain

        # Update
        kalman_gain_current = predicted_error_covariance / (predicted_error_covariance + 1)
        filtered_values[i] = predicted_value + kalman_gain_current * (prices[i] - predicted_value)
        error_covariance = (1 - kalman_gain_current) * predicted_error_covariance

    return filtered_values


def adaptive_kalman_filter(prices, volatility, base_gain=0.01, base_covariance=0.1):
    """
    Moon Dev's Adaptive Kalman Filter that adjusts based on volatility
    """
    n = len(prices)
    filtered_values = np.zeros(n)

    # Normalize volatility for adaptive gain
    vol_normalized = volatility / np.nanmean(volatility)

    # Initialize
    filtered_values[0] = prices[0]
    error_covariance = base_covariance

    for i in range(1, n):
        # Adaptive gain based on volatility
        adaptive_gain = base_gain * vol_normalized[i] if not np.isnan(vol_normalized[i]) else base_gain

        # Prediction
        predicted_value = filtered_values[i-1]
        predicted_error_covariance = error_covariance + adaptive_gain

        # Update
        kalman_gain_current = predicted_error_covariance / (predicted_error_covariance + 1)
        filtered_values[i] = predicted_value + kalman_gain_current * (prices[i] - predicted_value)
        error_covariance = (1 - kalman_gain_current) * predicted_error_covariance

    return filtered_values


class MACrossoverKalman(Strategy):
    """Moon Dev's Moving Average Crossover + Kalman Filter Strategy"""

    # Strategy parameters
    fast_period = FAST_MA_PERIOD
    slow_period = SLOW_MA_PERIOD
    kalman_gain = KALMAN_GAIN
    kalman_covariance = KALMAN_COVARIANCE
    volatility_lookback = VOLATILITY_LOOKBACK
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    enable_short = ENABLE_SHORT

    def init(self):
        """Initialize indicators - Moon Dev's Kalman-enhanced setup"""
        # Calculate base EMAs
        fast_ma = talib.EMA(self.data.Close.values, self.fast_period)
        slow_ma = talib.EMA(self.data.Close.values, self.slow_period)

        # Calculate volatility for adaptive Kalman filtering
        volatility = talib.ATR(self.data.High.values, self.data.Low.values,
                               self.data.Close.values, self.volatility_lookback)

        # Apply Kalman filtering to the moving averages
        fast_ma_kalman = adaptive_kalman_filter(fast_ma, volatility,
                                                self.kalman_gain, self.kalman_covariance)
        slow_ma_kalman = adaptive_kalman_filter(slow_ma, volatility,
                                                self.kalman_gain * 0.5, self.kalman_covariance)

        # Also apply Kalman to price for clean price action
        price_kalman = adaptive_kalman_filter(self.data.Close.values, volatility,
                                              self.kalman_gain * 2, self.kalman_covariance)

        # Store as indicators
        self.fast_ma_kalman = self.I(lambda: fast_ma_kalman)
        self.slow_ma_kalman = self.I(lambda: slow_ma_kalman)
        self.price_kalman = self.I(lambda: price_kalman)

        # Calculate ATR for stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)

        # Track crossovers
        self.ma_diff_kalman = self.fast_ma_kalman - self.slow_ma_kalman

        # Calculate momentum indicators for confirmation
        self.rsi = self.I(talib.RSI, self.data.Close, 14)

        # Kalman-filtered RSI for smoother momentum reading
        rsi_kalman = kalman_filter(talib.RSI(self.data.Close.values, 14),
                                   self.kalman_gain, self.kalman_covariance)
        self.rsi_kalman = self.I(lambda: rsi_kalman)

        # Calculate MACD for trend confirmation
        macd, signal, hist = talib.MACD(self.data.Close.values, fastperiod=12, slowperiod=26, signalperiod=9)
        self.macd_hist = self.I(lambda: hist)

        # Kalman-filtered MACD histogram
        macd_hist_kalman = kalman_filter(hist, self.kalman_gain * 0.5, self.kalman_covariance)
        self.macd_hist_kalman = self.I(lambda: macd_hist_kalman)

        print(f"🎯 Moon Dev initialized MA+Kalman with Fast={self.fast_period}, Slow={self.slow_period}, Gain={self.kalman_gain}")

    def next(self):
        """Trading logic for each candle - Moon Dev's Kalman-enhanced execution"""
        # Skip if we don't have enough data
        if len(self.data) < self.slow_period + 1:
            return

        # Current and previous MA difference (Kalman filtered)
        current_diff = self.ma_diff_kalman[-1]
        prev_diff = self.ma_diff_kalman[-2]

        # Check for crossover signals with Kalman-filtered MAs
        bullish_cross = prev_diff <= 0 and current_diff > 0
        bearish_cross = prev_diff >= 0 and current_diff < 0

        current_price = self.data.Close[-1]
        kalman_price = self.price_kalman[-1]
        current_rsi = self.rsi_kalman[-1]

        # Calculate trend strength from Kalman-filtered MAs
        ma_spread = abs(current_diff)
        avg_spread = np.mean(np.abs(self.ma_diff_kalman[-20:]))
        strong_trend = ma_spread > avg_spread * 1.2

        # Position management
        if not self.position:
            # Long entry with Kalman confirmation
            if bullish_cross:
                # Additional confirmations using Kalman-filtered indicators
                macd_bullish = self.macd_hist_kalman[-1] > 0 and self.macd_hist_kalman[-1] > self.macd_hist_kalman[-2]
                rsi_ok = current_rsi > 35 and current_rsi < 75
                price_above_slow = kalman_price > self.slow_ma_kalman[-1]

                if (macd_bullish or rsi_ok) and price_above_slow:
                    # Long entry
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)

                    # ATR-based stop adjustment
                    atr_stop = current_price - (2 * self.atr[-1])
                    sl_price = max(sl_price, atr_stop)

                    # Adjust position size based on signal strength
                    if strong_trend and macd_bullish:
                        size = 1.0  # Full position for strong signals
                    elif strong_trend or macd_bullish:
                        size = 0.8  # Reduced for medium signals
                    else:
                        size = 0.6  # Conservative for weak signals

                    self.buy(sl=sl_price, tp=tp_price, size=size)

            # Short entry with Kalman confirmation
            elif bearish_cross and self.enable_short:
                # Additional confirmations using Kalman-filtered indicators
                macd_bearish = self.macd_hist_kalman[-1] < 0 and self.macd_hist_kalman[-1] < self.macd_hist_kalman[-2]
                rsi_ok = current_rsi > 25 and current_rsi < 65
                price_below_slow = kalman_price < self.slow_ma_kalman[-1]

                if (macd_bearish or rsi_ok) and price_below_slow:
                    # Short entry
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)

                    # ATR-based stop adjustment
                    atr_stop = current_price + (2 * self.atr[-1])
                    sl_price = min(sl_price, atr_stop)

                    # Adjust position size based on signal strength
                    if strong_trend and macd_bearish:
                        size = 1.0  # Full position for strong signals
                    elif strong_trend or macd_bearish:
                        size = 0.8  # Reduced for medium signals
                    else:
                        size = 0.6  # Conservative for weak signals

                    self.sell(sl=sl_price, tp=tp_price, size=size)

        else:
            # Exit management with Kalman-filtered signals
            if self.position.is_long:
                # Exit long on bearish cross OR momentum reversal
                momentum_reversal = self.macd_hist_kalman[-1] < 0 and self.rsi_kalman[-1] < 45
                if bearish_cross or momentum_reversal:
                    self.position.close()

            elif self.position.is_short:
                # Exit short on bullish cross OR momentum reversal
                momentum_reversal = self.macd_hist_kalman[-1] > 0 and self.rsi_kalman[-1] > 55
                if bullish_cross or momentum_reversal:
                    self.position.close()

# Run single backtest with default parameters
bt = Backtest(data, MACrossoverKalman, cash=1000000, commission=0.00045)

print("\n🌙 ===== MOON DEV'S MA CROSSOVER + KALMAN - DEFAULT PARAMETERS ===== 🌙")
print(f"Fast MA: {FAST_MA_PERIOD}")
print(f"Slow MA: {SLOW_MA_PERIOD}")
print(f"Kalman Gain: {KALMAN_GAIN}")
print(f"Kalman Covariance: {KALMAN_COVARIANCE}")
print(f"Volatility Lookback: {VOLATILITY_LOOKBACK}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Short Trading: {'Enabled' if ENABLE_SHORT else 'Disabled'}")

stats_default = bt.run()
print("\n📊 Moon Dev's Kalman-Enhanced Backtest Results:")
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("🚀 TESTING MOON DEV'S MA CROSSOVER + KALMAN ON ALL DATA SOURCES 🚀")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(MACrossoverKalman, 'MACrossover_Kalman')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MACrossover_Kalman.csv")
        print("🌙 Moon Dev's MA Crossover + Kalman strategy testing finished! 🌙")