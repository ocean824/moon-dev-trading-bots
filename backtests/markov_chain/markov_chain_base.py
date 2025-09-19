"""
Moon Dev's Markov Chain [3D] Base Strategy - Enhanced Version
==============================================================
Precise implementation of TradingView's Markov Chain [3D] indicator.

Key Features:
- Market regime detection using Z-score of returns (default mode)
- Lookback period of 50 bars for transition probabilities
- Three market states: Bull (+1), Bear (-1), Neutral (0)
- Z-score thresholds of ±1/3 standard deviations for regime transitions
- Transition probability matrix with Laplace smoothing
- Rolling window approach for state tracking
- Entry on regime transitions with probability-based position sizing
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import talib
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Markov Chain Base Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Markov Chain parameters (from TradingView indicator)
LOOKBACK_PERIOD = 50  # Bars to calculate transition probabilities
Z_SCORE_THRESHOLD = 1/3  # Standard deviations for regime thresholds (±0.333)
SMOOTHING_ALPHA = 1  # Laplace smoothing parameter
MIN_CONFIDENCE = 0.35  # Minimum transition probability to take position
REGIME_SMOOTHING = 3  # Bars to smooth regime changes

# Risk management
POSITION_SIZE = 1000000  # Large position size as requested
STOP_LOSS_PERCENT = 2.5
TAKE_PROFIT_PERCENT = 5.0
ATR_MULTIPLIER_SL = 2.0
ATR_MULTIPLIER_TP = 3.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class MarkovChainBase(Strategy):
    """
    Markov Chain Strategy - Base Implementation
    - Detects market regimes using Z-score of returns
    - Calculates transition probability matrix with Laplace smoothing
    - Enters long on transitions to Bull regime
    - Enters short on transitions to Bear regime
    - Uses transition probabilities for position confidence
    """

    # Markov parameters
    lookback = LOOKBACK_PERIOD
    z_threshold = Z_SCORE_THRESHOLD
    smoothing = SMOOTHING_ALPHA
    min_confidence = MIN_CONFIDENCE
    regime_smoothing = REGIME_SMOOTHING

    # Risk management
    sl_pct = STOP_LOSS_PERCENT / 100
    tp_pct = TAKE_PROFIT_PERCENT / 100
    atr_mult_sl = ATR_MULTIPLIER_SL
    atr_mult_tp = ATR_MULTIPLIER_TP

    def calculate_regime(self, returns, z_scores):
        """
        Determine market regime based on Z-score with smoothing
        Returns: 1 (Bull), 0 (Neutral), -1 (Bear)
        """
        regimes = np.zeros(len(z_scores))

        # Classify based on Z-score thresholds (exactly as per TradingView)
        for i in range(len(z_scores)):
            if not np.isnan(z_scores[i]):
                if z_scores[i] > self.z_threshold:
                    regimes[i] = 1  # Bull regime
                elif z_scores[i] < -self.z_threshold:
                    regimes[i] = -1  # Bear regime
                else:
                    regimes[i] = 0  # Neutral regime

        # Apply smoothing to reduce whipsaws
        if self.regime_smoothing > 1:
            smoothed_regimes = pd.Series(regimes).rolling(self.regime_smoothing, min_periods=1).mean()
            # Convert back to discrete states
            final_regimes = np.zeros(len(smoothed_regimes))
            final_regimes[smoothed_regimes > 0.5] = 1
            final_regimes[smoothed_regimes < -0.5] = -1
            return final_regimes

        return regimes

    def calculate_transition_matrix(self, states):
        """
        Calculate transition probability matrix with Laplace smoothing
        """
        # Initialize transition counts (3x3 matrix)
        # States: -1 (Bear), 0 (Neutral), 1 (Bull)
        transition_counts = np.ones((3, 3)) * self.smoothing  # Laplace smoothing

        # Map states to indices: -1->0, 0->1, 1->2
        state_map = {-1: 0, 0: 1, 1: 2}

        # Count transitions
        for i in range(len(states) - 1):
            if not np.isnan(states[i]) and not np.isnan(states[i + 1]):
                from_idx = state_map[int(states[i])]
                to_idx = state_map[int(states[i + 1])]
                transition_counts[from_idx, to_idx] += 1

        # Normalize to get probabilities
        transition_matrix = transition_counts / transition_counts.sum(axis=1, keepdims=True)

        return transition_matrix

    def get_transition_probability(self, from_state, to_state, transition_matrix):
        """Get probability of transitioning from one state to another"""
        state_map = {-1: 0, 0: 1, 1: 2}
        from_idx = state_map[int(from_state)]
        to_idx = state_map[int(to_state)]
        return transition_matrix[from_idx, to_idx]

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate returns (as per TradingView: close-to-close returns)
        returns = close.pct_change()

        # Calculate rolling Z-score of returns (exactly as per indicator)
        rolling_mean = returns.rolling(window=self.lookback, min_periods=2).mean()
        rolling_std = returns.rolling(window=self.lookback, min_periods=2).std()

        # Handle division by zero
        z_scores = np.zeros(len(returns))
        valid_std = rolling_std > 0.0001
        z_scores[valid_std] = ((returns - rolling_mean) / rolling_std)[valid_std]

        # Determine regimes based on Z-score
        regimes = self.calculate_regime(returns.values, z_scores.values)

        # Calculate rolling transition matrices
        transition_matrices = []
        transition_probs_to_bull = []
        transition_probs_to_bear = []

        for i in range(len(close)):
            if i < self.lookback * 2:
                # Not enough data for meaningful transition matrix
                transition_matrices.append(np.ones((3, 3)) / 3)
                transition_probs_to_bull.append(0.33)
                transition_probs_to_bear.append(0.33)
            else:
                # Use lookback window for transition matrix
                window_states = regimes[i - self.lookback:i]
                trans_matrix = self.calculate_transition_matrix(window_states)
                transition_matrices.append(trans_matrix)

                # Get current state and transition probabilities
                current_state = regimes[i - 1] if i > 0 else 0

                # Calculate probability of transitioning to Bull or Bear
                prob_to_bull = self.get_transition_probability(current_state, 1, trans_matrix)
                prob_to_bear = self.get_transition_probability(current_state, -1, trans_matrix)
                prob_to_neutral = self.get_transition_probability(current_state, 0, trans_matrix)

                # Weight probabilities by regime strength (distance from neutral)
                regime_strength = abs(z_scores[i]) if i < len(z_scores) else 0.5
                regime_strength = min(regime_strength, 2.0) / 2.0  # Normalize to [0, 1]

                # Adjust probabilities based on regime strength
                prob_to_bull *= (1 + regime_strength * 0.5)
                prob_to_bear *= (1 + regime_strength * 0.5)

                transition_probs_to_bull.append(min(prob_to_bull, 1.0))
                transition_probs_to_bear.append(min(prob_to_bear, 1.0))

        # Calculate additional indicators for filtering
        self.sma_fast = self.I(talib.SMA, close, timeperiod=20)
        self.sma_slow = self.I(talib.SMA, close, timeperiod=50)
        self.rsi = self.I(talib.RSI, close, timeperiod=14)
        self.volume_sma = self.I(talib.SMA, volume, timeperiod=20)

        # Store as indicators
        self.regime = self.I(lambda: regimes, name='regime')
        self.z_score = self.I(lambda: z_scores, name='z_score')
        self.prob_to_bull = self.I(lambda: np.array(transition_probs_to_bull), name='prob_to_bull')
        self.prob_to_bear = self.I(lambda: np.array(transition_probs_to_bear), name='prob_to_bear')

        # Calculate ATR for dynamic stops
        self.atr = self.I(talib.ATR, high, low, close, timeperiod=14)

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.lookback * 2:
            return

        # Get current and previous regime
        current_regime = self.regime[-1]
        prev_regime = self.regime[-2] if len(self.regime) > 1 else 0

        # Get transition probabilities
        prob_to_bull = self.prob_to_bull[-1]
        prob_to_bear = self.prob_to_bear[-1]

        # Current price and ATR
        current_price = self.data.Close[-1]
        current_atr = self.atr[-1] if not np.isnan(self.atr[-1]) else current_price * 0.02

        # Position management
        if not self.position:
            # Entry logic based on regime transitions

            # Long entry: Transitioning to Bull regime with sufficient confidence
            if (current_regime == 1 and prev_regime != 1 and
                prob_to_bull >= self.min_confidence):

                # Additional filters for higher probability trades
                trend_filter = self.sma_fast[-1] > self.sma_slow[-1]  # Uptrend
                rsi_filter = 30 < self.rsi[-1] < 70  # Not overbought/oversold
                volume_filter = self.data.Volume[-1] > self.volume_sma[-1] * 0.8  # Decent volume

                if trend_filter and rsi_filter and volume_filter:
                    # Dynamic position sizing based on transition probability and Z-score strength
                    z_strength = min(abs(self.z_score[-1]) / 1.5, 1.0)  # Normalize Z-score strength
                    position_confidence = min(prob_to_bull * (1 + z_strength * 0.5), 1.0)

                    # Calculate stops using both percentage and ATR
                    sl_price_pct = current_price * (1 - self.sl_pct)
                    tp_price_pct = current_price * (1 + self.tp_pct)

                    # ATR-based stops with dynamic multipliers
                    atr_sl_mult = self.atr_mult_sl * (2 - position_confidence)  # Tighter stop for higher confidence
                    atr_tp_mult = self.atr_mult_tp * (1 + position_confidence * 0.5)

                    sl_price_atr = current_price - current_atr * atr_sl_mult
                    tp_price_atr = current_price + current_atr * atr_tp_mult

                    # Use optimal stops
                    sl_price = max(sl_price_pct, sl_price_atr)
                    tp_price = max(tp_price_pct, tp_price_atr)

                    self.buy(sl=sl_price, tp=tp_price, size=position_confidence)

            # Short entry: Transitioning to Bear regime with sufficient confidence
            elif (current_regime == -1 and prev_regime != -1 and
                  prob_to_bear >= self.min_confidence):

                # Additional filters for higher probability trades
                trend_filter = self.sma_fast[-1] < self.sma_slow[-1]  # Downtrend
                rsi_filter = 30 < self.rsi[-1] < 70  # Not overbought/oversold
                volume_filter = self.data.Volume[-1] > self.volume_sma[-1] * 0.8  # Decent volume

                if trend_filter and rsi_filter and volume_filter:
                    # Dynamic position sizing based on transition probability and Z-score strength
                    z_strength = min(abs(self.z_score[-1]) / 1.5, 1.0)
                    position_confidence = min(prob_to_bear * (1 + z_strength * 0.5), 1.0)

                    # Calculate stops
                    sl_price_pct = current_price * (1 + self.sl_pct)
                    tp_price_pct = current_price * (1 - self.tp_pct)

                    # ATR-based stops with dynamic multipliers
                    atr_sl_mult = self.atr_mult_sl * (2 - position_confidence)
                    atr_tp_mult = self.atr_mult_tp * (1 + position_confidence * 0.5)

                    sl_price_atr = current_price + current_atr * atr_sl_mult
                    tp_price_atr = current_price - current_atr * atr_tp_mult

                    # Use optimal stops
                    sl_price = min(sl_price_pct, sl_price_atr)
                    tp_price = min(tp_price_pct, tp_price_atr)

                    self.sell(sl=sl_price, tp=tp_price, size=position_confidence)

        else:
            # Exit management - more sophisticated regime-based exits
            if self.position.is_long:
                # Primary exit: regime changes away from Bull
                if current_regime == -1:  # Changed to Bear
                    self.position.close()

                # Secondary exit: transition probability drops significantly
                elif prob_to_bull < self.min_confidence * 0.5:
                    self.position.close()

                # Trailing stop in strong Bull regime
                elif current_regime == 1 and prob_to_bull > 0.6:
                    trail_distance = current_atr * 1.5
                    new_sl = current_price - trail_distance
                    if hasattr(self.position, 'sl') and new_sl > self.position.sl:
                        self.position.sl = new_sl

            elif self.position.is_short:
                # Primary exit: regime changes away from Bear
                if current_regime == 1:  # Changed to Bull
                    self.position.close()

                # Secondary exit: transition probability drops significantly
                elif prob_to_bear < self.min_confidence * 0.5:
                    self.position.close()

                # Trailing stop in strong Bear regime
                elif current_regime == -1 and prob_to_bear > 0.6:
                    trail_distance = current_atr * 1.5
                    new_sl = current_price + trail_distance
                    if hasattr(self.position, 'sl') and new_sl < self.position.sl:
                        self.position.sl = new_sl

# Run single backtest (default behavior)
print("\n🌙 ===== MARKOV CHAIN BASE STRATEGY - ENHANCED ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD} bars")
print(f"Z-Score Threshold: ±{Z_SCORE_THRESHOLD:.3f} std deviations")
print(f"Min Confidence: {MIN_CONFIDENCE:.1%}")
print(f"Regime Smoothing: {REGIME_SMOOTHING} bars")
print(f"Stop Loss: {STOP_LOSS_PERCENT}% / ATR×{ATR_MULTIPLIER_SL}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}% / ATR×{ATR_MULTIPLIER_TP}")

bt = Backtest(data, MarkovChainBase, cash=POSITION_SIZE, commission=0.00045)
stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MARKOV CHAIN BASE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(MarkovChainBase, 'MarkovChainBase')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MarkovChainBase.csv")