"""
Moon Dev's Volume Breakout MFI Strategy
========================================
Volume breakout with MFI (Money Flow Index) for volume-weighted confirmation
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

class VolumeBreakoutMFI(Strategy):
    """
    Volume Breakout Strategy with MFI Confirmation
    - Uses MFI as volume-weighted momentum oscillator
    - Identifies overbought/oversold conditions during consolidation
    - Confirms breakouts with money flow direction
    """
    
    # Strategy parameters
    consolidation_period = 20
    volume_ma_period = 20
    volume_surge_multiplier = 1.5
    atr_period = 14
    cmf_period = 20
    obv_ma_period = 10
    
    # MFI parameters
    mfi_period = 14
    mfi_oversold = 30
    mfi_overbought = 70
    mfi_extreme_oversold = 20
    mfi_extreme_overbought = 80
    
    # Risk management
    profit_target_multiplier = 1.5
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # ATR for volatility
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # Volume indicators
        self.volume_ma = self.I(ta.sma, volume, self.volume_ma_period)
        
        # OBV
        obv_values = ta.obv(close, volume)
        self.obv = self.I(lambda: obv_values.values, name='OBV')
        self.obv_ma = self.I(ta.sma, obv_values, self.obv_ma_period)
        
        # CMF
        try:
            cmf_values = ta.cmf(high, low, close, volume, self.cmf_period)
            if cmf_values is not None and not cmf_values.empty:
                self.cmf = self.I(lambda: cmf_values.ffill().values, name='CMF')
            else:
                # Fallback: simple money flow calculation
                typical_price = (high + low + close) / 3
                raw_money_flow = typical_price * volume
                money_flow_sum = raw_money_flow.rolling(self.cmf_period).sum()
                volume_sum = volume.rolling(self.cmf_period).sum()
                cmf_simple = money_flow_sum / volume_sum
                self.cmf = self.I(lambda: cmf_simple.fillna(0).values, name='CMF')
        except:
            # Fallback: simple money flow calculation
            typical_price = (high + low + close) / 3
            raw_money_flow = typical_price * volume
            money_flow_sum = raw_money_flow.rolling(self.cmf_period).sum()
            volume_sum = volume.rolling(self.cmf_period).sum()
            cmf_simple = money_flow_sum / volume_sum
            self.cmf = self.I(lambda: cmf_simple.fillna(0).values, name='CMF')
        
        # MFI - Money Flow Index
        mfi_values = ta.mfi(high, low, close, volume, self.mfi_period)
        self.mfi = self.I(lambda: mfi_values.ffill().values, name='MFI')
        
        # MFI moving average for trend
        self.mfi_ma = self.I(ta.sma, mfi_values, 10)
        
        # MFI divergence detection - compare price and MFI trends
        price_roc = ta.roc(close, 10)
        mfi_roc = ta.roc(mfi_values, 10)
        self.price_roc = self.I(lambda: price_roc.values, name='PriceROC')
        self.mfi_roc = self.I(lambda: mfi_roc.values, name='MFIROC')
        
        # Volume Flow Indicator (VFI) for additional confirmation
        typical_price = (high + low + close) / 3
        raw_money_flow = typical_price * volume
        self.money_flow_ma = self.I(ta.sma, raw_money_flow, self.volume_ma_period)
        
        # Rolling high/low for consolidation
        # Calculate rolling high/low for consolidation detection
        rolling_high = pd.Series(high).rolling(self.consolidation_period).max()
        rolling_low = pd.Series(low).rolling(self.consolidation_period).min()
        rolling_std = pd.Series(close).rolling(self.consolidation_period).std()
        
        # Fill NaN values with the actual high/low/close values
        rolling_high = rolling_high.fillna(high)
        rolling_low = rolling_low.fillna(low)
        rolling_std = rolling_std.fillna(0)
        
        self.rolling_high = self.I(lambda: rolling_high.values, name='RollingHigh')
        self.rolling_low = self.I(lambda: rolling_low.values, name='RollingLow')
        self.price_std = self.I(lambda: rolling_std.values, name='PriceStd')        
        # Track MFI extremes
        self.mfi_was_oversold = False
        self.mfi_was_overbought = False
    
    def detect_mfi_divergence(self):
        """Detect bullish or bearish divergence between price and MFI"""
        if len(self.price_roc) < 5 or len(self.mfi_roc) < 5:
            return None
            
        # Get recent values
        price_trend = self.price_roc[-1]
        mfi_trend = self.mfi_roc[-1]
        
        if pd.isna(price_trend) or pd.isna(mfi_trend):
            return None
        
        # Bullish divergence: price falling but MFI rising
        if price_trend < -2 and mfi_trend > 2:
            return 'bullish_divergence'
        
        # Bearish divergence: price rising but MFI falling
        elif price_trend > 2 and mfi_trend < -2:
            return 'bearish_divergence'
        
        return None
    
    def get_mfi_signal(self):
        """Get MFI-based signal"""
        if len(self.mfi) < 2:
            return None
            
        mfi_current = self.mfi[-1]
        mfi_prev = self.mfi[-2]
        mfi_ma_current = self.mfi_ma[-1] if len(self.mfi_ma) > 0 else 50
        
        if pd.isna(mfi_current) or pd.isna(mfi_prev):
            return None
        
        # Track if MFI was in extreme zones
        if mfi_prev <= self.mfi_extreme_oversold:
            self.mfi_was_oversold = True
        elif mfi_prev >= self.mfi_extreme_overbought:
            self.mfi_was_overbought = True
        
        # Strong bullish: MFI crosses above oversold
        if mfi_prev <= self.mfi_oversold and mfi_current > self.mfi_oversold:
            return 'strong_bullish'
        
        # Strong bearish: MFI crosses below overbought
        elif mfi_prev >= self.mfi_overbought and mfi_current < self.mfi_overbought:
            return 'strong_bearish'
        
        # Moderate bullish: MFI above MA and rising
        elif mfi_current > mfi_ma_current and mfi_current > mfi_prev:
            return 'bullish'
        
        # Moderate bearish: MFI below MA and falling
        elif mfi_current < mfi_ma_current and mfi_current < mfi_prev:
            return 'bearish'
        
        return 'neutral'
    
    def is_consolidating(self):
        """Check if price is consolidating with MFI consideration"""
        if len(self.data.Close) < self.consolidation_period + 5:
            return False
            
        current_atr = self.atr[-1]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        price_std = self.price_std[-1]
        mfi_current = self.mfi[-1] if len(self.mfi) > 0 else 50
        
        if current_atr is None or high_range is None or low_range is None or price_std is None:
            return False
        if pd.isna(current_atr) or pd.isna(high_range) or pd.isna(low_range) or pd.isna(price_std):
            return False
        
        if current_atr <= 0:
            return False
            
        range_height = high_range - low_range
        avg_price = (high_range + low_range) / 2
        range_percent = (range_height / avg_price) if avg_price > 0 else 0
        std_percent = (price_std / avg_price) if avg_price > 0 else 0
        
        # MFI in neutral zone suggests consolidation
        mfi_neutral = 40 <= mfi_current <= 60 if not pd.isna(mfi_current) else True
        
        is_tight_range = range_height < (current_atr * 4)
        is_low_volatility = std_percent < 0.04
        
        # Consolidation = tight range + low volatility
        # MFI neutral is a bonus but not required
        return is_tight_range and is_low_volatility
    
    def detect_volume_surge(self):
        """Check for volume surge with money flow confirmation"""
        if len(self.data.Volume) < self.volume_ma_period + 1:
            return False
            
        current_volume = self.data.Volume[-1]
        avg_volume = self.volume_ma[-1]
        
        # Money flow check
        current_money_flow = (self.data.High[-1] + self.data.Low[-1] + self.data.Close[-1]) / 3 * current_volume
        avg_money_flow = self.money_flow_ma[-1] if len(self.money_flow_ma) > 0 else 0
        
        if pd.isna(avg_volume) or avg_volume <= 0:
            return False
            
        # Volume surge confirmed by money flow increase
        volume_surge = current_volume > (avg_volume * self.volume_surge_multiplier)
        
        if not pd.isna(avg_money_flow) and avg_money_flow > 0:
            money_flow_surge = current_money_flow > (avg_money_flow * 1.5)
            return volume_surge or money_flow_surge
        
        return volume_surge
    
    def get_breakout_direction(self):
        """Determine breakout direction with MFI confirmation"""
        if len(self.data.Close) < 2:
            return None
            
        price = self.data.Close[-1]
        prev_price = self.data.Close[-2]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        
        # MFI values and signals
        mfi_current = self.mfi[-1] if len(self.mfi) > 0 else 50
        mfi_signal = self.get_mfi_signal()
        divergence = self.detect_mfi_divergence()
        
        # Volume indicators
        obv_current = self.obv[-1]
        obv_ma_current = self.obv_ma[-1]
        cmf_value = self.cmf[-1]
        
        if pd.isna(high_range) or pd.isna(low_range) or pd.isna(obv_current) or pd.isna(obv_ma_current) or pd.isna(cmf_value):
            return None
        
        # Breakout conditions
        broke_above = prev_price <= high_range and price > high_range
        broke_below = prev_price >= low_range and price < low_range
        
        # Volume confirmations
        obv_bullish = obv_current > obv_ma_current
        obv_bearish = obv_current < obv_ma_current
        cmf_bullish = cmf_value > 0
        cmf_bearish = cmf_value < 0
        
        # Long breakout with MFI confirmation
        if broke_above and (obv_bullish or cmf_bullish):
            # Strong signal if MFI was oversold or showing bullish divergence
            if mfi_signal in ['strong_bullish', 'bullish'] or divergence == 'bullish_divergence':
                # Extra confirmation: MFI not overbought
                if not pd.isna(mfi_current) and mfi_current < self.mfi_extreme_overbought:
                    return 'long'
            # Also accept if MFI recently bounced from oversold
            elif self.mfi_was_oversold and not pd.isna(mfi_current) and mfi_current > self.mfi_oversold:
                self.mfi_was_oversold = False
                return 'long'
        
        # Short breakout with MFI confirmation
        elif broke_below and (obv_bearish or cmf_bearish):
            if mfi_signal in ['strong_bearish', 'bearish'] or divergence == 'bearish_divergence':
                # Extra confirmation: MFI not oversold
                if not pd.isna(mfi_current) and mfi_current > self.mfi_extreme_oversold:
                    return 'short'
            # Also accept if MFI recently dropped from overbought
            elif self.mfi_was_overbought and not pd.isna(mfi_current) and mfi_current < self.mfi_overbought:
                self.mfi_was_overbought = False
                return 'short'
            
        return None
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.consolidation_period, self.volume_ma_period, self.obv_ma_period, self.mfi_period) + 5:
            return
        
        price = self.data.Close[-1]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        atr_value = self.atr[-1]
        
        if pd.isna(high_range) or pd.isna(low_range) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Entry logic
        if not self.position:
            if self.is_consolidating():
                if self.detect_volume_surge():
                    direction = self.get_breakout_direction()
                    mfi_current = self.mfi[-1] if len(self.mfi) > 0 else 50
                    
                    if direction == 'long':
                        consolidation_range = high_range - low_range
                        
                        # Adjust risk based on MFI level
                        if not pd.isna(mfi_current):
                            if mfi_current < self.mfi_oversold:
                                # Better risk/reward when oversold
                                stop_multiplier = 1.5
                                profit_multiplier = 3.0
                            elif mfi_current < 50:
                                stop_multiplier = 1.75
                                profit_multiplier = 2.5
                            else:
                                stop_multiplier = 2.0
                                profit_multiplier = self.profit_target_multiplier
                        else:
                            stop_multiplier = 2.0
                            profit_multiplier = self.profit_target_multiplier
                        
                        stop_loss = low_range - (atr_value * stop_multiplier)
                        take_profit = price + (consolidation_range * profit_multiplier)
                        
                        self.buy(sl=stop_loss, tp=take_profit, size=0.95)
                    
                    elif direction == 'short':
                        consolidation_range = high_range - low_range
                        
                        if not pd.isna(mfi_current):
                            if mfi_current > self.mfi_overbought:
                                stop_multiplier = 1.5
                                profit_multiplier = 3.0
                            elif mfi_current > 50:
                                stop_multiplier = 1.75
                                profit_multiplier = 2.5
                            else:
                                stop_multiplier = 2.0
                                profit_multiplier = self.profit_target_multiplier
                        else:
                            stop_multiplier = 2.0
                            profit_multiplier = self.profit_target_multiplier
                        
                        stop_loss = high_range + (atr_value * stop_multiplier)
                        take_profit = price - (consolidation_range * profit_multiplier)
                        
                        self.sell(sl=stop_loss, tp=take_profit, size=0.95)
        
        # Exit logic
        else:
            mfi_current = self.mfi[-1] if len(self.mfi) > 0 else 50
            cmf_value = self.cmf[-1]
            divergence = self.detect_mfi_divergence()
            
            if self.position.is_long:
                # Exit if MFI becomes extremely overbought or shows bearish divergence
                if not pd.isna(mfi_current):
                    if mfi_current >= self.mfi_extreme_overbought:
                        self.position.close()
                    elif divergence == 'bearish_divergence':
                        self.position.close()
                # Exit on CMF reversal
                if not pd.isna(cmf_value) and cmf_value < -0.1:
                    self.position.close()
            
            elif self.position.is_short:
                # Exit if MFI becomes extremely oversold or shows bullish divergence
                if not pd.isna(mfi_current):
                    if mfi_current <= self.mfi_extreme_oversold:
                        self.position.close()
                    elif divergence == 'bullish_divergence':
                        self.position.close()
                # Exit on CMF reversal
                if not pd.isna(cmf_value) and cmf_value > 0.1:
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S VOLUME BREAKOUT MFI STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Volume Breakout with MFI confirmation across all datasets...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        VolumeBreakoutMFI,
        'VolumeBreakoutMFI',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/VolumeBreakoutMFI.csv")
        print("="*80)

if __name__ == "__main__":
    main()