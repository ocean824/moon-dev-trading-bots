#!/usr/bin/env python3
"""
Run all ATAI Volume Pressure strategies on ALL 25 data sources
"""

import sys
import os
import pandas as pd

# Add parent directory to path for multi_data_tester import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data

# Import all strategies
from atai_volume_pressure_base import ATAIVolumePressureBase
from atai_volume_pressure_mfi import ATAIVolumePressureMFI
from atai_volume_pressure_adx import ATAIVolumePressureADX
from atai_volume_pressure_kalman import ATAIVolumePressureKalman

def main():
    """Run all strategies on all data sources and display results"""

    strategies = [
        (ATAIVolumePressureBase, 'ATAIVolumePressureBase'),
        (ATAIVolumePressureMFI, 'ATAIVolumePressureMFI'),
        (ATAIVolumePressureADX, 'ATAIVolumePressureADX'),
        (ATAIVolumePressureKalman, 'ATAIVolumePressureKalman')
    ]

    all_results = {}

    print("\n" + "="*100)
    print("ATAI VOLUME PRESSURE STRATEGIES - TESTING ALL 25 DATA SOURCES")
    print("="*100)

    for strategy_class, strategy_name in strategies:
        print(f"\n{'='*80}")
        print(f"🚀 Testing {strategy_name} on 25 data sources")
        print('='*80)

        try:
            # Run on all data sources
            results = test_on_all_data(
                strategy_class,
                strategy_name,
                cash=10000,
                commission=0.002,
                verbose=True
            )

            if results is not None and len(results) > 0:
                all_results[strategy_name] = results

                # Print summary
                print(f"\n📊 {strategy_name} Summary:")
                print(f"✅ Successfully tested on {len(results)} data sources")
                print(f"📈 Average Return: {results['Return_%'].mean():.2f}%")
                print(f"📊 Average Sharpe Ratio: {results['Sharpe'].mean():.3f}")
                print(f"📉 Average Max Drawdown: {results['Max_DD_%'].mean():.2f}%")
                print(f"🎯 Average Win Rate: {results['Win_Rate_%'].mean():.2f}%")
                print(f"💹 Total Trades: {results['Trades'].sum():.0f}")

                # Show top 5 performers for this strategy
                top5 = results.nlargest(5, 'Return_%')[['Data_Source', 'Return_%', 'Sharpe', 'Win_Rate_%']]
                print(f"\nTop 5 performers for {strategy_name}:")
                print(top5.to_string())

            else:
                print(f"❌ No results for {strategy_name}")

        except Exception as e:
            print(f"❌ Error testing {strategy_name}: {e}")

    # Final comparison table
    if all_results:
        print("\n" + "="*100)
        print("FINAL COMPARISON - ALL STRATEGIES ACROSS ALL DATA SOURCES")
        print("="*100)

        comparison_data = []
        for strategy_name, results in all_results.items():
            comparison_data.append({
                'Strategy': strategy_name.replace('ATAIVolumePressure', ''),
                'Avg Return %': results['Return_%'].mean(),
                'Best Return %': results['Return_%'].max(),
                'Worst Return %': results['Return_%'].min(),
                'Avg Sharpe': results['Sharpe'].mean(),
                'Avg Win Rate %': results['Win_Rate_%'].mean(),
                'Total Trades': results['Trades'].sum(),
                'Avg Max DD %': results['Max_DD_%'].mean(),
                'Data Sources': len(results)
            })

        comparison_df = pd.DataFrame(comparison_data)
        comparison_df = comparison_df.sort_values('Avg Return %', ascending=False)

        print("\n📊 Strategy Performance Ranking:")
        print(comparison_df.to_string(index=False))

        # Best overall performer
        best_strategy_idx = comparison_df['Avg Return %'].idxmax()
        best_strategy = comparison_df.loc[best_strategy_idx, 'Strategy']
        best_return = comparison_df.loc[best_strategy_idx, 'Avg Return %']

        print(f"\n🏆 Best Overall Strategy: {best_strategy} with {best_return:.2f}% average return")

        # Find single best result across all strategies and datasets
        best_single_return = -float('inf')
        best_single_strategy = ""
        best_single_dataset = ""

        for strategy_name, results in all_results.items():
            max_idx = results['Return_%'].idxmax()
            if results.loc[max_idx, 'Return_%'] > best_single_return:
                best_single_return = results.loc[max_idx, 'Return_%']
                best_single_strategy = strategy_name.replace('ATAIVolumePressure', '')
                best_single_dataset = results.loc[max_idx, 'Data_Source']

        print(f"\n🌟 Best Single Result: {best_single_strategy} on {best_single_dataset} = {best_single_return:.2f}%")

    print("\n" + "="*100)
    print("🚀 ALL ATAI VOLUME PRESSURE BACKTESTS COMPLETE!")
    print("="*100)

    return all_results

if __name__ == "__main__":
    results = main()