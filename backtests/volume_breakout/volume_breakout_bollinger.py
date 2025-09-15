"""
Moon Dev's Volume Breakout Bollinger Strategy
==============================================
Volume breakout with Bollinger Bands to identify consolidation and breakout points
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

class VolumeBreakoutBollinger(Strategy):
    """
    Volume Breakout Strategy with Bollinger Bands
    - Uses BB squeeze to identify consolidation periods
    - Confirms breakouts when price breaks BB with volume
    - BB width helps determine profit targets
    """
    
    # Strategy parameters
    consolidation_period = 20
    volume_ma_period = 20
    volume_surge_multiplier = 1.5
    atr_period = 14
    cmf_period = 20
    obv_ma_period = 10
    
    # Bollinger Band parameters
    bb_period = 20
    bb_std = 2.0
    bb_squeeze_threshold = 0.02  # BB width as % of price for squeeze detection
    
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
        
        # Bollinger Bands
        bb_result = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        upper_col = f'BBU_{self.bb_period}_{self.bb_std}'
        middle_col = f'BBM_{self.bb_period}_{self.bb_std}'
        lower_col = f'BBL_{self.bb_period}_{self.bb_std}'
        bandwidth_col = f'BBB_{self.bb_period}_{self.bb_std}'
        percent_col = f'BBP_{self.bb_period}_{self.bb_std}'
        
        self.bb_upper = self.I(lambda: bb_result[upper_col].ffill().values, name='BB_Upper')
        self.bb_middle = self.I(lambda: bb_result[middle_col].ffill().values, name='BB_Middle')
        self.bb_lower = self.I(lambda: bb_result[lower_col].ffill().values, name='BB_Lower')
        self.bb_width = self.I(lambda: bb_result[bandwidth_col].ffill().values, name='BB_Width')
        self.bb_percent = self.I(lambda: bb_result[percent_col].ffill().values, name='BB_Percent')
        
        # Keltner Channels for squeeze detection
        kc_result = ta.kc(high, low, close, length=20, scalar=1.5)
        if kc_result is not None and not kc_result.empty:
            self.kc_upper = self.I(lambda: kc_result.iloc[:, 0].ffill().values, name='KC_Upper')
            self.kc_lower = self.I(lambda: kc_result.iloc[:, 2].ffill().values, name='KC_Lower')
        else:
            # Fallback if KC calculation fails
            ema20 = ta.ema(close, 20)
            atr_val = ta.atr(high, low, close, 20)
            self.kc_upper = self.I(lambda: (ema20 + 1.5 * atr_val).values, name='KC_Upper')
            self.kc_lower = self.I(lambda: (ema20 - 1.5 * atr_val).values, name='KC_Lower')
        
        # Rolling high/low for additional consolidation detection
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
        # Track squeeze duration
        self.squeeze_count = 0
        self.in_squeeze = False
    
    def detect_bb_squeeze(self):
        """Detect Bollinger Band squeeze (consolidation)"""
        if len(self.bb_upper) < 2 or len(self.kc_upper) < 2:
            return False
            
        bb_upper = self.bb_upper[-1]
        bb_lower = self.bb_lower[-1]
        kc_upper = self.kc_upper[-1]
        kc_lower = self.kc_lower[-1]
        bb_width = self.bb_width[-1]
        bb_middle = self.bb_middle[-1]
        
        if pd.isna(bb_upper) or pd.isna(bb_lower) or pd.isna(kc_upper) or pd.isna(kc_lower) or pd.isna(bb_width):
            return False
        
        # Method 1: BB inside KC (classic squeeze)
        bb_inside_kc = bb_upper < kc_upper and bb_lower > kc_lower
        
        # Method 2: BB width is narrow relative to price
        if not pd.isna(bb_middle) and bb_middle > 0:
            width_percent = bb_width / bb_middle
            narrow_bands = width_percent < self.bb_squeeze_threshold
        else:
            narrow_bands = False
        
        # Method 3: BB width decreasing (getting tighter)
        if len(self.bb_width) > 5:
            width_ma = pd.Series(self.bb_width[-10:]).mean()
            width_decreasing = bb_width < width_ma if not pd.isna(width_ma) else False
        else:
            width_decreasing = False
        
        # Squeeze detected if any method triggers
        is_squeeze = bb_inside_kc or narrow_bands or width_decreasing
        
        # Track squeeze duration
        if is_squeeze:
            if not self.in_squeeze:
                self.in_squeeze = True
                self.squeeze_count = 1
            else:
                self.squeeze_count += 1
        else:
            self.in_squeeze = False
            self.squeeze_count = 0
        
        # Need at least 3 bars of squeeze for confirmation
        return self.squeeze_count >= 3
    
    def is_consolidating(self):
        """Check if price is consolidating using BB squeeze"""
        if len(self.data.Close) < self.consolidation_period + 5:
            return False
            
        # Primary method: BB squeeze
        bb_squeeze = self.detect_bb_squeeze()
        
        # Secondary method: traditional consolidation check
        current_atr = self.atr[-1]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        price_std = self.price_std[-1]
        
        if current_atr is None or high_range is None or low_range is None or price_std is None:
            return False
        if pd.isna(current_atr) or pd.isna(high_range) or pd.isna(low_range) or pd.isna(price_std):
            return bb_squeeze  # Return BB squeeze result if other checks fail
        
        if current_atr <= 0:
            return bb_squeeze
            
        range_height = high_range - low_range
        avg_price = (high_range + low_range) / 2
        range_percent = (range_height / avg_price) if avg_price > 0 else 0
        std_percent = (price_std / avg_price) if avg_price > 0 else 0
        
        is_tight_range = range_height < (current_atr * 4)
        is_low_volatility = std_percent < 0.04
        
        # Consolidation = BB squeeze OR traditional consolidation
        return bb_squeeze or (is_tight_range and is_low_volatility)
    
    def detect_volume_surge(self):
        """Check if there's a volume surge"""
        if len(self.data.Volume) < self.volume_ma_period + 1:
            return False
            
        current_volume = self.data.Volume[-1]
        avg_volume = self.volume_ma[-1]
        
        if pd.isna(avg_volume) or avg_volume <= 0:
            return False
            
        # Lower threshold if coming out of BB squeeze
        threshold = 1.5 if self.in_squeeze else self.volume_surge_multiplier
        
        return current_volume > (avg_volume * threshold)
    
    def get_breakout_direction(self):
        """Determine breakout direction with BB confirmation"""
        if len(self.data.Close) < 2:
            return None
            
        price = self.data.Close[-1]
        prev_price = self.data.Close[-2]
        
        # Bollinger Band values
        bb_upper = self.bb_upper[-1]
        bb_middle = self.bb_middle[-1]
        bb_lower = self.bb_lower[-1]
        bb_percent = self.bb_percent[-1]
        bb_width = self.bb_width[-1]
        
        # Use rolling high/low as alternative breakout levels
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        
        # Volume indicators
        obv_current = self.obv[-1]
        obv_ma_current = self.obv_ma[-1]
        cmf_value = self.cmf[-1]
        
        if pd.isna(bb_upper) or pd.isna(bb_lower) or pd.isna(bb_middle):
            return None
        
        if pd.isna(obv_current) or pd.isna(obv_ma_current) or pd.isna(cmf_value):
            return None
        
        # BB breakout conditions
        bb_broke_above = prev_price <= bb_upper and price > bb_upper
        bb_broke_below = prev_price >= bb_lower and price < bb_lower
        
        # Alternative: Range breakout (if BB squeeze was detected)
        range_broke_above = False
        range_broke_below = False
        if self.in_squeeze and not pd.isna(high_range) and not pd.isna(low_range):
            range_broke_above = prev_price <= high_range and price > high_range
            range_broke_below = prev_price >= low_range and price < low_range
        
        # BB expansion confirmation (bands widening after squeeze)
        bb_expanding = False
        if len(self.bb_width) > 2:
            bb_expanding = bb_width > self.bb_width[-2]
        
        # Volume confirmations
        obv_bullish = obv_current > obv_ma_current
        obv_bearish = obv_current < obv_ma_current
        cmf_bullish = cmf_value > 0.05
        cmf_bearish = cmf_value < -0.05
        
        # %B confirmation (position within bands)
        bb_percent_bullish = bb_percent > 0.8 if not pd.isna(bb_percent) else False
        bb_percent_bearish = bb_percent < 0.2 if not pd.isna(bb_percent) else False
        
        # Long breakout: BB breakout or range breakout with confirmations
        if (bb_broke_above or range_broke_above) and obv_bullish and cmf_bullish:
            # Extra confirmation: BB expanding and %B bullish
            if bb_expanding or bb_percent_bullish:
                return 'long'
        
        # Short breakout: BB breakout or range breakout with confirmations
        elif (bb_broke_below or range_broke_below) and obv_bearish and cmf_bearish:
            if bb_expanding or bb_percent_bearish:
                return 'short'
            
        return None
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.consolidation_period, self.volume_ma_period, self.obv_ma_period, self.bb_period) + 5:
            return
        
        price = self.data.Close[-1]
        bb_upper = self.bb_upper[-1]
        bb_middle = self.bb_middle[-1]
        bb_lower = self.bb_lower[-1]
        bb_width = self.bb_width[-1]
        atr_value = self.atr[-1]
        
        if pd.isna(bb_upper) or pd.isna(bb_lower) or pd.isna(bb_middle) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Entry logic
        if not self.position:
            # Check for consolidation (BB squeeze)
            if self.is_consolidating():
                # Check for volume surge
                if self.detect_volume_surge():
                    # Check for breakout direction
                    direction = self.get_breakout_direction()
                    
                    if direction == 'long':
                        # Use BB width for dynamic targets
                        bb_range = bb_upper - bb_lower
                        
                        # Tighter stop if squeeze was detected
                        if self.in_squeeze:
                            stop_loss = bb_lower - (atr_value * 0.5)
                            # Higher profit target after squeeze breakout
                            take_profit = price + (bb_range * 2.5)
                        else:
                            stop_loss = bb_lower
                            take_profit = price + (bb_range * self.profit_target_multiplier)
                        
                        self.buy(sl=stop_loss, tp=take_profit, size=0.95)
                    
                    elif direction == 'short':
                        bb_range = bb_upper - bb_lower
                        
                        if self.in_squeeze:
                            stop_loss = bb_upper + (atr_value * 0.5)
                            take_profit = price - (bb_range * 2.5)
                        else:
                            stop_loss = bb_upper
                            take_profit = price - (bb_range * self.profit_target_multiplier)
                        
                        self.sell(sl=stop_loss, tp=take_profit, size=0.95)
        
        # Exit logic
        else:
            bb_percent = self.bb_percent[-1] if len(self.bb_percent) > 0 else 0.5
            cmf_value = self.cmf[-1]
            
            if self.position.is_long:
                # Exit if price touches lower BB or %B goes below 0
                if price <= bb_lower:
                    self.position.close()
                elif not pd.isna(bb_percent) and bb_percent < 0:
                    self.position.close()
                # Exit if momentum reverses
                elif not pd.isna(cmf_value) and cmf_value < -0.1:
                    self.position.close()
                # Exit if BB starts contracting again (new squeeze)
                elif self.detect_bb_squeeze() and self.squeeze_count > 5:
                    self.position.close()
            
            elif self.position.is_short:
                # Exit if price touches upper BB or %B goes above 1
                if price >= bb_upper:
                    self.position.close()
                elif not pd.isna(bb_percent) and bb_percent > 1:
                    self.position.close()
                # Exit if momentum reverses
                elif not pd.isna(cmf_value) and cmf_value > 0.1:
                    self.position.close()
                # Exit if BB starts contracting again
                elif self.detect_bb_squeeze() and self.squeeze_count > 5:
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S VOLUME BREAKOUT BOLLINGER STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Volume Breakout with Bollinger Bands across all datasets...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        VolumeBreakoutBollinger,
        'VolumeBreakoutBollinger',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/VolumeBreakoutBollinger.csv")
        print("="*80)

if __name__ == "__main__":
    main()