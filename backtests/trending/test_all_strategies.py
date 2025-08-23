#!/usr/bin/env python3
"""
Run all trending strategies and display summary results
"""

import pandas as pd
import os
import sys
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all trending strategies
from trending_ma200_long import MA200LongTrend
from trending_golden_cross import GoldenCrossTrend
from trending_donchian_long import DonchianLongTrend
from trending_dual_ma import DualMATrend
from trending_rsi_ma import RSIMATrend
from trending_bollinger_trend import BollingerTrend
from trending_adx_ma import ADXMATrend
from trending_macd_adx import MACDADXTrend
from trending_volume_ma import VolumeMATrend
from trending_fast_ma_adx import FastMAADXTrend
from trending_fast_bb_adx import FastBBADXTrend
from trending_fast_macd_adx import FastMACDADXTrend
from multi_data_tester import test_on_all_data

# List of all strategies organized by category
strategies = [
    # Category 1: Slow Trend Following - Long Only
    (MA200LongTrend, 'MA200LongTrend', 'Slow Long-Only'),
    (GoldenCrossTrend, 'GoldenCrossTrend', 'Slow Long-Only'),
    (DonchianLongTrend, 'DonchianLongTrend', 'Slow Long-Only'),
    
    # Category 2: Slow Trend Following - Long and Short
    (DualMATrend, 'DualMATrend', 'Slow Long/Short'),
    (RSIMATrend, 'RSIMATrend', 'Slow Long/Short'),
    (BollingerTrend, 'BollingerTrend', 'Slow Long/Short'),
    
    # Category 3: Slow Trend with Trend Strength
    (ADXMATrend, 'ADXMATrend', 'Slow w/ Strength'),
    (MACDADXTrend, 'MACDADXTrend', 'Slow w/ Strength'),
    (VolumeMATrend, 'VolumeMATrend', 'Slow w/ Strength'),
    
    # Category 4: Fast Trend with Trend Strength
    (FastMAADXTrend, 'FastMAADXTrend', 'Fast w/ Strength'),
    (FastBBADXTrend, 'FastBBADXTrend', 'Fast w/ Strength'),
    (FastMACDADXTrend, 'FastMACDADXTrend', 'Fast w/ Strength')
]

print("="*80)
print("TRENDING STRATEGIES - COMPREHENSIVE TEST SUITE")
print("="*80)
print(f"\nTesting {len(strategies)} trending strategies across all data sources...")
print("\nCategories:")
print("1. Slow Trend Following - Long Only (3 strategies)")
print("2. Slow Trend Following - Long/Short (3 strategies)")
print("3. Slow Trend with Trend Strength (3 strategies)")
print("4. Fast Trend with Trend Strength (3 strategies)")

# Track overall stats
total_start = time.time()
all_summaries = {}
category_performance = {}

for i, (strategy_class, strategy_name, category) in enumerate(strategies, 1):
    print(f"\n[{i}/{len(strategies)}] Testing: {strategy_name} ({category})")
    print("-"*40)
    
    start_time = time.time()
    
    try:
        # Run the strategy and capture results (verbose=False to suppress individual stats)
        results = test_on_all_data(strategy_class, strategy_name, verbose=False)
        
        elapsed = time.time() - start_time
        
        if results is not None:
            # Store the summary
            all_summaries[strategy_name] = results
            
            # Track category performance
            if category not in category_performance:
                category_performance[category] = []
            category_performance[category].append({
                'strategy': strategy_name,
                'avg_return': results['Return_%'].mean(),
                'profitable_count': (results['Return_%'] > 0).sum(),
                'total_sources': len(results)
            })
            
            print(f"\nCompleted in {elapsed:.1f} seconds")
            print(f"Results saved to: ./results/{strategy_name}.csv")
            
            # Display FULL summary table with all data sources
            print("\nFULL SUMMARY:")
            print(results[['Data_Source', 'Return_%', 'Buy_Hold_%', 'Sharpe', 'Sortino', 
                          'Max_DD_%', 'Profit_Factor', 'Expectancy_%', 'Trades', 'Win_Rate_%']].to_string())
            
            # Show quick stats
            if not results.empty:
                avg_return = results['Return_%'].mean()
                positive_returns = (results['Return_%'] > 0).sum()
                total_data_sources = len(results)
                avg_sharpe = results['Sharpe'].mean()
                
                print(f"\nAverage Return: {avg_return:.2f}%")
                print(f"Average Sharpe: {avg_sharpe:.3f}")
                print(f"Profitable on {positive_returns}/{total_data_sources} data sources")
        else:
            print(f"Warning: {strategy_name} returned no results")
            
    except Exception as e:
        print(f"Error running {strategy_name}: {e}")

