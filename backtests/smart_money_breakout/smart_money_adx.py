"""
Smart Money Breakout Channels Strategy - ADX Enhanced
======================================================

Combines Smart Money channel breakouts with ADX (Average Directional Index)
for trend strength confirmation and improved breakout validation.

Enhancements:
- ADX trend strength filtering
- Directional movement (+DI/-DI) confirmation
- Trend persistence validation
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Smart Money Breakout + ADX Strategy Loading... 🌙")

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
ADX_PERIOD = 14                # ADX period
ADX_THRESHOLD = 25             # Minimum ADX for trend
DI_THRESHOLD = 5               # Minimum DI difference

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class SmartMoneyADX(Strategy):
    # Strategy parameters
    channel_lookback = CHANNEL_LOOKBACK
    volatility_threshold = VOLATILITY_THRESHOLD
    volume_lookback = VOLUME_LOOKBACK
    breakout_strength = BREAKOUT_STRENGTH
    atr_period = ATR_PERIOD
    atr_multiplier = ATR_MULTIPLIER
    take_profit_ratio = TAKE_PROFIT_RATIO
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    di_threshold = DI_THRESHOLD

    def init(self):
        # Price and volatility calculations
        close = self.data.Close
        high = self.data.High
        low = self.data.Low
        volume = self.data.Volume

        # ATR for position sizing and stops
        self.atr = self.I(talib.ATR, high, low, close, self.atr_period)

        # ADX and Directional Indicators
        self.adx = self.I(talib.ADX, high, low, close, self.adx_period)
        self.plus_di = self.I(talib.PLUS_DI, high, low, close, self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, high, low, close, self.adx_period)

        # ADX slope for trend acceleration
        self.adx_slope = self.I(lambda: pd.Series(self.adx).diff(3).values)

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

        # Trend strength indicator combining ADX and DI
        self.trend_strength = self.I(lambda: self.adx * np.sign(self.plus_di - self.minus_di))

    def evaluate_trend_quality(self):
        """Evaluate the quality of the current trend using ADX components"""
        if len(self.data) < self.adx_period:
            return 0

        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]
        adx_slope = self.adx_slope[-1] if self.adx_slope[-1] is not None else 0

        # Strong uptrend
        if (current_adx > self.adx_threshold and
            current_plus_di > current_minus_di + self.di_threshold and
            adx_slope > 0):
            return 2  # Very strong uptrend

        elif (current_adx > self.adx_threshold and
              current_plus_di > current_minus_di):
            return 1  # Moderate uptrend

        # Strong downtrend
        elif (current_adx > self.adx_threshold and
              current_minus_di > current_plus_di + self.di_threshold and
              adx_slope > 0):
            return -2  # Very strong downtrend

        elif (current_adx > self.adx_threshold and
              current_minus_di > current_plus_di):
            return -1  # Moderate downtrend

        return 0  # No clear trend or ranging market

    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.channel_lookback * 2, self.adx_period * 2):
            return

        # Current values
        current_close = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        current_open = self.data.Open[-1]

        # Channel values
        channel_high = self.channel_high[-1]
        channel_low = self.channel_low[-1]
        channel_width = channel_high - channel_low

        # Skip if channel is too narrow
        if channel_width < self.atr[-1] * 0.5:
            return

        # Evaluate trend quality
        trend_quality = self.evaluate_trend_quality()

        # ADX values
        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]

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

        # Position management
        if not self.position:
            # Long entry with ADX confirmation
            if bullish_breakout and volume_confirmation:
                # ADX conditions for long entry
                adx_long_signal = (
                    current_adx > self.adx_threshold and  # Trending market
                    current_plus_di > current_minus_di and  # Bullish direction
                    trend_quality >= 1  # At least moderate uptrend
                )

                if adx_long_signal and self.volume_delta[-1] > 0:
                    # Calculate stops with ADX adjustment
                    adx_adjustment = 1.0
                    if trend_quality == 2:  # Very strong trend
                        adx_adjustment = 0.8  # Tighter stop
                    elif current_adx < 30:  # Weak trend
                        adx_adjustment = 1.2  # Wider stop

                    stop_distance = self.atr[-1] * self.atr_multiplier * adx_adjustment
                    stop_price = current_close - stop_distance

                    # Dynamic take profit based on trend strength
                    tp_adjustment = 1.0
                    if trend_quality == 2:  # Very strong trend
                        tp_adjustment = 1.5  # Higher target

                    target_price = current_close + (stop_distance * self.take_profit_ratio * tp_adjustment)

                    # Position size based on trend strength
                    if trend_quality == 2:
                        position_size = 1200000  # Larger size for very strong trends
                    else:
                        position_size = 1000000

                    self.buy(size=position_size, sl=stop_price, tp=target_price)

            # Short entry with ADX confirmation
            elif bearish_breakout and volume_confirmation:
                # ADX conditions for short entry
                adx_short_signal = (
                    current_adx > self.adx_threshold and  # Trending market
                    current_minus_di > current_plus_di and  # Bearish direction
                    trend_quality <= -1  # At least moderate downtrend
                )

                if adx_short_signal and self.volume_delta[-1] < 0:
                    # Calculate stops with ADX adjustment
                    adx_adjustment = 1.0
                    if trend_quality == -2:  # Very strong downtrend
                        adx_adjustment = 0.8  # Tighter stop
                    elif current_adx < 30:  # Weak trend
                        adx_adjustment = 1.2  # Wider stop

                    stop_distance = self.atr[-1] * self.atr_multiplier * adx_adjustment
                    stop_price = current_close + stop_distance

                    # Dynamic take profit based on trend strength
                    tp_adjustment = 1.0
                    if trend_quality == -2:  # Very strong downtrend
                        tp_adjustment = 1.5  # Higher target

                    target_price = current_close - (stop_distance * self.take_profit_ratio * tp_adjustment)

                    # Position size based on trend strength
                    if trend_quality == -2:
                        position_size = 1200000  # Larger size for very strong trends
                    else:
                        position_size = 1000000

                    self.sell(size=position_size, sl=stop_price, tp=target_price)

        else:
            # Enhanced exit management with ADX
            if self.position.is_long:
                # Exit if trend weakens significantly
                trend_weakening = (
                    current_adx < 20 or  # Trend losing strength
                    current_minus_di > current_plus_di or  # Direction change
                    current_close < channel_high * 0.99  # Price rejection
                )
                if trend_weakening:
                    self.position.close()

            elif self.position.is_short:
                # Exit if trend weakens significantly
                trend_weakening = (
                    current_adx < 20 or  # Trend losing strength
                    current_plus_di > current_minus_di or  # Direction change
                    current_close > channel_low * 1.01  # Price rejection
                )
                if trend_weakening:
                    self.position.close()

# Run single backtest
bt = Backtest(data, SmartMoneyADX, cash=10000000, commission=0.00045)

print("\n🌙 ===== SMART MONEY BREAKOUT + ADX ===== 🌙")
print(f"Channel Lookback: {CHANNEL_LOOKBACK}")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Threshold: {ADX_THRESHOLD}")
print(f"DI Threshold: {DI_THRESHOLD}")

stats_default = bt.run()
print(stats_default)

# Optimization
print("\n🚀 Optimizing Smart Money + ADX Strategy...")
# Optimization removed

print("\n🏆 BEST PARAMETERS:")
print("\n✅ Smart Money + ADX Strategy Test Complete")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING SMART MONEY + ADX ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(SmartMoneyADX, 'smart_money_adx')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/smart_money_adx.csv")