"""
Moon Dev's Volume Breakout Fibonacci Strategy
==============================================
Volume breakout with Fibonacci extension levels for profit targets
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

class VolumeBreakoutFibonacci(Strategy):
    """
    Volume Breakout Strategy with Fibonacci Extensions
    - Uses Fibonacci levels for precise profit targets
    - 1.618, 2.618, 3.618 extensions from consolidation range
    - Dynamic stop loss adjustment based on Fib levels
    """
    
    # Strategy parameters
    consolidation_period = 20
    volume_ma_period = 20
    volume_surge_multiplier = 1.5
    atr_period = 14
    cmf_period = 20
    obv_ma_period = 10
    
    # Fibonacci levels
    fib_1 = 1.618  # First target
    fib_2 = 2.618  # Second target
    fib_3 = 3.618  # Third target
    
    # Position management
    partial_exit_percent = 0.33  # Exit 1/3 at each Fib level
    
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
        # Fibonacci retracement levels for current range
        self.fib_38 = self.I(lambda: self.calculate_fib_level(0.382), name='Fib38')
        self.fib_50 = self.I(lambda: self.calculate_fib_level(0.5), name='Fib50')
        self.fib_61 = self.I(lambda: self.calculate_fib_level(0.618), name='Fib61')
        
        # Track entry for Fibonacci calculations
        self.entry_price = 0
        self.entry_range = 0
        self.target_1_hit = False
        self.target_2_hit = False
        
    def calculate_fib_level(self, level):
        """Calculate Fibonacci retracement level"""
        high = pd.Series(self.data.High).rolling(self.consolidation_period).max()
        low = pd.Series(self.data.Low).rolling(self.consolidation_period).min()
        return (low + (high - low) * level).values
    
    def calculate_fib_extension(self, entry_price, range_size, level, is_long=True):
        """Calculate Fibonacci extension level from entry"""
        if is_long:
            return entry_price + (range_size * level)
        else:
            return entry_price - (range_size * level)
    
    def is_consolidating(self):
        """Check if price is in consolidation phase"""
        if len(self.data.Close) < self.consolidation_period + 5:
            return False
            
        current_atr = self.atr[-1]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        price_std = self.price_std[-1]
        
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
        
        # Check if price is near Fibonacci levels (suggests balance)
        current_price = self.data.Close[-1]
        fib_50 = self.fib_50[-1]
        near_fib = abs(current_price - fib_50) < (current_atr * 0.5) if not pd.isna(fib_50) else False
        
        is_tight_range = range_height < (current_atr * 4)
        is_low_volatility = std_percent < 0.04
        
        return is_tight_range and is_low_volatility
    
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
        """Determine breakout direction with Fibonacci confirmation"""
        if len(self.data.Close) < 2:
            return None
            
        price = self.data.Close[-1]
        prev_price = self.data.Close[-2]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        
        obv_current = self.obv[-1]
        obv_ma_current = self.obv_ma[-1]
        cmf_value = self.cmf[-1]
        
        # Fibonacci levels
        fib_61 = self.fib_61[-1]
        fib_38 = self.fib_38[-1]
        
        if pd.isna(high_range) or pd.isna(low_range) or pd.isna(obv_current) or pd.isna(obv_ma_current) or pd.isna(cmf_value):
            return None
        
        # Breakout conditions
        broke_above = prev_price <= high_range and price > high_range
        broke_below = prev_price >= low_range and price < low_range
        
        # Additional Fibonacci confirmation
        above_fib_61 = price > fib_61 if not pd.isna(fib_61) else True
        below_fib_38 = price < fib_38 if not pd.isna(fib_38) else True
        
        # Volume indicators
        obv_bullish = obv_current > obv_ma_current
        obv_bearish = obv_current < obv_ma_current
        cmf_bullish = cmf_value > 0
        cmf_bearish = cmf_value < 0
        
        # Long breakout with Fibonacci confirmation
        if broke_above and obv_bullish and cmf_bullish and above_fib_61:
            return 'long'
        
        # Short breakout with Fibonacci confirmation
        elif broke_below and obv_bearish and cmf_bearish and below_fib_38:
            return 'short'
            
        return None
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.consolidation_period, self.volume_ma_period, self.obv_ma_period) + 5:
            return
        
        price = self.data.Close[-1]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        atr_value = self.atr[-1]
        
        if pd.isna(high_range) or pd.isna(low_range) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Entry logic
        if not self.position:
            # Reset target tracking
            self.target_1_hit = False
            self.target_2_hit = False
            
            if self.is_consolidating():
                if self.detect_volume_surge():
                    direction = self.get_breakout_direction()
                    
                    if direction == 'long':
                        consolidation_range = high_range - low_range
                        self.entry_price = price
                        self.entry_range = consolidation_range
                        
                        # Fibonacci-based stops and targets
                        stop_loss = low_range - (consolidation_range * 0.236)  # 23.6% Fib below range
                        
                        # Use highest Fib extension as ultimate target
                        take_profit = self.calculate_fib_extension(price, consolidation_range, self.fib_3, True)
                        
                        self.buy(sl=stop_loss, tp=take_profit, size=0.95)
                    
                    elif direction == 'short':
                        consolidation_range = high_range - low_range
                        self.entry_price = price
                        self.entry_range = consolidation_range
                        
                        stop_loss = high_range + (consolidation_range * 0.236)
                        take_profit = self.calculate_fib_extension(price, consolidation_range, self.fib_3, False)
                        
                        self.sell(sl=stop_loss, tp=take_profit, size=0.95)
        
        # Position management with Fibonacci targets
        else:
            if self.entry_price > 0 and self.entry_range > 0:
                # Calculate Fibonacci targets
                if self.position.is_long:
                    target_1 = self.calculate_fib_extension(self.entry_price, self.entry_range, self.fib_1, True)
                    target_2 = self.calculate_fib_extension(self.entry_price, self.entry_range, self.fib_2, True)
                    
                    # Trail stop to breakeven after first target
                    if price >= target_1 and not self.target_1_hit:
                        self.target_1_hit = True
                        # Move stop to breakeven
                        new_stop = self.entry_price + (self.entry_range * 0.1)
                        if hasattr(self.position, 'sl') and new_stop > self.position.sl:
                            self.position.sl = new_stop
                    
                    # Trail stop to first target after second target
                    if price >= target_2 and not self.target_2_hit:
                        self.target_2_hit = True
                        # Move stop to first target
                        if hasattr(self.position, 'sl'):
                            self.position.sl = target_1
                
                elif self.position.is_short:
                    target_1 = self.calculate_fib_extension(self.entry_price, self.entry_range, self.fib_1, False)
                    target_2 = self.calculate_fib_extension(self.entry_price, self.entry_range, self.fib_2, False)
                    
                    if price <= target_1 and not self.target_1_hit:
                        self.target_1_hit = True
                        new_stop = self.entry_price - (self.entry_range * 0.1)
                        if hasattr(self.position, 'sl') and new_stop < self.position.sl:
                            self.position.sl = new_stop
                    
                    if price <= target_2 and not self.target_2_hit:
                        self.target_2_hit = True
                        if hasattr(self.position, 'sl'):
                            self.position.sl = target_1
            
            # Exit on momentum reversal
            cmf_value = self.cmf[-1]
            if not pd.isna(cmf_value):
                if self.position.is_long and cmf_value < -0.15:
                    self.position.close()
                elif self.position.is_short and cmf_value > 0.15:
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S VOLUME BREAKOUT FIBONACCI STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Volume Breakout with Fibonacci extensions across all datasets...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        VolumeBreakoutFibonacci,
        'VolumeBreakoutFibonacci',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/VolumeBreakoutFibonacci.csv")
        print("="*80)

if __name__ == "__main__":
    main()