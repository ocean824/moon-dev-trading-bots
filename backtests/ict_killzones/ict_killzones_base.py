"""
ICT Killzones & Pivots Strategy - Base Version
=============================================
Based on Inner Circle Trader concepts with killzone sessions,
session highs/lows, and pivot points for entry/exit signals.

Killzone Sessions (in UTC):
- Asia: 00:00-04:00 UTC
- London: 07:00-10:00 UTC
- NY AM: 12:00-15:00 UTC
- NY Lunch: 15:00-17:00 UTC
- NY PM: 17:00-20:00 UTC
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from datetime import time

print("🚀 Moon Dev's ICT Killzones Base Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
TAKE_PROFIT_PERCENT = 2.5
STOP_LOSS_PERCENT = 1.2
SESSION_BREAKOUT_THRESHOLD = 0.2  # % above/below session high/low to trigger
PIVOT_RANGE_PERCENT = 0.8  # % distance from pivot to consider "at pivot"

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class ICTKillzonesBase(Strategy):
    # Strategy parameters
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    session_threshold = SESSION_BREAKOUT_THRESHOLD / 100
    pivot_range = PIVOT_RANGE_PERCENT / 100

    def init(self):
        """Initialize indicators and session tracking"""
        # Calculate pivot points (standard pivots)
        high = self.data.High
        low = self.data.Low
        close = self.data.Close

        # Daily pivot calculations
        self.pivot_point = self.I(lambda: (high + low + close) / 3)
        self.resistance1 = self.I(lambda: 2 * self.pivot_point - low)
        self.resistance2 = self.I(lambda: self.pivot_point + (high - low))
        self.support1 = self.I(lambda: 2 * self.pivot_point - high)
        self.support2 = self.I(lambda: self.pivot_point - (high - low))

        # Volume indicator for confirmation
        self.volume_sma = self.I(talib.SMA, self.data.Volume, 20)

        # ATR for dynamic stops
        self.atr = self.I(talib.ATR, high, low, close, 14)

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
        """Trading logic based on ICT concepts"""
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
        if len(self.atr) < 14 or len(self.volume_sma) < 20:
            return

        atr_value = self.atr[-1]
        volume_avg = self.volume_sma[-1]
        pivot = self.pivot_point[-1]
        r1 = self.resistance1[-1]
        r2 = self.resistance2[-1]
        s1 = self.support1[-1]
        s2 = self.support2[-1]

        # Entry logic - Simplified for more trades
        if not self.position:
            # Determine trend based on pivot position
            above_pivot = current_price > pivot
            price_change = current_price - self.data.Close[-2] if len(self.data.Close) > 1 else 0

            # Long conditions
            long_signal = False

            # 1. Simple breakout above session high
            if self.session_high > 0 and current_price > self.session_high * (1 + self.session_threshold):
                long_signal = True

            # 2. Bounce from support levels during active sessions
            elif killzone in ['LONDON', 'NY_AM', 'NY_PM'] and above_pivot:
                if abs(current_price - s1) / s1 < self.pivot_range:
                    if price_change > 0:  # Price moving up
                        long_signal = True
                elif abs(current_price - pivot) / pivot < self.pivot_range:
                    if price_change > 0:
                        long_signal = True

            # 3. London session momentum
            elif killzone == 'LONDON':
                if current_price > pivot and price_change > 0:
                    if current_volume > volume_avg * 0.8:  # Lowered volume requirement
                        long_signal = True

            # 4. NY session trends
            elif killzone in ['NY_AM', 'NY_PM']:
                if above_pivot and price_change > 0:
                    long_signal = True

            # Short conditions
            short_signal = False

            # 1. Simple breakdown below session low
            if self.session_low < float('inf') and current_price < self.session_low * (1 - self.session_threshold):
                short_signal = True

            # 2. Rejection from resistance levels
            elif killzone in ['LONDON', 'NY_AM', 'NY_PM'] and not above_pivot:
                if abs(current_price - r1) / r1 < self.pivot_range:
                    if price_change < 0:  # Price moving down
                        short_signal = True
                elif abs(current_price - pivot) / pivot < self.pivot_range:
                    if price_change < 0:
                        short_signal = True

            # 3. London session momentum down
            elif killzone == 'LONDON':
                if current_price < pivot and price_change < 0:
                    if current_volume > volume_avg * 0.8:
                        short_signal = True

            # 4. NY session trends down
            elif killzone in ['NY_AM', 'NY_PM']:
                if not above_pivot and price_change < 0:
                    short_signal = True

            # 5. Asia session range trading
            elif killzone == 'ASIA':
                # Simple range trading in Asia session
                if current_price > r1:
                    short_signal = True
                elif current_price < s1:
                    long_signal = True

            # Execute trades
            if long_signal:
                # Use ATR-based stops for better adaptation
                sl_price = current_price - (2 * atr_value)
                tp_price = current_price + (3 * atr_value)

                # Ensure minimum risk/reward
                if tp_price > current_price * (1 + self.take_profit):
                    tp_price = current_price * (1 + self.take_profit)
                if sl_price < current_price * (1 - self.stop_loss):
                    sl_price = current_price * (1 - self.stop_loss)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            elif short_signal:
                # ATR-based stops for shorts
                sl_price = current_price + (2 * atr_value)
                tp_price = current_price - (3 * atr_value)

                # Ensure minimum risk/reward
                if tp_price < current_price * (1 - self.take_profit):
                    tp_price = current_price * (1 - self.take_profit)
                if sl_price > current_price * (1 + self.stop_loss):
                    sl_price = current_price * (1 + self.stop_loss)

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

# Run single backtest (default behavior)
bt = Backtest(data, ICTKillzonesBase, cash=10000000, commission=0.00045)

print("\n🌙 ===== ICT KILLZONES BASE - DEFAULT PARAMETERS ===== 🌙")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Session Breakout Threshold: {SESSION_BREAKOUT_THRESHOLD}%")
print(f"Pivot Range: {PIVOT_RANGE_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ICT KILLZONES BASE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(ICTKillzonesBase, 'ICTKillzonesBase')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/ICTKillzonesBase.csv")