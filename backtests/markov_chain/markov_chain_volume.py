"""
Moon Dev's Markov Chain Volume Strategy
========================================
Enhanced Markov Chain strategy with volume confirmation
for regime changes and improved signal quality.

Uses volume patterns to validate regime transitions.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import talib
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Markov Chain Volume Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Markov Chain parameters
LOOKBACK_PERIOD = 50
Z_SCORE_THRESHOLD = 1/3
SMOOTHING_ALPHA = 1
MIN_CONFIDENCE = 0.3

# Volume parameters
VOLUME_MA_PERIOD = 20
VOLUME_THRESHOLD = 1.2  # Volume must be 1.2x average for confirmation
OBV_PERIOD = 14  # On-Balance Volume period
VWAP_PERIOD = 20  # VWAP period for price levels

# Risk management
POSITION_SIZE = 1000000
STOP_LOSS_PERCENT = 2.0
TAKE_PROFIT_PERCENT = 4.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class MarkovChainVolume(Strategy):
    """
    Markov Chain Volume Strategy
    - Uses Markov Chain for regime detection
    - Requires volume confirmation for entries
    - Uses OBV divergence for additional confirmation
    - VWAP levels for support/resistance
    - Volume-weighted position sizing
    """

    # Markov parameters
    lookback = LOOKBACK_PERIOD
    z_threshold = Z_SCORE_THRESHOLD
    smoothing = SMOOTHING_ALPHA
    min_confidence = MIN_CONFIDENCE

    # Volume parameters
    vol_ma_period = VOLUME_MA_PERIOD
    vol_threshold = VOLUME_THRESHOLD
    obv_period = OBV_PERIOD
    vwap_period = VWAP_PERIOD

    # Risk management
    sl_pct = STOP_LOSS_PERCENT / 100
    tp_pct = TAKE_PROFIT_PERCENT / 100

    def calculate_regime(self, returns, z_scores):
        """Determine market regime based on Z-score"""
        regimes = np.zeros(len(z_scores))
        regimes[z_scores > self.z_threshold] = 1  # Bull
        regimes[z_scores < -self.z_threshold] = -1  # Bear
        return regimes

    def calculate_transition_matrix(self, states):
        """Calculate transition probability matrix with Laplace smoothing"""
        transition_counts = np.ones((3, 3)) * self.smoothing
        state_map = {-1: 0, 0: 1, 1: 2}

        for i in range(len(states) - 1):
            if not np.isnan(states[i]) and not np.isnan(states[i + 1]):
                from_idx = state_map[int(states[i])]
                to_idx = state_map[int(states[i + 1])]
                transition_counts[from_idx, to_idx] += 1

        transition_matrix = transition_counts / transition_counts.sum(axis=1, keepdims=True)
        return transition_matrix

    def get_transition_probability(self, from_state, to_state, transition_matrix):
        """Get probability of transitioning from one state to another"""
        state_map = {-1: 0, 0: 1, 1: 2}
        from_idx = state_map[int(from_state)]
        to_idx = state_map[int(to_state)]
        return transition_matrix[from_idx, to_idx]

    def calculate_obv_divergence(self, price, obv, lookback=20):
        """Detect OBV divergence"""
        bullish_div = np.zeros(len(price))
        bearish_div = np.zeros(len(price))

        for i in range(lookback, len(price)):
            price_window = price[i-lookback:i]
            obv_window = obv[i-lookback:i]

            # Find local extrema
            if i >= lookback + 5:
                # Bullish divergence: price makes lower low, OBV makes higher low
                price_min_idx = np.argmin(price_window)
                if price_min_idx > 2 and price_min_idx < len(price_window) - 2:
                    prev_price_window = price[i-lookback*2:i-lookback]
                    prev_obv_window = obv[i-lookback*2:i-lookback]
                    if len(prev_price_window) > 0:
                        prev_min_idx = np.argmin(prev_price_window)
                        if (price_window[price_min_idx] < prev_price_window[prev_min_idx] and
                            obv_window[price_min_idx] > prev_obv_window[prev_min_idx]):
                            bullish_div[i] = 1

                # Bearish divergence: price makes higher high, OBV makes lower high
                price_max_idx = np.argmax(price_window)
                if price_max_idx > 2 and price_max_idx < len(price_window) - 2:
                    prev_max_idx = np.argmax(prev_price_window)
                    if (price_window[price_max_idx] > prev_price_window[prev_max_idx] and
                        obv_window[price_max_idx] < prev_obv_window[prev_max_idx]):
                        bearish_div[i] = 1

        return bullish_div, bearish_div

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate returns
        returns = close.pct_change()

        # Calculate rolling Z-score
        rolling_mean = returns.rolling(window=self.lookback).mean()
        rolling_std = returns.rolling(window=self.lookback).std()
        z_scores = (returns - rolling_mean) / rolling_std

        # Determine regimes
        regimes = self.calculate_regime(returns.values, z_scores.values)

        # Volume indicators
        volume_ma = volume.rolling(window=self.vol_ma_period).mean()
        volume_ratio = volume / volume_ma

        # On-Balance Volume
        obv = ta.obv(close, volume)
        obv_ma = obv.rolling(window=self.obv_period).mean() if obv is not None else pd.Series(np.zeros(len(close)))

        # VWAP calculation
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).rolling(window=self.vwap_period).sum() / volume.rolling(window=self.vwap_period).sum()

        # OBV divergence
        if obv is not None:
            bullish_div, bearish_div = self.calculate_obv_divergence(close.values, obv.values)
        else:
            bullish_div = np.zeros(len(close))
            bearish_div = np.zeros(len(close))

        # Calculate rolling transition probabilities
        transition_probs_to_bull = []
        transition_probs_to_bear = []
        volume_strength = []

        for i in range(len(close)):
            if i < self.lookback * 2:
                transition_probs_to_bull.append(0.33)
                transition_probs_to_bear.append(0.33)
                volume_strength.append(0)
            else:
                window_states = regimes[i - self.lookback:i]
                trans_matrix = self.calculate_transition_matrix(window_states)
                current_state = regimes[i - 1] if i > 0 else 0

                prob_to_bull = self.get_transition_probability(current_state, 1, trans_matrix)
                prob_to_bear = self.get_transition_probability(current_state, -1, trans_matrix)

                transition_probs_to_bull.append(prob_to_bull)
                transition_probs_to_bear.append(prob_to_bear)

                # Calculate volume strength indicator
                recent_vol_ratio = volume_ratio.iloc[i-5:i].mean() if i >= 5 else 1.0
                volume_strength.append(recent_vol_ratio)

        # Store as indicators
        self.regime = self.I(lambda: regimes, name='regime')
        self.prob_to_bull = self.I(lambda: np.array(transition_probs_to_bull), name='prob_to_bull')
        self.prob_to_bear = self.I(lambda: np.array(transition_probs_to_bear), name='prob_to_bear')
        self.vol_ratio = self.I(lambda: volume_ratio.values, name='vol_ratio')
        self.vwap = self.I(lambda: vwap.values, name='vwap')
        self.bullish_div = self.I(lambda: bullish_div, name='bullish_div')
        self.bearish_div = self.I(lambda: bearish_div, name='bearish_div')
        self.vol_strength = self.I(lambda: np.array(volume_strength), name='vol_strength')

        # ATR for stops
        self.atr = self.I(talib.ATR, high, low, close, timeperiod=14)

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.lookback * 2:
            return

        # Get indicators
        current_regime = self.regime[-1]
        prev_regime = self.regime[-2] if len(self.regime) > 1 else 0
        prob_to_bull = self.prob_to_bull[-1]
        prob_to_bear = self.prob_to_bear[-1]
        vol_ratio = self.vol_ratio[-1] if not np.isnan(self.vol_ratio[-1]) else 1.0
        vwap_level = self.vwap[-1] if not np.isnan(self.vwap[-1]) else self.data.Close[-1]
        bullish_div = self.bullish_div[-1]
        bearish_div = self.bearish_div[-1]
        vol_strength = self.vol_strength[-1]

        current_price = self.data.Close[-1]
        current_atr = self.atr[-1] if not np.isnan(self.atr[-1]) else current_price * 0.02

        # Position management
        if not self.position:
            # Long entry conditions
            long_regime_change = current_regime == 1 and prev_regime != 1
            long_confidence = prob_to_bull >= self.min_confidence
            long_volume_confirm = vol_ratio >= self.vol_threshold or vol_strength > 1.1
            long_price_confirm = current_price > vwap_level * 0.995  # Price above or near VWAP
            long_divergence = bullish_div == 1

            # Enhanced long entry
            if long_regime_change and long_confidence and long_volume_confirm:
                # Extra confirmation from price action or divergence
                if long_price_confirm or long_divergence:
                    # Volume-weighted position sizing
                    volume_factor = min(vol_ratio / self.vol_threshold, 1.5)
                    position_scale = min(prob_to_bull * volume_factor, 1.0)

                    # Dynamic stops based on VWAP distance
                    vwap_distance = abs(current_price - vwap_level)
                    sl_distance = max(current_atr * 2, vwap_distance * 1.5)
                    tp_distance = max(current_atr * 3, vwap_distance * 3)

                    sl_price = current_price - sl_distance
                    tp_price = current_price + tp_distance

                    self.buy(sl=sl_price, tp=tp_price, size=position_scale)

            # Short entry conditions
            short_regime_change = current_regime == -1 and prev_regime != -1
            short_confidence = prob_to_bear >= self.min_confidence
            short_volume_confirm = vol_ratio >= self.vol_threshold or vol_strength > 1.1
            short_price_confirm = current_price < vwap_level * 1.005  # Price below or near VWAP
            short_divergence = bearish_div == 1

            # Enhanced short entry
            if short_regime_change and short_confidence and short_volume_confirm:
                # Extra confirmation from price action or divergence
                if short_price_confirm or short_divergence:
                    # Volume-weighted position sizing
                    volume_factor = min(vol_ratio / self.vol_threshold, 1.5)
                    position_scale = min(prob_to_bear * volume_factor, 1.0)

                    # Dynamic stops based on VWAP distance
                    vwap_distance = abs(current_price - vwap_level)
                    sl_distance = max(current_atr * 2, vwap_distance * 1.5)
                    tp_distance = max(current_atr * 3, vwap_distance * 3)

                    sl_price = current_price + sl_distance
                    tp_price = current_price - tp_distance

                    self.sell(sl=sl_price, tp=tp_price, size=position_scale)

        else:
            # Exit management
            if self.position.is_long:
                # Exit on regime change
                if current_regime != 1:
                    self.position.close()
                # Exit on volume exhaustion
                elif vol_ratio < 0.5 and vol_strength < 0.8:
                    self.position.close()
                # Exit on bearish divergence
                elif bearish_div == 1:
                    self.position.close()
                # Exit if price breaks below VWAP significantly
                elif current_price < vwap_level * 0.98:
                    self.position.close()

            elif self.position.is_short:
                # Exit on regime change
                if current_regime != -1:
                    self.position.close()
                # Exit on volume exhaustion
                elif vol_ratio < 0.5 and vol_strength < 0.8:
                    self.position.close()
                # Exit on bullish divergence
                elif bullish_div == 1:
                    self.position.close()
                # Exit if price breaks above VWAP significantly
                elif current_price > vwap_level * 1.02:
                    self.position.close()

# Run single backtest
print("\n🌙 ===== MARKOV CHAIN VOLUME STRATEGY ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Volume MA Period: {VOLUME_MA_PERIOD}")
print(f"Volume Threshold: {VOLUME_THRESHOLD}x")
print(f"VWAP Period: {VWAP_PERIOD}")

bt = Backtest(data, MarkovChainVolume, cash=POSITION_SIZE, commission=0.00045)
stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MARKOV CHAIN VOLUME ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    results = test_on_all_data(MarkovChainVolume, 'MarkovChainVolume')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MarkovChainVolume.csv")