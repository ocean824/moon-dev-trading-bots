"""
Moon Dev's Fibonacci Pivot Both Directions Strategy
===================================================
Uses Fibonacci retracement levels with daily pivot points for long and short positions
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class FibonacciPivotBothStrategy(Strategy):
    """
    Fibonacci Pivot Both Directions Strategy
    - Calculates pivot points using (High + Low + Close) / 3
    - Uses Fibonacci ratios for support/resistance levels
    - Long entries on pivot crossovers or support bounces
    - Short entries on pivot breaks or resistance rejections
    - Position sizing: 95% of equity
    """
    
    # Fibonacci levels
    fib_r1 = 0.382  # First resistance
    fib_r2 = 0.618  # Second resistance
    fib_r3 = 1.000  # Third resistance
    
    # Lookback for pivot calculation
    pivot_period = 1  # Daily pivot (use previous day's HLC)
    
    # Risk management
    position_size = 0.95
    stop_loss_pct = 0.02  # 2% stop loss
    take_profit_pct = 0.05  # 5% take profit
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Calculate daily range for pivot points
        # Use rolling window to get previous day's values
        high_prev = high.shift(1)
        low_prev = low.shift(1)
        close_prev = close.shift(1)
        
        # Calculate pivot point
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
        
        price = self.data.Close[-1]
        prev_price = self.data.Close[-2] if len(self.data.Close) > 1 else price
        
        # Get current levels
        pivot = self.pivot[-1]
        s1 = self.s1[-1]
        s2 = self.s2[-1]
        s3 = self.s3[-1]
        r1 = self.r1[-1]
        r2 = self.r2[-1]
        r3 = self.r3[-1]
        
        # Check for valid values
        if pd.isna(pivot) or pd.isna(s1) or pd.isna(r1):
            return
        
        # Long entry signals
        pivot_cross_up = prev_price <= pivot and price > pivot
        s1_bounce = price > s1 and self.data.Low[-1] <= s1 * 1.002  # Touch within 0.2%
        s2_bounce = price > s2 and self.data.Low[-1] <= s2 * 1.002
        s3_bounce = price > s3 and self.data.Low[-1] <= s3 * 1.002
        
        # Short entry signals
        pivot_cross_down = prev_price >= pivot and price < pivot
        r1_rejection = price < r1 and self.data.High[-1] >= r1 * 0.998  # Touch within 0.2%
        r2_rejection = price < r2 and self.data.High[-1] >= r2 * 0.998
        r3_rejection = price < r3 and self.data.High[-1] >= r3 * 0.998
        
        # Entry logic
        if not self.position:
            # Long entries
            if pivot_cross_up or s1_bounce or s2_bounce or s3_bounce:
                size = self.position_size
                self.buy(size=size)
                self.entry_price = price
                self.is_long = True
            
            # Short entries
            elif pivot_cross_down or r1_rejection or r2_rejection or r3_rejection:
                size = self.position_size
                self.sell(size=size)
                self.entry_price = price
                self.is_long = False
        
        # Exit logic for long positions
        elif self.position and self.is_long:
            # Calculate stop loss and take profit levels
            stop_loss = self.entry_price * (1 - self.stop_loss_pct)
            take_profit = self.entry_price * (1 + self.take_profit_pct)
            
            # Exit conditions
            hit_r1 = price >= r1
            hit_r2 = price >= r2
            hit_r3 = price >= r3
            
            # Exit on resistance levels, pivot break, or stop/target
            if hit_r3 or pivot_cross_down or price <= stop_loss or price >= take_profit:
                self.position.close()
                self.entry_price = 0
            elif hit_r2:
                # Partial exit at R2
                if self.position.size > 0.5:
                    self.position.close(0.5)
            elif hit_r1:
                # Partial exit at R1
                if self.position.size > 0.75:
                    self.position.close(0.25)
        
        # Exit logic for short positions
        elif self.position and not self.is_long:
            # Calculate stop loss and take profit levels
            stop_loss = self.entry_price * (1 + self.stop_loss_pct)
            take_profit = self.entry_price * (1 - self.take_profit_pct)
            
            # Exit conditions
            hit_s1 = price <= s1
            hit_s2 = price <= s2
            hit_s3 = price <= s3
            
            # Exit on support levels, pivot break, or stop/target
            if hit_s3 or pivot_cross_up or price >= stop_loss or price <= take_profit:
                self.position.close()
                self.entry_price = 0
            elif hit_s2:
                # Partial exit at S2
                if abs(self.position.size) > 0.5:
                    self.position.close(0.5)
            elif hit_s1:
                # Partial exit at S1
                if abs(self.position.size) > 0.75:
                    self.position.close(0.25)

def main():
    """Run the Fibonacci Pivot Both Directions Strategy on all datasets"""
    print("\n" + "="*80)
    print("MOON DEV'S FIBONACCI PIVOT BOTH DIRECTIONS STRATEGY")
    print("="*80)
    
    # Run on all data sources
    results = test_on_all_data(
        FibonacciPivotBothStrategy,
        'FibonacciPivotBoth',
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