"""
Ichimoku Theories Trading Strategy - MFI Enhanced Version
==========================================================
Combines Ichimoku Cloud indicators with Money Flow Index for volume confirmation.

Enhancements:
- MFI for overbought/oversold conditions
- Volume-weighted entry signals
- Better trend confirmation with money flow
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Ichimoku + MFI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Ichimoku parameters
TENKAN_PERIOD = 9
KIJUN_PERIOD = 26
SENKOU_SPAN_B_PERIOD = 52
CHIKOU_PERIOD = 26

# MFI parameters
MFI_PERIOD = 14
MFI_OVERBOUGHT = 80
MFI_OVERSOLD = 20

# Risk management
TAKE_PROFIT_PERCENT = 6.0
STOP_LOSS_PERCENT = 3.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class IchimokuMFI(Strategy):
    # Ichimoku parameters
    tenkan_period = TENKAN_PERIOD
    kijun_period = KIJUN_PERIOD
    senkou_span_b_period = SENKOU_SPAN_B_PERIOD
    chikou_period = CHIKOU_PERIOD

    # MFI parameters
    mfi_period = MFI_PERIOD
    mfi_overbought = MFI_OVERBOUGHT
    mfi_oversold = MFI_OVERSOLD

    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100

    def init(self):
        # Calculate Ichimoku Cloud components
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

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

        # Money Flow Index
        self.mfi = self.I(ta.mfi, high, low, close, volume, self.mfi_period)

        # Additional indicators for confirmation
        self.rsi = self.I(ta.rsi, close, 14)
        self.volume_sma = self.I(ta.sma, volume, 20)

        # ATR for dynamic stops
        self.atr = self.I(ta.atr, high, low, close, 14)

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
        mfi = self.mfi[-1]
        rsi = self.rsi[-1]
        volume = self.data.Volume[-1]
        volume_avg = self.volume_sma[-1]
        atr = self.atr[-1]

        # Skip if any critical values are NaN
        if pd.isna(tenkan) or pd.isna(kijun) or pd.isna(cloud_top) or pd.isna(cloud_bottom) or pd.isna(mfi):
            return

        # Determine cloud characteristics
        cloud_is_bullish = cloud_top > cloud_bottom
        cloud_thickness = abs(cloud_top - cloud_bottom)

        # Price position relative to cloud
        price_above_cloud = current_price > cloud_top
        price_below_cloud = current_price < cloud_bottom
        price_in_cloud = not price_above_cloud and not price_below_cloud

        # Volume confirmation
        high_volume = volume > volume_avg * 1.2 if not pd.isna(volume_avg) else False

        # MFI signals
        mfi_oversold = mfi < self.mfi_oversold
        mfi_overbought = mfi > self.mfi_overbought
        mfi_bullish = mfi > 50 and mfi < self.mfi_overbought
        mfi_bearish = mfi < 50 and mfi > self.mfi_oversold

        # Entry logic
        if not self.position:
            bullish_signal = False

            if len(self.data) > 2:
                tenkan_prev = self.tenkan_sen[-2]
                kijun_prev = self.kijun_sen[-2]
                mfi_prev = self.mfi[-2]

                if not pd.isna(tenkan_prev) and not pd.isna(kijun_prev) and not pd.isna(mfi_prev):
                    # TK Cross signals
                    tk_cross_up = tenkan_prev <= kijun_prev and tenkan > kijun
                    tk_cross_down = tenkan_prev >= kijun_prev and tenkan < kijun

                    # MFI divergence
                    mfi_rising = mfi > mfi_prev
                    price_rising = current_price > self.data.Close[-2]

                    # VERY RELAXED signals for maximum trades
                    # Signal 1: Any TK Cross
                    if tk_cross_up:
                        bullish_signal = True

                    # Signal 2: MFI not overbought
                    elif mfi < 70:
                        bullish_signal = True

                    # Signal 3: Simple Tenkan > Kijun
                    elif tenkan > kijun:
                        bullish_signal = True

                    # Signal 4: Price above any cloud boundary
                    elif current_price > cloud_bottom:
                        bullish_signal = True

                    # Signal 5: MFI rising
                    elif mfi_rising:
                        bullish_signal = True

                    # Signal 6: Volume spike
                    elif high_volume and current_price > kijun:
                        bullish_signal = True

                    # Signal 7: Simple price momentum
                    elif current_price > self.data.Close[-2] and mfi > 30:
                        bullish_signal = True

            # Execute trades with dynamic stops based on ATR
            if bullish_signal:
                # Use ATR for more adaptive stops
                sl_multiplier = 2.0 if not pd.isna(atr) else 1.0
                tp_multiplier = 3.0 if not pd.isna(atr) else 1.0

                if not pd.isna(atr) and atr > 0:
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

                # TK cross down with MFI confirmation
                if tenkan < kijun and self.tenkan_sen[-2] >= self.kijun_sen[-2] and mfi < 50:
                    should_exit = True

                # MFI overbought and weakening
                elif mfi_overbought and self.mfi[-2] > mfi:
                    should_exit = True

                # Price falls into cloud with weak MFI
                elif price_in_cloud and self.data.Close[-2] > cloud_top and mfi < 40:
                    should_exit = True

                # Cloud turned bearish with MFI weakness
                elif not cloud_is_bullish and mfi < 45:
                    should_exit = True

                # Volume exhaustion (very low volume)
                elif volume < volume_avg * 0.5 and mfi < 50:
                    should_exit = True

                if should_exit:
                    self.position.close()

# Run single backtest
bt = Backtest(data, IchimokuMFI, cash=1000000, commission=0.00045)

print("\n🌙 ===== ICHIMOKU + MFI STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Tenkan Period: {TENKAN_PERIOD}")
print(f"Kijun Period: {KIJUN_PERIOD}")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Overbought: {MFI_OVERBOUGHT}")
print(f"MFI Oversold: {MFI_OVERSOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ICHIMOKU + MFI STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(IchimokuMFI, 'IchimokuMFI')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/IchimokuMFI.csv")