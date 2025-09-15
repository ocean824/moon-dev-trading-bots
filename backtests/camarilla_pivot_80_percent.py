"""
🌙 Moon Dev's Camarilla Pivot Strategy - 80% Retracement
=========================================================
Uses 80% of Camarilla levels for tighter bands and more frequent signals
Tests across all datasets with multi-data framework
"""

from backtesting import Backtest, Strategy
import pandas as pd
import talib
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class CamarillaPivot80Percent(Strategy):
    """
    Camarilla Pivot 80% Retracement Strategy
    - Use 80% of the Camarilla levels (multiply levels by 0.8)
    - Creates tighter bands for more frequent signals
    - Long when price reaches 80% of S3 level
    - Short when price reaches 80% of R3 level
    - Use 80% of S1/R1 as targets
    """
    
    # Parameters
    retracement_factor = 0.8  # Use 80% of pivot levels
    atr_period = 14
    atr_multiplier_sl = 1.2  # Tighter stops for tighter bands
    volume_period = 20
    volume_threshold = 1.1  # Volume must be 10% above average
    momentum_period = 10  # For momentum confirmation
    
    def init(self):
        # Convert to pandas Series for calculations
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Calculate daily OHLC for pivot calculation
        # We'll use a rolling window to get previous period's values
        pivot_period = 24  # Assume hourly data, use 24 hours for daily pivot
        
        # Calculate previous period's high, low, close for pivots
        prev_high = high.rolling(window=pivot_period).max().shift(1)
        prev_low = low.rolling(window=pivot_period).min().shift(1)
        prev_close = close.shift(pivot_period)
        
        # Calculate standard Camarilla Pivot levels
        pivot_range = prev_high - prev_low
        
        # Calculate pivot point (for 80% adjustment reference)
        pivot_point = (prev_high + prev_low + prev_close) / 3
        
        # Standard Camarilla levels
        r4_full = prev_close + (pivot_range * 1.1 / 2)
        r3_full = prev_close + (pivot_range * 1.1 / 4)
        r2_full = prev_close + (pivot_range * 1.1 / 6)
        r1_full = prev_close + (pivot_range * 1.1 / 12)
        s1_full = prev_close - (pivot_range * 1.1 / 12)
        s2_full = prev_close - (pivot_range * 1.1 / 6)
        s3_full = prev_close - (pivot_range * 1.1 / 4)
        s4_full = prev_close - (pivot_range * 1.1 / 2)
        
        # Apply 80% retracement (tighter bands)
        # Distance from pivot point is reduced by 20%
        r4 = pivot_point + (r4_full - pivot_point) * self.retracement_factor
        r3 = pivot_point + (r3_full - pivot_point) * self.retracement_factor
        r2 = pivot_point + (r2_full - pivot_point) * self.retracement_factor
        r1 = pivot_point + (r1_full - pivot_point) * self.retracement_factor
        s1 = pivot_point - (pivot_point - s1_full) * self.retracement_factor
        s2 = pivot_point - (pivot_point - s2_full) * self.retracement_factor
        s3 = pivot_point - (pivot_point - s3_full) * self.retracement_factor
        s4 = pivot_point - (pivot_point - s4_full) * self.retracement_factor
        
        # Store adjusted pivot levels as indicators
        self.r4 = self.I(lambda: r4.values, name='R4_80')
        self.r3 = self.I(lambda: r3.values, name='R3_80')
        self.r2 = self.I(lambda: r2.values, name='R2_80')
        self.r1 = self.I(lambda: r1.values, name='R1_80')
        self.s1 = self.I(lambda: s1.values, name='S1_80')
        self.s2 = self.I(lambda: s2.values, name='S2_80')
        self.s3 = self.I(lambda: s3.values, name='S3_80')
        self.s4 = self.I(lambda: s4.values, name='S4_80')
        self.pivot = self.I(lambda: pivot_point.values, name='Pivot')
        
        # ATR for stop loss
        self.atr = self.I(talib.ATR, high, low, close, self.atr_period)
        
        # Volume SMA for confirmation
        self.volume_sma = self.I(talib.SMA, volume, self.volume_period)
        
        # Momentum indicator (ROC) for confirmation
        self.roc = self.I(talib.ROC, close, self.momentum_period)
        
        # Track recent touches of levels
        self.bars_since_s3_touch = 0
        self.bars_since_r3_touch = 0
        
    def next(self):
        # Skip if not enough data
        if len(self.data) < 30:
            return
            
        # Get current values
        price = self.data.Close[-1]
        high = self.data.High[-1]
        low = self.data.Low[-1]
        volume = self.data.Volume[-1]
        
        # Get adjusted pivot levels (80%)
        r4 = self.r4[-1]
        r3 = self.r3[-1]
        r2 = self.r2[-1]
        r1 = self.r1[-1]
        s1 = self.s1[-1]
        s2 = self.s2[-1]
        s3 = self.s3[-1]
        s4 = self.s4[-1]
        pivot = self.pivot[-1]
        
        # Get indicators
        atr = self.atr[-1]
        volume_avg = self.volume_sma[-1]
        roc = self.roc[-1]
        
        # Check for valid values
        if pd.isna(r4) or pd.isna(s4) or pd.isna(atr) or atr == 0 or pd.isna(roc):
            return
            
        # Volume confirmation (slightly relaxed for more signals)
        volume_confirmed = volume > volume_avg * self.volume_threshold if not pd.isna(volume_avg) else True
        
        # Update touch counters
        self.bars_since_s3_touch += 1
        self.bars_since_r3_touch += 1
        
        # Check for level touches
        if low <= s3:
            self.bars_since_s3_touch = 0
        if high >= r3:
            self.bars_since_r3_touch = 0
        
        # TRADING SIGNALS (using tighter 80% bands)
        if not self.position:
            # LONG SIGNAL - Price reaches 80% S3 level
            # Look for bounce from S3 with positive momentum shift
            long_condition1 = low <= s3 and price > s3  # Touch and bounce
            long_condition2 = self.bars_since_s3_touch <= 3  # Recent touch
            long_condition3 = roc > -5  # Not in strong downtrend
            long_signal = long_condition1 and long_condition2 and long_condition3 and volume_confirmed
            
            # Additional long on S2 touch in oversold conditions
            alt_long = low <= s2 and price > s2 and roc < -10 and volume_confirmed
            
            if long_signal or alt_long:
                # Use ATR-based stops
                stop_loss = price - (atr * self.atr_multiplier_sl)
                # Target based on ATR
                take_profit = price + (atr * 2)
                
                # Ensure proper order
                if stop_loss < price < take_profit:
                    self.buy(sl=stop_loss, tp=take_profit)
                
            # SHORT SIGNAL - Price reaches 80% R3 level
            # Look for rejection from R3 with negative momentum shift
            short_condition1 = high >= r3 and price < r3  # Touch and rejection
            short_condition2 = self.bars_since_r3_touch <= 3  # Recent touch
            short_condition3 = roc < 5  # Not in strong uptrend
            short_signal = short_condition1 and short_condition2 and short_condition3 and volume_confirmed
            
            # Additional short on R2 touch in overbought conditions
            alt_short = high >= r2 and price < r2 and roc > 10 and volume_confirmed
            
            if short_signal or alt_short:
                # Use ATR-based stops
                stop_loss = price + (atr * self.atr_multiplier_sl)
                # Target based on ATR
                take_profit = price - (atr * 2)
                
                # Ensure proper order
                if take_profit < price < stop_loss:
                    self.sell(sl=stop_loss, tp=take_profit)
                
        elif self.position:
            # POSITION MANAGEMENT with tighter bands
            if self.position.is_long:
                # Quick exit if price reaches pivot (middle point)
                if price >= pivot and roc > 5:
                    # Take partial profit at pivot
                    if price >= r1:
                        self.position.close()
                        
                # Exit if momentum turns strongly negative
                if roc < -10:
                    self.position.close()
                    
            elif self.position.is_short:
                # Quick exit if price reaches pivot (middle point)
                if price <= pivot and roc < -5:
                    # Take partial profit at pivot
                    if price <= s1:
                        self.position.close()
                        
                # Exit if momentum turns strongly positive
                if roc > 10:
                    self.position.close()

def main():
    """Run strategy on all data sources using multi-data tester"""
    print("\n" + "="*80)
    print("🌙 MOON DEV'S CAMARILLA PIVOT - 80% RETRACEMENT STRATEGY")
    print("="*80)
    print("Testing Camarilla Pivot 80% Retracement across all datasets...")
    print("Using tighter bands (80% of standard levels) for more frequent signals")
    print("="*80)
    
    # Use the multi-data tester
    results = test_on_all_data(
        CamarillaPivot80Percent, 
        'CamarillaPivot80Percent',
        optimize=False,  # No optimization for speed
        verbose=True
    )
    
    if results is not None:
        print("\n✅ Camarilla Pivot 80% Retracement testing complete!")
        print(f"Results saved to: ./results/CamarillaPivot80Percent.csv")

if __name__ == "__main__":
    main()