"""
🌙 Moon Dev's Camarilla Pivot Strategy - Kalman Filtered
=========================================================
Uses Kalman filter to smooth OHLC before calculating pivots
Tests across all datasets with multi-data framework
"""

from backtesting import Backtest, Strategy
import pandas as pd
import talib
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class KalmanFilter:
    """Simple Kalman filter implementation for price smoothing"""
    def __init__(self, process_variance=1e-5, measurement_variance=0.1):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.posteri_estimate = None
        self.posteri_error_estimate = 1.0
    
    def update(self, measurement):
        if self.posteri_estimate is None:
            self.posteri_estimate = measurement
            return measurement
        
        # Prediction
        priori_estimate = self.posteri_estimate
        priori_error_estimate = self.posteri_error_estimate + self.process_variance
        
        # Update
        blending_factor = priori_error_estimate / (priori_error_estimate + self.measurement_variance)
        self.posteri_estimate = priori_estimate + blending_factor * (measurement - priori_estimate)
        self.posteri_error_estimate = (1 - blending_factor) * priori_error_estimate
        
        return self.posteri_estimate

def apply_kalman_filter(series, process_variance=1e-5, measurement_variance=0.1):
    """Apply Kalman filter to a pandas Series"""
    kf = KalmanFilter(process_variance, measurement_variance)
    filtered_values = []
    for value in series:
        if pd.notna(value):
            filtered_values.append(kf.update(value))
        else:
            filtered_values.append(np.nan)
    return pd.Series(filtered_values, index=series.index)

