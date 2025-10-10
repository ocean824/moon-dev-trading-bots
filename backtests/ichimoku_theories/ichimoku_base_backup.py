"""
Ichimoku Theories Trading Strategy - Base Version
==================================================
Based on traditional Ichimoku Cloud indicators with wave pattern detection.

Components:
1. Tenkan Sen (Conversion Line) - 9 period average
2. Kijun Sen (Base Line) - 26 period average
3. Senkou Span A & B (Cloud boundaries)
4. Chikou Span (Lagging Span)
5. Price position relative to cloud
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Ichimoku Theories Strategy - Base Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Ichimoku parameters (traditional settings)
TENKAN_PERIOD = 9
KIJUN_PERIOD = 26
SENKOU_SPAN_B_PERIOD = 52
CHIKOU_PERIOD = 26

# Risk management
TAKE_PROFIT_PERCENT = 8.0
STOP_LOSS_PERCENT = 4.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class IchimokuBase(Strategy):
    # Ichimoku parameters
    tenkan_period = TENKAN_PERIOD
    kijun_period = KIJUN_PERIOD
    senkou_span_b_period = SENKOU_SPAN_B_PERIOD
    chikou_period = CHIKOU_PERIOD

    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        # Calculate Ichimoku Cloud components using pandas_ta
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Tenkan-sen (Conversion Line) = (9-period high + 9-period low)/2
        self.tenkan_sen = self.I(lambda: (
            high.rolling(self.tenkan_period).max() +
            low.rolling(self.tenkan_period).min()
        ) / 2)

        # Kijun-sen (Base Line) = (26-period high + 26-period low)/2
        self.kijun_sen = self.I(lambda: (
            high.rolling(self.kijun_period).max() +
            low.rolling(self.kijun_period).min()
        ) / 2)

        # Senkou Span A (Leading Span A) = (Tenkan-sen + Kijun-sen)/2 shifted forward 26 periods
        senkou_span_a_raw = (
            (high.rolling(self.tenkan_period).max() + low.rolling(self.tenkan_period).min()) / 2 +
            (high.rolling(self.kijun_period).max() + low.rolling(self.kijun_period).min()) / 2
        ) / 2
        # Note: In backtesting, we can't shift forward, so we use past values
        self.senkou_span_a = self.I(lambda: senkou_span_a_raw.shift(-self.kijun_period))

        # Senkou Span B (Leading Span B) = (52-period high + 52-period low)/2 shifted forward 26 periods
        senkou_span_b_raw = (
            high.rolling(self.senkou_span_b_period).max() +
            low.rolling(self.senkou_span_b_period).min()
        ) / 2
        self.senkou_span_b = self.I(lambda: senkou_span_b_raw.shift(-self.kijun_period))

        # Chikou Span (Lagging Span) = Close price shifted back 26 periods
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

        # Simple trend indicator
        self.sma_50 = self.I(ta.sma, close, 50)
        self.sma_200 = self.I(ta.sma, close, 200)

    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < 200:
            return

        # Current values
        current_price = self.data.Close[-1]
        tenkan = self.tenkan_sen[-1]
        kijun = self.kijun_sen[-1]
        cloud_top = self.cloud_top[-1]
        cloud_bottom = self.cloud_bottom[-1]

        # Skip if any values are NaN
        if pd.isna(tenkan) or pd.isna(kijun) or pd.isna(cloud_top) or pd.isna(cloud_bottom):
            return

        # Determine cloud color (bullish or bearish)
        cloud_is_bullish = cloud_top > cloud_bottom

        # Price position relative to cloud
        price_above_cloud = current_price > cloud_top
        price_below_cloud = current_price < cloud_bottom
        price_in_cloud = not price_above_cloud and not price_below_cloud

        # Trend confirmation
        uptrend = self.sma_50[-1] > self.sma_200[-1] if not pd.isna(self.sma_50[-1]) and not pd.isna(self.sma_200[-1]) else False
        downtrend = self.sma_50[-1] < self.sma_200[-1] if not pd.isna(self.sma_50[-1]) and not pd.isna(self.sma_200[-1]) else False

        # Entry logic
        if not self.position:
            # Strong bullish signals
            bullish_signal = False
            bearish_signal = False

            # Bullish entry conditions (relaxed for more signals):
            if len(self.data) > 2:
                tenkan_prev = self.tenkan_sen[-2]
                kijun_prev = self.kijun_sen[-2]

                if not pd.isna(tenkan_prev) and not pd.isna(kijun_prev):
                    tk_cross_up = tenkan_prev <= kijun_prev and tenkan > kijun
                    tk_cross_down = tenkan_prev >= kijun_prev and tenkan < kijun

                    # Signal 1: TK Cross with price above cloud
                    if tk_cross_up and price_above_cloud:
                        bullish_signal = True

                    # Signal 2: Price breaks above cloud
                    elif current_price > cloud_top and self.data.Close[-2] <= cloud_top:
                        bullish_signal = True

                    # Signal 3: Tenkan > Kijun with bullish cloud
                    elif tenkan > kijun and cloud_is_bullish and current_price > kijun:
                        bullish_signal = True

                    # Signal 4: Strong momentum above cloud
                    elif price_above_cloud and tenkan > kijun:
                        bullish_signal = True

                    # Signal 5: Cloud twist bullish with price support
                    elif cloud_is_bullish and current_price > tenkan and tenkan > kijun:
                        bullish_signal = True

            # Execute trades
            if bullish_signal:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price, size=1000000)

        # Exit logic for existing positions
        else:
            # Exit conditions (beyond SL/TP):
            # 1. Tenkan crosses below Kijun
            # 2. Price enters cloud from above
            # 3. Cloud turns bearish
            if self.position.is_long:
                should_exit = False

                # TK cross down
                if tenkan < kijun and self.tenkan_sen[-2] >= self.kijun_sen[-2]:
                    should_exit = True

                # Price falls into cloud
                elif price_in_cloud and self.data.Close[-2] > cloud_top:
                    should_exit = True

                # Cloud turned bearish
                elif not cloud_is_bullish and cloud_top < cloud_bottom:
                    should_exit = True

                if should_exit:
                    self.position.close()

# Run single backtest (default behavior)
bt = Backtest(data, IchimokuBase, cash=1000000, commission=0.00045)

print("\n🌙 ===== ICHIMOKU BASE STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Tenkan Period: {TENKAN_PERIOD}")
print(f"Kijun Period: {KIJUN_PERIOD}")
print(f"Senkou Span B Period: {SENKOU_SPAN_B_PERIOD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ICHIMOKU BASE STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(IchimokuBase, 'IchimokuBase')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/IchimokuBase.csv")