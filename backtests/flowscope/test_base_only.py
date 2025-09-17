#!/usr/bin/env python3
"""
Test just the FlowScopeBase strategy on all datasets
"""

import sys
import os
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flowscope_base import FlowScopeBase
from multi_data_tester import test_on_all_data

print("="*80)
print("TESTING FLOWSCOPE BASE STRATEGY ON ALL DATA SOURCES")
print("="*80)

start_time = time.time()

# Run the test with verbose=False for speed
results = test_on_all_data(FlowScopeBase, 'FlowScopeBase', verbose=False)

elapsed = time.time() - start_time

if results is not None:
    print(f"\n✅ Testing completed in {elapsed:.1f} seconds")
    print(f"Results saved to: ./results/FlowScopeBase.csv")

    # Show summary
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)

    print(f"Total Data Sources Tested: {len(results)}")
    print(f"Average Return: {results['Return_%'].mean():.2f}%")
    print(f"Best Return: {results['Return_%'].max():.2f}%")
    print(f"Worst Return: {results['Return_%'].min():.2f}%")
    print(f"Profitable Sources: {(results['Return_%'] > 0).sum()}/{len(results)}")
    print(f"Average Win Rate: {results['Win_Rate_%'].mean():.1f}%")
    print(f"Total Trades: {results['Trades'].sum()}")
    print(f"Average Sharpe: {results['Sharpe'].mean():.3f}")
    print(f"Average Max Drawdown: {results['Max_DD_%'].mean():.2f}%")

    # Show best performing data sources
    print("\n" + "="*60)
    print("TOP 5 BEST PERFORMING DATA SOURCES")
    print("="*60)

    top_5 = results.nlargest(5, 'Return_%')[['Data_Source', 'Return_%', 'Sharpe', 'Win_Rate_%', 'Trades']]
    print(top_5.to_string(index=False))

    # Show worst performing data sources
    print("\n" + "="*60)
    print("TOP 5 WORST PERFORMING DATA SOURCES")
    print("="*60)

    bottom_5 = results.nsmallest(5, 'Return_%')[['Data_Source', 'Return_%', 'Sharpe', 'Win_Rate_%', 'Trades']]
    print(bottom_5.to_string(index=False))

else:
    print(f"⚠️ No results generated")

print("\n" + "="*80)