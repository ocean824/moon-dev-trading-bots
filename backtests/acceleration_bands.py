"""
Moon Dev's Acceleration Bands Strategy
======================================
Uses acceleration bands with MA and ATR to identify breakout opportunities
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class AccelerationBandsStrategy(Strategy):
    """
    Acceleration Bands Strategy
    - Calculates bands using 20-period MA and 20-period ATR
    - Long when price breaks above upper band
    - Short when price breaks below lower band
    - Stop-loss within the bands
    - Profit targets based on ATR multiples
    """
    
    # Band parameters
    ma_period = 20
    atr_period = 20
    band_multiplier = 2.0  # ATR multiplier for band width
    
    # Risk management
    atr_sl_multiplier = 1.5  # Stop loss ATR multiplier
    atr_tp_multiplier = 3.0  # Take profit ATR multiplier
    
    # Confirmation parameters
    min_breakout_strength = 0.001  # Minimum breakout percentage
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Calculate MA (middle band)
        self.ma = self.I(ta.sma, close, self.ma_period)
        
        # Calculate ATR for band width
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # Calculate acceleration bands
        # Upper band = MA + (ATR * multiplier)
        # Lower band = MA - (ATR * multiplier)
        ma_series = ta.sma(close, self.ma_period)
        atr_series = ta.atr(high, low, close, self.atr_period)
        
        upper_band = ma_series + (atr_series * self.band_multiplier)
        lower_band = ma_series - (atr_series * self.band_multiplier)
        
        self.upper_band = self.I(lambda: upper_band.values, name='UpperBand')
        self.lower_band = self.I(lambda: lower_band.values, name='LowerBand')
        
        # Track breakout strength
        breakout_up = (close - upper_band) / upper_band
        breakout_down = (lower_band - close) / lower_band
        
        self.breakout_up = self.I(lambda: breakout_up.values, name='BreakoutUp')
        self.breakout_down = self.I(lambda: breakout_down.values, name='BreakoutDown')
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.ma_period, self.atr_period) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        upper = self.upper_band[-1]
        lower = self.lower_band[-1]
        atr_value = self.atr[-1]
        
        # Check for valid values
        if pd.isna(upper) or pd.isna(lower) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Get breakout strength
        breakout_up_strength = self.breakout_up[-1] if not pd.isna(self.breakout_up[-1]) else 0
        breakout_down_strength = self.breakout_down[-1] if not pd.isna(self.breakout_down[-1]) else 0
        
        # Long signal: Price breaks above upper band with strength
        long_signal = (price > upper) and (breakout_up_strength > self.min_breakout_strength)
        
        # Short signal: Price breaks below lower band with strength
        short_signal = (price < lower) and (breakout_down_strength > self.min_breakout_strength)
        
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
        
        # Exit if price returns within bands
        elif self.position:
            if self.position.is_long and price < upper:
                self.position.close()
            elif self.position.is_short and price > lower:
                self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S ACCELERATION BANDS STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Acceleration Bands Strategy across all datasets...")
    print("="*80)
    
    # Run tests on all data sources without optimization
    results = test_on_all_data(
        AccelerationBandsStrategy,
        'AccelerationBands',
        optimize=False,  # No optimization as requested
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/AccelerationBands.csv")
        print("="*80)

if __name__ == "__main__":
    main()