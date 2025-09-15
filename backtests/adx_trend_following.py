"""
Moon Dev's ADX Trend Following Strategy
========================================
Uses ADX to identify strong trends, enters long when ADX > 25 and DI+ > DI-, 
short when opposite. Follows trends with trailing stops.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class ADXTrendFollowingStrategy(Strategy):
    """
    ADX Trend Following Strategy
    - Uses ADX to measure trend strength (> 25 = strong trend)
    - DI+ > DI- indicates uptrend, DI- > DI+ indicates downtrend
    - Enters positions only in strong trends
    - Uses ATR-based trailing stops to ride trends
    """
    
    # ADX parameters
    adx_period = 14
    adx_threshold = 25  # Minimum ADX for trend strength
    adx_exit_threshold = 20  # Exit when ADX falls below this
    
    # DI crossover parameters
    di_diff_threshold = 5  # Minimum difference between DI+ and DI-
    
    # Risk management
    atr_period = 14
    atr_stop_multiplier = 2.5
    atr_trail_multiplier = 3.0
    
    def init(self):
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        
        # Calculate ADX and DI indicators
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        
        # Extract ADX and DI values
        self.adx = self.I(lambda: adx_result[f'ADX_{self.adx_period}'].ffill().values, name='ADX')
        self.di_plus = self.I(lambda: adx_result[f'DMP_{self.adx_period}'].ffill().values, name='DI_Plus')
        self.di_minus = self.I(lambda: adx_result[f'DMN_{self.adx_period}'].ffill().values, name='DI_Minus')
        
        # ATR for risk management
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # EMA for trend confirmation (optional)
        self.ema_fast = self.I(ta.ema, close, 20)
        self.ema_slow = self.I(ta.ema, close, 50)
        
        # Keep track of highest/lowest prices for trailing stops
        self.highest_price = 0
        self.lowest_price = float('inf')
        
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.adx_period, 50) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        adx_value = self.adx[-1]
        di_plus_value = self.di_plus[-1]
        di_minus_value = self.di_minus[-1]
        atr_value = self.atr[-1]
        ema_fast_value = self.ema_fast[-1]
        ema_slow_value = self.ema_slow[-1]
        
        # Check for valid values
        if pd.isna(adx_value) or pd.isna(di_plus_value) or pd.isna(di_minus_value) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Calculate DI difference
        di_diff = di_plus_value - di_minus_value
        
        # Get previous values for crossover detection
        if len(self.data.Close) > 1:
            prev_adx = self.adx[-2]
            prev_di_plus = self.di_plus[-2]
            prev_di_minus = self.di_minus[-2]
        else:
            return
        
        # Entry logic - Trend Following
        if not self.position:
            # Reset tracking variables
            self.highest_price = 0
            self.lowest_price = float('inf')
            
            # Long signal: Strong uptrend
            # ADX > threshold indicates strong trend
            # DI+ > DI- indicates uptrend direction
            # Optional: EMA fast > slow for additional confirmation
            if (adx_value > self.adx_threshold and 
                di_plus_value > di_minus_value and 
                di_diff > self.di_diff_threshold and
                (pd.isna(ema_fast_value) or pd.isna(ema_slow_value) or ema_fast_value > ema_slow_value)):
                
                # Initial stop loss
                stop_loss = price - (atr_value * self.atr_stop_multiplier)
                
                # Enter long position
                self.buy(sl=stop_loss, size=0.95)
                self.highest_price = price
            
            # Short signal: Strong downtrend
            # ADX > threshold indicates strong trend
            # DI- > DI+ indicates downtrend direction
            # Optional: EMA fast < slow for additional confirmation
            elif (adx_value > self.adx_threshold and 
                  di_minus_value > di_plus_value and 
                  abs(di_diff) > self.di_diff_threshold and
                  (pd.isna(ema_fast_value) or pd.isna(ema_slow_value) or ema_fast_value < ema_slow_value)):
                
                # Initial stop loss
                stop_loss = price + (atr_value * self.atr_stop_multiplier)
                
                # Enter short position
                self.sell(sl=stop_loss, size=0.95)
                self.lowest_price = price
        
        # Exit and trailing stop logic
        else:
            # For long positions
            if self.position.is_long:
                # Update highest price
                if price > self.highest_price:
                    self.highest_price = price
                
                # Exit conditions:
                # 1. Trend weakening: ADX falls below exit threshold
                # 2. Trend reversal: DI- crosses above DI+
                # 3. Trailing stop hit: Price falls below trailing stop
                
                # Calculate trailing stop
                trailing_stop = self.highest_price - (atr_value * self.atr_trail_multiplier)
                
                if (adx_value < self.adx_exit_threshold or 
                    di_minus_value > di_plus_value or 
                    price < trailing_stop):
                    self.position.close()
            
            # For short positions
            elif self.position.is_short:
                # Update lowest price
                if price < self.lowest_price:
                    self.lowest_price = price
                
                # Exit conditions:
                # 1. Trend weakening: ADX falls below exit threshold
                # 2. Trend reversal: DI+ crosses above DI-
                # 3. Trailing stop hit: Price rises above trailing stop
                
                # Calculate trailing stop
                trailing_stop = self.lowest_price + (atr_value * self.atr_trail_multiplier)
                
                if (adx_value < self.adx_exit_threshold or 
                    di_plus_value > di_minus_value or 
                    price > trailing_stop):
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S ADX TREND FOLLOWING STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing ADX Trend Following across all datasets...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        ADXTrendFollowingStrategy,
        'ADXTrendFollowing',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/ADXTrendFollowing.csv")
        print("="*80)

if __name__ == "__main__":
    main()