class CamarillaPivotKalman(Strategy):
    """
    Camarilla Pivot with Kalman Filter Strategy
    - Apply Kalman filter to smooth OHLC prices before calculating pivots
    - Reduces false signals from noisy data
    - Use standard Camarilla trading rules with smoothed levels
    - Add momentum confirmation from Kalman filtered price trend
    """
    
    # Parameters
    kalman_process_var = 1e-5  # Lower = more smoothing
    kalman_measure_var = 0.1   # Higher = more smoothing
    atr_period = 14
    atr_multiplier_sl = 1.5
    volume_period = 20
    volume_threshold = 1.15
    momentum_lookback = 5  # Bars to check Kalman trend
    
    def init(self):
        # Convert to pandas Series for calculations
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Apply Kalman filter to OHLC data
        close_filtered = apply_kalman_filter(close, self.kalman_process_var, self.kalman_measure_var)
        high_filtered = apply_kalman_filter(high, self.kalman_process_var, self.kalman_measure_var)
        low_filtered = apply_kalman_filter(low, self.kalman_process_var, self.kalman_measure_var)
        
        # Store filtered prices
        self.close_kalman = self.I(lambda: close_filtered.values, name='Close_Kalman')
        self.high_kalman = self.I(lambda: high_filtered.values, name='High_Kalman')
        self.low_kalman = self.I(lambda: low_filtered.values, name='Low_Kalman')
        
        # Calculate daily OHLC for pivot calculation using filtered data
        pivot_period = 24  # Assume hourly data, use 24 hours for daily pivot
        
        # Calculate previous period's high, low, close for pivots (using Kalman filtered)
        prev_high = high_filtered.rolling(window=pivot_period).max().shift(1)
        prev_low = low_filtered.rolling(window=pivot_period).min().shift(1)
        prev_close = close_filtered.shift(pivot_period)
        
        # Calculate Camarilla Pivot levels with smoothed data
        pivot_range = prev_high - prev_low
        
        # Resistance levels (smoothed)
        r4 = prev_close + (pivot_range * 1.1 / 2)
        r3 = prev_close + (pivot_range * 1.1 / 4)
        r2 = prev_close + (pivot_range * 1.1 / 6)
        r1 = prev_close + (pivot_range * 1.1 / 12)
        
        # Support levels (smoothed)
        s1 = prev_close - (pivot_range * 1.1 / 12)
        s2 = prev_close - (pivot_range * 1.1 / 6)
        s3 = prev_close - (pivot_range * 1.1 / 4)
        s4 = prev_close - (pivot_range * 1.1 / 2)
        
        # Store Kalman-filtered pivot levels
        self.r4 = self.I(lambda: r4.values, name='R4_Kalman')
        self.r3 = self.I(lambda: r3.values, name='R3_Kalman')
        self.r2 = self.I(lambda: r2.values, name='R2_Kalman')
        self.r1 = self.I(lambda: r1.values, name='R1_Kalman')
        self.s1 = self.I(lambda: s1.values, name='S1_Kalman')
        self.s2 = self.I(lambda: s2.values, name='S2_Kalman')
        self.s3 = self.I(lambda: s3.values, name='S3_Kalman')
        self.s4 = self.I(lambda: s4.values, name='S4_Kalman')
        
        # Calculate Kalman trend (momentum from filtered price)
        kalman_momentum = close_filtered.diff(self.momentum_lookback) / close_filtered.shift(self.momentum_lookback) * 100
        self.kalman_trend = self.I(lambda: kalman_momentum.values, name='Kalman_Trend')
        
        # ATR for stop loss (use original prices for volatility)
        self.atr = self.I(talib.ATR, high, low, close, self.atr_period)
        
        # Volume SMA for confirmation
        self.volume_sma = self.I(talib.SMA, volume, self.volume_period)
        
        # Track signal quality
        self.signal_strength = 0
        
    def next(self):
        # Skip if not enough data
        if len(self.data) < 30:
            return
            
        # Get current values (use actual prices for execution)
        price = self.data.Close[-1]
        high = self.data.High[-1]
        low = self.data.Low[-1]
        volume = self.data.Volume[-1]
        
        # Get Kalman filtered values for analysis
        close_kalman = self.close_kalman[-1]
        high_kalman = self.high_kalman[-1]
        low_kalman = self.low_kalman[-1]
        
        # Get Kalman-smoothed pivot levels
        r4 = self.r4[-1]
        r3 = self.r3[-1]
        r2 = self.r2[-1]
        r1 = self.r1[-1]
        s1 = self.s1[-1]
        s2 = self.s2[-1]
        s3 = self.s3[-1]
        s4 = self.s4[-1]
        
        # Get indicators
        atr = self.atr[-1]
        volume_avg = self.volume_sma[-1]
        kalman_trend = self.kalman_trend[-1]
        
        # Check for valid values
        if pd.isna(r4) or pd.isna(s4) or pd.isna(atr) or atr == 0 or pd.isna(kalman_trend):
            return
            
        # Volume confirmation
        volume_confirmed = volume > volume_avg * self.volume_threshold if not pd.isna(volume_avg) else False
        
        # SIGNAL GENERATION using Kalman-smoothed levels
        if not self.position:
            # LONG SIGNALS with Kalman confirmation
            # 1. Kalman price bounces from S3 with positive trend
            s3_bounce_kalman = low_kalman <= s3 and close_kalman > s3 and kalman_trend > -1
            
            # 2. Breakout above R4 with strong positive Kalman trend
            r4_breakout_kalman = high_kalman > r4 and close_kalman > r4 and kalman_trend > 2
            
            # 3. Strong support at S2 with trend reversal
            s2_support = low_kalman <= s2 and close_kalman > s2 and kalman_trend > -3 and kalman_trend > self.kalman_trend[-2] if len(self.kalman_trend) > 1 else False
            
            long_signal = (s3_bounce_kalman or r4_breakout_kalman or s2_support) and volume_confirmed
            
            # SHORT SIGNALS with Kalman confirmation
            # 1. Kalman price rejected from R3 with negative trend
            r3_reject_kalman = high_kalman >= r3 and close_kalman < r3 and kalman_trend < 1
            
            # 2. Breakdown below S4 with strong negative Kalman trend
            s4_breakdown_kalman = low_kalman < s4 and close_kalman < s4 and kalman_trend < -2
            
            # 3. Strong resistance at R2 with trend reversal
            r2_resistance = high_kalman >= r2 and close_kalman < r2 and kalman_trend < 3 and kalman_trend < self.kalman_trend[-2] if len(self.kalman_trend) > 1 else False
            
            short_signal = (r3_reject_kalman or s4_breakdown_kalman or r2_resistance) and volume_confirmed
            
            if long_signal:
                # Calculate signal strength based on Kalman trend
                self.signal_strength = abs(kalman_trend)
                
                # Dynamic stop based on signal strength
                sl_multiplier = self.atr_multiplier_sl * (1 - min(self.signal_strength / 10, 0.3))
                stop_loss = price - (atr * sl_multiplier)
                
                # Target based on ATR (ensure it's far enough)
                take_profit = price + (atr * 3)
                
                # Ensure proper order
                if stop_loss < price < take_profit:
                    self.buy(sl=stop_loss, tp=take_profit)
                
            elif short_signal:
                # Calculate signal strength based on Kalman trend
                self.signal_strength = abs(kalman_trend)
                
                # Dynamic stop based on signal strength
                sl_multiplier = self.atr_multiplier_sl * (1 - min(self.signal_strength / 10, 0.3))
                stop_loss = price + (atr * sl_multiplier)
                
                # Target based on ATR (ensure it's far enough)
                take_profit = price - (atr * 3)
                
                # Ensure proper order
                if take_profit < price < stop_loss:
                    self.sell(sl=stop_loss, tp=take_profit)
                
        elif self.position:
            # EXIT MANAGEMENT based on Kalman trend changes
            if self.position.is_long:
                # Exit if Kalman trend turns strongly negative
                if kalman_trend < -5:
                    self.position.close()
                # Exit if reaching R1 with positive trend
                elif close_kalman >= r1 and kalman_trend > 0:
                    self.position.close()
                        
            elif self.position.is_short:
                # Exit if Kalman trend turns strongly positive
                if kalman_trend > 5:
                    self.position.close()
                # Exit if reaching S1 with negative trend
                elif close_kalman <= s1 and kalman_trend < 0:
                    self.position.close()

def main():
    """Run strategy on all data sources using multi-data tester"""
    print("\n" + "="*80)
    print("🌙 MOON DEV'S CAMARILLA PIVOT - KALMAN FILTERED STRATEGY")
    print("="*80)
    print("Testing Camarilla Pivot with Kalman Filter across all datasets...")
    print("Using Kalman filter to smooth pivot calculations and reduce noise")
    print("="*80)
    
    # Use the multi-data tester
    results = test_on_all_data(
        CamarillaPivotKalman, 
        'CamarillaPivotKalman',
        optimize=False,  # No optimization for speed
        verbose=True
    )
    
    if results is not None:
        print("\n✅ Camarilla Pivot Kalman testing complete!")
        print(f"Results saved to: ./results/CamarillaPivotKalman.csv")

if __name__ == "__main__":
    main()