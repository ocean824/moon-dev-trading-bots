"""
Zero-lag TEMA + MFI Filter Strategy
====================================
Combines Zero-lag TEMA crossovers with Money Flow Index (MFI) filter.
Uses MFI to avoid overbought/oversold extremes.

Strategy Rules:
- Long only when: TEMA bullish cross AND MFI < 80 (not overbought)
- Short only when: TEMA bearish cross AND MFI > 20 (not oversold)
- Exit on opposite signal or MFI extremes (>80 for longs, <20 for shorts)
- 2% stop loss, 4% take profit
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

class ZeroLagTEMAMFIStrategy(Strategy):
    """
    Zero-lag TEMA + MFI Filter Strategy
    Fast period: 22, Slow period: 144
    MFI period: 14, Overbought: 80, Oversold: 20
    """
    
    # TEMA parameters
    fast_period = 22
    slow_period = 144
    
    # MFI parameters
    mfi_period = 14
    mfi_overbought = 80
    mfi_oversold = 20
    
    # Risk management
    stop_loss = 0.02  # 2%
    take_profit = 0.04  # 4%
    
    def init(self):
        """Initialize indicators using pandas_ta"""
        
        # Calculate Zero-lag TEMA for fast period
        close_series = pd.Series(self.data.Close)
        high_series = pd.Series(self.data.High)
        low_series = pd.Series(self.data.Low)
        volume_series = pd.Series(self.data.Volume)
        
        # Fast Zero-lag TEMA
        # First calculate regular TEMA components
        ema1_fast = ta.ema(close_series, length=self.fast_period)
        ema2_fast = ta.ema(ema1_fast, length=self.fast_period)
        ema3_fast = ta.ema(ema2_fast, length=self.fast_period)
        
        # Apply zero-lag formula: 3*(EMA1-EMA2)+EMA3
        zl_tema_fast_raw = 3 * (ema1_fast - ema2_fast) + ema3_fast
        
        # Apply the formula again for true zero-lag
        ema1_zl_fast = ta.ema(zl_tema_fast_raw, length=self.fast_period)
        ema2_zl_fast = ta.ema(ema1_zl_fast, length=self.fast_period)
        ema3_zl_fast = ta.ema(ema2_zl_fast, length=self.fast_period)
        self.zl_tema_fast = self.I(lambda: 3 * (ema1_zl_fast - ema2_zl_fast) + ema3_zl_fast, name='ZL_TEMA_Fast')
        
        # Slow Zero-lag TEMA
        # First calculate regular TEMA components
        ema1_slow = ta.ema(close_series, length=self.slow_period)
        ema2_slow = ta.ema(ema1_slow, length=self.slow_period)
        ema3_slow = ta.ema(ema2_slow, length=self.slow_period)
        
        # Apply zero-lag formula: 3*(EMA1-EMA2)+EMA3
        zl_tema_slow_raw = 3 * (ema1_slow - ema2_slow) + ema3_slow
        
        # Apply the formula again for true zero-lag
        ema1_zl_slow = ta.ema(zl_tema_slow_raw, length=self.slow_period)
        ema2_zl_slow = ta.ema(ema1_zl_slow, length=self.slow_period)
        ema3_zl_slow = ta.ema(ema2_zl_slow, length=self.slow_period)
        self.zl_tema_slow = self.I(lambda: 3 * (ema1_zl_slow - ema2_zl_slow) + ema3_zl_slow, name='ZL_TEMA_Slow')
        
        # Calculate MFI (Money Flow Index)
        mfi_result = ta.mfi(high_series, low_series, close_series, volume_series, length=self.mfi_period)
        if mfi_result is not None and not mfi_result.empty:
            self.mfi = self.I(lambda: mfi_result, name='MFI')
        else:
            # Fallback if pandas_ta MFI doesn't work
            self.mfi = self.I(lambda: np.full(len(close_series), 50), name='MFI')  # Default to neutral 50
        
        # Track entry prices for stop loss and take profit
        self.entry_price = None
        
    def next(self):
        """Execute trading logic with MFI filter"""
        
        # Skip if not enough data
        if len(self.data) < max(self.slow_period * 3, self.mfi_period * 2):
            return
            
        # Skip if NaN values in key indicators
        if (pd.isna(self.zl_tema_fast[-1]) or pd.isna(self.zl_tema_slow[-1]) or
            pd.isna(self.mfi[-1])):
            return
        
        current_price = self.data.Close[-1]
        current_mfi = self.mfi[-1]
        
        # Check for existing position
        if self.position:
            # Long position exit conditions
            if self.position.is_long:
                # Take profit
                if self.entry_price and current_price >= self.entry_price * (1 + self.take_profit):
                    self.position.close()
                    self.entry_price = None
                # Stop loss
                elif self.entry_price and current_price <= self.entry_price * (1 - self.stop_loss):
                    self.position.close()
                    self.entry_price = None
                # Exit on bearish crossover
                elif crossover(self.zl_tema_slow, self.zl_tema_fast):
                    self.position.close()
                    self.entry_price = None
                # Exit on MFI extreme overbought (>80)
                elif current_mfi > self.mfi_overbought:
                    self.position.close()
                    self.entry_price = None
                    
            # Short position exit conditions
            elif self.position.is_short:
                # Take profit
                if self.entry_price and current_price <= self.entry_price * (1 - self.take_profit):
                    self.position.close()
                    self.entry_price = None
                # Stop loss
                elif self.entry_price and current_price >= self.entry_price * (1 + self.stop_loss):
                    self.position.close()
                    self.entry_price = None
                # Exit on bullish crossover
                elif crossover(self.zl_tema_fast, self.zl_tema_slow):
                    self.position.close()
                    self.entry_price = None
                # Exit on MFI extreme oversold (<20)
                elif current_mfi < self.mfi_oversold:
                    self.position.close()
                    self.entry_price = None
        
        # Entry signals with MFI filter
        else:
            # Long entry: Fast TEMA crosses above Slow TEMA + MFI filter
            if crossover(self.zl_tema_fast, self.zl_tema_slow):
                # Only enter long if MFI is not overbought (< 80)
                if current_mfi < self.mfi_overbought:
                    self.buy()
                    self.entry_price = current_price
                
            # Short entry: Fast TEMA crosses below Slow TEMA + MFI filter
            elif crossover(self.zl_tema_slow, self.zl_tema_fast):
                # Only enter short if MFI is not oversold (> 20)
                if current_mfi > self.mfi_oversold:
                    self.sell()
                    self.entry_price = current_price


# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ZERO-LAG TEMA + MFI FILTER STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from multi_data_tester import test_on_all_data
    
    # Run tests on all data sources
    results = test_on_all_data(ZeroLagTEMAMFIStrategy, 'ZeroLagTEMAMFIStrategy')
    
    if results is not None:
        print("\n" + "="*80)
        print("STRATEGY TESTING COMPLETE")
        print("="*80)
        print(f"\nResults saved to: ./results/ZeroLagTEMAMFIStrategy.csv")
        
        # Display summary statistics
        print("\nSUMMARY STATISTICS:")
        print("-" * 40)
        
        if not results.empty:
            avg_return = results['Return_%'].mean()
            avg_sharpe = results['Sharpe'].mean()
            avg_sortino = results['Sortino'].mean()
            avg_max_dd = results['Max_DD_%'].mean()
            avg_win_rate = results['Win_Rate_%'].mean()
            profitable_sources = (results['Return_%'] > 0).sum()
            total_sources = len(results)
            
            print(f"Average Return: {avg_return:.2f}%")
            print(f"Average Sharpe Ratio: {avg_sharpe:.3f}")
            print(f"Average Sortino Ratio: {avg_sortino:.3f}")
            print(f"Average Max Drawdown: {avg_max_dd:.2f}%")
            print(f"Average Win Rate: {avg_win_rate:.1f}%")
            print(f"Profitable on {profitable_sources}/{total_sources} data sources ({profitable_sources/total_sources*100:.1f}%)")
            
            # Best and worst performing data sources
            best_source = results.loc[results['Return_%'].idxmax()]
            worst_source = results.loc[results['Return_%'].idxmin()]
            
            print(f"\nBest Performance: {best_source['Data_Source']} with {best_source['Return_%']:.2f}% return")
            print(f"Worst Performance: {worst_source['Data_Source']} with {worst_source['Return_%']:.2f}% return")