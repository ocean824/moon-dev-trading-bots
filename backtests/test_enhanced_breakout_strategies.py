"""
Test all enhanced breakout strategies
=====================================
This script tests all 6 enhanced breakout strategies on multiple data sources
and compiles the results into a summary.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data

# Import all the enhanced breakout strategies
from volatility_breakout_kalman import VolatilityBreakoutKalman
from volatility_breakout_adx import VolatilityBreakoutADX
from volatility_breakout_mfi import VolatilityBreakoutMFI
from false_breakout_kalman import FalseBreakoutKalman
from false_breakout_adx import FalseBreakoutADX
from false_breakout_mfi import FalseBreakoutMFI

print("🚀 Moon Dev's Enhanced Breakout Strategies Test Suite 🌙")
print("="*80)
print(f"Testing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# Define strategies to test
STRATEGIES = {
    'VolatilityBreakoutKalman': VolatilityBreakoutKalman,
    'VolatilityBreakoutADX': VolatilityBreakoutADX,
    'VolatilityBreakoutMFI': VolatilityBreakoutMFI,
    'FalseBreakoutKalman': FalseBreakoutKalman,
    'FalseBreakoutADX': FalseBreakoutADX,
    'FalseBreakoutMFI': FalseBreakoutMFI
}

# Store all results
all_results = []

# Test each strategy
for strategy_name, strategy_class in STRATEGIES.items():
    print(f"\n{'='*80}")
    print(f"🔍 Testing {strategy_name}...")
    print(f"{'='*80}")
    
    try:
        # Test on all data sources
        results = test_on_all_data(strategy_class, strategy_name, optimize=False)
        
        if results is not None and not results.empty:
            # Add strategy name to results
            results['Strategy'] = strategy_name
            all_results.append(results)
            
            # Print summary for this strategy
            print(f"\n✅ {strategy_name} Results Summary:")
            print(f"   Data Sources Tested: {len(results)}")
            print(f"   Avg Return: {results['Return_%'].mean():.2f}%")
            print(f"   Avg Sharpe: {results['Sharpe'].mean():.2f}")
            print(f"   Avg Win Rate: {results['Win_Rate_%'].mean():.2f}%")
            print(f"   Total Trades: {results['Trades'].sum()}")
        else:
            print(f"❌ No results for {strategy_name}")
            
    except Exception as e:
        print(f"❌ Error testing {strategy_name}: {e}")

# Combine all results
if all_results:
    print("\n" + "="*80)
    print("📊 COMPILING FINAL RESULTS...")
    print("="*80)
    
    combined_df = pd.concat(all_results, ignore_index=True)
    
    # Save combined results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'./results/ENHANCED_BREAKOUT_STRATEGIES_{timestamp}.csv'
    
    # Create results directory if it doesn't exist
    os.makedirs('./results', exist_ok=True)
    
    # Save to CSV
    combined_df.to_csv(results_file, index=False)
    print(f"\n✅ All results saved to: {results_file}")
    
    # Print overall summary
    print("\n" + "="*80)
    print("🏆 OVERALL PERFORMANCE SUMMARY")
    print("="*80)
    
    # Group by strategy and calculate averages
    strategy_summary = combined_df.groupby('Strategy').agg({
        'Return_%': 'mean',
        'Sharpe': 'mean',
        'Sortino': 'mean',
        'Win_Rate_%': 'mean',
        'Max_DD_%': 'mean',
        'Trades': 'sum',
        'Profit_Factor': 'mean'
    }).round(2)
    
    # Sort by Return
    strategy_summary = strategy_summary.sort_values('Return_%', ascending=False)
    
    print("\nAverage Performance Across All Data Sources:")
    print(strategy_summary)
    
    # Find best performing strategy
    print("\n" + "="*80)
    print("🥇 BEST PERFORMING STRATEGIES")
    print("="*80)
    
    # Best by Return
    best_return = strategy_summary['Return_%'].idxmax()
    print(f"\n💰 Best Return: {best_return}")
    print(f"   Average Return: {strategy_summary.loc[best_return, 'Return_%']:.2f}%")
    
    # Best by Sharpe
    best_sharpe = strategy_summary['Sharpe'].idxmax()
    print(f"\n📈 Best Sharpe: {best_sharpe}")
    print(f"   Average Sharpe: {strategy_summary.loc[best_sharpe, 'Sharpe']:.2f}")
    
    # Best by Win Rate
    best_winrate = strategy_summary['Win_Rate_%'].idxmax()
    print(f"\n🎯 Best Win Rate: {best_winrate}")
    print(f"   Average Win Rate: {strategy_summary.loc[best_winrate, 'Win_Rate_%']:.2f}%")
    
    # Best by Profit Factor
    best_pf = strategy_summary['Profit_Factor'].idxmax()
    print(f"\n💎 Best Profit Factor: {best_pf}")
    print(f"   Average Profit Factor: {strategy_summary.loc[best_pf, 'Profit_Factor']:.2f}")
    
    # Category Analysis
    print("\n" + "="*80)
    print("📊 CATEGORY ANALYSIS")
    print("="*80)
    
    # Volatility Breakout strategies
    vol_strategies = [s for s in strategy_summary.index if 'Volatility' in s]
    if vol_strategies:
        vol_avg_return = strategy_summary.loc[vol_strategies, 'Return_%'].mean()
        vol_avg_sharpe = strategy_summary.loc[vol_strategies, 'Sharpe'].mean()
        print(f"\n🌊 Volatility Breakout Strategies:")
        print(f"   Average Return: {vol_avg_return:.2f}%")
        print(f"   Average Sharpe: {vol_avg_sharpe:.2f}")
    
    # False Breakout strategies
    false_strategies = [s for s in strategy_summary.index if 'False' in s]
    if false_strategies:
        false_avg_return = strategy_summary.loc[false_strategies, 'Return_%'].mean()
        false_avg_sharpe = strategy_summary.loc[false_strategies, 'Sharpe'].mean()
        print(f"\n🔄 False Breakout Strategies:")
        print(f"   Average Return: {false_avg_return:.2f}%")
        print(f"   Average Sharpe: {false_avg_sharpe:.2f}")
    
    # Indicator comparison
    print("\n" + "="*80)
    print("🔬 INDICATOR COMPARISON")
    print("="*80)
    
    # Kalman strategies
    kalman_strategies = [s for s in strategy_summary.index if 'Kalman' in s]
    if kalman_strategies:
        kalman_avg_return = strategy_summary.loc[kalman_strategies, 'Return_%'].mean()
        print(f"\n🎯 Kalman Filter Strategies: {kalman_avg_return:.2f}% avg return")
    
    # ADX strategies
    adx_strategies = [s for s in strategy_summary.index if 'ADX' in s]
    if adx_strategies:
        adx_avg_return = strategy_summary.loc[adx_strategies, 'Return_%'].mean()
        print(f"📊 ADX Strategies: {adx_avg_return:.2f}% avg return")
    
    # MFI strategies
    mfi_strategies = [s for s in strategy_summary.index if 'MFI' in s]
    if mfi_strategies:
        mfi_avg_return = strategy_summary.loc[mfi_strategies, 'Return_%'].mean()
        print(f"💰 MFI Strategies: {mfi_avg_return:.2f}% avg return")
    
    print("\n" + "="*80)
    print("✅ Enhanced Breakout Strategies Testing Complete!")
    print("="*80)
    
else:
    print("\n❌ No results to compile")

print(f"\n🌙 Moon Dev's Enhanced Breakout Test Suite Complete! 🚀")