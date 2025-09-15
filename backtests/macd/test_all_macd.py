"""
Test All MACD Strategies
========================
Runs all MACD strategy variations and compares results
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backtests.multi_data_tester import test_on_all_data

# Import all MACD strategies
from macd_base import MACDBase
from macd_kalman import MACDKalman
from macd_fibonacci import MACDFibonacci
from macd_ema import MACDEMA
from macd_adx import MACDADX
from macd_mfi import MACDMFI
from macd_bollinger import MACDBollinger

print("\n" + "="*80)
print("TESTING ALL MACD STRATEGIES ON ALL DATA SOURCES")
print("="*80)

# Define all strategies to test
strategies = {
    'MACDBase': MACDBase,
    'MACDKalman': MACDKalman,
    'MACDFibonacci': MACDFibonacci,
    'MACDEMA': MACDEMA,
    'MACDADX': MACDADX,
    'MACDMFI': MACDMFI,
    'MACDBollinger': MACDBollinger
}

print(f"\n📊 Testing {len(strategies)} MACD strategies...")
print("Strategies to test:")
for name in strategies.keys():
    print(f"  - {name}")

# Test all strategies (without optimization for faster results)
print("\n🚀 Starting multi-data testing for all strategies...")

# Collect all results
all_results = []

for strategy_name, strategy_class in strategies.items():
    print(f"\n{'='*60}")
    print(f"Testing {strategy_name}...")
    print('='*60)
    
    # Test strategy on all data sources
    results = test_on_all_data(strategy_class, strategy_name, optimize=False, verbose=False)
    
    # Add results to collection if available
    if results is not None:
        results['Strategy'] = strategy_name
        all_results.append(results)

# Combine all results
if all_results:
    combined_results = pd.concat(all_results, ignore_index=True)
    
    print("\n" + "="*80)
    print("SUMMARY OF RESULTS")
    print("="*80)
    
    # Group by strategy and calculate average metrics
    strategy_summary = combined_results.groupby('Strategy').agg({
        'Return_%': 'mean',
        'Sharpe': 'mean',
        'Sortino': 'mean',
        'Max_DD_%': 'mean',
        'Win_Rate_%': 'mean',
        'Trades': 'sum',
        'Profit_Factor': 'mean'
    }).round(2)
    
    # Sort by Sortino ratio (best risk-adjusted returns)
    strategy_summary = strategy_summary.sort_values('Sortino', ascending=False)
    
    print("\n📊 Average Performance Across All Data Sources:")
    print(strategy_summary)
    
    print("\n🏆 Best Performing Strategy (by Sortino Ratio):")
    if len(strategy_summary) > 0:
        best_strategy = strategy_summary.index[0]
        print(f"   {best_strategy}")
        print(f"   - Avg Return: {strategy_summary.loc[best_strategy, 'Return_%']:.2f}%")
        print(f"   - Avg Sharpe: {strategy_summary.loc[best_strategy, 'Sharpe']:.2f}")
        print(f"   - Avg Sortino: {strategy_summary.loc[best_strategy, 'Sortino']:.2f}")
        print(f"   - Avg Max DD: {strategy_summary.loc[best_strategy, 'Max_DD_%']:.2f}%")
        print(f"   - Avg Win Rate: {strategy_summary.loc[best_strategy, 'Win_Rate_%']:.2f}%")
        print(f"   - Total Trades: {strategy_summary.loc[best_strategy, 'Trades']:.0f}")
    
    # Find best strategy for each data source
    print("\n📈 Best Strategy by Data Source:")
    best_by_source = combined_results.loc[combined_results.groupby('Data_Source')['Sortino'].idxmax()]
    for _, row in best_by_source.iterrows():
        print(f"   {row['Data_Source']}: {row['Strategy']} (Sortino: {row['Sortino']:.2f})")
    
    # Performance consistency analysis
    print("\n📊 Performance Consistency (Standard Deviation of Returns):")
    consistency = combined_results.groupby('Strategy')['Return_%'].std().sort_values()
    for strategy, std in consistency.items():
        print(f"   {strategy}: {std:.2f}% std dev")
    
    print("\n✅ Testing complete! Check the results folder for detailed CSV files.")
    
    # Save summary to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_file = f'./results/macd_summary_{timestamp}.csv'
    strategy_summary.to_csv(summary_file)
    print(f"\n📁 Summary saved to: {summary_file}")
    
    # Save full results
    full_results_file = f'./results/macd_all_results_{timestamp}.csv'
    combined_results.to_csv(full_results_file, index=False)
    print(f"📁 Full results saved to: {full_results_file}")
    
else:
    print("\n❌ No results generated. Please check for errors above.")