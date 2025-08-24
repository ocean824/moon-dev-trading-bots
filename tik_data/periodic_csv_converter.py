#!/usr/bin/env python3
"""
Periodic CSV Converter for Ultra-Fast Data
Runs continuously and converts latest data to CSV every X minutes

USAGE:
------
python3 periodic_csv_converter.py

WHAT IT DOES:
-------------
Processes ALL symbols (BTC, ETH, SOL) in one run - no parameters needed!
Runs every 5 minutes and converts last 30 days of tick data

HOW TO RUN IN SCREEN:
---------------------
screen -S csv_converter
python3 periodic_csv_converter.py
# Press Ctrl+A, then D to detach

INPUT/OUTPUT:
-------------
Reads from: /root/algos/liqs_oi_funding/ultra_fast_data/BTCUSDT/
           /root/algos/liqs_oi_funding/ultra_fast_data/ETHUSDT/
           /root/algos/liqs_oi_funding/ultra_fast_data/SOLUSDT/
           
Saves to:  /root/algos/liqs_oi_funding/data/btc_tickdata.csv
          /root/algos/liqs_oi_funding/data/eth_tickdata.csv
          /root/algos/liqs_oi_funding/data/sol_tickdata.csv
          
Runs every: 5 minutes (configured below)
"""

# CONFIGURATION - MODIFY THESE AS NEEDED
CONVERSION_INTERVAL_MINUTES = 5  # How often to convert data to CSV
DAYS_TO_PROCESS = 30  # How many days of recent data to include

# PATH CONFIGURATION - CHANGE THESE FOR YOUR SERVER
INPUT_BASE_DIR = "/root/algos/liqs_oi_funding/ultra_fast_data"  # Base dir with BTCUSDT, ETHUSDT, SOLUSDT subfolders
OUTPUT_DIR = "/root/algos/liqs_oi_funding/data"  # Where CSV files will be saved (no subfolders)

