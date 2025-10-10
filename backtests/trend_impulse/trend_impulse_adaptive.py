"""
Moon Dev's Trend Impulse Channels Adaptive Strategy
====================================================
Adaptive parameters based on market volatility regimes.
Automatically adjusts channel width, step sizes, and thresholds.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Trend Impulse Channels Adaptive Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Base parameters (will be adapted based on volatility)
ATR_PERIOD = 200
BASE_TRIGGER_THRESHOLD = 2.86
BASE_MAX_STEP_SIZE = 0.034
BASE_BAND_MULTIPLIER = 2.02
TREND_HOLD = 1

# Volatility regime parameters
VOLATILITY_LOOKBACK = 50
LOW_VOL_PERCENTILE = 30
HIGH_VOL_PERCENTILE = 70

# Risk management
BASE_TAKE_PROFIT = 3.0
BASE_STOP_LOSS = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class TrendImpulseAdaptive(Strategy):
    """
    Trend Impulse Channels with Adaptive Volatility

    Features:
    - Detects volatility regimes (low, normal, high)
    - Adjusts parameters dynamically:
      - Tighter channels in low volatility
      - Wider channels in high volatility
      - Faster reactions in trending markets
      - Slower reactions in ranging markets
    - Market structure detection for regime filtering
    """

    # Base parameters
    atr_period = ATR_PERIOD
    base_trigger_threshold = BASE_TRIGGER_THRESHOLD
    base_max_step_size = BASE_MAX_STEP_SIZE
    base_band_multiplier = BASE_BAND_MULTIPLIER
    trend_hold = TREND_HOLD

    # Volatility parameters
    volatility_lookback = VOLATILITY_LOOKBACK
    low_vol_percentile = LOW_VOL_PERCENTILE
    high_vol_percentile = HIGH_VOL_PERCENTILE

    # Risk management
    base_take_profit = BASE_TAKE_PROFIT / 100
    base_stop_loss = BASE_STOP_LOSS / 100

    # Market structure parameters
    structure_period = 20
    trend_strength_threshold = 0.6

    def detect_volatility_regime(self, atr, close):
        """Classify market into volatility regimes"""
        n = len(atr)
        volatility_regime = np.zeros(n)  # 0=normal, -1=low, 1=high
        atr_percentile = np.full(n, np.nan)
        historical_volatility = np.full(n, np.nan)

        for i in range(self.volatility_lookback, n):
            # Calculate ATR percentile
            recent_atr = atr[i-self.volatility_lookback:i]
            valid_atr = recent_atr[~np.isnan(recent_atr)]

            if len(valid_atr) > 10:
                current_atr = atr[i]
                if not np.isnan(current_atr):
                    atr_percentile[i] = (np.sum(valid_atr <= current_atr) / len(valid_atr)) * 100

                    # Classify regime
                    if atr_percentile[i] < self.low_vol_percentile:
                        volatility_regime[i] = -1  # Low volatility
                    elif atr_percentile[i] > self.high_vol_percentile:
                        volatility_regime[i] = 1   # High volatility
                    else:
                        volatility_regime[i] = 0   # Normal volatility

            # Calculate historical volatility (standard deviation of returns)
            if i > 20:
                returns = np.diff(np.log(close[i-20:i]))
                if len(returns) > 0:
                    historical_volatility[i] = np.std(returns) * np.sqrt(252)  # Annualized

        return volatility_regime, atr_percentile, historical_volatility

    def detect_market_structure(self, close, high, low):
        """Detect trending vs ranging market structure"""
        n = len(close)
        trend_strength = np.zeros(n)
        market_type = np.zeros(n)  # 1=trending, 0=ranging, -1=choppy

        for i in range(self.structure_period, n):
            window_close = close[i-self.structure_period:i]
            window_high = high[i-self.structure_period:i]
            window_low = low[i-self.structure_period:i]

            # Calculate directional movement
            price_change = window_close[-1] - window_close[0]
            price_range = np.max(window_high) - np.min(window_low)

            if price_range > 0:
                # Trend strength: how much of the range was directional
                trend_strength[i] = abs(price_change) / price_range

                # Classify market structure
                if trend_strength[i] > self.trend_strength_threshold:
                    market_type[i] = 1  # Trending
                elif trend_strength[i] < 0.3:
                    market_type[i] = -1  # Choppy
                else:
                    market_type[i] = 0  # Ranging

        return trend_strength, market_type

    def calculate_adaptive_parameters(self, volatility_regime, market_type, trend_strength):
        """Calculate adaptive parameters based on market conditions"""
        n = len(volatility_regime)
        trigger_threshold = np.full(n, self.base_trigger_threshold)
        max_step_size = np.full(n, self.base_max_step_size)
        band_multiplier = np.full(n, self.base_band_multiplier)

        for i in range(n):
            # Adapt based on volatility regime
            if volatility_regime[i] == -1:  # Low volatility
                # Tighter parameters for low vol
                trigger_threshold[i] = self.base_trigger_threshold * 0.7
                max_step_size[i] = self.base_max_step_size * 1.3
                band_multiplier[i] = self.base_band_multiplier * 0.7

            elif volatility_regime[i] == 1:  # High volatility
                # Wider parameters for high vol
                trigger_threshold[i] = self.base_trigger_threshold * 1.3
                max_step_size[i] = self.base_max_step_size * 0.7
                band_multiplier[i] = self.base_band_multiplier * 1.3

            # Further adapt based on market structure
            if market_type[i] == 1:  # Trending market
                # Favor trend following
                max_step_size[i] *= (1 + trend_strength[i] * 0.5)
                trigger_threshold[i] *= (1 + trend_strength[i] * 0.2)

            elif market_type[i] == -1:  # Choppy market
                # More conservative in chop
                trigger_threshold[i] *= 1.5
                max_step_size[i] *= 0.5
                band_multiplier[i] *= 1.2

        return trigger_threshold, max_step_size, band_multiplier

    def calculate_adaptive_trend_impulse(self, close, high, low, atr, trigger_threshold,
                                        max_step_size, band_multiplier):
        """Calculate trend impulse with adaptive parameters"""
        n = len(close)
        trend = np.full(n, np.nan)
        direction = np.zeros(n)
        trend_hold_counter = np.zeros(n)

        trend[0] = close[0]
        direction[0] = 1

        for i in range(1, n):
            if np.isnan(atr[i]):
                trend[i] = trend[i-1]
                direction[i] = direction[i-1]
                continue

            # Use adaptive parameters
            trigger = atr[i] * trigger_threshold[i]
            step_size = min(atr[i] * max_step_size[i], abs(close[i] - trend[i-1]) * 0.1)

            # Check for trend flips
            flip_up = close[i] > trend[i-1] + trigger and direction[i-1] <= 0
            flip_down = close[i] < trend[i-1] - trigger and direction[i-1] >= 0

            # Apply trend hold
            if flip_up or flip_down:
                trend_hold_counter[i] = trend_hold_counter[i-1] + 1
                if trend_hold_counter[i] < self.trend_hold:
                    flip_up = False
                    flip_down = False
                else:
                    trend_hold_counter[i] = 0
            else:
                trend_hold_counter[i] = 0

            # Update trend and direction
            if flip_up:
                direction[i] = 1
                trend[i] = close[i] - atr[i] * 0.5
            elif flip_down:
                direction[i] = -1
                trend[i] = close[i] + atr[i] * 0.5
            else:
                direction[i] = direction[i-1]
                if direction[i] > 0:
                    if close[i] > trend[i-1]:
                        trend[i] = trend[i-1] + step_size
                    else:
                        trend[i] = trend[i-1]
                else:
                    if close[i] < trend[i-1]:
                        trend[i] = trend[i-1] - step_size
                    else:
                        trend[i] = trend[i-1]

        # Calculate adaptive channel bands
        upper_band = trend + atr * band_multiplier
        lower_band = trend - atr * band_multiplier

        return trend, upper_band, lower_band, direction

    def generate_adaptive_signals(self, close, high, low, trend, upper_band, lower_band,
                                 direction, volatility_regime, market_type, trend_strength):
        """Generate signals adapted to market conditions"""
        n = len(close)
        long_signals = np.zeros(n)
        short_signals = np.zeros(n)

        for i in range(3, n):
            if np.isnan(trend[i]) or np.isnan(direction[i]):
                continue

            # Adjust signal generation based on market conditions
            signal_multiplier = 1.0

            # Boost signals in trending markets
            if market_type[i] == 1:
                signal_multiplier = 1.5

            # Reduce signals in choppy markets
            elif market_type[i] == -1:
                signal_multiplier = 0.5

            # Adjust for volatility regime
            if volatility_regime[i] == -1:  # Low vol - be more aggressive
                signal_multiplier *= 1.2
            elif volatility_regime[i] == 1:  # High vol - be more selective
                signal_multiplier *= 0.8

            # LONG SIGNALS
            if direction[i] > 0:  # Uptrend
                # Trend flip signal
                if direction[i] != direction[i-1]:
                    long_signals[i] = 3 * signal_multiplier

                # Channel bounce (stronger in trending markets)
                elif (low[i] <= lower_band[i] and close[i] > lower_band[i]):
                    if market_type[i] == 1:  # Trending
                        long_signals[i] = max(long_signals[i], 2.5 * signal_multiplier)
                    else:
                        long_signals[i] = max(long_signals[i], 1.5 * signal_multiplier)

                # Trend continuation (only in strong trends)
                elif (close[i] > trend[i] and trend_strength[i] > 0.5):
                    long_signals[i] = max(long_signals[i], 1 * signal_multiplier)

                # Breakout in low volatility
                elif (close[i] > upper_band[i-1] and volatility_regime[i] == -1):
                    long_signals[i] = max(long_signals[i], 2 * signal_multiplier)

            # SHORT SIGNALS
            if direction[i] < 0:  # Downtrend
                # Trend flip signal
                if direction[i] != direction[i-1]:
                    short_signals[i] = 3 * signal_multiplier

                # Channel rejection (stronger in trending markets)
                elif (high[i] >= upper_band[i] and close[i] < upper_band[i]):
                    if market_type[i] == 1:  # Trending
                        short_signals[i] = max(short_signals[i], 2.5 * signal_multiplier)
                    else:
                        short_signals[i] = max(short_signals[i], 1.5 * signal_multiplier)

                # Trend continuation (only in strong trends)
                elif (close[i] < trend[i] and trend_strength[i] > 0.5):
                    short_signals[i] = max(short_signals[i], 1 * signal_multiplier)

                # Breakdown in low volatility
                elif (close[i] < lower_band[i-1] and volatility_regime[i] == -1):
                    short_signals[i] = max(short_signals[i], 2 * signal_multiplier)

            # Filter out weak signals in ranging markets
            if market_type[i] == 0:  # Ranging
                if long_signals[i] < 1.5:
                    long_signals[i] = 0
                if short_signals[i] < 1.5:
                    short_signals[i] = 0

        return long_signals, short_signals

    def init(self):
        """Initialize adaptive indicators"""
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Calculate ATR
        atr = ta.atr(high, low, close, length=self.atr_period)

        # Ensure arrays are same length as data
        atr_full = np.full(len(close), np.nan)
        if atr is not None and len(atr) > 0:
            atr_full[-len(atr):] = atr.values

        # Detect volatility regime
        volatility_regime, atr_percentile, historical_vol = self.detect_volatility_regime(
            atr_full, close.values
        )

        # Detect market structure
        trend_strength, market_type = self.detect_market_structure(
            close.values, high.values, low.values
        )

        # Calculate adaptive parameters
        trigger_threshold, max_step_size, band_multiplier = self.calculate_adaptive_parameters(
            volatility_regime, market_type, trend_strength
        )

        # Calculate adaptive trend impulse
        trend, upper_band, lower_band, direction = self.calculate_adaptive_trend_impulse(
            close.values, high.values, low.values, atr_full,
            trigger_threshold, max_step_size, band_multiplier
        )

        # Generate adaptive signals
        long_signals, short_signals = self.generate_adaptive_signals(
            close.values, high.values, low.values,
            trend, upper_band, lower_band, direction,
            volatility_regime, market_type, trend_strength
        )

        # Store as indicators
        self.trend = self.I(lambda: trend)
        self.upper_band = self.I(lambda: upper_band)
        self.lower_band = self.I(lambda: lower_band)
        self.direction = self.I(lambda: direction)
        self.volatility_regime = self.I(lambda: volatility_regime)
        self.market_type = self.I(lambda: market_type)
        self.trend_strength = self.I(lambda: trend_strength)
        self.long_signals = self.I(lambda: long_signals)
        self.short_signals = self.I(lambda: short_signals)
        self.atr = self.I(lambda: atr_full)
        self.atr_percentile = self.I(lambda: atr_percentile)

    def next(self):
        """Execute adaptive trading logic"""
        # Skip if indicators not ready
        if np.isnan(self.trend[-1]) or np.isnan(self.atr[-1]):
            return

        current_price = self.data.Close[-1]

        # Adapt risk parameters based on volatility
        vol_adjustment = 1.0
        if self.volatility_regime[-1] == -1:  # Low vol
            vol_adjustment = 0.8  # Tighter stops in low vol
        elif self.volatility_regime[-1] == 1:  # High vol
            vol_adjustment = 1.3  # Wider stops in high vol

        # Position management
        if self.position:
            # Exit on trend reversal
            if self.position.is_long and self.direction[-1] < 0:
                self.position.close()
            elif self.position.is_short and self.direction[-1] > 0:
                self.position.close()

            # Adaptive trailing stops
            if self.position.is_long:
                # Tighter stops in ranging markets
                if self.market_type[-1] == 0:  # Ranging
                    trailing_stop = self.trend[-1]
                else:
                    trailing_stop = self.lower_band[-1]

                if current_price < trailing_stop:
                    self.position.close()

            elif self.position.is_short:
                # Tighter stops in ranging markets
                if self.market_type[-1] == 0:  # Ranging
                    trailing_stop = self.trend[-1]
                else:
                    trailing_stop = self.upper_band[-1]

                if current_price > trailing_stop:
                    self.position.close()

        else:
            # Entry signals with adaptive risk management
            if self.long_signals[-1] > 0:
                signal_strength = self.long_signals[-1]

                # Adaptive stops based on volatility and market type
                sl_multiplier = self.base_stop_loss * vol_adjustment
                if self.market_type[-1] == 1:  # Trending
                    sl_multiplier *= 1.2  # Wider stops in trends
                elif self.market_type[-1] == -1:  # Choppy
                    sl_multiplier *= 0.8  # Tighter stops in chop

                sl_price = current_price * (1 - sl_multiplier)
                sl_price = max(sl_price, self.lower_band[-1])

                # Adaptive targets
                tp_multiplier = self.base_take_profit * (signal_strength / 2)
                if self.trend_strength[-1] > 0.6:  # Strong trend
                    tp_multiplier *= 1.5  # Larger targets in strong trends

                tp_price = current_price * (1 + tp_multiplier)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

            elif self.short_signals[-1] > 0:
                signal_strength = self.short_signals[-1]

                # Adaptive stops based on volatility and market type
                sl_multiplier = self.base_stop_loss * vol_adjustment
                if self.market_type[-1] == 1:  # Trending
                    sl_multiplier *= 1.2  # Wider stops in trends
                elif self.market_type[-1] == -1:  # Choppy
                    sl_multiplier *= 0.8  # Tighter stops in chop

                sl_price = current_price * (1 + sl_multiplier)
                sl_price = max(sl_price, self.upper_band[-1])  # For shorts, use max

                # Adaptive targets
                tp_multiplier = self.base_take_profit * (signal_strength / 2)
                if self.trend_strength[-1] > 0.6:  # Strong trend
                    tp_multiplier *= 1.5  # Larger targets in strong trends

                tp_price = current_price * (1 - tp_multiplier)

                self.sell(sl=sl_price, tp=tp_price, size=1000000)

# Run single backtest
bt = Backtest(data, TrendImpulseAdaptive, cash=10000000, commission=0.00045)

print("\n🌙 ===== TREND IMPULSE ADAPTIVE - VOLATILITY-BASED ===== 🌙")
print(f"ATR Period: {ATR_PERIOD}")
print(f"Base Trigger: {BASE_TRIGGER_THRESHOLD} (adapts to volatility)")
print(f"Base Step Size: {BASE_MAX_STEP_SIZE} (adapts to market)")
print(f"Base Band Multiplier: {BASE_BAND_MULTIPLIER} (adapts to regime)")
print(f"Volatility Lookback: {VOLATILITY_LOOKBACK}")
print(f"Base Take Profit: {BASE_TAKE_PROFIT}%")
print(f"Base Stop Loss: {BASE_STOP_LOSS}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING TREND IMPULSE ADAPTIVE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(TrendImpulseAdaptive, 'TrendImpulseAdaptive')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/TrendImpulseAdaptive.csv")