"""
Moon Dev's Trend Impulse + Bollinger Bands Combination Strategy
===============================================================
Combines Trend Impulse Channels with Bollinger Bands for volatility-based signals.
Uses squeeze detection, band width filtering, and %B for precise entry timing.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Impulse + Bollinger Bands Combo Strategy Loading... 🌙")

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ATR_PERIOD = 14
EMA_FAST = 12
EMA_SLOW = 26
ATR_CHANNEL = 2.0

# Bollinger Bands parameters
BB_PERIOD = 20
BB_STD = 2.0
BB_SQUEEZE_THRESHOLD = 0.015  # Band width threshold for squeeze detection

# Risk management
TAKE_PROFIT_PERCENT = 3.5
STOP_LOSS_PERCENT = 1.5

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendImpulseBBandsCombo(Strategy):
    """
    Trend Impulse + Bollinger Bands Combination Strategy

    Entry Conditions:
    - Long: Trend Impulse bullish + BB squeeze breakout or %B oversold bounce
    - Short: Trend Impulse bearish + BB squeeze breakdown or %B overbought rejection

    Uses band width for volatility filtering and %B for entry timing.
    """

    # Parameters
    atr_period = ATR_PERIOD
    ema_fast = EMA_FAST
    ema_slow = EMA_SLOW
    atr_channel = ATR_CHANNEL
    bb_period = BB_PERIOD
    bb_std = BB_STD
    bb_squeeze_threshold = BB_SQUEEZE_THRESHOLD
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

        # Calculate Bollinger Bands
        bbands = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        if bbands is not None and not bbands.empty:
            bb_lower = bbands[f'BBL_{self.bb_period}_{self.bb_std}']
            bb_middle = bbands[f'BBM_{self.bb_period}_{self.bb_std}']
            bb_upper = bbands[f'BBU_{self.bb_period}_{self.bb_std}']
            bb_bandwidth = bbands[f'BBB_{self.bb_period}_{self.bb_std}']
            bb_percent = bbands[f'BBP_{self.bb_period}_{self.bb_std}']
        else:
            bb_lower = pd.Series([np.nan] * len(close))
            bb_middle = pd.Series([np.nan] * len(close))
            bb_upper = pd.Series([np.nan] * len(close))
            bb_bandwidth = pd.Series([np.nan] * len(close))
            bb_percent = pd.Series([np.nan] * len(close))

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

        self.bb_lower_full = np.full(len(close), np.nan)
        if bb_lower is not None:
            self.bb_lower_full[-len(bb_lower):] = bb_lower.values

        self.bb_middle_full = np.full(len(close), np.nan)
        if bb_middle is not None:
            self.bb_middle_full[-len(bb_middle):] = bb_middle.values

        self.bb_upper_full = np.full(len(close), np.nan)
        if bb_upper is not None:
            self.bb_upper_full[-len(bb_upper):] = bb_upper.values

        self.bb_bandwidth_full = np.full(len(close), np.nan)
        if bb_bandwidth is not None:
            self.bb_bandwidth_full[-len(bb_bandwidth):] = bb_bandwidth.values

        self.bb_percent_full = np.full(len(close), np.nan)
        if bb_percent is not None:
            self.bb_percent_full[-len(bb_percent):] = bb_percent.values

        # Calculate trend direction
        self.trend = np.where(self.ema_fast_full > self.ema_slow_full, 1, -1)

        # Calculate ATR channels
        self.upper_channel = self.ema_slow_full + (self.atr_full * self.atr_channel)
        self.lower_channel = self.ema_slow_full - (self.atr_full * self.atr_channel)

        # Detect Bollinger squeeze (low volatility periods)
        self.bb_squeeze = np.zeros(len(close))
        for i in range(len(close)):
            if not np.isnan(self.bb_bandwidth_full[i]):
                # Normalize bandwidth by price for relative comparison
                normalized_bandwidth = self.bb_bandwidth_full[i] / close.iloc[i] if close.iloc[i] > 0 else 0
                if normalized_bandwidth < self.bb_squeeze_threshold:
                    self.bb_squeeze[i] = 1  # Squeeze detected

        # Detect squeeze releases (expansion after squeeze)
        self.squeeze_release = np.zeros(len(close))
        for i in range(1, len(close)):
            if self.bb_squeeze[i-1] == 1 and self.bb_squeeze[i] == 0:
                # Check direction of breakout
                if close.iloc[i] > self.bb_middle_full[i]:
                    self.squeeze_release[i] = 1  # Bullish squeeze release
                else:
                    self.squeeze_release[i] = -1  # Bearish squeeze release

        # Store as indicators
        self.I_ema_fast = self.I(lambda: self.ema_fast_full)
        self.I_ema_slow = self.I(lambda: self.ema_slow_full)
        self.I_atr = self.I(lambda: self.atr_full)
        self.I_upper = self.I(lambda: self.upper_channel)
        self.I_lower = self.I(lambda: self.lower_channel)
        self.I_trend = self.I(lambda: self.trend)
        self.I_bb_lower = self.I(lambda: self.bb_lower_full)
        self.I_bb_middle = self.I(lambda: self.bb_middle_full)
        self.I_bb_upper = self.I(lambda: self.bb_upper_full)
        self.I_bb_bandwidth = self.I(lambda: self.bb_bandwidth_full)
        self.I_bb_percent = self.I(lambda: self.bb_percent_full)

    def next(self):
        """Trading logic with Bollinger Bands"""
        # Skip if not enough data
        if len(self.data) < max(self.ema_slow, self.bb_period) + 10:
            return

        # Get current values
        idx = len(self.data) - 1
        if idx < 0 or idx >= len(self.ema_fast_full):
            return

        current_price = self.data.Close[-1]
        current_trend = self.trend[idx]
        prev_trend = self.trend[idx-1] if idx > 0 else 0

        # Get Bollinger Bands values
        bb_lower = self.bb_lower_full[idx]
        bb_middle = self.bb_middle_full[idx]
        bb_upper = self.bb_upper_full[idx]
        bb_bandwidth = self.bb_bandwidth_full[idx]
        bb_percent = self.bb_percent_full[idx]
        is_squeeze = self.bb_squeeze[idx] == 1
        squeeze_release = self.squeeze_release[idx]

        # Skip if any indicator is NaN
        if np.isnan(self.ema_fast_full[idx]) or np.isnan(self.atr_full[idx]) or \
           np.isnan(bb_middle):
            return

        # Calculate normalized bandwidth for volatility assessment
        normalized_bandwidth = bb_bandwidth / current_price if current_price > 0 else 0

        # Position management
        if not self.position:
            # Long entry conditions with BB confirmation
            if current_trend > 0:  # Bullish trend
                enter_long = False

                # Squeeze breakout to the upside
                if squeeze_release > 0:
                    enter_long = True

                # Trend change with BB support
                if prev_trend <= 0 and current_price > bb_middle:
                    enter_long = True

                # Channel bounce + BB oversold (%B < 0.2)
                if (self.data.Low[-1] <= self.lower_channel[idx] and
                    current_price > self.lower_channel[idx] and
                    bb_percent < 0.2):
                    enter_long = True

                # BB lower band touch with trend support
                if (self.data.Low[-1] <= bb_lower and
                    current_price > bb_lower and
                    current_price > self.ema_slow_full[idx]):
                    enter_long = True

                # Breakout above upper channel with expanding bands
                if (idx > 1 and current_price > self.upper_channel[idx] and
                    self.data.Close[-2] <= self.upper_channel[idx-1] and
                    normalized_bandwidth > self.bb_squeeze_threshold * 1.5):
                    enter_long = True

                # Middle band bounce in strong uptrend
                if (idx > 1 and self.data.Low[-1] <= bb_middle and
                    current_price > bb_middle and
                    self.ema_fast_full[idx] > self.ema_slow_full[idx] * 1.01):  # Strong trend
                    enter_long = True

                if enter_long:
                    # Adjust position based on volatility
                    if normalized_bandwidth < self.bb_squeeze_threshold:
                        vol_multiplier = 1.2  # Low volatility = larger position
                    elif normalized_bandwidth > self.bb_squeeze_threshold * 2:
                        vol_multiplier = 0.8  # High volatility = smaller position
                    else:
                        vol_multiplier = 1.0

                    # Dynamic stops based on BB width
                    bb_stop = abs(bb_upper - bb_lower) * 0.5
                    atr_stop = self.atr_full[idx] * 2.0
                    stop_distance = min(bb_stop, atr_stop)

                    sl = max(current_price - stop_distance, current_price * (1 - self.stop_loss_pct))
                    tp = current_price * (1 + self.take_profit_pct * vol_multiplier)

                    self.buy(size=min(0.95, 0.95 * vol_multiplier), sl=sl, tp=tp)

            # Short entry conditions with BB confirmation
            elif current_trend < 0:  # Bearish trend
                enter_short = False

                # Squeeze breakdown to the downside
                if squeeze_release < 0:
                    enter_short = True

                # Trend change with BB resistance
                if prev_trend >= 0 and current_price < bb_middle:
                    enter_short = True

                # Channel rejection + BB overbought (%B > 0.8)
                if (self.data.High[-1] >= self.upper_channel[idx] and
                    current_price < self.upper_channel[idx] and
                    bb_percent > 0.8):
                    enter_short = True

                # BB upper band touch with trend resistance
                if (self.data.High[-1] >= bb_upper and
                    current_price < bb_upper and
                    current_price < self.ema_slow_full[idx]):
                    enter_short = True

                # Breakdown below lower channel with expanding bands
                if (idx > 1 and current_price < self.lower_channel[idx] and
                    self.data.Close[-2] >= self.lower_channel[idx-1] and
                    normalized_bandwidth > self.bb_squeeze_threshold * 1.5):
                    enter_short = True

                # Middle band rejection in strong downtrend
                if (idx > 1 and self.data.High[-1] >= bb_middle and
                    current_price < bb_middle and
                    self.ema_fast_full[idx] < self.ema_slow_full[idx] * 0.99):  # Strong downtrend
                    enter_short = True

                if enter_short:
                    # Adjust position based on volatility
                    if normalized_bandwidth < self.bb_squeeze_threshold:
                        vol_multiplier = 1.2
                    elif normalized_bandwidth > self.bb_squeeze_threshold * 2:
                        vol_multiplier = 0.8
                    else:
                        vol_multiplier = 1.0

                    # Dynamic stops based on BB width
                    bb_stop = abs(bb_upper - bb_lower) * 0.5
                    atr_stop = self.atr_full[idx] * 2.0
                    stop_distance = min(bb_stop, atr_stop)

                    sl = min(current_price + stop_distance, current_price * (1 + self.stop_loss_pct))
                    tp = current_price * (1 - self.take_profit_pct * vol_multiplier)

                    self.sell(size=min(0.95, 0.95 * vol_multiplier), sl=sl, tp=tp)

        else:
            # Exit management with Bollinger Bands
            if self.position.is_long:
                # Exit conditions for longs
                exit_signal = False

                # Trend reversal
                if current_trend < 0:
                    exit_signal = True

                # %B extremely overbought (> 1.0, outside upper band)
                elif bb_percent > 1.0:
                    exit_signal = True

                # Price closes below middle band in weak trend
                elif (current_price < bb_middle and
                      self.ema_fast_full[idx] < self.ema_slow_full[idx] * 1.005):
                    exit_signal = True

                # Price closes below lower channel
                elif current_price < self.lower_channel[idx]:
                    exit_signal = True

                # Squeeze forming at highs (potential reversal)
                elif is_squeeze and bb_percent > 0.8:
                    exit_signal = True

                if exit_signal:
                    self.position.close()

            else:  # Short position
                # Exit conditions for shorts
                exit_signal = False

                # Trend reversal
                if current_trend > 0:
                    exit_signal = True

                # %B extremely oversold (< 0, outside lower band)
                elif bb_percent < 0:
                    exit_signal = True

                # Price closes above middle band in weak trend
                elif (current_price > bb_middle and
                      self.ema_fast_full[idx] > self.ema_slow_full[idx] * 0.995):
                    exit_signal = True

                # Price closes above upper channel
                elif current_price > self.upper_channel[idx]:
                    exit_signal = True

                # Squeeze forming at lows (potential reversal)
                elif is_squeeze and bb_percent < 0.2:
                    exit_signal = True

                if exit_signal:
                    self.position.close()

# Run single backtest
bt = Backtest(data, TrendImpulseBBandsCombo, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND IMPULSE + BOLLINGER BANDS - PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"Fast EMA: {EMA_FAST}")
print(f"Slow EMA: {EMA_SLOW}")
print(f"ATR Channel: {ATR_CHANNEL}x")
print(f"BB Period: {BB_PERIOD}")
print(f"BB Std Dev: {BB_STD}")
print(f"BB Squeeze Threshold: {BB_SQUEEZE_THRESHOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND IMPULSE + BOLLINGER BANDS ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendImpulseBBandsCombo, 'TrendImpulseBBandsCombo')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendImpulseBBandsCombo.csv")