#!/usr/bin/env python3
"""
Run all Three Mountains & Three Rivers strategies and display summary results
==============================================================================
Tests all pattern variations across multiple data sources
Generates comprehensive performance comparison
"""

import pandas as pd
import os
import sys
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import strategies directly
from three_mountains_rivers_base import ThreeMountainsRiversBase
from three_mountains_rivers_kalman import ThreeMountainsRiversKalman
from three_mountains_rivers_fibonacci import ThreeMountainsRiversFibonacci
from three_mountains_rivers_ema import ThreeMountainsRiversEMA
from three_mountains_rivers_adx import ThreeMountainsRiversADX
from three_mountains_rivers_mfi import ThreeMountainsRiversMFI
from three_mountains_rivers_bollinger import ThreeMountainsRiversBollinger
from multi_data_tester import test_on_all_data

# List of all strategies with descriptive names
strategies = [
    (ThreeMountainsRiversBase, 'ThreeMountainsRiversBase'),
    (ThreeMountainsRiversKalman, 'ThreeMountainsRiversKalman'),
    (ThreeMountainsRiversFibonacci, 'ThreeMountainsRiversFibonacci'),
    (ThreeMountainsRiversEMA, 'ThreeMountainsRiversEMA'),
    (ThreeMountainsRiversADX, 'ThreeMountainsRiversADX'),
    (ThreeMountainsRiversMFI, 'ThreeMountainsRiversMFI'),
    (ThreeMountainsRiversBollinger, 'ThreeMountainsRiversBollinger')
]

print("="*80)
print("THREE MOUNTAINS & THREE RIVERS STRATEGIES - COMPREHENSIVE TEST")
print("="*80)
print("\nPattern Recognition Strategies:")
print("- Base: Core triple top/bottom pattern detection")
print("- Kalman: Smoothed price data for noise reduction")
print("- Fibonacci: Retracement levels for targets")
print("- EMA: Triple EMA trend confirmation")
print("- ADX: Trend strength and reversal confirmation")
print("- MFI: Money flow and volume analysis")
print("- Bollinger: Band extremes and squeeze detection")
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
            print("\nKEY METRICS:")
            summary_cols = ['Data_Source', 'Return_%', 'Buy_Hold_%', 'Sharpe', 'Sortino', 
                          'Max_DD_%', 'Profit_Factor', 'Expectancy_%', 'Trades', 'Win_Rate_%']
            
            # Filter columns that exist in the results
            available_cols = [col for col in summary_cols if col in results.columns]
            print(results[available_cols].to_string())
            
            # Show quick stats
            if not results.empty:
                avg_return = results['Return_%'].mean()
                best_return = results['Return_%'].max()
                worst_return = results['Return_%'].min()
                positive_returns = (results['Return_%'] > 0).sum()
                total_data_sources = len(results)
                avg_sharpe = results['Sharpe'].mean() if 'Sharpe' in results.columns else 0
                avg_win_rate = results['Win_Rate_%'].mean() if 'Win_Rate_%' in results.columns else 0
                total_trades = results['Trades'].sum() if 'Trades' in results.columns else 0
                
                print(f"\n📊 PERFORMANCE SUMMARY:")
                print(f"  Average Return: {avg_return:.2f}%")
                print(f"  Best Return: {best_return:.2f}%")
                print(f"  Worst Return: {worst_return:.2f}%")
                print(f"  Profitable Markets: {positive_returns}/{total_data_sources}")
                print(f"  Average Sharpe: {avg_sharpe:.3f}")
                print(f"  Average Win Rate: {avg_win_rate:.1f}%")
                print(f"  Total Trades: {total_trades}")
        else:
            print(f"⚠️ {strategy_name} returned no results")
            
    except Exception as e:
        print(f"❌ Error running {strategy_name}: {e}")
        import traceback
        traceback.print_exc()

# Final summary
total_elapsed = time.time() - total_start

print("\n" + "="*80)
print("FINAL SUMMARY - ALL THREE MOUNTAINS & RIVERS STRATEGIES")
print("="*80)

