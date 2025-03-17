'''
This script tracks positions for Hyperliquid's market maker addresses.
It fetches position data for each address and displays it in separate sections.

Market Maker Addresses:
- HLP: 0xdfc24b077bc1425ad1dea75bcb6f8158e10df303 (Parent vault)
- HLP_LONG: 0x010461c14e146ac35fe42271bdc1134ee31c703a (Long-biased, ~69% long)
- HEDGE2: 0x2e3d94f0562703b25c83308a05046ddaf9a8dd14
- HLP_SHORT: 0x31ca8395cf837de08b24da3f660e77761dfb974b (Short-biased, ~65% short)

🌙 Created by Moon Dev 🚀
'''

import os
import json
import time
import pandas as pd
import requests
from datetime import datetime
import numpy as np
import colorama
from colorama import Fore, Back, Style
import nice_funcs as n
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

# Initialize colorama for terminal colors
colorama.init(autoreset=True)

# Configure pandas to display numbers with commas and no scientific notation
pd.set_option('display.float_format', '{:.2f}'.format)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# ===== CONFIGURATION =====
API_URL = "https://api.hyperliquid.xyz/info"
DATA_DIR = "bots/hyperliquid/data/hl_positions"  # Directory path for market maker data
HEADERS = {"Content-Type": "application/json"}
DUMP_RAW_DATA = True  # Set to True to dump raw API response data (one-time operation)
HYPERLIQUID_VAULT_URL = "https://app.hyperliquid.xyz/vaults/{}"  # URL template for vault page
MAX_POSITIONS_TO_DISPLAY = 100  # Maximum number of positions to display for each direction (long/short)

# Market maker addresses with labels
MARKET_MAKERS = {
    "HLP": "0xdfc24b077bc1425ad1dea75bcb6f8158e10df303",  # Original HLP address
    "HLP_LONG": "0x010461c14e146ac35fe42271bdc1134ee31c703a",  # Previously HEDGE1 (long-biased)
    "HEDGE2": "0x2e3d94f0562703b25c83308a05046ddaf9a8dd14",
    "HLP_SHORT": "0x31ca8395cf837de08b24da3f660e77761dfb974b"  # Previously HEDGE3 (short-biased)
}

def ensure_data_dir():
    """Ensure the data directory exists"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"{Fore.CYAN}🌙 Moon Dev says: {Fore.GREEN}Data directory ready at {DATA_DIR} 🚀")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error creating directory: {str(e)}")
        return False
    return True

def dump_raw_api_data(data, label, address):
    """Dump raw API response data to a JSON file for analysis"""
    if not data:
        return
    
    try:
        # Create a filename with the label and address
        filename = os.path.join(DATA_DIR, f"raw_data_{label}_{address[:8]}.json")
        
        # Write the data to a JSON file with pretty formatting
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        
        print(f"{Fore.MAGENTA}💾 Dumped raw API data for {label} to {filename}")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error dumping raw data for {label}: {str(e)}")

def extract_table_data_from_html(html_content, nickname, address):
    """
    Extract table data from HTML content using BeautifulSoup
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        tables = soup.find_all('table')
        
        if not tables:
            print(f"{Fore.RED}⚠️ No tables found in HTML for {nickname}")
            return None
        
        # Process each table
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            if not rows:
                continue
                
            # Extract headers
            headers = []
            header_row = rows[0]
            for th in header_row.find_all('th'):
                headers.append(th.text.strip())
            
            # Extract data rows
            table_data = []
            for row in rows[1:]:  # Skip header row
                row_data = {}
                cells = row.find_all('td')
                for j, cell in enumerate(cells):
                    if j < len(headers):
                        row_data[headers[j]] = cell.text.strip()
                    else:
                        row_data[f"column_{j}"] = cell.text.strip()
                table_data.append(row_data)
            
            # Save table data to JSON
            table_file = os.path.join(DATA_DIR, f"table_{i}_{nickname}_{address[:8]}.json")
            with open(table_file, 'w', encoding='utf-8') as f:
                json.dump(table_data, f, indent=4)
            
            print(f"{Fore.MAGENTA}💾 Saved table {i} data to {table_file} ({len(table_data)} rows)")
        
        return True
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error extracting table data: {str(e)}")
        return None

