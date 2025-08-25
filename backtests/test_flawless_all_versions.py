#!/usr/bin/env python3
"""
Test all three versions of Flawless Victory Strategy on all data sources
"""

import pandas as pd
import os
import sys
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import strategies
from flawless_victory_strategy import FlawlessVictoryV1, FlawlessVictoryV2, FlawlessVictoryV3
from multi_data_tester import test_on_all_data

# List of all versions
strategies = [
    (FlawlessVictoryV1, 'FlawlessVictoryV1', 'No SL/TP - BB(20,1.0), RSI(14)'),
    (FlawlessVictoryV2, 'FlawlessVictoryV2', 'With SL/TP - BB(17,1.0), RSI(14), SL:6.6%, TP:2.3%'),
    (FlawlessVictoryV3, 'FlawlessVictoryV3', 'MFI Version - BB(20,1.0), RSI(14), MFI(14), SL:8.9%, TP:2.3%')
]

print("="*80)
print("FLAWLESS VICTORY STRATEGIES - ALL VERSIONS SUMMARY")
print("="*80)

# Track overall stats
total_start = time.time()
all_summaries = {}

for i, (strategy_class, strategy_name, description) in enumerate(strategies, 1):
    print(f"\n[{i}/{len(strategies)}] Testing: {strategy_name}")
    print(f"Description: {description}")
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
            
            # Show quick stats
            if not results.empty:
                avg_return = results['Return_%'].mean()
                best_return = results['Return_%'].max()
                worst_return = results['Return_%'].min()
                positive_returns = (results['Return_%'] > 0).sum()
                total_data_sources = len(results)
                avg_win_rate = results['Win_Rate_%'].mean()
                avg_sharpe = results['Sharpe'].mean()
                avg_max_dd = results['Max_DD_%'].mean()
                
                print(f"\nQuick Stats:")
                print(f"  Average Return: {avg_return:.2f}%")
                print(f"  Best Return: {best_return:.2f}%")
                print(f"  Worst Return: {worst_return:.2f}%")
                print(f"  Profitable on {positive_returns}/{total_data_sources} data sources")
                print(f"  Average Win Rate: {avg_win_rate:.1f}%")
                print(f"  Average Sharpe: {avg_sharpe:.3f}")
                print(f"  Average Max Drawdown: {avg_max_dd:.2f}%")
        else:
            print(f"⚠️ {strategy_name} returned no results")
            
    except Exception as e:
        print(f"❌ Error running {strategy_name}: {e}")
        import traceback
        traceback.print_exc()

# Final summary
total_elapsed = time.time() - total_start

print("\n" + "="*80)
print("FINAL COMPARISON - ALL FLAWLESS VICTORY VERSIONS")
print("="*80)

# Display comparison table of all versions
if len(all_summaries) > 0:
    # Create a comparison summary
    comparison_data = []
    for strategy_name, results in all_summaries.items():
        if not results.empty:
            # Find best performing data source
            best_idx = results['Return_%'].idxmax()
            best_data = results.loc[best_idx, 'Data_Source']
            best_return = results.loc[best_idx, 'Return_%']
            
            # Find worst performing data source
            worst_idx = results['Return_%'].idxmin()
            worst_data = results.loc[worst_idx, 'Data_Source']
            worst_return = results.loc[worst_idx, 'Return_%']
            
            comparison_data.append({
                'Version': strategy_name.replace('FlawlessVictory', ''),
                'Avg_Return_%': round(results['Return_%'].mean(), 2),
                'Best_Return_%': round(best_return, 2),
                'Best_On': best_data,
                'Worst_Return_%': round(worst_return, 2),
                'Worst_On': worst_data,
                'Win_Sources': f"{(results['Return_%'] > 0).sum()}/{len(results)}",
                'Avg_WinRate_%': round(results['Win_Rate_%'].mean(), 1),
                'Total_Trades': results['Trades'].sum(),
                'Avg_Sharpe': round(results['Sharpe'].mean(), 3),
                'Avg_Sortino': round(results['Sortino'].mean(), 3),
                'Avg_MaxDD_%': round(results['Max_DD_%'].mean(), 2),
                'Avg_PF': round(results['Profit_Factor'].mean(), 2)
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        print("\n📊 VERSION COMPARISON TABLE:")
        print(comparison_df.to_string(index=False))
        
        # Determine winner
        print("\n🏆 PERFORMANCE SUMMARY:")
        
        # Best average return
        best_avg_return_idx = comparison_df['Avg_Return_%'].idxmax()
        print(f"Best Average Return: Version {comparison_df.loc[best_avg_return_idx, 'Version']} "
              f"({comparison_df.loc[best_avg_return_idx, 'Avg_Return_%']}%)")
        
        # Best Sharpe ratio
        best_sharpe_idx = comparison_df['Avg_Sharpe'].idxmax()
        print(f"Best Risk-Adjusted (Sharpe): Version {comparison_df.loc[best_sharpe_idx, 'Version']} "
              f"({comparison_df.loc[best_sharpe_idx, 'Avg_Sharpe']})")
        
        # Most consistent (highest win rate)
        best_winrate_idx = comparison_df['Avg_WinRate_%'].idxmax()
        print(f"Most Consistent (Win Rate): Version {comparison_df.loc[best_winrate_idx, 'Version']} "
              f"({comparison_df.loc[best_winrate_idx, 'Avg_WinRate_%']}%)")
        
        # Lowest drawdown
        best_dd_idx = comparison_df['Avg_MaxDD_%'].idxmin()
        print(f"Lowest Drawdown: Version {comparison_df.loc[best_dd_idx, 'Version']} "
              f"({comparison_df.loc[best_dd_idx, 'Avg_MaxDD_%']}%)")

print(f"\n⏱️ Total execution time: {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)")
print("\n📁 All results saved in: ./results/")

# Create a combined summary
if len(all_summaries) > 0:
    print("\n📊 Creating combined results file...")
    
    # Create results directory if it doesn't exist
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Combine all results with version column
    combined_results = []
    for strategy_name, df in all_summaries.items():
        df_copy = df.copy()
        df_copy['Version'] = strategy_name.replace('FlawlessVictory', '')
        combined_results.append(df_copy)
    
    if combined_results:
        master_df = pd.concat(combined_results, ignore_index=True)
        master_file = os.path.join(results_dir, 'FLAWLESS_VICTORY_ALL_VERSIONS.csv')
        master_df.to_csv(master_file, index=False)
        print(f"✅ Master summary saved to: {master_file}")
        
        # Create pivot table for easy comparison
        pivot_file = os.path.join(results_dir, 'FLAWLESS_VICTORY_PIVOT.csv')
        pivot_table = master_df.pivot_table(
            index='Data_Source',
            columns='Version',
            values=['Return_%', 'Sharpe', 'Win_Rate_%', 'Max_DD_%'],
            aggfunc='first'
        )
        pivot_table.to_csv(pivot_file)
        print(f"✅ Pivot comparison saved to: {pivot_file}")

print("\n" + "="*80)
print("🎮 FLAWLESS VICTORY TESTING COMPLETE!")
print("="*80)