"""
Moon Dev's Momentum Cross Triple EMA Strategy
==============================================
Triple EMA Crossover Strategy with ATR-based stops
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class MomentumCrossTripleEMAStrategy(Strategy):
    """
    Triple EMA Crossover Strategy
    - Uses 50, 100, and 200 period EMAs
    - Long when 50 EMA crosses above 100 EMA (bullish trend)
    - Extra confirmation when 100 EMA crosses above 200 EMA
    - Short when opposite crossovers occur
    - ATR-based stops for risk management
    """
    
    # EMA parameters
    ema_fast = 50
    ema_medium = 100
    ema_slow = 200
    
    # Risk management
    atr_period = 14
    atr_sl_multiplier = 2.0
    trailing_stop_pct = 0.025  # 2.5% trailing stop
    
    # Volume confirmation
    volume_period = 20
    volume_multiplier = 1.2
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Calculate EMAs
        ema_50 = ta.ema(close, self.ema_fast)
        ema_100 = ta.ema(close, self.ema_medium)
        ema_200 = ta.ema(close, self.ema_slow)
        
        self.ema_50 = self.I(lambda: ema_50.values, name='EMA_50')
        self.ema_100 = self.I(lambda: ema_100.values, name='EMA_100')
        self.ema_200 = self.I(lambda: ema_200.values, name='EMA_200')
        
        # Previous values for crossover detection
        ema_50_prev = ema_50.shift(1)
        ema_100_prev = ema_100.shift(1)
        ema_200_prev = ema_200.shift(1)
        
        self.ema_50_prev = self.I(lambda: ema_50_prev.values, name='EMA_50_Prev')
        self.ema_100_prev = self.I(lambda: ema_100_prev.values, name='EMA_100_Prev')
        self.ema_200_prev = self.I(lambda: ema_200_prev.values, name='EMA_200_Prev')
        
        # Volume average for confirmation
        volume_avg = ta.sma(volume, self.volume_period)
        self.volume_avg = self.I(lambda: volume_avg.values, name='Volume_Avg')
        
        # Volume spike detection
        volume_spike = volume / volume_avg > self.volume_multiplier
        self.volume_spike = self.I(lambda: volume_spike.values, name='Volume_Spike')
        
        # ATR for stops
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # Track highest/lowest prices for trailing stops
        self.highest_price = 0
        self.lowest_price = float('inf')
        
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < self.ema_slow + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        ema_50_curr = self.ema_50[-1]
        ema_100_curr = self.ema_100[-1]
        ema_200_curr = self.ema_200[-1]
        
        ema_50_prev = self.ema_50_prev[-1]
        ema_100_prev = self.ema_100_prev[-1]
        ema_200_prev = self.ema_200_prev[-1]
        
        volume_confirmed = self.volume_spike[-1] if not pd.isna(self.volume_spike[-1]) else False
        atr_value = self.atr[-1]
        
        # Check for valid values
        if pd.isna(ema_50_curr) or pd.isna(ema_100_curr) or pd.isna(ema_200_curr) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Primary crossover: 50 EMA crossing 100 EMA
        fast_cross_medium_up = (ema_50_prev <= ema_100_prev) and (ema_50_curr > ema_100_curr)
        fast_cross_medium_down = (ema_50_prev >= ema_100_prev) and (ema_50_curr < ema_100_curr)
        
        # Secondary crossover: 100 EMA crossing 200 EMA (trend confirmation)
        medium_cross_slow_up = (ema_100_prev <= ema_200_prev) and (ema_100_curr > ema_200_curr)
        medium_cross_slow_down = (ema_100_prev >= ema_200_prev) and (ema_100_curr < ema_200_curr)
        
        # Trend alignment: All EMAs in order
        bullish_alignment = (ema_50_curr > ema_100_curr > ema_200_curr)
        bearish_alignment = (ema_50_curr < ema_100_curr < ema_200_curr)
        
        # Price position relative to EMAs
        price_above_all = price > max(ema_50_curr, ema_100_curr, ema_200_curr)
        price_below_all = price < min(ema_50_curr, ema_100_curr, ema_200_curr)
        
        # Long signal conditions
        long_signal = (
            fast_cross_medium_up and
            (bullish_alignment or ema_100_curr > ema_200_curr) and
            (volume_confirmed or medium_cross_slow_up)
        )
        
        # Short signal conditions  
        short_signal = (
            fast_cross_medium_down and
            (bearish_alignment or ema_100_curr < ema_200_curr) and
            (volume_confirmed or medium_cross_slow_down)
        )
        
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
        
        # Implement trailing stops and momentum exits
        if self.position:
            if self.position.is_long:
                # Update highest price
                if price > self.highest_price:
                    self.highest_price = price
                
                # Check trailing stop
                trailing_stop = self.highest_price * (1 - self.trailing_stop_pct)
                if price < trailing_stop:
                    self.position.close()
                
                # Exit if 50 EMA crosses below 100 EMA (momentum loss)
                if fast_cross_medium_down:
                    self.position.close()
                
                # Exit if price drops below 100 EMA with bearish momentum
                if price < ema_100_curr and ema_50_curr < ema_100_curr:
                    self.position.close()
            
            elif self.position.is_short:
                # Update lowest price
                if price < self.lowest_price:
                    self.lowest_price = price
                
                # Check trailing stop
                trailing_stop = self.lowest_price * (1 + self.trailing_stop_pct)
                if price > trailing_stop:
                    self.position.close()
                
                # Exit if 50 EMA crosses above 100 EMA (momentum loss)
                if fast_cross_medium_up:
                    self.position.close()
                
                # Exit if price rises above 100 EMA with bullish momentum
                if price > ema_100_curr and ema_50_curr > ema_100_curr:
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S MOMENTUM CROSS TRIPLE EMA STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Triple EMA Crossover across all datasets...")
    print("="*80)
    
    # Run tests on all data sources without optimization
    results = test_on_all_data(
        MomentumCrossTripleEMAStrategy,
        'MomentumCrossTripleEMA',
        optimize=False,  # No optimization as requested
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/MomentumCrossTripleEMA.csv")
        print("="*80)

if __name__ == "__main__":
    main()