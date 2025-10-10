"""
Test All Supertrend Strategies
===============================
This script tests all Supertrend strategy variations on multiple datasets
and generates comprehensive comparison results.
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add parent directory to path for multi_data_tester
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data

# Import all strategy classes
from supertrend_base import SupertrendBase
from supertrend_rsi import SupertrendRSI
from supertrend_volume import SupertrendVolume
from supertrend_macd import SupertrendMACD
from supertrend_adx import SupertrendADX
from supertrend_mtf import SupertrendMTF

print("="*80)
print("🚀 TESTING ALL SUPERTREND STRATEGIES 🚀")
print("="*80)
print("\nDr. Data Dawg, let's test all Supertrend variations on multiple datasets!\n")

# Dictionary of all strategies to test
strategies = {
    'Supertrend_Base': SupertrendBase,
    'Supertrend_RSI': SupertrendRSI,
    'Supertrend_Volume': SupertrendVolume,
    'Supertrend_MACD': SupertrendMACD,
    'Supertrend_ADX': SupertrendADX,
    'Supertrend_MTF': SupertrendMTF
}

# Test each strategy
all_results = []
for name, strategy_class in strategies.items():
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print('='*60)

    try:
        # Test on all data sources
        results = test_on_all_data(strategy_class, name, cash=10000000, verbose=False)

        if results is not None and not results.empty:
            # Add strategy name column
            results['Strategy'] = name
            all_results.append(results)

            # Print summary statistics
            print(f"\n✅ {name} - Summary:")
            print(f"   Total datasets tested: {len(results)}")
            print(f"   Average Return: {results['Return_%'].mean():.2f}%")
            print(f"   Average Sharpe: {results['Sharpe'].mean():.3f}")
            print(f"   Average Win Rate: {results['Win_Rate_%'].mean():.2f}%")
            print(f"   Total Trades: {results['Trades'].sum()}")
        else:
            print(f"❌ {name} - No results generated")

    except Exception as e:
        print(f"❌ Error testing {name}: {str(e)}")

# Combine all results
if all_results:
    print("\n" + "="*80)
    print("📊 CREATING COMBINED RESULTS")
    print("="*80)

    # Combine all dataframes
    combined_df = pd.concat(all_results, ignore_index=True)

    # Save combined results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    combined_file = f'results/all_supertrend_strategies_{timestamp}.csv'
    combined_df.to_csv(combined_file, index=False)
    print(f"\n✅ Combined results saved to: {combined_file}")

    # Create strategy comparison summary
    print("\n" + "="*60)
    print("📈 STRATEGY PERFORMANCE COMPARISON")
    print("="*60)

    summary = combined_df.groupby('Strategy').agg({
        'Return_%': ['mean', 'median', 'std'],
        'Sharpe': ['mean', 'median'],
        'Sortino': ['mean', 'median'],
        'Max_DD_%': ['mean', 'max'],
        'Win_Rate_%': ['mean', 'median'],
        'Trades': ['sum', 'mean'],
        'Profit_Factor': ['mean', 'median']
    }).round(2)

    print("\n", summary)

    # Save summary
    summary_file = f'results/supertrend_summary_{timestamp}.csv'
    summary.to_csv(summary_file)
    print(f"\n✅ Summary saved to: {summary_file}")

    # Find best performing strategy by different metrics
    print("\n" + "="*60)
    print("🏆 BEST PERFORMING STRATEGIES")
    print("="*60)

    # By Return
    best_return = combined_df.groupby('Strategy')['Return_%'].mean().idxmax()
    best_return_value = combined_df.groupby('Strategy')['Return_%'].mean().max()
    print(f"Best Average Return: {best_return} ({best_return_value:.2f}%)")

    # By Sharpe
    best_sharpe = combined_df.groupby('Strategy')['Sharpe'].mean().idxmax()
    best_sharpe_value = combined_df.groupby('Strategy')['Sharpe'].mean().max()
    print(f"Best Average Sharpe: {best_sharpe} ({best_sharpe_value:.3f})")

    # By Win Rate
    best_winrate = combined_df.groupby('Strategy')['Win_Rate_%'].mean().idxmax()
    best_winrate_value = combined_df.groupby('Strategy')['Win_Rate_%'].mean().max()
    print(f"Best Average Win Rate: {best_winrate} ({best_winrate_value:.2f}%)")

    # By Profit Factor
    best_pf = combined_df.groupby('Strategy')['Profit_Factor'].mean().idxmax()
    best_pf_value = combined_df.groupby('Strategy')['Profit_Factor'].mean().max()
    print(f"Best Average Profit Factor: {best_pf} ({best_pf_value:.3f})")

    print("\n" + "="*80)
    print("✅ ALL SUPERTREND STRATEGIES TESTED SUCCESSFULLY!")
    print("="*80)

else:
    print("\n❌ No results were generated for any strategy")

print("\nDr. Data Dawg, the Supertrend strategy suite is complete! 🌙")