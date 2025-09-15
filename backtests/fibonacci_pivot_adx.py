"""
Moon Dev's Fibonacci Pivot with ADX Filter Strategy
===================================================
Uses Fibonacci retracement levels with ADX trend confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class FibonacciPivotADXStrategy(Strategy):
    """
    Fibonacci Pivot with ADX Filter Strategy
    - Calculates pivot points using (High + Low + Close) / 3
    - Uses Fibonacci ratios for support/resistance levels
    - Only trades when ADX > 25 (strong trend)
    - Uses +DI/-DI for trend direction confirmation
    - Position sizing: 95% of equity
    """
    
    # Fibonacci levels
    fib_r1 = 0.382  # First resistance
    fib_r2 = 0.618  # Second resistance
    fib_r3 = 1.000  # Third resistance
    
    # ADX parameters
    adx_period = 14
    adx_threshold = 25  # Only trade in strong trends
    
    # Risk management
    position_size = 0.95
    stop_loss_pct = 0.02  # 2% stop loss
    take_profit_pct = 0.05  # 5% take profit
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Calculate daily range for pivot points
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
        
        # Calculate ADX for trend strength
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        self.adx = self.I(lambda: adx_result['ADX_14'].values, name='ADX')
        self.plus_di = self.I(lambda: adx_result['DMP_14'].values, name='+DI')
        self.minus_di = self.I(lambda: adx_result['DMN_14'].values, name='-DI')
        
        # Track entry price and direction
        self.entry_price = 0
        self.is_long = True
        
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < self.adx_period + 10:
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
        
        # Get ADX values
        adx = self.adx[-1]
        plus_di = self.plus_di[-1]
        minus_di = self.minus_di[-1]
        
        # Check for valid values
        if pd.isna(pivot) or pd.isna(s1) or pd.isna(r1) or pd.isna(adx):
            return
        
        # Check if trend is strong enough
        trend_strong = adx > self.adx_threshold
        uptrend = plus_di > minus_di
        downtrend = minus_di > plus_di
        
        # Long entry signals (only in strong uptrend)
        pivot_cross_up = prev_price <= pivot and price > pivot
        s1_bounce = price > s1 and self.data.Low[-1] <= s1 * 1.002
        s2_bounce = price > s2 and self.data.Low[-1] <= s2 * 1.002
        s3_bounce = price > s3 and self.data.Low[-1] <= s3 * 1.002
        
        # Short entry signals (only in strong downtrend)
        pivot_cross_down = prev_price >= pivot and price < pivot
        r1_rejection = price < r1 and self.data.High[-1] >= r1 * 0.998
        r2_rejection = price < r2 and self.data.High[-1] >= r2 * 0.998
        r3_rejection = price < r3 and self.data.High[-1] >= r3 * 0.998
        
        # Entry logic
        if not self.position:
            # Long entries (require strong uptrend)
            if trend_strong and uptrend and (pivot_cross_up or s1_bounce or s2_bounce or s3_bounce):
                size = self.position_size
                self.buy(size=size)
                self.entry_price = price
                self.is_long = True
            
            # Short entries (require strong downtrend)
            elif trend_strong and downtrend and (pivot_cross_down or r1_rejection or r2_rejection or r3_rejection):
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
            hit_r3 = price >= r3
            trend_weakening = adx < self.adx_threshold * 0.8  # Exit if trend weakens
            
            # Exit on resistance, weak trend, pivot break, or stop/target
            if hit_r3 or trend_weakening or pivot_cross_down or price <= stop_loss or price >= take_profit:
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
            
            # Exit conditions
            hit_s3 = price <= s3
            trend_weakening = adx < self.adx_threshold * 0.8  # Exit if trend weakens
            
            # Exit on support, weak trend, pivot break, or stop/target
            if hit_s3 or trend_weakening or pivot_cross_up or price >= stop_loss or price <= take_profit:
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
    """Run the Fibonacci Pivot with ADX Filter Strategy on all datasets"""
    print("\n" + "="*80)
    print("MOON DEV'S FIBONACCI PIVOT WITH ADX FILTER STRATEGY")
    print("="*80)
    
    # Run on all data sources
    results = test_on_all_data(
        FibonacciPivotADXStrategy,
        'FibonacciPivotADX',
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