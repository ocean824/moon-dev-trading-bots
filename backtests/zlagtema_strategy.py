"""
Zero-lag TEMA Crosses Strategy
==============================
Implements zero-lag Triple Exponential Moving Average (TEMA) crossover strategy.
Zero-lag TEMA formula: 3*(EMA1-EMA2)+EMA3, then apply same formula again.

Strategy Rules:
- Long entry: Fast TEMA crosses above Slow TEMA
- Short entry: Fast TEMA crosses below Slow TEMA  
- Exit on opposite signal
- 2% stop loss, 4% take profit
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

class ZeroLagTEMAStrategy(Strategy):
    """
    Zero-lag TEMA Crosses Strategy
    Fast period: 22, Slow period: 144
    """
    
    # TEMA parameters
    fast_period = 22
    slow_period = 144
    
    # Risk management
    stop_loss = 0.02  # 2%
    take_profit = 0.04  # 4%
    
    def init(self):
        """Initialize indicators using pandas_ta"""
        
        # Calculate Zero-lag TEMA for fast period
        close_series = pd.Series(self.data.Close)
        
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
        
        # Track entry prices for stop loss and take profit
        self.entry_price = None
        
    def next(self):
        """Execute trading logic"""
        
        # Skip if not enough data
        if len(self.data) < self.slow_period * 3:
            return
            
        # Skip if NaN values
        if pd.isna(self.zl_tema_fast[-1]) or pd.isna(self.zl_tema_slow[-1]):
            return
        
        current_price = self.data.Close[-1]
        
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
        
        # Entry signals
        else:
            # Long entry: Fast TEMA crosses above Slow TEMA
            if crossover(self.zl_tema_fast, self.zl_tema_slow):
                self.buy()
                self.entry_price = current_price
                
            # Short entry: Fast TEMA crosses below Slow TEMA
            elif crossover(self.zl_tema_slow, self.zl_tema_fast):
                self.sell()
                self.entry_price = current_price


# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ZERO-LAG TEMA CROSSES STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from multi_data_tester import test_on_all_data
    
    # Run tests on all data sources
    results = test_on_all_data(ZeroLagTEMAStrategy, 'ZeroLagTEMAStrategy')
    
    if results is not None:
        print("\n" + "="*80)
        print("STRATEGY TESTING COMPLETE")
        print("="*80)
        print(f"\nResults saved to: ./results/ZeroLagTEMAStrategy.csv")
        
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