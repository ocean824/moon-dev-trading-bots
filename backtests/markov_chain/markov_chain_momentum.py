"""
Moon Dev's Markov Chain Momentum Strategy
==========================================
Enhanced Markov Chain strategy with RSI and MACD momentum filters
for improved regime confirmation and signal quality.

Combines regime detection with momentum indicators.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import talib
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Markov Chain Momentum Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Markov Chain parameters
LOOKBACK_PERIOD = 50
Z_SCORE_THRESHOLD = 1/3
SMOOTHING_ALPHA = 1
MIN_CONFIDENCE = 0.3

# Momentum indicators
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
MOMENTUM_PERIOD = 10

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

class MarkovChainMomentum(Strategy):
    """
    Markov Chain Momentum Strategy
    - Uses Markov Chain for regime detection
    - RSI for overbought/oversold conditions
    - MACD for trend confirmation
    - Momentum oscillator for additional confirmation
    - Combines multiple signals for high-probability trades
    """

    # Markov parameters
    lookback = LOOKBACK_PERIOD
    z_threshold = Z_SCORE_THRESHOLD
    smoothing = SMOOTHING_ALPHA
    min_confidence = MIN_CONFIDENCE

    # Momentum parameters
    rsi_period = RSI_PERIOD
    rsi_ob = RSI_OVERBOUGHT
    rsi_os = RSI_OVERSOLD
    macd_fast = MACD_FAST
    macd_slow = MACD_SLOW
    macd_signal = MACD_SIGNAL
    mom_period = MOMENTUM_PERIOD

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

    def detect_rsi_divergence(self, price, rsi, lookback=14):
        """Detect RSI divergence patterns"""
        bullish_div = np.zeros(len(price))
        bearish_div = np.zeros(len(price))

        for i in range(lookback * 2, len(price)):
            price_window = price[i-lookback:i]
            rsi_window = rsi[i-lookback:i]

            if len(price_window) < lookback:
                continue

            # Bullish divergence: price lower low, RSI higher low
            price_min_idx = np.argmin(price_window)
            if 2 < price_min_idx < len(price_window) - 2:
                prev_window = price[i-lookback*2:i-lookback]
                prev_rsi = rsi[i-lookback*2:i-lookback]
                if len(prev_window) >= lookback:
                    prev_min_idx = np.argmin(prev_window)
                    if (price_window[price_min_idx] < prev_window[prev_min_idx] and
                        rsi_window[price_min_idx] > prev_rsi[prev_min_idx] and
                        rsi_window[price_min_idx] < self.rsi_os + 10):
                        bullish_div[i] = 1

            # Bearish divergence: price higher high, RSI lower high
            price_max_idx = np.argmax(price_window)
            if 2 < price_max_idx < len(price_window) - 2:
                prev_window = price[i-lookback*2:i-lookback]
                prev_rsi = rsi[i-lookback*2:i-lookback]
                if len(prev_window) >= lookback:
                    prev_max_idx = np.argmax(prev_window)
                    if (price_window[price_max_idx] > prev_window[prev_max_idx] and
                        rsi_window[price_max_idx] < prev_rsi[prev_max_idx] and
                        rsi_window[price_max_idx] > self.rsi_ob - 10):
                        bearish_div[i] = 1

        return bullish_div, bearish_div

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Calculate returns
        returns = close.pct_change()

        # Calculate rolling Z-score
        rolling_mean = returns.rolling(window=self.lookback).mean()
        rolling_std = returns.rolling(window=self.lookback).std()
        z_scores = (returns - rolling_mean) / rolling_std

        # Determine regimes
        regimes = self.calculate_regime(returns.values, z_scores.values)

        # RSI calculation
        rsi = talib.RSI(close.values, timeperiod=self.rsi_period)

        # MACD calculation
        macd, macd_signal, macd_hist = talib.MACD(close.values,
                                                   fastperiod=self.macd_fast,
                                                   slowperiod=self.macd_slow,
                                                   signalperiod=self.macd_signal)

        # Momentum indicator
        momentum = talib.MOM(close.values, timeperiod=self.mom_period)

        # RSI divergence detection
        rsi_bull_div, rsi_bear_div = self.detect_rsi_divergence(close.values, rsi)

        # Calculate rolling transition probabilities
        transition_probs_to_bull = []
        transition_probs_to_bear = []
        momentum_strength = []

        for i in range(len(close)):
            if i < self.lookback * 2:
                transition_probs_to_bull.append(0.33)
                transition_probs_to_bear.append(0.33)
                momentum_strength.append(0)
            else:
                window_states = regimes[i - self.lookback:i]
                trans_matrix = self.calculate_transition_matrix(window_states)
                current_state = regimes[i - 1] if i > 0 else 0

                prob_to_bull = self.get_transition_probability(current_state, 1, trans_matrix)
                prob_to_bear = self.get_transition_probability(current_state, -1, trans_matrix)

                transition_probs_to_bull.append(prob_to_bull)
                transition_probs_to_bear.append(prob_to_bear)

                # Calculate momentum strength score
                mom_score = 0
                if not np.isnan(rsi[i]):
                    if rsi[i] > 50:
                        mom_score += (rsi[i] - 50) / 50
                    else:
                        mom_score -= (50 - rsi[i]) / 50

                if not np.isnan(macd_hist[i]):
                    mom_score += np.tanh(macd_hist[i] / close.iloc[i] * 100)

                if not np.isnan(momentum[i]):
                    mom_score += np.tanh(momentum[i] / close.iloc[i] * 10)

                momentum_strength.append(mom_score / 3)  # Normalize

        # Store as indicators
        self.regime = self.I(lambda: regimes, name='regime')
        self.prob_to_bull = self.I(lambda: np.array(transition_probs_to_bull), name='prob_to_bull')
        self.prob_to_bear = self.I(lambda: np.array(transition_probs_to_bear), name='prob_to_bear')
        self.rsi = self.I(lambda: rsi, name='rsi')
        self.macd = self.I(lambda: macd, name='macd')
        self.macd_signal = self.I(lambda: macd_signal, name='macd_signal')
        self.macd_hist = self.I(lambda: macd_hist, name='macd_hist')
        self.momentum = self.I(lambda: momentum, name='momentum')
        self.rsi_bull_div = self.I(lambda: rsi_bull_div, name='rsi_bull_div')
        self.rsi_bear_div = self.I(lambda: rsi_bear_div, name='rsi_bear_div')
        self.mom_strength = self.I(lambda: np.array(momentum_strength), name='mom_strength')

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
        rsi_val = self.rsi[-1] if not np.isnan(self.rsi[-1]) else 50
        macd_val = self.macd[-1] if not np.isnan(self.macd[-1]) else 0
        macd_sig = self.macd_signal[-1] if not np.isnan(self.macd_signal[-1]) else 0
        macd_hist_val = self.macd_hist[-1] if not np.isnan(self.macd_hist[-1]) else 0
        momentum_val = self.momentum[-1] if not np.isnan(self.momentum[-1]) else 0
        rsi_bull_div = self.rsi_bull_div[-1]
        rsi_bear_div = self.rsi_bear_div[-1]
        mom_strength = self.mom_strength[-1]

        current_price = self.data.Close[-1]
        current_atr = self.atr[-1] if not np.isnan(self.atr[-1]) else current_price * 0.02

        # Position management
        if not self.position:
            # Long entry conditions
            regime_bull = current_regime == 1 and prev_regime != 1
            confidence_bull = prob_to_bull >= self.min_confidence
            rsi_bull = rsi_val < self.rsi_ob and rsi_val > self.rsi_os - 5  # Not overbought
            macd_bull = macd_val > macd_sig or macd_hist_val > 0  # MACD bullish
            momentum_bull = momentum_val > 0 or mom_strength > 0.1
            divergence_bull = rsi_bull_div == 1

            # Score-based entry for longs
            bull_score = 0
            if regime_bull: bull_score += 1
            if confidence_bull: bull_score += prob_to_bull
            if rsi_bull: bull_score += 0.5
            if macd_bull: bull_score += 0.5
            if momentum_bull: bull_score += 0.5
            if divergence_bull: bull_score += 1

            if bull_score >= 2.5:  # Threshold for entry
                # Position sizing based on signal strength
                position_scale = min(bull_score / 4, 1.0)

                # Dynamic stops based on momentum
                sl_mult = 2.5 if mom_strength < 0 else 2.0
                tp_mult = 2.5 if mom_strength > 0.3 else 3.0

                sl_price = current_price - current_atr * sl_mult
                tp_price = current_price + current_atr * tp_mult

                # Tighten stops if RSI is extreme
                if rsi_val > self.rsi_ob - 5:
                    tp_price = current_price + current_atr * 1.5

                self.buy(sl=sl_price, tp=tp_price, size=position_scale)

            # Short entry conditions
            regime_bear = current_regime == -1 and prev_regime != -1
            confidence_bear = prob_to_bear >= self.min_confidence
            rsi_bear = rsi_val > self.rsi_os and rsi_val < self.rsi_ob + 5  # Not oversold
            macd_bear = macd_val < macd_sig or macd_hist_val < 0  # MACD bearish
            momentum_bear = momentum_val < 0 or mom_strength < -0.1
            divergence_bear = rsi_bear_div == 1

            # Score-based entry for shorts
            bear_score = 0
            if regime_bear: bear_score += 1
            if confidence_bear: bear_score += prob_to_bear
            if rsi_bear: bear_score += 0.5
            if macd_bear: bear_score += 0.5
            if momentum_bear: bear_score += 0.5
            if divergence_bear: bear_score += 1

            if bear_score >= 2.5:  # Threshold for entry
                # Position sizing based on signal strength
                position_scale = min(bear_score / 4, 1.0)

                # Dynamic stops based on momentum
                sl_mult = 2.5 if mom_strength > 0 else 2.0
                tp_mult = 2.5 if mom_strength < -0.3 else 3.0

                sl_price = current_price + current_atr * sl_mult
                tp_price = current_price - current_atr * tp_mult

                # Tighten stops if RSI is extreme
                if rsi_val < self.rsi_os + 5:
                    tp_price = current_price - current_atr * 1.5

                self.sell(sl=sl_price, tp=tp_price, size=position_scale)

        else:
            # Exit management
            if self.position.is_long:
                # Exit conditions for longs
                exit_regime = current_regime == -1
                exit_rsi = rsi_val > self.rsi_ob
                exit_macd = macd_val < macd_sig and macd_hist_val < 0
                exit_momentum = mom_strength < -0.3
                exit_divergence = rsi_bear_div == 1

                if exit_regime or exit_rsi or (exit_macd and exit_momentum) or exit_divergence:
                    self.position.close()

            elif self.position.is_short:
                # Exit conditions for shorts
                exit_regime = current_regime == 1
                exit_rsi = rsi_val < self.rsi_os
                exit_macd = macd_val > macd_sig and macd_hist_val > 0
                exit_momentum = mom_strength > 0.3
                exit_divergence = rsi_bull_div == 1

                if exit_regime or exit_rsi or (exit_macd and exit_momentum) or exit_divergence:
                    self.position.close()

# Run single backtest
print("\n🌙 ===== MARKOV CHAIN MOMENTUM STRATEGY ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"RSI Period: {RSI_PERIOD} (OB: {RSI_OVERBOUGHT}, OS: {RSI_OVERSOLD})")
print(f"MACD: {MACD_FAST}/{MACD_SLOW}/{MACD_SIGNAL}")
print(f"Momentum Period: {MOMENTUM_PERIOD}")

bt = Backtest(data, MarkovChainMomentum, cash=POSITION_SIZE, commission=0.00045)
stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MARKOV CHAIN MOMENTUM ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    results = test_on_all_data(MarkovChainMomentum, 'MarkovChainMomentum')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MarkovChainMomentum.csv")