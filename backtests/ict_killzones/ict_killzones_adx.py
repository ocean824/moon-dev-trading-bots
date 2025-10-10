"""
ICT Killzones & Pivots Strategy - ADX Enhanced Version
======================================================
Combines ICT killzone concepts with ADX (Average Directional Index)
for trend strength confirmation and better directional bias.
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from datetime import time

print("🚀 Moon Dev's ICT Killzones + ADX Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
TAKE_PROFIT_PERCENT = 3.2
STOP_LOSS_PERCENT = 1.6
SESSION_BREAKOUT_THRESHOLD = 0.35
PIVOT_RANGE_PERCENT = 0.25
ADX_PERIOD = 14
ADX_TREND_THRESHOLD = 25
ADX_STRONG_TREND = 40
DI_SIGNAL_DIFF = 5  # Minimum difference between +DI and -DI

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ICTKillzonesADX(Strategy):
    # Strategy parameters
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    session_threshold = SESSION_BREAKOUT_THRESHOLD / 100
    pivot_range = PIVOT_RANGE_PERCENT / 100
    adx_period = ADX_PERIOD
    adx_threshold = ADX_TREND_THRESHOLD
    adx_strong = ADX_STRONG_TREND
    di_diff = DI_SIGNAL_DIFF

    def init(self):
        """Initialize indicators and session tracking"""
        # Calculate pivot points (standard pivots)
        high = self.data.High
        low = self.data.Low
        close = self.data.Close
        volume = self.data.Volume

        # Daily pivot calculations
        self.pivot_point = self.I(lambda: (high + low + close) / 3)
        self.resistance1 = self.I(lambda: 2 * self.pivot_point - low)
        self.resistance2 = self.I(lambda: self.pivot_point + (high - low))
        self.resistance3 = self.I(lambda: high + 2 * (self.pivot_point - low))
        self.support1 = self.I(lambda: 2 * self.pivot_point - high)
        self.support2 = self.I(lambda: self.pivot_point - (high - low))
        self.support3 = self.I(lambda: low - 2 * (high - self.pivot_point))

        # ADX and Directional Indicators
        self.adx = self.I(talib.ADX, high, low, close, self.adx_period)
        self.plus_di = self.I(talib.PLUS_DI, high, low, close, self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, high, low, close, self.adx_period)

        # Additional trend indicators
        self.ema_fast = self.I(talib.EMA, close, 12)
        self.ema_slow = self.I(talib.EMA, close, 26)

        # Volume indicators
        self.volume_sma = self.I(talib.SMA, volume, 20)
        self.cmf = self.I(talib.ADOSC, high, low, close, volume, 3, 10)  # Chaikin Money Flow proxy

        # ATR for dynamic stops
        self.atr = self.I(talib.ATR, high, low, close, 14)

        # Momentum indicator
        self.macd = self.I(lambda: talib.MACD(close, 12, 26, 9)[0])
        self.macd_signal = self.I(lambda: talib.MACD(close, 12, 26, 9)[1])

        # Track session highs and lows
        self.session_highs = []
        self.session_lows = []
        self.current_session = None
        self.session_high = 0
        self.session_low = float('inf')
        self.session_adx_sum = 0
        self.session_count = 0

    def get_killzone(self, current_time):
        """Determine which killzone we're in based on time"""
        hour = current_time.hour

        # Killzone definitions (simplified for hourly data)
        if 0 <= hour < 4:
            return 'ASIA'
        elif 7 <= hour < 10:
            return 'LONDON'
        elif 12 <= hour < 15:
            return 'NY_AM'
        elif 15 <= hour < 17:
            return 'NY_LUNCH'
        elif 17 <= hour < 20:
            return 'NY_PM'
        else:
            return None

    def get_trend_strength(self, adx_val, plus_di_val, minus_di_val):
        """Categorize trend strength based on ADX and DI values"""
        di_diff = plus_di_val - minus_di_val

        if adx_val >= self.adx_strong:
            if di_diff > self.di_diff:
                return 'STRONG_UP'
            elif di_diff < -self.di_diff:
                return 'STRONG_DOWN'
            else:
                return 'STRONG_NEUTRAL'
        elif adx_val >= self.adx_threshold:
            if di_diff > self.di_diff:
                return 'MODERATE_UP'
            elif di_diff < -self.di_diff:
                return 'MODERATE_DOWN'
            else:
                return 'MODERATE_NEUTRAL'
        else:
            return 'WEAK'

    def next(self):
        """Trading logic based on ICT concepts with ADX enhancement"""
        # Get current time and killzone
        current_time = self.data.index[-1]
        killzone = self.get_killzone(current_time)

        # Track session highs and lows
        if killzone != self.current_session:
            # New session started
            if self.current_session is not None:
                # Store previous session's high/low
                self.session_highs.append(self.session_high)
                self.session_lows.append(self.session_low)

            # Reset for new session
            self.current_session = killzone
            self.session_high = self.data.High[-1]
            self.session_low = self.data.Low[-1]
            self.session_adx_sum = 0
            self.session_count = 0
        else:
            # Update current session high/low
            if killzone is not None:
                self.session_high = max(self.session_high, self.data.High[-1])
                self.session_low = min(self.session_low, self.data.Low[-1])
                if len(self.adx) >= self.adx_period:
                    self.session_adx_sum += self.adx[-1]
                    self.session_count += 1

        # Skip if not in a killzone
        if killzone is None:
            return

        # Get current price and indicators
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]

        # Check if we have enough data
        if len(self.adx) < self.adx_period or len(self.atr) < 14:
            return

        adx_value = self.adx[-1]
        plus_di_value = self.plus_di[-1]
        minus_di_value = self.minus_di[-1]
        atr_value = self.atr[-1]
        volume_avg = self.volume_sma[-1]
        ema_fast_val = self.ema_fast[-1]
        ema_slow_val = self.ema_slow[-1]
        cmf_value = self.cmf[-1] if len(self.cmf) > 0 else 0
        macd_val = self.macd[-1] if len(self.macd) > 0 else 0
        macd_sig = self.macd_signal[-1] if len(self.macd_signal) > 0 else 0

        pivot = self.pivot_point[-1]
        r1 = self.resistance1[-1]
        r2 = self.resistance2[-1]
        r3 = self.resistance3[-1]
        s1 = self.support1[-1]
        s2 = self.support2[-1]
        s3 = self.support3[-1]

        # Get trend strength
        trend = self.get_trend_strength(adx_value, plus_di_value, minus_di_value)

        # Calculate session average ADX if available
        session_avg_adx = self.session_adx_sum / self.session_count if self.session_count > 0 else adx_value

        # Entry logic with ADX confirmation
        if not self.position:
            # Determine market conditions
            above_pivot = current_price > pivot
            ema_bullish = ema_fast_val > ema_slow_val
            ema_bearish = ema_fast_val < ema_slow_val
            macd_bullish = macd_val > macd_sig
            macd_bearish = macd_val < macd_sig

            # Long conditions
            long_signal = False

            # 1. Strong trend breakout with ADX confirmation
            if trend in ['STRONG_UP', 'MODERATE_UP']:
                if self.session_high > 0 and current_price > self.session_high * (1 + self.session_threshold):
                    if current_volume > volume_avg * 1.2 and ema_bullish:
                        long_signal = True

            # 2. Trend continuation at support with ADX
            elif trend == 'MODERATE_UP' and killzone in ['LONDON', 'NY_AM']:
                if abs(current_price - s1) / s1 < self.pivot_range:
                    if plus_di_value > minus_di_value + self.di_diff:
                        if macd_bullish and cmf_value > 0:
                            long_signal = True

            # 3. Asia range breakout with trend strength
            elif killzone == 'LONDON' and len(self.session_highs) > 0:
                asia_high = self.session_highs[-1] if self.session_highs else self.session_high
                if current_price > asia_high:
                    if adx_value > self.adx_threshold and plus_di_value > minus_di_value:
                        if adx_value > session_avg_adx:  # ADX expanding
                            long_signal = True

            # 4. Weak trend reversal pattern
            elif trend == 'WEAK' and killzone == 'NY_AM':
                # Look for trend emergence from consolidation
                if adx_value > self.adx[-2] and plus_di_value > minus_di_value:
                    if current_price > pivot and ema_bullish:
                        if current_volume > volume_avg * 1.3:
                            long_signal = True

            # 5. Strong momentum continuation
            elif trend == 'STRONG_UP' and killzone in ['NY_AM', 'LONDON']:
                if current_price > r1 and adx_value > self.adx[-2]:
                    if cmf_value > 0 and macd_bullish:
                        long_signal = True

            # Short conditions
            short_signal = False

            # 1. Strong downtrend breakdown with ADX confirmation
            if trend in ['STRONG_DOWN', 'MODERATE_DOWN']:
                if self.session_low < float('inf') and current_price < self.session_low * (1 - self.session_threshold):
                    if current_volume > volume_avg * 1.2 and ema_bearish:
                        short_signal = True

            # 2. Trend continuation at resistance with ADX
            elif trend == 'MODERATE_DOWN' and killzone in ['LONDON', 'NY_AM']:
                if abs(current_price - r1) / r1 < self.pivot_range:
                    if minus_di_value > plus_di_value + self.di_diff:
                        if macd_bearish and cmf_value < 0:
                            short_signal = True

            # 3. NY PM exhaustion with ADX divergence
            elif killzone == 'NY_PM':
                if trend == 'WEAK' and current_price > r2:
                    if adx_value < self.adx[-2]:  # ADX declining at highs
                        if minus_di_value > plus_di_value:
                            short_signal = True
                elif trend == 'STRONG_DOWN' and current_price < s2:
                    if adx_value < self.adx[-2]:  # Potential exhaustion
                        if plus_di_value > self.plus_di[-2]:  # +DI turning up
                            long_signal = True  # Reversal

            # 4. London close with trend exhaustion
            elif killzone == 'LONDON' and current_time.hour >= 9:
                if adx_value < session_avg_adx and trend in ['MODERATE_UP', 'STRONG_UP']:
                    if current_price < self.data.High[-2] and minus_di_value > self.minus_di[-2]:
                        short_signal = True

            # 5. Strong momentum continuation short
            elif trend == 'STRONG_DOWN' and killzone in ['NY_AM', 'LONDON']:
                if current_price < s1 and adx_value > self.adx[-2]:
                    if cmf_value < 0 and macd_bearish:
                        short_signal = True

            # Execute trades with ADX-adjusted stops
            if long_signal:
                # Wider stops for weak trends, tighter for strong trends
                stop_multiplier = 2.5 if trend == 'WEAK' else (1.5 if 'STRONG' in trend else 2.0)
                target_multiplier = 2.5 if 'STRONG' in trend else (2.0 if 'MODERATE' in trend else 1.5)

                sl_price = current_price - (stop_multiplier * atr_value)
                tp_price = current_price + (target_multiplier * atr_value)

                # Ensure minimum risk/reward
                if tp_price > current_price * (1 + self.take_profit):
                    tp_price = current_price * (1 + self.take_profit)
                if sl_price < current_price * (1 - self.stop_loss):
                    sl_price = current_price * (1 - self.stop_loss)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            elif short_signal:
                # Wider stops for weak trends, tighter for strong trends
                stop_multiplier = 2.5 if trend == 'WEAK' else (1.5 if 'STRONG' in trend else 2.0)
                target_multiplier = 2.5 if 'STRONG' in trend else (2.0 if 'MODERATE' in trend else 1.5)

                sl_price = current_price + (stop_multiplier * atr_value)
                tp_price = current_price - (target_multiplier * atr_value)

                # Ensure minimum risk/reward
                if tp_price < current_price * (1 - self.take_profit):
                    tp_price = current_price * (1 - self.take_profit)
                if sl_price > current_price * (1 + self.stop_loss):
                    sl_price = current_price * (1 + self.stop_loss)

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

# Run single backtest (default behavior)
bt = Backtest(data, ICTKillzonesADX, cash=10000000, commission=0.00045)

print("\n🌙 ===== ICT KILLZONES + ADX - DEFAULT PARAMETERS ===== 🌙")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Session Breakout Threshold: {SESSION_BREAKOUT_THRESHOLD}%")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Trend Threshold: {ADX_TREND_THRESHOLD}")
print(f"ADX Strong Trend: {ADX_STRONG_TREND}")
print(f"DI Signal Difference: {DI_SIGNAL_DIFF}")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ICT KILLZONES + ADX ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(ICTKillzonesADX, 'ICTKillzonesADX')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ICTKillzonesADX.csv")