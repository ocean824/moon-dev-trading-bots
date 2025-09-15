"""
Moon Dev's Parabolic SAR with MFI Confirmation Strategy
========================================================
Parabolic SAR strategy with Money Flow Index confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class ParabolicSARMFIStrategy(Strategy):
    """
    Parabolic SAR with MFI Confirmation Strategy
    - Uses standard SAR settings (Start=0.02, Increment=0.02, Maximum=0.2)
    - MFI < 30 confirms oversold for long entries
    - MFI > 70 confirms overbought for short entries
    - Combines trend (SAR) with momentum (MFI) for better entries
    """
    
    # SAR parameters (standard settings)
    sar_start = 0.02
    sar_increment = 0.02
    sar_maximum = 0.2
    
    # MFI parameters
    mfi_period = 14
    mfi_oversold = 30
    mfi_overbought = 70
    
    def init(self):
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)
        
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
        
        # Calculate MFI (Money Flow Index)
        mfi = ta.mfi(high, low, close, volume, length=self.mfi_period)
        self.mfi = self.I(lambda: mfi.values, name='MFI')
        
        # Track recent MFI extremes
        mfi_rolling_min = mfi.rolling(window=5).min()
        mfi_rolling_max = mfi.rolling(window=5).max()
        self.mfi_recent_low = self.I(lambda: mfi_rolling_min.values, name='MFI_Recent_Low')
        self.mfi_recent_high = self.I(lambda: mfi_rolling_max.values, name='MFI_Recent_High')
        
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < self.mfi_period + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        sar_curr = self.sar[-1]
        sar_prev = self.sar_prev[-1]
        mfi_value = self.mfi[-1]
        mfi_low = self.mfi_recent_low[-1]
        mfi_high = self.mfi_recent_high[-1]
        
        # Check for valid values
        if pd.isna(sar_curr) or pd.isna(sar_prev) or pd.isna(mfi_value):
            return
        
        # Determine SAR position and MFI conditions
        sar_below_price = sar_curr < price
        prev_price = self.data.Close[-2] if len(self.data.Close) > 1 else price
        sar_was_above = sar_prev > prev_price
        sar_was_below = sar_prev < prev_price
        
        # MFI conditions
        oversold_confirmed = mfi_value < self.mfi_oversold or mfi_low < self.mfi_oversold
        overbought_confirmed = mfi_value > self.mfi_overbought or mfi_high > self.mfi_overbought
        
        # Long entry: SAR flips below price AND oversold condition
        if not self.position and sar_below_price and sar_was_above:
            # Strong signal if MFI confirms oversold
            if oversold_confirmed:
                self.buy(size=0.95)
            # Weaker signal without MFI confirmation - use smaller size
            elif mfi_value < 50:
                self.buy(size=0.70)
        
        # Short entry: SAR flips above price AND overbought condition
        elif not self.position and not sar_below_price and sar_was_below:
            # Strong signal if MFI confirms overbought
            if overbought_confirmed:
                self.sell(size=0.95)
            # Weaker signal without MFI confirmation - use smaller size
            elif mfi_value > 50:
                self.sell(size=0.70)
        
        # Exit management
        elif self.position:
            # Exit long if SAR flips or MFI becomes overbought
            if self.position.is_long:
                if not sar_below_price or mfi_value > self.mfi_overbought + 5:
                    self.position.close()
            
            # Exit short if SAR flips or MFI becomes oversold
            elif self.position.is_short:
                if sar_below_price or mfi_value < self.mfi_oversold - 5:
                    self.position.close()

def main():
    """Run backtest on all data sources"""
    print("\n" + "="*80)
    print("MOON DEV'S PARABOLIC SAR WITH MFI CONFIRMATION STRATEGY")
    print("="*80)
    print("Testing on all available data sources...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        ParabolicSARMFIStrategy,
        'ParabolicSARMFI',
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