"""
CSV Results Viewer - Summary View
==================================
Reads all CSV files from a folder and displays key metrics only.
Perfect for quick overview of backtest performance.
"""

# ============================================================================
# CHANGE THIS PATH TO VIEW DIFFERENT FOLDERS
# ============================================================================
FOLDER_PATH = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/angled_volume_profile/results"  # <-- CHANGE THIS PATH HERE!
# ============================================================================

import pandas as pd
from pathlib import Path

# Set pandas display options for better viewing
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)
pd.set_option('display.float_format', lambda x: f'{x:.2f}' if pd.notna(x) else '')

# Key metrics to display (using actual column names from CSV)
KEY_METRICS = [
    'Data_Source',       # Data source
    'Duration',          # Duration
    'Exposure_Time_%',   # Exposure time
    'Return_%',          # Return percentage
    'Buy_Hold_%',        # Buy & hold percentage
    'Sharpe',            # Sharpe ratio
    'Sortino',           # Sortino ratio
    'Calmar',            # Calmar ratio
    'Max_DD_%',          # Max drawdown
    'Expectancy_%',      # Expectancy
    'Trades'             # Number of trades
]

# Get all CSV files in the folder
folder = Path(FOLDER_PATH)
csv_files = list(folder.glob("*.csv"))

print(f"\n📁 BACKTEST RESULTS SUMMARY")
print(f"📍 Path: {FOLDER_PATH}")
print(f"📊 Found {len(csv_files)} strategy files\n")

# Read and print each CSV with only key metrics
for csv_file in sorted(csv_files):
    print("=" * 150)
    print(f"🚀 Strategy: {csv_file.stem}")
    print("=" * 150)

    df = pd.read_csv(csv_file)

    # Filter to only show columns that exist in the dataframe
    available_cols = [col for col in KEY_METRICS if col in df.columns]

    # Display only the key metrics
    summary_df = df[available_cols]
    print(summary_df.to_string(index=False))
    print("\n")