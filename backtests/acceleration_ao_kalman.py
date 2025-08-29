"""
Moon Dev's Acceleration AO Kalman Strategy
===========================================
Awesome Oscillator with Kalman filter for smoother signals
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class AccelerationAOKalmanStrategy(Strategy):
    """
    AO with Kalman Filter Strategy
    - Same as acceleration_ao but use Kalman filtered prices
    - Should provide smoother momentum signals
    - Reduces noise in AO calculations
    """
    
    # AO parameters
    fast_period = 5
    slow_period = 34
    
    # Kalman filter parameters
    kalman_gain = 0.15  # Slightly higher gain for AO to maintain responsiveness
    
    # Volume parameters
    volume_period = 20
    volume_multiplier = 1.2  # Volume must be 20% above average
    
    # Risk management
    atr_period = 14
    atr_sl_multiplier = 2.0
    trailing_stop_pct = 0.02  # 2% trailing stop
    
    def kalman_filter(self, data, gain=0.15):
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
        
        # Apply Kalman filter to high and low for median price calculation
        high_filtered = self.kalman_filter(high.values, self.kalman_gain)
        low_filtered = self.kalman_filter(low.values, self.kalman_gain)
        
        # Convert back to series
        high_kalman = pd.Series(high_filtered, index=high.index)
        low_kalman = pd.Series(low_filtered, index=low.index)
        
        # Calculate Awesome Oscillator on filtered data
        # AO = SMA(median price, 5) - SMA(median price, 34)
        median_price_kalman = (high_kalman + low_kalman) / 2
        
        fast_sma = ta.sma(median_price_kalman, self.fast_period)
        slow_sma = ta.sma(median_price_kalman, self.slow_period)
        ao_kalman = fast_sma - slow_sma
        
        self.ao = self.I(lambda: ao_kalman.values, name='AO_Kalman')
        
        # Previous AO for crossover detection
        ao_prev = ao_kalman.shift(1)
        self.ao_prev = self.I(lambda: ao_prev.values, name='AO_Prev')
        
        # Apply additional smoothing to AO itself for cleaner signals
        ao_smoothed = self.kalman_filter(ao_kalman.values, gain=0.2)
        self.ao_smooth = self.I(lambda: ao_smoothed, name='AO_Smooth')
        
        # Volume average for confirmation
        self.volume_avg = self.I(ta.sma, volume, self.volume_period)
        
        # Volume spike detection
        volume_avg_series = ta.sma(volume, self.volume_period)
        volume_spike = volume / volume_avg_series > self.volume_multiplier
        self.volume_spike = self.I(lambda: volume_spike.values, name='VolumeSpike')
        
        # ATR for stops (use raw data for actual volatility)
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # Track highest/lowest prices for trailing stops
        self.highest_price = 0
        self.lowest_price = float('inf')
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.slow_period, self.volume_period, self.atr_period) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        ao_current = self.ao[-1]
        ao_previous = self.ao_prev[-1]
        ao_smooth_current = self.ao_smooth[-1]
        ao_smooth_prev = self.ao_smooth[-2] if len(self.ao_smooth) > 1 else ao_smooth_current
        volume_confirmed = self.volume_spike[-1] if not pd.isna(self.volume_spike[-1]) else False
        atr_value = self.atr[-1]
        
        # Check for valid values
        if pd.isna(ao_current) or pd.isna(ao_previous) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Use smoothed AO for cleaner crossover detection
        ao_cross_above_zero = (ao_smooth_prev <= 0) and (ao_smooth_current > 0)
        ao_cross_below_zero = (ao_smooth_prev >= 0) and (ao_smooth_current < 0)
        
        # Also look for momentum acceleration in smoothed AO
        ao_accel = ao_smooth_current - ao_smooth_prev
        ao_momentum_up = (ao_smooth_current > 0) and (ao_accel > abs(ao_smooth_prev) * 0.05)
        ao_momentum_down = (ao_smooth_current < 0) and (ao_accel < -abs(ao_smooth_prev) * 0.05)
        
        # Additional confirmation: AO trend consistency
        ao_trend_up = all(self.ao_smooth[i] > self.ao_smooth[i-1] for i in range(-3, 0) if i >= -len(self.ao_smooth))
        ao_trend_down = all(self.ao_smooth[i] < self.ao_smooth[i-1] for i in range(-3, 0) if i >= -len(self.ao_smooth))
        
        # Long signal: AO crosses above zero or strong upward momentum
        long_signal = ((ao_cross_above_zero and volume_confirmed) or 
                      (ao_momentum_up and ao_trend_up))
        
        # Short signal: AO crosses below zero or strong downward momentum
        short_signal = ((ao_cross_below_zero and volume_confirmed) or 
                       (ao_momentum_down and ao_trend_down))
        
        # Execute trades
        if long_signal:
            if self.position.is_short:
                self.position.close()
            if not self.position:
                stop_loss = price - (atr_value * self.atr_sl_multiplier)
                self.buy(sl=stop_loss)
                self.highest_price = price
        
        elif short_signal:
            if self.position.is_long:
                self.position.close()
            if not self.position:
                stop_loss = price + (atr_value * self.atr_sl_multiplier)
                self.sell(sl=stop_loss)
                self.lowest_price = price
        
        # Implement trailing stops
        if self.position:
            if self.position.is_long:
                # Update highest price
                if price > self.highest_price:
                    self.highest_price = price
                
                # Check trailing stop
                trailing_stop = self.highest_price * (1 - self.trailing_stop_pct)
                if price < trailing_stop:
                    self.position.close()
                
                # Exit if smoothed AO turns negative with momentum
                if ao_smooth_current < 0 and ao_accel < 0:
                    self.position.close()
            
            elif self.position.is_short:
                # Update lowest price
                if price < self.lowest_price:
                    self.lowest_price = price
                
                # Check trailing stop
                trailing_stop = self.lowest_price * (1 + self.trailing_stop_pct)
                if price > trailing_stop:
                    self.position.close()
                
                # Exit if smoothed AO turns positive with momentum
                if ao_smooth_current > 0 and ao_accel > 0:
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S ACCELERATION AO KALMAN STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing AO with Kalman Filter across all datasets...")
    print("="*80)
    
    # Run tests on all data sources without optimization
    results = test_on_all_data(
        AccelerationAOKalmanStrategy,
        'AccelerationAOKalman',
        optimize=False,  # No optimization as requested
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/AccelerationAOKalman.csv")
        print("="*80)

if __name__ == "__main__":
    main()