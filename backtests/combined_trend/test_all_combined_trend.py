"""
Test all Combined Trend strategies
Runs backtests for all variations and compares results
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data

# Import all strategy variations
from combined_trend_base import CombinedTrendBase
from combined_trend_mfi import CombinedTrendMFI
from combined_trend_adx import CombinedTrendADX
from combined_trend_kalman import CombinedTrendKalman


def test_all_strategies():
    """Test all Combined Trend strategy variations"""

    strategies = [
        (CombinedTrendBase, "CombinedTrendBase"),
        (CombinedTrendMFI, "CombinedTrendMFI"),
        (CombinedTrendADX, "CombinedTrendADX"),
        (CombinedTrendKalman, "CombinedTrendKalman")
    ]

    all_results = []
    summary_data = []

    print("="*100)
    print("TESTING ALL COMBINED TREND STRATEGIES")
    print("="*100)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    for strategy_class, strategy_name in strategies:
        print(f"\nTesting {strategy_name}...")
        print("-"*80)

        # Run backtests using test_on_all_data
        results_df = test_on_all_data(
            strategy_class=strategy_class,
            strategy_name=strategy_name,
            optimize=False,
            cash=10000,
            commission=0.002,
            verbose=False  # Less verbose for batch testing
        )

        if results_df is not None and not results_df.empty:
            # Calculate summary statistics
            profitable = (results_df['Return_%'] > 0).sum()
            total_tested = len(results_df)
            win_rate = (profitable / total_tested) * 100 if total_tested > 0 else 0

            summary = {
                'Strategy': strategy_name,
                'Datasets Tested': total_tested,
                'Profitable': profitable,
                'Win Rate %': win_rate,
                'Avg Return %': results_df['Return_%'].mean(),
                'Best Return %': results_df['Return_%'].max(),
                'Worst Return %': results_df['Return_%'].min(),
                'Avg Sharpe': results_df['Sharpe'].mean(),
                'Best Sharpe': results_df['Sharpe'].max(),
                'Avg Max DD %': results_df['Max_DD_%'].mean(),
                'Best Max DD %': results_df['Max_DD_%'].min(),  # Best is lowest
                'Avg Win Rate %': results_df['Win_Rate_%'].mean(),
                'Avg Trades': results_df['Trades'].mean()
            }

            summary_data.append(summary)

            # Add strategy name to results
            results_df['Strategy'] = strategy_name
            all_results.append(results_df)

            # Print individual strategy summary
            print(f"\n{strategy_name} Summary:")
            print(f"  Profitable: {profitable}/{total_tested} ({win_rate:.1f}%)")
            print(f"  Avg Return: {summary['Avg Return %']:.2f}%")
            print(f"  Best Return: {summary['Best Return %']:.2f}%")
            print(f"  Worst Return: {summary['Worst Return %']:.2f}%")
            print(f"  Avg Sharpe: {summary['Avg Sharpe']:.2f}")
            print(f"  Avg Max DD: {summary['Avg Max DD %']:.2f}%")
            print(f"  Avg Win Rate: {summary['Avg Win Rate %']:.2f}%")

    # Create summary DataFrame
    if summary_data:
        summary_df = pd.DataFrame(summary_data)

        # Print overall comparison
        print("\n" + "="*100)
        print("STRATEGY COMPARISON SUMMARY")
        print("="*100)

        # Sort by average return
        summary_df_sorted = summary_df.sort_values('Avg Return %', ascending=False)

        print("\nRanked by Average Return:")
        print("-"*80)
        for idx, row in summary_df_sorted.iterrows():
            print(f"{row['Strategy']:25} | "
                  f"Avg Return: {row['Avg Return %']:7.2f}% | "
                  f"Sharpe: {row['Avg Sharpe']:5.2f} | "
                  f"Max DD: {row['Avg Max DD %']:6.2f}% | "
                  f"Win Rate: {row['Avg Win Rate %']:5.1f}%")

        # Find best performing strategy across metrics
        print("\n" + "="*100)
        print("BEST PERFORMERS BY METRIC")
        print("="*100)

        metrics = [
            ('Avg Return %', True),
            ('Avg Sharpe', True),
            ('Avg Max DD %', False),  # Lower is better
            ('Avg Win Rate %', True),
            ('Win Rate %', True)  # Strategy win rate across datasets
        ]

        for metric, higher_is_better in metrics:
            if higher_is_better:
                best_idx = summary_df[metric].idxmax()
            else:
                best_idx = summary_df[metric].idxmin()
            best_strategy = summary_df.loc[best_idx, 'Strategy']
            best_value = summary_df.loc[best_idx, metric]
            print(f"{metric:20}: {best_strategy:25} ({best_value:.2f})")

        # Combine all results
        if all_results:
            combined_results = pd.concat(all_results, ignore_index=True)

            # Save combined results
            results_dir = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/combined_trend/results"
            os.makedirs(results_dir, exist_ok=True)

            combined_file = os.path.join(results_dir, "all_strategies_combined.csv")
            combined_results.to_csv(combined_file, index=False)
            print(f"\nCombined results saved to: {combined_file}")

            summary_file = os.path.join(results_dir, "strategy_comparison_summary.csv")
            summary_df.to_csv(summary_file, index=False)
            print(f"Summary comparison saved to: {summary_file}")

            # Find best dataset performers
            print("\n" + "="*100)
            print("TOP PERFORMING DATASETS")
            print("="*100)

            # Group by dataset and calculate average performance
            dataset_perf = combined_results.groupby('Data_Source').agg({
                'Return_%': 'mean',
                'Sharpe': 'mean',
                'Max_DD_%': 'mean',
                'Win_Rate_%': 'mean'
            }).round(2)

            dataset_perf_sorted = dataset_perf.sort_values('Return_%', ascending=False)
            print("\nTop 10 Datasets by Average Return:")
            print(dataset_perf_sorted.head(10))

            # Find most consistent performers
            print("\n" + "="*100)
            print("MOST CONSISTENT STRATEGIES")
            print("="*100)

            for strategy_name in summary_df['Strategy']:
                strategy_results = combined_results[combined_results['Strategy'] == strategy_name]
                if not strategy_results.empty:
                    positive_returns = (strategy_results['Return_%'] > 0).sum()
                    total = len(strategy_results)
                    consistency = (positive_returns / total) * 100 if total > 0 else 0

                    if consistency >= 40:  # At least 40% win rate across datasets
                        print(f"{strategy_name:25} | "
                              f"Consistency: {consistency:.1f}% | "
                              f"Positive: {positive_returns}/{total}")

    print("\n" + "="*100)
    print(f"Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*100)


if __name__ == "__main__":
    test_all_strategies()