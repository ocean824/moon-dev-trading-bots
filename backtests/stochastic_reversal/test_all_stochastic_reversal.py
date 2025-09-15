"""
Test All Stochastic Reversal Strategies
========================================
Runs all stochastic reversal variations and compares performance.
Creates a comprehensive comparison CSV with results from all strategies.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multi_data_tester import test_multiple_strategies
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import all strategy variations
from stochastic_reversal_base import StochasticReversalBase
from stochastic_reversal_adx import StochasticReversalADX
from stochastic_reversal_mfi import StochasticReversalMFI
from stochastic_reversal_bollinger import StochasticReversalBollinger
from stochastic_reversal_macd import StochasticReversalMACD
from stochastic_reversal_fibonacci import StochasticReversalFibonacci
from stochastic_reversal_kalman import StochasticReversalKalman

def print_strategy_summary(results_df, strategy_name):
    """Print formatted summary for a single strategy"""
    print(f"\n{'='*60}")
    print(f"  {strategy_name}")
    print(f"{'='*60}")
    
    if results_df is None or results_df.empty:
        print("  No results available")
        return
    
    # Calculate aggregate metrics
    avg_return = results_df['Return_%'].mean()
    avg_sharpe = results_df['Sharpe'].mean()
    avg_sortino = results_df['Sortino'].mean()
    avg_max_dd = results_df['Max_DD_%'].mean()
    avg_win_rate = results_df['Win_Rate_%'].mean()
    total_trades = results_df['Trades'].sum()
    
    print(f"  Average Return:     {avg_return:.2f}%")
    print(f"  Average Sharpe:     {avg_sharpe:.3f}")
    print(f"  Average Sortino:    {avg_sortino:.3f}")
    print(f"  Average Max DD:     {avg_max_dd:.2f}%")
    print(f"  Average Win Rate:   {avg_win_rate:.2f}%")
    print(f"  Total Trades:       {total_trades:.0f}")
    
    # Find best performing dataset
    if not results_df.empty:
        best_idx = results_df['Sortino'].idxmax()
        if pd.notna(best_idx):
            best_row = results_df.loc[best_idx]
            print(f"\n  Best Performance on: {best_row['Data_Source']}")
            print(f"    Return: {best_row['Return_%']:.2f}%")
            print(f"    Sharpe: {best_row['Sharpe']:.3f}")
            print(f"    Sortino: {best_row['Sortino']:.3f}")

def main():
    print("\n" + "="*80)
    print(" TESTING ALL STOCHASTIC REVERSAL STRATEGIES")
    print("="*80)
    print("\nDr. Data Dawg, let's test all stochastic reversal variations!")
    print("\nStrategies to test:")
    print("1. Base - Stochastic overbought/oversold reversals with divergence")
    print("2. ADX - Base + ADX trend strength filter")
    print("3. MFI - Base + Money Flow Index confirmation")
    print("4. Bollinger - Base + Bollinger Bands for volatility context")
    print("5. MACD - Base + MACD momentum confirmation")
    print("6. Fibonacci - Base + Fibonacci retracement levels")
    print("7. Kalman - Base + Kalman filter for noise reduction")
    
    # Define strategies to test
    strategies = {
        'StochasticReversalBase': StochasticReversalBase,
        'StochasticReversalADX': StochasticReversalADX,
        'StochasticReversalMFI': StochasticReversalMFI,
        'StochasticReversalBollinger': StochasticReversalBollinger,
        'StochasticReversalMACD': StochasticReversalMACD,
        'StochasticReversalFibonacci': StochasticReversalFibonacci,
        'StochasticReversalKalman': StochasticReversalKalman
    }
    
    print(f"\nTesting {len(strategies)} strategies on all configured data sources...")
    print("This will take several minutes. Each strategy will be tested on 20+ datasets.\n")
    
    # Test all strategies
    all_results = test_multiple_strategies(strategies, optimize=False)
    
    if all_results is None:
        print("\nError: No results returned from testing")
        return
    
    # Print individual strategy summaries
    print("\n" + "="*80)
    print(" INDIVIDUAL STRATEGY PERFORMANCE SUMMARIES")
    print("="*80)
    
    strategy_metrics = {}
    
    for strategy_name in strategies.keys():
        # Find the results file for this strategy
        results_file = f"./results/{strategy_name}.csv"
        if os.path.exists(results_file):
            df = pd.read_csv(results_file)
            print_strategy_summary(df, strategy_name)
            
            # Store metrics for comparison
            if not df.empty:
                strategy_metrics[strategy_name] = {
                    'Avg_Return': df['Return_%'].mean(),
                    'Avg_Sharpe': df['Sharpe'].mean(),
                    'Avg_Sortino': df['Sortino'].mean(),
                    'Avg_Max_DD': df['Max_DD_%'].mean(),
                    'Avg_Win_Rate': df['Win_Rate_%'].mean(),
                    'Total_Trades': df['Trades'].sum(),
                    'Best_Sortino': df['Sortino'].max(),
                    'Worst_DD': df['Max_DD_%'].min()
                }
    
    # Create comparison summary
    if strategy_metrics:
        print("\n" + "="*80)
        print(" STRATEGY COMPARISON MATRIX")
        print("="*80)
        
        comparison_df = pd.DataFrame(strategy_metrics).T
        comparison_df = comparison_df.round(3)
        
        # Sort by average Sortino ratio
        comparison_df = comparison_df.sort_values('Avg_Sortino', ascending=False)
        
        print("\nRanked by Average Sortino Ratio:")
        print(comparison_df.to_string())
        
        # Find overall winner
        print("\n" + "="*80)
        print(" OVERALL RESULTS")
        print("="*80)
        
        winner = comparison_df.index[0]
        print(f"\nBest Overall Strategy: {winner}")
        print(f"  Average Sortino: {comparison_df.loc[winner, 'Avg_Sortino']:.3f}")
        print(f"  Average Return:  {comparison_df.loc[winner, 'Avg_Return']:.2f}%")
        print(f"  Average Sharpe:  {comparison_df.loc[winner, 'Avg_Sharpe']:.3f}")
        
        # Save comparison to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        comparison_file = f"./results/stochastic_reversal_comparison_{timestamp}.csv"
        comparison_df.to_csv(comparison_file)
        print(f"\nComparison saved to: {comparison_file}")
    
    # Print key insights
    print("\n" + "="*80)
    print(" KEY INSIGHTS")
    print("="*80)
    
    if strategy_metrics:
        # Find strategies with best characteristics
        best_return = max(strategy_metrics.items(), key=lambda x: x[1]['Avg_Return'])[0]
        best_sharpe = max(strategy_metrics.items(), key=lambda x: x[1]['Avg_Sharpe'])[0]
        best_win_rate = max(strategy_metrics.items(), key=lambda x: x[1]['Avg_Win_Rate'])[0]
        lowest_dd = max(strategy_metrics.items(), key=lambda x: x[1]['Avg_Max_DD'])[0]
        
        print(f"\nHighest Average Return:    {best_return}")
        print(f"Best Risk-Adjusted (Sharpe): {best_sharpe}")
        print(f"Highest Win Rate:           {best_win_rate}")
        print(f"Lowest Drawdown:            {lowest_dd}")
        
        print("\nStrategy Characteristics:")
        print("- Base: Pure stochastic reversal with divergence detection")
        print("- ADX: Best in ranging markets (low ADX environments)")
        print("- MFI: Volume-weighted confirmation reduces false signals")
        print("- Bollinger: Volatility-based entries at band extremes")
        print("- MACD: Momentum confirmation for trend alignment")
        print("- Fibonacci: Precision entries at key retracement levels")
        print("- Kalman: Noise reduction for cleaner signals")
    
    print("\n" + "="*80)
    print(" TESTING COMPLETE!")
    print("="*80)
    print("\nAll results have been saved to the ./results/ directory")
    print("Check individual CSV files for detailed performance on each dataset")
    
    return all_results

if __name__ == "__main__":
    results = main()
    
    if results is not None:
        print("\n✅ All stochastic reversal strategies tested successfully!")
        print("📊 Results saved in ./results/ directory")
    else:
        print("\n❌ Testing encountered errors. Please check the output above.")