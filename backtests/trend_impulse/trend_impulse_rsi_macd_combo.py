"""
Moon Dev's Trend Impulse + RSI/MACD Combination Strategy
========================================================
Combines Trend Impulse with classic oscillators RSI and MACD.
Multiple confirmation requirements for high-probability trades.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Impulse + RSI/MACD Combo Strategy Loading... 🌙")

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ATR_PERIOD = 14
EMA_FAST = 12
EMA_SLOW = 26
ATR_CHANNEL = 2.0

# RSI parameters
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
RSI_STRONG_OB = 80  # Very overbought
RSI_STRONG_OS = 20  # Very oversold

# MACD parameters
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Risk management
TAKE_PROFIT_PERCENT = 3.5
STOP_LOSS_PERCENT = 1.5

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendImpulseRSIMACDCombo(Strategy):
    """
    Trend Impulse + RSI/MACD Combination Strategy

    Entry Conditions (requires 2 out of 3):
    - Long: Trend Impulse bullish + RSI oversold + MACD bullish cross
    - Short: Trend Impulse bearish + RSI overbought + MACD bearish cross

    Multiple confirmations for high-probability setups.
    """

    # Parameters
    atr_period = ATR_PERIOD
    ema_fast = EMA_FAST
    ema_slow = EMA_SLOW
    atr_channel = ATR_CHANNEL
    rsi_period = RSI_PERIOD
    rsi_overbought = RSI_OVERBOUGHT
    rsi_oversold = RSI_OVERSOLD
    rsi_strong_ob = RSI_STRONG_OB
    rsi_strong_os = RSI_STRONG_OS
    macd_fast = MACD_FAST
    macd_slow = MACD_SLOW
    macd_signal = MACD_SIGNAL
    take_profit_pct = TAKE_PROFIT_PERCENT / 100
    stop_loss_pct = STOP_LOSS_PERCENT / 100

    def init(self):
        """Initialize indicators"""
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Calculate EMAs for Trend Impulse
        ema_fast = ta.ema(close, length=self.ema_fast)
        ema_slow = ta.ema(close, length=self.ema_slow)

        # Calculate ATR for channels
        atr = ta.atr(high, low, close, length=self.atr_period)

        # Calculate RSI
        rsi = ta.rsi(close, length=self.rsi_period)

        # Calculate MACD
        macd_result = ta.macd(close, fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)
        if macd_result is not None and not macd_result.empty:
            macd_line = macd_result[f'MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}']
            macd_signal_line = macd_result[f'MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}']
            macd_histogram = macd_result[f'MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}']
        else:
            macd_line = pd.Series([np.nan] * len(close))
            macd_signal_line = pd.Series([np.nan] * len(close))
            macd_histogram = pd.Series([np.nan] * len(close))

        # Ensure arrays match data length
        self.ema_fast_full = np.full(len(close), np.nan)
        if ema_fast is not None:
            self.ema_fast_full[-len(ema_fast):] = ema_fast.values

        self.ema_slow_full = np.full(len(close), np.nan)
        if ema_slow is not None:
            self.ema_slow_full[-len(ema_slow):] = ema_slow.values

        self.atr_full = np.full(len(close), np.nan)
        if atr is not None:
            self.atr_full[-len(atr):] = atr.values

        self.rsi_full = np.full(len(close), np.nan)
        if rsi is not None:
            self.rsi_full[-len(rsi):] = rsi.values

        self.macd_line_full = np.full(len(close), np.nan)
        if macd_line is not None:
            self.macd_line_full[-len(macd_line):] = macd_line.values

        self.macd_signal_full = np.full(len(close), np.nan)
        if macd_signal_line is not None:
            self.macd_signal_full[-len(macd_signal_line):] = macd_signal_line.values

        self.macd_histogram_full = np.full(len(close), np.nan)
        if macd_histogram is not None:
            self.macd_histogram_full[-len(macd_histogram):] = macd_histogram.values

        # Calculate trend direction
        self.trend = np.where(self.ema_fast_full > self.ema_slow_full, 1, -1)

        # Calculate ATR channels
        self.upper_channel = self.ema_slow_full + (self.atr_full * self.atr_channel)
        self.lower_channel = self.ema_slow_full - (self.atr_full * self.atr_channel)

        # Detect MACD crossovers
        self.macd_cross = np.zeros(len(close))
        for i in range(1, len(close)):
            if not np.isnan(self.macd_line_full[i]) and not np.isnan(self.macd_signal_full[i]):
                # Bullish cross
                if (self.macd_line_full[i] > self.macd_signal_full[i] and
                    self.macd_line_full[i-1] <= self.macd_signal_full[i-1]):
                    self.macd_cross[i] = 1
                # Bearish cross
                elif (self.macd_line_full[i] < self.macd_signal_full[i] and
                      self.macd_line_full[i-1] >= self.macd_signal_full[i-1]):
                    self.macd_cross[i] = -1

        # Store as indicators
        self.I_ema_fast = self.I(lambda: self.ema_fast_full)
        self.I_ema_slow = self.I(lambda: self.ema_slow_full)
        self.I_atr = self.I(lambda: self.atr_full)
        self.I_upper = self.I(lambda: self.upper_channel)
        self.I_lower = self.I(lambda: self.lower_channel)
        self.I_trend = self.I(lambda: self.trend)
        self.I_rsi = self.I(lambda: self.rsi_full)
        self.I_macd = self.I(lambda: self.macd_line_full)
        self.I_macd_signal = self.I(lambda: self.macd_signal_full)
        self.I_macd_hist = self.I(lambda: self.macd_histogram_full)

    def next(self):
        """Trading logic with multiple confirmations"""
        # Skip if not enough data
        if len(self.data) < max(self.ema_slow, self.macd_slow) + 10:
            return

        # Get current values
        idx = len(self.data) - 1
        if idx < 0 or idx >= len(self.ema_fast_full):
            return

        current_price = self.data.Close[-1]
        current_trend = self.trend[idx]
        prev_trend = self.trend[idx-1] if idx > 0 else 0

        # Get oscillator values
        current_rsi = self.rsi_full[idx]
        current_macd = self.macd_line_full[idx]
        current_macd_signal = self.macd_signal_full[idx]
        current_macd_hist = self.macd_histogram_full[idx]
        prev_macd_hist = self.macd_histogram_full[idx-1] if idx > 0 else 0

        # Check for recent MACD cross (within last 3 bars)
        recent_macd_cross = 0
        for i in range(max(0, idx-2), idx+1):
            if self.macd_cross[i] != 0:
                recent_macd_cross = self.macd_cross[i]
                break

        # Skip if any indicator is NaN
        if np.isnan(self.ema_fast_full[idx]) or np.isnan(self.atr_full[idx]) or \
           np.isnan(current_rsi) or np.isnan(current_macd):
            return

        # Position management
        if not self.position:
            # Long entry - need at least 2 out of 3 confirmations
            if current_trend > 0:  # Bullish trend impulse
                long_confirmations = 0
                long_reasons = []

                # Check Trend Impulse signals
                trend_signal = False
                if prev_trend <= 0:  # Trend just turned bullish
                    trend_signal = True
                    long_reasons.append("trend_change")
                elif (self.data.Low[-1] <= self.lower_channel[idx] and
                      current_price > self.lower_channel[idx]):  # Channel bounce
                    trend_signal = True
                    long_reasons.append("channel_bounce")
                elif (idx > 1 and current_price > self.upper_channel[idx] and
                      self.data.Close[-2] <= self.upper_channel[idx-1]):  # Breakout
                    trend_signal = True
                    long_reasons.append("breakout")

                if trend_signal:
                    long_confirmations += 1

                # Check RSI condition
                if current_rsi < self.rsi_oversold:
                    long_confirmations += 1
                    long_reasons.append("rsi_oversold")
                elif current_rsi < 50:  # At least below midpoint
                    long_confirmations += 0.5
                    long_reasons.append("rsi_weak")

                # Check MACD condition
                if recent_macd_cross > 0:  # Recent bullish cross
                    long_confirmations += 1
                    long_reasons.append("macd_cross")
                elif current_macd > current_macd_signal:  # MACD above signal
                    long_confirmations += 0.5
                    long_reasons.append("macd_bullish")
                elif current_macd_hist > prev_macd_hist and current_macd_hist > 0:  # Histogram growing
                    long_confirmations += 0.5
                    long_reasons.append("macd_momentum")

                # Enter if we have enough confirmations
                if long_confirmations >= 2:
                    # Stronger signals get better risk/reward
                    signal_strength = min(long_confirmations / 3, 1.0)

                    # Calculate stops
                    atr_stop = self.atr_full[idx] * (2.5 - signal_strength * 0.5)
                    sl = max(current_price - atr_stop, current_price * (1 - self.stop_loss_pct))
                    tp = current_price * (1 + self.take_profit_pct * (1 + signal_strength * 0.2))

                    self.buy(size=0.95, sl=sl, tp=tp)

            # Short entry - need at least 2 out of 3 confirmations
            elif current_trend < 0:  # Bearish trend impulse
                short_confirmations = 0
                short_reasons = []

                # Check Trend Impulse signals
                trend_signal = False
                if prev_trend >= 0:  # Trend just turned bearish
                    trend_signal = True
                    short_reasons.append("trend_change")
                elif (self.data.High[-1] >= self.upper_channel[idx] and
                      current_price < self.upper_channel[idx]):  # Channel rejection
                    trend_signal = True
                    short_reasons.append("channel_rejection")
                elif (idx > 1 and current_price < self.lower_channel[idx] and
                      self.data.Close[-2] >= self.lower_channel[idx-1]):  # Breakdown
                    trend_signal = True
                    short_reasons.append("breakdown")

                if trend_signal:
                    short_confirmations += 1

                # Check RSI condition
                if current_rsi > self.rsi_overbought:
                    short_confirmations += 1
                    short_reasons.append("rsi_overbought")
                elif current_rsi > 50:  # At least above midpoint
                    short_confirmations += 0.5
                    short_reasons.append("rsi_strong")

                # Check MACD condition
                if recent_macd_cross < 0:  # Recent bearish cross
                    short_confirmations += 1
                    short_reasons.append("macd_cross")
                elif current_macd < current_macd_signal:  # MACD below signal
                    short_confirmations += 0.5
                    short_reasons.append("macd_bearish")
                elif current_macd_hist < prev_macd_hist and current_macd_hist < 0:  # Histogram declining
                    short_confirmations += 0.5
                    short_reasons.append("macd_momentum")

                # Enter if we have enough confirmations
                if short_confirmations >= 2:
                    # Stronger signals get better risk/reward
                    signal_strength = min(short_confirmations / 3, 1.0)

                    # Calculate stops
                    atr_stop = self.atr_full[idx] * (2.5 - signal_strength * 0.5)
                    sl = min(current_price + atr_stop, current_price * (1 + self.stop_loss_pct))
                    tp = current_price * (1 - self.take_profit_pct * (1 + signal_strength * 0.2))

                    self.sell(size=0.95, sl=sl, tp=tp)

        else:
            # Exit management
            if self.position.is_long:
                # Exit conditions for longs
                exit_signal = False

                # Trend reversal
                if current_trend < 0:
                    exit_signal = True

                # RSI extremely overbought
                elif current_rsi > self.rsi_strong_ob:
                    exit_signal = True

                # MACD bearish cross
                elif self.macd_cross[idx] < 0:
                    exit_signal = True

                # Price below channel
                elif current_price < self.lower_channel[idx]:
                    exit_signal = True

                # Histogram turning negative
                elif current_macd_hist < 0 and prev_macd_hist > 0:
                    exit_signal = True

                if exit_signal:
                    self.position.close()

            else:  # Short position
                # Exit conditions for shorts
                exit_signal = False

                # Trend reversal
                if current_trend > 0:
                    exit_signal = True

                # RSI extremely oversold
                elif current_rsi < self.rsi_strong_os:
                    exit_signal = True

                # MACD bullish cross
                elif self.macd_cross[idx] > 0:
                    exit_signal = True

                # Price above channel
                elif current_price > self.upper_channel[idx]:
                    exit_signal = True

                # Histogram turning positive
                elif current_macd_hist > 0 and prev_macd_hist < 0:
                    exit_signal = True

                if exit_signal:
                    self.position.close()

# Run single backtest
bt = Backtest(data, TrendImpulseRSIMACDCombo, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND IMPULSE + RSI/MACD - PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"Fast EMA: {EMA_FAST}")
print(f"Slow EMA: {EMA_SLOW}")
print(f"ATR Channel: {ATR_CHANNEL}x")
print(f"RSI Period: {RSI_PERIOD}")
print(f"RSI OB/OS: {RSI_OVERBOUGHT}/{RSI_OVERSOLD}")
print(f"MACD: {MACD_FAST}/{MACD_SLOW}/{MACD_SIGNAL}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND IMPULSE + RSI/MACD ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendImpulseRSIMACDCombo, 'TrendImpulseRSIMACDCombo')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendImpulseRSIMACDCombo.csv")