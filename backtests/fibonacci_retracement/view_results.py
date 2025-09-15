"""
View and compare Fibonacci Retracement strategy results
"""

import pandas as pd
import os
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("🚀 FIBONACCI RETRACEMENT STRATEGIES - RESULTS COMPARISON 🌙")
print("="*80)

# Read all result files
results_dir = './results'
strategies = [
    'FibonacciRetracementBase',
    'FibonacciRetracementADX',
    'FibonacciRetracementBollinger',
    'FibonacciRetracementEMA',
    'FibonacciRetracementKalman',
    'FibonacciRetracementMFI'
]

summary_data = []

for strategy in strategies:
    file_path = os.path.join(results_dir, f'{strategy}.csv')
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        
        # Calculate summary statistics
        avg_return = df['Return_%'].mean()
        median_return = df['Return_%'].median()
        avg_sharpe = df['Sharpe'].mean()
        avg_win_rate = df['Win_Rate_%'].mean()
        avg_max_dd = df['Max_DD_%'].mean()
        avg_trades = df['Trades'].mean()
        profitable_tests = len(df[df['Return_%'] > 0])
        total_tests = len(df)
        
        summary_data.append({
            'Strategy': strategy.replace('FibonacciRetracement', 'Fib+'),
            'Avg Return %': round(avg_return, 2),
            'Median Return %': round(median_return, 2),
            'Avg Sharpe': round(avg_sharpe, 3),
            'Avg Win Rate %': round(avg_win_rate, 2),
            'Avg Max DD %': round(avg_max_dd, 2),
            'Avg Trades': round(avg_trades, 1),
            'Profitable': f"{profitable_tests}/{total_tests}",
            'Success %': round(profitable_tests/total_tests*100, 1)
        })

# Create comparison dataframe
summary_df = pd.DataFrame(summary_data)

# Sort by average return
summary_df = summary_df.sort_values('Avg Return %', ascending=False)

print("\n📊 OVERALL PERFORMANCE COMPARISON:")
print("="*80)
print(summary_df.to_string(index=False))

print("\n" + "="*80)
print("🌟 KEY INSIGHTS:")
print("="*80)

# Best performers
best_return = summary_df.iloc[0]
print(f"\n📈 Highest Average Return: {best_return['Strategy']}")
print(f"   Return: {best_return['Avg Return %']}%")
print(f"   Median: {best_return['Median Return %']}%")
print(f"   Success Rate: {best_return['Success %']}%")

best_sharpe = summary_df.nlargest(1, 'Avg Sharpe').iloc[0]
print(f"\n📊 Best Risk-Adjusted (Sharpe): {best_sharpe['Strategy']}")
print(f"   Sharpe: {best_sharpe['Avg Sharpe']}")
print(f"   Return: {best_sharpe['Avg Return %']}%")

best_win_rate = summary_df.nlargest(1, 'Avg Win Rate %').iloc[0]
print(f"\n🎯 Highest Win Rate: {best_win_rate['Strategy']}")
print(f"   Win Rate: {best_win_rate['Avg Win Rate %']}%")
print(f"   Return: {best_win_rate['Avg Return %']}%")

lowest_dd = summary_df.nlargest(1, 'Avg Max DD %').iloc[0]  # Less negative is better
print(f"\n🛡️ Lowest Drawdown: {lowest_dd['Strategy']}")
print(f"   Max DD: {lowest_dd['Avg Max DD %']}%")
print(f"   Return: {lowest_dd['Avg Return %']}%")

most_consistent = summary_df.nlargest(1, 'Success %').iloc[0]
print(f"\n💰 Most Consistent: {most_consistent['Strategy']}")
print(f"   Success Rate: {most_consistent['Success %']}%")
print(f"   Profitable: {most_consistent['Profitable']}")

print("\n" + "="*80)
print("📈 STRATEGY RECOMMENDATIONS:")
print("="*80)

print("\n1. CONSERVATIVE APPROACH:")
conservative = summary_df[(summary_df['Avg Max DD %'] > -50) & (summary_df['Avg Return %'] > 0)]
if not conservative.empty:
    print(f"   Recommended: {conservative.iloc[0]['Strategy']}")
    print(f"   Balanced risk with positive returns")
else:
    print("   Consider position sizing adjustments for all strategies")

print("\n2. AGGRESSIVE APPROACH:")
print(f"   Recommended: {best_return['Strategy']}")
print(f"   Highest returns but watch the drawdown")

print("\n3. BALANCED APPROACH:")
# Calculate a balanced score
summary_df['Balanced Score'] = (
    (summary_df['Avg Return %'] - summary_df['Avg Return %'].min()) / 
    (summary_df['Avg Return %'].max() - summary_df['Avg Return %'].min()) * 0.4 +
    (summary_df['Avg Sharpe'] - summary_df['Avg Sharpe'].min()) / 
    (summary_df['Avg Sharpe'].max() - summary_df['Avg Sharpe'].min()) * 0.3 +
    (summary_df['Success %'] - summary_df['Success %'].min()) / 
    (summary_df['Success %'].max() - summary_df['Success %'].min()) * 0.3
)
balanced = summary_df.nlargest(1, 'Balanced Score').iloc[0]
print(f"   Recommended: {balanced['Strategy']}")
print(f"   Best overall balance of return, risk, and consistency")

print("\n" + "="*80)
print("✅ Analysis Complete!")
print("="*80)