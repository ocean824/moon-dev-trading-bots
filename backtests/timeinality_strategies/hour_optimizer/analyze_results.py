"""
Hour Optimizer Results Analyzer
================================
Analyzes all CSV results from hour optimization backtests and creates a comprehensive markdown report.

Reports Top 10 for:
- Highest Return %
- Highest Sharpe Ratio
- Lowest Max Drawdown %

For all 4 strategy types:
- Short Optimizer (separate day-hour combos)
- Short Combined Days (all days per hour)
- Long Optimizer (separate day-hour combos)
- Long Combined Days (all days per hour)
"""

import pandas as pd
import glob
import os
from datetime import datetime

# Disable scientific notation
pd.set_option('display.float_format', lambda x: '%.6f' % x)
pd.options.display.float_format = '{:.6f}'.format

print("🔍 Moon Dev's Hour Optimizer Results Analyzer Loading... 🌙\n")

# Find all result CSVs
short_optimizer_csvs = glob.glob('./short/results/hourly_short_optimizer_*.csv')
short_combined_csvs = glob.glob('./short/results/hourly_short_combined_*.csv')
long_optimizer_csvs = glob.glob('./long/results/hourly_long_optimizer_*.csv')
long_combined_csvs = glob.glob('./long/results/hourly_long_combined_*.csv')

print(f"📊 Found CSV files:")
print(f"   Short Optimizer: {len(short_optimizer_csvs)}")
print(f"   Short Combined: {len(short_combined_csvs)}")
print(f"   Long Optimizer: {len(long_optimizer_csvs)}")
print(f"   Long Combined: {len(long_combined_csvs)}")

# Load the most recent CSV from each category
def get_most_recent_csv(csv_list):
    if not csv_list:
        return None
    return max(csv_list, key=os.path.getctime)

short_opt_csv = get_most_recent_csv(short_optimizer_csvs)
short_comb_csv = get_most_recent_csv(short_combined_csvs)
long_opt_csv = get_most_recent_csv(long_optimizer_csvs)
long_comb_csv = get_most_recent_csv(long_combined_csvs)

print(f"\n📂 Using most recent CSVs:")
print(f"   Short Optimizer: {os.path.basename(short_opt_csv) if short_opt_csv else 'None'}")
print(f"   Short Combined: {os.path.basename(short_comb_csv) if short_comb_csv else 'None'}")
print(f"   Long Optimizer: {os.path.basename(long_opt_csv) if long_opt_csv else 'None'}")
print(f"   Long Combined: {os.path.basename(long_comb_csv) if long_comb_csv else 'None'}")

# Load data
datasets = {}
if short_opt_csv:
    datasets['Short_Optimizer'] = pd.read_csv(short_opt_csv)
    print(f"✅ Loaded Short Optimizer: {len(datasets['Short_Optimizer'])} rows")
if short_comb_csv:
    datasets['Short_Combined'] = pd.read_csv(short_comb_csv)
    print(f"✅ Loaded Short Combined: {len(datasets['Short_Combined'])} rows")
if long_opt_csv:
    datasets['Long_Optimizer'] = pd.read_csv(long_opt_csv)
    print(f"✅ Loaded Long Optimizer: {len(datasets['Long_Optimizer'])} rows")
if long_comb_csv:
    datasets['Long_Combined'] = pd.read_csv(long_comb_csv)
    print(f"✅ Loaded Long Combined: {len(datasets['Long_Combined'])} rows")

# Generate markdown report
print("\n📝 Generating markdown report...")

markdown_content = f"""# Hour Optimizer Results Analysis

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This report analyzes the performance of hourly trading strategies across different timeframes and data sources.

## Strategy Overview

| Strategy Type | Description | Total Backtests |
|--------------|-------------|-----------------|
"""

for name, df in datasets.items():
    desc = {
        'Short_Optimizer': 'Tests each day-hour combination separately',
        'Short_Combined': 'Tests each hour on all days combined',
        'Long_Optimizer': 'Tests each day-hour combination separately',
        'Long_Combined': 'Tests each hour on all days combined'
    }
    markdown_content += f"| {name.replace('_', ' ')} | {desc[name]} | {len(df)} |\n"

markdown_content += "\n---\n\n"

