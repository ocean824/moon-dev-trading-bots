"""
Moon Dev's Trend Impulse + MFI Combination Strategy
===================================================
Combines Trend Impulse Channels with Money Flow Index for volume-weighted signals.
Uses MFI divergences and money flow strength for trade confirmation.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Impulse + MFI Combo Strategy Loading... 🌙")

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ATR_PERIOD = 14
EMA_FAST = 12
EMA_SLOW = 26
ATR_CHANNEL = 2.0
MFI_PERIOD = 14
MFI_OVERBOUGHT = 80
MFI_OVERSOLD = 20
MFI_STRONG = 60  # Above this = strong money flow
MFI_WEAK = 40    # Below this = weak money flow

# Risk management
TAKE_PROFIT_PERCENT = 3.5
STOP_LOSS_PERCENT = 1.5

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendImpulseMFICombo(Strategy):
    """
    Trend Impulse + MFI Combination Strategy

    Entry Conditions:
    - Long: Trend Impulse bullish + MFI oversold or bullish divergence
    - Short: Trend Impulse bearish + MFI overbought or bearish divergence

    Volume-weighted position sizing based on MFI strength.
    """

    # Parameters
    atr_period = ATR_PERIOD
    ema_fast = EMA_FAST
    ema_slow = EMA_SLOW
    atr_channel = ATR_CHANNEL
    mfi_period = MFI_PERIOD
    mfi_overbought = MFI_OVERBOUGHT
    mfi_oversold = MFI_OVERSOLD
    mfi_strong = MFI_STRONG
    mfi_weak = MFI_WEAK
    take_profit_pct = TAKE_PROFIT_PERCENT / 100
    stop_loss_pct = STOP_LOSS_PERCENT / 100

    def init(self):
        """Initialize indicators"""
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate EMAs for Trend Impulse
        ema_fast = ta.ema(close, length=self.ema_fast)
        ema_slow = ta.ema(close, length=self.ema_slow)

        # Calculate ATR for channels
        atr = ta.atr(high, low, close, length=self.atr_period)

        # Calculate MFI
        mfi = ta.mfi(high, low, close, volume, length=self.mfi_period)

        # Calculate MFI moving average for divergence detection
        mfi_ma = ta.sma(mfi, length=5) if mfi is not None else None

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

        self.mfi_full = np.full(len(close), np.nan)
        if mfi is not None:
            self.mfi_full[-len(mfi):] = mfi.values

        self.mfi_ma_full = np.full(len(close), np.nan)
        if mfi_ma is not None:
            self.mfi_ma_full[-len(mfi_ma):] = mfi_ma.values

        # Calculate trend direction
        self.trend = np.where(self.ema_fast_full > self.ema_slow_full, 1, -1)

        # Calculate ATR channels
        self.upper_channel = self.ema_slow_full + (self.atr_full * self.atr_channel)
        self.lower_channel = self.ema_slow_full - (self.atr_full * self.atr_channel)

        # Detect MFI divergences (simplified)
        self.mfi_divergence = np.zeros(len(close))
        for i in range(10, len(close)):
            if not np.isnan(self.mfi_full[i]) and not np.isnan(self.mfi_full[i-5]):
                # Bullish divergence: price makes lower low, MFI makes higher low
                if close.iloc[i] < close.iloc[i-5] and self.mfi_full[i] > self.mfi_full[i-5]:
                    self.mfi_divergence[i] = 1
                # Bearish divergence: price makes higher high, MFI makes lower high
                elif close.iloc[i] > close.iloc[i-5] and self.mfi_full[i] < self.mfi_full[i-5]:
                    self.mfi_divergence[i] = -1

        # Store as indicators
        self.I_ema_fast = self.I(lambda: self.ema_fast_full)
        self.I_ema_slow = self.I(lambda: self.ema_slow_full)
        self.I_atr = self.I(lambda: self.atr_full)
        self.I_upper = self.I(lambda: self.upper_channel)
        self.I_lower = self.I(lambda: self.lower_channel)
        self.I_trend = self.I(lambda: self.trend)
        self.I_mfi = self.I(lambda: self.mfi_full)
        self.I_mfi_div = self.I(lambda: self.mfi_divergence)

    def next(self):
        """Trading logic with MFI confirmation"""
        # Skip if not enough data
        if len(self.data) < max(self.ema_slow, self.mfi_period) + 10:
            return

        # Get current values
        idx = len(self.data) - 1
        if idx < 0 or idx >= len(self.ema_fast_full):
            return

        current_price = self.data.Close[-1]
        current_trend = self.trend[idx]
        prev_trend = self.trend[idx-1] if idx > 0 else 0
        current_mfi = self.mfi_full[idx]
        current_divergence = self.mfi_divergence[idx]

        # Skip if any indicator is NaN
        if np.isnan(self.ema_fast_full[idx]) or np.isnan(self.atr_full[idx]) or np.isnan(current_mfi):
            return

        # Position management
        if not self.position:
            # Long entry conditions with MFI confirmation
            if current_trend > 0:  # Bullish trend
                enter_long = False

                # Strong entry: Trend change + MFI oversold
                if prev_trend <= 0 and current_mfi < self.mfi_oversold:
                    enter_long = True

                # Channel bounce + MFI not overbought
                if (self.data.Low[-1] <= self.lower_channel[idx] and
                    current_price > self.lower_channel[idx] and
                    current_mfi < self.mfi_overbought):
                    enter_long = True

                # Bullish divergence signal
                if current_divergence > 0:
                    enter_long = True

                # Breakout with strong money flow
                if (idx > 1 and current_price > self.upper_channel[idx] and
                    self.data.Close[-2] <= self.upper_channel[idx-1] and
                    current_mfi > self.mfi_strong):
                    enter_long = True

                if enter_long:
                    # Volume-weighted position sizing based on MFI
                    # Higher MFI = stronger money flow = larger position
                    if current_mfi < 30:
                        size_multiplier = 1.2  # Oversold = larger position
                    elif current_mfi > 70:
                        size_multiplier = 0.8  # Overbought = smaller position
                    else:
                        size_multiplier = 1.0

                    # Calculate stops
                    atr_stop = self.atr_full[idx] * 2.0
                    sl = max(current_price - atr_stop, current_price * (1 - self.stop_loss_pct))
                    tp = current_price * (1 + self.take_profit_pct)

                    self.buy(size=min(0.95, 0.95 * size_multiplier), sl=sl, tp=tp)

            # Short entry conditions with MFI confirmation
            elif current_trend < 0:  # Bearish trend
                enter_short = False

                # Strong entry: Trend change + MFI overbought
                if prev_trend >= 0 and current_mfi > self.mfi_overbought:
                    enter_short = True

                # Channel rejection + MFI not oversold
                if (self.data.High[-1] >= self.upper_channel[idx] and
                    current_price < self.upper_channel[idx] and
                    current_mfi > self.mfi_oversold):
                    enter_short = True

                # Bearish divergence signal
                if current_divergence < 0:
                    enter_short = True

                # Breakdown with weak money flow
                if (idx > 1 and current_price < self.lower_channel[idx] and
                    self.data.Close[-2] >= self.lower_channel[idx-1] and
                    current_mfi < self.mfi_weak):
                    enter_short = True

                if enter_short:
                    # Volume-weighted position sizing
                    if current_mfi > 70:
                        size_multiplier = 1.2  # Overbought = larger short position
                    elif current_mfi < 30:
                        size_multiplier = 0.8  # Oversold = smaller short position
                    else:
                        size_multiplier = 1.0

                    # Calculate stops
                    atr_stop = self.atr_full[idx] * 2.0
                    sl = min(current_price + atr_stop, current_price * (1 + self.stop_loss_pct))
                    tp = current_price * (1 - self.take_profit_pct)

                    self.sell(size=min(0.95, 0.95 * size_multiplier), sl=sl, tp=tp)

        else:
            # Exit management with MFI
            if self.position.is_long:
                # Exit if trend turns bearish
                if current_trend < 0:
                    self.position.close()
                # Exit if MFI extremely overbought (profit taking)
                elif current_mfi > 85:
                    self.position.close()
                # Exit if bearish divergence forms
                elif current_divergence < 0:
                    self.position.close()
                # Exit if price closes below lower channel
                elif current_price < self.lower_channel[idx]:
                    self.position.close()

            else:  # Short position
                # Exit if trend turns bullish
                if current_trend > 0:
                    self.position.close()
                # Exit if MFI extremely oversold (profit taking)
                elif current_mfi < 15:
                    self.position.close()
                # Exit if bullish divergence forms
                elif current_divergence > 0:
                    self.position.close()
                # Exit if price closes above upper channel
                elif current_price > self.upper_channel[idx]:
                    self.position.close()

# Run single backtest
bt = Backtest(data, TrendImpulseMFICombo, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND IMPULSE + MFI COMBO - PARAMETERS ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"Fast EMA: {EMA_FAST}")
print(f"Slow EMA: {EMA_SLOW}")
print(f"ATR Channel: {ATR_CHANNEL}x")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Overbought: {MFI_OVERBOUGHT}")
print(f"MFI Oversold: {MFI_OVERSOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND IMPULSE + MFI COMBO ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendImpulseMFICombo, 'TrendImpulseMFICombo')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendImpulseMFICombo.csv")