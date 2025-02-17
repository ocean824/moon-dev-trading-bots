'''
This is how you download data from Yahoo on the daily time frame. 
'''

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import logging


# Define the save directory
save_dir = 'data/yahoo_daily'

# Ensure the directory exists
os.makedirs(save_dir, exist_ok=True)

# Setup logging
logging.basicConfig(
    filename=os.path.join(save_dir, 'data_download.log'),
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)


# List of symbols (including futures)
symbols = [
    ('AAPL', 'stock'),
    ('GOOGL', 'stock'),
    ('MSFT', 'stock'),
    ('AMZN', 'stock'),
    ('EURUSD=X', 'forex'),
    ('GBPUSD=X', 'forex'),
    ('USDJPY=X', 'forex'),
    ('AUDUSD=X', 'forex'),
    ('ES=F', 'future'),  # S&P 500 futures
    ('NQ=F', 'future'),  # NASDAQ 100 futures
    ('YM=F', 'future'),  # Dow Jones futures
    ('RTY=F', 'future'),  # Russell 2000 futures
    ('GC=F', 'future'),  # Gold futures
    ('SI=F', 'future'),  # Silver futures
    ('CL=F', 'future'),  # Crude Oil futures
    ('NG=F', 'future')   # Natural Gas futures
]


def download_and_save_daily(symbol, asset_type):
    print(f"\nStarting download for {symbol} ({asset_type})")
    logging.info(f"Starting download for {symbol}")
    
    file_name = f"{symbol.replace('=', '_')}_{asset_type}_1d.csv"
    file_path = os.path.join(save_dir, file_name)
    
    # Determine start date
    if os.path.exists(file_path):
        try:
            existing_data = pd.read_csv(file_path, index_col='Date', parse_dates=True)
            existing_data.index = existing_data.index.tz_localize(None)
            last_date = existing_data.index[-1]
            print(f"Loaded existing data for {symbol}. Last date: {last_date}")
            logging.info(f"Loaded existing data for {symbol}. Last date: {last_date}")
            start_date = last_date + timedelta(days=1)
        except Exception as e:
            print(f"Error loading existing daily data for {symbol}: {e}. Starting from scratch.")
            logging.error(f"Error loading existing daily data for {symbol}: {e}. Starting from scratch.")
            existing_data = pd.DataFrame()
            start_date = datetime(2000, 1, 1)
    else:
        existing_data = pd.DataFrame()
        start_date = datetime(2000, 1, 1)
    
    # Set end_date to yesterday
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    
    if start_date > end_date:
        print(f"No new data to download for {symbol}.")
        logging.info(f"No new data to download for {symbol}.")
        return len(existing_data) if not existing_data.empty else 0
    
    print("Stage 1: Downloading recent data")
    # Try to download the most recent days individually
    all_new_data = pd.DataFrame()
    current_date = end_date
    attempts = 0
    max_attempts = 3  # Try up to 3 days back
    
    while attempts < max_attempts and current_date >= start_date:
        try:
            print(f"Attempting to download data for {symbol} on {current_date.date()}")
            data = yf.download(symbol, start=current_date, end=current_date + timedelta(days=1), interval='1d', progress=False)
            
            if not data.empty:
                data.index = data.index.tz_localize(None)
                all_new_data = pd.concat([data, all_new_data])
                print(f"Successfully downloaded data for {symbol} on {current_date.date()}")
                attempts = 0  # Reset attempts on successful download
            else:
                print(f"No data found for {symbol} on {current_date.date()}")
                attempts += 1
        
        except Exception as e:
            print(f"Error downloading data for {symbol} on {current_date.date()}: {e}")
            attempts += 1
        
        current_date -= timedelta(days=1)
        time.sleep(1)  # Rate limiting
    
    # If we've downloaded recent data, update the start_date for historical download
    if not all_new_data.empty:
        start_date = min(start_date, all_new_data.index[0] - timedelta(days=1))
    
    print("Stage 2: Downloading historical data")
    # Download historical data in chunks
    chunk_size = timedelta(days=365)
    while start_date <= current_date:
        chunk_end = min(start_date + chunk_size, current_date)
        try:
            print(f"Fetching historical data for {symbol} from {start_date.date()} to {chunk_end.date()}")
            data = yf.download(symbol, start=start_date, end=chunk_end + timedelta(days=1), interval='1d', progress=False)
            
            if not data.empty:
                data.index = data.index.tz_localize(None)
                all_new_data = pd.concat([data, all_new_data])
                print(f"Downloaded historical data for {symbol} from {start_date.date()} to {chunk_end.date()}")
            else:
                print(f"No historical data found for {symbol} from {start_date.date()} to {chunk_end.date()}")
        
        except Exception as e:
            print(f"Error downloading historical data for {symbol} from {start_date.date()} to {chunk_end.date()}: {e}")
        
        start_date = chunk_end + timedelta(days=1)
        time.sleep(1)  # Rate limiting
    
    print("Stage 3: Processing and saving data")
    if not all_new_data.empty:
        if not existing_data.empty:
            try:
                combined_data = pd.concat([existing_data, all_new_data]).drop_duplicates()
                print(f"Merged existing and new data for {symbol}")
            except Exception as e:
                print(f"Error merging existing and new data for {symbol}: {e}. Saving new data only.")
                combined_data = all_new_data
        else:
            combined_data = all_new_data
        
        combined_data.sort_index(inplace=True)
        combined_data.to_csv(file_path, date_format='%Y-%m-%d')
        print(f"Saved data for {symbol}. Total rows: {len(combined_data)}")
        return len(combined_data)
    else:
        print(f"No new data to save for {symbol}.")
        return len(existing_data) if not existing_data.empty else 0

def download_all_daily_data():
    for symbol, asset_type in symbols:
        rows = download_and_save_daily(symbol, asset_type)
        print(f"Total rows for {symbol} daily data: {rows}")
        logging.info(f"Total rows for {symbol} daily data: {rows}")
    
    print("\nAll daily data download attempts completed.")
    logging.info("All daily data download attempts completed.")

# Execute the download process
if __name__ == "__main__":
    print("Starting daily data download process...")
    download_all_daily_data()
    print("Daily data download process completed.")