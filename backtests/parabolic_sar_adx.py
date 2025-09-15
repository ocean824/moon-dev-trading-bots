"""
Moon Dev's Parabolic SAR with ADX Filter Strategy
==================================================
Parabolic SAR strategy with ADX trend strength filter
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class ParabolicSARADXStrategy(Strategy):
    """
    Parabolic SAR with ADX Filter Strategy
    - Uses standard SAR settings (Start=0.02, Increment=0.02, Maximum=0.2)
    - Only trades when ADX > 25 (strong trend)
    - Long when SAR below price and ADX > 25
    - Short when SAR above price and ADX > 25
    - Exit positions when ADX drops below 25
    """
    
    # SAR parameters (standard settings)
    sar_start = 0.02
    sar_increment = 0.02
    sar_maximum = 0.2
    
    # ADX parameters
    adx_period = 14
    adx_threshold = 25
    
    def init(self):
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        
        # Calculate Parabolic SAR
        psar_result = ta.psar(high, low, close, 
                              af0=self.sar_start, 
                              af=self.sar_increment, 
                              max_af=self.sar_maximum)
        
        # Combined SAR indicator
        combined_sar = psar_result['PSARl_0.02_0.2'].fillna(psar_result['PSARs_0.02_0.2'])
        self.sar = self.I(lambda: combined_sar.values, name='SAR')
        
        # Previous SAR for crossover detection
        self.sar_prev = self.I(lambda: combined_sar.shift(1).values, name='SAR_Prev')
        
        # Calculate ADX for trend strength
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        self.adx = self.I(lambda: adx_result[f'ADX_{self.adx_period}'].values, name='ADX')
        self.plus_di = self.I(lambda: adx_result[f'DMP_{self.adx_period}'].values, name='+DI')
        self.minus_di = self.I(lambda: adx_result[f'DMN_{self.adx_period}'].values, name='-DI')
        
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < self.adx_period + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        sar_curr = self.sar[-1]
        sar_prev = self.sar_prev[-1]
        adx_value = self.adx[-1]
        plus_di = self.plus_di[-1]
        minus_di = self.minus_di[-1]
        
        # Check for valid values
        if pd.isna(sar_curr) or pd.isna(sar_prev) or pd.isna(adx_value):
            return
        
        # Determine SAR position and trend strength
        sar_below_price = sar_curr < price
        strong_trend = adx_value > self.adx_threshold
        
        # Exit if trend becomes weak
        if self.position and not strong_trend:
            self.position.close()
            return
        
        # Only trade in strong trends
        if strong_trend:
            # Long signal: SAR below price and strong uptrend
            if sar_below_price and plus_di > minus_di:
                if self.position and self.position.is_short:
                    self.position.close()
                    self.buy(size=0.95)
                elif not self.position:
                    self.buy(size=0.95)
            
            # Short signal: SAR above price and strong downtrend
            elif not sar_below_price and minus_di > plus_di:
                if self.position and self.position.is_long:
                    self.position.close()
                    self.sell(size=0.95)
                elif not self.position:
                    self.sell(size=0.95)
            
            # Exit if SAR flips but trend direction unclear
            elif self.position:
                if (self.position.is_long and not sar_below_price) or \
                   (self.position.is_short and sar_below_price):
                    self.position.close()

def main():
    """Run backtest on all data sources"""
    print("\n" + "="*80)
    print("MOON DEV'S PARABOLIC SAR WITH ADX FILTER STRATEGY")
    print("="*80)
    print("Testing on all available data sources...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        ParabolicSARADXStrategy,
        'ParabolicSARADX',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("STRATEGY COMPLETE!")
        print("="*80)
        print(f"Total tests run: {len(results)}")
        print(f"Average Return: {results['Return_%'].mean():.2f}%")
        print(f"Average Sharpe: {results['Sharpe'].mean():.3f}")
        print(f"Average Max Drawdown: {results['Max_DD_%'].mean():.2f}%")
        print(f"Total Trades: {results['Trades'].sum()}")
        print("="*80)

if __name__ == "__main__":
    main()