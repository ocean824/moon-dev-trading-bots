#!/usr/bin/env python3
"""
Run all ATAI Volume Pressure strategy variations and save results
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data

# Import strategies
from atai_volume_pressure_base import ATAIVolumePressureBase
from atai_volume_pressure_mfi import ATAIVolumePressureMFI
from atai_volume_pressure_adx import ATAIVolumePressureADX
from atai_volume_pressure_kalman import ATAIVolumePressureKalman

def main():
    strategies = [
        (ATAIVolumePressureBase, 'ATAIVolumePressureBase'),
        (ATAIVolumePressureMFI, 'ATAIVolumePressureMFI'),
        (ATAIVolumePressureADX, 'ATAIVolumePressureADX'),
        (ATAIVolumePressureKalman, 'ATAIVolumePressureKalman')
    ]

    all_results = {}

    for strategy_class, strategy_name in strategies:
        print(f"\n{'='*80}")
        print(f"Testing {strategy_name} on all data sources")
        print('='*80)

        try:
            results = test_on_all_data(
                strategy_class,
                strategy_name,
                cash=10000,
                commission=0.002,
                verbose=True
            )

            if results is not None:
                all_results[strategy_name] = results
                print(f"\n📊 {strategy_name} Summary:")
                print(f"✅ Tested on {len(results)} data sources")
                print(f"📈 Average Return: {results['Return_%'].mean():.2f}%")
                print(f"📊 Average Sharpe: {results['Sharpe'].mean():.3f}")
                print(f"📉 Average Max DD: {results['Max_DD_%'].mean():.2f}%")
                print(f"🎯 Average Win Rate: {results['Win_Rate_%'].mean():.2f}%")
                print(f"💹 Total Trades: {results['Trades'].sum():.0f}")
        except Exception as e:
            print(f"Error testing {strategy_name}: {e}")

    # Print comparison table
    print("\n" + "="*100)
    print("ATAI VOLUME PRESSURE STRATEGIES - COMPLETE COMPARISON")
    print("="*100)

    if all_results:
        print(f"\n{'Strategy':<25} {'Avg Return%':<12} {'Avg Sharpe':<12} {'Avg Win%':<10} {'Total Trades':<12}")
        print("-"*80)

        for name, results in all_results.items():
            avg_return = results['Return_%'].mean()
            avg_sharpe = results['Sharpe'].mean()
            avg_win = results['Win_Rate_%'].mean()
            total_trades = results['Trades'].sum()

            print(f"{name:<25} {avg_return:<12.2f} {avg_sharpe:<12.3f} {avg_win:<10.2f} {total_trades:<12.0f}")

    print("\n🚀 All backtests complete!")
    return all_results

if __name__ == "__main__":
    results = main()