def scrape_positions_from_website(address, nickname):
    """Scrape positions from the Hyperliquid website for a given address."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    try:
        # Use webdriver-manager to handle driver installation
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        url = f"https://app.hyperliquid.xyz/vaults/{address}"
        print(f"🌙 Moon Dev says: Navigating to {url} 🚀")
        driver.get(url)
        
        # Wait for the page to load
        print(f"🌙 Moon Dev says: Waiting for positions to load... ⏳")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        
        # Save the raw HTML for analysis
        html_content = driver.page_source
        html_file = os.path.join(DATA_DIR, f"raw_html_{nickname}_{address[:8]}.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"{Fore.MAGENTA}💾 Saved raw HTML to {html_file} for analysis")
        
        # Extract table data from the HTML
        extract_table_data_from_html(html_content, nickname, address)
        
        # Try to click on the Positions tab if it exists
        try:
            positions_tab = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Positions')]"))
            )
            positions_tab.click()
            time.sleep(2)  # Wait for positions to load after clicking
            
            # Save the updated HTML after clicking the Positions tab
            html_after_click = driver.page_source
            html_after_file = os.path.join(DATA_DIR, f"raw_html_after_click_{nickname}_{address[:8]}.html")
            with open(html_after_file, 'w', encoding='utf-8') as f:
                f.write(html_after_click)
            print(f"{Fore.MAGENTA}💾 Saved HTML after clicking Positions tab to {html_after_file}")
            
            # Extract table data from the HTML after clicking
            extract_table_data_from_html(html_after_click, f"{nickname}_after_click", address)
        except Exception as e:
            print(f"⚠️ Could not click Positions tab")
        
        # Find the table with positions
        table = driver.find_element(By.TAG_NAME, "table")
        rows = table.find_elements(By.TAG_NAME, "tr")
        
        print(f"✅ Found {len(rows) - 1} positions in the table")  # -1 for header row
        
        positions = []
        error_count = 0
        
        # Skip the header row
        for row in rows[1:]:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 5:  # Ensure we have enough cells
                    # Column 0: Coin name (e.g., "BTC  20x")
                    symbol = cells[0].text.strip()
                    
                    # Column 1: Size (e.g., "5.19059 BTC")
                    size_text = cells[1].text.strip()
                    size_parts = size_text.split()
                    if len(size_parts) > 1:
                        # Remove commas and convert to float
                        size = float(size_parts[0].replace(',', ''))  # Take just the number part
                    else:
                        # Remove commas and convert to float
                        size = float(size_text.replace(',', ''))
                    
                    # Column 2: Position Value (e.g., "$396,319.41")
                    position_value = float(cells[2].text.strip().replace('$', '').replace(',', ''))
                    
                    # Column 3: Entry Price (e.g., "1,900.0")
                    entry_price = float(cells[3].text.strip().replace('$', '').replace(',', ''))
                    
                    # Column 4: Mark Price (e.g., "1,889.7")
                    mark_price = float(cells[4].text.strip().replace('$', '').replace(',', ''))
                    
                    # Column 5: PnL (e.g., "+$1,617.91 (+7.5%)")
                    pnl_text = cells[5].text.strip()
                    pnl_parts = pnl_text.split()
                    if len(pnl_parts) > 0:
                        pnl_value = pnl_parts[0].replace('$', '').replace(',', '')
                        if pnl_value.startswith('+'):
                            pnl = float(pnl_value[1:])  # Remove the + sign
                        elif pnl_value.startswith('-'):
                            pnl = -float(pnl_value[1:])  # Keep the - sign but convert to float
                        else:
                            pnl = float(pnl_value)
                    else:
                        pnl = 0.0
                    
                    # Create position object similar to API response format
                    position = {
                        "coin": symbol,
                        "szi": size,
                        "entryPx": position_value,  # This is actually the position value
                        "markPx": entry_price,      # This is actually the entry price
                        "pnl": mark_price,          # This is actually the mark price
                        "unrealizedPnl": pnl        # This is the PnL
                    }
                    positions.append(position)
            except Exception as e:
                error_count += 1
                if error_count <= 3:  # Only show first few errors to reduce noise
                    print(f"⚠️ Error processing row (showing first few errors only)")
                continue
        
        if error_count > 3:
            print(f"⚠️ {error_count} total errors occurred while processing rows")
            
        # Format the data to match the clearinghouse API response
        formatted_data = {
            "assetPositions": positions,
            "marginSummary": {
                "accountValue": 0,  # We don't have this from scraping
                "totalNtlPos": 0,   # We don't have this from scraping
                "totalRawUsd": 0    # We don't have this from scraping
            }
        }
        
        return formatted_data
    except Exception as e:
        print(f"⚠️ Error scraping positions: {str(e)[:100]}...")  # Truncate long error messages
        return None
    finally:
        if 'driver' in locals():
            driver.quit()

def get_vault_details(vault_address):
    """
    Get details about a vault including its relationship with other addresses
    """
    try:
        print(f"{Fore.YELLOW}🔍 Fetching vault details for {vault_address[:6]}...{vault_address[-4:]}")
        
        # Use the vaultDetails endpoint
        payload = {
            "type": "vaultDetails",
            "vaultAddress": vault_address
        }
        
        print(f"{Fore.CYAN}🌙 Moon Dev says: {Fore.YELLOW}Trying vaultDetails API at {API_URL} with payload: {json.dumps(payload)} 🚀")
        
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        
        data = response.json()
        
        # Dump raw data for analysis
        if DUMP_RAW_DATA:
            dump_raw_api_data(data, f"vault_details", vault_address)
        
        print(f"{Fore.GREEN}✅ Got vault details for {vault_address[:6]}...{vault_address[-4:]}")
        
        # Check if the vault has a relationship with other addresses
        if "relationship" in data and data["relationship"]:
            rel_type = data["relationship"].get("type")
            rel_data = data["relationship"].get("data")
            
            print(f"{Fore.CYAN}📊 Vault relationship type: {rel_type}")
            
            if rel_type == "parent" and "childAddresses" in rel_data:
                child_addresses = rel_data["childAddresses"]
                print(f"{Fore.GREEN}✅ Found {len(child_addresses)} child addresses for this vault:")
                for i, addr in enumerate(child_addresses, 1):
                    print(f"{Fore.CYAN}  {i}. {addr}")
                
                return data
        
        return data
    except Exception as e:
        print(f"{Fore.RED}❌ Error fetching vault details: {str(e)}")
        return None

def get_positions_for_address(label, address):
    """Get positions for a specific address using the appropriate API."""
    # Special case for HLP vault - use web scraping
    if label == "HLP":
        print(f"{Fore.YELLOW}⚠️ Using web scraping for HLP vault")
        scraped_data = scrape_positions_from_website(address, label)
        
        # Dump raw data for analysis
        if DUMP_RAW_DATA and scraped_data:
            dump_raw_api_data(scraped_data, f"{label}_scraped", address)
            
        return scraped_data
    
    # For other addresses, use the clearinghouse API
    print(f"{Fore.CYAN}🌙 Moon Dev says: {Fore.YELLOW}Trying clearinghouse API at {API_URL} with payload: {json.dumps({'type': 'clearinghouseState', 'user': address})} 🚀")
    
    try:
        response = requests.post(
            API_URL,
            json={"type": "clearinghouseState", "user": address},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Clearinghouse response status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Clearinghouse response keys: {list(data.keys())}")
            
            if "assetPositions" in data:
                position_count = len(data["assetPositions"])
                print(f"{Fore.GREEN}✅ Found {position_count} positions in clearinghouse response")
                
                # Dump raw API data for analysis
                if DUMP_RAW_DATA:
                    dump_raw_api_data(data, label, address)
                
                return data
            else:
                print(f"{Fore.RED}⚠️ No 'assetPositions' key in clearinghouse response")
                return None
        else:
            print(f"{Fore.RED}⚠️ Failed to get clearinghouse data: {response.status_code}")
            return None
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error getting clearinghouse data: {str(e)}")
        return None

def process_positions(data, label, address):
    """Process positions data from API response and return structured positions."""
    if not data or "assetPositions" not in data:
        print(f"{Fore.RED}⚠️ No positions found for {label}")
        return []
    
    positions = []
    
    # Check if this is scraped data or API data
    is_scraped_data = all(isinstance(pos, dict) and "coin" in pos for pos in data["assetPositions"])
    
    # Get the total notional position value from marginSummary if available
    total_ntl_pos = 0
    if "marginSummary" in data and "totalNtlPos" in data["marginSummary"]:
        total_ntl_pos = float(data["marginSummary"]["totalNtlPos"])
        print(f"{Fore.CYAN}🌙 Moon Dev says: Total notional position value from API: ${total_ntl_pos:,.2f} 🚀")
    
    # Print a single message instead of one per position
    print(f"{Fore.YELLOW}⏳ Processing {len(data['assetPositions'])} positions for {label}...")
    
    if is_scraped_data:
        # Handle scraped data format
        for position in data["assetPositions"]:
            try:
                coin = position["coin"]
                size = position["szi"]
                
                # For HLP vault, the entry_price in the scraped data is actually the position value
                # The actual entry price is in markPx and the mark price is in the pnl field
                if label == "HLP":
                    position_value = float(position["entryPx"])
                    entry_price = float(position["markPx"])
                    mark_price = float(position["pnl"])
                    
                    # Parse PnL from string format like "$123.45" or "($123.45)"
                    pnl_str = position.get("unrealizedPnl", "0")
                    if isinstance(pnl_str, str):
                        if '(' in pnl_str and ')' in pnl_str:
                            # Negative PnL is in parentheses
                            pnl = -float(pnl_str.replace('(', '').replace(')', '').replace('$', '').replace(',', ''))
                        else:
                            pnl = float(pnl_str.replace('$', '').replace(',', ''))
                    else:
                        pnl = float(pnl_str)
                else:
                    entry_price = position["entryPx"]
                    mark_price = position["markPx"]
                    
                    # Parse PnL from string format like "$123.45" or "($123.45)"
                    pnl_str = position["pnl"].replace('$', '').replace(',', '')
                    if '(' in pnl_str and ')' in pnl_str:
                        # Negative PnL is in parentheses
                        pnl = -float(pnl_str.replace('(', '').replace(')', ''))
                    else:
                        pnl = float(pnl_str)
                    
                    # Calculate position value
                    position_value = abs(size * mark_price)
                
                # Determine if long or short
                is_long = size > 0
                
                position_info = {
                    "label": label,
                    "address": address,
                    "coin": coin,
                    "entry_price": entry_price,
                    "mark_price": mark_price,
                    "leverage": 20,  # Assuming default leverage
                    "position_value": position_value,
                    "size": size,
                    "unrealized_pnl": pnl,
                    "liquidation_price": 0,  # Not available from scraped data
                    "is_long": is_long,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                positions.append(position_info)
                
            except Exception as e:
                print(f"{Fore.RED}⚠️ Error processing scraped position for {coin}: {str(e)}")
                continue
    else:
        # Handle API data format
        for asset_position in data["assetPositions"]:
            try:
                # Check if the position has the expected structure
                if "position" in asset_position:
                    position = asset_position["position"]
                    
                    coin = position["coin"]
                    # Use the exact size from the API without any scaling
                    size = float(position["szi"])
                    entry_price = float(position["entryPx"])
                    
                    # Calculate mark price if not directly available
                    if "markPx" in position:
                        mark_price = float(position["markPx"])
                    else:
                        # If we have position value and size, we can calculate mark price
                        if "positionValue" in position and size != 0:
                            position_value = float(position["positionValue"])
                            mark_price = position_value / abs(size)
                        else:
                            # Fallback to entry price
                            mark_price = entry_price
                    
                    # Use the position value directly from the API if available
                    if "positionValue" in position:
                        # Apply a scaling factor to match the UI values (API values are 10x higher)
                        position_value = float(position["positionValue"]) / 10
                    else:
                        # Calculate position value based on size and mark price
                        position_value = abs(size * mark_price)
                    
                    # Get unrealized PnL directly from the API
                    unrealized_pnl = float(position.get("unrealizedPnl", 0))
                    
                    # Get liquidation price if available
                    liquidation_price = 0
                    if "liquidationPx" in position and position["liquidationPx"] is not None:
                        liquidation_price = float(position["liquidationPx"])
                    
                    # Determine if long or short
                    is_long = size > 0
                    
                    # Get leverage
                    leverage = 20  # Default leverage
                    if "leverage" in position and "value" in position["leverage"]:
                        leverage = float(position["leverage"]["value"])
                    
                    position_info = {
                        "label": label,
                        "address": address,
                        "coin": coin,
                        "entry_price": entry_price,
                        "mark_price": mark_price,
                        "leverage": leverage,
                        "position_value": position_value,
                        "size": size,
                        "unrealized_pnl": unrealized_pnl,
                        "liquidation_price": liquidation_price,
                        "is_long": is_long,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    positions.append(position_info)
                
            except Exception as e:
                print(f"{Fore.RED}⚠️ Error processing position for {coin}: {str(e)}")
                continue
    
    print(f"{Fore.GREEN}✅ Processed {len(positions)} positions for {label}")
    return positions

def display_positions_for_market_maker(positions, label):
    """
    Display positions for a specific market maker
    """
    if not positions:
        print(f"{Fore.YELLOW}⚠️ No positions to display for {label}!")
        return
    
    # Create a DataFrame for easier manipulation
    df = pd.DataFrame(positions)
    
    # Print header with fancy box
    print(f"\n{Fore.CYAN}{'='*120}")
    print(f"{Fore.CYAN}{'='*35} 🏦 {label} MARKET MAKER POSITIONS 🏦 {'='*35}")
    print(f"{Fore.CYAN}{'='*120}")
    
    # Calculate total position value and PnL
    total_value = df['position_value'].sum()
    total_pnl = df['unrealized_pnl'].sum()
    
    # Calculate long and short exposure
    long_exposure = df[df['is_long']]['position_value'].sum()
    short_exposure = df[~df['is_long']]['position_value'].sum()
    net_exposure = long_exposure - short_exposure
    
    # Calculate percentages
    long_pct = (long_exposure / total_value * 100) if total_value > 0 else 0
    short_pct = (short_exposure / total_value * 100) if total_value > 0 else 0
    
    # Display summary
    print(f"{Fore.MAGENTA}📊 Total Position Value: ${total_value:,.2f}")
    print(f"{Fore.MAGENTA}📊 Total Unrealized PnL: ${total_pnl:,.2f}")
    print(f"{Fore.MAGENTA}📊 Total Positions: {len(positions)}")
    print(f"{Fore.GREEN}📊 Total LONG Exposure: ${long_exposure:,.2f} ({long_pct:.2f}%)")
    print(f"{Fore.RED}📊 Total SHORT Exposure: ${short_exposure:,.2f} ({short_pct:.2f}%)")
    print(f"{Fore.CYAN}📊 Net Exposure: ${net_exposure:,.2f} ({Fore.GREEN if net_exposure >= 0 else Fore.RED}{'LONG' if net_exposure >= 0 else 'SHORT'}{Fore.CYAN} biased)")
    
    # Split into longs and shorts
    longs = df[df['is_long']].sort_values('position_value', ascending=False)
    shorts = df[~df['is_long']].sort_values('position_value', ascending=False)
    
    # Display long positions
    print(f"\n{Fore.GREEN}{Style.BRIGHT}🚀 LONG POSITIONS ({len(longs)}) 📈")
    print(f"{Fore.GREEN}{'-'*120}")
    
    if len(longs) > 0:
        # Display positions up to MAX_POSITIONS_TO_DISPLAY
        top_longs = longs.head(MAX_POSITIONS_TO_DISPLAY)
        for i, (_, row) in enumerate(top_longs.iterrows(), 1):
            liq_price = row['liquidation_price'] if row['liquidation_price'] > 0 else "N/A"
            liq_display = f"${liq_price:,.2f}" if liq_price != "N/A" else "N/A"
            
            # Format the size with the coin symbol for better readability
            if abs(row['size']) < 0.001:
                size_display = f"{row['size']:.8f}"
            elif abs(row['size']) < 1:
                size_display = f"{row['size']:.6f}"
            elif abs(row['size']) < 1000:
                size_display = f"{row['size']:.4f}"
            else:
                size_display = f"{row['size']:,.2f}"
            
            print(f"{Fore.GREEN}#{i} {Fore.YELLOW}{row['coin']}  {row['leverage']}x " + 
                  f"{Fore.GREEN}${row['position_value']:,.2f} " + 
                  f"{Fore.BLUE}| Size: {size_display} " +
                  f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} " +
                  f"{Fore.MAGENTA}| PnL: ${row['unrealized_pnl']:,.2f} " +
                  f"{Fore.RED}| Liq: {liq_display}")
        
        # If there are more positions than MAX_POSITIONS_TO_DISPLAY, show a message
        if len(longs) > MAX_POSITIONS_TO_DISPLAY:
            print(f"{Fore.YELLOW}... and {len(longs) - MAX_POSITIONS_TO_DISPLAY} more long positions (showing top {MAX_POSITIONS_TO_DISPLAY} by value)")
    else:
        print(f"{Fore.YELLOW}No long positions found!")
    
    # Display short positions
    print(f"\n{Fore.RED}{Style.BRIGHT}💥 SHORT POSITIONS ({len(shorts)}) 📉")
    print(f"{Fore.RED}{'-'*120}")
    
    if len(shorts) > 0:
        # Display positions up to MAX_POSITIONS_TO_DISPLAY
        top_shorts = shorts.head(MAX_POSITIONS_TO_DISPLAY)
        for i, (_, row) in enumerate(top_shorts.iterrows(), 1):
            liq_price = row['liquidation_price'] if row['liquidation_price'] > 0 else "N/A"
            liq_display = f"${liq_price:,.2f}" if liq_price != "N/A" else "N/A"
            
            # Format the size with the coin symbol for better readability
            if abs(row['size']) < 0.001:
                size_display = f"{row['size']:.8f}"
            elif abs(row['size']) < 1:
                size_display = f"{row['size']:.6f}"
            elif abs(row['size']) < 1000:
                size_display = f"{row['size']:.4f}"
            else:
                size_display = f"{row['size']:,.2f}"
            
            print(f"{Fore.RED}#{i} {Fore.YELLOW}{row['coin']}  {row['leverage']}x " + 
                  f"{Fore.RED}${row['position_value']:,.2f} " + 
                  f"{Fore.BLUE}| Size: {size_display} " +
                  f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} " +
                  f"{Fore.MAGENTA}| PnL: ${row['unrealized_pnl']:,.2f} " +
                  f"{Fore.RED}| Liq: {liq_display}")
        
        # If there are more positions than MAX_POSITIONS_TO_DISPLAY, show a message
        if len(shorts) > MAX_POSITIONS_TO_DISPLAY:
            print(f"{Fore.YELLOW}... and {len(shorts) - MAX_POSITIONS_TO_DISPLAY} more short positions (showing top {MAX_POSITIONS_TO_DISPLAY} by value)")
    else:
        print(f"{Fore.YELLOW}No short positions found!")
    
    # Print footer
    print(f"{Fore.CYAN}{'='*120}")
    
    # Add exposure data to the DataFrame for later use
    df_summary = pd.DataFrame({
        'label': [label],
        'total_value': [total_value],
        'total_pnl': [total_pnl],
        'long_exposure': [long_exposure],
        'short_exposure': [short_exposure],
        'long_pct': [long_pct],
        'short_pct': [short_pct],
        'net_exposure': [net_exposure],
        'position_count': [len(positions)]
    })
    
    return df, df_summary

def save_positions_to_csv(all_positions):
    """
    Save all positions to CSV files
    """
    if not all_positions:
        print(f"{Fore.RED}🌙 Moon Dev says: No positions found to save! 😢")
        return
    
    # Create a DataFrame with all positions
    df = pd.DataFrame(all_positions)
    
    # Format numeric columns
    numeric_cols = ['entry_price', 'position_value', 'unrealized_pnl', 'liquidation_price', 'size']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].astype(float)
    
    # Save all positions to a single file
    all_positions_file = os.path.join(DATA_DIR, "all_market_maker_positions.csv")
    df.to_csv(all_positions_file, index=False, float_format='%.6f')
    print(f"{Fore.GREEN}🌙 Moon Dev says: Saved {len(all_positions)} positions to {all_positions_file} 🚀")
    
    # Save positions for each market maker separately
    for label in df['label'].unique():
        label_df = df[df['label'] == label]
        label_file = os.path.join(DATA_DIR, f"{label}_positions.csv")
        label_df.to_csv(label_file, index=False, float_format='%.6f')
        print(f"{Fore.GREEN}💾 Saved {len(label_df)} positions for {label} to {label_file}")
    
    # Create and save aggregated view by coin
    print(f"\n{Fore.YELLOW}🔄 Creating aggregated view...")
    
    # Aggregate by coin and direction (long/short)
    agg_df = df.groupby(['label', 'coin', 'is_long']).agg({
        'position_value': 'sum',
        'unrealized_pnl': 'sum',
        'size': 'sum',
        'leverage': 'mean',  # Average leverage
    }).reset_index()
    
    # Add direction and rename columns
    agg_df['direction'] = agg_df['is_long'].apply(lambda x: 'LONG' if x else 'SHORT')
    agg_df = agg_df.rename(columns={
        'position_value': 'total_value',
        'unrealized_pnl': 'total_pnl',
        'leverage': 'avg_leverage',
    })
    
    # Sort by total value
    agg_df = agg_df.sort_values(['label', 'total_value'], ascending=[True, False])
    
    # Save aggregated view
    agg_file = os.path.join(DATA_DIR, "aggregated_market_maker_positions.csv")
    agg_df.to_csv(agg_file, index=False, float_format='%.6f')
    print(f"{Fore.GREEN}📊 Saved aggregated positions to {agg_file}")
    
    return df, agg_df

def display_combined_summary(all_positions_df, summary_dfs):
    """
    Display a combined summary of all market maker positions
    """
    if all_positions_df is None or all_positions_df.empty:
        print(f"{Fore.RED}No positions to display in combined summary!")
        return
    
    # Print header with fancy box
    print(f"\n{Fore.CYAN}{'='*120}")
    print(f"{Fore.CYAN}{'='*30} 🏦 COMBINED MARKET MAKER SUMMARY 🏦 {'='*30}")
    print(f"{Fore.CYAN}{'='*120}")
    
    # Combine all summary DataFrames
    combined_summary = pd.concat(summary_dfs)
    
    # Calculate total across all market makers
    total_value = combined_summary['total_value'].sum()
    total_pnl = combined_summary['total_pnl'].sum()
    total_positions = combined_summary['position_count'].sum()
    total_long_exposure = combined_summary['long_exposure'].sum()
    total_short_exposure = combined_summary['short_exposure'].sum()
    total_net_exposure = total_long_exposure - total_short_exposure
    
    # Calculate overall percentages
    total_long_pct = (total_long_exposure / total_value * 100) if total_value > 0 else 0
    total_short_pct = (total_short_exposure / total_value * 100) if total_value > 0 else 0
    
    # Display overall summary
    print(f"{Fore.MAGENTA}📊 OVERALL SUMMARY:")
    print(f"{Fore.MAGENTA}📊 Total Position Value: ${total_value:,.2f}")
    print(f"{Fore.MAGENTA}📊 Total Unrealized PnL: ${total_pnl:,.2f}")
    print(f"{Fore.MAGENTA}📊 Total Positions: {total_positions}")
    print(f"{Fore.GREEN}📊 Total LONG Exposure Across All MMs: ${total_long_exposure:,.2f} ({total_long_pct:.2f}%)")
    print(f"{Fore.RED}📊 Total SHORT Exposure Across All MMs: ${total_short_exposure:,.2f} ({total_short_pct:.2f}%)")
    print(f"{Fore.CYAN}📊 Net Exposure Across All MMs: ${total_net_exposure:,.2f} ({Fore.GREEN if total_net_exposure >= 0 else Fore.RED}{'LONG' if total_net_exposure >= 0 else 'SHORT'}{Fore.CYAN} biased)")
    
    # Display summary by market maker
    print(f"\n{Fore.YELLOW}📊 SUMMARY BY MARKET MAKER:")
    for _, row in combined_summary.iterrows():
        print(f"{Fore.CYAN}{row['label']}: " +
              f"{Fore.GREEN}${row['total_value']:,.2f} " +
              f"{Fore.MAGENTA}| PnL: ${row['total_pnl']:,.2f} " +
              f"{Fore.GREEN}| LONG: ${row['long_exposure']:,.2f} ({row['long_pct']:.2f}%) " +
              f"{Fore.RED}| SHORT: ${row['short_exposure']:,.2f} ({row['short_pct']:.2f}%) " +
              f"{Fore.CYAN}| NET: ${row['net_exposure']:,.2f} " +
              f"{Fore.YELLOW}| Positions: {row['position_count']}")
    
    # Group by coin for top coins
    coin_summary = all_positions_df.groupby('coin').agg({
        'position_value': 'sum'
    }).reset_index()
    
    coin_summary = coin_summary.sort_values('position_value', ascending=False)
    
    # Display top coins
    print(f"\n{Fore.YELLOW}📊 TOP COINS BY POSITION VALUE:")
    for i, (_, row) in enumerate(coin_summary.head(10).iterrows(), 1):
        print(f"{Fore.CYAN}#{i} {Fore.YELLOW}{row['coin']}: {Fore.GREEN}${row['position_value']:,.2f}")
    
    # Print footer
    print(f"\n{Fore.CYAN}{'='*120}")
    print(f"{Fore.CYAN}{'='*30} 🌙 Moon Dev Market Maker Tracker 🚀 {'='*30}")
    print(f"{Fore.CYAN}{'='*120}")

def dump_readable_positions(positions, label):
    """
    Dump positions in a more readable JSON format for analysis
    """
    if not positions:
        print(f"{Fore.RED}⚠️ No positions to dump for {label}!")
        return
    
    try:
        # Create a filename with the label
        filename = os.path.join(DATA_DIR, f"readable_{label}_positions.json")
        
        # Convert positions to a more readable format
        readable_positions = []
        for pos in positions:
            readable_pos = {
                "coin": pos["coin"],
                "size": pos["size"],
                "size_formatted": f"{pos['size']:,.4f}",
                "entry_price": pos["entry_price"],
                "mark_price": pos["mark_price"],
                "position_value": pos["position_value"],
                "position_value_formatted": f"${pos['position_value']:,.2f}",
                "unrealized_pnl": pos["unrealized_pnl"],
                "unrealized_pnl_formatted": f"${pos['unrealized_pnl']:,.2f}",
                "is_long": pos["is_long"],
                "direction": "LONG" if pos["is_long"] else "SHORT",
                "leverage": pos["leverage"],
                "liquidation_price": pos["liquidation_price"]
            }
            readable_positions.append(readable_pos)
        
        # Sort by position value (descending)
        readable_positions = sorted(readable_positions, key=lambda x: x["position_value"], reverse=True)
        
        # Write the data to a JSON file with pretty formatting
        with open(filename, 'w') as f:
            json.dump(readable_positions, f, indent=4)
        
        print(f"{Fore.MAGENTA}💾 Dumped readable positions for {label} to {filename}")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Error dumping readable positions for {label}: {str(e)}")

def main():
    """Main function to run the market maker position tracker"""
    start_time = time.time()
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.MAGENTA}{'*'*20} 🌙 Moon Dev's Market Maker Tracker Starting... 🏦 {'*'*20}")
    print(f"{Fore.CYAN}{'='*80}")
    
    # Ensure data directory exists
    ensure_data_dir()
    
    # Fetch and process positions for each market maker
    all_positions = []
    all_dfs = []
    summary_dfs = []
    
    # Create a reordered dictionary to process HLP last
    reordered_market_makers = {}
    hlp_address = None
    
    # First add all non-HLP addresses
    for label, address in MARKET_MAKERS.items():
        if label != "HLP":
            reordered_market_makers[label] = address
        else:
            hlp_address = address
    
    # Then add HLP at the end if it exists
    if hlp_address:
        reordered_market_makers["HLP"] = hlp_address
    
    # Process each market maker in the new order
    for label, address in reordered_market_makers.items():
        # Fetch positions
        data = get_positions_for_address(label, address)
        
        # Process positions
        if data:
            positions = process_positions(data, label, address)
            
            # Dump readable positions for analysis
            dump_readable_positions(positions, label)
            
            # Display positions
            if positions:
                df, summary_df = display_positions_for_market_maker(positions, label)
                all_positions.extend(positions)
                all_dfs.append(df)
                summary_dfs.append(summary_df)
    
    # Combine all DataFrames
    if all_dfs:
        combined_df = pd.concat(all_dfs)
        
        # Display combined summary
        display_combined_summary(combined_df, summary_dfs)
        
        # Save positions to CSV
        save_positions_to_csv(all_positions)
    else:
        print(f"{Fore.RED}⚠️ No positions found for any market maker!")
    
    # Calculate and display execution time
    execution_time = time.time() - start_time
    print(f"\n{Fore.CYAN}⏱️ Execution time: {execution_time:.2f} seconds")
    
    print(f"\n{Fore.MAGENTA}{'*'*20} 🌙 Moon Dev says: Market maker tracking complete! 🚀 {'*'*20}")
    print(f"{Fore.CYAN}📁 CSV files saved in: {DATA_DIR}")
    print(f"{Fore.CYAN}📁 JSON files saved in: {DATA_DIR}")

if __name__ == "__main__":
    print("sup dawg")
    main() 