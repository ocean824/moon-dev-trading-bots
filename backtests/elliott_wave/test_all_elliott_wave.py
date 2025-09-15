#!/usr/bin/env python3
"""
Run all Elliott Wave strategies and display summary results
===========================================================
Tests all variations of Elliott Wave patterns with different indicators
"""

import pandas as pd
import os
import sys
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import base strategies
from elliott_impulse_base import ElliottImpulseBase
from elliott_corrective_base import ElliottCorrectiveBase
from elliott_combined_base import ElliottCombinedBase

# Import impulse variations
from elliott_impulse_adx import ElliottImpulseADX
from elliott_impulse_mfi import ElliottImpulseMFI
from elliott_impulse_bollinger import ElliottImpulseBollinger

# Import multi-data tester
from multi_data_tester import test_on_all_data

# List of all strategies
strategies = [
    # Base strategies
    (ElliottImpulseBase, 'ElliottImpulseBase'),
    (ElliottCorrectiveBase, 'ElliottCorrectiveBase'),
    (ElliottCombinedBase, 'ElliottCombinedBase'),
    
    # Impulse variations
    (ElliottImpulseADX, 'ElliottImpulseADX'),
    (ElliottImpulseMFI, 'ElliottImpulseMFI'),
    (ElliottImpulseBollinger, 'ElliottImpulseBollinger'),
]

print("="*80)
print("ELLIOTT WAVE STRATEGIES - COMPREHENSIVE TESTING")
print("="*80)
print(f"\nTesting {len(strategies)} Elliott Wave strategies across all data sources")
print("This will test impulse waves, corrective waves, and combined patterns")
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
                avg_sharpe = results['Sharpe'].mean()
                avg_win_rate = results['Win_Rate_%'].mean()
                
                print(f"\nQuick Stats:")
                print(f"  Average Return: {avg_return:.2f}%")
                print(f"  Average Sharpe: {avg_sharpe:.3f}")
                print(f"  Average Win Rate: {avg_win_rate:.1f}%")
                print(f"  Profitable on {positive_returns}/{total_data_sources} data sources")
        else:
            print(f"⚠️ {strategy_name} returned no results")
            
    except Exception as e:
        print(f"❌ Error running {strategy_name}: {e}")

# Final summary
total_elapsed = time.time() - total_start

print("\n" + "="*80)
print("FINAL SUMMARY - ALL ELLIOTT WAVE STRATEGIES")
print("="*80)

# Display comparison table of all strategies
if len(all_summaries) > 0:
    # Create a comparison summary
    comparison_data = []
    for strategy_name, results in all_summaries.items():
        if not results.empty:
            # Determine strategy type
            if 'Impulse' in strategy_name and 'Corrective' not in strategy_name:
                strategy_type = 'Impulse'
            elif 'Corrective' in strategy_name and 'Impulse' not in strategy_name:
                strategy_type = 'Corrective'
            elif 'Combined' in strategy_name:
                strategy_type = 'Combined'
            else:
                strategy_type = 'Unknown'
            
            comparison_data.append({
                'Strategy': strategy_name,
                'Type': strategy_type,
                'Avg_Return_%': round(results['Return_%'].mean(), 2),
                'Best_Return_%': round(results['Return_%'].max(), 2),
                'Worst_Return_%': round(results['Return_%'].min(), 2),
                'Profitable_Sources': f"{(results['Return_%'] > 0).sum()}/{len(results)}",
                'Avg_Win_Rate_%': round(results['Win_Rate_%'].mean(), 1),
                'Total_Trades': results['Trades'].sum(),
                'Avg_Sharpe': round(results['Sharpe'].mean(), 3),
                'Avg_Sortino': round(results['Sortino'].mean(), 3),
                'Avg_Max_DD_%': round(results['Max_DD_%'].mean(), 2),
                'Avg_Profit_Factor': round(results['Profit_Factor'].mean(), 3)
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        
        # Sort by average return
        comparison_df = comparison_df.sort_values('Avg_Return_%', ascending=False)
        
        print("\nStrategy Performance Comparison:")
        print(comparison_df.to_string(index=False))
        
        # Group analysis by strategy type
        print("\n" + "-"*80)
        print("ANALYSIS BY WAVE TYPE:")
        print("-"*80)
        
        for wave_type in ['Impulse', 'Corrective', 'Combined']:
            type_strategies = [s for s in comparison_data if s['Type'] == wave_type]
            if type_strategies:
                avg_return = sum(s['Avg_Return_%'] for s in type_strategies) / len(type_strategies)
                avg_sharpe = sum(s['Avg_Sharpe'] for s in type_strategies) / len(type_strategies)
                avg_win_rate = sum(s['Avg_Win_Rate_%'] for s in type_strategies) / len(type_strategies)
                
                print(f"\n{wave_type} Wave Strategies:")
                print(f"  Count: {len(type_strategies)}")
                print(f"  Avg Return: {avg_return:.2f}%")
                print(f"  Avg Sharpe: {avg_sharpe:.3f}")
                print(f"  Avg Win Rate: {avg_win_rate:.1f}%")

print(f"\nTotal execution time: {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)")
print(f"Tested {len(strategies)} strategies on multiple data sources")
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
        master_file = os.path.join(results_dir, 'ELLIOTT_WAVE_ALL_STRATEGIES.csv')
        master_df.to_csv(master_file, index=False)
        print(f"Master summary saved to: {master_file}")
        
        # Also save the comparison summary
        if comparison_data:
            comparison_file = os.path.join(results_dir, 'ELLIOTT_WAVE_COMPARISON.csv')
            comparison_df.to_csv(comparison_file, index=False)
            print(f"Comparison summary saved to: {comparison_file}")

print("\n" + "="*80)
print("ELLIOTT WAVE TESTING COMPLETE")
print("="*80)