#!/usr/bin/env python3
"""
🌙 MOON DEV'S LIQUIDATION DATA PREPROCESSING PIPELINE 🌙
=====================================================

This script preprocesses liquidation data to:
- Filter for specific symbols (BTC, ETH, etc.)
- Clean and standardize the data
- Output to organized subfolders
- Prepare data for machine learning models

Author: Moon Dev 🚀
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 🌙 MOON DEV'S CONFIGURATION 🌙
SYMBOLS_TO_KEEP = ['BTC']  # Add 'ETH' later when ready! 🚀
INPUT_DATA_PATH = 'data/moondev_api/liq_data.csv'
OUTPUT_BASE_DIR = 'research/machine_learning/processed_data'
CHUNK_SIZE = 100000  # Process in chunks for large files

class MoonDevLiquidationPreprocessor:
    """
    🌙 Moon Dev's Liquidation Data Preprocessor
    
    Filters and processes liquidation data for trading model training!
    """
    
    def __init__(self, symbols_to_keep=None, output_dir=None):
        """
        🚀 Initialize Moon Dev's preprocessing pipeline!
        """
        self.symbols_to_keep = symbols_to_keep or SYMBOLS_TO_KEEP
        self.output_dir = output_dir or OUTPUT_BASE_DIR
        self.input_path = INPUT_DATA_PATH
        
        print("🌙 MOON DEV'S LIQUIDATION PREPROCESSOR INITIALIZED! 🚀")
        print(f"   🎯 Symbols to keep: {self.symbols_to_keep}")
        print(f"   📁 Output directory: {self.output_dir}")
        print(f"   📊 Input data: {self.input_path}")
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"   ✅ Output directory ready!")
    
    def load_and_analyze_raw_data(self):
        """
        🔍 Load raw liquidation data and analyze what we're working with!
        """
        print("\n🔍 MOON DEV ANALYZING RAW LIQUIDATION DATA... 🌙")
        
        try:
            # Try to get basic info without loading full dataset
            total_rows = sum(1 for _ in open(self.input_path)) - 1  # Subtract header
            print(f"   📊 Total rows in dataset: {total_rows:,}")
            
            # Load a sample to analyze structure
            sample_df = pd.read_csv(self.input_path, nrows=10000)
            print(f"   📋 Columns: {list(sample_df.columns)}")
            print(f"   📅 Date range (sample): {sample_df['datetime'].min()} to {sample_df['datetime'].max()}")
            
            # Analyze symbols in sample
            if 'symbol' in sample_df.columns:
                symbol_counts = sample_df['symbol'].value_counts()
                print(f"   🪙 Top symbols in sample:")
                for symbol, count in symbol_counts.head(10).items():
                    emoji = "🚀" if symbol in self.symbols_to_keep else "📊"
                    print(f"     {emoji} {symbol}: {count:,} liquidations")
                
                # Check if our target symbols exist
                for symbol in self.symbols_to_keep:
                    if symbol in symbol_counts.index:
                        print(f"   ✅ Target symbol {symbol} found in data!")
                    else:
                        print(f"   ⚠️ Target symbol {symbol} NOT found in sample!")
            
            return sample_df
            
        except Exception as e:
            print(f"   ❌ Error analyzing raw data: {e}")
            return None
    
    def filter_liquidation_data(self):
        """
        🎯 Filter liquidation data to keep only Moon Dev's target symbols!
        """
        print(f"\n🎯 MOON DEV FILTERING FOR SYMBOLS: {self.symbols_to_keep} 🌙")
        
        filtered_data = []
        total_rows_processed = 0
        total_rows_kept = 0
        
        try:
            # Process data in chunks to handle large files
            chunk_iter = pd.read_csv(self.input_path, chunksize=CHUNK_SIZE)
            
            for chunk_num, chunk in enumerate(chunk_iter, 1):
                print(f"   🔄 Processing chunk {chunk_num} ({len(chunk):,} rows)...")
                
                # Filter for target symbols
                if 'symbol' in chunk.columns:
                    filtered_chunk = chunk[chunk['symbol'].isin(self.symbols_to_keep)]
                    
                    if len(filtered_chunk) > 0:
                        filtered_data.append(filtered_chunk)
                        total_rows_kept += len(filtered_chunk)
                        print(f"     ✅ Kept {len(filtered_chunk):,} rows from chunk {chunk_num}")
                    else:
                        print(f"     ⚪ No target symbols in chunk {chunk_num}")
                else:
                    print(f"     ❌ No 'symbol' column found in chunk {chunk_num}")
                
                total_rows_processed += len(chunk)
                
                # Progress update every 10 chunks
                if chunk_num % 10 == 0:
                    print(f"   📊 Progress: {total_rows_processed:,} rows processed, {total_rows_kept:,} kept")
            
            if filtered_data:
                # Combine all filtered chunks
                print("\n🔗 MOON DEV COMBINING FILTERED DATA... 🌙")
                final_df = pd.concat(filtered_data, ignore_index=True)
                
                print(f"   🎉 FILTERING COMPLETE!")
                print(f"   📊 Original rows: {total_rows_processed:,}")
                print(f"   🎯 Filtered rows: {len(final_df):,}")
                print(f"   📈 Keep ratio: {len(final_df)/total_rows_processed*100:.2f}%")
                
                return final_df
            else:
                print(f"   ❌ No data found for symbols: {self.symbols_to_keep}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error filtering data: {e}")
            return None
    
    def clean_and_standardize_data(self, df):
        """
        🧹 Clean and standardize Moon Dev's filtered liquidation data!
        """
        print(f"\n🧹 MOON DEV CLEANING AND STANDARDIZING DATA... 🌙")
        
        original_rows = len(df)
        print(f"   📊 Starting with {original_rows:,} rows")
        
        # Convert datetime column
        if 'datetime' in df.columns:
            print("   📅 Converting datetime column...")
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.sort_values('datetime').reset_index(drop=True)
            print(f"   ✅ Datetime converted and sorted")
        
        # Clean numeric columns
        numeric_columns = ['original_quantity', 'price', 'average_price', 
                          'order_last_filled_quantity', 'order_filled_accumulated_quantity', 
                          'usd_size']
        
        for col in numeric_columns:
            if col in df.columns:
                print(f"   🔢 Cleaning numeric column: {col}")
                # Remove any non-numeric values
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Check for nulls
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    print(f"     ⚠️ Found {null_count} null values in {col}")
                    df = df.dropna(subset=[col])
                    print(f"     🧹 Dropped null values, now {len(df):,} rows")
        
        # Remove zero or negative USD sizes (invalid liquidations)
        if 'usd_size' in df.columns:
            print("   💰 Filtering for valid USD liquidation sizes...")
            valid_mask = df['usd_size'] > 0
            df = df[valid_mask].reset_index(drop=True)
            print(f"   ✅ Kept {len(df):,} rows with valid USD sizes")
        
        # Add symbol-specific features if needed
        print("   🏷️ Adding symbol standardization...")
        if 'symbol' in df.columns:
            # Ensure symbols are uppercase and clean
            df['symbol'] = df['symbol'].str.upper().str.strip()
            
            # Add symbol-specific features
            df['is_btc'] = (df['symbol'] == 'BTC').astype(int)
            if 'ETH' in self.symbols_to_keep:
                df['is_eth'] = (df['symbol'] == 'ETH').astype(int)
        
        # Final data quality check
        print("   🔍 Final data quality check...")
        final_rows = len(df)
        rows_removed = original_rows - final_rows
        
        print(f"   📊 Data cleaning summary:")
        print(f"     🏁 Final rows: {final_rows:,}")
        print(f"     🗑️ Rows removed: {rows_removed:,}")
        print(f"     📈 Data retention: {final_rows/original_rows*100:.2f}%")
        
        return df
    
    def save_processed_data(self, df):
        """
        💾 Save Moon Dev's processed liquidation data!
        """
        print(f"\n💾 MOON DEV SAVING PROCESSED DATA... 🌙")
        
        # Create symbol-specific filename
        symbols_str = '_'.join(self.symbols_to_keep)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save main processed file
        main_filename = f"liquidations_{symbols_str}_processed.csv"
        main_filepath = os.path.join(self.output_dir, main_filename)
        
        print(f"   💾 Saving main file: {main_filename}")
        df.to_csv(main_filepath, index=False)
        print(f"   ✅ Main file saved: {main_filepath}")
        
        # Save metadata file
        metadata = {
            'processing_timestamp': timestamp,
            'symbols_filtered': self.symbols_to_keep,
            'total_rows': len(df),
            'date_range_start': str(df['datetime'].min()) if 'datetime' in df.columns else 'N/A',
            'date_range_end': str(df['datetime'].max()) if 'datetime' in df.columns else 'N/A',
            'total_usd_volume': float(df['usd_size'].sum()) if 'usd_size' in df.columns else 0,
            'avg_liquidation_size': float(df['usd_size'].mean()) if 'usd_size' in df.columns else 0,
            'columns': list(df.columns)
        }
        
        metadata_filename = f"liquidations_{symbols_str}_metadata.txt"
        metadata_filepath = os.path.join(self.output_dir, metadata_filename)
        
        print(f"   📋 Saving metadata: {metadata_filename}")
        with open(metadata_filepath, 'w') as f:
            f.write("🌙 MOON DEV'S LIQUIDATION DATA METADATA 🌙\n")
            f.write("=" * 50 + "\n\n")
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")
        
        print(f"   ✅ Metadata saved: {metadata_filepath}")
        
        # Print final summary
        print(f"\n🎉 MOON DEV'S PREPROCESSING COMPLETE! 🚀")
        print(f"   📁 Output directory: {self.output_dir}")
        print(f"   📊 Main file: {main_filename} ({len(df):,} rows)")
        print(f"   📋 Metadata: {metadata_filename}")
        
        if 'usd_size' in df.columns:
            total_volume = df['usd_size'].sum()
            avg_size = df['usd_size'].mean()
            print(f"   💰 Total volume: ${total_volume:,.2f}")
            print(f"   📊 Average liquidation: ${avg_size:.2f}")
        
        return main_filepath, metadata_filepath
    
    def run_full_preprocessing(self):
        """
        🚀 Run Moon Dev's complete preprocessing pipeline!
        """
        print("🌙" * 50)
        print("🚀 MOON DEV'S LIQUIDATION PREPROCESSING PIPELINE 🚀")
        print("🌙" * 50)
        
        # Step 1: Analyze raw data
        sample_df = self.load_and_analyze_raw_data()
        if sample_df is None:
            print("❌ Failed to analyze raw data. Exiting...")
            return None
        
        # Step 2: Filter data
        filtered_df = self.filter_liquidation_data()
        if filtered_df is None or len(filtered_df) == 0:
            print("❌ No data found after filtering. Exiting...")
            return None
        
        # Step 3: Clean and standardize
        clean_df = self.clean_and_standardize_data(filtered_df)
        if clean_df is None or len(clean_df) == 0:
            print("❌ No data left after cleaning. Exiting...")
            return None
        
        # Step 4: Save processed data
        file_paths = self.save_processed_data(clean_df)
        
        print("\n🎉 MOON DEV'S PREPROCESSING MISSION ACCOMPLISHED! 🌙")
        return file_paths


def main():
    """
    🌙 Main execution function for Moon Dev's preprocessing!
    """
    print("🚀 STARTING MOON DEV'S LIQUIDATION PREPROCESSING... 🌙")
    
    # Initialize preprocessor
    preprocessor = MoonDevLiquidationPreprocessor(
        symbols_to_keep=SYMBOLS_TO_KEEP,
        output_dir=OUTPUT_BASE_DIR
    )
    
    # Run full preprocessing pipeline
    result = preprocessor.run_full_preprocessing()
    
    if result:
        print(f"\n✅ PREPROCESSING COMPLETE! Files saved:")
        print(f"   📊 Data: {result[0]}")
        print(f"   📋 Metadata: {result[1]}")
    else:
        print(f"\n❌ PREPROCESSING FAILED!")
    
    return result


if __name__ == "__main__":
    main() 