# Display comparison table of all strategies
if len(all_summaries) > 0:
    # Create a comparison summary
    comparison_data = []
    for strategy_name, results in all_summaries.items():
        if not results.empty:
            # Extract strategy type from name
            strategy_type = strategy_name.replace('ThreeMountainsRivers', '')
            
            comparison_data.append({
                'Strategy': strategy_type,
                'Avg_Return_%': round(results['Return_%'].mean(), 2),
                'Best_Return_%': round(results['Return_%'].max(), 2),
                'Worst_Return_%': round(results['Return_%'].min(), 2),
                'Profitable_Sources': f"{(results['Return_%'] > 0).sum()}/{len(results)}",
                'Avg_Sharpe': round(results['Sharpe'].mean(), 3) if 'Sharpe' in results.columns else 0,
                'Avg_Sortino': round(results['Sortino'].mean(), 3) if 'Sortino' in results.columns else 0,
                'Avg_Win_Rate_%': round(results['Win_Rate_%'].mean(), 1) if 'Win_Rate_%' in results.columns else 0,
                'Total_Trades': results['Trades'].sum() if 'Trades' in results.columns else 0,
                'Avg_Max_DD_%': round(results['Max_DD_%'].mean(), 2) if 'Max_DD_%' in results.columns else 0,
                'Avg_Profit_Factor': round(results['Profit_Factor'].mean(), 3) if 'Profit_Factor' in results.columns else 0
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        # Sort by average return
        comparison_df = comparison_df.sort_values('Avg_Return_%', ascending=False)
        
        print("\n📊 STRATEGY COMPARISON (Sorted by Average Return):")
        print(comparison_df.to_string(index=False))
        
        # Find best performing strategy
        best_strategy = comparison_df.iloc[0]
        print(f"\n🏆 BEST PERFORMING STRATEGY: {best_strategy['Strategy']}")
        print(f"   Average Return: {best_strategy['Avg_Return_%']}%")
        print(f"   Profitable on {best_strategy['Profitable_Sources']} data sources")
        print(f"   Average Sharpe: {best_strategy['Avg_Sharpe']}")
        
        # Performance insights
        print("\n💡 PERFORMANCE INSIGHTS:")
        
        # Check which strategies are consistently profitable
        consistently_profitable = []
        for _, row in comparison_df.iterrows():
            profitable_ratio = eval(row['Profitable_Sources'].split('/')[0]) / eval(row['Profitable_Sources'].split('/')[1])
            if profitable_ratio > 0.5:
                consistently_profitable.append(row['Strategy'])
        
        if consistently_profitable:
            print(f"   Consistently Profitable (>50% markets): {', '.join(consistently_profitable)}")
        
        # Check for best risk-adjusted returns
        if 'Avg_Sharpe' in comparison_df.columns:
            best_sharpe = comparison_df.nlargest(3, 'Avg_Sharpe')['Strategy'].tolist()
            print(f"   Best Risk-Adjusted (Sharpe): {', '.join(best_sharpe)}")
        
        # Check for lowest drawdowns
        if 'Avg_Max_DD_%' in comparison_df.columns:
            lowest_dd = comparison_df.nsmallest(3, 'Avg_Max_DD_%')['Strategy'].tolist()
            print(f"   Lowest Drawdowns: {', '.join(lowest_dd)}")

print(f"\n⏱️ Total execution time: {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)")
print("\n📁 All results saved in: ./results/")

# Create a combined summary if requested
if len(all_summaries) > 0:
    print("\n📊 Creating master summary file...")
    
    # Create results directory if it doesn't exist
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Combine all results with strategy name column
    combined_results = []
    for strategy_name, df in all_summaries.items():
        df_copy = df.copy()
        # Simplify strategy name
        df_copy['Strategy'] = strategy_name.replace('ThreeMountainsRivers', 'TMR_')
        combined_results.append(df_copy)
    
    if combined_results:
        master_df = pd.concat(combined_results, ignore_index=True)
        master_file = os.path.join(results_dir, 'THREE_MOUNTAINS_RIVERS_ALL_RESULTS.csv')
        master_df.to_csv(master_file, index=False)
        print(f"✅ Master summary saved to: {master_file}")
        
        # Also save the comparison summary
        if comparison_data:
            comparison_file = os.path.join(results_dir, 'THREE_MOUNTAINS_RIVERS_COMPARISON.csv')
            comparison_df.to_csv(comparison_file, index=False)
            print(f"✅ Comparison summary saved to: {comparison_file}")

print("\n" + "="*80)
print("THREE MOUNTAINS & THREE RIVERS TESTING COMPLETE")
print("="*80)

# Print pattern trading tips
print("\n📚 PATTERN TRADING TIPS:")
print("1. Three Mountains (Triple Top) works best in overbought conditions")
print("2. Three Rivers (Triple Bottom) works best in oversold conditions")
print("3. Volume confirmation improves pattern reliability")
print("4. Combine with momentum indicators for better timing")
print("5. Use appropriate stop losses above peaks or below troughs")
print("6. Consider market conditions when selecting strategy variation")
print("="*80)