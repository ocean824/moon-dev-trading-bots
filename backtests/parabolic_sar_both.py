"""
Moon Dev's Parabolic SAR Both Directions Strategy
==================================================
Long and short trend following strategy using Parabolic SAR
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class ParabolicSARBothStrategy(Strategy):
    """
    Parabolic SAR Both Directions Strategy
    - Uses standard SAR settings (Start=0.02, Increment=0.02, Maximum=0.2)
    - Long when SAR is below price
    - Short when SAR is above price
    - Always in the market, alternating between long and short
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
        sar_was_below = sar_prev < self.data.Close[-2] if len(self.data.Close) > 1 else False
        
        # Long signal: SAR is below price (uptrend)
        if sar_below_price:
            # If currently short, close and go long
            if self.position and self.position.is_short:
                self.position.close()
                self.buy(size=0.95)
            # If not in position, enter long
            elif not self.position:
                self.buy(size=0.95)
        
        # Short signal: SAR is above price (downtrend)
        else:
            # If currently long, close and go short
            if self.position and self.position.is_long:
                self.position.close()
                self.sell(size=0.95)
            # If not in position, enter short
            elif not self.position:
                self.sell(size=0.95)

def main():
    """Run backtest on all data sources"""
    print("\n" + "="*80)
    print("MOON DEV'S PARABOLIC SAR BOTH DIRECTIONS STRATEGY")
    print("="*80)
    print("Testing on all available data sources...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        ParabolicSARBothStrategy,
        'ParabolicSARBoth',
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