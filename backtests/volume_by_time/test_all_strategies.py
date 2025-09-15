"""
Test all Volume by Time strategies with multi-data testing
Tests each strategy across multiple data sources and compares performance
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import multi-data tester function
from multi_data_tester import test_on_all_data

# Import all Volume by Time strategies
from volume_by_time_base import VolumeByTimeBase
from volume_by_time_adx import VolumeByTimeADX
from volume_by_time_vwap import VolumeByTimeVWAP
from volume_by_time_mfi import VolumeByTimeMFI

def print_separator(title=""):
    """Print a formatted separator"""
    if title:
        print("\n" + "="*80)
        print(f"  {title}")
        print("="*80)
    else:
        print("\n" + "="*80)

def format_metric(value, metric_type="percent"):
    """Format metric for display"""
    if pd.isna(value):
        return "N/A"

    if metric_type == "percent":
        return f"{value:.2f}%"
    elif metric_type == "ratio":
        return f"{value:.2f}"
    elif metric_type == "currency":
        return f"${value:,.2f}"
    elif metric_type == "count":
        return f"{int(value):,}"
    else:
        return f"{value:.2f}"

def run_all_tests():
    """Run all Volume by Time strategies with multi-data testing"""

    # Strategy configurations
    strategies = [
        {
            'name': 'VolumeByTimeBase',
            'class': VolumeByTimeBase,
            'description': 'Base strategy using volume spikes at specific times'
        },
        {
            'name': 'VolumeByTimeADX',
            'class': VolumeByTimeADX,
            'description': 'Volume spikes filtered by ADX trend strength'
        },
        {
            'name': 'VolumeByTimeVWAP',
            'class': VolumeByTimeVWAP,
            'description': 'Volume spikes with VWAP for price action context'
        },
        {
            'name': 'VolumeByTimeMFI',
            'class': VolumeByTimeMFI,
            'description': 'Volume spikes confirmed by Money Flow Index'
        }
    ]

    # Results storage
    all_results = []
    summary_data = []

    print_separator("VOLUME BY TIME STRATEGIES - MULTI-DATA BACKTESTING")
    print("\nTesting all Volume by Time strategy variations across multiple data sources...")
    print(f"Number of strategies to test: {len(strategies)}")

    # Test each strategy
    for i, strategy_config in enumerate(strategies, 1):
        print_separator(f"[{i}/{len(strategies)}] {strategy_config['name']}")
        print(f"Description: {strategy_config['description']}")
        print("\nRunning backtests across all data sources...")

        try:
            # Run multi-data test using test_on_all_data function
            results = test_on_all_data(
                strategy_class=strategy_config['class'],
                strategy_name=strategy_config['name'],
                optimize=False,
                cash=100000,  # Increased for BTC prices
                commission=0.002,
                verbose=False
            )

            if results is not None and not results.empty:
                # Calculate aggregate metrics
                total_returns = []
                sharpe_ratios = []
                win_rates = []
                max_drawdowns = []
                total_trades = []
                successful_tests = 0

                print("\nIndividual Results Summary:")
                print("-" * 60)

                for result in results:
                    if result.get('stats') is not None:
                        stats = result['stats']

                        # Extract metrics safely
                        total_return = stats.get('Return [%]', np.nan)
                        sharpe = stats.get('Sharpe Ratio', np.nan)
                        win_rate = stats.get('Win Rate [%]', np.nan)
                        max_dd = stats.get('Max. Drawdown [%]', np.nan)
                        n_trades = stats.get('# Trades', 0)

                        # Store for aggregation
                        if not pd.isna(total_return):
                            total_returns.append(total_return)
                        if not pd.isna(sharpe):
                            sharpe_ratios.append(sharpe)
                        if not pd.isna(win_rate):
                            win_rates.append(win_rate)
                        if not pd.isna(max_dd):
                            max_drawdowns.append(max_dd)
                        if n_trades > 0:
                            total_trades.append(n_trades)
                            successful_tests += 1

                        # Print individual result only if trades were made
                        if n_trades > 0:
                            print(f"  {result.get('name', 'Unknown'):15} | "
                                  f"Return: {format_metric(total_return)} | "
                                  f"Sharpe: {format_metric(sharpe, 'ratio')} | "
                                  f"Trades: {format_metric(n_trades, 'count')}")

                print(f"\nSuccessful tests (with trades): {successful_tests}/{len(results)}")

                # Calculate and print aggregate metrics
                if total_returns:
                    print("\nAggregate Metrics:")
                    print("-" * 60)

                    avg_return = np.mean(total_returns)
                    median_return = np.median(total_returns)
                    positive_returns = sum(1 for r in total_returns if r > 0)

                    print(f"  Average Return:       {format_metric(avg_return)}")
                    print(f"  Median Return:        {format_metric(median_return)}")
                    print(f"  Positive Returns:     {positive_returns}/{len(total_returns)} "
                          f"({format_metric(100*positive_returns/len(total_returns) if total_returns else 0)})")

                    if sharpe_ratios:
                        avg_sharpe = np.mean(sharpe_ratios)
                        print(f"  Average Sharpe Ratio: {format_metric(avg_sharpe, 'ratio')}")

                    if win_rates:
                        avg_win_rate = np.mean(win_rates)
                        print(f"  Average Win Rate:     {format_metric(avg_win_rate)}")

                    if max_drawdowns:
                        avg_max_dd = np.mean(max_drawdowns)
                        worst_dd = min(max_drawdowns)
                        print(f"  Avg Max Drawdown:     {format_metric(avg_max_dd)}")
                        print(f"  Worst Drawdown:       {format_metric(worst_dd)}")

                    if total_trades:
                        total_all_trades = sum(total_trades)
                        avg_trades = np.mean(total_trades)
                        print(f"  Total Trades:         {format_metric(total_all_trades, 'count')}")
                        print(f"  Avg Trades/Symbol:    {format_metric(avg_trades, 'ratio')}")

                    # Store summary for final comparison
                    summary_data.append({
                        'Strategy': strategy_config['name'],
                        'Avg Return': avg_return,
                        'Median Return': median_return,
                        'Avg Sharpe': avg_sharpe if sharpe_ratios else np.nan,
                        'Avg Win Rate': avg_win_rate if win_rates else np.nan,
                        'Avg Max DD': avg_max_dd if max_drawdowns else np.nan,
                        'Total Trades': total_all_trades if total_trades else 0,
                        'Success Rate': f"{positive_returns}/{len(total_returns)}"
                    })
                else:
                    print("\n  No trades generated across any data source")
                    summary_data.append({
                        'Strategy': strategy_config['name'],
                        'Avg Return': np.nan,
                        'Median Return': np.nan,
                        'Avg Sharpe': np.nan,
                        'Avg Win Rate': np.nan,
                        'Avg Max DD': np.nan,
                        'Total Trades': 0,
                        'Success Rate': "0/0"
                    })

                # Store all results
                all_results.append({
                    'strategy': strategy_config['name'],
                    'results': results,
                    'summary': summary_data[-1] if summary_data else None
                })

            else:
                print("  No results generated for this strategy")

        except Exception as e:
            print(f"  Error testing strategy: {str(e)}")
            import traceback
            traceback.print_exc()

    # Print final comparison
    print_separator("FINAL STRATEGY COMPARISON")

    if summary_data:
        # Create comparison DataFrame
        comparison_df = pd.DataFrame(summary_data)

        # Remove rows with no trades
        comparison_df = comparison_df[comparison_df['Total Trades'] > 0]

        if not comparison_df.empty:
            # Sort by average return
            comparison_df = comparison_df.sort_values('Avg Return', ascending=False)

            print("\nStrategy Performance Ranking (by Average Return):")
            print("-" * 80)

            for idx, row in comparison_df.iterrows():
                print(f"\n{row['Strategy']}:")
                print(f"  Avg Return:    {format_metric(row['Avg Return'])}")
                print(f"  Median Return: {format_metric(row['Median Return'])}")
                print(f"  Avg Sharpe:    {format_metric(row['Avg Sharpe'], 'ratio')}")
                print(f"  Avg Win Rate:  {format_metric(row['Avg Win Rate'])}")
                print(f"  Avg Max DD:    {format_metric(row['Avg Max DD'])}")
                print(f"  Total Trades:  {format_metric(row['Total Trades'], 'count')}")
                print(f"  Success Rate:  {row['Success Rate']}")

            # Identify best strategies
            print_separator("RECOMMENDATIONS")

            # Best by return
            if not comparison_df.empty:
                best_return = comparison_df.iloc[0]
                print(f"\nBest Average Return: {best_return['Strategy']}")
                print(f"  Return: {format_metric(best_return['Avg Return'])}")

                # Best by Sharpe
                if 'Avg Sharpe' in comparison_df.columns:
                    best_sharpe_idx = comparison_df['Avg Sharpe'].idxmax()
                    if not pd.isna(best_sharpe_idx):
                        best_sharpe = comparison_df.loc[best_sharpe_idx]
                        print(f"\nBest Risk-Adjusted (Sharpe): {best_sharpe['Strategy']}")
                        print(f"  Sharpe: {format_metric(best_sharpe['Avg Sharpe'], 'ratio')}")

                # Most consistent (best median)
                if 'Median Return' in comparison_df.columns:
                    best_median_idx = comparison_df['Median Return'].idxmax()
                    if not pd.isna(best_median_idx):
                        best_median = comparison_df.loc[best_median_idx]
                        print(f"\nMost Consistent (Median): {best_median['Strategy']}")
                        print(f"  Median Return: {format_metric(best_median['Median Return'])}")

            # Save results to CSV
            results_dir = Path(__file__).parent / 'results'
            results_dir.mkdir(exist_ok=True)

            csv_path = results_dir / 'volume_by_time_comparison.csv'
            comparison_df.to_csv(csv_path, index=False)
            print(f"\nResults saved to: {csv_path}")
        else:
            print("\nNo strategies generated trades. Consider adjusting parameters.")
    else:
        print("\nNo results to compare")

    print_separator("TESTING COMPLETE")

    return all_results

if __name__ == "__main__":
    print("\n" + "="*80)
    print("  VOLUME BY TIME STRATEGIES - COMPREHENSIVE TESTING")
    print("="*80)
    print("\nThis will test all Volume by Time strategy variations across multiple")
    print("data sources and timeframes. This may take several minutes...")
    print("\nStrategies to test:")
    print("  1. Volume by Time Base - Basic volume spike detection")
    print("  2. Volume by Time + ADX - With trend strength filter")
    print("  3. Volume by Time + VWAP - With price action context")
    print("  4. Volume by Time + MFI - With money flow confirmation")

    print("\nStarting tests...")

    results = run_all_tests()

    print("\n" + "="*80)
    print("  All Volume by Time strategies have been tested successfully!")
    print("="*80)