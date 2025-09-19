"""
Smart Money Breakout Channels Strategy - MFI Enhanced
======================================================

Combines Smart Money channel breakouts with Money Flow Index (MFI) for
improved entry filtering and overbought/oversold conditions.

Enhancements:
- MFI divergence detection
- Overbought/Oversold filtering
- Volume-weighted breakout confirmation
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Smart Money Breakout + MFI Strategy Loading... 🌙")

# Data configuration for single test
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
CHANNEL_LOOKBACK = 20          # Period for channel detection
VOLATILITY_THRESHOLD = 0.02    # Threshold for consolidation detection
VOLUME_LOOKBACK = 20           # Period for volume analysis
BREAKOUT_STRENGTH = 0.6        # Strong close requirement
ATR_PERIOD = 14                # ATR for stop loss
ATR_MULTIPLIER = 2.0           # Stop loss distance
TAKE_PROFIT_RATIO = 2.0        # Risk/Reward ratio
MFI_PERIOD = 14                # Money Flow Index period
MFI_OVERBOUGHT = 70            # MFI overbought level
MFI_OVERSOLD = 30              # MFI oversold level

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class SmartMoneyMFI(Strategy):
    # Strategy parameters
    channel_lookback = CHANNEL_LOOKBACK
    volatility_threshold = VOLATILITY_THRESHOLD
    volume_lookback = VOLUME_LOOKBACK
    breakout_strength = BREAKOUT_STRENGTH
    atr_period = ATR_PERIOD
    atr_multiplier = ATR_MULTIPLIER
    take_profit_ratio = TAKE_PROFIT_RATIO
    mfi_period = MFI_PERIOD
    mfi_overbought = MFI_OVERBOUGHT
    mfi_oversold = MFI_OVERSOLD

    def init(self):
        # Price and volatility calculations
        close = self.data.Close
        high = self.data.High
        low = self.data.Low
        volume = self.data.Volume

        # ATR for position sizing and stops
        self.atr = self.I(talib.ATR, high, low, close, self.atr_period)

        # Money Flow Index
        self.mfi = self.I(talib.MFI, high, low, close, volume, self.mfi_period)

        # MFI signal line (smoothed MFI for divergence detection)
        self.mfi_signal = self.I(talib.SMA, self.mfi, 5)

        # Normalized volatility for channel detection
        typical_price = (high + low + close) / 3
        price_range = high - low
        self.volatility = self.I(lambda: price_range / typical_price)

        # Volatility bands
        volatility_sma = self.I(talib.SMA, self.volatility, self.channel_lookback)
        volatility_std = self.I(lambda: pd.Series(self.volatility).rolling(self.channel_lookback).std().values)

        self.upper_vol_band = self.I(lambda: volatility_sma + (volatility_std * 1.5))
        self.lower_vol_band = self.I(lambda: volatility_sma - (volatility_std * 1.5))

        # Channel boundaries
        self.channel_high = self.I(talib.MAX, high, self.channel_lookback)
        self.channel_low = self.I(talib.MIN, low, self.channel_lookback)

        # Volume analysis
        self.volume_sma = self.I(talib.SMA, volume, self.volume_lookback)
        self.volume_ratio = self.I(lambda: volume / self.volume_sma)

        # Up/Down volume
        close_diff = self.I(lambda: pd.Series(close).diff().values)
        self.up_volume = self.I(lambda: np.where(close_diff > 0, volume, 0))
        self.down_volume = self.I(lambda: np.where(close_diff < 0, volume, 0))

        # Volume delta
        self.volume_delta = self.I(lambda: self.up_volume - self.down_volume)

        # MFI divergence detection helper arrays
        self.price_highs = self.I(talib.MAX, high, 5)
        self.price_lows = self.I(talib.MIN, low, 5)

    def check_mfi_divergence(self):
        """Check for bullish or bearish MFI divergence"""
        if len(self.data) < 20:
            return 0, 0

        # Get recent price and MFI peaks/troughs
        lookback = 20
        prices = self.data.Close[-lookback:]
        mfi_values = self.mfi[-lookback:]

        # Find local highs and lows
        price_high_idx = np.argmax(prices)
        price_low_idx = np.argmin(prices)
        mfi_high_idx = np.argmax(mfi_values)
        mfi_low_idx = np.argmin(mfi_values)

        bullish_div = 0
        bearish_div = 0

        # Bullish divergence: price makes lower low, MFI makes higher low
        if price_low_idx > lookback // 2:  # Recent low
            prev_price_low = np.min(prices[:price_low_idx-2]) if price_low_idx > 2 else prices[0]
            prev_mfi_low = np.min(mfi_values[:price_low_idx-2]) if price_low_idx > 2 else mfi_values[0]

            if prices[price_low_idx] < prev_price_low and mfi_values[price_low_idx] > prev_mfi_low:
                bullish_div = 1

        # Bearish divergence: price makes higher high, MFI makes lower high
        if price_high_idx > lookback // 2:  # Recent high
            prev_price_high = np.max(prices[:price_high_idx-2]) if price_high_idx > 2 else prices[0]
            prev_mfi_high = np.max(mfi_values[:price_high_idx-2]) if price_high_idx > 2 else mfi_values[0]

            if prices[price_high_idx] > prev_price_high and mfi_values[price_high_idx] < prev_mfi_high:
                bearish_div = 1

        return bullish_div, bearish_div

    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.channel_lookback * 2, self.mfi_period * 2):
            return

        # Current values
        current_close = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        current_open = self.data.Open[-1]
        current_mfi = self.mfi[-1]

        # Channel values
        channel_high = self.channel_high[-1]
        channel_low = self.channel_low[-1]
        channel_width = channel_high - channel_low

        # Skip if channel is too narrow
        if channel_width < self.atr[-1] * 0.5:
            return

        # Check for MFI divergence
        bullish_div, bearish_div = self.check_mfi_divergence()

        # Breakout detection with strong close
        body_size = abs(current_close - current_open)

        # Bullish breakout
        bullish_breakout = current_close > channel_high
        if bullish_breakout and self.breakout_strength > 0:
            body_above = max(0, min(current_close, current_high) - channel_high)
            strong_close = (body_above / body_size) > self.breakout_strength if body_size > 0 else False
            bullish_breakout = bullish_breakout and strong_close

        # Bearish breakout
        bearish_breakout = current_close < channel_low
        if bearish_breakout and self.breakout_strength > 0:
            body_below = max(0, channel_low - max(current_close, current_low))
            strong_close = (body_below / body_size) > self.breakout_strength if body_size > 0 else False
            bearish_breakout = bearish_breakout and strong_close

        # Volume confirmation
        volume_confirmation = self.volume_ratio[-1] > 1.2

        # MFI conditions
        mfi_bullish = current_mfi < self.mfi_overbought and current_mfi > self.mfi_oversold
        mfi_oversold = current_mfi < self.mfi_oversold
        mfi_overbought = current_mfi > self.mfi_overbought

        # Position management
        if not self.position:
            # Long entry with MFI confirmation
            if bullish_breakout and volume_confirmation:
                # Enhanced entry conditions with MFI
                mfi_entry = (
                    (mfi_bullish or mfi_oversold) or  # Not overbought
                    bullish_div or                     # Bullish divergence
                    (current_mfi > self.mfi_signal[-1] and current_mfi < self.mfi_overbought)  # MFI trending up
                )

                if mfi_entry and self.volume_delta[-1] > 0:
                    # Calculate stops
                    stop_distance = self.atr[-1] * self.atr_multiplier
                    stop_price = current_close - stop_distance
                    target_price = current_close + (stop_distance * self.take_profit_ratio)

                    # Adjust position size based on MFI strength
                    if mfi_oversold or bullish_div:
                        position_size = 1200000  # Larger size for strong signals
                    else:
                        position_size = 1000000

                    self.buy(size=position_size, sl=stop_price, tp=target_price)

            # Short entry with MFI confirmation
            elif bearish_breakout and volume_confirmation:
                # Enhanced entry conditions with MFI
                mfi_entry = (
                    (mfi_bullish or mfi_overbought) or  # Not oversold
                    bearish_div or                       # Bearish divergence
                    (current_mfi < self.mfi_signal[-1] and current_mfi > self.mfi_oversold)  # MFI trending down
                )

                if mfi_entry and self.volume_delta[-1] < 0:
                    # Calculate stops
                    stop_distance = self.atr[-1] * self.atr_multiplier
                    stop_price = current_close + stop_distance
                    target_price = current_close - (stop_distance * self.take_profit_ratio)

                    # Adjust position size based on MFI strength
                    if mfi_overbought or bearish_div:
                        position_size = 1200000  # Larger size for strong signals
                    else:
                        position_size = 1000000

                    self.sell(size=position_size, sl=stop_price, tp=target_price)

        else:
            # Enhanced exit management with MFI
            if self.position.is_long:
                # Exit if MFI becomes extremely overbought or price breaks back below channel
                if current_mfi > 85 or current_close < channel_high * 0.99:
                    self.position.close()

            elif self.position.is_short:
                # Exit if MFI becomes extremely oversold or price breaks back above channel
                if current_mfi < 15 or current_close > channel_low * 1.01:
                    self.position.close()

# Run single backtest
bt = Backtest(data, SmartMoneyMFI, cash=10000000, commission=0.00045)

print("\n🌙 ===== SMART MONEY BREAKOUT + MFI ===== 🌙")
print(f"Channel Lookback: {CHANNEL_LOOKBACK}")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Overbought: {MFI_OVERBOUGHT}")
print(f"MFI Oversold: {MFI_OVERSOLD}")

stats_default = bt.run()
print(stats_default)

# Optimization
print("\n🚀 Optimizing Smart Money + MFI Strategy...")
# Optimization removed

print("\n🏆 BEST PARAMETERS:")
print("\n✅ Smart Money + MFI Strategy Test Complete")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING SMART MONEY + MFI ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(SmartMoneyMFI, 'smart_money_mfi')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/smart_money_mfi.csv")