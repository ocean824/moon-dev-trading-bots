"""
Moon Dev's Momentum Cross Impulse MACD Kalman Strategy
=======================================================
Impulse MACD with Kalman Filter for smoother momentum signals
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class MomentumCrossImpulseMACDKalmanStrategy(Strategy):
    """
    Impulse MACD with Kalman Filter
    - Same as impulse MACD strategy but with Kalman filtered prices
    - Should provide smoother MACD signals with less noise
    - Better trend identification with cleaner impulse signals
    """
    
    # MACD parameters
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    
    # Impulse EMA period
    impulse_ema_period = 13
    
    # Kalman filter parameters
    kalman_gain = 0.11  # Moderate gain for MACD balance
    
    # Risk management
    atr_period = 14
    atr_sl_multiplier = 2.0
    trailing_stop_pct = 0.025
    
    # Volume confirmation
    volume_period = 20
    volume_multiplier = 1.2
    
    # Momentum thresholds
    histogram_accel_threshold = 0.08  # Lower threshold for Kalman smoothed data
    
    def kalman_filter(self, data, gain=0.11):
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
        
        # Apply Kalman filter to close price
        close_filtered = self.kalman_filter(close.values, self.kalman_gain)
        close_kalman = pd.Series(close_filtered, index=close.index)
        
        # Calculate MACD on filtered prices
        macd_result = ta.macd(close_kalman,
                              fast=self.macd_fast,
                              slow=self.macd_slow,
                              signal=self.macd_signal)
        
        # Extract MACD components
        macd_line = macd_result[f'MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}']
        signal_line = macd_result[f'MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}']
        histogram = macd_result[f'MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}']
        
        # Apply additional Kalman smoothing to MACD components
        macd_smoothed = self.kalman_filter(macd_line.values, gain=0.15)
        signal_smoothed = self.kalman_filter(signal_line.values, gain=0.15)
        histogram_smoothed = histogram.values  # Keep histogram unsmoothed for sensitivity
        
        self.macd = self.I(lambda: macd_smoothed, name='MACD_Kalman')
        self.signal = self.I(lambda: signal_smoothed, name='Signal_Kalman')
        self.histogram = self.I(lambda: histogram_smoothed, name='Histogram')
        
        # Previous values for crossover detection
        macd_prev = np.roll(macd_smoothed, 1)
        signal_prev = np.roll(signal_smoothed, 1)
        histogram_prev = np.roll(histogram_smoothed, 1)
        macd_prev[0] = macd_smoothed[0]
        signal_prev[0] = signal_smoothed[0]
        histogram_prev[0] = histogram_smoothed[0]
        
        self.macd_prev = self.I(lambda: macd_prev, name='MACD_Prev')
        self.signal_prev = self.I(lambda: signal_prev, name='Signal_Prev')
        self.histogram_prev = self.I(lambda: histogram_prev, name='Histogram_Prev')
        
        # Calculate Impulse EMA on Kalman filtered prices
        impulse_ema = ta.ema(close_kalman, self.impulse_ema_period)
        impulse_ema_prev = impulse_ema.shift(1)
        
        self.impulse_ema = self.I(lambda: impulse_ema.values, name='Impulse_EMA_Kalman')
        self.impulse_ema_prev = self.I(lambda: impulse_ema_prev.values, name='Impulse_EMA_Prev')
        
        # Impulse system colors with Kalman smoothed data
        ema_rising = impulse_ema > impulse_ema_prev
        ema_falling = impulse_ema < impulse_ema_prev
        hist_rising = pd.Series(histogram_smoothed) > pd.Series(histogram_prev)
        hist_falling = pd.Series(histogram_smoothed) < pd.Series(histogram_prev)
        
        impulse_green = ema_rising & hist_rising
        impulse_red = ema_falling & hist_falling
        impulse_blue = ~(impulse_green | impulse_red)
        
        self.impulse_green = self.I(lambda: impulse_green.values, name='Impulse_Green')
        self.impulse_red = self.I(lambda: impulse_red.values, name='Impulse_Red')
        self.impulse_blue = self.I(lambda: impulse_blue.values, name='Impulse_Blue')
        
        # Track impulse state changes
        self.last_impulse_color = 'blue'
        self.impulse_bars = 0
        
        # Volume average for confirmation
        volume_avg = ta.sma(volume, self.volume_period)
        self.volume_avg = self.I(lambda: volume_avg.values, name='Volume_Avg')
        
        # Volume spike detection
        volume_spike = volume / volume_avg > self.volume_multiplier
        self.volume_spike = self.I(lambda: volume_spike.values, name='Volume_Spike')
        
        # ATR for stops (use raw data for actual volatility)
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # Track highest/lowest prices for trailing stops
        self.highest_price = 0
        self.lowest_price = float('inf')
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.macd_slow, self.volume_period, self.atr_period, self.impulse_ema_period) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        macd_curr = self.macd[-1]
        signal_curr = self.signal[-1]
        histogram_curr = self.histogram[-1]
        
        macd_prev = self.macd_prev[-1]
        signal_prev = self.signal_prev[-1]
        histogram_prev = self.histogram_prev[-1]
        
        impulse_green = self.impulse_green[-1] if not pd.isna(self.impulse_green[-1]) else False
        impulse_red = self.impulse_red[-1] if not pd.isna(self.impulse_red[-1]) else False
        impulse_blue = self.impulse_blue[-1] if not pd.isna(self.impulse_blue[-1]) else False
        
        volume_confirmed = self.volume_spike[-1] if not pd.isna(self.volume_spike[-1]) else False
        atr_value = self.atr[-1]
        
        # Check for valid values
        if pd.isna(macd_curr) or pd.isna(signal_curr) or pd.isna(histogram_curr) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Track impulse state changes
        current_impulse = 'green' if impulse_green else ('red' if impulse_red else 'blue')
        if current_impulse != self.last_impulse_color:
            self.last_impulse_color = current_impulse
            self.impulse_bars = 0
        else:
            self.impulse_bars += 1
        
        # MACD crossovers (cleaner with Kalman)
        macd_cross_up = (macd_prev <= signal_prev) and (macd_curr > signal_curr)
        macd_cross_down = (macd_prev >= signal_prev) and (macd_curr < signal_curr)
        
        # Histogram momentum (acceleration) - adjusted for Kalman smoothed data
        if histogram_prev != 0:
            histogram_accel = abs((histogram_curr - histogram_prev) / histogram_prev)
        else:
            histogram_accel = 0
        
        strong_bullish_momentum = histogram_curr > 0 and histogram_accel > self.histogram_accel_threshold
        strong_bearish_momentum = histogram_curr < 0 and histogram_accel > self.histogram_accel_threshold
        
        # Zero line crossovers
        macd_above_zero = macd_curr > 0
        macd_below_zero = macd_curr < 0
        macd_cross_zero_up = (macd_prev <= 0) and (macd_curr > 0)
        macd_cross_zero_down = (macd_prev >= 0) and (macd_curr < 0)
        
        # Histogram divergence from zero
        histogram_expanding = abs(histogram_curr) > abs(histogram_prev)
        histogram_contracting = abs(histogram_curr) < abs(histogram_prev)
        
        # Impulse confirmation (require impulse to hold for at least 2 bars with Kalman)
        impulse_confirmed = self.impulse_bars >= 2
        
        # Long signal conditions (more stringent with Kalman filter)
        long_signal = (
            (macd_cross_up and impulse_green and impulse_confirmed) or
            (impulse_green and strong_bullish_momentum and histogram_expanding and impulse_confirmed) or
            (macd_cross_zero_up and (impulse_green or impulse_blue) and volume_confirmed)
        )
        
        # Short signal conditions
        short_signal = (
            (macd_cross_down and impulse_red and impulse_confirmed) or
            (impulse_red and strong_bearish_momentum and histogram_expanding and impulse_confirmed) or
            (macd_cross_zero_down and (impulse_red or impulse_blue) and volume_confirmed)
        )
        
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
        
        # Implement trailing stops and momentum exits
        if self.position:
            if self.position.is_long:
                # Update highest price
                if price > self.highest_price:
                    self.highest_price = price
                
                # Check trailing stop
                trailing_stop = self.highest_price * (1 - self.trailing_stop_pct)
                if price < trailing_stop:
                    self.position.close()
                
                # Exit on impulse red (strong bearish signal with Kalman)
                if impulse_red and impulse_confirmed:
                    self.position.close()
                
                # Exit on MACD crossover down with negative histogram
                if macd_cross_down and histogram_curr < 0:
                    self.position.close()
                
                # Exit if histogram contracts significantly (Kalman makes this more reliable)
                if histogram_prev > 0 and histogram_curr > 0:
                    if histogram_curr < histogram_prev * 0.4:  # 60% contraction
                        self.position.close()
            
            elif self.position.is_short:
                # Update lowest price
                if price < self.lowest_price:
                    self.lowest_price = price
                
                # Check trailing stop
                trailing_stop = self.lowest_price * (1 + self.trailing_stop_pct)
                if price > trailing_stop:
                    self.position.close()
                
                # Exit on impulse green (strong bullish signal with Kalman)
                if impulse_green and impulse_confirmed:
                    self.position.close()
                
                # Exit on MACD crossover up with positive histogram
                if macd_cross_up and histogram_curr > 0:
                    self.position.close()
                
                # Exit if histogram contracts significantly (Kalman makes this more reliable)
                if histogram_prev < 0 and histogram_curr < 0:
                    if abs(histogram_curr) < abs(histogram_prev) * 0.4:  # 60% contraction
                        self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S MOMENTUM CROSS IMPULSE MACD KALMAN STRATEGY")
    print("="*80)
    print("Testing Impulse MACD with Kalman Filter across all datasets...")
    print("="*80)
    
    # Run tests on all data sources without optimization
    results = test_on_all_data(
        MomentumCrossImpulseMACDKalmanStrategy,
        'MomentumCrossImpulseMACDKalman',
        optimize=False,  # No optimization as requested
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/MomentumCrossImpulseMACDKalman.csv")
        print("="*80)

if __name__ == "__main__":
    main()