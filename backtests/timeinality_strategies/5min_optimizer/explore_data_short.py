"""
5-Minute SHORT Strategy Data Explorer
=======================================
Explores the results from 5-minute SHORT optimizer with filters and analysis.

Filters:
1. Minimum trades threshold (default 8 since we have 8 weeks of data)
2. Show all strategies with > 5% return (not truncated)
3. Ranked by return percentage
"""

import pandas as pd
import os

# Disable truncation for display
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)
pd.set_option('display.float_format', lambda x: '%.6f' % x)

print("📊 Moon Dev's 5-Minute SHORT Data Explorer 🌙\n")

# Find the most recent SHORT results CSV
results_dir = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/timeinality_strategies/5min_optimizer/short/results'
csv_files = [f for f in os.listdir(results_dir) if f.endswith('.csv')]
csv_files.sort(reverse=True)  # Most recent first

if not csv_files:
    print("❌ No CSV files found in results directory!")
    exit()

latest_csv = os.path.join(results_dir, csv_files[0])
print(f"📂 Loading: {csv_files[0]}\n")

# Load data
df = pd.read_csv(latest_csv)
print(f"✅ Loaded {len(df)} total backtests\n")

# ============================================================================
# BASIC STATISTICS
# ============================================================================
print("="*100)
print("OVERALL STATISTICS (ALL STRATEGIES)")
print("="*100)
print(f"Total Strategies Tested: {len(df)}")
print(f"Average Return: {df['Return_%'].mean():.2f}%")
print(f"Median Return: {df['Return_%'].median():.2f}%")
print(f"Best Return: {df['Return_%'].max():.2f}%")
print(f"Worst Return: {df['Return_%'].min():.2f}%")
print(f"Positive Return Strategies: {len(df[df['Return_%'] > 0])} ({len(df[df['Return_%'] > 0])/len(df)*100:.1f}%)")
print(f"Negative Return Strategies: {len(df[df['Return_%'] < 0])} ({len(df[df['Return_%'] < 0])/len(df)*100:.1f}%)")

# ============================================================================
# TOP PERFORMERS BY DIFFERENT METRICS
# ============================================================================
print("\n" + "="*100)
print("TOP 30 BY RETURN %")
print("="*100)
top_return = df.nlargest(30, 'Return_%')
print(top_return.to_string(index=False))

print("\n" + "="*100)
print("TOP 30 BY SHARPE RATIO (Risk-Adjusted Returns)")
print("="*100)
top_sharpe = df.nlargest(30, 'Sharpe_Ratio')
print(top_sharpe[['Data_Source', 'Day', 'Time_UTC', 'Return_%', 'Sharpe_Ratio', 'Max_Drawdown_%', 'Win_Rate_%']].to_string(index=False))

print("\n" + "="*100)
print("TOP 30 BY SHALLOWEST DRAWDOWN (Best Risk Management)")
print("="*100)
top_dd = df.nlargest(30, 'Max_Drawdown_%')  # Largest (closest to 0) = shallowest
print(top_dd[['Data_Source', 'Day', 'Time_UTC', 'Return_%', 'Sharpe_Ratio', 'Max_Drawdown_%', 'Win_Rate_%']].to_string(index=False))

print("\n" + "="*100)
print("TOP 30 BY WIN RATE %")
print("="*100)
top_winrate = df.nlargest(30, 'Win_Rate_%')
print(top_winrate[['Data_Source', 'Day', 'Time_UTC', 'Return_%', 'Win_Rate_%', 'Sharpe_Ratio', 'Max_Drawdown_%']].to_string(index=False))

# ============================================================================
# FILTER: High Quality Strategies (Multiple Criteria)
# ============================================================================
print("\n" + "="*100)
print("HIGH QUALITY STRATEGIES (Return > 10%, Sharpe > 2.0, Win Rate > 75%)")
print("="*100)
high_quality = df[
    (df['Return_%'] > 10) &
    (df['Sharpe_Ratio'] > 2.0) &
    (df['Win_Rate_%'] > 75)
].copy()
high_quality_sorted = high_quality.sort_values('Return_%', ascending=False)
print(f"Found {len(high_quality)} high-quality strategies\n")
if len(high_quality) > 0:
    print(high_quality_sorted.to_string(index=False))
else:
    print("No strategies meet all criteria. Try lowering thresholds.")

# ============================================================================
# FILTER: Strategies with > 5% Return
# ============================================================================
RETURN_THRESHOLD = 5.0
df_over_5pct = df[df['Return_%'] > RETURN_THRESHOLD].copy()
df_over_5pct_sorted = df_over_5pct.sort_values('Return_%', ascending=False)

print("\n" + "="*100)
print(f"ALL STRATEGIES WITH > {RETURN_THRESHOLD}% RETURN")
print("="*100)
print(f"Found {len(df_over_5pct)} strategies with return > {RETURN_THRESHOLD}%\n")

