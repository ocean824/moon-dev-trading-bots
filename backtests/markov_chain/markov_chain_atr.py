"""
Moon Dev's Markov Chain [3D] ATR Strategy - Enhanced Version
=============================================================
Markov Chain strategy with advanced ATR-based position sizing and dynamic stops.

Key Enhancements:
- ATR-based position sizing adjusted for volatility regimes
- Dynamic stop losses that adapt to market conditions
- Volatility filters to avoid choppy markets
- Position sizing based on both probability and volatility
- Trailing stops using ATR bands
- Multi-timeframe ATR analysis for better volatility assessment
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import talib
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Markov Chain ATR Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Markov Chain parameters (from TradingView indicator)
LOOKBACK_PERIOD = 50
Z_SCORE_THRESHOLD = 1/3
SMOOTHING_ALPHA = 1
MIN_CONFIDENCE = 0.35
REGIME_SMOOTHING = 3

# ATR parameters
ATR_PERIOD = 14
ATR_FAST_PERIOD = 7  # For volatility regime detection
ATR_SLOW_PERIOD = 28  # For volatility regime detection
ATR_MULTIPLIER_SL = 1.5  # Tighter stops in trending markets
ATR_MULTIPLIER_TP = 3.0
VOLATILITY_FILTER = True
MAX_VOLATILITY = 0.06  # Max daily volatility to trade
MIN_VOLATILITY = 0.005  # Min volatility (avoid dead markets)

# Risk management
POSITION_SIZE = 1000000
BASE_RISK_PERCENT = 1.5  # Base risk per trade
MAX_POSITION_SCALE = 1.0  # Maximum position size multiplier

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class MarkovChainATR(Strategy):
    """
    Markov Chain ATR Strategy - Enhanced Version
    - Uses Markov Chain for regime detection with Z-score
    - Multi-timeframe ATR for volatility regime classification
    - Dynamic position sizing based on risk and volatility
    - Adaptive stops that adjust to market conditions
    - Volatility filtering to avoid extreme conditions
    """

    # Markov parameters
    lookback = LOOKBACK_PERIOD
    z_threshold = Z_SCORE_THRESHOLD
    smoothing = SMOOTHING_ALPHA
    min_confidence = MIN_CONFIDENCE
    regime_smoothing = REGIME_SMOOTHING

    # ATR parameters
    atr_period = ATR_PERIOD
    atr_fast_period = ATR_FAST_PERIOD
    atr_slow_period = ATR_SLOW_PERIOD
    atr_mult_sl = ATR_MULTIPLIER_SL
    atr_mult_tp = ATR_MULTIPLIER_TP
    volatility_filter = VOLATILITY_FILTER
    max_volatility = MAX_VOLATILITY
    min_volatility = MIN_VOLATILITY
    base_risk_pct = BASE_RISK_PERCENT / 100
    max_position_scale = MAX_POSITION_SCALE

    def calculate_regime(self, returns, z_scores):
        """
        Determine market regime based on Z-score with smoothing
        Returns: 1 (Bull), 0 (Neutral), -1 (Bear)
        """
        regimes = np.zeros(len(z_scores))

        # Classify based on Z-score thresholds
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
            final_regimes = np.zeros(len(smoothed_regimes))
            final_regimes[smoothed_regimes > 0.5] = 1
            final_regimes[smoothed_regimes < -0.5] = -1
            return final_regimes

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

    def calculate_position_size(self, atr_value, price, confidence, volatility_regime):
        """
        Calculate position size based on ATR, confidence, and volatility regime
        """
        # Base position size using ATR-based risk
        risk_amount = self.base_risk_pct * POSITION_SIZE
        stop_distance = atr_value * self.atr_mult_sl

        # Position size based on risk
        position_value = risk_amount / (stop_distance / price)

        # Scale by confidence and volatility regime
        volatility_scale = 1.0
        if volatility_regime == 'high':
            volatility_scale = 0.7
        elif volatility_regime == 'extreme':
            volatility_scale = 0.5
        elif volatility_regime == 'low':
            volatility_scale = 1.2

        position_value *= confidence * volatility_scale

        # Normalize to [0, 1] for backtesting, apply max scale
        return min(position_value / POSITION_SIZE, self.max_position_scale)

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate returns
        returns = close.pct_change()

        # Calculate rolling Z-score of returns (exactly as per indicator)
        rolling_mean = returns.rolling(window=self.lookback, min_periods=2).mean()
        rolling_std = returns.rolling(window=self.lookback, min_periods=2).std()

        # Handle division by zero
        z_scores = np.zeros(len(returns))
        valid_std = rolling_std > 0.0001
        z_scores[valid_std] = ((returns - rolling_mean) / rolling_std)[valid_std]

        # Determine regimes
        regimes = self.calculate_regime(returns.values, z_scores)

        # Calculate multiple ATR timeframes for volatility regime
        atr_values = talib.ATR(high.values, low.values, close.values,
                              timeperiod=self.atr_period)
        atr_fast = talib.ATR(high.values, low.values, close.values,
                            timeperiod=self.atr_fast_period)
        atr_slow = talib.ATR(high.values, low.values, close.values,
                            timeperiod=self.atr_slow_period)

        # Calculate ATR ratio for volatility regime detection
        atr_ratio = np.zeros(len(atr_fast))
        valid_idx = (atr_slow > 0) & ~np.isnan(atr_slow) & ~np.isnan(atr_fast)
        atr_ratio[valid_idx] = atr_fast[valid_idx] / atr_slow[valid_idx]

        # Determine volatility regime
        volatility_regime = []
        for i in range(len(atr_ratio)):
            if atr_ratio[i] > 1.5:
                volatility_regime.append('extreme')
            elif atr_ratio[i] > 1.2:
                volatility_regime.append('high')
            elif atr_ratio[i] < 0.8:
                volatility_regime.append('low')
            else:
                volatility_regime.append('normal')

        # Calculate transition probabilities
        transition_probs_to_bull = []
        transition_probs_to_bear = []
        regime_strength = []

        for i in range(len(close)):
            if i < self.lookback * 2:
                transition_probs_to_bull.append(0.33)
                transition_probs_to_bear.append(0.33)
                regime_strength.append(0)
            else:
                window_states = regimes[i - self.lookback:i]
                trans_matrix = self.calculate_transition_matrix(window_states)
                current_state = regimes[i - 1] if i > 0 else 0

                # Calculate probability of transitioning
                prob_to_bull = self.get_transition_probability(current_state, 1, trans_matrix)
                prob_to_bear = self.get_transition_probability(current_state, -1, trans_matrix)

                # Weight probabilities by regime strength (Z-score magnitude)
                z_strength = abs(z_scores[i]) if i < len(z_scores) else 0.5
                z_strength = min(z_strength, 2.0) / 2.0  # Normalize to [0, 1]

                # Adjust probabilities based on regime strength
                prob_to_bull *= (1 + z_strength * 0.5)
                prob_to_bear *= (1 + z_strength * 0.5)

                transition_probs_to_bull.append(min(prob_to_bull, 1.0))
                transition_probs_to_bear.append(min(prob_to_bear, 1.0))

                # Calculate regime persistence strength
                if current_state == 1:
                    strength = self.get_transition_probability(1, 1, trans_matrix)
                elif current_state == -1:
                    strength = self.get_transition_probability(-1, -1, trans_matrix)
                else:
                    strength = 0.5
                regime_strength.append(strength)

        # Store indicators
        self.regime = self.I(lambda: regimes, name='regime')
        self.z_score = self.I(lambda: z_scores, name='z_score')
        self.prob_to_bull = self.I(lambda: np.array(transition_probs_to_bull), name='prob_to_bull')
        self.prob_to_bear = self.I(lambda: np.array(transition_probs_to_bear), name='prob_to_bear')
        self.atr = self.I(lambda: atr_values, name='atr')
        self.atr_ratio = self.I(lambda: atr_ratio, name='atr_ratio')
        self.volatility_regime = self.I(lambda: volatility_regime, name='vol_regime')
        self.regime_strength = self.I(lambda: np.array(regime_strength), name='regime_strength')

        # Additional indicators for filtering
        self.volatility = self.I(lambda: returns.rolling(20).std().values, name='volatility')
        self.adx = self.I(talib.ADX, high, low, close, timeperiod=14)
        self.rsi = self.I(talib.RSI, close, timeperiod=14)
        self.volume_sma = self.I(talib.SMA, volume, timeperiod=20)

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.lookback * 2:
            return

        # Get current and previous regime
        current_regime = self.regime[-1]
        prev_regime = self.regime[-2] if len(self.regime) > 1 else 0

        # Get volatility regime
        vol_regime = self.volatility_regime[-1] if isinstance(self.volatility_regime[-1], str) else 'normal'

        # Get indicators
        prob_to_bull = self.prob_to_bull[-1]
        prob_to_bear = self.prob_to_bear[-1]
        current_atr = self.atr[-1] if not np.isnan(self.atr[-1]) else self.data.Close[-1] * 0.02
        regime_str = self.regime_strength[-1]
        current_price = self.data.Close[-1]

        # Volatility filter - enhanced with both high and low volatility checks
        if self.volatility_filter:
            current_vol = self.volatility[-1] if not np.isnan(self.volatility[-1]) else 0
            if current_vol > self.max_volatility:
                # Close positions in extreme volatility
                if self.position:
                    self.position.close()
                return  # Skip new entries in high volatility
            elif current_vol < self.min_volatility:
                return  # Skip trading in dead markets

        # ADX filter - only trade in trending markets
        adx_val = self.adx[-1] if not np.isnan(self.adx[-1]) else 25
        if adx_val < 20:  # Weak trend
            return

        # Position management
        if not self.position:
            # Long entry: Transitioning to Bull regime with sufficient confidence
            if (current_regime == 1 and prev_regime != 1 and
                prob_to_bull >= self.min_confidence):

                # Additional filters
                rsi_filter = 30 < self.rsi[-1] < 70 if not np.isnan(self.rsi[-1]) else True
                volume_filter = self.data.Volume[-1] > self.volume_sma[-1] * 0.8

                if rsi_filter and volume_filter:
                    # Calculate position size based on ATR and volatility regime
                    position_confidence = min(prob_to_bull * (1 + regime_str * 0.3), 1.0)
                    position_size = self.calculate_position_size(
                        current_atr, current_price, position_confidence, vol_regime
                    )

                    # Dynamic stops based on ATR and volatility regime
                    sl_mult = self.atr_mult_sl
                    tp_mult = self.atr_mult_tp

                    # Adjust multipliers based on volatility regime
                    if vol_regime == 'high':
                        sl_mult *= 1.3  # Wider stops in high volatility
                        tp_mult *= 1.2
                    elif vol_regime == 'low':
                        sl_mult *= 0.8  # Tighter stops in low volatility
                        tp_mult *= 0.9

                    # Adjust for regime strength
                    if regime_str > 0.7:  # Strong trend
                        tp_mult *= 1.3  # Wider profit target
                        sl_mult *= 0.9  # Slightly tighter stop

                    sl_price = current_price - current_atr * sl_mult
                    tp_price = current_price + current_atr * tp_mult

                    self.buy(sl=sl_price, tp=tp_price, size=position_size)

            # Short entry: Transitioning to Bear regime with sufficient confidence
            elif (current_regime == -1 and prev_regime != -1 and
                  prob_to_bear >= self.min_confidence):

                # Additional filters
                rsi_filter = 30 < self.rsi[-1] < 70 if not np.isnan(self.rsi[-1]) else True
                volume_filter = self.data.Volume[-1] > self.volume_sma[-1] * 0.8

                if rsi_filter and volume_filter:
                    # Calculate position size
                    position_confidence = min(prob_to_bear * (1 + regime_str * 0.3), 1.0)
                    position_size = self.calculate_position_size(
                        current_atr, current_price, position_confidence, vol_regime
                    )

                    # Dynamic stops based on ATR and volatility regime
                    sl_mult = self.atr_mult_sl
                    tp_mult = self.atr_mult_tp

                    # Adjust multipliers based on volatility regime
                    if vol_regime == 'high':
                        sl_mult *= 1.3
                        tp_mult *= 1.2
                    elif vol_regime == 'low':
                        sl_mult *= 0.8
                        tp_mult *= 0.9

                    # Adjust for regime strength
                    if regime_str > 0.7:
                        tp_mult *= 1.3
                        sl_mult *= 0.9

                    sl_price = current_price + current_atr * sl_mult
                    tp_price = current_price - current_atr * tp_mult

                    self.sell(sl=sl_price, tp=tp_price, size=position_size)

        else:
            # Exit management with advanced ATR-based trailing stops
            if self.position.is_long:
                # Exit on regime change to Bear
                if current_regime == -1:
                    self.position.close()

                # Exit if probability drops significantly
                elif prob_to_bull < self.min_confidence * 0.4:
                    self.position.close()

                # Volatility-based exit
                elif vol_regime == 'extreme':
                    self.position.close()

                # ATR-based trailing stop with volatility adjustment
                elif current_regime == 1 and prob_to_bull > 0.5:
                    # Tighter trailing in low volatility, wider in high
                    trail_mult = 1.5
                    if vol_regime == 'low':
                        trail_mult = 1.2
                    elif vol_regime == 'high':
                        trail_mult = 2.0

                    # Adjust trailing based on regime strength
                    if regime_str > 0.7:
                        trail_mult *= 0.8  # Tighter trail in strong trends

                    trail_distance = current_atr * trail_mult
                    new_sl = current_price - trail_distance
                    if hasattr(self.position, 'sl') and new_sl > self.position.sl:
                        self.position.sl = new_sl

            elif self.position.is_short:
                # Exit on regime change to Bull
                if current_regime == 1:
                    self.position.close()

                # Exit if probability drops significantly
                elif prob_to_bear < self.min_confidence * 0.4:
                    self.position.close()

                # Volatility-based exit
                elif vol_regime == 'extreme':
                    self.position.close()

                # ATR-based trailing stop with volatility adjustment
                elif current_regime == -1 and prob_to_bear > 0.5:
                    # Adjust trailing based on volatility
                    trail_mult = 1.5
                    if vol_regime == 'low':
                        trail_mult = 1.2
                    elif vol_regime == 'high':
                        trail_mult = 2.0

                    # Adjust for regime strength
                    if regime_str > 0.7:
                        trail_mult *= 0.8

                    trail_distance = current_atr * trail_mult
                    new_sl = current_price + trail_distance
                    if hasattr(self.position, 'sl') and new_sl < self.position.sl:
                        self.position.sl = new_sl

# Run single backtest
print("\n🌙 ===== MARKOV CHAIN ATR STRATEGY - ENHANCED ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD} bars")
print(f"Z-Score Threshold: ±{Z_SCORE_THRESHOLD:.3f} std deviations")
print(f"Min Confidence: {MIN_CONFIDENCE:.1%}")
print(f"ATR Periods: {ATR_PERIOD} (main), {ATR_FAST_PERIOD} (fast), {ATR_SLOW_PERIOD} (slow)")
print(f"ATR Stop Loss Multiplier: {ATR_MULTIPLIER_SL}x")
print(f"ATR Take Profit Multiplier: {ATR_MULTIPLIER_TP}x")
print(f"Volatility Range: {MIN_VOLATILITY:.1%} - {MAX_VOLATILITY:.1%}")
print(f"Base Risk: {BASE_RISK_PERCENT}% per trade")

bt = Backtest(data, MarkovChainATR, cash=POSITION_SIZE, commission=0.00045)
stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MARKOV CHAIN ATR ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    results = test_on_all_data(MarkovChainATR, 'MarkovChainATR')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MarkovChainATR.csv")