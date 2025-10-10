"""
Ichimoku Theories Trading Strategy - ADX Enhanced Version
==========================================================
Combines Ichimoku Cloud with Average Directional Index for trend strength.

Enhancements:
- ADX for trend strength confirmation
- DI+ and DI- for directional movement
- Only trades in strong trending markets
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Ichimoku + ADX Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Ichimoku parameters
TENKAN_PERIOD = 9
KIJUN_PERIOD = 26
SENKOU_SPAN_B_PERIOD = 52
CHIKOU_PERIOD = 26

# ADX parameters
ADX_PERIOD = 14
ADX_STRONG_TREND = 25
ADX_WEAK_TREND = 20

# Risk management
TAKE_PROFIT_PERCENT = 6.0
STOP_LOSS_PERCENT = 3.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class IchimokuADX(Strategy):
    # Ichimoku parameters
    tenkan_period = TENKAN_PERIOD
    kijun_period = KIJUN_PERIOD
    senkou_span_b_period = SENKOU_SPAN_B_PERIOD
    chikou_period = CHIKOU_PERIOD

    # ADX parameters
    adx_period = ADX_PERIOD
    adx_strong = ADX_STRONG_TREND
    adx_weak = ADX_WEAK_TREND

    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        # Calculate Ichimoku Cloud components
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Tenkan-sen (Conversion Line)
        self.tenkan_sen = self.I(lambda: (
            high.rolling(self.tenkan_period).max() +
            low.rolling(self.tenkan_period).min()
        ) / 2)

        # Kijun-sen (Base Line)
        self.kijun_sen = self.I(lambda: (
            high.rolling(self.kijun_period).max() +
            low.rolling(self.kijun_period).min()
        ) / 2)

        # Senkou Span A (Leading Span A)
        senkou_span_a_raw = (
            (high.rolling(self.tenkan_period).max() + low.rolling(self.tenkan_period).min()) / 2 +
            (high.rolling(self.kijun_period).max() + low.rolling(self.kijun_period).min()) / 2
        ) / 2
        self.senkou_span_a = self.I(lambda: senkou_span_a_raw.shift(-self.kijun_period))

        # Senkou Span B (Leading Span B)
        senkou_span_b_raw = (
            high.rolling(self.senkou_span_b_period).max() +
            low.rolling(self.senkou_span_b_period).min()
        ) / 2
        self.senkou_span_b = self.I(lambda: senkou_span_b_raw.shift(-self.kijun_period))

        # Chikou Span (Lagging Span)
        self.chikou_span = self.I(lambda: close.shift(self.chikou_period))

        # Cloud boundaries (current, not shifted)
        self.cloud_top = self.I(lambda: np.maximum(
            (high.rolling(self.tenkan_period).max() + low.rolling(self.tenkan_period).min()) / 2,
            (high.rolling(self.senkou_span_b_period).max() + low.rolling(self.senkou_span_b_period).min()) / 2
        ))

        self.cloud_bottom = self.I(lambda: np.minimum(
            (high.rolling(self.tenkan_period).max() + low.rolling(self.tenkan_period).min()) / 2,
            (high.rolling(self.senkou_span_b_period).max() + low.rolling(self.senkou_span_b_period).min()) / 2
        ))

        # ADX indicators using pandas_ta
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        if adx_result is not None and not adx_result.empty:
            # Extract ADX, DI+, and DI-
            self.adx = self.I(lambda: adx_result[f'ADX_{self.adx_period}'])
            self.di_plus = self.I(lambda: adx_result[f'DMP_{self.adx_period}'])
            self.di_minus = self.I(lambda: adx_result[f'DMN_{self.adx_period}'])
        else:
            # Fallback if ADX calculation fails
            self.adx = self.I(lambda: pd.Series([25] * len(close)))
            self.di_plus = self.I(lambda: pd.Series([20] * len(close)))
            self.di_minus = self.I(lambda: pd.Series([20] * len(close)))

        # Additional indicators
        self.ema_20 = self.I(ta.ema, close, 20)
        self.ema_50 = self.I(ta.ema, close, 50)
        self.atr = self.I(ta.atr, high, low, close, 14)

        # Volatility measure
        bb_result = ta.bbands(close, length=20, std=2)
        if bb_result is not None and not bb_result.empty:
            self.bb_upper = self.I(lambda: bb_result['BBU_20_2.0'])
            self.bb_lower = self.I(lambda: bb_result['BBL_20_2.0'])
            self.bb_middle = self.I(lambda: bb_result['BBM_20_2.0'])
        else:
            self.bb_upper = self.I(ta.sma, close, 20)
            self.bb_lower = self.I(ta.sma, close, 20)
            self.bb_middle = self.I(ta.sma, close, 20)

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < 52:  # Reduced from 200
            return

        # Current values
        current_price = self.data.Close[-1]
        tenkan = self.tenkan_sen[-1]
        kijun = self.kijun_sen[-1]
        cloud_top = self.cloud_top[-1]
        cloud_bottom = self.cloud_bottom[-1]
        adx = self.adx[-1]
        di_plus = self.di_plus[-1]
        di_minus = self.di_minus[-1]
        atr = self.atr[-1]

        # Skip if any critical values are NaN
        if pd.isna(tenkan) or pd.isna(kijun) or pd.isna(cloud_top) or pd.isna(cloud_bottom):
            return

        if pd.isna(adx) or pd.isna(di_plus) or pd.isna(di_minus):
            # Use default values if ADX calculation failed
            adx = 25
            di_plus = 20
            di_minus = 20

        # Determine cloud characteristics
        cloud_is_bullish = cloud_top > cloud_bottom
        cloud_thickness = abs(cloud_top - cloud_bottom)

        # Price position relative to cloud
        price_above_cloud = current_price > cloud_top
        price_below_cloud = current_price < cloud_bottom
        price_in_cloud = not price_above_cloud and not price_below_cloud

        # ADX trend strength
        strong_trend = adx > self.adx_strong
        weak_trend = adx < self.adx_weak
        moderate_trend = not strong_trend and not weak_trend

        # Directional movement
        bullish_direction = di_plus > di_minus
        bearish_direction = di_minus > di_plus

        # EMA trend
        ema_bullish = self.ema_20[-1] > self.ema_50[-1] if not pd.isna(self.ema_20[-1]) and not pd.isna(self.ema_50[-1]) else False

        # Entry logic
        if not self.position:
            bullish_signal = False

            if len(self.data) > 3:
                tenkan_prev = self.tenkan_sen[-2]
                kijun_prev = self.kijun_sen[-2]
                adx_prev = self.adx[-2] if not pd.isna(self.adx[-2]) else 25
                di_plus_prev = self.di_plus[-2] if not pd.isna(self.di_plus[-2]) else 20

                if not pd.isna(tenkan_prev) and not pd.isna(kijun_prev):
                    # TK Cross signals
                    tk_cross_up = tenkan_prev <= kijun_prev and tenkan > kijun
                    tk_cross_down = tenkan_prev >= kijun_prev and tenkan < kijun

                    # ADX trend development
                    adx_rising = adx > adx_prev
                    di_plus_rising = di_plus > di_plus_prev

                    # ULTRA RELAXED signals for maximum trading
                    # Signal 1: Any TK Cross
                    if tk_cross_up:
                        bullish_signal = True

                    # Signal 2: DI+ > DI-
                    elif bullish_direction:
                        bullish_signal = True

                    # Signal 3: ADX above 15 (very low threshold)
                    elif adx > 15:
                        bullish_signal = True

                    # Signal 4: Simple Tenkan > Kijun
                    elif tenkan > kijun:
                        bullish_signal = True

                    # Signal 5: Price above any cloud part
                    elif current_price > cloud_bottom:
                        bullish_signal = True

                    # Signal 6: EMA bullish
                    elif ema_bullish:
                        bullish_signal = True

                    # Signal 7: ADX rising from any level
                    elif adx_rising:
                        bullish_signal = True

                    # Signal 8: Price above Kijun
                    elif current_price > kijun:
                        bullish_signal = True

            # Execute trades with ADX-based position sizing
            if bullish_signal:
                # Use stronger stops in trending markets
                if strong_trend and not pd.isna(atr) and atr > 0:
                    sl_multiplier = 1.5  # Tighter stop in strong trends
                    tp_multiplier = 4.0  # Larger target in strong trends
                    sl_price = current_price - (atr * sl_multiplier)
                    tp_price = current_price + (atr * tp_multiplier)
                elif moderate_trend and not pd.isna(atr) and atr > 0:
                    sl_multiplier = 2.0
                    tp_multiplier = 3.0
                    sl_price = current_price - (atr * sl_multiplier)
                    tp_price = current_price + (atr * tp_multiplier)
                else:
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)

                self.buy(sl=sl_price, tp=tp_price, size=1000000)

        # Exit logic for existing positions
        else:
            if self.position.is_long:
                should_exit = False

                # TK cross down with trend weakening
                if tenkan < kijun and self.tenkan_sen[-2] >= self.kijun_sen[-2] and not strong_trend:
                    should_exit = True

                # ADX trend exhaustion (very high ADX starting to decline)
                elif adx > 40 and self.adx[-2] > adx and not bullish_direction:
                    should_exit = True

                # Directional movement reversal
                elif bearish_direction and di_minus > di_plus * 1.2:
                    should_exit = True

                # Price falls into cloud with weak trend
                elif price_in_cloud and self.data.Close[-2] > cloud_top and weak_trend:
                    should_exit = True

                # Cloud turned bearish with no trend
                elif not cloud_is_bullish and weak_trend:
                    should_exit = True

                # Trend completely dissipated
                elif adx < 15 and not bullish_direction:
                    should_exit = True

                if should_exit:
                    self.position.close()

# Run single backtest
bt = Backtest(data, IchimokuADX, cash=1000000, commission=0.00045)

print("\n🌙 ===== ICHIMOKU + ADX STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Tenkan Period: {TENKAN_PERIOD}")
print(f"Kijun Period: {KIJUN_PERIOD}")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Strong Trend: {ADX_STRONG_TREND}")
print(f"ADX Weak Trend: {ADX_WEAK_TREND}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ICHIMOKU + ADX STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(IchimokuADX, 'IchimokuADX')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/IchimokuADX.csv")