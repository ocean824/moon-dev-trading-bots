"""
ICT Killzones & Pivots Strategy - MFI Enhanced Version
======================================================
Combines ICT killzone concepts with Money Flow Index (MFI) for
better volume-weighted price movement confirmation.
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from datetime import time

print("🚀 Moon Dev's ICT Killzones + MFI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
TAKE_PROFIT_PERCENT = 3.5
STOP_LOSS_PERCENT = 1.5
SESSION_BREAKOUT_THRESHOLD = 0.4
PIVOT_RANGE_PERCENT = 0.3
MFI_PERIOD = 14
MFI_OVERBOUGHT = 80
MFI_OVERSOLD = 20

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ICTKillzonesMFI(Strategy):
    # Strategy parameters
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    session_threshold = SESSION_BREAKOUT_THRESHOLD / 100
    pivot_range = PIVOT_RANGE_PERCENT / 100
    mfi_period = MFI_PERIOD
    mfi_overbought = MFI_OVERBOUGHT
    mfi_oversold = MFI_OVERSOLD

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

        # MFI - Money Flow Index
        self.mfi = self.I(talib.MFI, high, low, close, volume, self.mfi_period)

        # Volume indicators
        self.volume_sma = self.I(talib.SMA, volume, 20)
        self.obv = self.I(talib.OBV, close, volume)
        self.obv_sma = self.I(talib.SMA, self.obv, 20)

        # ATR for dynamic stops
        self.atr = self.I(talib.ATR, high, low, close, 14)

        # RSI for additional confirmation
        self.rsi = self.I(talib.RSI, close, 14)

        # Track session highs and lows
        self.session_highs = []
        self.session_lows = []
        self.current_session = None
        self.session_high = 0
        self.session_low = float('inf')
        self.session_volume = 0

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
        """Trading logic based on ICT concepts with MFI enhancement"""
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
            self.session_volume = self.data.Volume[-1]
        else:
            # Update current session high/low
            if killzone is not None:
                self.session_high = max(self.session_high, self.data.High[-1])
                self.session_low = min(self.session_low, self.data.Low[-1])
                self.session_volume += self.data.Volume[-1]

        # Skip if not in a killzone
        if killzone is None:
            return

        # Get current price and indicators
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]

        # Check if we have enough data
        if len(self.mfi) < self.mfi_period or len(self.atr) < 14:
            return

        mfi_value = self.mfi[-1]
        atr_value = self.atr[-1]
        volume_avg = self.volume_sma[-1]
        obv_value = self.obv[-1]
        obv_avg = self.obv_sma[-1]
        rsi_value = self.rsi[-1]
        pivot = self.pivot_point[-1]
        r1 = self.resistance1[-1]
        r2 = self.resistance2[-1]
        r3 = self.resistance3[-1]
        s1 = self.support1[-1]
        s2 = self.support2[-1]
        s3 = self.support3[-1]

        # Entry logic with MFI confirmation
        if not self.position:
            # Determine trend and money flow
            above_pivot = current_price > pivot
            bullish_mfi = mfi_value > 50 and mfi_value < self.mfi_overbought
            bearish_mfi = mfi_value < 50 and mfi_value > self.mfi_oversold
            divergence_bull = current_price < self.data.Close[-2] and mfi_value > self.mfi[-2]
            divergence_bear = current_price > self.data.Close[-2] and mfi_value < self.mfi[-2]

            # Long conditions
            long_signal = False

            # 1. Breakout with strong money flow
            if self.session_high > 0 and current_price > self.session_high * (1 + self.session_threshold):
                if bullish_mfi and current_volume > volume_avg * 1.2:
                    if obv_value > obv_avg:  # OBV confirmation
                        long_signal = True

            # 2. Oversold bounce with MFI divergence
            elif mfi_value < self.mfi_oversold and killzone in ['LONDON', 'NY_AM']:
                if abs(current_price - s1) / s1 < self.pivot_range or abs(current_price - s2) / s2 < self.pivot_range:
                    if divergence_bull:
                        long_signal = True

            # 3. Session-specific patterns with MFI
            elif killzone == 'LONDON' and len(self.session_highs) > 0:
                asia_high = self.session_highs[-1] if self.session_highs else self.session_high
                if current_price > asia_high and bullish_mfi:
                    if rsi_value > 50 and rsi_value < 70:  # Not overbought
                        long_signal = True

            # 4. NY AM power hour with money flow
            elif killzone == 'NY_AM' and bullish_mfi:
                if current_price > pivot and mfi_value > self.mfi[-2]:
                    if current_volume > volume_avg * 1.5:  # High volume
                        long_signal = True

            # Short conditions
            short_signal = False

            # 1. Breakdown with weak money flow
            if self.session_low < float('inf') and current_price < self.session_low * (1 - self.session_threshold):
                if bearish_mfi and current_volume > volume_avg * 1.2:
                    if obv_value < obv_avg:  # OBV confirmation
                        short_signal = True

            # 2. Overbought rejection with MFI divergence
            elif mfi_value > self.mfi_overbought and killzone in ['LONDON', 'NY_AM']:
                if abs(current_price - r1) / r1 < self.pivot_range or abs(current_price - r2) / r2 < self.pivot_range:
                    if divergence_bear:
                        short_signal = True

            # 3. NY PM exhaustion with MFI
            elif killzone == 'NY_PM':
                if mfi_value > self.mfi_overbought and current_price > r2:
                    if current_volume < volume_avg * 0.8:  # Low volume at highs
                        short_signal = True
                elif mfi_value < self.mfi_oversold and current_price < s2:
                    if current_volume < volume_avg * 0.8:  # Potential reversal
                        long_signal = True

            # 4. London close reversal with MFI
            elif killzone == 'LONDON' and current_time.hour >= 9:
                if mfi_value > 70 and rsi_value > 70:
                    if current_price < self.data.High[-2]:  # Failed to make new high
                        short_signal = True

            # Execute trades with MFI-adjusted targets
            if long_signal:
                # Adjust targets based on MFI strength
                mfi_multiplier = 1 + (mfi_value - 50) / 100  # Scale based on MFI

                sl_price = current_price - (2 * atr_value)
                tp_price = current_price + (3 * atr_value * mfi_multiplier)

                # Ensure minimum risk/reward
                if tp_price > current_price * (1 + self.take_profit):
                    tp_price = current_price * (1 + self.take_profit)
                if sl_price < current_price * (1 - self.stop_loss):
                    sl_price = current_price * (1 - self.stop_loss)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            elif short_signal:
                # Adjust targets based on MFI weakness
                mfi_multiplier = 1 + (50 - mfi_value) / 100  # Scale inversely

                sl_price = current_price + (2 * atr_value)
                tp_price = current_price - (3 * atr_value * mfi_multiplier)

                # Ensure minimum risk/reward
                if tp_price < current_price * (1 - self.take_profit):
                    tp_price = current_price * (1 - self.take_profit)
                if sl_price > current_price * (1 + self.stop_loss):
                    sl_price = current_price * (1 + self.stop_loss)

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

# Run single backtest (default behavior)
bt = Backtest(data, ICTKillzonesMFI, cash=10000000, commission=0.00045)

print("\n🌙 ===== ICT KILLZONES + MFI - DEFAULT PARAMETERS ===== 🌙")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Session Breakout Threshold: {SESSION_BREAKOUT_THRESHOLD}%")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Overbought: {MFI_OVERBOUGHT}")
print(f"MFI Oversold: {MFI_OVERSOLD}")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ICT KILLZONES + MFI ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(ICTKillzonesMFI, 'ICTKillzonesMFI')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ICTKillzonesMFI.csv")