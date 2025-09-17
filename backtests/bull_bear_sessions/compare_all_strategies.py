"""
Compare all Bull vs Bear Sessions strategy variations
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

print("\n" + "="*80)
print("🚀 BULL VS BEAR SESSIONS - STRATEGY COMPARISON 🚀")
print("="*80)

# Read results from CSV files (if they exist)
results_dir = 'results'
strategy_results = {}

# List of strategy CSV files to look for
strategy_files = [
    'BullBearSessionsSimple.csv',
    'BullBearSessionsBase.csv',
    'BullBearSessionsMFI.csv',
    'BullBearSessionsADX.csv',
    'BullBearSessionsKalman.csv'
]

print("\n📊 Loading available results...")

for file in strategy_files:
    filepath = os.path.join(results_dir, file)
    if os.path.exists(filepath):
        strategy_name = file.replace('.csv', '')
        strategy_results[strategy_name] = pd.read_csv(filepath)
        print(f"✅ Loaded: {strategy_name}")
    else:
        print(f"⚠️  Not found: {file}")

if not strategy_results:
    print("\n❌ No results files found. Please run the strategies first.")
    exit(1)

# Create comparison summary
print("\n" + "="*60)
print("STRATEGY PERFORMANCE COMPARISON")
print("="*60)

comparison_data = []

for strategy_name, df in strategy_results.items():
    # Calculate aggregate metrics
    comparison_data.append({
        'Strategy': strategy_name,
        'Avg_Return_%': df['Return_%'].replace([np.inf, -np.inf], np.nan).dropna().mean(),
        'Median_Return_%': df['Return_%'].replace([np.inf, -np.inf], np.nan).dropna().median(),
        'Avg_Sharpe': df['Sharpe'].mean(),
        'Avg_Sortino': df['Sortino'].replace([np.inf, -np.inf], np.nan).dropna().mean(),
        'Avg_Calmar': df['Calmar'].replace([np.inf, -np.inf], np.nan).dropna().mean(),
        'Avg_Max_DD_%': df['Max_DD_%'].mean(),
        'Avg_Win_Rate_%': df['Win_Rate_%'].mean(),
        'Avg_Profit_Factor': df['Profit_Factor'].replace([np.inf, -np.inf], np.nan).dropna().mean(),
        'Total_Trades': df['Trades'].sum(),
        'Positive_Markets': (df['Return_%'] > 0).sum(),
        'Total_Markets': len(df),
        'Success_Rate_%': ((df['Return_%'] > 0).sum() / len(df)) * 100
    })

comparison_df = pd.DataFrame(comparison_data)

# Sort by success rate and Sortino ratio
comparison_df['Score'] = comparison_df['Success_Rate_%'] * 0.3 + comparison_df['Avg_Sortino'].clip(-10, 10) * 10
comparison_df = comparison_df.sort_values('Score', ascending=False)

print("\n1. OVERALL RANKING (by Combined Score):")
print("-" * 60)
for idx, row in comparison_df.iterrows():
    print(f"{row['Strategy']}")
    print(f"  📈 Success Rate: {row['Success_Rate_%']:.1f}% ({row['Positive_Markets']}/{row['Total_Markets']} markets)")
    print(f"  💰 Avg Return: {row['Avg_Return_%']:.2f}%")
    print(f"  📊 Sortino: {row['Avg_Sortino']:.3f} | Sharpe: {row['Avg_Sharpe']:.3f}")
    print(f"  🎯 Win Rate: {row['Avg_Win_Rate_%']:.1f}%")
    print()

print("\n2. KEY METRICS COMPARISON:")
print("-" * 60)

# Best by different metrics
metrics = {
    'Highest Win Rate': 'Avg_Win_Rate_%',
    'Best Risk-Adjusted (Sortino)': 'Avg_Sortino',
    'Most Consistent (Success Rate)': 'Success_Rate_%',
    'Lowest Drawdown': 'Avg_Max_DD_%'
}

for metric_name, column in metrics.items():
    if column == 'Avg_Max_DD_%':
        best_idx = comparison_df[column].idxmax()  # For drawdown, less negative is better
    else:
        best_idx = comparison_df[column].idxmax()

    best_row = comparison_df.loc[best_idx]
    print(f"\n{metric_name}: {best_row['Strategy']}")
    print(f"  → {best_row[column]:.2f}" + ("%" if "%" in column else ""))

print("\n3. DETAILED COMPARISON TABLE:")
print("-" * 60)

# Select key columns for display
display_columns = ['Strategy', 'Success_Rate_%', 'Avg_Win_Rate_%', 'Avg_Sortino', 'Avg_Sharpe', 'Avg_Max_DD_%']
print(comparison_df[display_columns].to_string(index=False))

# Save comprehensive comparison
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
comparison_file = f'results/strategy_comparison_{timestamp}.csv'
comparison_df.to_csv(comparison_file, index=False)

print(f"\n✅ Comparison saved to: {comparison_file}")

# FINAL RECOMMENDATION
print("\n" + "="*60)
print("🏆 FINAL RECOMMENDATION")
print("="*60)

if len(comparison_df) > 0:
    best_strategy = comparison_df.iloc[0]
    print(f"\nBest Overall Strategy: {best_strategy['Strategy']}")
    print(f"\nKey Strengths:")
    print(f"  • Works in {best_strategy['Success_Rate_%']:.1f}% of market conditions")
    print(f"  • Sortino Ratio: {best_strategy['Avg_Sortino']:.3f}")
    print(f"  • Win Rate: {best_strategy['Avg_Win_Rate_%']:.1f}%")
    print(f"  • Tested across {best_strategy['Total_Markets']} different markets")

    print(f"\nRecommended Settings:")
    if 'Simple' in best_strategy['Strategy']:
        print("  • Lookback Period: 20 bars")
        print("  • Volume Threshold: 60%")
        print("  • Take Profit: 3%")
        print("  • Stop Loss: 2%")
    else:
        print("  • Session Hours: [6, 12, 18, 24]")
        print("  • Volume Percentile: 70%")
        print("  • Delta Threshold: 55%")
        print("  • Take Profit: 3-3.5%")
        print("  • Stop Loss: 1.8-2%")

print("\n" + "="*80)
print("✅ ANALYSIS COMPLETE!")
print("="*80)