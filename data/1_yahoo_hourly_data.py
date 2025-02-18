# Number of days of historical data to download
DAYS_OF_DATA = 2000  # 2 years of data

'''
I'm coding a script to get hourly data from Yahoo Finance so I can have data for any stock or futures or even forex. 

This file will be able to grab the data on the hourly. 
'''

import yfinance as yf
import pandas as pd 
from datetime import datetime, timedelta 
import os 
import time 

# save director
save_dir = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/yahoo_hourly'

symbols = ['AAPL', 'TSLA', 'NVDA', 'GOOG']

def download_and_save_hourly(symbol):
    print(f"🌙 Moon Dev's Hourly Data Downloader initiating for {symbol} 🚀")
    print(f"📅 Fetching {DAYS_OF_DATA} days of hourly data")

    file_name = f"{symbol.replace('=', '_')}_hourly.csv"
    file_path = os.path.join(save_dir, file_name)

    end_date = datetime.now().replace(tzinfo=None)
    start_date = end_date - timedelta(days=DAYS_OF_DATA)

    all_data = pd.DataFrame()
    error_count = 0
    chunk_size = timedelta(days=30)

    while error_count < 2:
        chunk_start = max(start_date, end_date - chunk_size)
        
        print(f"🔄 Moon Dev is fetching data from {chunk_start} to {end_date}")

        try: 
            data = yf.download(symbol, start=chunk_start, end=end_date, interval='1h')

            if not data.empty:
                data.index = data.index.tz_localize(None)
                all_data = pd.concat([all_data, data])
                print(f"✨ Moon Dev successfully downloaded {len(data)} rows for {symbol}")
                error_count = 0

            else:
                print(f"⚠️ No data found for {symbol} in the specified date range.")
                error_count += 1

        except Exception as e:
            print(f"❌ Error downloading {symbol}: {e}")
            error_count += 1

        end_date = chunk_start - timedelta(hours=1)
        time.sleep(1) 

    if not all_data.empty:
        all_data = all_data[~all_data.index.duplicated(keep='first')]  # Remove any duplicates
        all_data.sort_index(inplace=True)
        all_data.to_csv(file_path, date_format='%Y-%m-%d %H:%M:%S')
        print(f"💾 Moon Dev saved {len(all_data)} rows for {symbol} to {file_path} 🎉")
        return len(all_data)

    else:
        print(f"😢 No data was downloaded for {symbol}")
        return 0
    
def download_all_hourly_data():
    for symbol in symbols:
        rows = download_and_save_hourly(symbol)
        print(f"Total rows for {symbol} hourly data: {rows}")


if __name__ == "__main__":
    print("Starting hourly data download process...")
    download_all_hourly_data()

    print("\nAll hourly data download attempts completed.")

    
                