import pandas as pd
import numpy as np
import gzip
import json
import glob
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csv_converter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PeriodicCSVConverter:
    def __init__(self):
        self.input_base_dir = Path(INPUT_BASE_DIR)
        self.output_dir = Path(OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.interval_seconds = CONVERSION_INTERVAL_MINUTES * 60
        self.days_to_process = DAYS_TO_PROCESS
        self.running = True
        
        # Define all symbols to process
        self.symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        
        logger.info(f"📊 CSV Converter initialized for ALL symbols")
        logger.info(f"📁 Input directory: {self.input_base_dir.absolute()}")
        logger.info(f"💾 Output directory: {self.output_dir.absolute()}")
        logger.info(f"⏱️  Conversion interval: {CONVERSION_INTERVAL_MINUTES} minutes")
        logger.info(f"📅 Processing last {DAYS_TO_PROCESS} days of data for BTC, ETH, SOL")
    
    def process_binance_order_book(self, data):
        """Convert Binance order book data to our expected format."""
        try:
            result = {
                'timestamp': data['timestamp'],
                'datetime': pd.to_datetime(data['timestamp'], unit='ms')
            }
            
            # Process bids
            bids = data.get('bids', [])
            for i in range(min(15, len(bids))):
                result[f'bid_px_{i}'] = float(bids[i][0])
                result[f'bid_qty_{i}'] = float(bids[i][1])
            
            # Process asks
            asks = data.get('asks', [])
            for i in range(min(15, len(asks))):
                result[f'ask_px_{i}'] = float(asks[i][0])
                result[f'ask_qty_{i}'] = float(asks[i][1])
            
            # Calculate mid price and spread
            if bids and asks:
                result['mid_price'] = (float(bids[0][0]) + float(asks[0][0])) / 2
                result['spread'] = float(asks[0][0]) - float(bids[0][0])
            
            return result
        except (KeyError, IndexError, ValueError):
            return None
    
    def convert_to_csv(self):
        """Convert recent ultra-fast data to CSV format for all symbols."""
        try:
            logger.info("🔄 Starting CSV conversion for all symbols...")
            
            # Process each symbol
            for symbol in self.symbols:
                self.process_symbol(symbol)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during CSV conversion: {e}")
            return False
    
    def process_symbol(self, symbol):
        """Process a single symbol's data to CSV."""
        try:
            logger.info(f"📊 Processing {symbol}...")
            
            # Get input directory for this symbol
            data_dir = self.input_base_dir / symbol
            
            if not data_dir.exists():
                logger.warning(f"⚠️  Directory {data_dir} does not exist, skipping {symbol}")
                return None
            
            # Find data files from the last N days
            cutoff_time = datetime.now() - timedelta(days=self.days_to_process)
            data_files = sorted(glob.glob(str(data_dir / f"{symbol}_ultra_fast_*.json.gz")))
            
            # Filter files by modification time
            recent_files = []
            for file_path in data_files:
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_mtime >= cutoff_time:
                    recent_files.append(file_path)
            
            if not recent_files:
                logger.warning(f"No data files found from the last {self.days_to_process} days")
                return None
            
            logger.info(f"📁 Processing {len(recent_files)} recent files...")
            
            all_data = []
            processed_files = 0
            
            for file_path in recent_files:
                try:
                    with gzip.open(file_path, 'rt') as f:
                        for line in f:
                            if line.strip():
                                data = json.loads(line.strip())
                                
                                # Only process depth updates
                                if data.get('type') == 'depth':
                                    processed = self.process_binance_order_book(data)
                                    if processed:
                                        all_data.append(processed)
                    
                    processed_files += 1
                    if processed_files % 10 == 0:
                        logger.info(f"   Processed {processed_files}/{len(recent_files)} files...")
                        
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    continue
            
            if not all_data:
                logger.warning("No valid data found in recent files")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(all_data)
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Remove duplicates based on timestamp
            df = df.drop_duplicates(subset=['timestamp'], keep='last')
            
            # Determine output filename based on symbol
            if symbol == "BTCUSDT":
                output_filename = "btc_tickdata.csv"
            elif symbol == "ETHUSDT":
                output_filename = "eth_tickdata.csv"
            elif symbol == "SOLUSDT":
                output_filename = "sol_tickdata.csv"
            else:
                output_filename = f"{symbol.lower()}_tickdata.csv"
            
            # Save CSV file (no subfolders)
            output_file = self.output_dir / output_filename
            df.to_csv(output_file, index=False)
            
            # Log statistics
            start_time = pd.to_datetime(df['timestamp'].min(), unit='ms')
            end_time = pd.to_datetime(df['timestamp'].max(), unit='ms')
            duration = (end_time - start_time).total_seconds() / 3600
            
            logger.info(f"✅ {symbol} complete: {len(df):,} snapshots")
            logger.info(f"📅 Time span: {duration:.1f} hours")
            logger.info(f"💾 Saved to: {output_file.name}")
            
            return len(df)
            
        except Exception as e:
            logger.error(f"❌ Error processing {symbol}: {e}")
            return None
    
    
    def run(self):
        """Run the periodic CSV converter."""
        logger.info("🚀 Starting periodic CSV converter...")
        logger.info(f"⏱️  Will convert data every {self.interval_seconds/60:.0f} minutes")
        logger.info("Press Ctrl+C to stop")
        
        while self.running:
            try:
                # Perform conversion for all symbols
                success = self.convert_to_csv()
                
                if success:
                    logger.info(f"✅ Successfully processed all symbols")
                else:
                    logger.warning("⚠️  Some symbols failed to process")
                
                
                # Wait for next interval
                logger.info(f"💤 Waiting {self.interval_seconds/60:.0f} minutes until next conversion...")
                time.sleep(self.interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                logger.info("Waiting before retry...")
                time.sleep(60)  # Wait 1 minute before retrying
        
        logger.info("✅ CSV converter stopped")

def main():
    """Main function to run the periodic CSV converter."""
    
    print("📊 PERIODIC CSV CONVERTER FOR ULTRA-FAST DATA")
    print("=" * 50)
    print(f"Processing: BTC, ETH, SOL (all symbols)")
    print(f"Configuration:")
    print(f"  Input dir: {INPUT_BASE_DIR}/[BTCUSDT, ETHUSDT, SOLUSDT]")
    print(f"  Output dir: {OUTPUT_DIR}/")
    print(f"  Output files: btc_tickdata.csv, eth_tickdata.csv, sol_tickdata.csv")
    print(f"  Interval: {CONVERSION_INTERVAL_MINUTES} minutes")
    print(f"  Processing: Last {DAYS_TO_PROCESS} days")
    print("=" * 50)
    
    # Create and run converter (processes all symbols)
    converter = PeriodicCSVConverter()
    converter.run()

if __name__ == "__main__":
    main()