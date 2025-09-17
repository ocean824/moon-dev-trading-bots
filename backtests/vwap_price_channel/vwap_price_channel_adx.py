"""
Moon Dev's VWAP Price Channel ADX Strategy
===========================================
VWAP Price Channel with ADX for trend strength filtering
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class VWAPPriceChannelADX(Strategy):
    """
    VWAP Price Channel Strategy with ADX Trend Strength Filter
    - Uses VWAP-based dynamic price channels
    - Only trades when ADX > 25 (strong trend)
    - ADX provides trend strength confirmation
    """

    # Strategy parameters
    length = 20  # Lookback period for highest/lowest
    adx_period = 14  # ADX period
    adx_threshold = 25  # Minimum ADX for trading
    atr_multiplier = 2.0  # For stop loss
    take_profit_ratio = 2.5  # Risk/reward ratio

    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)

        # Calculate ADX
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        adx_col = f'ADX_{self.adx_period}'
        dmp_col = f'DMP_{self.adx_period}'
        dmn_col = f'DMN_{self.adx_period}'

        self.adx = self.I(lambda: adx_result[adx_col].ffill().values, name='ADX')
        self.dmp = self.I(lambda: adx_result[dmp_col].ffill().values, name='DM+')
        self.dmn = self.I(lambda: adx_result[dmn_col].ffill().values, name='DM-')

        # Calculate highest and lowest over period
        highest = high.rolling(window=self.length, min_periods=1).max()
        lowest = low.rolling(window=self.length, min_periods=1).min()

        # Detect new highs and lows
        new_high = (high == highest).astype(float)
        new_low = (low == lowest).astype(float)

        # Calculate VWAP for highs and lows
        # High VWAP calculation
        high_vwap_values = []
        cumulative_high_vol = 0
        cumulative_high_pv = 0

        for i in range(len(high)):
            if new_high.iloc[i] == 1:
                cumulative_high_vol = volume.iloc[i]
                cumulative_high_pv = high.iloc[i] * volume.iloc[i]
            else:
                cumulative_high_vol += volume.iloc[i]
                cumulative_high_pv += high.iloc[i] * volume.iloc[i]

            if cumulative_high_vol > 0:
                high_vwap_values.append(cumulative_high_pv / cumulative_high_vol)
            else:
                high_vwap_values.append(high.iloc[i])

        # Low VWAP calculation
        low_vwap_values = []
        cumulative_low_vol = 0
        cumulative_low_pv = 0

        for i in range(len(low)):
            if new_low.iloc[i] == 1:
                cumulative_low_vol = volume.iloc[i]
                cumulative_low_pv = low.iloc[i] * volume.iloc[i]
            else:
                cumulative_low_vol += volume.iloc[i]
                cumulative_low_pv += low.iloc[i] * volume.iloc[i]

            if cumulative_low_vol > 0:
                low_vwap_values.append(cumulative_low_pv / cumulative_low_vol)
            else:
                low_vwap_values.append(low.iloc[i])

        high_vwap = pd.Series(high_vwap_values, index=high.index)
        low_vwap = pd.Series(low_vwap_values, index=low.index)

        # Calculate channel bounds
        upper_channel = []
        lower_channel = []

        for i in range(len(close)):
            if i == 0:
                upper_channel.append(highest.iloc[i])
                lower_channel.append(lowest.iloc[i])
            else:
                # Upper channel logic
                if new_high.iloc[i] == 1:
                    upper_channel.append(highest.iloc[i])
                else:
                    h_change = high_vwap.iloc[i] - high_vwap.iloc[i-1] if i > 0 else 0
                    if highest.iloc[i] == highest.iloc[i-1]:
                        upper_channel.append(upper_channel[-1] + h_change)
                    else:
                        upper_channel.append(min(highest.iloc[i], upper_channel[-1] + h_change))

                # Lower channel logic
                if new_low.iloc[i] == 1:
                    lower_channel.append(lowest.iloc[i])
                else:
                    l_change = low_vwap.iloc[i] - low_vwap.iloc[i-1] if i > 0 else 0
                    if lowest.iloc[i] == lowest.iloc[i-1]:
                        lower_channel.append(lower_channel[-1] + l_change)
                    else:
                        lower_channel.append(max(lowest.iloc[i], lower_channel[-1] + l_change))

        upper_channel = pd.Series(upper_channel, index=close.index)
        lower_channel = pd.Series(lower_channel, index=close.index)

        # Calculate middle channel
        middle_channel = (upper_channel + lower_channel) / 2

        # Trend detection
        dir_values = []
        dir2_values = []
        current_dir2 = 0

        for i in range(len(close)):
            if new_high.iloc[i] == 1:
                dir_values.append(1)
                current_dir2 = 1
            elif new_low.iloc[i] == 1:
                dir_values.append(-1)
                current_dir2 = -1
            else:
                dir_values.append(0)

            dir2_values.append(current_dir2)

        # Store as indicators
        self.upper_channel = self.I(lambda: upper_channel.ffill().values, name='Upper_Channel')
        self.lower_channel = self.I(lambda: lower_channel.ffill().values, name='Lower_Channel')
        self.middle_channel = self.I(lambda: middle_channel.ffill().values, name='Middle_Channel')
        self.trend_direction = self.I(lambda: np.array(dir2_values), name='Trend_Direction')

        # ATR for risk management
        self.atr = self.I(ta.atr, high, low, close, 14)

    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.length, self.adx_period) + 5:
            return

        # Get current values
        price = self.data.Close[-1]

        upper = self.upper_channel[-1]
        lower = self.lower_channel[-1]
        middle = self.middle_channel[-1]
        trend = self.trend_direction[-1]
        adx_value = self.adx[-1]
        dmp_value = self.dmp[-1]
        dmn_value = self.dmn[-1]
        atr_value = self.atr[-1]

        # Previous values for crossover detection
        if len(self.data.Close) > 1:
            prev_close = self.data.Close[-2]
            prev_upper = self.upper_channel[-2]
            prev_lower = self.lower_channel[-2]
        else:
            return

        # Check for valid values
        if pd.isna(upper) or pd.isna(lower) or pd.isna(adx_value) or pd.isna(atr_value) or atr_value <= 0:
            return

        # Entry logic with ADX filter
        if not self.position:
            # Long signal: Price crosses above lower channel, trend is bullish, ADX > threshold, DM+ > DM-
            if (prev_close <= prev_lower and price > lower and
                trend == 1 and adx_value > self.adx_threshold and dmp_value > dmn_value):
                stop_loss = price - (atr_value * self.atr_multiplier)
                take_profit = price + (atr_value * self.atr_multiplier * self.take_profit_ratio)
                self.buy(sl=stop_loss, tp=take_profit, size=0.95)

            # Short signal: Price crosses below upper channel, trend is bearish, ADX > threshold, DM- > DM+
            elif (prev_close >= prev_upper and price < upper and
                  trend == -1 and adx_value > self.adx_threshold and dmn_value > dmp_value):
                stop_loss = price + (atr_value * self.atr_multiplier)
                take_profit = price - (atr_value * self.atr_multiplier * self.take_profit_ratio)
                self.sell(sl=stop_loss, tp=take_profit, size=0.95)

        # Exit logic - Exit on opposite signal, middle channel cross, or weak trend
        else:
            # Exit long
            if self.position.is_long:
                # Exit on bearish reversal, middle channel break, or weak trend (ADX < 20)
                if (price < middle) or (adx_value < 20) or \
                   (prev_close >= prev_upper and price < upper and trend == -1):
                    self.position.close()

            # Exit short
            elif self.position.is_short:
                # Exit on bullish reversal, middle channel break, or weak trend (ADX < 20)
                if (price > middle) or (adx_value < 20) or \
                   (prev_close <= prev_lower and price > lower and trend == 1):
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S VWAP PRICE CHANNEL ADX STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing VWAP Price Channel with ADX trend strength filter across all datasets...")
    print("="*80)

    # Run tests on all data sources without optimization
    results = test_on_all_data(
        VWAPPriceChannelADX,
        'VWAPPriceChannelADX',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )

    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/VWAPPriceChannelADX.csv")
        print("="*80)

if __name__ == "__main__":
    main()