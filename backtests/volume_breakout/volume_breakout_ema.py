"""
Moon Dev's Volume Breakout EMA Strategy
========================================
Volume breakout with EMA confirmation for trend direction
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

class VolumeBreakoutEMA(Strategy):
    """
    Volume Breakout Strategy with EMA Confirmation
    - Uses multiple EMAs to confirm breakout direction
    - EMA ribbon for trend strength assessment
    - Dynamic position sizing based on EMA alignment
    """
    
    # Strategy parameters
    consolidation_period = 20
    volume_ma_period = 20
    volume_surge_multiplier = 1.5
    atr_period = 14
    cmf_period = 20
    obv_ma_period = 10
    
    # EMA periods
    ema_fast = 8
    ema_medium = 21
    ema_slow = 55
    ema_anchor = 200  # Long-term trend
    
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
        
        # EMA ribbon
        self.ema_8 = self.I(ta.ema, close, self.ema_fast)
        self.ema_21 = self.I(ta.ema, close, self.ema_medium)
        self.ema_55 = self.I(ta.ema, close, self.ema_slow)
        self.ema_200 = self.I(ta.ema, close, self.ema_anchor)
        
        # EMA slope for momentum
        ema_21_values = ta.ema(close, self.ema_medium)
        self.ema_21_slope = self.I(lambda: ta.slope(ema_21_values, 5).values, name='EMA21_Slope')
        
        # Volume-weighted average (simplified VWAP fallback)
        try:
            vwap_values = ta.vwap(high, low, close, volume)
            if vwap_values is not None and not vwap_values.empty:
                self.vwap = self.I(lambda: vwap_values.values, name='VWAP')
            else:
                raise Exception('VWAP calculation failed')
        except:
            # Fallback: Volume-weighted typical price
            typical_price = (high + low + close) / 3
            vwap_simple = (typical_price * volume).rolling(20).sum() / volume.rolling(20).sum()
            self.vwap = self.I(lambda: vwap_simple.fillna(close).values, name='VWAP')
        
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
    def get_ema_alignment(self):
        """Check EMA alignment for trend confirmation"""
        if len(self.data.Close) < self.ema_anchor:
            return 'neutral'
            
        ema_8_val = self.ema_8[-1]
        ema_21_val = self.ema_21[-1]
        ema_55_val = self.ema_55[-1]
        ema_200_val = self.ema_200[-1]
        
        if pd.isna(ema_8_val) or pd.isna(ema_21_val) or pd.isna(ema_55_val) or pd.isna(ema_200_val):
            return 'neutral'
        
        # Perfect bullish alignment: 8 > 21 > 55 > 200
        if ema_8_val > ema_21_val > ema_55_val > ema_200_val:
            return 'strong_bullish'
        # Partial bullish: fast EMAs above slow
        elif ema_8_val > ema_21_val and ema_21_val > ema_55_val:
            return 'bullish'
        # Perfect bearish alignment: 8 < 21 < 55 < 200
        elif ema_8_val < ema_21_val < ema_55_val < ema_200_val:
            return 'strong_bearish'
        # Partial bearish
        elif ema_8_val < ema_21_val and ema_21_val < ema_55_val:
            return 'bearish'
        else:
            return 'neutral'
    
    def is_consolidating(self):
        """Check if price is consolidating around EMAs"""
        if len(self.data.Close) < max(self.consolidation_period, self.ema_slow) + 5:
            return False
            
        current_atr = self.atr[-1]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        price_std = self.price_std[-1]
        
        # EMA values
        ema_21_val = self.ema_21[-1]
        ema_55_val = self.ema_55[-1]
        current_price = self.data.Close[-1]
        
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
        
        # Additional check: price near EMAs suggests consolidation
        near_ema = False
        if not pd.isna(ema_21_val) and not pd.isna(ema_55_val):
            distance_to_ema = min(abs(current_price - ema_21_val), abs(current_price - ema_55_val))
            near_ema = distance_to_ema < (current_atr * 0.5)
        
        is_tight_range = range_height < (current_atr * 4)
        is_low_volatility = std_percent < 0.04
        
        return (is_tight_range and is_low_volatility) or near_ema
    
    def detect_volume_surge(self):
        """Check if there's a volume surge"""
        if len(self.data.Volume) < self.volume_ma_period + 1:
            return False
            
        current_volume = self.data.Volume[-1]
        avg_volume = self.volume_ma[-1]
        
        if pd.isna(avg_volume) or avg_volume <= 0:
            return False
            
        return current_volume > (avg_volume * self.volume_surge_multiplier)
    
    def get_breakout_direction(self):
        """Determine breakout direction with EMA confirmation"""
        if len(self.data.Close) < max(2, self.ema_anchor):
            return None
            
        price = self.data.Close[-1]
        prev_price = self.data.Close[-2]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        
        # EMA values
        ema_8_val = self.ema_8[-1]
        ema_21_val = self.ema_21[-1]
        ema_21_slope = self.ema_21_slope[-1] if len(self.ema_21_slope) > 0 else 0
        vwap_val = self.vwap[-1] if len(self.vwap) > 0 else price
        
        # Volume indicators
        obv_current = self.obv[-1]
        obv_ma_current = self.obv_ma[-1]
        cmf_value = self.cmf[-1]
        
        if pd.isna(high_range) or pd.isna(low_range) or pd.isna(obv_current) or pd.isna(obv_ma_current) or pd.isna(cmf_value):
            return None
        
        # Get EMA alignment
        ema_alignment = self.get_ema_alignment()
        
        # Breakout conditions
        broke_above = prev_price <= high_range and price > high_range
        broke_below = prev_price >= low_range and price < low_range
        
        # EMA confirmations
        above_emas = price > ema_8_val and price > ema_21_val if not pd.isna(ema_8_val) and not pd.isna(ema_21_val) else False
        below_emas = price < ema_8_val and price < ema_21_val if not pd.isna(ema_8_val) and not pd.isna(ema_21_val) else False
        ema_slope_up = ema_21_slope > 0 if not pd.isna(ema_21_slope) else False
        ema_slope_down = ema_21_slope < 0 if not pd.isna(ema_21_slope) else False
        
        # VWAP confirmation
        above_vwap = price > vwap_val if not pd.isna(vwap_val) else True
        below_vwap = price < vwap_val if not pd.isna(vwap_val) else True
        
        # Volume confirmations
        obv_bullish = obv_current > obv_ma_current
        obv_bearish = obv_current < obv_ma_current
        cmf_bullish = cmf_value > 0
        cmf_bearish = cmf_value < 0
        
        # Long breakout: needs EMA confirmation
        if broke_above and (obv_bullish or cmf_bullish):
            if ema_alignment in ['bullish', 'strong_bullish'] and above_emas and ema_slope_up and above_vwap:
                return 'long'
        
        # Short breakout: needs EMA confirmation
        elif broke_below and (obv_bearish or cmf_bearish):
            if ema_alignment in ['bearish', 'strong_bearish'] and below_emas and ema_slope_down and below_vwap:
                return 'short'
            
        return None
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.consolidation_period, self.volume_ma_period, self.obv_ma_period, self.ema_anchor) + 5:
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
                    ema_alignment = self.get_ema_alignment()
                    
                    if direction == 'long':
                        consolidation_range = high_range - low_range
                        
                        # Tighter stop for strong alignment
                        stop_multiplier = 1.5 if ema_alignment == 'strong_bullish' else 2.0
                        stop_loss = low_range - (atr_value * stop_multiplier)
                        
                        # Better profit target for strong trend
                        profit_multiplier = 2.5 if ema_alignment == 'strong_bullish' else self.profit_target_multiplier
                        take_profit = price + (consolidation_range * profit_multiplier)
                        
                        self.buy(sl=stop_loss, tp=take_profit, size=0.95)
                    
                    elif direction == 'short':
                        consolidation_range = high_range - low_range
                        
                        stop_multiplier = 1.5 if ema_alignment == 'strong_bearish' else 2.0
                        stop_loss = high_range + (atr_value * stop_multiplier)
                        
                        profit_multiplier = 2.5 if ema_alignment == 'strong_bearish' else self.profit_target_multiplier
                        take_profit = price - (consolidation_range * profit_multiplier)
                        
                        self.sell(sl=stop_loss, tp=take_profit, size=0.95)
        
        # Exit logic
        else:
            # Get current EMA values
            ema_8_val = self.ema_8[-1]
            ema_21_val = self.ema_21[-1]
            cmf_value = self.cmf[-1]
            
            if self.position.is_long:
                # Exit if price crosses below fast EMA or CMF turns negative
                if not pd.isna(ema_8_val) and price < ema_8_val:
                    self.position.close()
                elif not pd.isna(cmf_value) and cmf_value < -0.1:
                    self.position.close()
                # Exit if EMA alignment turns bearish
                elif self.get_ema_alignment() in ['bearish', 'strong_bearish']:
                    self.position.close()
            
            elif self.position.is_short:
                # Exit if price crosses above fast EMA or CMF turns positive
                if not pd.isna(ema_8_val) and price > ema_8_val:
                    self.position.close()
                elif not pd.isna(cmf_value) and cmf_value > 0.1:
                    self.position.close()
                # Exit if EMA alignment turns bullish
                elif self.get_ema_alignment() in ['bullish', 'strong_bullish']:
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S VOLUME BREAKOUT EMA STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Volume Breakout with EMA confirmation across all datasets...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        VolumeBreakoutEMA,
        'VolumeBreakoutEMA',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/VolumeBreakoutEMA.csv")
        print("="*80)

if __name__ == "__main__":
    main()