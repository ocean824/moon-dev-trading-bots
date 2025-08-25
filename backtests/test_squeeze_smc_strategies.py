#!/usr/bin/env python3
"""
Test all Squeeze and SMC strategies and display summary results
================================================================

This script runs all three strategies:
1. Squeeze Momentum (LazyBear's indicator)
2. Smart Money Concepts (simplified)
3. Combined Squeeze + SMC

And displays a comprehensive comparison of their performance.
"""

import pandas as pd
import os
import sys
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import strategies directly
from squeeze_momentum_strategy import SqueezeMomentum
from smart_money_strategy import SmartMoneyConcepts
from squeeze_smc_combined_strategy import SqueezeSMCCombined
from multi_data_tester import test_on_all_data

# List of all strategies
strategies = [
    (SqueezeMomentum, 'SqueezeMomentum'),
    (SmartMoneyConcepts, 'SmartMoneyConcepts'),
    (SqueezeSMCCombined, 'SqueezeSMCCombined')
]

print("="*80)
print("SQUEEZE & SMC STRATEGIES - COMPREHENSIVE TEST")
print("="*80)
print("\nStrategies to test:")
print("1. Squeeze Momentum - LazyBear's famous squeeze indicator")
print("2. Smart Money Concepts - Order blocks, FVGs, and structure")
print("3. Combined Strategy - Best of both worlds")
print("-"*80)

# Track overall stats
total_start = time.time()
all_summaries = {}

for i, (strategy_class, strategy_name) in enumerate(strategies, 1):
    print(f"\n[{i}/{len(strategies)}] Testing: {strategy_name}")
    print("-"*40)
    
    start_time = time.time()
    
    try:
        # Run the strategy and capture results (verbose=False to suppress individual stats)
        results = test_on_all_data(strategy_class, strategy_name, verbose=False)
        
        elapsed = time.time() - start_time
        
        if results is not None:
            # Store the summary
            all_summaries[strategy_name] = results
            
            print(f"\nCompleted {strategy_name} in {elapsed:.1f} seconds")
            print(f"Results saved to: ./results/{strategy_name}.csv")
            
            # Display the nice summary table
            print("\nSUMMARY:")
            print(results[['Data_Source', 'Return_%', 'Buy_Hold_%', 'Sharpe', 'Sortino', 
                          'Max_DD_%', 'Profit_Factor', 'Expectancy_%', 'Trades', 'Win_Rate_%']].to_string())
            
            # Show quick stats
            if not results.empty:
                avg_return = results['Return_%'].mean()
                positive_returns = (results['Return_%'] > 0).sum()
                total_data_sources = len(results)
                avg_sharpe = results['Sharpe'].mean()
                avg_win_rate = results['Win_Rate_%'].mean()
                
                print(f"\nQuick Stats:")
                print(f"  Average Return: {avg_return:.2f}%")
                print(f"  Profitable on {positive_returns}/{total_data_sources} data sources")
                print(f"  Average Sharpe: {avg_sharpe:.3f}")
                print(f"  Average Win Rate: {avg_win_rate:.1f}%")
        else:
            print(f"Warning: {strategy_name} returned no results")
            
    except Exception as e:
        print(f"Error running {strategy_name}: {e}")

# Final summary
total_elapsed = time.time() - total_start

print("\n" + "="*80)
print("FINAL COMPARISON - ALL STRATEGIES")
print("="*80)

# Display comparison table of all strategies
if len(all_summaries) > 0:
    # Create a comparison summary
    comparison_data = []
    for strategy_name, results in all_summaries.items():
        if not results.empty:
            # Strategy description
            if strategy_name == 'SqueezeMomentum':
                desc = 'Squeeze OFF + Momentum'
            elif strategy_name == 'SmartMoneyConcepts':
                desc = 'Order Blocks + Structure'
            else:
                desc = 'Combined Confluence'
            
            comparison_data.append({
                'Strategy': strategy_name,
                'Description': desc,
                'Avg_Return_%': round(results['Return_%'].mean(), 2),
                'Best_Return_%': round(results['Return_%'].max(), 2),
                'Worst_Return_%': round(results['Return_%'].min(), 2),
                'Profitable_Sources': f"{(results['Return_%'] > 0).sum()}/{len(results)}",
                'Avg_Win_Rate_%': round(results['Win_Rate_%'].mean(), 1),
                'Total_Trades': results['Trades'].sum(),
                'Avg_Sharpe': round(results['Sharpe'].mean(), 3),
                'Avg_Sortino': round(results['Sortino'].mean(), 3),
                'Avg_Max_DD_%': round(results['Max_DD_%'].mean(), 2)
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        print("\nStrategy Performance Comparison:")
        print(comparison_df.to_string(index=False))
        
        # Rank strategies
        print("\n" + "-"*80)
        print("PERFORMANCE RANKING (by Average Return):")
        comparison_df_sorted = comparison_df.sort_values('Avg_Return_%', ascending=False)
        for idx, row in enumerate(comparison_df_sorted.itertuples(), 1):
            print(f"{idx}. {row.Strategy}: {row.Avg_Return_}% avg return, "
                  f"Sharpe {row.Avg_Sharpe}, Win Rate {row.Avg_Win_Rate_}%")

print(f"\nTotal execution time: {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)")
print("\nAll results saved in: ./results/")

# Create a combined summary if requested
if len(all_summaries) > 0:
    print("\nCombining all results into a master summary...")
    
    # Create results directory if it doesn't exist
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Combine all results with strategy name column
    combined_results = []
    for strategy_name, df in all_summaries.items():
        df_copy = df.copy()
        df_copy['Strategy'] = strategy_name
        combined_results.append(df_copy)
    
    if combined_results:
        master_df = pd.concat(combined_results, ignore_index=True)
        master_file = os.path.join(results_dir, 'SQUEEZE_SMC_STRATEGIES_SUMMARY.csv')
        master_df.to_csv(master_file, index=False)
        print(f"Master summary saved to: {master_file}")

print("="*80)
print("\nSTRATEGY INSIGHTS:")
print("-"*40)
print("1. Squeeze Momentum: Best for catching breakouts after consolidation")
print("2. Smart Money Concepts: Best for precision entries at key levels")
print("3. Combined Strategy: Highest confluence, fewer but higher quality trades")
print("="*80)