if len(df_over_5pct) > 0:
    print(df_over_5pct_sorted.to_string(index=False))

    # Additional analysis for > 5% strategies
    print("\n" + "="*100)
    print(f"ANALYSIS: STRATEGIES WITH > {RETURN_THRESHOLD}% RETURN")
    print("="*100)
    print(f"Total count: {len(df_over_5pct)}")
    print(f"Average Return: {df_over_5pct['Return_%'].mean():.2f}%")
    print(f"Average Sharpe: {df_over_5pct['Sharpe_Ratio'].mean():.2f}")
    print(f"Average Win Rate: {df_over_5pct['Win_Rate_%'].mean():.2f}%")
    print(f"Average Max DD: {df_over_5pct['Max_Drawdown_%'].mean():.2f}%")
    print(f"Average Trades: {df_over_5pct['Total_Trades'].mean():.1f}")

    # Breakdown by symbol
    print("\n" + "-"*100)
    print("BREAKDOWN BY SYMBOL:")
    print("-"*100)
    symbol_counts = df_over_5pct['Data_Source'].value_counts()
    for symbol, count in symbol_counts.items():
        symbol_data = df_over_5pct[df_over_5pct['Data_Source'] == symbol]
        avg_return = symbol_data['Return_%'].mean()
        avg_sharpe = symbol_data['Sharpe_Ratio'].mean()
        avg_winrate = symbol_data['Win_Rate_%'].mean()
        print(f"{symbol}: {count} strategies | Avg Return: {avg_return:.2f}% | Avg Sharpe: {avg_sharpe:.2f} | Avg WR: {avg_winrate:.1f}%")

    # Breakdown by day
    print("\n" + "-"*100)
    print("BREAKDOWN BY DAY OF WEEK:")
    print("-"*100)
    day_counts = df_over_5pct['Day'].value_counts()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for day in day_order:
        if day in day_counts.index:
            count = day_counts[day]
            day_data = df_over_5pct[df_over_5pct['Day'] == day]
            avg_return = day_data['Return_%'].mean()
            avg_sharpe = day_data['Sharpe_Ratio'].mean()
            print(f"{day}: {count} strategies | Avg Return: {avg_return:.2f}% | Avg Sharpe: {avg_sharpe:.2f}")

    # Breakdown by hour
    print("\n" + "-"*100)
    print("BREAKDOWN BY HOUR (ALL 24 HOURS):")
    print("-"*100)
    hour_counts = df_over_5pct['Hour_UTC'].value_counts().sort_index()
    for hour in range(24):
        if hour in hour_counts.index:
            count = hour_counts[hour]
            hour_data = df_over_5pct[df_over_5pct['Hour_UTC'] == hour]
            avg_return = hour_data['Return_%'].mean()
            avg_sharpe = hour_data['Sharpe_Ratio'].mean()
            print(f"Hour {hour:02d}:XX: {count} strategies | Avg Return: {avg_return:.2f}% | Avg Sharpe: {avg_sharpe:.2f}")

    # Best 5-minute interval per hour
    print("\n" + "-"*100)
    print("BEST 5-MINUTE INTERVAL FOR EACH HOUR (Top Return):")
    print("-"*100)
    for hour in range(24):
        hour_data = df_over_5pct[df_over_5pct['Hour_UTC'] == hour]
        if len(hour_data) > 0:
            best = hour_data.nlargest(1, 'Return_%').iloc[0]
            print(f"Hour {hour:02d}:XX → {best['Time_UTC']} | {best['Data_Source']} | {best['Day']} | Return: {best['Return_%']:.2f}% | Sharpe: {best['Sharpe_Ratio']:.2f}")

else:
    print(f"No strategies found with return > {RETURN_THRESHOLD}%")

# ============================================================================
# CONSISTENCY ANALYSIS: Same time across different symbols
# ============================================================================
print("\n" + "="*100)
print("CONSISTENCY CHECK: Times that work well across multiple symbols")
print("="*100)
# Group by Day + Time and count how many symbols perform well there
time_performance = df_over_5pct.groupby(['Day', 'Time_UTC']).agg({
    'Data_Source': 'count',
    'Return_%': 'mean',
    'Sharpe_Ratio': 'mean',
    'Win_Rate_%': 'mean'
}).rename(columns={'Data_Source': 'Symbol_Count'})
time_performance = time_performance[time_performance['Symbol_Count'] >= 3]  # At least 3 symbols
time_performance = time_performance.sort_values('Return_%', ascending=False)
print(f"Found {len(time_performance)} time slots that work for 3+ symbols\n")
print(time_performance.head(20).to_string())

# ============================================================================
# RISK-ADJUSTED RANKINGS
# ============================================================================
print("\n" + "="*100)
print("RISK-ADJUSTED RANKING (Return/MaxDD Ratio)")
print("="*100)
df_positive = df[df['Return_%'] > 0].copy()
df_positive['Return_DD_Ratio'] = df_positive['Return_%'] / abs(df_positive['Max_Drawdown_%'])
top_risk_adjusted = df_positive.nlargest(30, 'Return_DD_Ratio')
print(top_risk_adjusted[['Data_Source', 'Day', 'Time_UTC', 'Return_%', 'Max_Drawdown_%', 'Return_DD_Ratio', 'Sharpe_Ratio', 'Win_Rate_%']].to_string(index=False))

print("\n" + "="*100)
print("EXPLORATION COMPLETE! 🌙")
print("="*100)
