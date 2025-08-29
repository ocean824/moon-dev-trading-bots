"""
Moon Dev's Momentum Cross Triple EMA Kalman Strategy
=====================================================
Triple EMA with Kalman Filter for smoother crossover signals
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class MomentumCrossTripleEMAKalmanStrategy(Strategy):
    """
    Triple EMA with Kalman Filter
    - Same as triple EMA strategy but apply Kalman filter to smooth price before calculating EMAs
    - Should reduce whipsaws in crossover signals
    - Provides cleaner trend identification
    """
    
    # EMA parameters
    ema_fast = 50
    ema_medium = 100
    ema_slow = 200
    
    # Kalman filter parameters
    kalman_gain = 0.1  # Lower gain for smoother price action
    
    # Risk management
    atr_period = 14
    atr_sl_multiplier = 2.0
    trailing_stop_pct = 0.025
    
    # Volume confirmation
    volume_period = 20
    volume_multiplier = 1.2
    
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
        volume = pd.Series(self.data.Volume)
        
        # Apply Kalman filter to close price
        close_filtered = self.kalman_filter(close.values, self.kalman_gain)
        close_kalman = pd.Series(close_filtered, index=close.index)
        
        # Calculate EMAs on filtered prices
        ema_50 = ta.ema(close_kalman, self.ema_fast)
        ema_100 = ta.ema(close_kalman, self.ema_medium)
        ema_200 = ta.ema(close_kalman, self.ema_slow)
        
        self.ema_50 = self.I(lambda: ema_50.values, name='EMA_50_Kalman')
        self.ema_100 = self.I(lambda: ema_100.values, name='EMA_100_Kalman')
        self.ema_200 = self.I(lambda: ema_200.values, name='EMA_200_Kalman')
        
        # Previous values for crossover detection
        ema_50_prev = ema_50.shift(1)
        ema_100_prev = ema_100.shift(1)
        ema_200_prev = ema_200.shift(1)
        
        self.ema_50_prev = self.I(lambda: ema_50_prev.values, name='EMA_50_Prev')
        self.ema_100_prev = self.I(lambda: ema_100_prev.values, name='EMA_100_Prev')
        self.ema_200_prev = self.I(lambda: ema_200_prev.values, name='EMA_200_Prev')
        
        # Apply additional smoothing to crossover signals
        # Calculate crossover strength (distance between EMAs)
        cross_strength_fast_medium = (ema_50 - ema_100) / ema_100 * 100
        cross_strength_medium_slow = (ema_100 - ema_200) / ema_200 * 100
        
        self.cross_strength_fm = self.I(lambda: cross_strength_fast_medium.values, name='Cross_Strength_FM')
        self.cross_strength_ms = self.I(lambda: cross_strength_medium_slow.values, name='Cross_Strength_MS')
        
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
        
        # Track crossover confirmation bars
        self.crossover_confirm_bars = 0
        self.last_crossover_type = None  # 'bullish' or 'bearish'
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < self.ema_slow + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        ema_50_curr = self.ema_50[-1]
        ema_100_curr = self.ema_100[-1]
        ema_200_curr = self.ema_200[-1]
        
        ema_50_prev = self.ema_50_prev[-1]
        ema_100_prev = self.ema_100_prev[-1]
        ema_200_prev = self.ema_200_prev[-1]
        
        cross_strength_fm = self.cross_strength_fm[-1]
        cross_strength_ms = self.cross_strength_ms[-1]
        
        volume_confirmed = self.volume_spike[-1] if not pd.isna(self.volume_spike[-1]) else False
        atr_value = self.atr[-1]
        
        # Check for valid values
        if pd.isna(ema_50_curr) or pd.isna(ema_100_curr) or pd.isna(ema_200_curr) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Primary crossover: 50 EMA crossing 100 EMA
        fast_cross_medium_up = (ema_50_prev <= ema_100_prev) and (ema_50_curr > ema_100_curr)
        fast_cross_medium_down = (ema_50_prev >= ema_100_prev) and (ema_50_curr < ema_100_curr)
        
        # Secondary crossover: 100 EMA crossing 200 EMA (trend confirmation)
        medium_cross_slow_up = (ema_100_prev <= ema_200_prev) and (ema_100_curr > ema_200_curr)
        medium_cross_slow_down = (ema_100_prev >= ema_200_prev) and (ema_100_curr < ema_200_curr)
        
        # Trend alignment: All EMAs in order
        bullish_alignment = (ema_50_curr > ema_100_curr > ema_200_curr)
        bearish_alignment = (ema_50_curr < ema_100_curr < ema_200_curr)
        
        # Crossover strength confirmation (Kalman filtered signals should be stronger)
        strong_bullish_cross = cross_strength_fm > 0.5  # 0.5% separation
        strong_bearish_cross = cross_strength_fm < -0.5
        
        # Update crossover confirmation
        if fast_cross_medium_up:
            self.last_crossover_type = 'bullish'
            self.crossover_confirm_bars = 0
        elif fast_cross_medium_down:
            self.last_crossover_type = 'bearish'
            self.crossover_confirm_bars = 0
        else:
            self.crossover_confirm_bars += 1
        
        # Require crossover to hold for 2 bars (reduces false signals with Kalman)
        crossover_confirmed = self.crossover_confirm_bars >= 2
        
        # Long signal conditions (more stringent with Kalman filter)
        long_signal = (
            self.last_crossover_type == 'bullish' and
            crossover_confirmed and
            strong_bullish_cross and
            (bullish_alignment or ema_100_curr > ema_200_curr) and
            (volume_confirmed or medium_cross_slow_up or cross_strength_ms > 0.3)
        )
        
        # Short signal conditions
        short_signal = (
            self.last_crossover_type == 'bearish' and
            crossover_confirmed and
            strong_bearish_cross and
            (bearish_alignment or ema_100_curr < ema_200_curr) and
            (volume_confirmed or medium_cross_slow_down or cross_strength_ms < -0.3)
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
                
                # Exit if crossover strength weakens significantly
                if cross_strength_fm < -0.3:  # Negative crossover strength
                    self.position.close()
                
                # Exit if price drops below 100 EMA with bearish momentum
                if price < ema_100_curr and ema_50_curr < ema_100_curr:
                    self.position.close()
            
            elif self.position.is_short:
                # Update lowest price
                if price < self.lowest_price:
                    self.lowest_price = price
                
                # Check trailing stop
                trailing_stop = self.lowest_price * (1 + self.trailing_stop_pct)
                if price > trailing_stop:
                    self.position.close()
                
                # Exit if crossover strength weakens significantly
                if cross_strength_fm > 0.3:  # Positive crossover strength
                    self.position.close()
                
                # Exit if price rises above 100 EMA with bullish momentum
                if price > ema_100_curr and ema_50_curr > ema_100_curr:
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S MOMENTUM CROSS TRIPLE EMA KALMAN STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Triple EMA with Kalman Filter across all datasets...")
    print("="*80)
    
    # Run tests on all data sources without optimization
    results = test_on_all_data(
        MomentumCrossTripleEMAKalmanStrategy,
        'MomentumCrossTripleEMAKalman',
        optimize=False,  # No optimization as requested
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/MomentumCrossTripleEMAKalman.csv")
        print("="*80)

if __name__ == "__main__":
    main()