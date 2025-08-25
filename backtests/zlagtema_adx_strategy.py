"""
Zero-lag TEMA + ADX Filter Strategy
====================================
Combines Zero-lag TEMA crossovers with ADX trend strength filter.
Only trades when trend is strong (ADX > 25) and DI confirms direction.

Strategy Rules:
- Long only when: TEMA bullish cross AND ADX > 25 AND DI+ > DI-
- Short only when: TEMA bearish cross AND ADX > 25 AND DI- > DI+
- Exit on opposite signal or ADX weakness
- 2% stop loss, 4% take profit
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

class ZeroLagTEMAADXStrategy(Strategy):
    """
    Zero-lag TEMA + ADX Filter Strategy
    Fast period: 22, Slow period: 144, ADX threshold: 25
    """
    
    # TEMA parameters
    fast_period = 22
    slow_period = 144
    
    # ADX parameters
    adx_period = 14
    adx_threshold = 25
    
    # Risk management
    stop_loss = 0.02  # 2%
    take_profit = 0.04  # 4%
    
    def init(self):
        """Initialize indicators using pandas_ta"""
        
        # Calculate Zero-lag TEMA for fast period
        close_series = pd.Series(self.data.Close)
        high_series = pd.Series(self.data.High)
        low_series = pd.Series(self.data.Low)
        
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
        
        # Calculate ADX and directional indicators
        adx_result = ta.adx(high_series, low_series, close_series, length=self.adx_period)
        if adx_result is not None and not adx_result.empty:
            # ADX result contains ADX_{period}, DMP_{period}, DMN_{period}
            adx_col = f'ADX_{self.adx_period}'
            dmp_col = f'DMP_{self.adx_period}'
            dmn_col = f'DMN_{self.adx_period}'
            
            self.adx = self.I(lambda: adx_result[adx_col] if adx_col in adx_result.columns else np.nan, name='ADX')
            self.plus_di = self.I(lambda: adx_result[dmp_col] if dmp_col in adx_result.columns else np.nan, name='DI+')
            self.minus_di = self.I(lambda: adx_result[dmn_col] if dmn_col in adx_result.columns else np.nan, name='DI-')
        else:
            # Fallback if pandas_ta ADX doesn't work
            self.adx = self.I(lambda: np.full(len(close_series), np.nan), name='ADX')
            self.plus_di = self.I(lambda: np.full(len(close_series), np.nan), name='DI+')
            self.minus_di = self.I(lambda: np.full(len(close_series), np.nan), name='DI-')
        
        # Track entry prices for stop loss and take profit
        self.entry_price = None
        
    def next(self):
        """Execute trading logic with ADX filter"""
        
        # Skip if not enough data
        if len(self.data) < max(self.slow_period * 3, self.adx_period * 2):
            return
            
        # Skip if NaN values in key indicators
        if (pd.isna(self.zl_tema_fast[-1]) or pd.isna(self.zl_tema_slow[-1]) or
            pd.isna(self.adx[-1]) or pd.isna(self.plus_di[-1]) or pd.isna(self.minus_di[-1])):
            return
        
        current_price = self.data.Close[-1]
        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]
        
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
                # Exit on ADX weakness (trend ending)
                elif current_adx < self.adx_threshold * 0.8:  # Exit if ADX drops below 80% of threshold
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
                # Exit on ADX weakness (trend ending)
                elif current_adx < self.adx_threshold * 0.8:  # Exit if ADX drops below 80% of threshold
                    self.position.close()
                    self.entry_price = None
        
        # Entry signals with ADX filter
        else:
            # Check if ADX indicates strong trend
            strong_trend = current_adx > self.adx_threshold
            
            # Long entry: Fast TEMA crosses above Slow TEMA + ADX filter
            if crossover(self.zl_tema_fast, self.zl_tema_slow):
                # Additional filters: ADX > threshold AND DI+ > DI-
                if strong_trend and current_plus_di > current_minus_di:
                    self.buy()
                    self.entry_price = current_price
                
            # Short entry: Fast TEMA crosses below Slow TEMA + ADX filter
            elif crossover(self.zl_tema_slow, self.zl_tema_fast):
                # Additional filters: ADX > threshold AND DI- > DI+
                if strong_trend and current_minus_di > current_plus_di:
                    self.sell()
                    self.entry_price = current_price


# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ZERO-LAG TEMA + ADX FILTER STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from multi_data_tester import test_on_all_data
    
    # Run tests on all data sources
    results = test_on_all_data(ZeroLagTEMAADXStrategy, 'ZeroLagTEMAADXStrategy')
    
    if results is not None:
        print("\n" + "="*80)
        print("STRATEGY TESTING COMPLETE")
        print("="*80)
        print(f"\nResults saved to: ./results/ZeroLagTEMAADXStrategy.csv")
        
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