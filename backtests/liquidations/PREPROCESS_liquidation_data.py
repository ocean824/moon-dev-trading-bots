"""
Moon Dev's Liquidation Data Preprocessor
=========================================
Preprocesses raw liquidation data from Moon Dev API into a standard format
ready for all backtesting strategies.

This script:
1. Loads raw liquidation data (12 columns, no headers)
2. Adds proper column names
3. Creates datetime from timestamp_ms
4. Converts all numeric columns
5. Adds useful derived columns
6. Saves preprocessed data for quick loading in backtests
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# ==============================================================================
# CONFIGURATION - Change symbol here to process different assets
# ==============================================================================
SYMBOL = 'BTC'  # Options: 'BTC', 'ETH', 'SOL', None (for all symbols)

print("🌙 Moon Dev's Liquidation Data Preprocessor 🚀")
print("=" * 60)

def preprocess_liquidation_data(input_path, output_path=None, symbol_filter='BTC'):
    """
    Preprocess raw liquidation data into standard format

    Parameters:
    -----------
    input_path : str
        Path to raw liquidation CSV file (12 columns, no headers)
    output_path : str, optional
        Path to save preprocessed data. If None, saves with '_preprocessed' suffix
    symbol_filter : str, optional
        Symbol to filter for (e.g., 'BTC', 'ETH', 'SOL'). If None, includes all symbols.
        Default is 'BTC'

    Returns:
    --------
    pd.DataFrame
        Preprocessed liquidation data with proper columns and datetime index
    """

    print(f"\n📊 Loading raw liquidation data from: {input_path}")

    # Define the 12 column names for raw data
    column_names = [
        'symbol',           # Trading pair (e.g., "BTC", "ETH")
        'side',            # "BUY" (long liq) or "SELL" (short liq)
        'order_type',      # "LIMIT", "MARKET"
        'time_in_force',   # "IOC", "GTC", etc.
        'quantity',        # Original quantity
        'price',           # Liquidation price
        'avg_price',       # Average fill price
        'status',          # "FILLED", "PARTIAL"
        'filled_qty',      # Filled quantity
        'total_qty',       # Total quantity
        'timestamp_ms',    # Unix timestamp in milliseconds
        'usd_value'        # USD value of liquidation
    ]

    # Load data with proper column names
    data = pd.read_csv(input_path, names=column_names)
    print(f"✅ Loaded {len(data):,} total liquidation records")

    # Check what symbols are available
    unique_symbols = data['symbol'].unique()
    print(f"📊 Found {len(unique_symbols)} unique symbols in data")
    print(f"First 10 symbols: {list(unique_symbols[:10])}")

    # Filter by symbol if specified
    if symbol_filter:
        print(f"🔍 Filtering for {symbol_filter} liquidations only...")
        # Try exact match first
        filtered_data = data[data['symbol'] == symbol_filter]

        # If no exact match, try case-insensitive or with USDT suffix
        if len(filtered_data) == 0:
            # Try with USDT suffix
            filtered_data = data[data['symbol'] == f"{symbol_filter}USDT"]
            if len(filtered_data) == 0:
                # Try case-insensitive match
                filtered_data = data[data['symbol'].str.upper() == symbol_filter.upper()]
                if len(filtered_data) == 0:
                    # Try case-insensitive with USDT
                    filtered_data = data[data['symbol'].str.upper() == f"{symbol_filter.upper()}USDT"]

        data = filtered_data
        print(f"✅ Found {len(data):,} {symbol_filter} liquidation records")

        if len(data) == 0:
            print(f"⚠️ WARNING: No liquidations found for symbol {symbol_filter}")
            print("Available symbols in data:", unique_symbols[:20])
            return None
    else:
        print("📊 Processing ALL symbols (no filter applied)")
        print(f"Unique symbols found: {data['symbol'].nunique()}")

    # Convert numeric columns
    print("\n🔧 Converting numeric columns...")
    numeric_columns = ['quantity', 'price', 'avg_price', 'filled_qty',
                       'total_qty', 'timestamp_ms', 'usd_value']

    for col in numeric_columns:
        data[col] = pd.to_numeric(data[col], errors='coerce')

    # Create datetime from timestamp_ms
    print("📅 Creating datetime column from timestamps...")
    data['datetime'] = pd.to_datetime(data['timestamp_ms'], unit='ms')

    # Add useful derived columns
    print("➕ Adding derived columns...")

    # Separate long and short liquidations
    data['is_long_liquidation'] = data['side'].str.upper() == 'BUY'
    data['is_short_liquidation'] = data['side'].str.upper() == 'SELL'

    # USD values for long/short separately
    data['long_liq_usd'] = np.where(data['is_long_liquidation'], data['usd_value'], 0)
    data['short_liq_usd'] = np.where(data['is_short_liquidation'], data['usd_value'], 0)

    # Add date components for easier filtering
    data['date'] = data['datetime'].dt.date
    data['hour'] = data['datetime'].dt.hour
    data['day_of_week'] = data['datetime'].dt.dayofweek
    data['month'] = data['datetime'].dt.month
    data['year'] = data['datetime'].dt.year

    # Add liquidation size categories
    data['size_category'] = pd.cut(
        data['usd_value'],
        bins=[0, 10_000, 100_000, 1_000_000, 10_000_000, float('inf')],
        labels=['Small (<10K)', 'Medium (10K-100K)', 'Large (100K-1M)',
                'Huge (1M-10M)', 'Whale (>10M)']
    )

    # Clean up any NaN values
    print("🧹 Cleaning data...")
    initial_count = len(data)
    data = data.dropna(subset=['datetime', 'price', 'usd_value'])
    removed_count = initial_count - len(data)

    if removed_count > 0:
        print(f"⚠️ Removed {removed_count:,} rows with invalid data")

    # Sort by datetime
    data = data.sort_values('datetime')

    # Set datetime as index
    data.set_index('datetime', inplace=True)

    # Print summary statistics
    print("\n📊 Preprocessed Data Summary:")
    print(f"Total records: {len(data):,}")
    print(f"Date range: {data.index.min()} to {data.index.max()}")
    print(f"Total days: {(data.index.max() - data.index.min()).days}")
    print(f"\n💰 Liquidation Statistics:")
    print(f"Total USD liquidated: ${data['usd_value'].sum():,.2f}")
    print(f"Long liquidations: ${data['long_liq_usd'].sum():,.2f}")
    print(f"Short liquidations: ${data['short_liq_usd'].sum():,.2f}")
    print(f"Average liquidation size: ${data['usd_value'].mean():,.2f}")
    print(f"Median liquidation size: ${data['usd_value'].median():,.2f}")
    print(f"Max single liquidation: ${data['usd_value'].max():,.2f}")

    # Liquidation size distribution
    print(f"\n📊 Size Distribution:")
    size_dist = data['size_category'].value_counts()
    for category in size_dist.index:
        count = size_dist[category]
        pct = (count / len(data)) * 100
        print(f"  {category}: {count:,} ({pct:.2f}%)")

    # Save preprocessed data
    if output_path is None:
        # Add symbol and '_preprocessed' before the file extension
        base, ext = os.path.splitext(input_path)
        if symbol_filter:
            output_path = f"{base}_{symbol_filter}_preprocessed{ext}"
        else:
            output_path = f"{base}_ALL_preprocessed{ext}"

    print(f"\n💾 Saving preprocessed data to: {output_path}")
    data.to_csv(output_path)

    file_size_mb = os.path.getsize(output_path) / (1024**2)
    print(f"✅ Saved! File size: {file_size_mb:.2f} MB")

    return data


def create_resampled_ohlcv(data, timeframe='1T', save_path=None):
    """
    Create OHLCV data from liquidation data for backtesting

    Parameters:
    -----------
    data : pd.DataFrame
        Preprocessed liquidation data
    timeframe : str
        Resampling timeframe ('1T' for 1 minute, '5T' for 5 minutes, etc.)
    save_path : str, optional
        Path to save resampled data

    Returns:
    --------
    pd.DataFrame
        Resampled OHLCV data with liquidation volumes
    """

    print(f"\n⏱️ Creating {timeframe} resampled OHLCV data...")

    # Resample to specified timeframe
    resampled = data.resample(timeframe).agg({
        'price': ['first', 'max', 'min', 'last', 'mean'],
        'usd_value': 'sum',
        'long_liq_usd': 'sum',
        'short_liq_usd': 'sum',
        'symbol': 'count'  # Count of liquidations
    })

    # Flatten column names
    resampled.columns = ['Open', 'High', 'Low', 'Close', 'price',
                         'total_liquidations', 'long_liquidations',
                         'short_liquidations', 'liquidation_count']

    # Forward fill price data
    price_columns = ['Open', 'High', 'Low', 'Close', 'price']
    resampled[price_columns] = resampled[price_columns].ffill()

    # Fill liquidation data with zeros
    liq_columns = ['total_liquidations', 'long_liquidations',
                   'short_liquidations', 'liquidation_count']
    resampled[liq_columns] = resampled[liq_columns].fillna(0)

    # Add Volume column (using total liquidations as proxy)
    resampled['Volume'] = resampled['total_liquidations']

    # Drop rows with no price data
    resampled = resampled.dropna(subset=['Close'])

    print(f"✅ Created {len(resampled):,} {timeframe} bars")

    if save_path:
        print(f"💾 Saving resampled data to: {save_path}")
        resampled.to_csv(save_path)

    return resampled


# Main execution
if __name__ == "__main__":

    # Input and output paths
    RAW_DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_full.csv'

    # Output paths now include symbol
    if SYMBOL:
        PREPROCESSED_PATH = f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_{SYMBOL}_preprocessed.csv'
        RESAMPLED_1M_PATH = f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_{SYMBOL}_1m_ohlcv.csv'
        RESAMPLED_5M_PATH = f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_{SYMBOL}_5m_ohlcv.csv'
    else:
        PREPROCESSED_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_ALL_preprocessed.csv'
        RESAMPLED_1M_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_ALL_1m_ohlcv.csv'
        RESAMPLED_5M_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_ALL_5m_ohlcv.csv'

    print(f"🎯 Processing liquidation data for: {SYMBOL if SYMBOL else 'ALL SYMBOLS'}")

    # Check if preprocessed file already exists
    if os.path.exists(PREPROCESSED_PATH):
        print(f"📂 Found existing preprocessed file: {PREPROCESSED_PATH}")
        user_input = input("Do you want to reprocess? (y/n): ").lower()

        if user_input == 'y':
            # Preprocess the raw data with symbol filter
            data = preprocess_liquidation_data(RAW_DATA_PATH, PREPROCESSED_PATH, symbol_filter=SYMBOL)
        else:
            print("📊 Loading existing preprocessed data...")
            data = pd.read_csv(PREPROCESSED_PATH, index_col='datetime', parse_dates=True)
            print(f"✅ Loaded {len(data):,} records")
    else:
        # Preprocess the raw data with symbol filter
        data = preprocess_liquidation_data(RAW_DATA_PATH, PREPROCESSED_PATH, symbol_filter=SYMBOL)

    # Check if we have data to process
    if data is None:
        print("\n❌ No data to process. Exiting...")
        exit(1)

    # Create resampled versions for backtesting
    print("\n🎯 Creating resampled data for backtesting...")

    # 1-minute bars
    ohlcv_1m = create_resampled_ohlcv(data, '1T', RESAMPLED_1M_PATH)

    # 5-minute bars
    ohlcv_5m = create_resampled_ohlcv(data, '5T', RESAMPLED_5M_PATH)

    print("\n" + "=" * 60)
    print("✅ PREPROCESSING COMPLETE!")
    print("=" * 60)
    print("\n📁 Generated Files:")
    print(f"1. Preprocessed data: {PREPROCESSED_PATH}")
    print(f"2. 1-minute OHLCV: {RESAMPLED_1M_PATH}")
    print(f"3. 5-minute OHLCV: {RESAMPLED_5M_PATH}")
    print("\n🚀 Ready for backtesting!")