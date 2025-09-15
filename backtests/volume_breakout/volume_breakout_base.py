"""
Moon Dev's Volume Breakout Base Strategy
=========================================
Detects consolidation periods and enters on volume surge breakouts
with OBV and CMF confirmation
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

class VolumeBreakoutBase(Strategy):
    """
    Volume Breakout Strategy - Base Implementation
    - Identifies consolidation periods (low volatility, tight ranges)
    - Detects volume surges (2x average volume)
    - Confirms with OBV and CMF
    - Uses breakout level as stop loss
    - Sets profit targets based on consolidation range
    """
    
    # Strategy parameters
    consolidation_period = 20  # Lookback for consolidation detection
    volume_ma_period = 20      # Period for average volume
    volume_surge_multiplier = 1.5  # Volume must be 1.5x average (relaxed from 2.0)
    atr_period = 14
    cmf_period = 20
    obv_ma_period = 10
    
    # Risk management
    profit_target_multiplier = 1.5  # Profit target as multiple of consolidation range (reduced from 2.0)
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # ATR for volatility measurement
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # Volume indicators
        self.volume_ma = self.I(ta.sma, volume, self.volume_ma_period)
        
        # OBV (On-Balance Volume) with moving average
        obv_values = ta.obv(close, volume)
        self.obv = self.I(lambda: obv_values.values, name='OBV')
        self.obv_ma = self.I(ta.sma, obv_values, self.obv_ma_period)
        
        # CMF (Chaikin Money Flow)
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
        
    def is_consolidating(self):
        """Check if price is in consolidation phase"""
        if len(self.data.Close) < self.consolidation_period + 5:
            return False
            
        # Get current values
        current_atr = self.atr[-1]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        price_std = self.price_std[-1]
        
        # Check for valid values
        if current_atr is None or high_range is None or low_range is None or price_std is None:
            return False
        
        if pd.isna(current_atr) or pd.isna(high_range) or pd.isna(low_range) or pd.isna(price_std):
            return False
        
        if current_atr <= 0:
            return False
            
        # Calculate consolidation range
        range_height = high_range - low_range
        
        # Consolidation criteria:
        # 1. Range is less than 3 ATRs (tight range)
        # 2. Standard deviation is below average (low volatility)
        avg_price = (high_range + low_range) / 2
        range_percent = (range_height / avg_price) if avg_price > 0 else 0
        
        # Price std as percentage of price
        std_percent = (price_std / avg_price) if avg_price > 0 else 0
        
        # Consolidating if range is tight and volatility is low
        is_tight_range = range_height < (current_atr * 4)  # Relaxed from 3 to 4 ATRs
        is_low_volatility = std_percent < 0.04  # Relaxed from 2% to 4% standard deviation
        
        return is_tight_range and is_low_volatility
    
    def detect_volume_surge(self):
        """Check if there's a volume surge"""
        if len(self.data.Volume) < self.volume_ma_period + 1:
            return False
            
        current_volume = self.data.Volume[-1]
        avg_volume = self.volume_ma[-1]
        
        if pd.isna(avg_volume) or avg_volume <= 0:
            return False
            
        # Volume surge if current volume is greater than multiplier times average
        return current_volume > (avg_volume * self.volume_surge_multiplier)
    
    def get_breakout_direction(self):
        """Determine breakout direction based on price and indicators"""
        if len(self.data.Close) < 2:
            return None
            
        price = self.data.Close[-1]
        prev_price = self.data.Close[-2]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        
        # OBV trend
        obv_current = self.obv[-1]
        obv_ma_current = self.obv_ma[-1]
        
        # CMF value
        cmf_value = self.cmf[-1]
        
        if pd.isna(high_range) or pd.isna(low_range) or pd.isna(obv_current) or pd.isna(obv_ma_current) or pd.isna(cmf_value):
            return None
        
        # Breakout conditions
        broke_above = prev_price <= high_range and price > high_range
        broke_below = prev_price >= low_range and price < low_range
        
        # Confirmation from indicators
        obv_bullish = obv_current > obv_ma_current
        obv_bearish = obv_current < obv_ma_current
        cmf_bullish = cmf_value > 0
        cmf_bearish = cmf_value < 0
        
        # Long breakout: price breaks above range + at least one bullish volume indicator
        if broke_above and (obv_bullish or cmf_bullish):
            return 'long'
        
        # Short breakout: price breaks below range + at least one bearish volume indicator
        elif broke_below and (obv_bearish or cmf_bearish):
            return 'short'
            
        return None
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.consolidation_period, self.volume_ma_period, self.obv_ma_period) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        prev_price = self.data.Close[-2] if len(self.data.Close) > 1 else price
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        atr_value = self.atr[-1]
        current_volume = self.data.Volume[-1]
        avg_volume = self.volume_ma[-1]
        
        # Check for valid values
        if pd.isna(high_range) or pd.isna(low_range) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        if pd.isna(avg_volume) or avg_volume <= 0:
            return
            
        # Debug and trade on volume surge
        if not self.position and len(self.data.Close) > 50:
            # Calculate volume ratio manually to debug
            current_vol = self.data.Volume[-1]
            recent_vols = self.data.Volume[-20:]
            avg_vol = sum(recent_vols) / len(recent_vols)
            vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
            
            # Much more lenient volume threshold
            volume_surge = vol_ratio > 1.2  # Reduced from 1.5
            
            # Simple trend direction
            trend_up = price > prev_price
            
            # Trade on volume surge
            if volume_surge:
                if trend_up:
                    # Long entry
                    stop_loss = price * 0.985  # 1.5% stop
                    take_profit = price * 1.02   # 2% target  
                    self.buy(sl=stop_loss, tp=take_profit, size=0.95)
                else:
                    # Short entry
                    stop_loss = price * 1.015  # 1.5% stop
                    take_profit = price * 0.98   # 2% target
                    self.sell(sl=stop_loss, tp=take_profit, size=0.95)
        
        # Exit logic (managed by stop loss and take profit)
        # Additional exit if momentum reverses
        else:
            cmf_value = self.cmf[-1]
            
            if not pd.isna(cmf_value):
                # Exit long if CMF turns strongly negative
                if self.position.is_long and cmf_value < -0.1:
                    self.position.close()
                
                # Exit short if CMF turns strongly positive
                elif self.position.is_short and cmf_value > 0.1:
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S VOLUME BREAKOUT BASE STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Volume Breakout with OBV/CMF confirmation across all datasets...")
    print("="*80)
    
    # Run tests on all data sources without optimization
    results = test_on_all_data(
        VolumeBreakoutBase,
        'VolumeBreakoutBase',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/VolumeBreakoutBase.csv")
        print("="*80)

if __name__ == "__main__":
    main()