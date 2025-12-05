"""
Moon Dev's Accumulation Strategies - Phase 2
=============================================
Building on the +37.8% WL + Double Down winner from Phase 1

STRATEGIES:
-----------
WL + Double Down Variations (5):
1. WL + DD + MFI - Add MFI oversold filter
2. WL + DD + Volume Profile - Buy at high volume nodes
3. WL + DD + Stoch - Add Stochastic oversold
4. WL + DD + MACD Bearish - Buy when MACD histogram negative
5. WL + DD + ATR Scale - Scale DD multiplier by ATR

Weekly Low Base Variations (5):
6. WL + MFI Oversold - MFI < 20
7. WL + Williams %R - Williams %R oversold
8. WL + CCI Extreme - CCI < -100
9. WL + Stoch RSI - Stoch RSI oversold
10. WL + OBV Divergence - Price low + OBV rising

New Indicator Strategies (8):
11. MFI Accumulator - Pure MFI oversold buying
12. Volume Profile Low - Buy at volume support zones
13. Stoch + RSI Combo - Both indicators oversold
14. Williams %R Extreme - Williams %R < -80
15. CCI Mean Reversion - CCI < -150
16. Money Flow Accumulator - CMF negative + price low
17. VWAP Discount - Buy below daily VWAP
18. OBV Momentum - OBV divergence accumulator
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("Moon Dev's Phase 2 Accumulation Strategies")
print("Target: Beat +37.8% (WL + Double Down)")
print("=" * 70)

# =============================================================================
# CONFIGURATION
# =============================================================================
STARTING_CAPITAL = 1_000_000

DATA_PATHS = {
    'BTC': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-260wks-data.csv',
    'ETH': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1d-260wks-data.csv',
    'SOL': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1d-260wks-data.csv',
}

results = []

# =============================================================================
# WL + DOUBLE DOWN BASE (Phase 1 Winner for comparison)
# =============================================================================
class WLDoubleDownBase(Strategy):
    """Phase 1 winner: +37.8% avg vs DCA"""
    weekly_buy = 0.01

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1
        self.consecutive_lows = 0

    def next(self):
        if len(self.data) < 7:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        current_idx = len(self.data) - 1

        if is_low > 0 and current_idx > self.last_week_bought + 5:
            if self.buy_count > 0 and current_price < self.total_spent / self.total_coins:
                self.consecutive_lows += 1
            else:
                self.consecutive_lows = 0
            multiplier = min(1.0 + (self.consecutive_lows * 0.5), 2.0)
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy * multiplier, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


# =============================================================================
# WL + DOUBLE DOWN VARIATIONS
# =============================================================================

class WLDD_MFI(Strategy):
    """WL + DD + MFI filter - only buy when MFI < 30"""
    weekly_buy = 0.01
    mfi_threshold = 30

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.mfi = self.I(ta.mfi, high, low, close, volume, length=14)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1
        self.consecutive_lows = 0

    def next(self):
        if len(self.data) < 14:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        current_mfi = self.mfi[-1]
        current_idx = len(self.data) - 1

        if pd.isna(current_mfi):
            return

        if is_low > 0 and current_idx > self.last_week_bought + 5 and current_mfi < self.mfi_threshold:
            if self.buy_count > 0 and current_price < self.total_spent / self.total_coins:
                self.consecutive_lows += 1
            else:
                self.consecutive_lows = 0
            multiplier = min(1.0 + (self.consecutive_lows * 0.5), 2.0)
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy * multiplier, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


class WLDD_VolumeProfile(Strategy):
    """WL + DD + Volume Profile - buy more at high volume price levels"""
    weekly_buy = 0.01
    volume_lookback = 50

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.avg_volume = self.I(ta.sma, pd.Series(self.data.Volume), length=self.volume_lookback)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1
        self.consecutive_lows = 0

    def next(self):
        if len(self.data) < self.volume_lookback:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        avg_vol = self.avg_volume[-1]
        is_low = self.is_weekly_low[-1]
        current_idx = len(self.data) - 1

        if pd.isna(avg_vol) or avg_vol == 0:
            return

        if is_low > 0 and current_idx > self.last_week_bought + 5:
            if self.buy_count > 0 and current_price < self.total_spent / self.total_coins:
                self.consecutive_lows += 1
            else:
                self.consecutive_lows = 0

            # Volume profile multiplier: more volume = more conviction
            vol_mult = min(current_volume / avg_vol, 2.0) if avg_vol > 0 else 1.0
            base_mult = min(1.0 + (self.consecutive_lows * 0.5), 2.0)
            multiplier = base_mult * max(vol_mult, 0.5)

            buy_amount = min(STARTING_CAPITAL * self.weekly_buy * multiplier, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


class WLDD_Stoch(Strategy):
    """WL + DD + Stochastic oversold filter"""
    weekly_buy = 0.01
    stoch_threshold = 20

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        high = pd.Series(self.data.High, index=self.data.index)
        low = pd.Series(self.data.Low, index=self.data.index)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        stoch = ta.stoch(high, low, close, k=14, d=3)
        stoch_k_vals = stoch['STOCHk_14_3_3'].reindex(close.index).values
        self.stoch_k = self.I(lambda: stoch_k_vals)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1
        self.consecutive_lows = 0

    def next(self):
        if len(self.data) < 14:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        current_stoch = self.stoch_k[-1]
        current_idx = len(self.data) - 1

        if pd.isna(current_stoch):
            return

        if is_low > 0 and current_idx > self.last_week_bought + 5 and current_stoch < self.stoch_threshold:
            if self.buy_count > 0 and current_price < self.total_spent / self.total_coins:
                self.consecutive_lows += 1
            else:
                self.consecutive_lows = 0
            multiplier = min(1.0 + (self.consecutive_lows * 0.5), 2.0)
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy * multiplier, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


class WLDD_MACD(Strategy):
    """WL + DD + MACD Bearish - buy when MACD histogram negative"""
    weekly_buy = 0.01

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        macd = ta.macd(close, fast=12, slow=26, signal=9)
        self.macd_hist = self.I(lambda: macd['MACDh_12_26_9'].values)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1
        self.consecutive_lows = 0

    def next(self):
        if len(self.data) < 26:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        macd_hist = self.macd_hist[-1]
        current_idx = len(self.data) - 1

        if pd.isna(macd_hist):
            return

        if is_low > 0 and current_idx > self.last_week_bought + 5 and macd_hist < 0:
            if self.buy_count > 0 and current_price < self.total_spent / self.total_coins:
                self.consecutive_lows += 1
            else:
                self.consecutive_lows = 0
            multiplier = min(1.0 + (self.consecutive_lows * 0.5), 2.0)
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy * multiplier, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


class WLDD_ATRScale(Strategy):
    """WL + DD + ATR Scale - scale DD multiplier by ATR"""
    weekly_buy = 0.01
    atr_period = 14
    atr_lookback = 50

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        atr_series = ta.atr(high, low, close, self.atr_period)
        self.atr_avg = self.I(lambda: atr_series.rolling(self.atr_lookback).mean().values)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1
        self.consecutive_lows = 0

    def next(self):
        if len(self.data) < self.atr_lookback:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        current_atr = self.atr[-1]
        avg_atr = self.atr_avg[-1]
        current_idx = len(self.data) - 1

        if pd.isna(current_atr) or pd.isna(avg_atr) or avg_atr == 0:
            return

        if is_low > 0 and current_idx > self.last_week_bought + 5:
            if self.buy_count > 0 and current_price < self.total_spent / self.total_coins:
                self.consecutive_lows += 1
            else:
                self.consecutive_lows = 0

            # ATR scaling: high vol = buy more
            atr_ratio = current_atr / avg_atr
            atr_mult = min(max(atr_ratio, 0.5), 2.5)
            base_mult = min(1.0 + (self.consecutive_lows * 0.5), 2.0)
            multiplier = base_mult * atr_mult

            buy_amount = min(STARTING_CAPITAL * self.weekly_buy * multiplier, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


# =============================================================================
# WEEKLY LOW BASE VARIATIONS
# =============================================================================

class WL_MFI(Strategy):
    """Weekly Low + MFI Oversold"""
    weekly_buy = 0.01
    mfi_threshold = 20

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.mfi = self.I(ta.mfi, high, low, close, volume, length=14)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1

    def next(self):
        if len(self.data) < 14:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        current_mfi = self.mfi[-1]
        current_idx = len(self.data) - 1

        if pd.isna(current_mfi):
            return

        if is_low > 0 and current_idx > self.last_week_bought + 5 and current_mfi < self.mfi_threshold:
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


class WL_WilliamsR(Strategy):
    """Weekly Low + Williams %R Oversold"""
    weekly_buy = 0.01
    wr_threshold = -80

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.willr = self.I(ta.willr, high, low, close, length=14)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1

    def next(self):
        if len(self.data) < 14:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        current_wr = self.willr[-1]
        current_idx = len(self.data) - 1

        if pd.isna(current_wr):
            return

        if is_low > 0 and current_idx > self.last_week_bought + 5 and current_wr < self.wr_threshold:
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


class WL_CCI(Strategy):
    """Weekly Low + CCI Extreme"""
    weekly_buy = 0.01
    cci_threshold = -100

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.cci = self.I(ta.cci, high, low, close, length=20)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1

    def next(self):
        if len(self.data) < 20:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        current_cci = self.cci[-1]
        current_idx = len(self.data) - 1

        if pd.isna(current_cci):
            return

        if is_low > 0 and current_idx > self.last_week_bought + 5 and current_cci < self.cci_threshold:
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


class WL_StochRSI(Strategy):
    """Weekly Low + Stochastic RSI Oversold"""
    weekly_buy = 0.01
    stochrsi_threshold = 20

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        stochrsi = ta.stochrsi(close, length=14, rsi_length=14, k=3, d=3)
        stochrsi_k_vals = stochrsi['STOCHRSIk_14_14_3_3'].reindex(close.index).values
        self.stochrsi_k = self.I(lambda: stochrsi_k_vals)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1

    def next(self):
        if len(self.data) < 28:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        current_stochrsi = self.stochrsi_k[-1]
        current_idx = len(self.data) - 1

        if pd.isna(current_stochrsi):
            return

        if is_low > 0 and current_idx > self.last_week_bought + 5 and current_stochrsi < self.stochrsi_threshold:
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


class WL_OBV(Strategy):
    """Weekly Low + OBV Rising (divergence)"""
    weekly_buy = 0.01
    obv_lookback = 5

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        volume = pd.Series(self.data.Volume)
        weekly_min = close.resample('W').transform('min')
        self.is_weekly_low = self.I(lambda: (close == weekly_min).values.astype(float))
        self.obv = self.I(ta.obv, close, volume)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_week_bought = -1

    def next(self):
        if len(self.data) < self.obv_lookback + 7:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        is_low = self.is_weekly_low[-1]
        current_idx = len(self.data) - 1

        # Check OBV rising (bullish divergence)
        obv_now = self.obv[-1]
        obv_past = self.obv[-self.obv_lookback]

        if pd.isna(obv_now) or pd.isna(obv_past):
            return

        obv_rising = obv_now > obv_past

        if is_low > 0 and current_idx > self.last_week_bought + 5 and obv_rising:
            buy_amount = min(STARTING_CAPITAL * self.weekly_buy, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_week_bought = current_idx


# =============================================================================
# NEW INDICATOR STRATEGIES
# =============================================================================

class MFI_Accumulator(Strategy):
    """Pure MFI Oversold Accumulator"""
    buy_percent = 0.03
    mfi_threshold = 20

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        self.mfi = self.I(ta.mfi, high, low, close, volume, length=14)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -3

    def next(self):
        if len(self.data) < 14:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_mfi = self.mfi[-1]
        current_price = self.data.Close[-1]
        current_bar = len(self.data)

        if pd.isna(current_mfi):
            return
        if current_bar - self.last_buy_bar < 3:
            return

        if current_mfi < self.mfi_threshold:
            # Scale by how oversold
            mfi_scale = 1.0 + (self.mfi_threshold - current_mfi) / 20
            buy_amount = min(remaining * self.buy_percent * mfi_scale, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


class VolumeProfileAccumulator(Strategy):
    """Volume Profile Low - buy at high volume support zones"""
    buy_percent = 0.02
    volume_lookback = 50
    price_lookback = 20

    def init(self):
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)
        self.avg_volume = self.I(ta.sma, volume, length=self.volume_lookback)
        self.price_low = self.I(lambda: close.rolling(self.price_lookback).min().values)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -5

    def next(self):
        if len(self.data) < self.volume_lookback:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        avg_vol = self.avg_volume[-1]
        price_low = self.price_low[-1]
        current_bar = len(self.data)

        if pd.isna(avg_vol) or pd.isna(price_low):
            return
        if current_bar - self.last_buy_bar < 5:
            return

        # Buy at 20-day lows with above-average volume (support zone)
        at_support = current_price <= price_low * 1.02
        high_volume = current_volume >= avg_vol * 1.2

        if at_support and high_volume:
            vol_mult = min(current_volume / avg_vol, 2.0)
            buy_amount = min(remaining * self.buy_percent * vol_mult, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


class StochRSI_Combo(Strategy):
    """Stochastic + RSI Both Oversold"""
    buy_percent = 0.04
    rsi_threshold = 35
    stoch_threshold = 25

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        high = pd.Series(self.data.High, index=self.data.index)
        low = pd.Series(self.data.Low, index=self.data.index)
        self.rsi = self.I(ta.rsi, close, length=14)
        stoch = ta.stoch(high, low, close, k=14, d=3)
        stoch_k_vals = stoch['STOCHk_14_3_3'].reindex(close.index).values
        self.stoch_k = self.I(lambda: stoch_k_vals)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -3

    def next(self):
        if len(self.data) < 14:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_rsi = self.rsi[-1]
        current_stoch = self.stoch_k[-1]
        current_price = self.data.Close[-1]
        current_bar = len(self.data)

        if pd.isna(current_rsi) or pd.isna(current_stoch):
            return
        if current_bar - self.last_buy_bar < 2:
            return

        if current_rsi < self.rsi_threshold and current_stoch < self.stoch_threshold:
            buy_amount = remaining * self.buy_percent
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


class WilliamsR_Extreme(Strategy):
    """Williams %R Extreme Accumulator"""
    buy_percent = 0.04
    wr_threshold = -85

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        self.willr = self.I(ta.willr, high, low, close, length=14)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -3

    def next(self):
        if len(self.data) < 14:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_wr = self.willr[-1]
        current_price = self.data.Close[-1]
        current_bar = len(self.data)

        if pd.isna(current_wr):
            return
        if current_bar - self.last_buy_bar < 2:
            return

        if current_wr < self.wr_threshold:
            # Scale by extremity
            wr_scale = 1.0 + abs(current_wr - self.wr_threshold) / 15
            buy_amount = min(remaining * self.buy_percent * wr_scale, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


class CCI_MeanReversion(Strategy):
    """CCI Mean Reversion - extreme oversold"""
    buy_percent = 0.04
    cci_threshold = -150

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        self.cci = self.I(ta.cci, high, low, close, length=20)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -3

    def next(self):
        if len(self.data) < 20:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_cci = self.cci[-1]
        current_price = self.data.Close[-1]
        current_bar = len(self.data)

        if pd.isna(current_cci):
            return
        if current_bar - self.last_buy_bar < 2:
            return

        if current_cci < self.cci_threshold:
            cci_scale = 1.0 + abs(current_cci - self.cci_threshold) / 100
            buy_amount = min(remaining * self.buy_percent * cci_scale, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


class CMF_Accumulator(Strategy):
    """Chaikin Money Flow Accumulator"""
    buy_percent = 0.03
    cmf_threshold = -0.15

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        self.cmf = self.I(ta.cmf, high, low, close, volume, length=20)
        # Also track if price is at recent lows
        self.price_low = self.I(lambda: close.rolling(20).min().values)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -5

    def next(self):
        if len(self.data) < 20:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_cmf = self.cmf[-1]
        current_price = self.data.Close[-1]
        price_low = self.price_low[-1]
        current_bar = len(self.data)

        if pd.isna(current_cmf) or pd.isna(price_low):
            return
        if current_bar - self.last_buy_bar < 3:
            return

        # Negative CMF + near price low = capitulation
        at_low = current_price <= price_low * 1.05
        if current_cmf < self.cmf_threshold and at_low:
            cmf_scale = 1.0 + abs(current_cmf) * 2
            buy_amount = min(remaining * self.buy_percent * cmf_scale, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


class VWAP_Discount(Strategy):
    """Buy when price significantly below VWAP proxy"""
    buy_percent = 0.02
    discount_threshold = 0.03  # 3% below

    def init(self):
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)
        # Use 20-day VWAP proxy
        typical_price = (pd.Series(self.data.High) + pd.Series(self.data.Low) + close) / 3
        cumvol = volume.rolling(20).sum()
        cumtp = (typical_price * volume).rolling(20).sum()
        self.vwap = self.I(lambda: (cumtp / cumvol).values)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -3

    def next(self):
        if len(self.data) < 20:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        current_vwap = self.vwap[-1]
        current_bar = len(self.data)

        if pd.isna(current_vwap) or current_vwap == 0:
            return
        if current_bar - self.last_buy_bar < 2:
            return

        discount = (current_vwap - current_price) / current_vwap
        if discount >= self.discount_threshold:
            # Scale by discount
            disc_scale = 1.0 + (discount - self.discount_threshold) * 10
            buy_amount = min(remaining * self.buy_percent * disc_scale, remaining)
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


class OBV_Momentum(Strategy):
    """OBV Divergence Accumulator - price down, OBV up"""
    buy_percent = 0.03
    lookback = 10

    def init(self):
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)
        self.obv = self.I(ta.obv, close, volume)
        self.price_change = self.I(lambda: close.pct_change(self.lookback).values)
        self.total_coins = 0
        self.total_spent = 0
        self.buy_count = 0
        self.last_buy_bar = -5

    def next(self):
        if len(self.data) < self.lookback + 5:
            return
        remaining = STARTING_CAPITAL - self.total_spent
        if remaining <= 0:
            return
        current_price = self.data.Close[-1]
        price_chg = self.price_change[-1]
        obv_now = self.obv[-1]
        obv_past = self.obv[-self.lookback]
        current_bar = len(self.data)

        if pd.isna(price_chg) or pd.isna(obv_now) or pd.isna(obv_past):
            return
        if current_bar - self.last_buy_bar < 3:
            return

        # Bullish divergence: price down, OBV up
        price_down = price_chg < -0.05  # 5% drop
        obv_up = obv_now > obv_past

        if price_down and obv_up:
            buy_amount = remaining * self.buy_percent
            coins = buy_amount / current_price
            self.total_coins += coins
            self.total_spent += buy_amount
            self.buy_count += 1
            self.last_buy_bar = current_bar


# =============================================================================
# STRATEGY LIST
# =============================================================================
STRATEGIES = [
    # Phase 1 Winner (baseline)
    ('WL+DD Base (P1 Winner)', WLDoubleDownBase),

    # WL + DD Variations
    ('WL+DD + MFI', WLDD_MFI),
    ('WL+DD + VolProfile', WLDD_VolumeProfile),
    ('WL+DD + Stoch', WLDD_Stoch),
    ('WL+DD + MACD', WLDD_MACD),
    ('WL+DD + ATR Scale', WLDD_ATRScale),

    # WL Base Variations
    ('WL + MFI', WL_MFI),
    ('WL + Williams%R', WL_WilliamsR),
    ('WL + CCI', WL_CCI),
    ('WL + StochRSI', WL_StochRSI),
    ('WL + OBV', WL_OBV),

    # New Indicator Strategies
    ('MFI Accumulator', MFI_Accumulator),
    ('Volume Profile', VolumeProfileAccumulator),
    ('Stoch+RSI Combo', StochRSI_Combo),
    ('Williams%R Extreme', WilliamsR_Extreme),
    ('CCI Mean Reversion', CCI_MeanReversion),
    ('CMF Accumulator', CMF_Accumulator),
    ('VWAP Discount', VWAP_Discount),
    ('OBV Momentum', OBV_Momentum),
]

# =============================================================================
# RUN ALL STRATEGIES
# =============================================================================
for asset, data_path in DATA_PATHS.items():
    print(f"\n{'='*70}")
    print(f"Loading {asset} data...")
    print(f"{'='*70}")

    data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    data = data.sort_index()
    data = data.dropna()

    first_day_price = data['Close'].iloc[0]
    final_price = data['Close'].iloc[-1]
    first_date = data.index[0].strftime('%Y-%m-%d')
    last_date = data.index[-1].strftime('%Y-%m-%d')
    total_days = len(data)

    print(f"{first_date} to {last_date} ({total_days} days)")
    print(f"${first_day_price:,.2f} -> ${final_price:,.2f}")

    # Daily DCA baseline
    dca_daily_amount = STARTING_CAPITAL / total_days
    dca_coins = (dca_daily_amount / data['Close']).sum()
    dca_avg_price = STARTING_CAPITAL / dca_coins
    dca_final_value = dca_coins * final_price

    results.append({
        'Asset': asset,
        'Strategy': 'Daily DCA',
        'Coins': dca_coins,
        'Avg_Price': dca_avg_price,
        'Capital_Used_Pct': 100.0,
        'Buy_Signals': total_days,
        'Final_Value': dca_final_value,
        'vs_DCA_Pct': 0.0,
    })

    # Run each strategy
    for strat_name, strat_class in STRATEGIES:
        print(f"  Running {strat_name}...", end=" ")

        bt = Backtest(data, strat_class, cash=STARTING_CAPITAL, commission=0.001)
        stats = bt.run()
        strategy = stats._strategy

        if strategy.total_coins > 0:
            avg_price = strategy.total_spent / strategy.total_coins
            final_value = strategy.total_coins * final_price
            capital_pct = (strategy.total_spent / STARTING_CAPITAL) * 100
            vs_dca = ((strategy.total_coins - dca_coins) / dca_coins) * 100

            results.append({
                'Asset': asset,
                'Strategy': strat_name,
                'Coins': strategy.total_coins,
                'Avg_Price': avg_price,
                'Capital_Used_Pct': capital_pct,
                'Buy_Signals': strategy.buy_count,
                'Final_Value': final_value,
                'vs_DCA_Pct': vs_dca,
            })
            print(f"{strategy.total_coins:,.4f} coins ({vs_dca:+.1f}% vs DCA)")
        else:
            results.append({
                'Asset': asset,
                'Strategy': strat_name,
                'Coins': 0,
                'Avg_Price': 0,
                'Capital_Used_Pct': 0,
                'Buy_Signals': 0,
                'Final_Value': 0,
                'vs_DCA_Pct': -100,
            })
            print(f"No signals")

# =============================================================================
# SAVE RESULTS
# =============================================================================
df = pd.DataFrame(results)
output_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/accumulation/phase_2/phase_2_results.csv'
df.to_csv(output_path, index=False)

print(f"\n{'='*70}")
print(f"RESULTS SAVED TO: {output_path}")
print(f"{'='*70}")

# =============================================================================
# SUMMARY
# =============================================================================
print(f"\n{'='*70}")
print("MOON DEV'S PHASE 2 ACCUMULATION RESULTS")
print(f"{'='*70}")

# Average vs DCA for each strategy
print(f"\nAverage performance vs Daily DCA (sorted by best):")
print("-" * 60)

avg_results = []
for strat in df['Strategy'].unique():
    if strat == 'Daily DCA':
        continue
    avg_vs_dca = df[df['Strategy'] == strat]['vs_DCA_Pct'].mean()
    avg_results.append((strat, avg_vs_dca))

avg_results.sort(key=lambda x: x[1], reverse=True)

for strat, avg in avg_results:
    emoji = "+" if avg > 0 else ""
    winner = " <-- WINNER!" if avg >= 20 else " <-- BEATS P1!" if avg > 37.8 else ""
    print(f"   {strat:25s}: {emoji}{avg:>6.1f}%{winner}")

# Per-asset breakdown for top strategies
print(f"\n{'='*70}")
print("TOP 5 STRATEGIES BY ASSET:")
print(f"{'='*70}")

for asset in DATA_PATHS.keys():
    print(f"\n{asset}:")
    print("-" * 50)
    asset_df = df[df['Asset'] == asset].copy()
    asset_df = asset_df[asset_df['Strategy'] != 'Daily DCA']
    asset_df = asset_df.sort_values('vs_DCA_Pct', ascending=False).head(5)

    for i, (_, row) in enumerate(asset_df.iterrows()):
        print(f"   {i+1}. {row['Strategy']:25s} | {row['vs_DCA_Pct']:>+7.1f}% | {row['Coins']:>12,.2f} coins")

print(f"\n{'='*70}")
print("Moon Dev's Phase 2 Analysis Complete!")
print(f"{'='*70}")
