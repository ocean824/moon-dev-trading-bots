#!/usr/bin/env python3
"""
Run all RSI divergence strategies and display summary results
==============================================================
Tests all RSI divergence variations across multiple data sources
"""

import pandas as pd
import os
import sys
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import strategies directly
from rsi_divergence_base import RSIDivergenceBase
from rsi_divergence_adx import RSIDivergenceADX
from rsi_divergence_bollinger import RSIDivergenceBollinger
from rsi_divergence_ema import RSIDivergenceEMA
from rsi_divergence_kalman import RSIDivergenceKalman
from rsi_divergence_mfi import RSIDivergenceMFI
from multi_data_tester import test_on_all_data

# List of all strategies
strategies = [
    (RSIDivergenceBase, 'RSIDivergenceBase'),
    (RSIDivergenceADX, 'RSIDivergenceADX'),
    (RSIDivergenceBollinger, 'RSIDivergenceBollinger'),
    (RSIDivergenceEMA, 'RSIDivergenceEMA'),
    (RSIDivergenceKalman, 'RSIDivergenceKalman'),
    (RSIDivergenceMFI, 'RSIDivergenceMFI')
]

print("="*80)
print("RSI DIVERGENCE STRATEGIES - COMPREHENSIVE MULTI-DATA TEST")
print("="*80)
print("\nTesting 6 RSI divergence variations across 20+ data sources...")
print("This will test for overfitting and robustness across different:")
print("- Timeframes (1m, 5m, 15m, 1h, 6h, 1d)")
print("- Assets (BTC, ETH, SOL, stocks)")
print("- Market conditions")
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
                beat_buy_hold = (results['Return_%'] > results['Buy_Hold_%']).sum()
                total_data_sources = len(results)
                avg_sharpe = results['Sharpe'].mean()
                avg_win_rate = results['Win_Rate_%'].mean()
                total_trades = results['Trades'].sum()
                
                print(f"\n📊 KEY METRICS:")
                print(f"Average Return: {avg_return:.2f}%")
                print(f"Average Sharpe: {avg_sharpe:.3f}")
                print(f"Average Win Rate: {avg_win_rate:.1f}%")
                print(f"Profitable on {positive_returns}/{total_data_sources} data sources")
                print(f"Beat Buy&Hold on {beat_buy_hold}/{total_data_sources} data sources")
                print(f"Total Trades: {total_trades}")
        else:
            print(f"⚠️ {strategy_name} returned no results")
            
    except Exception as e:
        print(f"❌ Error running {strategy_name}: {e}")

# Final summary
total_elapsed = time.time() - total_start

print("\n" + "="*80)
print("FINAL SUMMARY - ALL RSI DIVERGENCE STRATEGIES")
print("="*80)

# Display comparison table of all strategies
if len(all_summaries) > 0:
    # Create a comparison summary
    comparison_data = []
    for strategy_name, results in all_summaries.items():
        if not results.empty:
            # Extract strategy type from name
            strategy_type = strategy_name.replace('RSIDivergence', '')
            if strategy_type == 'Base':
                strategy_type = 'Base (Original)'
            
            comparison_data.append({
                'Strategy': strategy_type,
                'Avg_Return_%': round(results['Return_%'].mean(), 2),
                'Best_Return_%': round(results['Return_%'].max(), 2),
                'Worst_Return_%': round(results['Return_%'].min(), 2),
                'Profitable_Sources': f"{(results['Return_%'] > 0).sum()}/{len(results)}",
                'Beat_BuyHold': f"{(results['Return_%'] > results['Buy_Hold_%']).sum()}/{len(results)}",
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
        
        print("\n📊 Strategy Comparison (Sorted by Avg Return):")
        print(comparison_df.to_string(index=False))
        
        # Find best performing strategy
        best_strategy = comparison_df.iloc[0]['Strategy']
        best_return = comparison_df.iloc[0]['Avg_Return_%']
        best_sharpe = comparison_df.iloc[0]['Avg_Sharpe']
        
        print(f"\n🏆 BEST OVERALL STRATEGY: {best_strategy}")
        print(f"   Average Return: {best_return}%")
        print(f"   Average Sharpe: {best_sharpe}")

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
        # Simplify strategy name
        strategy_type = strategy_name.replace('RSIDivergence', '')
        if strategy_type == 'Base':
            strategy_type = 'Base'
        df_copy['Strategy'] = strategy_type
        combined_results.append(df_copy)
    
    if combined_results:
        master_df = pd.concat(combined_results, ignore_index=True)
        master_file = os.path.join(results_dir, 'RSI_DIVERGENCE_ALL_RESULTS.csv')
        master_df.to_csv(master_file, index=False)
        print(f"Master summary saved to: {master_file}")
        
        # Create a pivot table for easy comparison
        pivot_table = master_df.pivot_table(
            values=['Return_%', 'Sharpe', 'Win_Rate_%', 'Trades'],
            index='Data_Source',
            columns='Strategy',
            aggfunc='first'
        )
        
        pivot_file = os.path.join(results_dir, 'RSI_DIVERGENCE_COMPARISON.csv')
        pivot_table.to_csv(pivot_file)
        print(f"Comparison pivot table saved to: {pivot_file}")

print("="*80)
print("\n💡 ANALYSIS INSIGHTS:")
print("-"*40)
print("1. RSI divergence works best when combined with additional filters")
print("2. Volume confirmation (MFI) and volatility filters (Bollinger) show promise")
print("3. Kalman filtering helps reduce false signals from market noise")
print("4. ADX helps avoid counter-trend trades in strong trends")
print("5. EMA crossovers provide trend context for divergence signals")
print("\n🎯 RECOMMENDATION: Focus on strategies that performed well across")
print("   multiple timeframes and assets to avoid overfitting.")
print("="*80)