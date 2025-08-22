import pandas as pd
import numpy as np
from datetime import time
import pytz

# INPUT/OUTPUT FILE CONFIGURATIONS
# Process both 1-hour and 5-minute data files
DATA_FILES = [
    {
        'input': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv',
        'output': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data_inverse_gapped.csv'
    },
    {
        'input': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data.csv',
        'output': '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data_inverse_gapped.csv'
    }
]

# AFTER-HOURS CONFIGURATION (EASTERN TIME)
# Inverse of market hours (9:30 AM - 4:00 PM ET)
# Keep: 4:00 PM - 9:30 AM ET (after-hours and pre-market)
MARKET_CLOSE_HOUR = 16  # 4:00 PM
MARKET_CLOSE_MINUTE = 0
MARKET_OPEN_HOUR = 9  # 9:30 AM
MARKET_OPEN_MINUTE = 30

# Timezone configuration
UTC_TZ = pytz.UTC
EASTERN_TZ = pytz.timezone('US/Eastern')

def inverse_gap_data(df, datetime_column='datetime'):
    """
    Keep only after-hours data (opposite of market hours).
    Keeps data from 4:00 PM - 9:30 AM ET and weekends.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input dataframe with datetime index or column
    datetime_column : str
        Name of the datetime column (if not using index)
        
    Returns:
    --------
    pd.DataFrame
        DataFrame filtered to only include after-hours (4:00 PM - 9:30 AM ET) and weekends
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
    
    # Create after-hours filter (inverse of market hours)
    market_open = time(MARKET_OPEN_HOUR, MARKET_OPEN_MINUTE)
    market_close = time(MARKET_CLOSE_HOUR, MARKET_CLOSE_MINUTE)
    
    # Keep data OUTSIDE market hours (before 9:30 AM or after 4:00 PM)
    after_hours_mask = (
        (datetime_eastern.time < market_open) | 
        (datetime_eastern.time >= market_close)
    )
    
    # Also keep all weekend data (Saturday=5, Sunday=6)
    weekend_mask = datetime_eastern.dayofweek >= 5
    
    # Combine filters: after-hours OR weekends
    final_mask = after_hours_mask | weekend_mask
    
    # Apply filter
    filtered_df = df_copy[final_mask]
    
    # Print statistics
    original_count = len(df_copy)
    filtered_count = len(filtered_df)
    removed_count = original_count - filtered_count
    removal_pct = (removed_count / original_count * 100) if original_count > 0 else 0
    
    print(f"Inverse Data Gapping Statistics:")
    print(f"  Original rows: {original_count:,}")
    print(f"  Filtered rows (after-hours): {filtered_count:,}")
    print(f"  Removed rows (market hours): {removed_count:,} ({removal_pct:.1f}%)")
    print(f"  Keeping: Weekdays 4:00 PM - 9:30 AM ET + All weekend hours")
    
    return filtered_df


def main():
    """
    Process both data files with inverse gapping (after-hours only)
    """
    
    print("=" * 60)
    print("INVERSE DATA GAPPER - After-Hours Filter")
    print("=" * 60)
    print(f"Filtering to After-Hours Trading:")
    print(f"  Weekdays: 4:00 PM - 9:30 AM Eastern Time")
    print(f"  Weekends: All hours (24/7)")
    print("=" * 60)
    
    for file_config in DATA_FILES:
        print(f"\nProcessing: {file_config['input']}")
        print("-" * 40)
        
        # Read CSV with datetime parsing
        df = pd.read_csv(file_config['input'], parse_dates=['datetime'])
        
        # Set datetime as index
        if 'datetime' in df.columns:
            df.set_index('datetime', inplace=True)
        
        # Apply inverse gapping (after-hours only)
        gapped_df = inverse_gap_data(df, 'datetime')
        
        # Save to file
        print(f"Saving inverse gapped data to: {file_config['output']}")
        gapped_df.to_csv(file_config['output'])
        print(f"✅ Complete!")
    
    print("\n" + "=" * 60)
    print("All files processed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()