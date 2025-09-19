"""
BE-Indicator Aggregator Toolkit - MFI Enhanced Strategy
=======================================================

This strategy enhances the base BE-Indicator with Money Flow Index (MFI) integration.
MFI acts as a volume-weighted RSI, providing better signals for detecting
true buying/selling pressure.

Key Enhancements:
- MFI replaces ES1 as primary oscillator
- Volume-weighted conditions for better signal quality
- Smart money flow detection
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta
import talib
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's BE-Indicator MFI Enhanced Strategy Loading... 🌙")

# Data configuration
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
TAKE_PROFIT_PERCENT = 3.5  # Slightly higher TP with MFI confirmation
STOP_LOSS_PERCENT = 1.5    # Same stop loss
MFI_PERIOD = 14            # Money Flow Index period

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")


class BEIndicatorMFI(Strategy):
    """
    MFI-enhanced implementation of BE-Indicator Aggregator

    Key changes:
    1. MFI as ES1 for volume-weighted momentum
    2. Modified condition logic for money flow patterns
    3. Divergence detection between price and MFI
    """

    # Strategy parameters
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    # Indicator periods
    mfi_period = MFI_PERIOD
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
        """Initialize all indicators with MFI as primary oscillator"""

        # Prepare data series
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # ES1: Money Flow Index (0-100 range)
        # MFI combines price and volume to measure buying/selling pressure
        self.es1_mfi = ta.mfi(high, low, close, volume, length=self.mfi_period)
        self.es1_mfi = self.es1_mfi.fillna(50).reindex(close.index, fill_value=50)

        # ES2: SMA vs Price with volume confirmation
        sma = ta.sma(close, length=self.es2_period)
        self.es2_sma_diff = ((close - sma) / sma * 100)
        self.es2_sma_diff = self.es2_sma_diff.fillna(0).reindex(close.index, fill_value=0)

        # ES3: EMA vs Price
        ema = ta.ema(close, length=self.es3_period)
        self.es3_ema_diff = ((close - ema) / ema * 100)
        self.es3_ema_diff = self.es3_ema_diff.fillna(0).reindex(close.index, fill_value=0)

        # ES4-ES5: MACD with MFI confirmation
        macd_result = ta.macd(close, fast=self.es4_period, slow=self.es5_period, signal=self.es6_period)
        if macd_result is not None and len(macd_result.columns) >= 3:
            macd_line = macd_result.iloc[:, 0]
            macd_signal = macd_result.iloc[:, 2]
            self.es4_macd = ((macd_line - macd_line.min()) / (macd_line.max() - macd_line.min() + 0.0001) * 100)
            self.es5_macd_signal = ((macd_signal - macd_signal.min()) / (macd_signal.max() - macd_signal.min() + 0.0001) * 100)
        else:
            self.es4_macd = pd.Series(50, index=close.index)
            self.es5_macd_signal = pd.Series(50, index=close.index)

        # ES6: Bollinger Band position
        bb_result = ta.bbands(close, length=self.es7_period, std=2.0)
        if bb_result is not None and len(bb_result.columns) >= 3:
            bb_lower = bb_result.iloc[:, 0]
            bb_upper = bb_result.iloc[:, 2]
            bb_width = bb_upper - bb_lower
            self.es6_bb_position = ((close - bb_lower) / (bb_width + 0.0001) * 100).clip(0, 100)
            self.es6_bb_position = self.es6_bb_position.fillna(50).reindex(close.index, fill_value=50)
        else:
            self.es6_bb_position = pd.Series(50, index=close.index)

        # ES7: ATR for volatility
        atr = ta.atr(high, low, close, length=self.es8_period)
        self.es7_atr_pct = (atr / close * 100).clip(0, 10) * 10
        self.es7_atr_pct = self.es7_atr_pct.fillna(50).reindex(close.index, fill_value=50)

        # ES8: Stochastic with MFI divergence check
        stoch_result = ta.stoch(high, low, close, k=self.es9_period, d=3)
        if stoch_result is not None and len(stoch_result.columns) >= 1:
            self.es8_stoch = stoch_result.iloc[:, 0]
            self.es8_stoch = self.es8_stoch.fillna(50).reindex(close.index, fill_value=50)
        else:
            self.es8_stoch = pd.Series(50, index=close.index)

        # ES9: CCI
        cci = ta.cci(high, low, close, length=self.es10_period)
        self.es9_cci = ((cci + 200) / 4).clip(0, 100)
        self.es9_cci = self.es9_cci.fillna(50).reindex(close.index, fill_value=50)

        # ES10: Volume Flow Indicator (custom)
        # Combines volume with price movement for better flow analysis
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume
        positive_flow = pd.Series(np.where(typical_price > typical_price.shift(1), money_flow, 0), index=close.index)
        negative_flow = pd.Series(np.where(typical_price <= typical_price.shift(1), money_flow, 0), index=close.index)

        positive_sum = positive_flow.rolling(window=14).sum()
        negative_sum = negative_flow.rolling(window=14).sum()
        flow_ratio = positive_sum / (negative_sum + 1)
        self.es10_flow_strength = (flow_ratio / (1 + flow_ratio) * 100)  # Normalize to 0-100
        self.es10_flow_strength = self.es10_flow_strength.fillna(50).reindex(close.index, fill_value=50)

        # Detect MFI divergences
        self.mfi_divergence = self._detect_divergence(close, self.es1_mfi, 20)

        # Convert all to numpy arrays
        self.es1 = self.I(lambda: self.es1_mfi.values)
        self.es2 = self.I(lambda: self.es2_sma_diff.values)
        self.es3 = self.I(lambda: self.es3_ema_diff.values)
        self.es4 = self.I(lambda: self.es4_macd.values)
        self.es5 = self.I(lambda: self.es5_macd_signal.values)
        self.es6 = self.I(lambda: self.es6_bb_position.values)
        self.es7 = self.I(lambda: self.es7_atr_pct.values)
        self.es8 = self.I(lambda: self.es8_stoch.values)
        self.es9 = self.I(lambda: self.es9_cci.values)
        self.es10 = self.I(lambda: self.es10_flow_strength.values)
        self.divergence = self.I(lambda: self.mfi_divergence.values)

    def _detect_divergence(self, price, indicator, period):
        """Detect bullish and bearish divergences between price and MFI"""
        divergence = pd.Series(0, index=price.index)

        for i in range(period, len(price)):
            # Get recent price and indicator windows
            price_window = price.iloc[i-period:i]
            indicator_window = indicator.iloc[i-period:i]

            # Skip if not enough data
            if len(price_window) < period or indicator_window.isna().any():
                continue

            # Find local extrema
            price_min_idx = price_window.idxmin()
            price_max_idx = price_window.idxmax()
            ind_min_idx = indicator_window.idxmin()
            ind_max_idx = indicator_window.idxmax()

            # Bullish divergence: price makes lower low, but MFI makes higher low
            if price.iloc[i] == price_window.min():
                prev_lows = price_window[price_window == price_window.nsmallest(2).max()]
                if len(prev_lows) > 0 and indicator.iloc[i] > indicator[prev_lows.index[0]]:
                    divergence.iloc[i] = 1  # Bullish

            # Bearish divergence: price makes higher high, but MFI makes lower high
            if price.iloc[i] == price_window.max():
                prev_highs = price_window[price_window == price_window.nlargest(2).min()]
                if len(prev_highs) > 0 and indicator.iloc[i] < indicator[prev_highs.index[0]]:
                    divergence.iloc[i] = -1  # Bearish

        return divergence

    def check_condition(self, source, operator, threshold):
        """Check a single condition"""
        if operator == 'G':
            return source > threshold
        elif operator == 'L':
            return source < threshold
        elif operator == 'E':
            return abs(source - threshold) < 1
        return False

    def evaluate_conditions(self, condition_type, conditions):
        """Evaluate complex condition logic"""
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
        MFI-enhanced trading logic

        Key improvements:
        - MFI oversold/overbought zones (20/80) for primary signals
        - Money flow strength confirmation
        - Divergence-based entries for high-probability trades
        """

        if len(self.data) < 50:
            return

        # Get current values
        current_mfi = self.es1[-1]          # MFI (replaces RSI)
        current_sma_diff = self.es2[-1]
        current_ema_diff = self.es3[-1]
        current_macd = self.es4[-1]
        current_macd_signal = self.es5[-1]
        current_bb = self.es6[-1]
        current_atr = self.es7[-1]
        current_stoch = self.es8[-1]
        current_cci = self.es9[-1]
        current_flow = self.es10[-1]        # Money flow strength
        current_divergence = self.divergence[-1]

        # Skip if indicators are invalid
        if any(pd.isna([current_mfi, current_macd, current_bb, current_flow])):
            return

        if not self.position:
            # LONG CONDITIONS with MFI focus
            long_conditions = [
                # Primary: MFI oversold with flow strength
                [(current_mfi, 'L', 25), (current_flow, 'G', 45)],

                # Bullish divergence with confirmation
                [(current_divergence, 'E', 1), (current_mfi, 'L', 40)],

                # Strong money flow with MACD cross
                [(current_flow, 'G', 60), (current_macd, 'G', current_macd_signal), (current_mfi, 'L', 50)],

                # Extreme oversold with multiple confirmations
                [(current_mfi, 'L', 20), (current_stoch, 'L', 20), (current_bb, 'L', 20)]
            ]

            long_signal = False
            for condition_group in long_conditions:
                if self.evaluate_conditions('AND', condition_group):
                    long_signal = True
                    break

            # Alternative: ATLEAST 3 bullish indicators including MFI
            bullish_indicators = [
                (current_mfi, 'L', 30),          # MFI oversold
                (current_flow, 'G', 50),          # Positive money flow
                (current_macd, 'G', current_macd_signal),  # MACD cross
                (current_bb, 'L', 25),           # BB oversold
                (current_stoch, 'L', 25),        # Stoch oversold
                (current_sma_diff, 'G', 0.5),    # Above SMA
            ]

            if not long_signal:
                long_signal = self.evaluate_conditions('ATLEAST3', bullish_indicators)

            # SHORT CONDITIONS with MFI focus
            short_conditions = [
                # Primary: MFI overbought with weak flow
                [(current_mfi, 'G', 75), (current_flow, 'L', 55)],

                # Bearish divergence with confirmation
                [(current_divergence, 'E', -1), (current_mfi, 'G', 60)],

                # Weak money flow with MACD cross
                [(current_flow, 'L', 40), (current_macd, 'L', current_macd_signal), (current_mfi, 'G', 50)],

                # Extreme overbought with multiple confirmations
                [(current_mfi, 'G', 80), (current_stoch, 'G', 80), (current_bb, 'G', 80)]
            ]

            short_signal = False
            for condition_group in short_conditions:
                if self.evaluate_conditions('AND', condition_group):
                    short_signal = True
                    break

            # Alternative: ATLEAST 3 bearish indicators including MFI
            bearish_indicators = [
                (current_mfi, 'G', 70),          # MFI overbought
                (current_flow, 'L', 50),          # Negative money flow
                (current_macd, 'L', current_macd_signal),  # MACD cross
                (current_bb, 'G', 75),           # BB overbought
                (current_stoch, 'G', 75),        # Stoch overbought
                (current_sma_diff, 'L', -0.5),   # Below SMA
            ]

            if not short_signal:
                short_signal = self.evaluate_conditions('ATLEAST3', bearish_indicators)

            # Execute trades
            current_price = self.data.Close[-1]

            if long_signal:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price, size=0.95)

            elif short_signal:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price, size=0.95)


# Run single backtest
bt = Backtest(data, BEIndicatorMFI, cash=10000000, commission=0.00045)

print("\n🌙 ===== BE-INDICATOR MFI ENHANCED STRATEGY ===== 🌙")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"MFI Period: {MFI_PERIOD}")
print("Enhanced with Money Flow Index and divergence detection")

stats = bt.run()
print("\n" + "="*80)
print("BACKTEST RESULTS:")
print("="*80)
print(stats)
print("="*80)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING BE-INDICATOR MFI ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(BEIndicatorMFI, 'BEIndicatorMFI')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/BEIndicatorMFI.csv")