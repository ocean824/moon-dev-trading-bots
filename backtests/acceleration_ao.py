"""
Moon Dev's Acceleration AO Strategy
====================================
Uses Awesome Oscillator for momentum acceleration signals
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class AccelerationAOStrategy(Strategy):
    """
    Momentum Acceleration Indicator (AO) Strategy
    - Calculate AO as difference between 5-period and 34-period SMA
    - Long when AO crosses above zero
    - Short when AO crosses below zero
    - Include volume confirmation
    - Use trailing stops
    """
    
    # AO parameters
    fast_period = 5
    slow_period = 34
    
    # Volume parameters
    volume_period = 20
    volume_multiplier = 1.2  # Volume must be 20% above average
    
    # Risk management
    atr_period = 14
    atr_sl_multiplier = 2.0
    trailing_stop_pct = 0.02  # 2% trailing stop
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Calculate Awesome Oscillator
        # AO = SMA(median price, 5) - SMA(median price, 34)
        median_price = (high + low) / 2
        
        fast_sma = ta.sma(median_price, self.fast_period)
        slow_sma = ta.sma(median_price, self.slow_period)
        ao = fast_sma - slow_sma
        
        self.ao = self.I(lambda: ao.values, name='AO')
        
        # Previous AO for crossover detection
        ao_prev = ao.shift(1)
        self.ao_prev = self.I(lambda: ao_prev.values, name='AO_Prev')
        
        # Volume average for confirmation
        self.volume_avg = self.I(ta.sma, volume, self.volume_period)
        
        # Volume spike detection
        volume_avg_series = ta.sma(volume, self.volume_period)
        volume_spike = volume / volume_avg_series > self.volume_multiplier
        self.volume_spike = self.I(lambda: volume_spike.values, name='VolumeSpike')
        
        # ATR for stops
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # Track highest/lowest prices for trailing stops
        self.highest_price = 0
        self.lowest_price = float('inf')
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.slow_period, self.volume_period, self.atr_period) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        ao_current = self.ao[-1]
        ao_previous = self.ao_prev[-1]
        volume_confirmed = self.volume_spike[-1] if not pd.isna(self.volume_spike[-1]) else False
        atr_value = self.atr[-1]
        
        # Check for valid values
        if pd.isna(ao_current) or pd.isna(ao_previous) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Detect AO crossovers
        ao_cross_above_zero = (ao_previous <= 0) and (ao_current > 0)
        ao_cross_below_zero = (ao_previous >= 0) and (ao_current < 0)
        
        # Also look for momentum acceleration (AO increasing/decreasing rapidly)
        ao_momentum_up = (ao_current > ao_previous) and (ao_current > 0) and ((ao_current - ao_previous) > abs(ao_previous) * 0.1)
        ao_momentum_down = (ao_current < ao_previous) and (ao_current < 0) and ((ao_previous - ao_current) > abs(ao_previous) * 0.1)
        
        # Long signal: AO crosses above zero with volume confirmation
        long_signal = (ao_cross_above_zero or ao_momentum_up) and volume_confirmed
        
        # Short signal: AO crosses below zero with volume confirmation  
        short_signal = (ao_cross_below_zero or ao_momentum_down) and volume_confirmed
        
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
        
        # Implement trailing stops
        if self.position:
            if self.position.is_long:
                # Update highest price
                if price > self.highest_price:
                    self.highest_price = price
                
                # Check trailing stop
                trailing_stop = self.highest_price * (1 - self.trailing_stop_pct)
                if price < trailing_stop:
                    self.position.close()
                
                # Also exit if AO turns negative
                if ao_current < 0:
                    self.position.close()
            
            elif self.position.is_short:
                # Update lowest price
                if price < self.lowest_price:
                    self.lowest_price = price
                
                # Check trailing stop
                trailing_stop = self.lowest_price * (1 + self.trailing_stop_pct)
                if price > trailing_stop:
                    self.position.close()
                
                # Also exit if AO turns positive
                if ao_current > 0:
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S ACCELERATION AO STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Awesome Oscillator Strategy across all datasets...")
    print("="*80)
    
    # Run tests on all data sources without optimization
    results = test_on_all_data(
        AccelerationAOStrategy,
        'AccelerationAO',
        optimize=False,  # No optimization as requested
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/AccelerationAO.csv")
        print("="*80)

if __name__ == "__main__":
    main()