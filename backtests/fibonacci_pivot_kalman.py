"""
Moon Dev's Fibonacci Pivot with Kalman Filter Strategy
======================================================
Uses Fibonacci retracement levels with Kalman filtered price for noise reduction
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class FibonacciPivotKalmanStrategy(Strategy):
    """
    Fibonacci Pivot with Kalman Filter Strategy
    - Calculates pivot points using Kalman filtered prices
    - Uses Fibonacci ratios for support/resistance levels
    - Kalman filter reduces noise for cleaner signals
    - Both long and short positions
    - Position sizing: 95% of equity
    """
    
    # Fibonacci levels
    fib_r1 = 0.382  # First resistance
    fib_r2 = 0.618  # Second resistance
    fib_r3 = 1.000  # Third resistance
    
    # Kalman filter parameters
    kalman_gain = 0.1  # Process noise covariance
    
    # Risk management
    position_size = 0.95
    stop_loss_pct = 0.02  # 2% stop loss
    take_profit_pct = 0.05  # 5% take profit
    
    def kalman_filter(self, prices):
        """Apply Kalman filter to price series"""
        filtered = np.zeros_like(prices)
        filtered[0] = prices[0] if not pd.isna(prices[0]) else 0
        
        for i in range(1, len(prices)):
            if pd.isna(prices[i]):
                filtered[i] = filtered[i-1]
            else:
                # Simple 1D Kalman filter
                filtered[i] = filtered[i-1] + self.kalman_gain * (prices[i] - filtered[i-1])
        
        return filtered
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Apply Kalman filter to smooth prices
        close_kalman = self.kalman_filter(close.values)
        high_kalman = self.kalman_filter(high.values)
        low_kalman = self.kalman_filter(low.values)
        
        # Store Kalman filtered prices
        self.close_kalman = self.I(lambda: close_kalman, name='Close_Kalman')
        self.high_kalman = self.I(lambda: high_kalman, name='High_Kalman')
        self.low_kalman = self.I(lambda: low_kalman, name='Low_Kalman')
        
        # Calculate daily range for pivot points using Kalman filtered prices
        high_prev = pd.Series(high_kalman).shift(1)
        low_prev = pd.Series(low_kalman).shift(1)
        close_prev = pd.Series(close_kalman).shift(1)
        
        # Calculate pivot point with Kalman filtered prices
        pivot = (high_prev + low_prev + close_prev) / 3
        self.pivot = self.I(lambda: pivot.values, name='Pivot')
        
        # Calculate range for Fibonacci levels
        daily_range = high_prev - low_prev
        
        # Resistance levels
        r1 = pivot + self.fib_r1 * daily_range
        r2 = pivot + self.fib_r2 * daily_range
        r3 = pivot + self.fib_r3 * daily_range
        
        # Support levels
        s1 = pivot - self.fib_r1 * daily_range
        s2 = pivot - self.fib_r2 * daily_range
        s3 = pivot - self.fib_r3 * daily_range
        
        self.r1 = self.I(lambda: r1.values, name='R1')
        self.r2 = self.I(lambda: r2.values, name='R2')
        self.r3 = self.I(lambda: r3.values, name='R3')
        self.s1 = self.I(lambda: s1.values, name='S1')
        self.s2 = self.I(lambda: s2.values, name='S2')
        self.s3 = self.I(lambda: s3.values, name='S3')
        
        # Track entry price and direction
        self.entry_price = 0
        self.is_long = True
        
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < 10:
            return
        
        # Use Kalman filtered price for signals
        price = self.close_kalman[-1]
        prev_price = self.close_kalman[-2] if len(self.close_kalman) > 1 else price
        actual_price = self.data.Close[-1]  # Actual price for execution
        
        # Get current levels
        pivot = self.pivot[-1]
        s1 = self.s1[-1]
        s2 = self.s2[-1]
        s3 = self.s3[-1]
        r1 = self.r1[-1]
        r2 = self.r2[-1]
        r3 = self.r3[-1]
        
        # Check for valid values
        if pd.isna(pivot) or pd.isna(s1) or pd.isna(r1) or pd.isna(price):
            return
        
        # Long entry signals (using Kalman filtered prices)
        pivot_cross_up = prev_price <= pivot and price > pivot
        s1_bounce = price > s1 and self.low_kalman[-1] <= s1 * 1.002
        s2_bounce = price > s2 and self.low_kalman[-1] <= s2 * 1.002
        s3_bounce = price > s3 and self.low_kalman[-1] <= s3 * 1.002
        
        # Short entry signals (using Kalman filtered prices)
        pivot_cross_down = prev_price >= pivot and price < pivot
        r1_rejection = price < r1 and self.high_kalman[-1] >= r1 * 0.998
        r2_rejection = price < r2 and self.high_kalman[-1] >= r2 * 0.998
        r3_rejection = price < r3 and self.high_kalman[-1] >= r3 * 0.998
        
        # Entry logic
        if not self.position:
            # Long entries
            if pivot_cross_up or s1_bounce or s2_bounce or s3_bounce:
                size = self.position_size
                self.buy(size=size)
                self.entry_price = actual_price
                self.is_long = True
            
            # Short entries
            elif pivot_cross_down or r1_rejection or r2_rejection or r3_rejection:
                size = self.position_size
                self.sell(size=size)
                self.entry_price = actual_price
                self.is_long = False
        
        # Exit logic for long positions
        elif self.position and self.is_long:
            # Calculate stop loss and take profit levels
            stop_loss = self.entry_price * (1 - self.stop_loss_pct)
            take_profit = self.entry_price * (1 + self.take_profit_pct)
            
            # Exit conditions (using Kalman filtered prices for signals)
            hit_r3 = price >= r3
            
            # Exit on resistance, pivot break, or stop/target
            if hit_r3 or pivot_cross_down or actual_price <= stop_loss or actual_price >= take_profit:
                self.position.close()
                self.entry_price = 0
            elif price >= r2:
                # Partial exit at R2
                if self.position.size > 0.5:
                    self.position.close(0.5)
            elif price >= r1:
                # Partial exit at R1
                if self.position.size > 0.75:
                    self.position.close(0.25)
        
        # Exit logic for short positions
        elif self.position and not self.is_long:
            # Calculate stop loss and take profit levels
            stop_loss = self.entry_price * (1 + self.stop_loss_pct)
            take_profit = self.entry_price * (1 - self.take_profit_pct)
            
            # Exit conditions (using Kalman filtered prices for signals)
            hit_s3 = price <= s3
            
            # Exit on support, pivot break, or stop/target
            if hit_s3 or pivot_cross_up or actual_price >= stop_loss or actual_price <= take_profit:
                self.position.close()
                self.entry_price = 0
            elif price <= s2:
                # Partial exit at S2
                if abs(self.position.size) > 0.5:
                    self.position.close(0.5)
            elif price <= s1:
                # Partial exit at S1
                if abs(self.position.size) > 0.75:
                    self.position.close(0.25)

def main():
    """Run the Fibonacci Pivot with Kalman Filter Strategy on all datasets"""
    print("\n" + "="*80)
    print("MOON DEV'S FIBONACCI PIVOT WITH KALMAN FILTER STRATEGY")
    print("="*80)
    
    # Run on all data sources
    results = test_on_all_data(
        FibonacciPivotKalmanStrategy,
        'FibonacciPivotKalman',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("STRATEGY COMPLETE!")
        print("="*80)

if __name__ == "__main__":
    main()