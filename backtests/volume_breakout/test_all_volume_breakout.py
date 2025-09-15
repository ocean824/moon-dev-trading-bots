#!/usr/bin/env python3
"""
Run all Volume Breakout strategies and display summary results
===============================================================
Tests all 7 variations of the Volume Breakout strategy
"""

import pandas as pd
import os
import sys
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import strategies directly
from volume_breakout_base import VolumeBreakoutBase
from volume_breakout_kalman import VolumeBreakoutKalman
from volume_breakout_fibonacci import VolumeBreakoutFibonacci
from volume_breakout_ema import VolumeBreakoutEMA
from volume_breakout_adx import VolumeBreakoutADX
from volume_breakout_mfi import VolumeBreakoutMFI
from volume_breakout_bollinger import VolumeBreakoutBollinger
from multi_data_tester import test_on_all_data

# List of all strategies
strategies = [
    (VolumeBreakoutBase, 'VolumeBreakoutBase'),
    (VolumeBreakoutKalman, 'VolumeBreakoutKalman'),
    (VolumeBreakoutFibonacci, 'VolumeBreakoutFibonacci'),
    (VolumeBreakoutEMA, 'VolumeBreakoutEMA'),
    (VolumeBreakoutADX, 'VolumeBreakoutADX'),
    (VolumeBreakoutMFI, 'VolumeBreakoutMFI'),
    (VolumeBreakoutBollinger, 'VolumeBreakoutBollinger')
]

print("="*80)
print("VOLUME BREAKOUT STRATEGIES - COMPREHENSIVE TESTING")
print("="*80)
print("Testing all Volume Breakout variations across multiple data sources")
print("This will test:")
print("1. Base (OBV/CMF confirmation)")
print("2. Kalman (Smoothed signals)")
print("3. Fibonacci (Extension targets)")
print("4. EMA (Trend confirmation)")
print("5. ADX (Trend strength)")
print("6. MFI (Money flow)")
print("7. Bollinger (Squeeze detection)")
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
                avg_sharpe = results['Sharpe'].mean()
                avg_win_rate = results['Win_Rate_%'].mean()
                
                print(f"\nQuick Stats:")
                print(f"  Average Return: {avg_return:.2f}%")
                print(f"  Avg Sharpe Ratio: {avg_sharpe:.3f}")
                print(f"  Avg Win Rate: {avg_win_rate:.1f}%")
                print(f"  Profitable on {positive_returns}/{total_data_sources} data sources")
        else:
            print(f"⚠️ {strategy_name} returned no results")
            
    except Exception as e:
        print(f"❌ Error running {strategy_name}: {e}")

# Final summary
total_elapsed = time.time() - total_start

print("\n" + "="*80)
print("FINAL SUMMARY - ALL VOLUME BREAKOUT STRATEGIES")
print("="*80)

# Display comparison table of all strategies
if len(all_summaries) > 0:
    # Create a comparison summary
    comparison_data = []
    for strategy_name, results in all_summaries.items():
        if not results.empty:
            # Calculate additional metrics
            best_sharpe = results['Sharpe'].max()
            worst_dd = results['Max_DD_%'].min()
            total_trades = results['Trades'].sum()
            
            comparison_data.append({
                'Strategy': strategy_name.replace('VolumeBreakout', 'VB_'),  # Shorten for display
                'Avg_Return_%': round(results['Return_%'].mean(), 2),
                'Best_Return_%': round(results['Return_%'].max(), 2),
                'Worst_Return_%': round(results['Return_%'].min(), 2),
                'Profitable': f"{(results['Return_%'] > 0).sum()}/{len(results)}",
                'Avg_Sharpe': round(results['Sharpe'].mean(), 3),
                'Best_Sharpe': round(best_sharpe, 3),
                'Avg_Win_%': round(results['Win_Rate_%'].mean(), 1),
                'Total_Trades': total_trades,
                'Avg_DD_%': round(results['Max_DD_%'].mean(), 2),
                'Worst_DD_%': round(worst_dd, 2),
                'Avg_PF': round(results['Profit_Factor'].mean(), 2)
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        # Sort by average return
        comparison_df = comparison_df.sort_values('Avg_Return_%', ascending=False)
        
        print("\nStrategy Performance Ranking (sorted by Avg Return):")
        print(comparison_df.to_string(index=False))
        
        # Find best performing strategy overall
        best_strategy = comparison_df.iloc[0]['Strategy']
        best_return = comparison_df.iloc[0]['Avg_Return_%']
        best_sharpe_strategy = comparison_df.loc[comparison_df['Avg_Sharpe'].idxmax(), 'Strategy']
        best_sharpe_val = comparison_df['Avg_Sharpe'].max()
        
        print(f"\n🏆 BEST PERFORMERS:")
        print(f"  Highest Avg Return: {best_strategy} ({best_return}%)")
        print(f"  Best Risk-Adjusted: {best_sharpe_strategy} (Sharpe: {best_sharpe_val})")
        
        # Performance by category
        print(f"\n📊 PERFORMANCE BY CATEGORY:")
        
        # Group strategies by type
        base_strats = ['VB_Base']
        filter_strats = ['VB_Kalman']
        target_strats = ['VB_Fibonacci']
        trend_strats = ['VB_EMA', 'VB_ADX']
        volume_strats = ['VB_MFI']
        volatility_strats = ['VB_Bollinger']
        
        for category, strat_list in [
            ("Core Strategy", base_strats),
            ("Filtered Signals", filter_strats),
            ("Advanced Targets", target_strats),
            ("Trend Confirmation", trend_strats),
            ("Volume Analysis", volume_strats),
            ("Volatility-Based", volatility_strats)
        ]:
            category_df = comparison_df[comparison_df['Strategy'].isin(strat_list)]
            if not category_df.empty:
                avg_ret = category_df['Avg_Return_%'].mean()
                avg_sharpe = category_df['Avg_Sharpe'].mean()
                print(f"  {category}: Return={avg_ret:.2f}%, Sharpe={avg_sharpe:.3f}")

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
        master_file = os.path.join(results_dir, 'VOLUME_BREAKOUT_ALL_STRATEGIES.csv')
        master_df.to_csv(master_file, index=False)
        print(f"Master summary saved to: {master_file}")
        
        # Create a pivot table for easier comparison
        pivot_table = master_df.pivot_table(
            index='Data_Source',
            columns='Strategy',
            values=['Return_%', 'Sharpe', 'Win_Rate_%'],
            aggfunc='first'
        )
        
        pivot_file = os.path.join(results_dir, 'VOLUME_BREAKOUT_PIVOT_COMPARISON.csv')
        pivot_table.to_csv(pivot_file)
        print(f"Pivot comparison saved to: {pivot_file}")

print("\n" + "="*80)
print("VOLUME BREAKOUT STRATEGY TESTING COMPLETE!")
print("="*80)
print("\nKey Insights:")
print("- Base strategy provides foundation with OBV/CMF confirmation")
print("- Kalman filter reduces noise for cleaner signals")
print("- Fibonacci extensions offer dynamic profit targets")
print("- EMA alignment ensures trend-following entries")
print("- ADX confirms trend strength after breakout")
print("- MFI adds money flow analysis to volume signals")
print("- Bollinger Bands excel at squeeze detection")
print("\nRecommendation: Review individual strategy results to identify")
print("which variation performs best on your preferred timeframes.")
print("="*80)