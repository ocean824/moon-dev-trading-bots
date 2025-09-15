#!/usr/bin/env python3
"""
Run all Volume Price Trend (VPT) strategies and display summary results
"""

import pandas as pd
import os
import sys
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import VPT strategies directly
from vpt_base import VPTBase
from vpt_adx import VPTADX
from vpt_bollinger import VPTBollinger
from vpt_ema import VPTEMA
from vpt_kalman import VPTKalman
from vpt_mfi import VPTMFI
from multi_data_tester import test_on_all_data

# List of all VPT strategies
strategies = [
    (VPTBase, 'VPTBase'),
    (VPTADX, 'VPTADX'),
    (VPTBollinger, 'VPTBollinger'),
    (VPTEMA, 'VPTEMA'),
    (VPTKalman, 'VPTKalman'),
    (VPTMFI, 'VPTMFI')
]

print("="*80)
print("VOLUME PRICE TREND (VPT) STRATEGIES - SUMMARY RESULTS")
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
print("FINAL SUMMARY - ALL VPT STRATEGIES")
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
                'Avg_Max_DD_%': round(results['Max_DD_%'].mean(), 2)
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        print("\nVPT Strategy Comparison:")
        print(comparison_df.to_string(index=False))

print(f"\nTotal execution time: {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)")
print("\nAll VPT results saved in: ./results/")

# Create a combined summary if requested
if len(all_summaries) > 0:
    print("\nCombining all VPT results into a master summary...")
    
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
        master_file = os.path.join(results_dir, 'ALL_VPT_STRATEGIES_SUMMARY.csv')
        master_df.to_csv(master_file, index=False)
        print(f"Master VPT summary saved to: {master_file}")

print("="*80)
print("VPT STRATEGY ANALYSIS COMPLETE!")
print("="*80)

# Top level insights
if len(all_summaries) > 0 and comparison_data:
    print("\n🔍 KEY INSIGHTS:")
    
    # Best performing strategy by average return
    best_avg = max(comparison_data, key=lambda x: x['Avg_Return_%'])
    print(f"📈 Best Average Return: {best_avg['Strategy']} ({best_avg['Avg_Return_%']}%)")
    
    # Most consistent strategy (most profitable sources)
    best_consistent = max(comparison_data, key=lambda x: int(x['Profitable_Sources'].split('/')[0]))
    print(f"🎯 Most Consistent: {best_consistent['Strategy']} ({best_consistent['Profitable_Sources']} profitable)")
    
    # Highest Sharpe ratio
    best_sharpe = max(comparison_data, key=lambda x: x['Avg_Sharpe'])
    print(f"⚡ Best Risk-Adjusted: {best_sharpe['Strategy']} (Sharpe: {best_sharpe['Avg_Sharpe']})")
    
    # Most active strategy
    most_trades = max(comparison_data, key=lambda x: x['Total_Trades'])
    print(f"🔄 Most Active: {most_trades['Strategy']} ({most_trades['Total_Trades']} total trades)")
    
print("\n🌙 Dr. Data Dawg, your VPT strategy suite is complete! 🚀")