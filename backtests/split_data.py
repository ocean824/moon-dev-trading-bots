import pandas as pd
import os
from pathlib import Path

def split_data(file_path: str, in_sample_percentage: float):
    """
    Split data into in-sample and out-of-sample sets and save them as separate files.
    
    Args:
        file_path (str): Path to the input CSV file
        in_sample_percentage (float): Percentage of data to use as in-sample (0-100)
    """
    print(f"🌙 Moon Dev Data Splitter Initializing... 🌙")
    
    # Read the data
    df = pd.read_csv(file_path)
    print(f"📊 Moon Dev loaded {len(df)} rows of data")
    
    # Calculate split index
    split_index = int(len(df) * (in_sample_percentage / 100))
    
    # Split the data
    in_sample = df.iloc[:split_index]
    out_sample = df.iloc[split_index:]
    
    print(f"🎯 Moon Dev Split Stats:")
    print(f"    In-Sample Size: {len(in_sample)} rows ({in_sample_percentage}%)")
    print(f"    Out-of-Sample Size: {len(out_sample)} rows ({100-in_sample_percentage}%)")
    
    # Generate new file names
    file_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    name_without_ext = os.path.splitext(file_name)[0]
    
    is_file = os.path.join(file_dir, f"IS_{name_without_ext}.csv")
    os_file = os.path.join(file_dir, f"OS_{name_without_ext}.csv")
    
    # Save the split datasets
    in_sample.to_csv(is_file, index=False)
    out_sample.to_csv(os_file, index=False)
    
    print(f"💾 Moon Dev saved the split files:")
    print(f"    In-Sample: {is_file}")
    print(f"    Out-of-Sample: {os_file}")
    print("🌙 Moon Dev Data Split Complete! 🌙")

if __name__ == "__main__":
    file_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1d-1000wks-data.csv"
    in_sample_percentage = 70  # Can be modified as needed
    
    split_data(file_path, in_sample_percentage)
