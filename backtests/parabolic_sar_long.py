"""
Moon Dev's Parabolic SAR Long Only Strategy
============================================
Long-only trend following strategy using Parabolic SAR
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class ParabolicSARLongStrategy(Strategy):
    """
    Parabolic SAR Long Only Strategy
    - Uses standard SAR settings (Start=0.02, Increment=0.02, Maximum=0.2)
    - Long entry when SAR flips from above to below price
    - Exit when SAR flips from below to above price
    - No short positions - cash only when not long
    """
    
    # SAR parameters (standard settings)
    sar_start = 0.02
    sar_increment = 0.02
    sar_maximum = 0.2
    
    def init(self):
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        
        # Calculate Parabolic SAR
        psar_result = ta.psar(high, low, close, 
                              af0=self.sar_start, 
                              af=self.sar_increment, 
                              max_af=self.sar_maximum)
        
        # Extract long and short SAR values
        self.sar_long = self.I(lambda: psar_result['PSARl_0.02_0.2'].values, name='SAR_Long')
        self.sar_short = self.I(lambda: psar_result['PSARs_0.02_0.2'].values, name='SAR_Short')
        
        # Combined SAR indicator (use whichever is not NaN)
        combined_sar = psar_result['PSARl_0.02_0.2'].fillna(psar_result['PSARs_0.02_0.2'])
        self.sar = self.I(lambda: combined_sar.values, name='SAR')
        
        # Previous SAR for crossover detection
        self.sar_prev = self.I(lambda: combined_sar.shift(1).values, name='SAR_Prev')
        
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < 10:
            return
        
        # Get current values
        price = self.data.Close[-1]
        sar_curr = self.sar[-1]
        sar_prev = self.sar_prev[-1]
        
        # Check for valid values
        if pd.isna(sar_curr) or pd.isna(sar_prev):
            return
        
        # Determine SAR position relative to price
        sar_below_price = sar_curr < price
        sar_was_above_price = sar_prev > self.data.Close[-2] if len(self.data.Close) > 1 else False
        
        # Long entry signal: SAR flips from above to below price
        if not self.position and sar_below_price and sar_was_above_price:
            # Enter long position with 95% of equity
            self.buy(size=0.95)
        
        # Exit signal: SAR flips from below to above price
        elif self.position and not sar_below_price:
            # Exit long position
            self.position.close()

def main():
    """Run backtest on all data sources"""
    print("\n" + "="*80)
    print("MOON DEV'S PARABOLIC SAR LONG ONLY STRATEGY")
    print("="*80)
    print("Testing on all available data sources...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        ParabolicSARLongStrategy,
        'ParabolicSARLong',
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