# Final summary
total_elapsed = time.time() - total_start

print("\n" + "="*80)
print("FINAL SUMMARY - ALL TRENDING STRATEGIES")
print("="*80)

# Display category performance summary
print("\nCATEGORY PERFORMANCE:")
print("-"*40)
for category, strategies_list in category_performance.items():
    avg_category_return = sum(s['avg_return'] for s in strategies_list) / len(strategies_list)
    total_profitable = sum(s['profitable_count'] for s in strategies_list)
    total_tests = sum(s['total_sources'] for s in strategies_list)
    
    print(f"\n{category}:")
    print(f"  Average Return: {avg_category_return:.2f}%")
    print(f"  Win Rate: {total_profitable}/{total_tests} ({100*total_profitable/total_tests:.1f}%)")
    print(f"  Strategies: {', '.join(s['strategy'] for s in strategies_list)}")

# Display comparison table of all strategies
if len(all_summaries) > 0:
    print("\n" + "="*80)
    print("STRATEGY COMPARISON TABLE")
    print("="*80)
    
    comparison_data = []
    for strategy_name, results in all_summaries.items():
        if not results.empty:
            # Find the category
            category = next((cat for _, name, cat in strategies if name == strategy_name), 'Unknown')
            
            comparison_data.append({
                'Strategy': strategy_name,
                'Category': category,
                'Avg_Return_%': round(results['Return_%'].mean(), 2),
                'Best_Return_%': round(results['Return_%'].max(), 2),
                'Worst_Return_%': round(results['Return_%'].min(), 2),
                'Win_Rate': f"{(results['Return_%'] > 0).sum()}/{len(results)}",
                'Avg_Sharpe': round(results['Sharpe'].mean(), 3),
                'Avg_Win_%': round(results['Win_Rate_%'].mean(), 1),
                'Total_Trades': results['Trades'].sum(),
                'Avg_DD_%': round(results['Max_DD_%'].mean(), 2)
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        # Sort by average return
        comparison_df = comparison_df.sort_values('Avg_Return_%', ascending=False)
        print("\nTop Performers by Average Return:")
        print(comparison_df.to_string(index=False))
        
        # Show best strategies per category
        print("\n" + "="*80)
        print("BEST STRATEGY PER CATEGORY")
        print("="*80)
        for category in comparison_df['Category'].unique():
            cat_df = comparison_df[comparison_df['Category'] == category]
            best = cat_df.iloc[0]
            print(f"\n{category}: {best['Strategy']}")
            print(f"  Average Return: {best['Avg_Return_%']}%")
            print(f"  Sharpe Ratio: {best['Avg_Sharpe']}")
            print(f"  Win Rate: {best['Win_Rate']}")

print(f"\nTotal execution time: {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)")
print("\nAll results saved in: ./results/")

# Create a combined summary
if len(all_summaries) > 0:
    print("\nCombining all results into a master summary...")
    
    # Create results directory if it doesn't exist
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Combine all results with strategy name and category columns
    combined_results = []
    for strategy_name, df in all_summaries.items():
        df_copy = df.copy()
        df_copy['Strategy'] = strategy_name
        # Add category
        category = next((cat for _, name, cat in strategies if name == strategy_name), 'Unknown')
        df_copy['Category'] = category
        combined_results.append(df_copy)
    
    if combined_results:
        master_df = pd.concat(combined_results, ignore_index=True)
        master_file = os.path.join(results_dir, 'ALL_TRENDING_STRATEGIES.csv')
        master_df.to_csv(master_file, index=False)
        print(f"Master summary saved to: {master_file}")
        
        # Create category summary
        category_summary = master_df.groupby('Category').agg({
            'Return_%': ['mean', 'std', 'min', 'max'],
            'Sharpe': 'mean',
            'Max_DD_%': 'mean',
            'Win_Rate_%': 'mean',
            'Trades': 'sum'
        }).round(2)
        
        category_file = os.path.join(results_dir, 'CATEGORY_SUMMARY.csv')
        category_summary.to_csv(category_file)
        print(f"Category summary saved to: {category_file}")

print("="*80)
print("TESTING COMPLETE!")
print("="*80)