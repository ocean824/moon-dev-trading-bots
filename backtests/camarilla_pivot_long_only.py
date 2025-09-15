"""
🌙 Moon Dev's Camarilla Pivot Strategy - Long Only
===================================================
Uses Camarilla Pivot Points for long-only trading
Tests across all datasets with multi-data framework
"""

from backtesting import Backtest, Strategy
import pandas as pd
import talib
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class CamarillaPivotLongOnly(Strategy):
    """
    Camarilla Pivot Long Only Strategy
    - Only take long positions
    - Entry on bounce from S3 support or breakout above R4
    - Use R1, R2, R3 as scaled profit targets
    - Trailing stop using S1 level
    - Wait for oversold conditions before entering
    """
    
    # Parameters
    rsi_period = 14
    rsi_oversold = 35
    atr_period = 14
    atr_multiplier_sl = 1.5
    volume_period = 20
    volume_threshold = 1.1  # Volume must be 10% above average
    
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
        
        # RSI for oversold conditions
        self.rsi = self.I(talib.RSI, close, self.rsi_period)
        
        # ATR for stop loss
        self.atr = self.I(talib.ATR, high, low, close, self.atr_period)
        
        # Volume SMA for confirmation
        self.volume_sma = self.I(talib.SMA, volume, self.volume_period)
        
        # Track entry and targets
        self.entry_price = None
        self.initial_stop = None
        self.target_hit = 0  # Track which target level we've reached
        
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
        rsi = self.rsi[-1]
        atr = self.atr[-1]
        volume_avg = self.volume_sma[-1]
        
        # Check for valid values
        if pd.isna(r4) or pd.isna(s4) or pd.isna(atr) or atr == 0 or pd.isna(rsi):
            return
            
        # Volume confirmation
        volume_confirmed = volume > volume_avg * self.volume_threshold if not pd.isna(volume_avg) else False
        
        # LONG ENTRY CONDITIONS (Long Only)
        if not self.position:
            # Check for oversold condition
            oversold = rsi < self.rsi_oversold
            
            # 1. Bounce from S3 support with oversold
            s3_bounce = low <= s3 and price > s3 and oversold
            
            # 2. Bounce from S2 in strong oversold
            s2_bounce = low <= s2 and price > s2 and rsi < 25
            
            # 3. Breakout above R4 with momentum
            r4_breakout = high > r4 and price > r4 and rsi > 50
            
            long_signal = (s3_bounce or s2_bounce or r4_breakout) and volume_confirmed
            
            if long_signal:
                # Calculate initial stop loss
                stop_loss = price - (atr * self.atr_multiplier_sl)
                # Make sure stop is reasonable
                stop_loss = min(stop_loss, price * 0.97)  # Max 3% stop
                
                # Set initial target
                take_profit = price + (atr * 2.5)
                # Make sure target is reasonable
                take_profit = max(take_profit, price * 1.02)  # Min 2% target
                
                # Ensure proper order: SL < price < TP
                if stop_loss < price < take_profit:
                    self.buy(sl=stop_loss, tp=take_profit)
                    self.entry_price = price
                    self.initial_stop = stop_loss
                    self.target_hit = 0
                
        elif self.position and self.position.is_long:
            # POSITION MANAGEMENT - Simple exit rules
            
            # Exit if RSI becomes overbought
            if rsi > 70:
                self.position.close()
                self.entry_price = None
                self.target_hit = 0
                
            # Exit if price reaches R2 level
            elif price >= r2:
                self.position.close()
                self.entry_price = None
                self.target_hit = 0

def main():
    """Run strategy on all data sources using multi-data tester"""
    print("\n" + "="*80)
    print("🌙 MOON DEV'S CAMARILLA PIVOT - LONG ONLY STRATEGY")
    print("="*80)
    print("Testing Camarilla Pivot Long Only across all datasets...")
    print("="*80)
    
    # Use the multi-data tester
    results = test_on_all_data(
        CamarillaPivotLongOnly, 
        'CamarillaPivotLongOnly',
        optimize=False,  # No optimization for speed
        verbose=True
    )
    
    if results is not None:
        print("\n✅ Camarilla Pivot Long Only testing complete!")
        print(f"Results saved to: ./results/CamarillaPivotLongOnly.csv")

if __name__ == "__main__":
    main()