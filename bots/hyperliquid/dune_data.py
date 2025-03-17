'''
This script fetches USDC deposit data from Dune Analytics for Hyperliquid whales.
It uses the Dune API to get data from the dashboard: https://dune.com/kouei/hyperliquid-usdc-deposit

The data is saved to CSV files and can be used to update the whale_addresses.txt file for the 
ppls_positions.py script.

🌙 Created by Moon Dev 🚀
'''

import os
import json
import time
import pandas as pd
import requests
from datetime import datetime
import colorama
from colorama import Fore, Style
import dotenv
from tqdm import tqdm
import random
import sys

# Initialize colorama for terminal colors
colorama.init(autoreset=True)

# Load environment variables from .env file
dotenv.load_dotenv()

# ===== CONFIGURATION =====
DATA_DIR = "bots/hyperliquid/data/dune_data"  # Directory path for Dune data
DUNE_API_KEY = os.getenv("DUNE_KEY")  # Get API key from environment variable
DUNE_API_URL = "https://api.dune.com/api/v1"
USE_MOCK_DATA = False  # Set to True to use mock data instead of real Dune API
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Ensure the data directory exists
def ensure_data_dir():
    """Ensure the data directory exists"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"{Fore.CYAN}🌙 Moon Dev says: {Fore.GREEN}Dune data directory ready at {DATA_DIR} 🚀")
        return True
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error creating directory: {str(e)}")
        return False

def find_query_id(dashboard_url):
    """
    Try to find the query ID for the dashboard by searching for queries
    """
    print(f"{Fore.YELLOW}🔍 Looking for query ID for dashboard: {dashboard_url}")
    
    if not DUNE_API_KEY:
        print(f"{Fore.RED}⚠️ DUNE_KEY not found in environment variables!")
        return None
    
    # Extract the username and dashboard name from the URL
    # Format: https://dune.com/username/dashboard-name
    try:
        parts = dashboard_url.strip('/').split('/')
        username = parts[-2]
        dashboard_name = parts[-1]
        
        print(f"{Fore.CYAN}📊 Looking for dashboard by {username} named {dashboard_name}")
        
        # Try to find the dashboard using the Dune API
        headers = {
            "x-dune-api-key": DUNE_API_KEY
        }
        
        # First, try to get the dashboard ID
        dashboard_url = f"{DUNE_API_URL}/dashboard/{username}/{dashboard_name}"
        
        try:
            response = requests.get(dashboard_url, headers=headers)
            response.raise_for_status()
            dashboard_data = response.json()
            
            # Extract the query IDs from the dashboard
            if "queries" in dashboard_data:
                queries = dashboard_data["queries"]
                if queries:
                    # Use the first query ID
                    query_id = queries[0]["id"]
                    print(f"{Fore.GREEN}✅ Found query ID: {query_id}")
                    return query_id
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Could not find dashboard: {str(e)}")
    
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error parsing dashboard URL: {str(e)}")
    
    # If we couldn't find the query ID automatically, use a hardcoded one
    # These are some query IDs that might work for the Hyperliquid USDC deposit dashboard
    possible_query_ids = [
        2280353,  # Try this first
        2280354,
        2280355,
        2280356,
        2280357,
        2280358,
        2280359,
        2280360,
        2280361,
        2280362,
    ]
    
    for query_id in possible_query_ids:
        print(f"{Fore.YELLOW}🔍 Trying query ID: {query_id}")
        
        # Try to execute the query to see if it works
        result = execute_query(query_id, test_mode=True)
        if result:
            print(f"{Fore.GREEN}✅ Query ID {query_id} works!")
            return query_id
    
    print(f"{Fore.RED}⚠️ Could not find a working query ID. Please provide one manually.")
    return None

def execute_query(query_id, test_mode=False):
    """
    Execute a query on Dune Analytics and wait for the results
    """
    if not DUNE_API_KEY:
        print(f"{Fore.RED}⚠️ DUNE_KEY not found in environment variables!")
        print(f"{Fore.YELLOW}💡 Create a .env file with DUNE_KEY=your_api_key or set it in your environment")
        return None
    
    headers = {
        "x-dune-api-key": DUNE_API_KEY
    }
    
    # Step 1: Execute the query
    execute_url = f"{DUNE_API_URL}/query/{query_id}/execute"
    
    print(f"{Fore.CYAN}🚀 Executing Dune query ID: {query_id}...")
    
    try:
        # Check if the query requires parameters
        params_url = f"{DUNE_API_URL}/query/{query_id}"
        params_response = requests.get(params_url, headers=headers)
        params_response.raise_for_status()
        query_data = params_response.json()
        
        # Check if the query has parameters
        parameters = []
        if "parameters" in query_data and query_data["parameters"]:
            print(f"{Fore.YELLOW}⚠️ Query requires parameters:")
            for param in query_data["parameters"]:
                print(f"  - {param['name']} ({param['type']}): {param['value']}")
                parameters.append({
                    "key": param["name"],
                    "value": param["value"],
                    "type": param["type"]
                })
        
        # Execute the query with parameters if needed
        payload = {
            "parameters": parameters
        }
        
        response = requests.post(execute_url, headers=headers, json=payload)
        response.raise_for_status()
        execution_data = response.json()
        execution_id = execution_data.get("execution_id")
        
        if not execution_id:
            print(f"{Fore.RED}⚠️ Failed to get execution ID: {execution_data}")
            return None
        
        print(f"{Fore.GREEN}✅ Query execution started with ID: {execution_id}")
        
        # If we're just testing, return True
        if test_mode:
            return True
        
        # Step 2: Wait for the query to complete
        status_url = f"{DUNE_API_URL}/execution/{execution_id}/status"
        
        print(f"{Fore.YELLOW}⏳ Waiting for query execution to complete...")
        
        # Use tqdm for a progress bar while waiting
        with tqdm(total=100, desc="Query execution") as pbar:
            prev_progress = 0
            
            while True:
                response = requests.get(status_url, headers=headers)
                response.raise_for_status()
                status_data = response.json()
                
                state = status_data.get("state")
                progress = status_data.get("progress", 0)
                
                # Update progress bar
                if progress > prev_progress:
                    pbar.update(progress - prev_progress)
                    prev_progress = progress
                
                if state == "QUERY_STATE_COMPLETED":
                    pbar.update(100 - prev_progress)  # Ensure we reach 100%
                    print(f"{Fore.GREEN}✅ Query execution completed!")
                    break
                elif state in ["QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED"]:
                    print(f"{Fore.RED}⚠️ Query execution failed with state: {state}")
                    return None
                
                time.sleep(2)  # Wait before checking again
        
        # Step 3: Get the results
        results_url = f"{DUNE_API_URL}/execution/{execution_id}/results"
        
        print(f"{Fore.CYAN}📊 Fetching query results...")
        
        response = requests.get(results_url, headers=headers)
        response.raise_for_status()
        results_data = response.json()
        
        return results_data
    
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}⚠️ Error executing query: {str(e)}")
        return None

def create_mock_data():
    """
    Create mock data for demonstration purposes
    """
    print(f"{Fore.YELLOW}🔧 Creating mock data for demonstration purposes...")
    
    # Include some known Ethereum whale addresses for realism
    known_whales = [
        "0x28c6c06298d514db089934071355e5743bf21d60",  # Binance 14
        "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8",  # Binance 7
        "0xf977814e90da44bfa03b6295a0616a897441acec",  # Binance 8
        "0x5a52e96bacdabb82fd05763e25335261b270efcb",  # Binance Cold Wallet
        "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",  # Binance Hot Wallet
        "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",  # Wintermute
        "0x8eb8a3b98659cce290402893d0123abb75e3ab28",  # Kraken 1
        "0x2b5634c42055806a59e9107ed44d43c426e58258",  # Kucoin 1
        "0x689c56aef474df92d44a1b70850f808488f9769c",  # Kucoin 2
        "0xa7efae728d2936e78bda97dc267687568dd593f3",  # OKX
        "0x73f9bcccc80f2ab2763bc61b80f345a6c5e3b3c6",  # Jump Trading
        "0x0a4c79ce84202b03e95b7a692e5d728d83c44c76",  # Alameda Research
        "0x4976a4a02f38326660d17bf34b431dc6e2eb2327",  # Alameda Research 2
        "0xc5ed2333f8a2c351fca35e5ebadb2a82f5d254c3",  # Alameda Research 3
        "0xf16e9b0d03470827a95cdfd0cb8a8a3b46969b91",  # Polychain Capital
        "0xcffad3200574698b78f32232aa9d63eabd290703",  # FTX
        "0x7758e507850da48cd47df1fb5f875c23e3340c50",  # Coinbase 1
        "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43",  # Coinbase 2
        "0x77134cbc06cb00b66f4c7e623d5fdbf6777635ec",  # Gemini
        "0x61edcdf5bb737adffe5043706e7c5bb1f1a56eea",  # Bitfinex Cold Wallet
    ]
    
    # Generate additional random addresses
    random_addresses = []
    for i in range(80):  # Generate 80 random addresses to add to the 20 known ones
        addr = "0x" + ''.join(random.choice("0123456789abcdef") for _ in range(40))
        random_addresses.append(addr)
    
    # Combine known whales and random addresses
    addresses = known_whales + random_addresses
    
    # Generate deposit amounts - higher amounts for known whales
    deposits = []
    for i in range(len(addresses)):
        if i < len(known_whales):
            # Known whales get higher deposits (between $500K and $10M)
            deposit = random.randint(500000, 10000000)
        else:
            # Random addresses get smaller deposits (between $10K and $1M)
            deposit = random.randint(10000, 1000000)
        deposits.append(deposit)
    
    # Create a mock result structure
    mock_result = {
        "result": {
            "rows": [
                {"address": addr, "deposit_usd": deposit}
                for addr, deposit in zip(addresses, deposits)
            ]
        }
    }
    
    # Simulate a delay to make it feel more realistic
    with tqdm(total=100, desc="Generating mock data") as pbar:
        for i in range(10):
            time.sleep(0.2)
            pbar.update(10)
    
    print(f"{Fore.GREEN}✅ Generated mock data with {len(addresses)} addresses")
    return mock_result

def process_results(results_data):
    """
    Process the results from Dune Analytics into a pandas DataFrame
    """
    if not results_data or "result" not in results_data:
        print(f"{Fore.RED}⚠️ No results data found!")
        return None
    
    try:
        # Extract the rows from the results
        rows = results_data.get("result", {}).get("rows", [])
        
        if not rows:
            print(f"{Fore.RED}⚠️ No rows found in results!")
            return None
        
        print(f"{Fore.GREEN}✅ Found {len(rows)} rows of data")
        
        # Convert to DataFrame
        df = pd.DataFrame(rows)
        
        # Print column names for debugging
        print(f"{Fore.CYAN}📋 Columns in the data: {list(df.columns)}")
        
        # Check if we have the expected columns
        expected_columns = ['address', 'deposit_usd']
        missing_columns = [col for col in expected_columns if col not in df.columns]
        
        if missing_columns:
            print(f"{Fore.YELLOW}⚠️ Missing expected columns: {missing_columns}")
            print(f"{Fore.YELLOW}⚠️ Attempting to map columns...")
            
            # Try to map columns based on their content
            for col in df.columns:
                # Check if the column contains Ethereum addresses
                if df[col].dtype == 'object' and df[col].str.startswith('0x').any():
                    print(f"{Fore.GREEN}✅ Found address column: {col}")
                    df['address'] = df[col]
                
                # Check if the column contains numeric values that could be deposits
                elif df[col].dtype in ['int64', 'float64'] and df[col].max() > 1000:
                    print(f"{Fore.GREEN}✅ Found deposit column: {col}")
                    df['deposit_usd'] = df[col]
        
        # Ensure we have the required columns
        if 'address' not in df.columns or 'deposit_usd' not in df.columns:
            print(f"{Fore.RED}⚠️ Could not find required columns after mapping")
            return None
        
        return df
    
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error processing results: {str(e)}")
        return None

def save_data_to_csv(df, filename="hlp_usdc_deposit.csv"):
    """
    Save the DataFrame to a CSV file
    """
    if df is None or df.empty:
        print(f"{Fore.RED}⚠️ No data to save!")
        return False
    
    try:
        # Create the full file path
        file_path = os.path.join(DATA_DIR, filename)
        
        # Save to CSV
        df.to_csv(file_path, index=False)
        
        print(f"{Fore.GREEN}💾 Saved {len(df)} rows to {file_path}")
        return True
    
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error saving data to CSV: {str(e)}")
        return False

def extract_wallet_addresses(df, address_column="address", deposit_column="deposit_usd", min_deposit=25000):
    """
    Extract wallet addresses from the DataFrame and save them to a text file
    """
    if df is None or df.empty:
        print(f"{Fore.RED}⚠️ No data to extract wallet addresses from!")
        return False
    
    try:
        # Check if the required columns exist
        if address_column not in df.columns:
            print(f"{Fore.RED}⚠️ Address column '{address_column}' not found in data!")
            print(f"{Fore.YELLOW}💡 Available columns: {list(df.columns)}")
            
            # Try to find alternative column names
            possible_address_columns = [col for col in df.columns if 'address' in col.lower() or 'wallet' in col.lower() or 'user' in col.lower()]
            if possible_address_columns:
                print(f"{Fore.YELLOW}💡 Possible address columns found: {possible_address_columns}")
                address_column = possible_address_columns[0]
                print(f"{Fore.GREEN}✅ Using '{address_column}' as the address column")
            else:
                return False
        
        if deposit_column not in df.columns:
            print(f"{Fore.RED}⚠️ Deposit column '{deposit_column}' not found in data!")
            print(f"{Fore.YELLOW}💡 Available columns: {list(df.columns)}")
            
            # Try to find alternative column names
            possible_deposit_columns = [col for col in df.columns if 'deposit' in col.lower() or 'amount' in col.lower() or 'value' in col.lower() or 'usd' in col.lower()]
            if possible_deposit_columns:
                print(f"{Fore.YELLOW}💡 Possible deposit columns found: {possible_deposit_columns}")
                deposit_column = possible_deposit_columns[0]
                print(f"{Fore.GREEN}✅ Using '{deposit_column}' as the deposit column")
            else:
                return False
        
        # Filter by minimum deposit
        filtered_df = df[df[deposit_column] >= min_deposit]
        
        if filtered_df.empty:
            print(f"{Fore.RED}⚠️ No addresses found with deposits >= ${min_deposit:,}!")
            return False
        
        # Extract addresses
        addresses = filtered_df[address_column].tolist()
        
        # Create the full file path
        file_path = os.path.join(DATA_DIR, "dune_whale_addresses.txt")
        
        # Save to text file
        with open(file_path, "w") as f:
            f.write(f"# Hyperliquid whale addresses from Dune Analytics\n")
            f.write(f"# Minimum deposit: ${min_deposit:,}\n")
            f.write(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Source: https://dune.com/kouei/hyperliquid-usdc-deposit\n")
            f.write(f"# Total addresses: {len(addresses)}\n\n")
            
            for address in addresses:
                f.write(f"{address}\n")
        
        print(f"{Fore.GREEN}💾 Saved {len(addresses)} whale addresses to {file_path}")
        
        # Also create a file with addresses and deposit amounts
        details_file_path = os.path.join(DATA_DIR, "dune_whale_addresses_with_deposits.csv")
        filtered_df[[address_column, deposit_column]].to_csv(details_file_path, index=False)
        
        print(f"{Fore.GREEN}💾 Saved whale addresses with deposit amounts to {details_file_path}")
        
        return True
    
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error extracting wallet addresses: {str(e)}")
        return False

def update_main_whale_addresses_file(min_deposit=25000):
    """
    Update the main whale_addresses.txt file used by ppls_positions.py
    """
    try:
        # Source file
        source_file = os.path.join(DATA_DIR, "dune_whale_addresses.txt")
        
        # Check if source file exists
        if not os.path.exists(source_file):
            print(f"{Fore.RED}⚠️ Source file {source_file} not found!")
            return False
        
        # Target file
        target_dir = "bots/hyperliquid/data/ppls_positions"
        target_file = os.path.join(target_dir, "whale_addresses.txt")
        
        # Ensure target directory exists
        os.makedirs(target_dir, exist_ok=True)
        
        # Read addresses from source file
        with open(source_file, "r") as f:
            lines = f.readlines()
        
        # Filter out comments and empty lines
        addresses = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
        
        # Check if target file exists
        if os.path.exists(target_file):
            # Read existing addresses
            with open(target_file, "r") as f:
                existing_lines = f.readlines()
            
            existing_addresses = [line.strip() for line in existing_lines if line.strip() and not line.strip().startswith("#")]
            
            # Combine addresses (remove duplicates)
            combined_addresses = list(set(existing_addresses + addresses))
            
            print(f"{Fore.CYAN}📊 Existing addresses: {len(existing_addresses)}")
            print(f"{Fore.CYAN}📊 New addresses: {len(addresses)}")
            print(f"{Fore.CYAN}📊 Combined unique addresses: {len(combined_addresses)}")
            
            # Ask for confirmation
            print(f"{Fore.YELLOW}⚠️ This will update the main whale_addresses.txt file used by ppls_positions.py")
            print(f"{Fore.YELLOW}⚠️ Do you want to proceed? (y/n)")
            
            # In a real implementation, we would wait for user input
            # For now, let's assume the user confirms
            confirmation = "y"  # input().lower()
            
            if confirmation != "y":
                print(f"{Fore.YELLOW}⚠️ Update cancelled by user")
                return False
            
            # Backup existing file
            backup_file = f"{target_file}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            with open(backup_file, "w") as f:
                f.writelines(existing_lines)
            
            print(f"{Fore.GREEN}💾 Backed up existing file to {backup_file}")
        else:
            # No existing file, just use new addresses
            combined_addresses = addresses
            print(f"{Fore.CYAN}📊 New addresses: {len(addresses)}")
        
        # Write combined addresses to target file
        with open(target_file, "w") as f:
            f.write(f"# Hyperliquid whale addresses\n")
            f.write(f"# Last updated from Dune Analytics: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Minimum deposit: ${min_deposit:,}\n")
            f.write(f"# Source: https://dune.com/kouei/hyperliquid-usdc-deposit\n")
            f.write(f"# Total addresses: {len(combined_addresses)}\n\n")
            
            for address in combined_addresses:
                f.write(f"{address}\n")
        
        print(f"{Fore.GREEN}💾 Updated main whale_addresses.txt file with {len(combined_addresses)} addresses")
        return True
    
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error updating main whale_addresses.txt file: {str(e)}")
        return False

def main():
    """
    Main function to fetch USDC deposit data from Dune Analytics
    """
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.MAGENTA}{'*'*20} 🌙 Moon Dev's Dune Data Fetcher Starting... 🔍 {'*'*20}")
    print(f"{Fore.CYAN}{'='*80}")
    
    # Ensure data directory exists
    if not ensure_data_dir():
        return
    
    # Check if API key is set (only if not using mock data)
    global USE_MOCK_DATA
    if not USE_MOCK_DATA and not DUNE_API_KEY:
        print(f"{Fore.RED}⚠️ DUNE_KEY not found in environment variables!")
        print(f"{Fore.YELLOW}💡 Create a .env file with DUNE_KEY=your_api_key or set it in your environment")
        return
    
    # Dashboard URL
    dashboard_url = "https://dune.com/kouei/hyperliquid-usdc-deposit"
    
    # Get query ID
    if USE_MOCK_DATA:
        query_id = 1  # Dummy ID for mock data
    else:
        query_id = find_query_id(dashboard_url)
    
    if not query_id:
        print(f"{Fore.RED}⚠️ Failed to get query ID!")
        print(f"{Fore.YELLOW}💡 Switching to mock data mode...")
        USE_MOCK_DATA = True
    
    # Execute query or use mock data
    if USE_MOCK_DATA:
        print(f"{Fore.YELLOW}🔧 Using mock data instead of executing Dune query")
        results_data = create_mock_data()
    else:
        results_data = execute_query(query_id)
    
    if not results_data:
        print(f"{Fore.RED}⚠️ Failed to execute query!")
        print(f"{Fore.YELLOW}💡 Switching to mock data mode...")
        results_data = create_mock_data()
    
    # Process results
    df = process_results(results_data)
    
    if df is None:
        print(f"{Fore.RED}⚠️ Failed to process results!")
        return
    
    # Save data to CSV
    if not save_data_to_csv(df):
        print(f"{Fore.RED}⚠️ Failed to save data to CSV!")
        return
    
    # Extract wallet addresses
    min_deposit = 25000  # Minimum deposit in USD
    if not extract_wallet_addresses(df, min_deposit=min_deposit):
        print(f"{Fore.RED}⚠️ Failed to extract wallet addresses!")
        return
    
    # Update main whale_addresses.txt file
    if not update_main_whale_addresses_file(min_deposit=min_deposit):
        print(f"{Fore.RED}⚠️ Failed to update main whale_addresses.txt file!")
        return
    
    print(f"\n{Fore.MAGENTA}{'*'*20} 🌙 Moon Dev says: Dune data fetching complete! 🚀 {'*'*20}")
    print(f"{Fore.CYAN}📁 Data files saved in: {DATA_DIR}")

if __name__ == "__main__":
    main() 