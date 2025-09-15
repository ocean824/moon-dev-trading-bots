"""
Moon Dev's Bollinger Breakout with MACD Confirmation Strategy
==============================================================
Bollinger Band breakout with MACD momentum confirmation
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class BollingerBreakoutMACDStrategy(Strategy):
    """
    Bollinger Band Breakout with MACD Confirmation
    - Uses 21-period BB with 2.7 std dev
    - MACD must be above signal for long entries
    - Long when price closes above upper band with MACD confirmation
    - Exit when price closes below middle band
    """
    
    # Bollinger Band parameters
    bb_period = 21
    bb_std = 2.7
    
    # MACD parameters
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Calculate Bollinger Bands
        bb_result = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        
        # Extract bands
        upper_col = f'BBU_{self.bb_period}_{self.bb_std}'
        middle_col = f'BBM_{self.bb_period}_{self.bb_std}'
        lower_col = f'BBL_{self.bb_period}_{self.bb_std}'
        
        self.bb_upper = self.I(lambda: bb_result[upper_col].ffill().values, name='BB_Upper')
        self.bb_middle = self.I(lambda: bb_result[middle_col].ffill().values, name='BB_Middle')
        self.bb_lower = self.I(lambda: bb_result[lower_col].ffill().values, name='BB_Lower')
        
        # Calculate MACD
        macd_result = ta.macd(close, fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)
        self.macd = self.I(lambda: macd_result[f'MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'].ffill().values, name='MACD')
        self.macd_signal = self.I(lambda: macd_result[f'MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'].ffill().values, name='MACD_Signal')
        
        # ATR for risk management
        self.atr = self.I(ta.atr, high, low, close, 14)
        
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.bb_period, self.macd_slow) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        upper_band = self.bb_upper[-1]
        middle_band = self.bb_middle[-1]
        lower_band = self.bb_lower[-1]
        macd_value = self.macd[-1]
        signal_value = self.macd_signal[-1]
        atr_value = self.atr[-1]
        
        # Previous values for crossover detection
        if len(self.data.Close) > 1:
            prev_close = self.data.Close[-2]
            prev_upper = self.bb_upper[-2]
            prev_lower = self.bb_lower[-2]
            prev_macd = self.macd[-2]
            prev_signal = self.macd_signal[-2]
        else:
            return
        
        # Check for valid values
        if pd.isna(upper_band) or pd.isna(middle_band) or pd.isna(macd_value) or pd.isna(signal_value) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # MACD conditions
        macd_bullish = macd_value > signal_value
        macd_bearish = macd_value < signal_value
        macd_cross_up = (prev_macd <= prev_signal) and (macd_value > signal_value)
        macd_cross_down = (prev_macd >= prev_signal) and (macd_value < signal_value)
        
        # Entry logic
        if not self.position:
            # Long signal: Price breaks above upper band with MACD confirmation
            if (prev_close <= prev_upper and price > upper_band and macd_bullish):
                stop_loss = price - (atr_value * 2.0)
                self.buy(sl=stop_loss, size=0.95)
            
            # Short signal: Price breaks below lower band with MACD confirmation
            elif (prev_close >= prev_lower and price < lower_band and macd_bearish):
                stop_loss = price + (atr_value * 2.0)
                self.sell(sl=stop_loss, size=0.95)
        
        # Exit logic
        else:
            # Exit long when price crosses below middle band
            if self.position.is_long:
                if price < middle_band:
                    self.position.close()
                # Also exit on MACD bearish crossover
                elif macd_cross_down:
                    self.position.close()
            
            # Exit short when price crosses above middle band
            elif self.position.is_short:
                if price > middle_band:
                    self.position.close()
                # Also exit on MACD bullish crossover
                elif macd_cross_up:
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S BOLLINGER BREAKOUT MACD STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Bollinger Breakout with MACD Confirmation across all datasets...")
    print("="*80)
    
    # Run tests on all data sources without optimization
    results = test_on_all_data(
        BollingerBreakoutMACDStrategy,
        'BollingerBreakoutMACD',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/BollingerBreakoutMACD.csv")
        print("="*80)

if __name__ == "__main__":
    main()