# Generate top 10 tables for each dataset and metric
for dataset_name, df in datasets.items():
    markdown_content += f"# {dataset_name.replace('_', ' ')}\n\n"

    # Top 10 Highest Return
    markdown_content += f"## 🏆 Top 10 Highest Return %\n\n"
    top_return = df.nlargest(10, 'Return_%')

    # Determine columns to show
    if 'Day' in df.columns:
        # Optimizer format (separate days)
        markdown_content += "| Rank | Data Source | Day | Hour UTC | Return % | Sharpe | Max DD % | Trades | Win Rate % | Profit Factor |\n"
        markdown_content += "|------|-------------|-----|----------|----------|--------|----------|--------|------------|---------------|\n"
        for idx, (i, row) in enumerate(top_return.iterrows(), 1):
            markdown_content += f"| {idx} | {row['Data_Source']} | {row['Day']} | {row['Hour_UTC']:02.0f}:00 | {row['Return_%']:.2f} | {row['Sharpe_Ratio']:.3f} | {row['Max_Drawdown_%']:.2f} | {int(row['Total_Trades'])} | {row['Win_Rate_%']:.1f} | {row['Profit_Factor']:.3f} |\n"
    else:
        # Combined format
        markdown_content += "| Rank | Data Source | Days Tested | Hour UTC | Return % | Sharpe | Max DD % | Trades | Win Rate % | Profit Factor |\n"
        markdown_content += "|------|-------------|-------------|----------|----------|--------|----------|--------|------------|---------------|\n"
        for idx, (i, row) in enumerate(top_return.iterrows(), 1):
            markdown_content += f"| {idx} | {row['Data_Source']} | {row['Days_Tested']} | {row['Hour_UTC']:02.0f}:00 | {row['Return_%']:.2f} | {row['Sharpe_Ratio']:.3f} | {row['Max_Drawdown_%']:.2f} | {int(row['Total_Trades'])} | {row['Win_Rate_%']:.1f} | {row['Profit_Factor']:.3f} |\n"

    markdown_content += "\n"

    # Top 10 Highest Sharpe Ratio
    markdown_content += f"## 📊 Top 10 Highest Sharpe Ratio\n\n"
    top_sharpe = df.nlargest(10, 'Sharpe_Ratio')

    if 'Day' in df.columns:
        markdown_content += "| Rank | Data Source | Day | Hour UTC | Sharpe | Return % | Max DD % | Trades | Win Rate % | Profit Factor |\n"
        markdown_content += "|------|-------------|-----|----------|--------|----------|----------|--------|------------|---------------|\n"
        for idx, (i, row) in enumerate(top_sharpe.iterrows(), 1):
            markdown_content += f"| {idx} | {row['Data_Source']} | {row['Day']} | {row['Hour_UTC']:02.0f}:00 | {row['Sharpe_Ratio']:.3f} | {row['Return_%']:.2f} | {row['Max_Drawdown_%']:.2f} | {int(row['Total_Trades'])} | {row['Win_Rate_%']:.1f} | {row['Profit_Factor']:.3f} |\n"
    else:
        markdown_content += "| Rank | Data Source | Days Tested | Hour UTC | Sharpe | Return % | Max DD % | Trades | Win Rate % | Profit Factor |\n"
        markdown_content += "|------|-------------|-------------|----------|--------|----------|----------|--------|------------|---------------|\n"
        for idx, (i, row) in enumerate(top_sharpe.iterrows(), 1):
            markdown_content += f"| {idx} | {row['Data_Source']} | {row['Days_Tested']} | {row['Hour_UTC']:02.0f}:00 | {row['Sharpe_Ratio']:.3f} | {row['Return_%']:.2f} | {row['Max_Drawdown_%']:.2f} | {int(row['Total_Trades'])} | {row['Win_Rate_%']:.1f} | {row['Profit_Factor']:.3f} |\n"

    markdown_content += "\n"

    # Top 10 Lowest Max Drawdown (best risk management)
    markdown_content += f"## 🛡️ Top 10 Lowest Max Drawdown %\n\n"
    top_drawdown = df.nsmallest(10, 'Max_Drawdown_%')

    if 'Day' in df.columns:
        markdown_content += "| Rank | Data Source | Day | Hour UTC | Max DD % | Return % | Sharpe | Trades | Win Rate % | Profit Factor |\n"
        markdown_content += "|------|-------------|-----|----------|----------|----------|--------|--------|------------|---------------|\n"
        for idx, (i, row) in enumerate(top_drawdown.iterrows(), 1):
            markdown_content += f"| {idx} | {row['Data_Source']} | {row['Day']} | {row['Hour_UTC']:02.0f}:00 | {row['Max_Drawdown_%']:.2f} | {row['Return_%']:.2f} | {row['Sharpe_Ratio']:.3f} | {int(row['Total_Trades'])} | {row['Win_Rate_%']:.1f} | {row['Profit_Factor']:.3f} |\n"
    else:
        markdown_content += "| Rank | Data Source | Days Tested | Hour UTC | Max DD % | Return % | Sharpe | Trades | Win Rate % | Profit Factor |\n"
        markdown_content += "|------|-------------|-------------|----------|----------|----------|--------|--------|------------|---------------|\n"
        for idx, (i, row) in enumerate(top_drawdown.iterrows(), 1):
            markdown_content += f"| {idx} | {row['Data_Source']} | {row['Days_Tested']} | {row['Hour_UTC']:02.0f}:00 | {row['Max_Drawdown_%']:.2f} | {row['Return_%']:.2f} | {row['Sharpe_Ratio']:.3f} | {int(row['Total_Trades'])} | {row['Win_Rate_%']:.1f} | {row['Profit_Factor']:.3f} |\n"

    markdown_content += "\n---\n\n"

# Add summary statistics at the end
markdown_content += "# Summary Statistics\n\n"
markdown_content += "## Overall Performance by Strategy Type\n\n"
markdown_content += "| Strategy | Avg Return % | Median Return % | Best Return % | Worst Return % | Avg Sharpe | Avg Max DD % |\n"
markdown_content += "|----------|--------------|-----------------|---------------|----------------|------------|-------------|\n"

for name, df in datasets.items():
    markdown_content += f"| {name.replace('_', ' ')} | {df['Return_%'].mean():.2f} | {df['Return_%'].median():.2f} | {df['Return_%'].max():.2f} | {df['Return_%'].min():.2f} | {df['Sharpe_Ratio'].mean():.3f} | {df['Max_Drawdown_%'].mean():.2f} |\n"

markdown_content += "\n---\n\n"
markdown_content += "*Analysis completed by Moon Dev's Hour Optimizer Results Analyzer 🌙*\n"

# Save markdown file
output_file = 'FINAL_RESULTS.md'
with open(output_file, 'w') as f:
    f.write(markdown_content)

print(f"\n✅ Markdown report generated: {output_file}")
print(f"📊 Report includes top 10 tables for {len(datasets)} strategy types")
print(f"🎯 Metrics analyzed: Return %, Sharpe Ratio, Max Drawdown %")
print("\n🌙 Analysis complete! Check FINAL_RESULTS.md for full report.")
