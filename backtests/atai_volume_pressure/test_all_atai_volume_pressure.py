"""
Test all ATAI Volume Pressure strategies with multi-data testing
"""

import sys
import os
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multi_data_tester import test_on_all_data
from atai_volume_pressure_base import ATAIVolumePressureBase
from atai_volume_pressure_mfi import ATAIVolumePressureMFI
from atai_volume_pressure_adx import ATAIVolumePressureADX
from atai_volume_pressure_kalman import ATAIVolumePressureKalman

def main():
    """Run all ATAI Volume Pressure strategies on multiple data sources"""

    # List of strategies to test
    strategies = [
        ("ATAI Volume Pressure Base", ATAIVolumePressureBase),
        ("ATAI Volume Pressure MFI", ATAIVolumePressureMFI),
        ("ATAI Volume Pressure ADX", ATAIVolumePressureADX),
        ("ATAI Volume Pressure Kalman", ATAIVolumePressureKalman),
    ]

    print("\n" + "="*80)
    print("TESTING ALL ATAI VOLUME PRESSURE STRATEGIES")
    print("="*80)

    all_results = {}

    for strategy_name, strategy_class in strategies:
        print(f"\n{'='*60}")
        print(f"Testing: {strategy_name}")
        print('='*60)

        try:
            # Run multi-data test for this strategy
            df_results = test_on_all_data(
                strategy_class,
                strategy_name=strategy_name,
                cash=10000,  # Starting with $10k
                verbose=True
            )

            if df_results is not None and not df_results.empty:
                all_results[strategy_name] = df_results

                # Print summary statistics
                print(f"\n{'-'*40}")
                print(f"Summary for {strategy_name}:")
                print(f"{'-'*40}")

                # Calculate aggregate metrics
                successful = df_results[df_results['Return_%'].notna()]
                if not successful.empty:
                    avg_return = successful['Return_%'].mean()
                    avg_sharpe = successful['Sharpe'].mean()
                    avg_win_rate = successful['Win_Rate_%'].mean()
                    avg_max_dd = successful['Max_DD_%'].mean()
                    total_trades = successful['Trades'].sum()

                    print(f"Successful backtests: {len(successful)}/{len(df_results)}")
                    print(f"Average Return: {avg_return:.2f}%")
                    print(f"Average Sharpe Ratio: {avg_sharpe:.3f}")
                    print(f"Average Win Rate: {avg_win_rate:.2f}%")
                    print(f"Average Max Drawdown: {avg_max_dd:.2f}%")
                    print(f"Total Trades: {total_trades}")

                    # Best performing data source
                    best_idx = successful['Return_%'].idxmax()
                    best_row = successful.loc[best_idx]
                    print(f"\nBest performing data source:")
                    print(f"  Data: {best_row['Data_Source']}")
                    print(f"  Return: {best_row['Return_%']:.2f}%")
                    print(f"  Sharpe: {best_row['Sharpe']:.3f}")

        except Exception as e:
            print(f"Error testing {strategy_name}: {e}")
            continue

    # Final summary across all strategies
    if all_results:
        print("\n" + "="*80)
        print("FINAL SUMMARY - ALL ATAI VOLUME PRESSURE STRATEGIES")
        print("="*80)

        print("\nStrategy Performance Ranking (by average return):")
        print("-" * 50)

        strategy_performance = []
        for strategy_name, df_results in all_results.items():
            successful = df_results[df_results['Return_%'].notna()]
            if not successful.empty:
                avg_return = successful['Return_%'].mean()
                num_successful = len(successful)
                strategy_performance.append((strategy_name, avg_return, num_successful))

        # Sort by average return
        strategy_performance.sort(key=lambda x: x[1], reverse=True)

        for i, (name, avg_return, successful) in enumerate(strategy_performance, 1):
            print(f"{i}. {name}: {avg_return:.2f}% avg return ({successful} successful tests)")

        # Find overall best result
        print("\n" + "-"*50)
        print("Best Individual Result Across All Strategies:")
        print("-"*50)

        best_return = -float('inf')
        best_strategy = None
        best_data = None
        best_sharpe = None

        for strategy_name, df_results in all_results.items():
            successful = df_results[df_results['Return_%'].notna()]
            if not successful.empty:
                max_idx = successful['Return_%'].idxmax()
                if successful.loc[max_idx, 'Return_%'] > best_return:
                    best_return = successful.loc[max_idx, 'Return_%']
                    best_strategy = strategy_name
                    best_data = successful.loc[max_idx, 'Data_Source']
                    best_sharpe = successful.loc[max_idx, 'Sharpe']

        if best_strategy:
            print(f"Strategy: {best_strategy}")
            print(f"Data Source: {best_data}")
            print(f"Return: {best_return:.2f}%")
            print(f"Sharpe Ratio: {best_sharpe:.3f}")

        print("\n" + "="*80)
        print("ATAI Volume Pressure Strategy Testing Complete!")
        print("="*80)


if __name__ == "__main__":
    main()