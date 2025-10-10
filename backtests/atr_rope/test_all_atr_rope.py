"""
Test All ATR Rope Strategies
=============================
Runs all ATR Rope strategy variations on multiple datasets and saves results.
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backtests.multi_data_tester import test_on_all_data

# Import all strategy classes
from atr_rope_base import ATRRopeBase
from atr_rope_rsi import ATRRopeRSI
from atr_rope_volume import ATRRopeVolume
from atr_rope_macd import ATRRopeMACD
from atr_rope_mfi import ATRRopeMFI

print("="*80)
print("🚀 TESTING ALL ATR ROPE STRATEGIES ON ALL DATA SOURCES 🚀")
print("="*80)

# Dictionary of all strategies to test
strategies = {
    'ATRRopeBase': ATRRopeBase,
    'ATRRopeRSI': ATRRopeRSI,
    'ATRRopeVolume': ATRRopeVolume,
    'ATRRopeMACD': ATRRopeMACD,
    'ATRRopeMFI': ATRRopeMFI
}

# Test each strategy
all_results = []
for name, strategy_class in strategies.items():
    print(f"\n{'='*60}")
    print(f"Testing {name}...")
    print(f"{'='*60}")

    try:
        # Test on all data sources
        results = test_on_all_data(strategy_class, name, verbose=False)

        if results is not None:
            # Add strategy name column
            results['Strategy'] = name
            all_results.append(results)
            print(f"✅ {name} testing complete!")

            # Print summary statistics
            print(f"\nSummary for {name}:")
            print(f"Average Return: {results['Return_%'].mean():.2f}%")
            print(f"Average Sharpe: {results['Sharpe'].mean():.3f}")
            print(f"Average Win Rate: {results['Win_Rate_%'].mean():.2f}%")
            print(f"Total Trades: {results['Trades'].sum()}")
        else:
            print(f"❌ {name} testing failed!")

    except Exception as e:
        print(f"❌ Error testing {name}: {e}")

# Combine all results and save comparison
if all_results:
    print("\n" + "="*80)
    print("CREATING COMPARISON REPORT")
    print("="*80)

    # Combine all dataframes
    combined_df = pd.concat(all_results, ignore_index=True)

    # Save combined results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_file = f"results/atr_rope_comparison_{timestamp}.csv"
    combined_df.to_csv(comparison_file, index=False)
    print(f"✅ Comparison saved to: {comparison_file}")

    # Create summary report
    print("\n" + "="*60)
    print("STRATEGY PERFORMANCE SUMMARY")
    print("="*60)

    # Group by strategy and calculate averages
    summary = combined_df.groupby('Strategy').agg({
        'Return_%': 'mean',
        'Sharpe': 'mean',
        'Sortino': 'mean',
        'Max_DD_%': 'mean',
        'Win_Rate_%': 'mean',
        'Profit_Factor': 'mean',
        'Expectancy_%': 'mean',
        'Trades': 'sum'
    }).round(2)

    # Sort by return
    summary = summary.sort_values('Return_%', ascending=False)

    print("\nAverage Performance Across All Data Sources:")
    print(summary)

    # Find best performing strategy for each data source
    print("\n" + "="*60)
    print("BEST STRATEGY PER DATA SOURCE")
    print("="*60)

    best_per_source = combined_df.loc[combined_df.groupby('Data_Source')['Return_%'].idxmax()]
    print(best_per_source[['Data_Source', 'Strategy', 'Return_%', 'Sharpe', 'Win_Rate_%']])

    # Overall best performing configuration
    print("\n" + "="*60)
    print("TOP 10 BEST PERFORMING CONFIGURATIONS")
    print("="*60)

    top_10 = combined_df.nlargest(10, 'Return_%')[['Strategy', 'Data_Source', 'Return_%', 'Sharpe', 'Win_Rate_%', 'Trades']]
    print(top_10)

    # Strategy ranking
    print("\n" + "="*60)
    print("OVERALL STRATEGY RANKING")
    print("="*60)

    ranking = summary[['Return_%', 'Sharpe', 'Win_Rate_%', 'Trades']].sort_values('Return_%', ascending=False)
    for i, (strategy, row) in enumerate(ranking.iterrows(), 1):
        print(f"{i}. {strategy}: Return={row['Return_%']:.2f}%, Sharpe={row['Sharpe']:.3f}, Win Rate={row['Win_Rate_%']:.2f}%, Total Trades={row['Trades']:.0f}")

print("\n" + "="*80)
print("🎉 ALL TESTING COMPLETE! 🎉")
print("="*80)