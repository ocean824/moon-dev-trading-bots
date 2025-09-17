"""
Test all Bull vs Bear Sessions strategies and compare results
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data

# Import all strategy classes
from bull_bear_sessions_base import BullBearSessionsBase
from bull_bear_sessions_mfi import BullBearSessionsMFI
from bull_bear_sessions_adx import BullBearSessionsADX
from bull_bear_sessions_kalman import BullBearSessionsKalman

print("\n" + "="*80)
print("🚀 TESTING ALL BULL VS BEAR SESSIONS STRATEGIES 🚀")
print("="*80)

# Define strategies to test
strategies = {
    'BullBearSessions_Base': BullBearSessionsBase,
    'BullBearSessions_MFI': BullBearSessionsMFI,
    'BullBearSessions_ADX': BullBearSessionsADX,
    'BullBearSessions_Kalman': BullBearSessionsKalman
}

# Store results for comparison
all_results = {}

# Test each strategy
for name, strategy_class in strategies.items():
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print('='*60)

    try:
        # Run tests on all data sources
        results = test_on_all_data(strategy_class, name, verbose=False)

        if results is not None:
            all_results[name] = results

            # Print summary statistics
            print(f"\n✅ {name} Results Summary:")
            print(f"Average Return: {results['Return_%'].mean():.2f}%")
            print(f"Average Sharpe: {results['Sharpe'].mean():.3f}")
            print(f"Average Sortino: {results['Sortino'].mean():.3f}")
            print(f"Average Max DD: {results['Max_DD_%'].mean():.2f}%")
            print(f"Average Win Rate: {results['Win_Rate_%'].mean():.2f}%")
            print(f"Average Trades: {results['Trades'].mean():.0f}")

    except Exception as e:
        print(f"❌ Error testing {name}: {e}")
        continue

# Create comparison DataFrame
if all_results:
    print("\n" + "="*80)
    print("📊 STRATEGY COMPARISON SUMMARY")
    print("="*80)

    comparison_data = []

    for strategy_name, results in all_results.items():
        comparison_data.append({
            'Strategy': strategy_name,
            'Avg_Return_%': results['Return_%'].mean(),
            'Avg_Sharpe': results['Sharpe'].mean(),
            'Avg_Sortino': results['Sortino'].mean(),
            'Avg_Calmar': results['Calmar'].mean(),
            'Avg_Max_DD_%': results['Max_DD_%'].mean(),
            'Avg_Win_Rate_%': results['Win_Rate_%'].mean(),
            'Avg_Profit_Factor': results['Profit_Factor'].mean(),
            'Avg_Expectancy_%': results['Expectancy_%'].mean(),
            'Avg_SQN': results['SQN'].mean(),
            'Total_Trades': results['Trades'].sum(),
            'Best_Return_%': results['Return_%'].max(),
            'Worst_Return_%': results['Return_%'].min(),
            'Positive_Markets': (results['Return_%'] > 0).sum(),
            'Total_Markets': len(results)
        })

    comparison_df = pd.DataFrame(comparison_data)
    comparison_df = comparison_df.sort_values('Avg_Sortino', ascending=False)

    # Save comparison to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    comparison_file = f'results/bull_bear_sessions_comparison_{timestamp}.csv'
    os.makedirs('results', exist_ok=True)
    comparison_df.to_csv(comparison_file, index=False)

    print("\nOverall Comparison (Sorted by Sortino Ratio):")
    print(comparison_df.to_string())

    print(f"\n✅ Comparison saved to: {comparison_file}")

    # Find best strategy
    best_strategy = comparison_df.iloc[0]['Strategy']
    print(f"\n🏆 BEST OVERALL STRATEGY: {best_strategy}")
    print(f"   - Sortino Ratio: {comparison_df.iloc[0]['Avg_Sortino']:.3f}")
    print(f"   - Average Return: {comparison_df.iloc[0]['Avg_Return_%']:.2f}%")
    print(f"   - Win Rate: {comparison_df.iloc[0]['Avg_Win_Rate_%']:.2f}%")
    print(f"   - Success Rate: {comparison_df.iloc[0]['Positive_Markets']}/{comparison_df.iloc[0]['Total_Markets']} markets profitable")

    # Additional insights
    print("\n📈 KEY INSIGHTS:")

    # Most consistent strategy (lowest max drawdown)
    most_consistent = comparison_df.loc[comparison_df['Avg_Max_DD_%'].idxmin()]
    print(f"\n1. Most Consistent (Lowest Drawdown): {most_consistent['Strategy']}")
    print(f"   - Max Drawdown: {most_consistent['Avg_Max_DD_%']:.2f}%")

    # Highest win rate
    highest_winrate = comparison_df.loc[comparison_df['Avg_Win_Rate_%'].idxmax()]
    print(f"\n2. Highest Win Rate: {highest_winrate['Strategy']}")
    print(f"   - Win Rate: {highest_winrate['Avg_Win_Rate_%']:.2f}%")

    # Most profitable
    most_profitable = comparison_df.loc[comparison_df['Avg_Return_%'].idxmax()]
    print(f"\n3. Most Profitable: {most_profitable['Strategy']}")
    print(f"   - Average Return: {most_profitable['Avg_Return_%']:.2f}%")

    # Best risk-adjusted (Calmar)
    best_calmar = comparison_df.loc[comparison_df['Avg_Calmar'].idxmax()]
    print(f"\n4. Best Risk-Adjusted (Calmar): {best_calmar['Strategy']}")
    print(f"   - Calmar Ratio: {best_calmar['Avg_Calmar']:.3f}")

    # Market adaptability
    print("\n5. Market Adaptability (Profitable Markets):")
    for _, row in comparison_df.iterrows():
        success_rate = (row['Positive_Markets'] / row['Total_Markets']) * 100
        print(f"   - {row['Strategy']}: {row['Positive_Markets']}/{row['Total_Markets']} ({success_rate:.1f}%)")

print("\n" + "="*80)
print("✅ ALL TESTING COMPLETE!")
print("="*80)