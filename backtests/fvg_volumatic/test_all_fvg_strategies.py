"""
Test All FVG (Fair Value Gap) Strategies
========================================

This script tests all FVG strategy variations on multiple data sources
and generates comprehensive comparison results.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import strategies
from fvg_base import FVGBase
from fvg_mfi import FVGMFI
from fvg_adx import FVGADX
from fvg_kalman import FVGKalman

# Import multi-data tester
from multi_data_tester import test_on_all_data, test_multiple_strategies

def run_all_fvg_tests():
    """
    Test all FVG strategies on all configured data sources
    """
    print("\n" + "="*80)
    print(" "*20 + "🌙 MOON DEV'S FVG STRATEGY SUITE TEST 🌙")
    print("="*80)
    print(f"Testing started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # Define all strategies to test
    strategies = {
        'FVG_Base': FVGBase,
        'FVG_MFI': FVGMFI,
        'FVG_ADX': FVGADX,
        'FVG_Kalman': FVGKalman
    }

    # Test each strategy individually
    all_results = []

    for name, strategy_class in strategies.items():
        print(f"\n📊 Testing {name} Strategy...")
        print("-" * 50)

        try:
            # Test on all data sources
            results = test_on_all_data(strategy_class, name)

            if results is not None:
                print(f"✅ {name} completed successfully")
                print(f"   Average Return: {results['Return_%'].mean():.2f}%")
                print(f"   Average Sharpe: {results['Sharpe'].mean():.2f}")
                print(f"   Average Win Rate: {results['Win_Rate_%'].mean():.1f}%")
                all_results.append(results)
            else:
                print(f"❌ {name} failed to complete")

        except Exception as e:
            print(f"❌ Error testing {name}: {str(e)}")
            continue

    # Combine all results
    if all_results:
        print("\n" + "="*80)
        print(" "*25 + "📊 SUMMARY RESULTS 📊")
        print("="*80)

        # Create comparison summary
        summary_data = []

        for strategy_name in strategies.keys():
            # Find results for this strategy
            strategy_results = None
            for result_df in all_results:
                if strategy_name in result_df.columns[0] if len(result_df.columns) > 0 else False:
                    strategy_results = result_df
                    break

            if strategy_results is not None and not strategy_results.empty:
                summary_data.append({
                    'Strategy': strategy_name,
                    'Avg_Return_%': strategy_results['Return_%'].mean(),
                    'Avg_Sharpe': strategy_results['Sharpe'].mean(),
                    'Avg_Sortino': strategy_results['Sortino'].mean(),
                    'Avg_Calmar': strategy_results['Calmar'].mean(),
                    'Avg_Max_DD_%': strategy_results['Max_DD_%'].mean(),
                    'Avg_Win_Rate_%': strategy_results['Win_Rate_%'].mean(),
                    'Total_Trades': strategy_results['Trades'].sum(),
                    'Avg_Profit_Factor': strategy_results['Profit_Factor'].mean()
                })

        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_df = summary_df.sort_values('Avg_Sharpe', ascending=False)

            # Save summary to CSV
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            summary_file = f'./results/FVG_ALL_STRATEGIES_SUMMARY_{timestamp}.csv'
            summary_df.to_csv(summary_file, index=False)

            # Print summary
            print("\n📈 Strategy Performance Ranking (by Sharpe Ratio):")
            print("-" * 50)
            for idx, row in summary_df.iterrows():
                print(f"\n{row['Strategy']}:")
                print(f"  • Average Return: {row['Avg_Return_%']:.2f}%")
                print(f"  • Sharpe Ratio: {row['Avg_Sharpe']:.2f}")
                print(f"  • Sortino Ratio: {row['Avg_Sortino']:.2f}")
                print(f"  • Win Rate: {row['Avg_Win_Rate_%']:.1f}%")
                print(f"  • Max Drawdown: {row['Avg_Max_DD_%']:.1f}%")
                print(f"  • Total Trades: {row['Total_Trades']:.0f}")

            # Identify best strategy
            best_strategy = summary_df.iloc[0]
            print("\n" + "="*50)
            print("🏆 BEST PERFORMING STRATEGY: " + best_strategy['Strategy'])
            print("="*50)
            print(f"Sharpe Ratio: {best_strategy['Avg_Sharpe']:.2f}")
            print(f"Average Return: {best_strategy['Avg_Return_%']:.2f}%")
            print(f"Win Rate: {best_strategy['Avg_Win_Rate_%']:.1f}%")

            print(f"\n✅ Summary saved to: {summary_file}")

    print("\n" + "="*80)
    print(f"Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

if __name__ == "__main__":
    # Change to the fvg_volumatic directory to save results there
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("\n🚀 Starting comprehensive FVG strategy testing...")
    print("This will test 4 strategies on 25+ data sources.")
    print("Expected runtime: 5-10 minutes")

    run_all_fvg_tests()

    print("\n✅ All FVG strategy tests complete!")