"""
🌙 Moon Dev's Camarilla Pivot Strategy - Long and Short
========================================================
Uses Camarilla Pivot Points for reversal and breakout trading
Tests across all datasets with multi-data framework
"""

from backtesting import Backtest, Strategy
import pandas as pd
import talib
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class CamarillaPivotLongShort(Strategy):
    """
    Camarilla Pivot Long/Short Strategy
    - Long entry: Price bounces off S3 or breaks above R4
    - Short entry: Price bounces off R3 or breaks below S4
    - Uses S1/R1 as initial targets, S2/R2 as extended targets
    - Volume confirmation for entries
    """
    
    # Parameters
    atr_period = 14
    atr_multiplier_sl = 1.5
    volume_period = 20
    volume_threshold = 1.2  # Volume must be 20% above average
    
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
        
        # Calculate Camarilla Pivot levels
        pivot_range = prev_high - prev_low
        
        # Resistance levels
        r4 = prev_close + (pivot_range * 1.1 / 2)
        r3 = prev_close + (pivot_range * 1.1 / 4)
        r2 = prev_close + (pivot_range * 1.1 / 6)
        r1 = prev_close + (pivot_range * 1.1 / 12)
        
        # Support levels
        s1 = prev_close - (pivot_range * 1.1 / 12)
        s2 = prev_close - (pivot_range * 1.1 / 6)
        s3 = prev_close - (pivot_range * 1.1 / 4)
        s4 = prev_close - (pivot_range * 1.1 / 2)
        
        # Store pivot levels as indicators
        self.r4 = self.I(lambda: r4.values, name='R4')
        self.r3 = self.I(lambda: r3.values, name='R3')
        self.r2 = self.I(lambda: r2.values, name='R2')
        self.r1 = self.I(lambda: r1.values, name='R1')
        self.s1 = self.I(lambda: s1.values, name='S1')
        self.s2 = self.I(lambda: s2.values, name='S2')
        self.s3 = self.I(lambda: s3.values, name='S3')
        self.s4 = self.I(lambda: s4.values, name='S4')
        
        # ATR for stop loss
        self.atr = self.I(talib.ATR, high, low, close, self.atr_period)
        
        # Volume SMA for confirmation
        self.volume_sma = self.I(talib.SMA, volume, self.volume_period)
        
        # Track pivot crosses
        self.last_cross_level = None
        self.bars_since_cross = 0
        
    def next(self):
        # Skip if not enough data
        if len(self.data) < 30:
            return
            
        # Get current values
        price = self.data.Close[-1]
        high = self.data.High[-1]
        low = self.data.Low[-1]
        volume = self.data.Volume[-1]
        
        # Get pivot levels
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
        
        # Check for valid values
        if pd.isna(r4) or pd.isna(s4) or pd.isna(atr) or atr == 0:
            return
            
        # Volume confirmation
        volume_confirmed = volume > volume_avg * self.volume_threshold if not pd.isna(volume_avg) else False
        
        # Track bars since last pivot cross
        self.bars_since_cross += 1
        
        # LONG SIGNALS
        # 1. Bounce from S3 support
        s3_bounce = low <= s3 and price > s3 and self.bars_since_cross > 2
        
        # 2. Breakout above R4
        r4_breakout = high > r4 and price > r4
        
        long_signal = (s3_bounce or r4_breakout) and volume_confirmed
        
        # SHORT SIGNALS
        # 1. Bounce from R3 resistance
        r3_bounce = high >= r3 and price < r3 and self.bars_since_cross > 2
        
        # 2. Breakdown below S4
        s4_breakdown = low < s4 and price < s4
        
        short_signal = (r3_bounce or s4_breakdown) and volume_confirmed
        
        # POSITION MANAGEMENT
        if not self.position:
            if long_signal:
                # Calculate stops and targets
                stop_loss = price - (atr * self.atr_multiplier_sl)
                # Ensure stop loss is below S4
                stop_loss = min(stop_loss, s4) if not pd.isna(s4) else stop_loss
                
                # Set target based on signal type
                if s3_bounce:
                    take_profit = price + (atr * 2)  # ATR-based target
                else:  # R4 breakout
                    take_profit = price + (atr * 3)  # Larger target for breakout
                
                # Ensure TP > price > SL
                if stop_loss < price < take_profit:
                    self.buy(sl=stop_loss, tp=take_profit)
                    self.last_cross_level = 'long'
                    self.bars_since_cross = 0
                
            elif short_signal:
                # Calculate stops and targets
                stop_loss = price + (atr * self.atr_multiplier_sl)
                # Ensure stop loss is above R4
                stop_loss = max(stop_loss, r4) if not pd.isna(r4) else stop_loss
                
                # Set target based on signal type
                if r3_bounce:
                    take_profit = price - (atr * 2)  # ATR-based target
                else:  # S4 breakdown
                    take_profit = price - (atr * 3)  # Larger target for breakdown
                
                # Ensure TP < price < SL
                if take_profit < price < stop_loss:
                    self.sell(sl=stop_loss, tp=take_profit)
                self.last_cross_level = 'short'
                self.bars_since_cross = 0
                
        elif self.position:
            # Manage existing position
            if self.position.is_long:
                # Exit at R2 if reached
                if price >= r2:
                    self.position.close()
                    
            elif self.position.is_short:
                # Exit at S2 if reached
                if price <= s2:
                    self.position.close()

def main():
    """Run strategy on all data sources using multi-data tester"""
    print("\n" + "="*80)
    print("🌙 MOON DEV'S CAMARILLA PIVOT - LONG/SHORT STRATEGY")
    print("="*80)
    print("Testing Camarilla Pivot Long/Short across all datasets...")
    print("="*80)
    
    # Use the multi-data tester
    results = test_on_all_data(
        CamarillaPivotLongShort, 
        'CamarillaPivotLongShort',
        optimize=False,  # No optimization for speed
        verbose=True
    )
    
    if results is not None:
        print("\n✅ Camarilla Pivot Long/Short testing complete!")
        print(f"Results saved to: ./results/CamarillaPivotLongShort.csv")

if __name__ == "__main__":
    main()