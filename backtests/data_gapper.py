import pandas as pd
import numpy as np
from datetime import time
import pytz

# INPUT/OUTPUT FILE CONFIGURATION
INPUT_FILE = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data.csv'
OUTPUT_FILE = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_gapped.csv'

# MARKET HOURS CONFIGURATION (EASTERN TIME)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16  # 4:00 PM in 24-hour format
MARKET_CLOSE_MINUTE = 0

# Timezone configuration
UTC_TZ = pytz.UTC
EASTERN_TZ = pytz.timezone('US/Eastern')

def gap_data(df, datetime_column='datetime'):
    """
    Remove non-market hours data from a DataFrame.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe with datetime index or column
    datetime_column : str
        Name of the datetime column (if not using index)
        
    Returns:
    --------
    pd.DataFrame
        DataFrame filtered to only include market hours (9:30 AM - 4:00 PM ET)
    """
    
    # Create a copy to avoid modifying the original
    df_copy = df.copy()
    
    # Handle datetime index or column
    if df_copy.index.name == datetime_column or isinstance(df_copy.index, pd.DatetimeIndex):
        datetime_series = df_copy.index
        use_index = True
    else:
        datetime_series = pd.to_datetime(df_copy[datetime_column])
        use_index = False
    
    # Ensure datetime is timezone-aware (assume UTC if not specified)
    if datetime_series.tz is None:
        datetime_series = datetime_series.tz_localize(UTC_TZ)
    elif datetime_series.tz != UTC_TZ:
        datetime_series = datetime_series.tz_convert(UTC_TZ)
    
    # Convert to Eastern Time for filtering
    datetime_eastern = datetime_series.tz_convert(EASTERN_TZ)
    
    # Create market hours filter
    market_open = time(MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE)
    market_close = time(MARKET_CLOSE_HOUR, MARKET_CLOSE_MINUTE)
    
    # Filter for market hours only
    market_hours_mask = (
        (datetime_eastern.time >= market_open) & 
        (datetime_eastern.time < market_close)
    )
    
    # Also filter out weekends (Saturday=5, Sunday=6)
    weekday_mask = datetime_eastern.dayofweek < 5
    
    # Combine filters
    final_mask = market_hours_mask & weekday_mask
    
    # Apply filter
    filtered_df = df_copy[final_mask]
    
    # Print statistics
    original_count = len(df_copy)
    filtered_count = len(filtered_df)
    removed_count = original_count - filtered_count
    removal_pct = (removed_count / original_count * 100) if original_count > 0 else 0
    
    print(f"Data Gapping Statistics:")
    print(f"  Original rows: {original_count:,}")
    print(f"  Filtered rows: {filtered_count:,}")
    print(f"  Removed rows: {removed_count:,} ({removal_pct:.1f}%)")
    print(f"  Market hours: {MARKET_OPEN_HOUR}:{MARKET_OPEN_MINUTE:02d} - {MARKET_CLOSE_HOUR}:{MARKET_CLOSE_MINUTE:02d} ET")
    
    return filtered_df


def gap_csv_file(input_file, output_file=None, datetime_column='datetime'):
    """
    Read a CSV file, gap the data to market hours only, and save the result.
    
    Parameters:
    -----------
    input_file : str
        Path to input CSV file
    output_file : str, optional
        Path to output CSV file. If None, will append '_gapped' to input filename
    datetime_column : str
        Name of the datetime column in the CSV
        
    Returns:
    --------
    pd.DataFrame
        Gapped dataframe
    """
    
    print(f"Loading data from: {input_file}")
    
    # Read CSV with datetime parsing
    df = pd.read_csv(input_file, parse_dates=[datetime_column])
    
    # If datetime is the index, set it
    if datetime_column in df.columns:
        df.set_index(datetime_column, inplace=True)
    
    # Apply gapping
    gapped_df = gap_data(df, datetime_column)
    
    # Save to file if output specified
    if output_file is None:
        # Auto-generate output filename
        import os
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_gapped{ext}"
    
    print(f"Saving gapped data to: {output_file}")
    gapped_df.to_csv(output_file)
    
    return gapped_df


def main():
    """
    Process the configured input file and save gapped output
    """
    
    print("=" * 60)
    print("DATA GAPPER - Market Hours Filter")
    print("=" * 60)
    print(f"Input file: {INPUT_FILE}")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Market hours: {MARKET_OPEN_HOUR}:{MARKET_OPEN_MINUTE:02d} AM - {MARKET_CLOSE_HOUR % 12}:{MARKET_CLOSE_MINUTE:02d} PM ET")
    print("=" * 60)
    
    # Process the file
    gapped_data = gap_csv_file(INPUT_FILE, OUTPUT_FILE, datetime_column='datetime')
    
    print("\nComplete! Gapped data saved to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()