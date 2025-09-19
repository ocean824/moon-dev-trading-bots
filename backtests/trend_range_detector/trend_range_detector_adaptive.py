"""
Moon Dev's Trend Range Detector with Adaptive ATR Strategy
===========================================================
Dynamically adjusts ATR multiplier based on market volatility conditions.
Tighter ranges in low volatility, wider ranges in high volatility.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Range Detector Adaptive Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
WMA_PERIOD = 20
ATR_PERIOD = 14
BASE_ATR_MULTIPLIER = 1.5  # Base multiplier, will be adapted (reduced)
MIN_ATR_MULTIPLIER = 1.0  # Minimum multiplier in low volatility (reduced)
MAX_ATR_MULTIPLIER = 2.5  # Maximum multiplier in high volatility (reduced)
VOLATILITY_LOOKBACK = 50  # Bars to measure volatility regime
VOLATILITY_PERCENTILE = 30  # Percentile thresholds for regime detection
MIN_RANGE_LENGTH = 30  # Reduced for more signals
BREAKOUT_CONFIRM_BARS = 2
ADAPTIVE_SPEED = 0.1  # How quickly multiplier adapts (0-1)
STOP_LOSS_PERCENT = 2.0
TAKE_PROFIT_PERCENT = 4.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendRangeDetectorAdaptive(Strategy):
    """
    Trend Range Detector with Adaptive ATR Multiplier
    - Measures market volatility regime continuously
    - Adjusts ATR multiplier based on volatility conditions
    - Uses historical volatility percentiles for adaptation
    - Tighter ranges in trending markets, wider in choppy markets
    - Dynamic risk management based on volatility
    """

    # Core parameters
    wma_period = WMA_PERIOD
    atr_period = ATR_PERIOD
    base_atr_multiplier = BASE_ATR_MULTIPLIER
    min_atr_multiplier = MIN_ATR_MULTIPLIER
    max_atr_multiplier = MAX_ATR_MULTIPLIER
    min_range_length = MIN_RANGE_LENGTH
    breakout_confirm = BREAKOUT_CONFIRM_BARS

    # Adaptive parameters
    volatility_lookback = VOLATILITY_LOOKBACK
    volatility_percentile = VOLATILITY_PERCENTILE
    adaptive_speed = ADAPTIVE_SPEED

    # Risk management
    stop_loss_pct = STOP_LOSS_PERCENT / 100
    take_profit_pct = TAKE_PROFIT_PERCENT / 100

    def calculate_weighted_ma(self, prices):
        """Calculate custom weighted moving average"""
        wma = np.zeros(len(prices))

        for i in range(self.wma_period, len(prices)):
            weights = np.arange(1, self.wma_period + 1)
            window = prices[i - self.wma_period + 1:i + 1]
            wma[i] = np.sum(window * weights) / np.sum(weights)

        return wma

    def calculate_volatility_regime(self, atr_values, prices):
        """
        Calculate volatility regime and adaptive multiplier
        Returns: volatility_regime (array), adaptive_multipliers (array)
        """
        volatility_regime = np.zeros(len(atr_values))
        adaptive_multipliers = np.full(len(atr_values), self.base_atr_multiplier)

        # Calculate returns for additional volatility measure
        returns = np.zeros(len(prices))
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                returns[i] = (prices[i] - prices[i-1]) / prices[i-1]

        for i in range(self.volatility_lookback, len(atr_values)):
            # Get recent ATR values
            recent_atr = atr_values[i - self.volatility_lookback:i]
            recent_atr = recent_atr[~np.isnan(recent_atr)]

            if len(recent_atr) < 10:
                continue

            # Calculate volatility metrics
            current_atr = atr_values[i]
            atr_mean = np.mean(recent_atr)
            atr_std = np.std(recent_atr)

            # Calculate return volatility
            recent_returns = returns[i - self.volatility_lookback:i]
            return_vol = np.std(recent_returns) if len(recent_returns) > 0 else 0

            # Determine volatility regime (0=low, 1=normal, 2=high)
            if current_atr < np.percentile(recent_atr, self.volatility_percentile):
                volatility_regime[i] = 0  # Low volatility
            elif current_atr > np.percentile(recent_atr, 100 - self.volatility_percentile):
                volatility_regime[i] = 2  # High volatility
            else:
                volatility_regime[i] = 1  # Normal volatility

            # Calculate adaptive multiplier
            # In low volatility, use smaller multiplier (tighter ranges)
            # In high volatility, use larger multiplier (wider ranges)
            if atr_mean > 0:
                volatility_ratio = current_atr / atr_mean
            else:
                volatility_ratio = 1.0

            # Add return volatility influence
            if return_vol > 0:
                vol_influence = min(2.0, return_vol * 100)  # Scale return vol
                volatility_ratio = (volatility_ratio + vol_influence) / 2

            # Calculate target multiplier based on volatility
            if volatility_regime[i] == 0:  # Low volatility
                target_multiplier = self.min_atr_multiplier + (self.base_atr_multiplier - self.min_atr_multiplier) * 0.3
            elif volatility_regime[i] == 2:  # High volatility
                target_multiplier = self.base_atr_multiplier + (self.max_atr_multiplier - self.base_atr_multiplier) * 0.7
            else:  # Normal volatility
                target_multiplier = self.base_atr_multiplier

            # Adjust target based on volatility ratio
            target_multiplier *= volatility_ratio

            # Clamp to min/max bounds
            target_multiplier = max(self.min_atr_multiplier, min(self.max_atr_multiplier, target_multiplier))

            # Smooth adaptation (EMA-like smoothing)
            if i > 0:
                adaptive_multipliers[i] = (
                    adaptive_multipliers[i-1] * (1 - self.adaptive_speed) +
                    target_multiplier * self.adaptive_speed
                )
            else:
                adaptive_multipliers[i] = target_multiplier

        return volatility_regime, adaptive_multipliers

    def detect_adaptive_ranges(self, prices, highs, lows, atr, adaptive_multipliers):
        """Detect ranges using adaptive ATR multipliers"""
        ranges = []
        in_range = False
        range_start = 0
        range_center = 0
        range_top = 0
        range_bottom = 0
        range_multiplier = self.base_atr_multiplier

        wma = self.calculate_weighted_ma(prices)

        for i in range(max(self.atr_period + self.wma_period, self.volatility_lookback), len(prices)):
            if atr[i] == 0 or np.isnan(atr[i]):
                continue

            # Use adaptive multiplier for this bar
            current_multiplier = adaptive_multipliers[i]
            current_center = wma[i]
            current_range = atr[i] * current_multiplier
            current_top = current_center + current_range / 2
            current_bottom = current_center - current_range / 2

            # More lenient range detection using close price
            price_in_range = current_bottom <= prices[i] <= current_top

            if not in_range and price_in_range:
                in_range = True
                range_start = i
                range_center = current_center
                range_top = current_top
                range_bottom = current_bottom
                range_multiplier = current_multiplier
                range_count = 1

            elif in_range:
                if price_in_range:
                    range_count += 1
                    # Adapt range boundaries based on current multiplier
                    adapt_factor = 0.1
                    range_center = (range_center * (1 - adapt_factor) + current_center * adapt_factor)

                    # Allow range to expand/contract based on volatility
                    new_range = atr[i] * current_multiplier
                    new_top = range_center + new_range / 2
                    new_bottom = range_center - new_range / 2

                    # Smooth transition
                    range_top = range_top * 0.9 + new_top * 0.1
                    range_bottom = range_bottom * 0.9 + new_bottom * 0.1
                    range_multiplier = range_multiplier * 0.9 + current_multiplier * 0.1

                    # Check if we have enough bars and potential breakout
                    if range_count >= self.min_range_length:
                        if prices[i] > range_top * 0.98 or prices[i] < range_bottom * 1.02:
                            ranges.append({
                                'start': range_start,
                                'end': i,
                                'center': range_center,
                                'top': range_top,
                                'bottom': range_bottom,
                                'length': range_count,
                                'multiplier': range_multiplier,
                                'volatility': adaptive_multipliers[i]
                            })
                            in_range = False
                else:
                    if range_count >= self.min_range_length:
                        ranges.append({
                            'start': range_start,
                            'end': i,
                            'center': range_center,
                            'top': range_top,
                            'bottom': range_bottom,
                            'length': range_length,
                            'multiplier': range_multiplier,
                            'volatility': adaptive_multipliers[i]
                        })
                    in_range = False

        return ranges

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Calculate ATR
        atr = ta.atr(high, low, close, length=self.atr_period)
        atr_full = np.full(len(close), np.nan)
        atr_full[-len(atr):] = atr.values

        # Calculate volatility regime and adaptive multipliers
        volatility_regime, adaptive_multipliers = self.calculate_volatility_regime(
            atr_full, close.values
        )

        # Detect ranges with adaptive multipliers
        ranges = self.detect_adaptive_ranges(
            close.values, high.values, low.values, atr_full, adaptive_multipliers
        )

        # Create signals
        self.signal = np.zeros(len(close))
        self.volatility_state = volatility_regime
        self.adaptive_mult = adaptive_multipliers
        self.range_top = np.full(len(close), np.nan)
        self.range_bottom = np.full(len(close), np.nan)
        self.range_center = np.full(len(close), np.nan)

        # Mark range boundaries and breakouts
        for r in ranges:
            for j in range(r['start'], r['end']):
                self.range_top[j] = r['top']
                self.range_bottom[j] = r['bottom']
                self.range_center[j] = r['center']

            if r['end'] < len(close):
                end_price = close.iloc[r['end']]
                # Adjust confirmation requirements based on volatility
                vol_state = volatility_regime[r['end']]
                confirm_bars = self.breakout_confirm
                if vol_state == 2:  # High volatility needs more confirmation
                    confirm_bars += 1

                # Simplified breakout detection
                if end_price > r['top']:
                    # Confirm breakout
                    confirmed = True
                    for k in range(1, min(confirm_bars, len(close) - r['end'])):
                        if close.iloc[r['end'] + k] < r['top'] * 0.995:
                            confirmed = False
                            break
                    breakout = confirmed
                else:
                    breakout = False

                if breakout:
                    # Strength based on volatility regime
                    signal_strength = 1.0
                    if vol_state == 0:  # Low vol breakouts are stronger
                        signal_strength = 1.2
                    elif vol_state == 2:  # High vol breakouts need caution
                        signal_strength = 0.8

                    self.signal[r['end']] = signal_strength

                # Simplified breakdown detection
                if end_price < r['bottom']:
                    # Confirm breakdown
                    confirmed = True
                    for k in range(1, min(confirm_bars, len(close) - r['end'])):
                        if close.iloc[r['end'] + k] > r['bottom'] * 1.005:
                            confirmed = False
                            break
                    breakdown = confirmed
                else:
                    breakdown = False

                if breakdown:
                    signal_strength = -1.0
                    if vol_state == 0:
                        signal_strength = -1.2
                    elif vol_state == 2:
                        signal_strength = -0.8

                    self.signal[r['end']] = signal_strength

        # Store indicators
        self.I(lambda: self.signal, name='Signal')
        self.I(lambda: self.volatility_state, name='VolatilityRegime')
        self.I(lambda: self.adaptive_mult, name='AdaptiveMultiplier')
        self.I(lambda: self.range_top, name='RangeTop')
        self.I(lambda: self.range_bottom, name='RangeBottom')

    def next(self):
        current_signal = self.signal[-1] if len(self.signal) > 0 else 0
        current_price = self.data.Close[-1]
        current_vol_state = self.volatility_state[-1] if len(self.volatility_state) > 0 else 1
        current_multiplier = self.adaptive_mult[-1] if len(self.adaptive_mult) > 0 else self.base_atr_multiplier

        # Dynamic position sizing based on volatility regime
        position_size = 1000000

        # Adjust size based on volatility state
        if current_vol_state == 0:  # Low volatility - can use larger size
            position_size *= 1.25
        elif current_vol_state == 2:  # High volatility - reduce size
            position_size *= 0.75

        # Further adjust based on multiplier
        multiplier_ratio = current_multiplier / self.base_atr_multiplier
        position_size *= max(0.5, min(1.5, 1.0 / multiplier_ratio))

        # Adjust for range width
        if not np.isnan(self.range_top[-1]) and not np.isnan(self.range_bottom[-1]):
            range_width = (self.range_top[-1] - self.range_bottom[-1]) / self.range_bottom[-1]
            position_size *= max(0.5, min(2.0, 1.0 / (1 + range_width * 10)))

        # Entry logic with adaptive stops
        if not self.position:
            if current_signal > 0:
                # Long entry
                # Adjust stops based on volatility
                stop_distance_multiplier = 1.0
                profit_multiplier = 1.0

                if current_vol_state == 0:  # Tight stops in low vol
                    stop_distance_multiplier = 0.7
                    profit_multiplier = 1.5
                elif current_vol_state == 2:  # Wider stops in high vol
                    stop_distance_multiplier = 1.3
                    profit_multiplier = 2.0

                if not np.isnan(self.range_center[-1]):
                    stop_distance = (self.range_center[-1] - self.range_bottom[-1]) * stop_distance_multiplier
                    sl_price = self.range_center[-1] - stop_distance
                    tp_price = current_price + (current_price - self.range_bottom[-1]) * profit_multiplier
                else:
                    sl_price = current_price * (1 - self.stop_loss_pct * stop_distance_multiplier)
                    tp_price = current_price * (1 + self.take_profit_pct * profit_multiplier)

                self.buy(size=position_size * abs(current_signal), sl=sl_price, tp=tp_price)

            elif current_signal < 0:
                # Short entry
                stop_distance_multiplier = 1.0
                profit_multiplier = 1.0

                if current_vol_state == 0:
                    stop_distance_multiplier = 0.7
                    profit_multiplier = 1.5
                elif current_vol_state == 2:
                    stop_distance_multiplier = 1.3
                    profit_multiplier = 2.0

                if not np.isnan(self.range_center[-1]):
                    stop_distance = (self.range_top[-1] - self.range_center[-1]) * stop_distance_multiplier
                    sl_price = self.range_center[-1] + stop_distance
                    tp_price = current_price - (self.range_top[-1] - current_price) * profit_multiplier
                else:
                    sl_price = current_price * (1 + self.stop_loss_pct * stop_distance_multiplier)
                    tp_price = current_price * (1 - self.take_profit_pct * profit_multiplier)

                self.sell(size=position_size * abs(current_signal), sl=sl_price, tp=tp_price)

        # Exit on range re-entry or volatility regime change
        elif self.position:
            # Check for significant volatility regime change
            vol_change_exit = False
            if len(self.volatility_state) > 10:
                recent_vol_states = list(self.volatility_state)[-10:]
                # If volatility regime changed dramatically
                if current_vol_state == 2 and np.mean(recent_vol_states[:-1]) < 1:
                    vol_change_exit = True  # Sudden spike in volatility

            if self.position.is_long:
                if not np.isnan(self.range_top[-1]) and current_price < self.range_top[-1]:
                    self.position.close()
                elif vol_change_exit:
                    self.position.close()

            elif self.position.is_short:
                if not np.isnan(self.range_bottom[-1]) and current_price > self.range_bottom[-1]:
                    self.position.close()
                elif vol_change_exit:
                    self.position.close()

# Run single backtest
bt = Backtest(data, TrendRangeDetectorAdaptive, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND RANGE DETECTOR ADAPTIVE - DEFAULT PARAMETERS ===== 🌙")
print(f"WMA Period: {WMA_PERIOD}")
print(f"Base ATR Multiplier: {BASE_ATR_MULTIPLIER}")
print(f"Adaptive Range: {MIN_ATR_MULTIPLIER} - {MAX_ATR_MULTIPLIER}")
print(f"Volatility Lookback: {VOLATILITY_LOOKBACK} bars")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND RANGE DETECTOR ADAPTIVE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendRangeDetectorAdaptive, 'TrendRangeDetectorAdaptive')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendRangeDetectorAdaptive.csv")