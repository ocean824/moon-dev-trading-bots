"""
🌙 Moon Dev's Camarilla Pivot Strategy - Money Flow Index
==========================================================
Combines Camarilla Pivots with MFI for oversold/overbought confirmation
Tests across all datasets with multi-data framework
"""

from backtesting import Backtest, Strategy
import pandas as pd
import talib
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class CamarillaPivotMFI(Strategy):
    """
    Camarilla Pivot with Money Flow Index Strategy
    - Combine Camarilla Pivots with MFI (Money Flow Index)
    - Long only when price at S3 AND MFI < 20 (oversold)
    - Short only when price at R3 AND MFI > 80 (overbought)
    - Use MFI divergences for additional confirmation
    - Exit when MFI reaches opposite extreme
    """
    
    # Parameters
    mfi_period = 14
    mfi_oversold = 20
    mfi_overbought = 80
    mfi_exit_long = 70   # Exit long when MFI reaches this level
    mfi_exit_short = 30  # Exit short when MFI reaches this level
    divergence_lookback = 10  # Bars to check for divergence
    atr_period = 14
    atr_multiplier_sl = 1.5
    volume_period = 20
    volume_threshold = 1.1
    
    def init(self):
        # Convert to pandas Series for calculations
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Calculate MFI (Money Flow Index)
        self.mfi = self.I(talib.MFI, high, low, close, volume, self.mfi_period)
        
        # Calculate daily OHLC for pivot calculation
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
        
        # Track divergence signals
        self.bullish_divergence = False
        self.bearish_divergence = False
        self.last_pivot_low = None
        self.last_pivot_high = None
        self.last_mfi_low = None
        self.last_mfi_high = None
        
    def check_divergence(self):
        """Check for MFI divergences with price"""
        if len(self.data) < self.divergence_lookback + 5:
            return
            
        # Get recent data
        recent_prices = self.data.Close[-self.divergence_lookback:]
        recent_lows = self.data.Low[-self.divergence_lookback:]
        recent_highs = self.data.High[-self.divergence_lookback:]
        recent_mfi = [self.mfi[i] for i in range(-self.divergence_lookback, 0)]
        
        # Check for valid MFI values
        if any(pd.isna(val) for val in recent_mfi):
            return
            
        # Find local pivots in price
        price_pivot_low_idx = np.argmin(recent_lows)
        price_pivot_high_idx = np.argmax(recent_highs)
        
        # Find corresponding MFI values
        mfi_at_price_low = recent_mfi[price_pivot_low_idx]
        mfi_at_price_high = recent_mfi[price_pivot_high_idx]
        
        # Check for bullish divergence (price makes lower low, MFI makes higher low)
        if self.last_pivot_low is not None and self.last_mfi_low is not None:
            price_lower_low = recent_lows[price_pivot_low_idx] < self.last_pivot_low
            mfi_higher_low = mfi_at_price_low > self.last_mfi_low
            self.bullish_divergence = price_lower_low and mfi_higher_low and recent_mfi[-1] < 30
        
        # Check for bearish divergence (price makes higher high, MFI makes lower high)
        if self.last_pivot_high is not None and self.last_mfi_high is not None:
            price_higher_high = recent_highs[price_pivot_high_idx] > self.last_pivot_high
            mfi_lower_high = mfi_at_price_high < self.last_mfi_high
            self.bearish_divergence = price_higher_high and mfi_lower_high and recent_mfi[-1] > 70
        
        # Update last pivot values
        self.last_pivot_low = recent_lows[price_pivot_low_idx]
        self.last_pivot_high = recent_highs[price_pivot_high_idx]
        self.last_mfi_low = mfi_at_price_low
        self.last_mfi_high = mfi_at_price_high
        
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
        mfi = self.mfi[-1]
        atr = self.atr[-1]
        volume_avg = self.volume_sma[-1]
        
        # Check for valid values
        if pd.isna(r4) or pd.isna(s4) or pd.isna(atr) or atr == 0 or pd.isna(mfi):
            return
            
        # Volume confirmation
        volume_confirmed = volume > volume_avg * self.volume_threshold if not pd.isna(volume_avg) else False
        
        # Check for divergences
        self.check_divergence()
        
        # ENTRY SIGNALS with MFI confirmation
        if not self.position:
            # LONG SIGNAL - S3 touch with MFI oversold
            s3_touch = low <= s3 and price > s3
            s2_touch = low <= s2 and price > s2  # Stronger support level
            mfi_oversold = mfi < self.mfi_oversold
            mfi_recovering = mfi > self.mfi[-2] if len(self.mfi) > 1 else False
            
            # Primary long condition: S3 + MFI oversold
            long_primary = s3_touch and mfi_oversold and volume_confirmed
            
            # Secondary long condition: S2 + MFI < 30
            long_secondary = s2_touch and mfi < 30 and volume_confirmed
            
            # Divergence long: Bullish divergence at any support
            long_divergence = self.bullish_divergence and (s3_touch or s2_touch or low <= s1)
            
            long_signal = long_primary or long_secondary or long_divergence
            
            # SHORT SIGNAL - R3 touch with MFI overbought
            r3_touch = high >= r3 and price < r3
            r2_touch = high >= r2 and price < r2  # Stronger resistance level
            mfi_overbought = mfi > self.mfi_overbought
            mfi_weakening = mfi < self.mfi[-2] if len(self.mfi) > 1 else False
            
            # Primary short condition: R3 + MFI overbought
            short_primary = r3_touch and mfi_overbought and volume_confirmed
            
            # Secondary short condition: R2 + MFI > 70
            short_secondary = r2_touch and mfi > 70 and volume_confirmed
            
            # Divergence short: Bearish divergence at any resistance
            short_divergence = self.bearish_divergence and (r3_touch or r2_touch or high >= r1)
            
            short_signal = short_primary or short_secondary or short_divergence
            
            if long_signal:
                # Dynamic stop based on MFI extremity
                mfi_factor = 1 - (mfi / 100)  # Lower MFI = tighter stop
                sl_multiplier = self.atr_multiplier_sl * (1 + mfi_factor * 0.3)
                stop_loss = price - (atr * sl_multiplier)
                
                # Target based on ATR to ensure proper distance
                take_profit = price + (atr * 2.5)
                
                # Ensure proper order
                if stop_loss < price < take_profit:
                    self.buy(sl=stop_loss, tp=take_profit)
                
            elif short_signal:
                # Dynamic stop based on MFI extremity
                mfi_factor = mfi / 100  # Higher MFI = tighter stop
                sl_multiplier = self.atr_multiplier_sl * (1 + mfi_factor * 0.3)
                stop_loss = price + (atr * sl_multiplier)
                
                # Target based on ATR to ensure proper distance
                take_profit = price - (atr * 2.5)
                
                # Ensure proper order
                if take_profit < price < stop_loss:
                    self.sell(sl=stop_loss, tp=take_profit)
                
        elif self.position:
            # EXIT MANAGEMENT based on MFI extremes
            if self.position.is_long:
                # Exit conditions for long
                mfi_exit = mfi >= self.mfi_exit_long  # MFI reaches overbought
                price_target = price >= r1  # Reached first target
                mfi_divergence_exit = self.bearish_divergence and mfi > 60
                
                if mfi_exit or (price_target and mfi > 50) or mfi_divergence_exit:
                    self.position.close()
                    
                # Exit if MFI is recovering strongly
                elif mfi > 45:
                    self.position.close()
                    
            elif self.position.is_short:
                # Exit conditions for short
                mfi_exit = mfi <= self.mfi_exit_short  # MFI reaches oversold
                price_target = price <= s1  # Reached first target
                mfi_divergence_exit = self.bullish_divergence and mfi < 40
                
                if mfi_exit or (price_target and mfi < 50) or mfi_divergence_exit:
                    self.position.close()
                    
                # Exit if MFI is falling strongly
                elif mfi < 55:
                    self.position.close()

def main():
    """Run strategy on all data sources using multi-data tester"""
    print("\n" + "="*80)
    print("🌙 MOON DEV'S CAMARILLA PIVOT - MONEY FLOW INDEX STRATEGY")
    print("="*80)
    print("Testing Camarilla Pivot with MFI across all datasets...")
    print("Using MFI for oversold/overbought confirmation and divergences")
    print("="*80)
    
    # Use the multi-data tester
    results = test_on_all_data(
        CamarillaPivotMFI, 
        'CamarillaPivotMFI',
        optimize=False,  # No optimization for speed
        verbose=True
    )
    
    if results is not None:
        print("\n✅ Camarilla Pivot MFI testing complete!")
        print(f"Results saved to: ./results/CamarillaPivotMFI.csv")

if __name__ == "__main__":
    main()