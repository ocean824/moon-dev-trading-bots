"""
Moon Dev's Volume Breakout ADX Strategy
========================================
Volume breakout with ADX to confirm trend strength after breakout
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

class VolumeBreakoutADX(Strategy):
    """
    Volume Breakout Strategy with ADX Confirmation
    - Uses ADX to confirm trend strength after breakout
    - DI+ and DI- for directional confirmation
    - Only enters when ADX shows strong trend formation
    """
    
    # Strategy parameters
    consolidation_period = 20
    volume_ma_period = 20
    volume_surge_multiplier = 1.5
    atr_period = 14
    cmf_period = 20
    obv_ma_period = 10
    
    # ADX parameters
    adx_period = 14
    adx_threshold = 25  # Minimum ADX for trend strength
    adx_strong = 40     # Strong trend threshold
    di_threshold = 20   # Minimum DI value for direction
    
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
        
        # ADX, DI+, DI-
        adx_result = ta.adx(high, low, close, self.adx_period)
        if adx_result is not None and not adx_result.empty:
            self.adx = self.I(lambda: adx_result[f'ADX_{self.adx_period}'].ffill().values, name='ADX')
            self.di_plus = self.I(lambda: adx_result[f'DMP_{self.adx_period}'].ffill().values, name='DI+')
            self.di_minus = self.I(lambda: adx_result[f'DMN_{self.adx_period}'].ffill().values, name='DI-')
        else:
            # Fallback if ADX calculation fails
            self.adx = self.I(lambda: np.full(len(close), 20), name='ADX')
            self.di_plus = self.I(lambda: np.full(len(close), 20), name='DI+')
            self.di_minus = self.I(lambda: np.full(len(close), 20), name='DI-')
        
        # ADX slope for trend acceleration
        adx_values = pd.Series(self.adx)
        self.adx_slope = self.I(lambda: ta.slope(adx_values, 5).values, name='ADX_Slope')
        
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
        # Parabolic SAR for additional trend confirmation
        psar_result = ta.psar(high, low, close)
        if psar_result is not None and not psar_result.empty:
            # Get the appropriate column names
            if 'PSARl_0.02_0.2' in psar_result.columns:
                self.psar_long = self.I(lambda: psar_result['PSARl_0.02_0.2'].ffill().values, name='PSAR_Long')
            else:
                self.psar_long = self.I(lambda: np.full(len(close), np.nan), name='PSAR_Long')
            
            if 'PSARs_0.02_0.2' in psar_result.columns:
                self.psar_short = self.I(lambda: psar_result['PSARs_0.02_0.2'].ffill().values, name='PSAR_Short')
            else:
                self.psar_short = self.I(lambda: np.full(len(close), np.nan), name='PSAR_Short')
        else:
            self.psar_long = self.I(lambda: np.full(len(close), np.nan), name='PSAR_Long')
            self.psar_short = self.I(lambda: np.full(len(close), np.nan), name='PSAR_Short')
    
    def get_adx_strength(self):
        """Categorize ADX strength"""
        if len(self.adx) < 1:
            return 'weak'
            
        adx_val = self.adx[-1]
        adx_slope_val = self.adx_slope[-1] if len(self.adx_slope) > 0 else 0
        
        if pd.isna(adx_val):
            return 'weak'
        
        # Strong and rising trend
        if adx_val >= self.adx_strong and not pd.isna(adx_slope_val) and adx_slope_val > 0:
            return 'very_strong'
        # Strong trend
        elif adx_val >= self.adx_strong:
            return 'strong'
        # Moderate trend
        elif adx_val >= self.adx_threshold:
            return 'moderate'
        # Weak trend
        else:
            return 'weak'
    
    def is_consolidating(self):
        """Check if price is consolidating (low ADX preferred)"""
        if len(self.data.Close) < self.consolidation_period + 5:
            return False
            
        current_atr = self.atr[-1]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        price_std = self.price_std[-1]
        adx_val = self.adx[-1]
        
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
        
        # Low ADX indicates consolidation/no trend
        low_adx = adx_val < 25 if not pd.isna(adx_val) else True
        
        is_tight_range = range_height < (current_atr * 4)
        is_low_volatility = std_percent < 0.04
        
        # Consolidation = tight range + low volatility + low ADX
        return is_tight_range and is_low_volatility and low_adx
    
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
        """Determine breakout direction with ADX/DI confirmation"""
        if len(self.data.Close) < 2:
            return None
            
        price = self.data.Close[-1]
        prev_price = self.data.Close[-2]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        
        # ADX and DI values
        adx_val = self.adx[-1]
        di_plus_val = self.di_plus[-1]
        di_minus_val = self.di_minus[-1]
        adx_slope_val = self.adx_slope[-1] if len(self.adx_slope) > 0 else 0
        
        # PSAR values
        psar_long_val = self.psar_long[-1] if len(self.psar_long) > 0 else np.nan
        psar_short_val = self.psar_short[-1] if len(self.psar_short) > 0 else np.nan
        
        # Volume indicators
        obv_current = self.obv[-1]
        obv_ma_current = self.obv_ma[-1]
        cmf_value = self.cmf[-1]
        
        if pd.isna(high_range) or pd.isna(low_range) or pd.isna(obv_current) or pd.isna(obv_ma_current) or pd.isna(cmf_value):
            return None
        
        # Breakout conditions
        broke_above = prev_price <= high_range and price > high_range
        broke_below = prev_price >= low_range and price < low_range
        
        # ADX confirmations
        adx_strength = self.get_adx_strength()
        adx_rising = adx_slope_val > 0 if not pd.isna(adx_slope_val) else False
        
        # Directional confirmations
        di_bullish = False
        di_bearish = False
        if not pd.isna(di_plus_val) and not pd.isna(di_minus_val):
            di_bullish = di_plus_val > di_minus_val and di_plus_val > self.di_threshold
            di_bearish = di_minus_val > di_plus_val and di_minus_val > self.di_threshold
        
        # PSAR confirmation
        psar_bullish = not pd.isna(psar_long_val) and pd.isna(psar_short_val)
        psar_bearish = not pd.isna(psar_short_val) and pd.isna(psar_long_val)
        
        # Volume confirmations
        obv_bullish = obv_current > obv_ma_current
        obv_bearish = obv_current < obv_ma_current
        cmf_bullish = cmf_value > 0
        cmf_bearish = cmf_value < 0
        
        # Long breakout: needs ADX confirmation of trend starting
        if broke_above and (obv_bullish or cmf_bullish):
            # Need ADX rising or already strong, plus directional confirmation
            if (adx_strength in ['moderate', 'strong', 'very_strong'] or adx_rising) and di_bullish:
                # Bonus confirmation from PSAR
                if psar_bullish or True:  # PSAR is optional
                    return 'long'
        
        # Short breakout: needs ADX confirmation
        elif broke_below and (obv_bearish or cmf_bearish):
            if (adx_strength in ['moderate', 'strong', 'very_strong'] or adx_rising) and di_bearish:
                if psar_bearish or True:  # PSAR is optional
                    return 'short'
            
        return None
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.consolidation_period, self.volume_ma_period, self.obv_ma_period, self.adx_period) + 5:
            return
        
        price = self.data.Close[-1]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        atr_value = self.atr[-1]
        
        if pd.isna(high_range) or pd.isna(low_range) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Entry logic
        if not self.position:
            # First check for consolidation (low ADX)
            if self.is_consolidating():
                # Then check for volume surge
                if self.detect_volume_surge():
                    # Finally check for breakout with ADX confirmation
                    direction = self.get_breakout_direction()
                    adx_strength = self.get_adx_strength()
                    
                    if direction == 'long':
                        consolidation_range = high_range - low_range
                        
                        # Tighter stop for stronger ADX
                        if adx_strength in ['strong', 'very_strong']:
                            stop_multiplier = 1.5
                            profit_multiplier = 3.0  # Higher target for strong trends
                        else:
                            stop_multiplier = 2.0
                            profit_multiplier = self.profit_target_multiplier
                        
                        stop_loss = low_range - (atr_value * stop_multiplier)
                        take_profit = price + (consolidation_range * profit_multiplier)
                        
                        self.buy(sl=stop_loss, tp=take_profit, size=0.95)
                    
                    elif direction == 'short':
                        consolidation_range = high_range - low_range
                        
                        if adx_strength in ['strong', 'very_strong']:
                            stop_multiplier = 1.5
                            profit_multiplier = 3.0
                        else:
                            stop_multiplier = 2.0
                            profit_multiplier = self.profit_target_multiplier
                        
                        stop_loss = high_range + (atr_value * stop_multiplier)
                        take_profit = price - (consolidation_range * profit_multiplier)
                        
                        self.sell(sl=stop_loss, tp=take_profit, size=0.95)
        
        # Exit logic
        else:
            # Get current values
            adx_val = self.adx[-1]
            di_plus_val = self.di_plus[-1]
            di_minus_val = self.di_minus[-1]
            cmf_value = self.cmf[-1]
            
            if self.position.is_long:
                # Exit if trend weakens (ADX drops) or DI- crosses above DI+
                if not pd.isna(adx_val) and adx_val < 20:
                    self.position.close()
                elif not pd.isna(di_plus_val) and not pd.isna(di_minus_val):
                    if di_minus_val > di_plus_val:
                        self.position.close()
                elif not pd.isna(cmf_value) and cmf_value < -0.1:
                    self.position.close()
            
            elif self.position.is_short:
                # Exit if trend weakens or DI+ crosses above DI-
                if not pd.isna(adx_val) and adx_val < 20:
                    self.position.close()
                elif not pd.isna(di_plus_val) and not pd.isna(di_minus_val):
                    if di_plus_val > di_minus_val:
                        self.position.close()
                elif not pd.isna(cmf_value) and cmf_value > 0.1:
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S VOLUME BREAKOUT ADX STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Volume Breakout with ADX trend confirmation across all datasets...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        VolumeBreakoutADX,
        'VolumeBreakoutADX',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/VolumeBreakoutADX.csv")
        print("="*80)

if __name__ == "__main__":
    main()