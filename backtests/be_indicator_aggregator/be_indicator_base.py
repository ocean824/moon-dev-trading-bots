"""
BE-Indicator Aggregator Toolkit - Base Strategy
=============================================

This strategy demonstrates how to translate Pine Script's BE-Indicator Aggregator
logic into Python backtesting framework. The BE-Indicator uses complex condition
logic with 10 external sources (ES1-ES10) and processes signals using OR, AND,
and ATLEAST operators.

Pine Script Condition Format:
- L-OR: ES1|G|50, ES2|L|30  (Long OR condition: ES1 > 50 OR ES2 < 30)
- S-AND: ES3|G|70, ES4|L|30  (Short AND condition: ES3 > 70 AND ES4 < 30)
- L-ATLEAST2: ES1|G|50, ES2|G|60, ES3|G|40  (At least 2 conditions must be true)

External Sources (ES1-ES10) can be any indicator like RSI, MACD, Moving Averages, etc.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta
import talib
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's BE-Indicator Aggregator Base Strategy Loading... 🌙")

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
TAKE_PROFIT_PERCENT = 3.0  # Default take profit
STOP_LOSS_PERCENT = 1.5    # Default stop loss

# Condition builder configuration
USE_COMPLEX_CONDITIONS = True  # Enable complex condition logic

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")


class BEIndicatorBase(Strategy):
    """
    Base implementation of BE-Indicator Aggregator logic

    This strategy demonstrates:
    1. Setting up 10 external sources (ES1-ES10) as different indicators
    2. Implementing condition logic (OR, AND, ATLEAST)
    3. Generating long/short signals based on complex conditions
    4. Managing positions with SL/TP
    """

    # Strategy parameters
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    # Indicator periods for ES1-ES10
    es1_period = 14  # RSI period
    es2_period = 20  # SMA period
    es3_period = 50  # EMA period
    es4_period = 12  # MACD fast
    es5_period = 26  # MACD slow
    es6_period = 9   # MACD signal
    es7_period = 20  # Bollinger Bands period
    es8_period = 14  # ATR period
    es9_period = 14  # Stochastic period
    es10_period = 10 # CCI period

    def init(self):
        """Initialize all 10 external sources as different indicators"""

        # Prepare data series
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # ES1: RSI (0-100 range)
        self.es1_rsi = ta.rsi(close, length=self.es1_period)
        self.es1_rsi = self.es1_rsi.fillna(50)

        # ES2: SMA vs Price (percentage difference)
        sma = ta.sma(close, length=self.es2_period)
        self.es2_sma_diff = ((close - sma) / sma * 100)
        self.es2_sma_diff = self.es2_sma_diff.fillna(0)

        # ES3: EMA vs Price (percentage difference)
        ema = ta.ema(close, length=self.es3_period)
        self.es3_ema_diff = ((close - ema) / ema * 100)
        self.es3_ema_diff = self.es3_ema_diff.fillna(0)

        # ES4: MACD Line (normalized to 0-100)
        macd_result = ta.macd(close, fast=self.es4_period, slow=self.es5_period, signal=self.es6_period)
        if macd_result is not None and len(macd_result.columns) >= 3:
            macd_line = macd_result.iloc[:, 0]  # MACD line
            macd_signal = macd_result.iloc[:, 2]  # Signal line
            self.es4_macd = ((macd_line - macd_line.min()) / (macd_line.max() - macd_line.min() + 0.0001) * 100)
            self.es5_macd_signal = ((macd_signal - macd_signal.min()) / (macd_signal.max() - macd_signal.min() + 0.0001) * 100)
        else:
            self.es4_macd = pd.Series(50, index=close.index)
            self.es5_macd_signal = pd.Series(50, index=close.index)

        # ES6: Bollinger Band position (0 = lower band, 100 = upper band)
        bb_result = ta.bbands(close, length=self.es7_period, std=2.0)
        if bb_result is not None and len(bb_result.columns) >= 3:
            bb_lower = bb_result.iloc[:, 0]
            bb_upper = bb_result.iloc[:, 2]
            bb_width = bb_upper - bb_lower
            self.es6_bb_position = ((close - bb_lower) / (bb_width + 0.0001) * 100).clip(0, 100)
        else:
            self.es6_bb_position = pd.Series(50, index=close.index)

        # ES7: ATR (normalized to percentage of price)
        atr = ta.atr(high, low, close, length=self.es8_period)
        self.es7_atr_pct = (atr / close * 100).clip(0, 10) * 10  # Scale to 0-100
        self.es7_atr_pct = self.es7_atr_pct.fillna(50)

        # ES8: Stochastic %K (0-100 range)
        stoch_result = ta.stoch(high, low, close, k=self.es9_period, d=3)
        if stoch_result is not None and len(stoch_result.columns) >= 1:
            self.es8_stoch = stoch_result.iloc[:, 0]  # %K line
            # Ensure same length as close by reindexing
            self.es8_stoch = self.es8_stoch.reindex(close.index, fill_value=50)
        else:
            self.es8_stoch = pd.Series(50, index=close.index)

        # ES9: CCI (Commodity Channel Index, normalized to 0-100)
        cci = ta.cci(high, low, close, length=self.es10_period)
        self.es9_cci = ((cci + 200) / 4).clip(0, 100)  # Normalize from [-200, 200] to [0, 100]
        self.es9_cci = self.es9_cci.fillna(50)

        # ES10: Volume ratio (current volume vs average, normalized)
        volume_ma = volume.rolling(window=20).mean()
        self.es10_volume_ratio = ((volume / (volume_ma + 1)) * 50).clip(0, 100)
        self.es10_volume_ratio = self.es10_volume_ratio.fillna(50)

        # Convert all to numpy arrays for indexing
        self.es1 = self.I(lambda: self.es1_rsi.values)
        self.es2 = self.I(lambda: self.es2_sma_diff.values)
        self.es3 = self.I(lambda: self.es3_ema_diff.values)
        self.es4 = self.I(lambda: self.es4_macd.values)
        self.es5 = self.I(lambda: self.es5_macd_signal.values)
        self.es6 = self.I(lambda: self.es6_bb_position.values)
        self.es7 = self.I(lambda: self.es7_atr_pct.values)
        self.es8 = self.I(lambda: self.es8_stoch.values)
        self.es9 = self.I(lambda: self.es9_cci.values)
        self.es10 = self.I(lambda: self.es10_volume_ratio.values)

    def check_condition(self, source, operator, threshold):
        """
        Check a single condition

        Args:
            source: The indicator value (ES1-ES10)
            operator: 'G' for greater than, 'L' for less than, 'E' for equals
            threshold: The threshold value to compare against

        Returns:
            bool: True if condition is met
        """
        if operator == 'G':
            return source > threshold
        elif operator == 'L':
            return source < threshold
        elif operator == 'E':
            return abs(source - threshold) < 1  # Allow small tolerance for equals
        return False

    def evaluate_conditions(self, condition_type, conditions):
        """
        Evaluate complex condition logic

        Args:
            condition_type: 'OR', 'AND', or 'ATLEAST{n}'
            conditions: List of (source_value, operator, threshold) tuples

        Returns:
            bool: True if the complex condition is satisfied
        """
        results = [self.check_condition(src, op, thresh) for src, op, thresh in conditions]

        if condition_type == 'OR':
            return any(results)
        elif condition_type == 'AND':
            return all(results)
        elif condition_type.startswith('ATLEAST'):
            required = int(condition_type.replace('ATLEAST', ''))
            return sum(results) >= required

        return False

    def next(self):
        """
        Main trading logic implementing BE-Indicator conditions

        Default conditions:
        - Long: RSI < 30 OR (MACD crossover AND BB position < 20)
        - Short: RSI > 70 OR (MACD crossunder AND BB position > 80)
        """

        if len(self.data) < 50:  # Need enough data for indicators
            return

        # Get current indicator values
        current_es1 = self.es1[-1]  # RSI
        current_es2 = self.es2[-1]  # SMA diff
        current_es3 = self.es3[-1]  # EMA diff
        current_es4 = self.es4[-1]  # MACD
        current_es5 = self.es5[-1]  # MACD Signal
        current_es6 = self.es6[-1]  # BB position
        current_es7 = self.es7[-1]  # ATR
        current_es8 = self.es8[-1]  # Stochastic
        current_es9 = self.es9[-1]  # CCI
        current_es10 = self.es10[-1]  # Volume ratio

        # Skip if any indicator is NaN
        if any(pd.isna([current_es1, current_es4, current_es6, current_es8])):
            return

        if not self.position:
            # LONG CONDITIONS
            # Complex condition: (RSI < 30) OR (MACD > Signal AND BB < 20) OR (Stoch < 20 AND Volume > 150%)
            long_conditions = [
                # Condition 1: Oversold RSI
                [(current_es1, 'L', 35)],

                # Condition 2: MACD bullish with BB oversold
                [(current_es4, 'G', current_es5), (current_es6, 'L', 20)],

                # Condition 3: Stoch oversold with volume spike
                [(current_es8, 'L', 35), (current_es10, 'G', 60)]
            ]

            # Check if any condition group is satisfied
            long_signal = False
            for condition_group in long_conditions:
                if self.evaluate_conditions('AND', condition_group):
                    long_signal = True
                    break

            # Alternative: Check ATLEAST 2 bullish indicators
            bullish_indicators = [
                (current_es1, 'L', 40),      # RSI oversold
                (current_es4, 'G', current_es5),  # MACD crossover
                (current_es6, 'L', 30),      # BB lower zone
                (current_es8, 'L', 30),      # Stoch oversold
                (current_es2, 'G', 1),        # Price above SMA
            ]

            if not long_signal:
                long_signal = self.evaluate_conditions('ATLEAST2', bullish_indicators)

            # SHORT CONDITIONS
            # Complex condition: (RSI > 70) OR (MACD < Signal AND BB > 80) OR (Stoch > 80 AND Volume > 150%)
            short_conditions = [
                # Condition 1: Overbought RSI
                [(current_es1, 'G', 65)],

                # Condition 2: MACD bearish with BB overbought
                [(current_es4, 'L', current_es5), (current_es6, 'G', 80)],

                # Condition 3: Stoch overbought with volume spike
                [(current_es8, 'G', 65), (current_es10, 'G', 60)]
            ]

            # Check if any condition group is satisfied
            short_signal = False
            for condition_group in short_conditions:
                if self.evaluate_conditions('AND', condition_group):
                    short_signal = True
                    break

            # Alternative: Check ATLEAST 2 bearish indicators
            bearish_indicators = [
                (current_es1, 'G', 60),      # RSI overbought
                (current_es4, 'L', current_es5),  # MACD crossunder
                (current_es6, 'G', 70),      # BB upper zone
                (current_es8, 'G', 70),      # Stoch overbought
                (current_es2, 'L', -1),       # Price below SMA
            ]

            if not short_signal:
                short_signal = self.evaluate_conditions('ATLEAST2', bearish_indicators)

            # Execute trades based on signals
            current_price = self.data.Close[-1]

            if long_signal:
                # Calculate stop loss and take profit
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)

                # Enter long position with 95% of available cash
                self.buy(sl=sl_price, tp=tp_price, size=0.95)

            elif short_signal:
                # Calculate stop loss and take profit for short
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)

                # Enter short position with 95% of available cash
                self.sell(sl=sl_price, tp=tp_price, size=0.95)


# Run single backtest
bt = Backtest(data, BEIndicatorBase, cash=10000000, commission=0.00045)

print("\n🌙 ===== BE-INDICATOR BASE STRATEGY ===== 🌙")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print("Conditions: Complex multi-indicator logic with OR/AND/ATLEAST operators")

stats = bt.run()
print("\n" + "="*80)
print("BACKTEST RESULTS:")
print("="*80)
print(stats)
print("="*80)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING BE-INDICATOR BASE ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(BEIndicatorBase, 'BEIndicatorBase')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/BEIndicatorBase.csv")