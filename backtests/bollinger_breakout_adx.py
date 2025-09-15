"""
Moon Dev's Bollinger Breakout with ADX Filter Strategy
========================================================
Bollinger Band breakout with ADX trend strength filter
Only trades when trend is strong (ADX > 25)
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class BollingerBreakoutADXStrategy(Strategy):
    """
    Bollinger Band Breakout with ADX Filter
    - Uses 21-period BB with 2.7 std dev
    - ADX > 25 required for trend strength
    - Long when price closes above upper band with strong trend
    - Exit when price closes below middle band
    """
    
    # Bollinger Band parameters
    bb_period = 21
    bb_std = 2.7
    
    # ADX parameters
    adx_period = 14
    adx_threshold = 25
    
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
        
        # Calculate ADX for trend strength
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        self.adx = self.I(lambda: adx_result[f'ADX_{self.adx_period}'].ffill().values, name='ADX')
        self.plus_di = self.I(lambda: adx_result[f'DMP_{self.adx_period}'].ffill().values, name='+DI')
        self.minus_di = self.I(lambda: adx_result[f'DMN_{self.adx_period}'].ffill().values, name='-DI')
        
        # ATR for risk management
        self.atr = self.I(ta.atr, high, low, close, 14)
        
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.bb_period, self.adx_period) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        upper_band = self.bb_upper[-1]
        middle_band = self.bb_middle[-1]
        lower_band = self.bb_lower[-1]
        adx_value = self.adx[-1]
        plus_di = self.plus_di[-1]
        minus_di = self.minus_di[-1]
        atr_value = self.atr[-1]
        
        # Previous values for crossover detection
        if len(self.data.Close) > 1:
            prev_close = self.data.Close[-2]
            prev_upper = self.bb_upper[-2]
            prev_lower = self.bb_lower[-2]
        else:
            return
        
        # Check for valid values
        if pd.isna(upper_band) or pd.isna(middle_band) or pd.isna(adx_value) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Check trend strength - ADX must be above threshold
        strong_trend = adx_value > self.adx_threshold
        
        # Entry logic
        if not self.position:
            # Long signal: Price breaks above upper band with strong trend
            if (prev_close <= prev_upper and price > upper_band and 
                strong_trend and plus_di > minus_di):
                stop_loss = price - (atr_value * 2.0)
                self.buy(sl=stop_loss, size=0.95)
            
            # Short signal: Price breaks below lower band with strong trend
            elif (prev_close >= prev_lower and price < lower_band and 
                  strong_trend and minus_di > plus_di):
                stop_loss = price + (atr_value * 2.0)
                self.sell(sl=stop_loss, size=0.95)
        
        # Exit logic
        else:
            # Exit long when price crosses below middle band
            if self.position.is_long and price < middle_band:
                self.position.close()
            
            # Exit short when price crosses above middle band
            elif self.position.is_short and price > middle_band:
                self.position.close()
            
            # Also exit if trend weakens significantly
            if adx_value < 20:
                self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S BOLLINGER BREAKOUT ADX STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Bollinger Breakout with ADX Filter across all datasets...")
    print("="*80)
    
    # Run tests on all data sources without optimization
    results = test_on_all_data(
        BollingerBreakoutADXStrategy,
        'BollingerBreakoutADX',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/BollingerBreakoutADX.csv")
        print("="*80)

if __name__ == "__main__":
    main()