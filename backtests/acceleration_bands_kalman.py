"""
Moon Dev's Acceleration Bands Kalman Strategy
==============================================
Acceleration bands with Kalman filter for noise reduction
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class AccelerationBandsKalmanStrategy(Strategy):
    """
    Acceleration Bands with Kalman Filter Strategy
    - Same as acceleration_bands but apply Kalman filter to smooth price data
    - This should reduce false signals from the bands
    - Uses filtered price for band calculation and signals
    """
    
    # Band parameters
    ma_period = 20
    atr_period = 20
    band_multiplier = 2.0  # ATR multiplier for band width
    
    # Kalman filter parameters
    kalman_gain = 0.1  # Lower = more smoothing, higher = less smoothing
    
    # Risk management
    atr_sl_multiplier = 1.5  # Stop loss ATR multiplier
    atr_tp_multiplier = 3.0  # Take profit ATR multiplier
    
    # Confirmation parameters
    min_breakout_strength = 0.001  # Minimum breakout percentage
    
    def kalman_filter(self, data, gain=0.1):
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
        
        # Apply Kalman filter to price data
        close_filtered = self.kalman_filter(close.values, self.kalman_gain)
        high_filtered = self.kalman_filter(high.values, self.kalman_gain)
        low_filtered = self.kalman_filter(low.values, self.kalman_gain)
        
        # Convert back to series
        close_kalman = pd.Series(close_filtered, index=close.index)
        high_kalman = pd.Series(high_filtered, index=high.index)
        low_kalman = pd.Series(low_filtered, index=low.index)
        
        # Store filtered close price
        self.close_kalman = self.I(lambda: close_kalman.values, name='CloseKalman')
        
        # Calculate MA on filtered data (middle band)
        ma_kalman = ta.sma(close_kalman, self.ma_period)
        self.ma = self.I(lambda: ma_kalman.values, name='MA_Kalman')
        
        # Calculate ATR on filtered data for band width
        atr_kalman = ta.atr(high_kalman, low_kalman, close_kalman, self.atr_period)
        self.atr = self.I(lambda: atr_kalman.values, name='ATR_Kalman')
        
        # Calculate acceleration bands on filtered data
        upper_band = ma_kalman + (atr_kalman * self.band_multiplier)
        lower_band = ma_kalman - (atr_kalman * self.band_multiplier)
        
        self.upper_band = self.I(lambda: upper_band.values, name='UpperBand')
        self.lower_band = self.I(lambda: lower_band.values, name='LowerBand')
        
        # Track breakout strength using filtered price
        breakout_up = (close_kalman - upper_band) / upper_band
        breakout_down = (lower_band - close_kalman) / lower_band
        
        self.breakout_up = self.I(lambda: breakout_up.values, name='BreakoutUp')
        self.breakout_down = self.I(lambda: breakout_down.values, name='BreakoutDown')
        
        # Also store raw ATR for stop losses (use actual volatility, not filtered)
        self.atr_raw = self.I(ta.atr, high, low, close, self.atr_period)
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.ma_period, self.atr_period) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]  # Use actual price for execution
        price_filtered = self.close_kalman[-1]  # Use filtered price for signals
        upper = self.upper_band[-1]
        lower = self.lower_band[-1]
        atr_value = self.atr_raw[-1]  # Use raw ATR for stops
        
        # Check for valid values
        if pd.isna(upper) or pd.isna(lower) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Get breakout strength
        breakout_up_strength = self.breakout_up[-1] if not pd.isna(self.breakout_up[-1]) else 0
        breakout_down_strength = self.breakout_down[-1] if not pd.isna(self.breakout_down[-1]) else 0
        
        # Long signal: Filtered price breaks above upper band with strength
        long_signal = (price_filtered > upper) and (breakout_up_strength > self.min_breakout_strength)
        
        # Short signal: Filtered price breaks below lower band with strength
        short_signal = (price_filtered < lower) and (breakout_down_strength > self.min_breakout_strength)
        
        # Execute trades
        if long_signal:
            if self.position.is_short:
                self.position.close()
            if not self.position:
                # Stop loss within the bands (at MA level)
                stop_loss = self.ma[-1] if not pd.isna(self.ma[-1]) else price - (atr_value * self.atr_sl_multiplier)
                # Take profit based on ATR
                take_profit = price + (atr_value * self.atr_tp_multiplier)
                self.buy(sl=stop_loss, tp=take_profit)
        
        elif short_signal:
            if self.position.is_long:
                self.position.close()
            if not self.position:
                # Stop loss within the bands (at MA level)
                stop_loss = self.ma[-1] if not pd.isna(self.ma[-1]) else price + (atr_value * self.atr_sl_multiplier)
                # Take profit based on ATR
                take_profit = price - (atr_value * self.atr_tp_multiplier)
                self.sell(sl=stop_loss, tp=take_profit)
        
        # Exit if filtered price returns within bands
        elif self.position:
            if self.position.is_long and price_filtered < upper:
                self.position.close()
            elif self.position.is_short and price_filtered > lower:
                self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S ACCELERATION BANDS KALMAN STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Acceleration Bands with Kalman Filter across all datasets...")
    print("="*80)
    
    # Run tests on all data sources without optimization
    results = test_on_all_data(
        AccelerationBandsKalmanStrategy,
        'AccelerationBandsKalman',
        optimize=False,  # No optimization as requested
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/AccelerationBandsKalman.csv")
        print("="*80)

if __name__ == "__main__":
    main()