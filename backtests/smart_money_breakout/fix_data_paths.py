#!/usr/bin/env python3
"""
Fix data paths in all Smart Money strategy files
"""

import os
import glob

# Find all smart_money_*.py files
strategy_files = glob.glob('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/smart_money_breakout/smart_money_*.py')

# The old incorrect path and the new correct path
old_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/BTC-USD_daily.csv'
new_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

for filepath in strategy_files:
    print(f"Checking {os.path.basename(filepath)}...")

    with open(filepath, 'r') as f:
        content = f.read()

    if old_path in content:
        # Replace the old path with the new path
        content = content.replace(old_path, new_path)

        # Also fix the data loading function to handle the coinbase format
        if 'pd.read_csv(data_path, parse_dates=[\'Date\'])' in content:
            content = content.replace(
                "pd.read_csv(data_path, parse_dates=['Date'])",
                "pd.read_csv(data_path, parse_dates=['datetime'])"
            )
            content = content.replace(
                "df = df.set_index('Date')",
                "df = df.set_index('datetime')"
            )

        # Fix column names for coinbase data
        if 'def run_backtest(data_path' in content:
            # Find and replace the run_backtest function
            old_func = '''def run_backtest(data_path, cash=1000000, commission=0.001):
    """Run backtest on a single dataset"""
    try:
        # Load data
        df = pd.read_csv(data_path, parse_dates=['Date'])
        df = df.set_index('Date')

        # Ensure required columns exist
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']'''

            new_func = '''def run_backtest(data_path, cash=1000000, commission=0.001):
    """Run backtest on a single dataset"""
    try:
        # Load data - handle coinbase format
        df = pd.read_csv(data_path, parse_dates=['datetime'])
        df = df.set_index('datetime')

        # Rename columns to match backtesting.py requirements
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

        # Ensure required columns exist
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']'''

            if old_func in content:
                content = content.replace(old_func, new_func)

        # Write back the fixed content
        with open(filepath, 'w') as f:
            f.write(content)

        print(f"✅ Fixed {os.path.basename(filepath)}")
    else:
        # Check if it's using a different pattern
        if '/data/BTC-USD' in content or 'BTC-USD_' in content:
            print(f"⚠️  Found different pattern in {os.path.basename(filepath)}, needs manual check")
        else:
            print(f"✓  {os.path.basename(filepath)} - no changes needed")

print("\n✅ Data paths fixed!")