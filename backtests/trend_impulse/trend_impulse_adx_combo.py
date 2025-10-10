"""
Moon Dev's Trend Impulse + ADX Combination Strategy
===================================================
Combines Trend Impulse Channels with ADX for stronger trend filtering.
Uses ADX > 25 to confirm strong trends and +DI/-DI for directional confirmation.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Impulse + ADX Combo Strategy Loading... 🌙")

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ATR_PERIOD = 14
EMA_FAST = 12
EMA_SLOW = 26
ATR_CHANNEL = 2.0
ADX_PERIOD = 14
ADX_THRESHOLD = 25  # Only trade when ADX > 25 (strong trend)

# Risk management
TAKE_PROFIT_PERCENT = 3.5
STOP_LOSS_PERCENT = 1.5

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendImpulseADXCombo(Strategy):
    """
    Trend Impulse + ADX Combination Strategy

    Entry Conditions:
    - Long: Trend Impulse bullish signal + ADX > 25 + +DI > -DI
    - Short: Trend Impulse bearish signal + ADX > 25 + -DI > +DI

    Position sizing adjusted based on ADX strength.
    """

    # Parameters
    atr_period = ATR_PERIOD
    ema_fast = EMA_FAST
    ema_slow = EMA_SLOW
    atr_channel = ATR_CHANNEL
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
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

        # Calculate ADX, +DI, -DI
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        if adx_result is not None and not adx_result.empty:
            adx = adx_result[f'ADX_{self.adx_period}']
            plus_di = adx_result[f'DMP_{self.adx_period}']
            minus_di = adx_result[f'DMN_{self.adx_period}']
        else:
            adx = pd.Series([np.nan] * len(close))
            plus_di = pd.Series([np.nan] * len(close))
            minus_di = pd.Series([np.nan] * len(close))

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

        self.adx_full = np.full(len(close), np.nan)
        if adx is not None:
            self.adx_full[-len(adx):] = adx.values

        self.plus_di_full = np.full(len(close), np.nan)
        if plus_di is not None:
            self.plus_di_full[-len(plus_di):] = plus_di.values

        self.minus_di_full = np.full(len(close), np.nan)
        if minus_di is not None:
            self.minus_di_full[-len(minus_di):] = minus_di.values

        # Calculate trend direction
        self.trend = np.where(self.ema_fast_full > self.ema_slow_full, 1, -1)

        # Calculate ATR channels
        self.upper_channel = self.ema_slow_full + (self.atr_full * self.atr_channel)
        self.lower_channel = self.ema_slow_full - (self.atr_full * self.atr_channel)

        # Store as indicators
        self.I_ema_fast = self.I(lambda: self.ema_fast_full)
        self.I_ema_slow = self.I(lambda: self.ema_slow_full)
        self.I_atr = self.I(lambda: self.atr_full)
        self.I_upper = self.I(lambda: self.upper_channel)
        self.I_lower = self.I(lambda: self.lower_channel)
        self.I_trend = self.I(lambda: self.trend)
        self.I_adx = self.I(lambda: self.adx_full)
        self.I_plus_di = self.I(lambda: self.plus_di_full)
        self.I_minus_di = self.I(lambda: self.minus_di_full)

    def next(self):
        """Trading logic with ADX filtering"""
        # Skip if not enough data
        if len(self.data) < max(self.ema_slow, self.adx_period) + 10:
            return

        # Get current values
        idx = len(self.data) - 1
        if idx < 0 or idx >= len(self.ema_fast_full):
            return

        current_price = self.data.Close[-1]
        current_trend = self.trend[idx]
        prev_trend = self.trend[idx-1] if idx > 0 else 0

        # Get ADX values
        current_adx = self.adx_full[idx]
        current_plus_di = self.plus_di_full[idx]
        current_minus_di = self.minus_di_full[idx]

        # Skip if any indicator is NaN
        if np.isnan(self.ema_fast_full[idx]) or np.isnan(self.atr_full[idx]) or np.isnan(current_adx):
            return

        # Position management
        if not self.position:
            # Long entry conditions with ADX filter
            if current_trend > 0 and current_adx > self.adx_threshold and current_plus_di > current_minus_di:
                enter_long = False

                # Trend change signal
                if prev_trend <= 0:
                    enter_long = True

                # Channel bounce signal
                if (self.data.Low[-1] <= self.lower_channel[idx] and
                    current_price > self.lower_channel[idx]):
                    enter_long = True

                # Breakout signal with strong ADX
                if (idx > 1 and current_price > self.upper_channel[idx] and
                    self.data.Close[-2] <= self.upper_channel[idx-1] and
                    current_adx > 30):  # Extra strong trend for breakouts
                    enter_long = True

                if enter_long:
                    # Adjust position size based on ADX strength
                    # Higher ADX = stronger trend = larger position
                    adx_multiplier = min(current_adx / 25, 2.0)  # Scale from 1x to 2x

                    # Calculate stops with ADX adjustment
                    atr_stop = self.atr_full[idx] * (2.5 - adx_multiplier * 0.5)  # Tighter stops for stronger trends
                    sl = max(current_price - atr_stop, current_price * (1 - self.stop_loss_pct))
                    tp = current_price * (1 + self.take_profit_pct * adx_multiplier)  # Larger targets for stronger trends

                    self.buy(size=0.95, sl=sl, tp=tp)

            # Short entry conditions with ADX filter
            elif current_trend < 0 and current_adx > self.adx_threshold and current_minus_di > current_plus_di:
                enter_short = False

                # Trend change signal
                if prev_trend >= 0:
                    enter_short = True

                # Channel rejection signal
                if (self.data.High[-1] >= self.upper_channel[idx] and
                    current_price < self.upper_channel[idx]):
                    enter_short = True

                # Breakdown signal with strong ADX
                if (idx > 1 and current_price < self.lower_channel[idx] and
                    self.data.Close[-2] >= self.lower_channel[idx-1] and
                    current_adx > 30):  # Extra strong trend for breakdowns
                    enter_short = True

                if enter_short:
                    # Adjust position size based on ADX strength
                    adx_multiplier = min(current_adx / 25, 2.0)

                    # Calculate stops with ADX adjustment
                    atr_stop = self.atr_full[idx] * (2.5 - adx_multiplier * 0.5)
                    sl = min(current_price + atr_stop, current_price * (1 + self.stop_loss_pct))
                    tp = current_price * (1 - self.take_profit_pct * adx_multiplier)

                    self.sell(size=0.95, sl=sl, tp=tp)

        else:
            # Exit management with ADX
            if self.position.is_long:
                # Exit if trend turns bearish or ADX drops (trend weakening)
                if current_trend < 0 or current_adx < 20:
                    self.position.close()
                # Exit if DI crosses bearish
                elif current_minus_di > current_plus_di:
                    self.position.close()
                # Exit if price closes below lower channel
                elif current_price < self.lower_channel[idx]:
                    self.position.close()

            else:  # Short position
                # Exit if trend turns bullish or ADX drops
                if current_trend > 0 or current_adx < 20:
                    self.position.close()
                # Exit if DI crosses bullish
                elif current_plus_di > current_minus_di:
                    self.position.close()
                # Exit if price closes above upper channel
                elif current_price > self.upper_channel[idx]:
                    self.position.close()

# Run single backtest
bt = Backtest(data, TrendImpulseADXCombo, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND IMPULSE + ADX COMBO - PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"Fast EMA: {EMA_FAST}")
print(f"Slow EMA: {EMA_SLOW}")
print(f"ATR Channel: {ATR_CHANNEL}x")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Threshold: {ADX_THRESHOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND IMPULSE + ADX COMBO ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendImpulseADXCombo, 'TrendImpulseADXCombo')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendImpulseADXCombo.csv")