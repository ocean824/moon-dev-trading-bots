import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from datetime import time

print("🚀 Moon Dev's Bull vs Bear Sessions + MFI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
SESSION_HOURS = [6, 12, 18, 24]  # Session boundaries (0-6, 6-12, 12-18, 18-24)
VOLUME_PERCENTILE = 70  # Percentile for Value Area calculation
MIN_SESSION_VOLUME = 50  # Minimum volume percentile for valid signals
DELTA_THRESHOLD = 0.55  # 55% bull volume for bullish bias
MFI_PERIOD = 14
MFI_OVERSOLD = 30
MFI_OVERBOUGHT = 70
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class BullBearSessionsMFI(Strategy):
    """
    Bull vs Bear Market Sessions + Money Flow Index Strategy

    This strategy combines session-based volume profile analysis with MFI
    to confirm volume-based signals with money flow momentum.
    MFI helps filter out false signals and confirm true buying/selling pressure.
    """

    # Strategy parameters
    session_hours = SESSION_HOURS
    volume_percentile = VOLUME_PERCENTILE
    min_session_volume = MIN_SESSION_VOLUME
    delta_threshold = DELTA_THRESHOLD
    mfi_period = MFI_PERIOD
    mfi_oversold = MFI_OVERSOLD
    mfi_overbought = MFI_OVERBOUGHT
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        # Calculate session-based indicators
        def calculate_session_profile(high, low, close, open_, volume):
            """
            Calculate volume profiles for each trading session
            Returns arrays of POC, bull percentage, and session strength
            """
            n = len(high)
            poc_levels = np.zeros(n)
            bull_percentages = np.zeros(n)
            session_strengths = np.zeros(n)
            value_area_highs = np.zeros(n)
            value_area_lows = np.zeros(n)
            delta_values = np.zeros(n)  # Bull volume - Bear volume

            for i in range(24, n):  # Need at least 24 hours (1 day) of data
                # Determine current session (0-3 based on hour)
                current_hour = i % 24
                current_session = min(current_hour // 6, 3)

                # Get session data (last 6 hours for current session)
                session_start = i - (current_hour % 6) - 6
                session_end = i

                if session_start < 0:
                    continue

                # Extract session data
                session_high = high[session_start:session_end+1]
                session_low = low[session_start:session_end+1]
                session_close = close[session_start:session_end+1]
                session_open = open_[session_start:session_end+1]
                session_volume = volume[session_start:session_end+1]

                if len(session_high) == 0:
                    continue

                # Create volume profile with 10 price bins
                price_range_high = np.max(session_high)
                price_range_low = np.min(session_low)

                if price_range_high == price_range_low:
                    poc_levels[i] = price_range_high
                    bull_percentages[i] = 0.5
                    delta_values[i] = 0
                    continue

                # Create price bins
                bins = np.linspace(price_range_low, price_range_high, 11)
                bin_volumes = np.zeros(10)
                bin_bull_volumes = np.zeros(10)
                bin_bear_volumes = np.zeros(10)

                # Distribute volume across bins
                for j in range(len(session_high)):
                    # Determine if this candle was bullish or bearish
                    is_bullish = session_close[j] >= session_open[j]
                    candle_volume = session_volume[j]

                    # Find which bins this candle touched
                    candle_low = session_low[j]
                    candle_high = session_high[j]

                    for k in range(10):
                        bin_low = bins[k]
                        bin_high = bins[k + 1]

                        # Check if candle overlaps with this bin
                        if candle_high >= bin_low and candle_low <= bin_high:
                            # Calculate overlap percentage
                            overlap_low = max(candle_low, bin_low)
                            overlap_high = min(candle_high, bin_high)
                            overlap_range = overlap_high - overlap_low
                            candle_range = candle_high - candle_low if candle_high > candle_low else 0.0001

                            # Distribute volume proportionally
                            volume_portion = candle_volume * (overlap_range / candle_range)
                            bin_volumes[k] += volume_portion

                            if is_bullish:
                                bin_bull_volumes[k] += volume_portion
                            else:
                                bin_bear_volumes[k] += volume_portion

                # Find Point of Control (bin with highest volume)
                if np.sum(bin_volumes) > 0:
                    poc_bin = np.argmax(bin_volumes)
                    poc_price = (bins[poc_bin] + bins[poc_bin + 1]) / 2
                    poc_levels[i] = poc_price

                    # Calculate bull percentage and delta at POC
                    if bin_volumes[poc_bin] > 0:
                        bull_percentages[i] = bin_bull_volumes[poc_bin] / bin_volumes[poc_bin]
                        total_bull = np.sum(bin_bull_volumes)
                        total_bear = np.sum(bin_bear_volumes)
                        total_vol = total_bull + total_bear
                        if total_vol > 0:
                            delta_values[i] = (total_bull - total_bear) / total_vol
                    else:
                        bull_percentages[i] = 0.5
                        delta_values[i] = 0

                    # Calculate Value Area (70% of volume)
                    total_volume = np.sum(bin_volumes)
                    target_volume = total_volume * self.volume_percentile / 100

                    # Expand from POC until we reach target volume
                    va_bins = [poc_bin]
                    va_volume = bin_volumes[poc_bin]

                    left_idx = poc_bin - 1
                    right_idx = poc_bin + 1

                    while va_volume < target_volume and (left_idx >= 0 or right_idx < 10):
                        left_vol = bin_volumes[left_idx] if left_idx >= 0 else 0
                        right_vol = bin_volumes[right_idx] if right_idx < 10 else 0

                        if left_vol > right_vol and left_idx >= 0:
                            va_bins.append(left_idx)
                            va_volume += left_vol
                            left_idx -= 1
                        elif right_idx < 10:
                            va_bins.append(right_idx)
                            va_volume += right_vol
                            right_idx += 1
                        else:
                            break

                    # Set Value Area boundaries
                    va_bin_min = min(va_bins)
                    va_bin_max = max(va_bins)
                    value_area_lows[i] = bins[va_bin_min]
                    value_area_highs[i] = bins[va_bin_max + 1] if va_bin_max < 9 else bins[10]

                    # Calculate session strength (volume relative to average)
                    avg_volume = np.mean(volume[max(0, i-96):i])  # 96 hours = 4 days
                    if avg_volume > 0:
                        session_strengths[i] = total_volume / (avg_volume * 6)  # Normalized by session length
                    else:
                        session_strengths[i] = 1.0
                else:
                    poc_levels[i] = close[i]
                    bull_percentages[i] = 0.5
                    delta_values[i] = 0
                    value_area_highs[i] = high[i]
                    value_area_lows[i] = low[i]
                    session_strengths[i] = 1.0

            return poc_levels, bull_percentages, session_strengths, value_area_highs, value_area_lows, delta_values

        # Calculate session profiles
        poc, bull_pct, strength, va_high, va_low, delta = calculate_session_profile(
            self.data.High,
            self.data.Low,
            self.data.Close,
            self.data.Open,
            self.data.Volume
        )

        self.poc_levels = self.I(lambda: poc, name="POC")
        self.bull_percentages = self.I(lambda: bull_pct, name="Bull%")
        self.session_strengths = self.I(lambda: strength, name="Strength")
        self.value_area_highs = self.I(lambda: va_high, name="VA_High")
        self.value_area_lows = self.I(lambda: va_low, name="VA_Low")
        self.delta_values = self.I(lambda: delta, name="Delta")

        # Calculate Money Flow Index
        self.mfi = self.I(talib.MFI,
                          self.data.High,
                          self.data.Low,
                          self.data.Close,
                          self.data.Volume,
                          timeperiod=self.mfi_period)

        # Volume filter
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=24)

        # Calculate session transitions with MFI confirmation
        def detect_confirmed_transitions(bull_pct, mfi, threshold, mfi_os, mfi_ob):
            """Detect session transitions confirmed by MFI"""
            transitions = np.zeros(len(bull_pct))

            for i in range(6, len(bull_pct)):
                prev_bull = bull_pct[i-6] > threshold
                curr_bull = bull_pct[i] > threshold
                mfi_val = mfi[i] if not np.isnan(mfi[i]) else 50

                if not prev_bull and curr_bull and mfi_val < mfi_ob:
                    # Bear to Bull transition confirmed by MFI not overbought
                    transitions[i] = 1
                elif prev_bull and not curr_bull and mfi_val > mfi_os:
                    # Bull to Bear transition confirmed by MFI not oversold
                    transitions[i] = -1

            return transitions

        self.confirmed_transitions = self.I(
            lambda: detect_confirmed_transitions(
                bull_pct, self.mfi, self.delta_threshold,
                self.mfi_oversold, self.mfi_overbought
            ),
            name="ConfirmedTransitions"
        )

    def next(self):
        # Skip if not enough data
        if len(self.data) < 96 or np.isnan(self.mfi[-1]):
            return

        # Get current values
        current_price = self.data.Close[-1]
        current_poc = self.poc_levels[-1]
        current_bull_pct = self.bull_percentages[-1]
        current_strength = self.session_strengths[-1]
        current_transition = self.confirmed_transitions[-1]
        current_volume = self.data.Volume[-1]
        current_mfi = self.mfi[-1]
        current_delta = self.delta_values[-1]
        va_high = self.value_area_highs[-1]
        va_low = self.value_area_lows[-1]

        # Volume filter - only trade on significant volume
        if current_volume < self.volume_ma[-1] * (self.min_session_volume / 100):
            return

        # Position management
        if not self.position:
            # Entry logic with MFI confirmation

            # Long Entry: Bear to Bull transition with MFI confirmation
            if current_transition == 1 and current_strength > 1.0:
                if current_price <= current_poc * 1.005 and current_mfi < self.mfi_oversold + 10:
                    # Strong bull session starting, MFI shows oversold/recovery
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)
                    self.buy(sl=sl_price, tp=tp_price)

            # Short Entry: Bull to Bear transition with MFI confirmation
            elif current_transition == -1 and current_strength > 1.0:
                if current_price >= current_poc * 0.995 and current_mfi > self.mfi_overbought - 10:
                    # Strong bear session starting, MFI shows overbought/decline
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)
                    self.sell(sl=sl_price, tp=tp_price)

            # MFI divergence entries
            elif current_bull_pct > 0.65 and current_delta > 0.2:
                # Bullish session with positive delta
                if current_mfi < self.mfi_oversold and current_price < current_poc:
                    # MFI oversold in bullish session - strong buy signal
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)
                    self.buy(sl=sl_price, tp=tp_price)

            elif current_bull_pct < 0.35 and current_delta < -0.2:
                # Bearish session with negative delta
                if current_mfi > self.mfi_overbought and current_price > current_poc:
                    # MFI overbought in bearish session - strong sell signal
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)
                    self.sell(sl=sl_price, tp=tp_price)

            # MFI extreme entries with volume confirmation
            elif current_mfi < self.mfi_oversold - 5 and current_strength > 1.2:
                if current_bull_pct > 0.5 and current_price <= current_poc:
                    # Extreme oversold with bullish volume profile
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)
                    self.buy(sl=sl_price, tp=tp_price)

            elif current_mfi > self.mfi_overbought + 5 and current_strength > 1.2:
                if current_bull_pct < 0.5 and current_price >= current_poc:
                    # Extreme overbought with bearish volume profile
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)
                    self.sell(sl=sl_price, tp=tp_price)

        else:
            # Dynamic exit based on MFI and session changes
            if self.position.is_long:
                # Exit long if MFI becomes extremely overbought or session turns bearish
                if current_mfi > self.mfi_overbought + 10 or (current_bull_pct < 0.35 and current_transition == -1):
                    self.position.close()

            else:  # Short position
                # Exit short if MFI becomes extremely oversold or session turns bullish
                if current_mfi < self.mfi_oversold - 10 or (current_bull_pct > 0.65 and current_transition == 1):
                    self.position.close()

# Run single backtest
bt = Backtest(data, BullBearSessionsMFI, cash=1000000, commission=0.00045)

print("\n🌙 ===== BULL VS BEAR SESSIONS + MFI - DEFAULT PARAMETERS ===== 🌙")
print(f"Session Hours: {SESSION_HOURS}")
print(f"Volume Percentile: {VOLUME_PERCENTILE}%")
print(f"Delta Threshold: {DELTA_THRESHOLD}")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Oversold: {MFI_OVERSOLD}")
print(f"MFI Overbought: {MFI_OVERBOUGHT}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING BULL VS BEAR SESSIONS + MFI ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(BullBearSessionsMFI, 'BullBearSessionsMFI')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/BullBearSessionsMFI.csv")