"""
Moon Dev's MA Crossover Strategy Comparison Script
===================================================

This script tests all variations of the MA Crossover strategy on multiple data sources
and creates a comprehensive comparison report.

Author: Moon Dev
Date: October 2025
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data, test_multiple_strategies
import pandas as pd
from datetime import datetime

# Import all strategy variations
from ma_crossover_base import MACrossoverBase
from ma_crossover_mfi import MACrossoverMFI
from ma_crossover_adx import MACrossoverADX
from ma_crossover_kalman import MACrossoverKalman

print("="*80)
print("🚀 MOON DEV'S MA CROSSOVER STRATEGY COMPARISON TEST 🚀")
print("="*80)
print("\nTesting 4 variations of MA Crossover strategy:")
print("1. Base - Classic MA Crossover")
print("2. MFI - Money Flow Index Enhanced")
print("3. ADX - Trend Strength Filtered")
print("4. Kalman - Noise Reduction Enhanced")
print("\n" + "="*80)

# Define strategies to test
strategies = {
    'MACrossover_Base': MACrossoverBase,
    'MACrossover_MFI': MACrossoverMFI,
    'MACrossover_ADX': MACrossoverADX,
    'MACrossover_Kalman': MACrossoverKalman
}

# Test each strategy individually
all_results = {}
for name, strategy_class in strategies.items():
    print(f"\n🔄 Testing {name}...")
    try:
        results = test_on_all_data(strategy_class, name, verbose=False)
        if results is not None:
            all_results[name] = results
            print(f"✅ {name} tested successfully on {len(results)} data sources")
        else:
            print(f"❌ {name} failed to generate results")
    except Exception as e:
        print(f"❌ Error testing {name}: {e}")

# Create comparison summary
if all_results:
    print("\n" + "="*80)
    print("📊 STRATEGY COMPARISON SUMMARY")
    print("="*80)

    # Aggregate results by strategy
    comparison_data = []

    for strategy_name, results_df in all_results.items():
        avg_return = results_df['Return_%'].mean()
        avg_sharpe = results_df['Sharpe'].mean()
        avg_sortino = results_df['Sortino'].mean()
        avg_max_dd = results_df['Max_DD_%'].mean()
        avg_win_rate = results_df['Win_Rate_%'].mean()
        total_trades = results_df['Trades'].sum()
        avg_profit_factor = results_df['Profit_Factor'].mean()

        comparison_data.append({
            'Strategy': strategy_name,
            'Avg_Return_%': round(avg_return, 2),
            'Avg_Sharpe': round(avg_sharpe, 3),
            'Avg_Sortino': round(avg_sortino, 3),
            'Avg_Max_DD_%': round(avg_max_dd, 2),
            'Avg_Win_Rate_%': round(avg_win_rate, 2),
            'Total_Trades': int(total_trades),
            'Avg_Profit_Factor': round(avg_profit_factor, 3)
        })

    comparison_df = pd.DataFrame(comparison_data)
    comparison_df = comparison_df.sort_values('Avg_Return_%', ascending=False)

    print("\n🏆 Overall Performance Ranking:")
    print(comparison_df.to_string(index=False))

    # Save comparison to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_file = f"./results/MA_Crossover_Comparison_{timestamp}.csv"
    comparison_df.to_csv(comparison_file, index=False)
    print(f"\n💾 Comparison saved to: {comparison_file}")

    # Find best strategy for each metric
    print("\n🏅 Best Strategy by Metric:")
    print(f"Highest Return: {comparison_df.loc[comparison_df['Avg_Return_%'].idxmax(), 'Strategy']}")
    print(f"Best Sharpe: {comparison_df.loc[comparison_df['Avg_Sharpe'].idxmax(), 'Strategy']}")
    print(f"Best Sortino: {comparison_df.loc[comparison_df['Avg_Sortino'].idxmax(), 'Strategy']}")
    print(f"Lowest Drawdown: {comparison_df.loc[comparison_df['Avg_Max_DD_%'].idxmin(), 'Strategy']}")
    print(f"Highest Win Rate: {comparison_df.loc[comparison_df['Avg_Win_Rate_%'].idxmax(), 'Strategy']}")
    print(f"Best Profit Factor: {comparison_df.loc[comparison_df['Avg_Profit_Factor'].idxmax(), 'Strategy']}")

    # Performance by timeframe analysis
    print("\n📈 Performance by Timeframe:")
    for strategy_name, results_df in all_results.items():
        print(f"\n{strategy_name}:")

        # Group by timeframe patterns
        timeframe_groups = {
            '1-minute': results_df[results_df['Data_Source'].str.contains('1m', case=False)],
            '5-minute': results_df[results_df['Data_Source'].str.contains('5m', case=False)],
            '15-minute': results_df[results_df['Data_Source'].str.contains('15m', case=False)],
            '1-hour': results_df[results_df['Data_Source'].str.contains('1h', case=False)],
            '6-hour': results_df[results_df['Data_Source'].str.contains('6h', case=False)],
            'Daily': results_df[results_df['Data_Source'].str.contains('1d', case=False)]
        }

        for tf_name, tf_df in timeframe_groups.items():
            if not tf_df.empty:
                avg_return = tf_df['Return_%'].mean()
                avg_sharpe = tf_df['Sharpe'].mean()
                print(f"  {tf_name}: Return={avg_return:.2f}%, Sharpe={avg_sharpe:.3f}")

print("\n" + "="*80)
print("✨ Moon Dev's MA Crossover Strategy Testing Complete! ✨")
print("="*80)