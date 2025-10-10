"""
Bollinger + RSI Strategy Suite Tester
=====================================

This script runs all 4 Bollinger + RSI strategy variations on multiple data sources
and generates a comprehensive comparison report.

Strategy Variations:
1. Base - Original BB + RSI strategy
2. MFI - Enhanced with Money Flow Index
3. ADX - Enhanced with Average Directional Index
4. Kalman - Enhanced with Kalman Filter for noise reduction
"""

import pandas as pd
import numpy as np
import os
import time
from datetime import datetime
import sys

# Add parent directory to path for multi_data_tester
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data

# Import all strategy classes
from bb_rsi_base import BollingerRSIBase
from bb_rsi_mfi import BollingerRSIMFI
from bb_rsi_adx import BollingerRSIADX
from bb_rsi_kalman import BollingerRSIKalman

print("🚀 Moon Dev's Bollinger + RSI Strategy Suite Testing... 🌙")
print("="*80)

# Define all strategies to test
strategies = {
    'BollingerRSIBase': BollingerRSIBase,
    'BollingerRSIMFI': BollingerRSIMFI,
    'BollingerRSIADX': BollingerRSIADX,
    'BollingerRSIKalman': BollingerRSIKalman
}

# Run each strategy
all_results = {}
start_time = time.time()

for i, (name, strategy_class) in enumerate(strategies.items(), 1):
    print(f"\n[{i}/4] Testing {name}...")
    print("-" * 60)

    try:
        # Test strategy on all data sources
        results = test_on_all_data(strategy_class, name, verbose=False)

        if results is not None:
            all_results[name] = results
            print(f"✅ {name} completed - {len(results)} datasets tested")

            # Show quick summary
            avg_return = results['Return_%'].mean()
            avg_sharpe = results[results['Sharpe'] != 0]['Sharpe'].mean()
            total_trades = results['Trades'].sum()

            print(f"   📊 Avg Return: {avg_return:.2f}%")
            print(f"   📈 Avg Sharpe: {avg_sharpe:.3f}")
            print(f"   🔄 Total Trades: {total_trades}")
        else:
            print(f"❌ {name} failed")

    except Exception as e:
        print(f"❌ Error testing {name}: {e}")

# Generate comparison report
if all_results:
    print("\n" + "="*80)
    print("GENERATING COMPREHENSIVE COMPARISON REPORT")
    print("="*80)

    # Combine all results
    comparison_data = []

    for strategy_name, results in all_results.items():
        for _, row in results.iterrows():
            row_data = row.to_dict()
            row_data['Strategy'] = strategy_name
            comparison_data.append(row_data)

    # Create comprehensive DataFrame
    comparison_df = pd.DataFrame(comparison_data)

    # Reorder columns to put Strategy first
    cols = ['Strategy'] + [col for col in comparison_df.columns if col != 'Strategy']
    comparison_df = comparison_df[cols]

    # Save comprehensive comparison
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = "./results"
    os.makedirs(results_dir, exist_ok=True)

    comparison_file = f"{results_dir}/BollingerRSI_Comparison_{timestamp}.csv"
    comparison_df.to_csv(comparison_file, index=False)

    print(f"📊 Comprehensive comparison saved: {comparison_file}")

    # Generate summary statistics
    print("\n" + "="*80)
    print("STRATEGY PERFORMANCE SUMMARY")
    print("="*80)

    summary_stats = []

    for strategy in strategies.keys():
        strategy_data = comparison_df[comparison_df['Strategy'] == strategy]

        if len(strategy_data) > 0:
            stats = {
                'Strategy': strategy,
                'Avg_Return_%': strategy_data['Return_%'].mean(),
                'Median_Return_%': strategy_data['Return_%'].median(),
                'Best_Return_%': strategy_data['Return_%'].max(),
                'Worst_Return_%': strategy_data['Return_%'].min(),
                'Avg_Sharpe': strategy_data[strategy_data['Sharpe'] != 0]['Sharpe'].mean(),
                'Avg_Win_Rate_%': strategy_data[strategy_data['Win_Rate_%'] > 0]['Win_Rate_%'].mean(),
                'Total_Trades': strategy_data['Trades'].sum(),
                'Avg_Trades_Per_Dataset': strategy_data['Trades'].mean(),
                'Datasets_Tested': len(strategy_data),
                'Profitable_Datasets': len(strategy_data[strategy_data['Return_%'] > 0]),
                'Win_Rate_by_Dataset_%': (len(strategy_data[strategy_data['Return_%'] > 0]) / len(strategy_data)) * 100
            }
            summary_stats.append(stats)

    summary_df = pd.DataFrame(summary_stats)

    # Save summary
    summary_file = f"{results_dir}/BollingerRSI_Summary_{timestamp}.csv"
    summary_df.to_csv(summary_file, index=False)

    print(f"📈 Strategy summary saved: {summary_file}")

    # Display summary table
    print("\nSTRATEGY RANKING BY PERFORMANCE:")
    print("-" * 80)

    # Sort by average return
    summary_display = summary_df.sort_values('Avg_Return_%', ascending=False)

    print(summary_display[['Strategy', 'Avg_Return_%', 'Avg_Sharpe', 'Avg_Win_Rate_%',
                          'Total_Trades', 'Profitable_Datasets', 'Win_Rate_by_Dataset_%']].to_string(index=False))

    # Best performing strategy analysis
    best_strategy = summary_display.iloc[0]['Strategy']
    best_return = summary_display.iloc[0]['Avg_Return_%']

    print(f"\n🏆 BEST PERFORMING STRATEGY: {best_strategy}")
    print(f"📊 Average Return: {best_return:.2f}%")
    print(f"📈 Profitable on {summary_display.iloc[0]['Profitable_Datasets']:.0f}/{summary_display.iloc[0]['Datasets_Tested']:.0f} datasets")

    # Data source analysis
    print("\n" + "="*80)
    print("BEST PERFORMING DATA SOURCES (across all strategies)")
    print("="*80)

    data_source_performance = comparison_df.groupby('Data_Source').agg({
        'Return_%': 'mean',
        'Sharpe': lambda x: x[x != 0].mean(),
        'Win_Rate_%': lambda x: x[x > 0].mean(),
        'Trades': 'mean'
    }).round(2)

    data_source_performance = data_source_performance.sort_values('Return_%', ascending=False)
    print(data_source_performance.head(10).to_string())

    elapsed_time = time.time() - start_time
    print(f"\n⏱️  Total testing time: {elapsed_time/60:.1f} minutes")
    print(f"📁 All results saved in: {results_dir}/")

else:
    print("\n❌ No results generated. Check strategy implementations.")

print("\n🌙 Bollinger + RSI Strategy Suite Testing Complete! 🌙")