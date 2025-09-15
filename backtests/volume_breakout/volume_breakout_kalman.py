"""
Moon Dev's Volume Breakout Kalman Strategy
===========================================
Volume breakout with Kalman filter for smoother signal detection
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

class VolumeBreakoutKalman(Strategy):
    """
    Volume Breakout Strategy with Kalman Filter
    - Uses Kalman filter to smooth price and volume data
    - Better breakout detection with noise reduction
    - Maintains core volume surge and confirmation logic
    """
    
    # Strategy parameters
    consolidation_period = 20
    volume_ma_period = 20
    volume_surge_multiplier = 1.5
    atr_period = 14
    cmf_period = 20
    obv_ma_period = 10
    
    # Kalman filter parameters
    kalman_gain = 0.05  # Smoothing factor (0.01 = more smooth, 0.1 = less smooth)
    
    # Risk management
    profit_target_multiplier = 1.5
    
    def kalman_filter(self, data, gain=0.05):
        """Apply Kalman filter to smooth data"""
        filtered = np.zeros_like(data)
        filtered[0] = data[0] if not pd.isna(data[0]) else 0
        
        for i in range(1, len(data)):
            if pd.isna(data[i]):
                filtered[i] = filtered[i-1]
            else:
                filtered[i] = filtered[i-1] + gain * (data[i] - filtered[i-1])
        
        return filtered
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Apply Kalman filter to price data
        close_smooth = self.kalman_filter(close.values, self.kalman_gain)
        high_smooth = self.kalman_filter(high.values, self.kalman_gain)
        low_smooth = self.kalman_filter(low.values, self.kalman_gain)
        volume_smooth = self.kalman_filter(volume.values, self.kalman_gain * 2)  # More smoothing for volume
        
        self.close_kalman = self.I(lambda: close_smooth, name='CloseKalman')
        self.high_kalman = self.I(lambda: high_smooth, name='HighKalman')
        self.low_kalman = self.I(lambda: low_smooth, name='LowKalman')
        self.volume_kalman = self.I(lambda: volume_smooth, name='VolumeKalman')
        
        # ATR on smoothed data
        self.atr = self.I(ta.atr, pd.Series(high_smooth), pd.Series(low_smooth), pd.Series(close_smooth), self.atr_period)
        
        # Volume indicators on smoothed data
        self.volume_ma = self.I(ta.sma, pd.Series(volume_smooth), self.volume_ma_period)
        
        # OBV with Kalman smoothed price and volume
        obv_values = ta.obv(pd.Series(close_smooth), pd.Series(volume_smooth))
        self.obv = self.I(lambda: obv_values.values, name='OBV')
        self.obv_ma = self.I(ta.sma, obv_values, self.obv_ma_period)
        
        # CMF on smoothed data
        try:
            cmf_values = ta.cmf(pd.Series(high_smooth), pd.Series(low_smooth), 
                               pd.Series(close_smooth), pd.Series(volume_smooth), self.cmf_period)
            if cmf_values is not None and not cmf_values.empty:
                self.cmf = self.I(lambda: cmf_values.ffill().values, name='CMF')
            else:
                # Fallback: simple money flow calculation
                typical_price = (high_smooth + low_smooth + close_smooth) / 3
                raw_money_flow = typical_price * volume_smooth
                money_flow_sum = pd.Series(raw_money_flow).rolling(self.cmf_period).sum()
                volume_sum = pd.Series(volume_smooth).rolling(self.cmf_period).sum()
                cmf_simple = money_flow_sum / volume_sum
                self.cmf = self.I(lambda: cmf_simple.fillna(0).values, name='CMF')
        except:
            # Fallback: simple money flow calculation
            typical_price = (high_smooth + low_smooth + close_smooth) / 3
            raw_money_flow = typical_price * volume_smooth
            money_flow_sum = pd.Series(raw_money_flow).rolling(self.cmf_period).sum()
            volume_sum = pd.Series(volume_smooth).rolling(self.cmf_period).sum()
            cmf_simple = money_flow_sum / volume_sum
            self.cmf = self.I(lambda: cmf_simple.fillna(0).values, name='CMF')
        
        # Rolling high/low on Kalman filtered data
        # Calculate rolling high/low for consolidation detection
        rolling_high = pd.Series(high_smooth).rolling(self.consolidation_period).max()
        rolling_low = pd.Series(low_smooth).rolling(self.consolidation_period).min()
        rolling_std = pd.Series(close_smooth).rolling(self.consolidation_period).std()
        
        # Fill NaN values with the smoothed high/low/close values
        rolling_high = rolling_high.ffill().bfill()
        rolling_low = rolling_low.ffill().bfill()
        rolling_std = rolling_std.fillna(0)
        
        # Ensure no remaining NaNs by using the original smoothed data
        rolling_high = rolling_high.combine_first(pd.Series(high_smooth, index=rolling_high.index))
        rolling_low = rolling_low.combine_first(pd.Series(low_smooth, index=rolling_low.index))
        rolling_std = rolling_std.fillna(0)
        
        self.rolling_high = self.I(lambda: rolling_high.values, name='RollingHigh')
        self.rolling_low = self.I(lambda: rolling_low.values, name='RollingLow')
        self.price_std = self.I(lambda: rolling_std.values, name='PriceStd')        
        # Rate of change on Kalman filtered price for trend detection
        self.roc = self.I(lambda: ta.roc(pd.Series(close_smooth), 10).values, name='ROC')
        
    def is_consolidating(self):
        """Check if price is in consolidation phase using smoothed data"""
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
        
        # Tighter criteria with Kalman smoothing
        is_tight_range = range_height < (current_atr * 2.5)  # Slightly tighter
        is_low_volatility = std_percent < 0.015  # Lower threshold due to smoothing
        
        return is_tight_range and is_low_volatility
    
    def detect_volume_surge(self):
        """Check for volume surge using Kalman filtered volume"""
        if len(self.data.Volume) < self.volume_ma_period + 1:
            return False
            
        current_volume = self.volume_kalman[-1]
        avg_volume = self.volume_ma[-1]
        raw_volume = self.data.Volume[-1]  # Also check raw volume
        
        if pd.isna(avg_volume) or avg_volume <= 0:
            return False
            
        # Check both smoothed and raw volume for surge
        smoothed_surge = current_volume > (avg_volume * self.volume_surge_multiplier)
        raw_surge = raw_volume > (avg_volume * self.volume_surge_multiplier * 1.5)  # Higher threshold for raw
        
        return smoothed_surge or raw_surge
    
    def get_breakout_direction(self):
        """Determine breakout direction using Kalman filtered data"""
        if len(self.data.Close) < 2:
            return None
            
        price = self.close_kalman[-1]
        prev_price = self.close_kalman[-2]
        high_range = self.rolling_high[-1]
        low_range = self.rolling_low[-1]
        
        # Use raw price for actual breakout detection
        raw_price = self.data.Close[-1]
        raw_prev = self.data.Close[-2]
        
        obv_current = self.obv[-1]
        obv_ma_current = self.obv_ma[-1]
        cmf_value = self.cmf[-1]
        roc_value = self.roc[-1] if len(self.roc) > 0 else 0
        
        if pd.isna(high_range) or pd.isna(low_range) or pd.isna(obv_current) or pd.isna(obv_ma_current) or pd.isna(cmf_value):
            return None
        
        # Breakout on smoothed data
        broke_above = prev_price <= high_range and price > high_range
        broke_below = prev_price >= low_range and price < low_range
        
        # Also check raw price breakout
        raw_broke_above = raw_prev <= high_range and raw_price > high_range
        raw_broke_below = raw_prev >= low_range and raw_price < low_range
        
        # Confirmation from indicators
        obv_bullish = obv_current > obv_ma_current
        obv_bearish = obv_current < obv_ma_current
        cmf_bullish = cmf_value > 0.05  # Slightly higher threshold
        cmf_bearish = cmf_value < -0.05
        roc_bullish = roc_value > 0 if not pd.isna(roc_value) else False
        roc_bearish = roc_value < 0 if not pd.isna(roc_value) else False
        
        # Long breakout with Kalman confirmation
        if (broke_above or raw_broke_above) and obv_bullish and cmf_bullish and roc_bullish:
            return 'long'
        
        # Short breakout with Kalman confirmation
        elif (broke_below or raw_broke_below) and obv_bearish and cmf_bearish and roc_bearish:
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
            if self.is_consolidating():
                if self.detect_volume_surge():
                    direction = self.get_breakout_direction()
                    
                    if direction == 'long':
                        consolidation_range = high_range - low_range
                        stop_loss = low_range - (atr_value * 0.5)  # Slightly wider stop with Kalman
                        take_profit = price + (consolidation_range * self.profit_target_multiplier)
                        
                        self.buy(sl=stop_loss, tp=take_profit, size=0.95)
                    
                    elif direction == 'short':
                        consolidation_range = high_range - low_range
                        stop_loss = high_range + (atr_value * 0.5)
                        take_profit = price - (consolidation_range * self.profit_target_multiplier)
                        
                        self.sell(sl=stop_loss, tp=take_profit, size=0.95)
        
        # Exit logic
        else:
            cmf_value = self.cmf[-1]
            roc_value = self.roc[-1] if len(self.roc) > 0 else 0
            
            if not pd.isna(cmf_value) and not pd.isna(roc_value):
                # Exit long if momentum reverses
                if self.position.is_long and (cmf_value < -0.1 or roc_value < -5):
                    self.position.close()
                
                # Exit short if momentum reverses
                elif self.position.is_short and (cmf_value > 0.1 or roc_value > 5):
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S VOLUME BREAKOUT KALMAN STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Volume Breakout with Kalman filtering across all datasets...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        VolumeBreakoutKalman,
        'VolumeBreakoutKalman',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/VolumeBreakoutKalman.csv")
        print("="*80)

if __name__ == "__main__":
    main()