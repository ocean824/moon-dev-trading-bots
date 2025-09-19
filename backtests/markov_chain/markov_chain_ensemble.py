"""
Moon Dev's Markov Chain Ensemble Strategy
==========================================
Advanced Markov Chain strategy that uses multiple regime detection methods
and combines them into an ensemble signal for robust trading.

Uses Z-score, RSI, MACD, Volume, and Price Action for regime detection.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import talib
import pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Markov Chain Ensemble Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Markov Chain parameters
LOOKBACK_PERIOD = 50
Z_SCORE_THRESHOLD = 1/3
SMOOTHING_ALPHA = 1
MIN_CONFIDENCE = 0.35  # Higher threshold for ensemble

# Ensemble indicator parameters
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2
ATR_PERIOD = 14
VOLUME_PERIOD = 20
ADX_PERIOD = 14

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

class MarkovChainEnsemble(Strategy):
    """
    Markov Chain Ensemble Strategy
    - Multiple regime detection methods combined
    - Z-score based regime (primary)
    - RSI-based regime (momentum)
    - MACD-based regime (trend)
    - Volume-based regime (participation)
    - Price action regime (Bollinger Bands)
    - ADX for trend strength confirmation
    - Ensemble voting for final regime decision
    """

    # Markov parameters
    lookback = LOOKBACK_PERIOD
    z_threshold = Z_SCORE_THRESHOLD
    smoothing = SMOOTHING_ALPHA
    min_confidence = MIN_CONFIDENCE

    # Indicator parameters
    rsi_period = RSI_PERIOD
    macd_fast = MACD_FAST
    macd_slow = MACD_SLOW
    macd_signal = MACD_SIGNAL
    bb_period = BOLLINGER_PERIOD
    bb_std = BOLLINGER_STD
    atr_period = ATR_PERIOD
    vol_period = VOLUME_PERIOD
    adx_period = ADX_PERIOD

    # Risk management
    sl_pct = STOP_LOSS_PERCENT / 100
    tp_pct = TAKE_PROFIT_PERCENT / 100

    def calculate_regime_zscore(self, returns, z_scores):
        """Z-score based regime detection"""
        regimes = np.zeros(len(z_scores))
        regimes[z_scores > self.z_threshold] = 1
        regimes[z_scores < -self.z_threshold] = -1
        return regimes

    def calculate_regime_rsi(self, rsi):
        """RSI-based regime detection"""
        regimes = np.zeros(len(rsi))
        regimes[rsi > 60] = 1  # Bullish momentum
        regimes[rsi < 40] = -1  # Bearish momentum
        return regimes

    def calculate_regime_macd(self, macd_hist):
        """MACD-based regime detection"""
        regimes = np.zeros(len(macd_hist))
        # Use smoothed MACD histogram
        smoothed = pd.Series(macd_hist).rolling(5).mean().values
        regimes[smoothed > 0] = 1
        regimes[smoothed < 0] = -1
        return regimes

    def calculate_regime_volume(self, volume, volume_ma):
        """Volume-based regime detection"""
        regimes = np.zeros(len(volume))
        vol_ratio = volume / volume_ma
        # High volume with price increase = bullish
        # High volume with price decrease = bearish
        for i in range(1, len(volume)):
            if vol_ratio[i] > 1.2:  # High volume
                if self.data.Close[i] > self.data.Close[i-1]:
                    regimes[i] = 1
                else:
                    regimes[i] = -1
        return regimes

    def calculate_regime_bb(self, close, upper, lower, middle):
        """Bollinger Bands based regime detection"""
        regimes = np.zeros(len(close))
        for i in range(len(close)):
            if close[i] > upper[i]:
                regimes[i] = 1  # Breaking upper band
            elif close[i] < lower[i]:
                regimes[i] = -1  # Breaking lower band
            elif close[i] > middle[i]:
                regimes[i] = 0.5  # Above middle, mild bullish
            elif close[i] < middle[i]:
                regimes[i] = -0.5  # Below middle, mild bearish
        return regimes

    def calculate_ensemble_regime(self, regimes_list, weights=None):
        """Combine multiple regime signals into ensemble"""
        if weights is None:
            weights = np.ones(len(regimes_list)) / len(regimes_list)

        ensemble = np.zeros(len(regimes_list[0]))
        for i, regime in enumerate(regimes_list):
            ensemble += regime * weights[i]

        # Convert weighted average to discrete regime
        final_regime = np.zeros(len(ensemble))
        final_regime[ensemble > 0.3] = 1
        final_regime[ensemble < -0.3] = -1

        return final_regime, ensemble

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

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate returns
        returns = close.pct_change()

        # 1. Z-score regime
        rolling_mean = returns.rolling(window=self.lookback).mean()
        rolling_std = returns.rolling(window=self.lookback).std()
        z_scores = (returns - rolling_mean) / rolling_std
        regime_zscore = self.calculate_regime_zscore(returns.values, z_scores.values)

        # 2. RSI regime
        rsi = talib.RSI(close.values, timeperiod=self.rsi_period)
        regime_rsi = self.calculate_regime_rsi(rsi)

        # 3. MACD regime
        macd, macd_signal, macd_hist = talib.MACD(close.values,
                                                   fastperiod=self.macd_fast,
                                                   slowperiod=self.macd_slow,
                                                   signalperiod=self.macd_signal)
        regime_macd = self.calculate_regime_macd(macd_hist)

        # 4. Volume regime
        volume_ma = volume.rolling(window=self.vol_period).mean()
        regime_volume = self.calculate_regime_volume(volume.values, volume_ma.values)

        # 5. Bollinger Bands regime
        bb = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        upper_band = bb[f'BBU_{self.bb_period}_{self.bb_std}'].values if f'BBU_{self.bb_period}_{self.bb_std}' in bb.columns else close.values * 1.02
        lower_band = bb[f'BBL_{self.bb_period}_{self.bb_std}'].values if f'BBL_{self.bb_period}_{self.bb_std}' in bb.columns else close.values * 0.98
        middle_band = bb[f'BBM_{self.bb_period}_{self.bb_std}'].values if f'BBM_{self.bb_period}_{self.bb_std}' in bb.columns else close.values
        regime_bb = self.calculate_regime_bb(close.values, upper_band, lower_band, middle_band)

        # Calculate ADX for trend strength
        adx = talib.ADX(high.values, low.values, close.values, timeperiod=self.adx_period)

        # Combine regimes with weights
        # Higher weights for more reliable indicators
        weights = [0.3,   # Z-score (primary)
                   0.2,   # RSI
                   0.2,   # MACD
                   0.15,  # Volume
                   0.15]  # Bollinger Bands

        regimes_list = [regime_zscore, regime_rsi, regime_macd, regime_volume, regime_bb]
        ensemble_regime, ensemble_score = self.calculate_ensemble_regime(regimes_list, weights)

        # Calculate transition probabilities for ensemble regime
        transition_probs_to_bull = []
        transition_probs_to_bear = []
        confidence_scores = []

        for i in range(len(close)):
            if i < self.lookback * 2:
                transition_probs_to_bull.append(0.33)
                transition_probs_to_bear.append(0.33)
                confidence_scores.append(0)
            else:
                window_states = ensemble_regime[i - self.lookback:i]
                trans_matrix = self.calculate_transition_matrix(window_states)
                current_state = ensemble_regime[i - 1] if i > 0 else 0

                prob_to_bull = self.get_transition_probability(current_state, 1, trans_matrix)
                prob_to_bear = self.get_transition_probability(current_state, -1, trans_matrix)

                transition_probs_to_bull.append(prob_to_bull)
                transition_probs_to_bear.append(prob_to_bear)

                # Calculate confidence based on agreement between indicators
                agreement = 0
                for regime in regimes_list:
                    if not np.isnan(regime[i]):
                        if ensemble_regime[i] == 1 and regime[i] > 0:
                            agreement += 1
                        elif ensemble_regime[i] == -1 and regime[i] < 0:
                            agreement += 1
                        elif ensemble_regime[i] == 0 and abs(regime[i]) < 0.5:
                            agreement += 1

                confidence = agreement / len(regimes_list)
                confidence_scores.append(confidence)

        # Store indicators
        self.regime = self.I(lambda: ensemble_regime, name='regime')
        self.ensemble_score = self.I(lambda: ensemble_score, name='ensemble_score')
        self.prob_to_bull = self.I(lambda: np.array(transition_probs_to_bull), name='prob_to_bull')
        self.prob_to_bear = self.I(lambda: np.array(transition_probs_to_bear), name='prob_to_bear')
        self.confidence = self.I(lambda: np.array(confidence_scores), name='confidence')
        self.rsi = self.I(lambda: rsi, name='rsi')
        self.macd_hist = self.I(lambda: macd_hist, name='macd_hist')
        self.adx = self.I(lambda: adx, name='adx')
        self.bb_upper = self.I(lambda: upper_band, name='bb_upper')
        self.bb_lower = self.I(lambda: lower_band, name='bb_lower')

        # ATR for stops
        self.atr = self.I(talib.ATR, high, low, close, timeperiod=self.atr_period)

    def next(self):
        # Skip if not enough data
        if len(self.data) < self.lookback * 2:
            return

        # Get indicators
        current_regime = self.regime[-1]
        prev_regime = self.regime[-2] if len(self.regime) > 1 else 0
        ensemble_score = self.ensemble_score[-1]
        prob_to_bull = self.prob_to_bull[-1]
        prob_to_bear = self.prob_to_bear[-1]
        confidence = self.confidence[-1]
        rsi_val = self.rsi[-1] if not np.isnan(self.rsi[-1]) else 50
        macd_hist_val = self.macd_hist[-1] if not np.isnan(self.macd_hist[-1]) else 0
        adx_val = self.adx[-1] if not np.isnan(self.adx[-1]) else 25
        bb_upper = self.bb_upper[-1]
        bb_lower = self.bb_lower[-1]

        current_price = self.data.Close[-1]
        current_atr = self.atr[-1] if not np.isnan(self.atr[-1]) else current_price * 0.02

        # Position management
        if not self.position:
            # Long entry - strong ensemble signal required
            long_regime = current_regime == 1 and prev_regime != 1
            long_confidence = prob_to_bull >= self.min_confidence and confidence >= 0.6
            long_trend = adx_val > 25  # Trending market
            long_ensemble = ensemble_score > 0.4  # Strong bullish consensus
            long_price = current_price > bb_lower  # Not at extreme low

            if long_regime and long_confidence and long_trend and long_ensemble and long_price:
                # Position sizing based on confidence and ADX
                adx_factor = min(adx_val / 40, 1.0)  # Scale by trend strength
                position_scale = min(confidence * prob_to_bull * adx_factor, 1.0)

                # Dynamic stops based on volatility and trend strength
                sl_mult = 2.0 if adx_val > 30 else 2.5
                tp_mult = 3.0 if adx_val > 30 else 2.5

                # Adjust for Bollinger Band position
                bb_range = bb_upper - bb_lower
                if current_price < (bb_lower + bb_range * 0.2):
                    tp_mult *= 1.5  # More room to run from oversold

                sl_price = current_price - current_atr * sl_mult
                tp_price = current_price + current_atr * tp_mult

                self.buy(sl=sl_price, tp=tp_price, size=position_scale)

            # Short entry - strong ensemble signal required
            short_regime = current_regime == -1 and prev_regime != -1
            short_confidence = prob_to_bear >= self.min_confidence and confidence >= 0.6
            short_trend = adx_val > 25  # Trending market
            short_ensemble = ensemble_score < -0.4  # Strong bearish consensus
            short_price = current_price < bb_upper  # Not at extreme high

            if short_regime and short_confidence and short_trend and short_ensemble and short_price:
                # Position sizing based on confidence and ADX
                adx_factor = min(adx_val / 40, 1.0)
                position_scale = min(confidence * prob_to_bear * adx_factor, 1.0)

                # Dynamic stops
                sl_mult = 2.0 if adx_val > 30 else 2.5
                tp_mult = 3.0 if adx_val > 30 else 2.5

                # Adjust for Bollinger Band position
                bb_range = bb_upper - bb_lower
                if current_price > (bb_upper - bb_range * 0.2):
                    tp_mult *= 1.5  # More room to run from overbought

                sl_price = current_price + current_atr * sl_mult
                tp_price = current_price - current_atr * tp_mult

                self.sell(sl=sl_price, tp=tp_price, size=position_scale)

        else:
            # Advanced exit management
            if self.position.is_long:
                # Exit conditions
                exit_regime = current_regime == -1
                exit_confidence = confidence < 0.4 or prob_to_bull < 0.2
                exit_ensemble = ensemble_score < -0.2
                exit_bb = current_price > bb_upper * 1.01  # Extended above bands
                exit_adx = adx_val < 20 and prev_regime == 1  # Trend weakening

                if exit_regime or exit_confidence or exit_ensemble or exit_bb or exit_adx:
                    self.position.close()

                # Trail stop in strong trends
                elif adx_val > 35 and ensemble_score > 0.5:
                    new_sl = current_price - current_atr * 1.5
                    if new_sl > self.position.sl:
                        self.position.sl = new_sl

            elif self.position.is_short:
                # Exit conditions
                exit_regime = current_regime == 1
                exit_confidence = confidence < 0.4 or prob_to_bear < 0.2
                exit_ensemble = ensemble_score > 0.2
                exit_bb = current_price < bb_lower * 0.99  # Extended below bands
                exit_adx = adx_val < 20 and prev_regime == -1  # Trend weakening

                if exit_regime or exit_confidence or exit_ensemble or exit_bb or exit_adx:
                    self.position.close()

                # Trail stop in strong trends
                elif adx_val > 35 and ensemble_score < -0.5:
                    new_sl = current_price + current_atr * 1.5
                    if new_sl < self.position.sl:
                        self.position.sl = new_sl

# Run single backtest
print("\n🌙 ===== MARKOV CHAIN ENSEMBLE STRATEGY ===== 🌙")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Min Confidence: {MIN_CONFIDENCE}")
print(f"Using 5 regime detection methods:")
print("  1. Z-score (30% weight)")
print("  2. RSI (20% weight)")
print("  3. MACD (20% weight)")
print("  4. Volume (15% weight)")
print("  5. Bollinger Bands (15% weight)")

bt = Backtest(data, MarkovChainEnsemble, cash=POSITION_SIZE, commission=0.00045)
stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MARKOV CHAIN ENSEMBLE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    results = test_on_all_data(MarkovChainEnsemble, 'MarkovChainEnsemble')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MarkovChainEnsemble.csv")