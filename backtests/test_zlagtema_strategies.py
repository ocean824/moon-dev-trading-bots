#!/usr/bin/env python3
"""
Run all Zero-lag TEMA strategies and display summary results
"""

import pandas as pd
import os
import sys
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import strategies directly
from zlagtema_strategy import ZeroLagTEMAStrategy
from zlagtema_adx_strategy import ZeroLagTEMAADXStrategy
from zlagtema_mfi_strategy import ZeroLagTEMAMFIStrategy
from multi_data_tester import test_on_all_data

# List of all strategies
strategies = [
    (ZeroLagTEMAStrategy, 'ZeroLagTEMA_Base'),
    (ZeroLagTEMAADXStrategy, 'ZeroLagTEMA_ADX'),
    (ZeroLagTEMAMFIStrategy, 'ZeroLagTEMA_MFI')
]

print("="*80)
print("ZERO-LAG TEMA STRATEGIES - SUMMARY RESULTS")
print("="*80)

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
            
            print(f"\n✅ {strategy_name} completed in {elapsed:.1f} seconds")
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
                
                print(f"\nAverage Return: {avg_return:.2f}%")
                print(f"Profitable on {positive_returns}/{total_data_sources} data sources")
        else:
            print(f"⚠️ {strategy_name} returned no results")
            
    except Exception as e:
        print(f"❌ Error running {strategy_name}: {e}")

# Final summary
total_elapsed = time.time() - total_start

print("\n" + "="*80)
print("FINAL SUMMARY - ALL ZERO-LAG TEMA STRATEGIES")
print("="*80)

# Display comparison table of all strategies
if len(all_summaries) > 0:
    # Create a comparison summary
    comparison_data = []
    for strategy_name, results in all_summaries.items():
        if not results.empty:
            comparison_data.append({
                'Strategy': strategy_name,
                'Avg_Return_%': round(results['Return_%'].mean(), 2),
                'Best_Return_%': round(results['Return_%'].max(), 2),
                'Worst_Return_%': round(results['Return_%'].min(), 2),
                'Profitable_Sources': f"{(results['Return_%'] > 0).sum()}/{len(results)}",
                'Avg_Win_Rate_%': round(results['Win_Rate_%'].mean(), 1),
                'Total_Trades': results['Trades'].sum(),
                'Avg_Sharpe': round(results['Sharpe'].mean(), 3),
                'Avg_Sortino': round(results['Sortino'].mean(), 3),
                'Avg_Max_DD_%': round(results['Max_DD_%'].mean(), 2),
                'Avg_Profit_Factor': round(results['Profit_Factor'].mean(), 2)
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        print("\nStrategy Comparison:")
        print(comparison_df.to_string(index=False))
        
        # Identify the best overall strategy
        if not comparison_df.empty:
            best_strategy = comparison_df.loc[comparison_df['Avg_Return_%'].idxmax()]
            print(f"\n🏆 Best Overall Strategy: {best_strategy['Strategy']}")
            print(f"   - Average Return: {best_strategy['Avg_Return_%']}%")
            print(f"   - Average Sharpe: {best_strategy['Avg_Sharpe']}")
            print(f"   - Average Win Rate: {best_strategy['Avg_Win_Rate_%']}%")

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
        master_file = os.path.join(results_dir, 'ZLAGTEMA_STRATEGIES_SUMMARY.csv')
        master_df.to_csv(master_file, index=False)
        print(f"Master summary saved to: {master_file}")

print("="*80)