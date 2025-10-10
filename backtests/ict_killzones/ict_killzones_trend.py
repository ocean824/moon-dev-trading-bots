"""
ICT Killzones & Pivots Strategy - Trend Following Version
=========================================================
Simplified trend following approach using ICT killzone concepts
with moving averages and momentum indicators.
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from datetime import time

print("🚀 Moon Dev's ICT Killzones Trend Following Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 1.5
EMA_FAST = 12
EMA_SLOW = 26
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ICTKillzonesTrend(Strategy):
    # Strategy parameters
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    ema_fast = EMA_FAST
    ema_slow = EMA_SLOW
    rsi_period = RSI_PERIOD
    rsi_overbought = RSI_OVERBOUGHT
    rsi_oversold = RSI_OVERSOLD

    def init(self):
        """Initialize indicators and session tracking"""
        close = self.data.Close
        high = self.data.High
        low = self.data.Low
        volume = self.data.Volume

        # Calculate pivot points (standard pivots)
        self.pivot_point = self.I(lambda: (high + low + close) / 3)
        self.resistance1 = self.I(lambda: 2 * self.pivot_point - low)
        self.resistance2 = self.I(lambda: self.pivot_point + (high - low))
        self.support1 = self.I(lambda: 2 * self.pivot_point - high)
        self.support2 = self.I(lambda: self.pivot_point - (high - low))

        # Trend indicators
        self.ema_fast_line = self.I(talib.EMA, close, self.ema_fast)
        self.ema_slow_line = self.I(talib.EMA, close, self.ema_slow)
        self.rsi = self.I(talib.RSI, close, self.rsi_period)

        # Momentum indicators
        self.macd = self.I(lambda: talib.MACD(close, 12, 26, 9)[0])
        self.macd_signal = self.I(lambda: talib.MACD(close, 12, 26, 9)[1])
        self.macd_hist = self.I(lambda: talib.MACD(close, 12, 26, 9)[2])

        # Volume indicators
        self.volume_sma = self.I(talib.SMA, volume, 20)

        # ATR for dynamic stops
        self.atr = self.I(talib.ATR, high, low, close, 14)

        # Bollinger Bands
        self.bb_upper = self.I(lambda: talib.BBANDS(close, 20, 2.0, 2.0)[0])
        self.bb_middle = self.I(lambda: talib.BBANDS(close, 20, 2.0, 2.0)[1])
        self.bb_lower = self.I(lambda: talib.BBANDS(close, 20, 2.0, 2.0)[2])

        # Track session highs and lows
        self.session_highs = []
        self.session_lows = []
        self.current_session = None
        self.session_high = 0
        self.session_low = float('inf')

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

    def next(self):
        """Trading logic based on trend following in killzones"""
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
        else:
            # Update current session high/low
            if killzone is not None:
                self.session_high = max(self.session_high, self.data.High[-1])
                self.session_low = min(self.session_low, self.data.Low[-1])

        # Skip if not in a killzone
        if killzone is None:
            return

        # Get current price and indicators
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]

        # Check if we have enough data
        if (len(self.ema_fast_line) < self.ema_fast or
            len(self.ema_slow_line) < self.ema_slow or
            len(self.rsi) < self.rsi_period):
            return

        ema_fast_val = self.ema_fast_line[-1]
        ema_slow_val = self.ema_slow_line[-1]
        rsi_val = self.rsi[-1]
        atr_val = self.atr[-1] if len(self.atr) > 13 else current_price * 0.01
        volume_avg = self.volume_sma[-1] if len(self.volume_sma) > 19 else current_volume

        macd_val = self.macd[-1] if len(self.macd) > 0 else 0
        macd_sig = self.macd_signal[-1] if len(self.macd_signal) > 0 else 0
        macd_hist_val = self.macd_hist[-1] if len(self.macd_hist) > 0 else 0

        bb_upper_val = self.bb_upper[-1] if len(self.bb_upper) > 0 else current_price * 1.02
        bb_lower_val = self.bb_lower[-1] if len(self.bb_lower) > 0 else current_price * 0.98
        bb_middle_val = self.bb_middle[-1] if len(self.bb_middle) > 0 else current_price

        pivot = self.pivot_point[-1]
        r1 = self.resistance1[-1]
        r2 = self.resistance2[-1]
        s1 = self.support1[-1]
        s2 = self.support2[-1]

        # Entry logic based on trend following in specific killzones
        if not self.position:
            # Determine market conditions
            bullish_trend = ema_fast_val > ema_slow_val
            bearish_trend = ema_fast_val < ema_slow_val
            price_above_ema = current_price > ema_fast_val
            price_below_ema = current_price < ema_fast_val
            macd_bullish = macd_val > macd_sig
            macd_bearish = macd_val < macd_sig
            volume_above_avg = current_volume > volume_avg

            # Long conditions based on killzone and trend
            long_signal = False

            # 1. London session trend following
            if killzone == 'LONDON':
                if bullish_trend and price_above_ema and macd_bullish:
                    if rsi_val > 50 and rsi_val < self.rsi_overbought:
                        if current_price > pivot:
                            long_signal = True

            # 2. NY AM power hour
            elif killzone == 'NY_AM':
                if bullish_trend and macd_hist_val > 0:
                    if current_price > bb_middle_val:
                        if volume_above_avg:
                            long_signal = True

            # 3. NY PM continuation
            elif killzone == 'NY_PM':
                if bullish_trend and price_above_ema:
                    if rsi_val < self.rsi_overbought:
                        if current_price > self.session_high * 0.999:  # Near session high
                            long_signal = True

            # 4. Asia range breakout
            elif killzone == 'ASIA':
                if len(self.session_highs) > 0:
                    prev_high = self.session_highs[-1] if self.session_highs else self.session_high
                    if current_price > prev_high and bullish_trend:
                        if macd_bullish:
                            long_signal = True

            # Short conditions based on killzone and trend
            short_signal = False

            # 1. London session trend following down
            if killzone == 'LONDON':
                if bearish_trend and price_below_ema and macd_bearish:
                    if rsi_val < 50 and rsi_val > self.rsi_oversold:
                        if current_price < pivot:
                            short_signal = True

            # 2. NY AM breakdown
            elif killzone == 'NY_AM':
                if bearish_trend and macd_hist_val < 0:
                    if current_price < bb_middle_val:
                        if volume_above_avg:
                            short_signal = True

            # 3. NY PM reversal
            elif killzone == 'NY_PM':
                if bearish_trend and price_below_ema:
                    if rsi_val > self.rsi_oversold:
                        if current_price < self.session_low * 1.001:  # Near session low
                            short_signal = True

            # 4. Asia range breakdown
            elif killzone == 'ASIA':
                if len(self.session_lows) > 0:
                    prev_low = self.session_lows[-1] if self.session_lows else self.session_low
                    if current_price < prev_low and bearish_trend:
                        if macd_bearish:
                            short_signal = True

            # Execute trades with simple percentage stops
            if long_signal:
                # Simple percentage-based stops
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)

                # Ensure proper order: SL < Entry < TP for longs
                if sl_price >= current_price or tp_price <= current_price:
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            elif short_signal:
                # Simple percentage-based stops
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)

                # Ensure proper order: TP < Entry < SL for shorts
                if tp_price >= current_price or sl_price <= current_price:
                    tp_price = current_price * (1 - self.take_profit)
                    sl_price = current_price * (1 + self.stop_loss)

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

# Run single backtest (default behavior)
bt = Backtest(data, ICTKillzonesTrend, cash=10000000, commission=0.00045)

print("\n🌙 ===== ICT KILLZONES TREND - DEFAULT PARAMETERS ===== 🌙")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"EMA Fast: {EMA_FAST}")
print(f"EMA Slow: {EMA_SLOW}")
print(f"RSI Period: {RSI_PERIOD}")
print(f"RSI Overbought: {RSI_OVERBOUGHT}")
print(f"RSI Oversold: {RSI_OVERSOLD}")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ICT KILLZONES TREND ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(ICTKillzonesTrend, 'ICTKillzonesTrend')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ICTKillzonesTrend.csv")