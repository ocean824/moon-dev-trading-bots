'''
Building out a statistical arbitrage bot that looks at liquidation points in order to pick out which to long and which to short. 

this is similar to the liq_statarb.py but this time we are going to enter after big liquidations have happened. 
'''

import os
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime
import colorama
from colorama import Fore, Back, Style
import sys
import traceback
import random
from termcolor import colored
import requests
from eth_account.signers.local import LocalAccount
import eth_account
from dotenv import load_dotenv
import schedule

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from api import MoonDevAPI  # Import MoonDevAPI from the root directory
import nice_funcs as n  # Import nice_funcs

# Initialize colorama for terminal colors
colorama.init(autoreset=True)

# Load environment variables from .env file
load_dotenv()

# Get the Hyperliquid key from environment variables
HYPER_LIQUID_KEY = os.getenv('HYPER_LIQUID_KEY')

# Initialize account
account = LocalAccount = eth_account.Account.from_key(HYPER_LIQUID_KEY)

# Initialize API
api = MoonDevAPI()

# Configure pandas display options
pd.set_option('display.float_format', '{:.2f}'.format)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# Configuration
MIN_POSITION_VALUE = 50000  # Only track positions with value >= $50,000
TOP_N_POSITIONS = 30  # Number of top positions to display
TOKENS_TO_ANALYZE = ['BTC', 'ETH', 'XRP', 'SOL']  # Core tokens to analyze
HIGHLIGHT_THRESHOLD = 1000000  # $1 million - Changed from 2M to 1M
POSITION_SIZE_USD = 10  # Position size in USD
LEVERAGE = 10  # Leverage to use for trading
COMBINED_STOP_LOSS = -3  # Combined stop loss percentage (negative)
COMBINED_TAKE_PROFIT = 3  # Combined take profit percentage (positive)

# Liquidation settings
LIQUIDATION_THRESHOLD = 300000  # $300k threshold for total liquidations to trigger entries
LIQUIDATION_LOOKBACK_MINUTES = 5  # Time period to look back for liquidations

# API Rate Limiting Settings
MAX_RETRIES = 3  # Maximum number of retries for API calls
BASE_DELAY = 1.0  # Base delay between API calls in seconds
RETRY_DELAY = 2.0  # Delay between retries in seconds

def api_call_with_retry(func, *args, **kwargs):
    """
    Wrapper function to handle API calls with retry logic
    """
    for attempt in range(MAX_RETRIES):
        try:
            # Add random jitter to base delay
            jitter = random.uniform(0.1, 0.5)
            time.sleep(BASE_DELAY + jitter)
            
            result = func(*args, **kwargs)
            return result
            
        except Exception as e:
            if '429' in str(e):  # Rate limit error
                if attempt < MAX_RETRIES - 1:  # Don't sleep on last attempt
                    sleep_time = RETRY_DELAY * (attempt + 1) + random.uniform(0.1, 0.5)
                    print(f"{Fore.YELLOW}⚠️ Rate limit hit, waiting {sleep_time:.1f}s before retry {attempt + 1}/{MAX_RETRIES}")
                    time.sleep(sleep_time)
                continue
            raise  # Re-raise other exceptions
    
    print(f"{Fore.RED}❌ Max retries ({MAX_RETRIES}) reached, skipping operation")
    return None

def get_position_safely(symbol, account):
    """Safe wrapper for position checking"""
    print(f"\n{Fore.CYAN}🔍 Moon Dev checking position for {symbol}...")
    try:
        result = api_call_with_retry(n.get_position, symbol, account)
        
        # Debug the raw result
        print(f"{Fore.YELLOW}📋 Raw position data type: {type(result)}")
        print(f"{Fore.YELLOW}📋 Raw position data: {result}")
        
        if result is None:
            print(f"{Fore.RED}❌ Got None response checking position for {symbol}")
            return None, False, 0, None, 0, 0, True  # Return default values
            
        # Check if result is a tuple with expected length
        if isinstance(result, tuple) and len(result) == 7:
            print(f"{Fore.GREEN}✅ Successfully got position data for {symbol}")
            return result
        else:
            print(f"{Fore.RED}❌ Unexpected position data format for {symbol}")
            print(f"{Fore.RED}Expected tuple of length 7, got: {type(result)} of length {len(result) if hasattr(result, '__len__') else 'N/A'}")
            return None, False, 0, None, 0, 0, True  # Return default values
            
    except Exception as e:
        print(f"{Fore.RED}❌ Error in get_position_safely for {symbol}: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return None, False, 0, None, 0, 0, True  # Return default values

def get_price_safely(symbol):
    """Safe wrapper for price checking"""
    print(f"\n{Fore.CYAN}💰 Moon Dev fetching price for {symbol}...")
    try:
        result = api_call_with_retry(n.ask_bid, symbol)
        if result is None:
            print(f"{Fore.RED}❌ Got None response fetching price for {symbol}")
            return None, None, None
        ask, bid, last = result
        print(f"{Fore.GREEN}✅ Got prices for {symbol}:")
        print(f"{Fore.YELLOW}📈 Ask: ${ask if ask else 'None'}")
        print(f"{Fore.YELLOW}📉 Bid: ${bid if bid else 'None'}")
        print(f"{Fore.YELLOW}📊 Last: ${last if last else 'None'}")
        return result
    except Exception as e:
        print(f"{Fore.RED}❌ Error in get_price_safely for {symbol}: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return None, None, None

def adjust_leverage_safely(symbol, size, leverage, account):
    """Safe wrapper for leverage adjustment"""
    return api_call_with_retry(n.adjust_leverage_usd_size, symbol, size, leverage, account)

# # # CLOSE ALL POSITIONS
# n.close_all_positions(account)
# time.sleep(7886)

def process_positions(df):
    """Process the position data into a more usable format"""
    if df is None or df.empty:
        print(f"{Fore.RED}❌ No positions data to process!")
        return pd.DataFrame()
    
    print(f"{Fore.CYAN}🔍 Processing {len(df)} positions...")
    
    # Filter positions below minimum value threshold
    filtered_df = df[df['position_value'] >= MIN_POSITION_VALUE].copy()
    
    # Make sure numeric columns are the right type
    numeric_cols = ['entry_price', 'position_value', 'unrealized_pnl', 'liquidation_price', 'leverage']
    for col in numeric_cols:
        if col in filtered_df.columns:
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors='coerce')
    
    # Convert boolean columns if needed
    if 'is_long' in filtered_df.columns and filtered_df['is_long'].dtype != bool:
        filtered_df['is_long'] = filtered_df['is_long'].map({'True': True, 'False': False})
    
    # Validate position types for positions with valid liquidation prices
    valid_liq_df = filtered_df[filtered_df['liquidation_price'] > 0].copy()
    if not valid_liq_df.empty:
        # Create a corrected position type column based on liquidation vs entry price
        valid_liq_df['is_long_corrected'] = valid_liq_df['liquidation_price'] < valid_liq_df['entry_price']
        
        # Update the filtered dataframe with corrected position types
        filtered_df.loc[valid_liq_df.index, 'is_long'] = valid_liq_df['is_long_corrected']
    
    print(f"{Fore.GREEN}✅ Processed {len(filtered_df)} positions after filtering (min value: ${MIN_POSITION_VALUE:,})")
    return filtered_df

def display_liquidation_risk(df):
    """Display positions closest to liquidation and save to DataFrame"""
    if df is None or df.empty:
        print(f"{Fore.RED}❌ No positions to analyze!")
        return
    
    # Create data directory if it doesn't exist
    data_dir = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/bots/hyperliquid/data"
    os.makedirs(data_dir, exist_ok=True)
    
    # Create a copy to avoid modifying the original
    risk_df = df.copy()
    
    # Filter out positions with invalid liquidation prices
    risk_df = risk_df[risk_df['liquidation_price'] > 0]
    
    if risk_df.empty:
        print(f"{Fore.YELLOW}⚠️ No positions with valid liquidation prices found!")
        return
    
    # Filter risk_df to only include tokens in TOKENS_TO_ANALYZE
    risk_df = risk_df[risk_df['coin'].isin(TOKENS_TO_ANALYZE)]
    
    # Get current prices for each token
    current_prices = {}
    for coin in TOKENS_TO_ANALYZE:
        try:
            url = f"https://api.hyperliquid.xyz/info"
            headers = {"Content-Type": "application/json"}
            body = {"type": "metaAndAssetCtxs"}
            response = requests.post(url, headers=headers, json=body)
            data = response.json()
            
            # Find the coin in the universe
            for i, asset in enumerate(data[0]['universe']):
                if asset['name'] == coin:
                    current_prices[coin] = float(data[1][i]['markPx'])
                    break
                    
        except Exception as e:
            print(f"{Fore.RED}❌ Error fetching price for {coin}: {str(e)}")
            continue
    
    # Add current price to the DataFrame
    risk_df['current_price'] = risk_df['coin'].map(current_prices)
    
    # Calculate distance to liquidation percentage
    risk_df['distance_to_liq_pct'] = np.where(
        risk_df['is_long'],
        abs((risk_df['current_price'] - risk_df['liquidation_price']) / risk_df['current_price'] * 100),
        abs((risk_df['liquidation_price'] - risk_df['current_price']) / risk_df['current_price'] * 100)
    )
    
    # Sort by distance to liquidation (ascending)
    risk_df = risk_df.sort_values('distance_to_liq_pct')
    
    # Split into longs and shorts
    risky_longs = risk_df[risk_df['is_long']].sort_values('distance_to_liq_pct')
    risky_shorts = risk_df[~risk_df['is_long']].sort_values('distance_to_liq_pct')
    
    # Initialize dictionaries to store largest positions per symbol
    largest_longs = {coin: None for coin in TOKENS_TO_ANALYZE}
    largest_shorts = {coin: None for coin in TOKENS_TO_ANALYZE}
    
    # Display positions closest to liquidation - LONGS
    print(f"\n{Fore.GREEN}{Style.BRIGHT}🚀 TOP {TOP_N_POSITIONS} LONG POSITIONS CLOSEST TO LIQUIDATION 📈")
    print(f"{Fore.GREEN}{'-'*80}")
    
    if len(risky_longs) > 0:
        for i, (_, row) in enumerate(risky_longs.head(TOP_N_POSITIONS).iterrows(), 1):
            highlight = row['position_value'] > HIGHLIGHT_THRESHOLD
            
            # Store the first position over threshold for each symbol
            if highlight and largest_longs[row['coin']] is None:
                largest_longs[row['coin']] = row
            
            display_text = (
                f"{Fore.GREEN}#{i} {Fore.YELLOW}{row['coin']} "
                f"{Fore.GREEN}${row['position_value']:,.2f} "
                f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} "
                f"{Fore.RED}| Liq: ${row['liquidation_price']:,.2f} "
                f"{Fore.MAGENTA}| Current: ${row['current_price']:,.2f} "
                f"{Fore.MAGENTA}| Distance: {row['distance_to_liq_pct']:.2f}% "
                f"{Fore.CYAN}| Leverage: {row['leverage']}x"
            )
            
            if highlight:
                display_text = colored(
                    f"#{i} {row['coin']} ${row['position_value']:,.2f} "
                    f"| Entry: ${row['entry_price']:,.2f} "
                    f"| Liq: ${row['liquidation_price']:,.2f} "
                    f"| Current: ${row['current_price']:,.2f} "
                    f"| Distance: {row['distance_to_liq_pct']:.2f}% "
                    f"| Leverage: {row['leverage']}x",
                    'black', 'on_yellow'
                )
            
            print(display_text)
            print(f"{Fore.CYAN}   Address: {row['address']}")
    else:
        print(f"{Fore.YELLOW}No long positions with liquidation prices found!")
    
    # Display positions closest to liquidation - SHORTS
    print(f"\n{Fore.RED}{Style.BRIGHT}💥 TOP {TOP_N_POSITIONS} SHORT POSITIONS CLOSEST TO LIQUIDATION 📉")
    print(f"{Fore.RED}{'-'*80}")
    
    if len(risky_shorts) > 0:
        for i, (_, row) in enumerate(risky_shorts.head(TOP_N_POSITIONS).iterrows(), 1):
            highlight = row['position_value'] > HIGHLIGHT_THRESHOLD
            
            # Store the first position over threshold for each symbol
            if highlight and largest_shorts[row['coin']] is None:
                largest_shorts[row['coin']] = row
            
            display_text = (
                f"{Fore.RED}#{i} {Fore.YELLOW}{row['coin']} "
                f"{Fore.RED}${row['position_value']:,.2f} "
                f"{Fore.BLUE}| Entry: ${row['entry_price']:,.2f} "
                f"{Fore.RED}| Liq: ${row['liquidation_price']:,.2f} "
                f"{Fore.MAGENTA}| Current: ${row['current_price']:,.2f} "
                f"{Fore.MAGENTA}| Distance: {row['distance_to_liq_pct']:.2f}% "
                f"{Fore.CYAN}| Leverage: {row['leverage']}x"
            )
            
            if highlight:
                display_text = colored(
                    f"#{i} {row['coin']} ${row['position_value']:,.2f} "
                    f"| Entry: ${row['entry_price']:,.2f} "
                    f"| Liq: ${row['liquidation_price']:,.2f} "
                    f"| Current: ${row['current_price']:,.2f} "
                    f"| Distance: {row['distance_to_liq_pct']:.2f}% "
                    f"| Leverage: {row['leverage']}x",
                    'black', 'on_yellow'
                )
            
            print(display_text)
            print(f"{Fore.CYAN}   Address: {row['address']}")
    else:
        print(f"{Fore.YELLOW}No short positions with liquidation prices found!")

    # Final summary of largest positions near liquidation per symbol
    print(f"\n{Fore.CYAN}{'='*100}")
    print(f"{Fore.CYAN}💥 LARGEST POSITIONS NEAR LIQUIDATION BY SYMBOL (>${HIGHLIGHT_THRESHOLD:,}) 💥")
    print(f"{Fore.CYAN}{'='*100}")

    for coin in TOKENS_TO_ANALYZE:
        print(f"\n{Fore.YELLOW}{'='*50} {coin} {'='*50}")
        
        # Display largest long for this symbol
        if largest_longs[coin] is not None:
            print(f"\n{Fore.GREEN}🚀 LARGEST {coin} LONG AT RISK:")
            print(colored(
                f"${largest_longs[coin]['position_value']:,.2f} position "
                f"| Entry: ${largest_longs[coin]['entry_price']:,.2f} "
                f"| Current: ${largest_longs[coin]['current_price']:,.2f} "
                f"| Liq: ${largest_longs[coin]['liquidation_price']:,.2f} "
                f"| Distance: {largest_longs[coin]['distance_to_liq_pct']:.2f}% "
                f"| Leverage: {largest_longs[coin]['leverage']}x",
                'black', 'on_green'
            ))
            print(f"{Fore.GREEN}Address: {largest_longs[coin]['address']}")
        else:
            print(f"\n{Fore.YELLOW}No large {coin} long positions (>${HIGHLIGHT_THRESHOLD:,}) near liquidation")

        # Display largest short for this symbol
        if largest_shorts[coin] is not None:
            print(f"\n{Fore.RED}📉 LARGEST {coin} SHORT AT RISK:")
            print(colored(
                f"${largest_shorts[coin]['position_value']:,.2f} position "
                f"| Entry: ${largest_shorts[coin]['entry_price']:,.2f} "
                f"| Current: ${largest_shorts[coin]['current_price']:,.2f} "
                f"| Liq: ${largest_shorts[coin]['liquidation_price']:,.2f} "
                f"| Distance: {largest_shorts[coin]['distance_to_liq_pct']:.2f}% "
                f"| Leverage: {largest_shorts[coin]['leverage']}x",
                'black', 'on_red'
            ))
            print(f"{Fore.RED}Address: {largest_shorts[coin]['address']}")
        else:
            print(f"\n{Fore.YELLOW}No large {coin} short positions (>${HIGHLIGHT_THRESHOLD:,}) near liquidation")

    print(f"\n{Fore.CYAN}{'='*100}")

    # Create DataFrame for largest positions at risk
    trade_data = []
    
    for coin in TOKENS_TO_ANALYZE:
        if largest_longs[coin] is not None:
            trade_data.append({
                'symbol': coin,
                'position_type': 'LONG',
                'position_value': largest_longs[coin]['position_value'],
                'entry_price': largest_longs[coin]['entry_price'],
                'current_price': largest_longs[coin]['current_price'],
                'liquidation_price': largest_longs[coin]['liquidation_price'],
                'distance_to_liq_pct': largest_longs[coin]['distance_to_liq_pct'],
                'leverage': largest_longs[coin]['leverage'],
                'address': largest_longs[coin]['address'],
                'suggested_action': 'SHORT'  # We short when there's a large long near liquidation
            })
            
        if largest_shorts[coin] is not None:
            trade_data.append({
                'symbol': coin,
                'position_type': 'SHORT',
                'position_value': largest_shorts[coin]['position_value'],
                'entry_price': largest_shorts[coin]['entry_price'],
                'current_price': largest_shorts[coin]['current_price'],
                'liquidation_price': largest_shorts[coin]['liquidation_price'],
                'distance_to_liq_pct': largest_shorts[coin]['distance_to_liq_pct'],
                'leverage': largest_shorts[coin]['leverage'],
                'address': largest_shorts[coin]['address'],
                'suggested_action': 'LONG'  # We long when there's a large short near liquidation
            })
    
    # Create DataFrame
    trade_df = pd.DataFrame(trade_data)
    
    if not trade_df.empty:
        # Sort by distance to liquidation
        trade_df = trade_df.sort_values('distance_to_liq_pct')
        
        # Save to CSV (fixed filename)
        csv_file = os.path.join(data_dir, "liquidation_trades.csv")
        trade_df.to_csv(csv_file, index=False)
        
        # Print the trading opportunities DataFrame
        print(f"\n{Fore.CYAN}{'='*100}")
        print(f"{Fore.CYAN}🎯 TRADING OPPORTUNITIES BASED ON LIQUIDATION RISK 🎯")
        print(f"{Fore.CYAN}{'='*100}")
        
        # Format the DataFrame for display
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        
        # Create a copy for display with formatted values
        display_df = trade_df.copy()
        
        # Format price and value columns with dollar signs
        price_value_cols = ['position_value', 'entry_price', 'current_price', 'liquidation_price']
        for col in price_value_cols:
            display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}")
        
        # Format percentage columns
        display_df['distance_to_liq_pct'] = display_df['distance_to_liq_pct'].apply(lambda x: f"{x:.2f}%")
        
        # Format leverage column
        display_df['leverage'] = display_df['leverage'].apply(lambda x: f"{x:.2f}x")
        
        # Print the formatted DataFrame
        print(display_df.to_string())
        
        # Sort by distance to liquidation and position value
        sorted_opportunities = trade_df.sort_values(['distance_to_liq_pct', 'position_value'], 
                                                  ascending=[True, False])
        
        # Find best opportunities for different symbols
        best_long = None
        best_short = None
        used_symbols = set()
        
        # Find the two closest positions to liquidation for different symbols
        for _, position in sorted_opportunities.iterrows():
            if position['symbol'] not in used_symbols:
                if position['suggested_action'] == 'LONG' and best_long is None:
                    best_long = position
                    used_symbols.add(position['symbol'])
                elif position['suggested_action'] == 'SHORT' and best_short is None:
                    best_short = position
                    used_symbols.add(position['symbol'])
                
                # Break if we found both positions
                if best_long is not None and best_short is not None:
                    break
        
        # Print the full DataFrame
        print(f"\n{Fore.CYAN}{'='*100}")
        print(f"{Fore.CYAN}📊 FULL LIQUIDATION OPPORTUNITIES DATAFRAME 📊")
        print(f"{Fore.CYAN}{'='*100}")
        print(trade_df.to_string())
        
        print(f"\n{Fore.CYAN}💾 Data saved to: {csv_file}")
        print(f"\n{Fore.CYAN}{'='*100}")

        # Add clear summary of planned trades
        print(f"\n{Fore.CYAN}{'='*100}")
        print(colored("🎯 PLANNED TRADES SUMMARY - MOON DEV'S LIQUIDATION HUNTER 🎯", 'black', 'on_cyan'))
        print(f"{Fore.CYAN}{'='*100}")
        
        if best_long is not None:
            print(colored(
                f"🚀 GOING LONG ON {best_long['symbol']} | " +
                f"Large short position (${best_long['position_value']:,.2f}) at risk | " +
                f"Distance to liquidation: {best_long['distance_to_liq_pct']:.2f}%",
                'black', 'on_green'
            ))
        
        if best_short is not None:
            print(colored(
                f"📉 GOING SHORT ON {best_short['symbol']} | " +
                f"Large long position (${best_short['position_value']:,.2f}) at risk | " +
                f"Distance to liquidation: {best_short['distance_to_liq_pct']:.2f}%",
                'black', 'on_red'
            ))
            
        print(f"{Fore.CYAN}{'='*100}\n")
        
        # After finding best_long and best_short, call manage_positions
        manage_positions(best_long, best_short)
        
        # Display best opportunities if found
        if best_long is not None:
            print(f"\n{Fore.GREEN}🚀 BEST LONG OPPORTUNITY:")
            print(f"{Fore.GREEN}{'-'*80}")
            print(colored(
                f"Symbol: {best_long['symbol']} | "
                f"Position Value: ${best_long['position_value']:,.2f} | "
                f"Current Price: ${best_long['current_price']:,.2f} | "
                f"Liquidation Price: ${best_long['liquidation_price']:,.2f} | "
                f"Distance: {best_long['distance_to_liq_pct']:.2f}% | "
                f"Leverage: {best_long['leverage']}x",
                'black', 'on_green'
            ))
            print(f"{Fore.GREEN}Address: {best_long['address']}")
        
        if best_short is not None:
            print(f"\n{Fore.RED}📉 BEST SHORT OPPORTUNITY:")
            print(f"{Fore.RED}{'-'*80}")
            print(colored(
                f"Symbol: {best_short['symbol']} | "
                f"Position Value: ${best_short['position_value']:,.2f} | "
                f"Current Price: ${best_short['current_price']:,.2f} | "
                f"Liquidation Price: ${best_short['liquidation_price']:,.2f} | "
                f"Distance: {best_short['distance_to_liq_pct']:.2f}% | "
                f"Leverage: {best_short['leverage']}x",
                'black', 'on_red'
            ))
            print(f"{Fore.RED}Address: {best_short['address']}")
        
        # Print the full DataFrame
        print(f"\n{Fore.CYAN}{'='*100}")
        print(f"{Fore.CYAN}📊 FULL LIQUIDATION OPPORTUNITIES DATAFRAME 📊")
        print(f"{Fore.CYAN}{'='*100}")
        print(trade_df.to_string())
        
        print(f"\n{Fore.CYAN}💾 Data saved to: {csv_file}")
        print(f"\n{Fore.CYAN}{'='*100}")
    else:
        print(f"\n{Fore.YELLOW}No positions above ${HIGHLIGHT_THRESHOLD:,} found near liquidation")

def fetch_positions_from_api():
    """Fetch positions from Moon Dev API"""
    try:
        # Get positions data from the API with retry logic
        positions_df = api_call_with_retry(api.get_positions_hlp)
        
        if positions_df is None or positions_df.empty:
            print(f"{Fore.RED}❌ No positions data received from API!")
            return None
            
        return positions_df
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error fetching positions: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return None

def close_positions_safely(account):
    """
    Close all positions safely by placing limit orders in parallel and monitoring fills.
    Will keep trying until all positions are closed.
    """
    print(f"\n{Fore.CYAN}{'='*100}")
    print(f"{Fore.CYAN}🔄 MOON DEV CLOSING POSITIONS SAFELY IN PARALLEL 🔄")
    print(f"{Fore.CYAN}{'='*100}")
    
    attempt = 1
    
    while True:
        active_positions = []
        
        # First check which positions are still open
        for symbol in TOKENS_TO_ANALYZE:
            positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = n.get_position(symbol, account)
            if im_in_pos:
                active_positions.append({
                    'symbol': symbol,
                    'size': abs(float(pos_size)),  # Make sure size is absolute value
                    'is_long': is_long,
                    'pnl': pnl_perc
                })
        
        if not active_positions:
            print(f"{Fore.GREEN}✅ All positions closed successfully!")
            return True
            
        print(f"\n{Fore.YELLOW}📊 Attempt {attempt} - Found {len(active_positions)} active positions")
        
        # Place limit orders to close all positions
        for pos in active_positions:
            try:
                # Cancel any existing orders first
                print(f"{Fore.YELLOW}🗑️ Canceling existing orders for {pos['symbol']}...")
                n.cancel_symbol_orders(account, pos['symbol'])
                time.sleep(0.5)  # Small delay after canceling
                
                # Get current prices
                ask, bid, _ = n.ask_bid(pos['symbol'])
                
                # If long position, we sell at bid (is_buy = False)
                # If short position, we buy at ask (is_buy = True)
                is_buy = not pos['is_long']  # Opposite of position direction
                close_price = ask if is_buy else bid
                
                # Place limit order to close
                direction_emoji = "📈" if pos['is_long'] else "📉"
                position_type = "LONG" if pos['is_long'] else "SHORT"
                print(f"{Fore.CYAN}{direction_emoji} Closing {position_type} {pos['symbol']} position: Size={pos['size']}, PnL={pos['pnl']:.2f}%")
                print(f"{Fore.CYAN}Using {'ask' if is_buy else 'bid'} price: ${close_price}")
                
                # Place the closing order with absolute size value
                n.limit_order(pos['symbol'], is_buy, pos['size'], close_price, True, account)
                print(f"{Fore.GREEN}✅ Close order placed for {pos['symbol']}")
                
            except Exception as e:
                print(f"{Fore.RED}❌ Error closing {pos['symbol']}: {str(e)}")
                continue
        
        # Wait for orders to potentially fill
        print(f"{Fore.YELLOW}⏳ Waiting 5 seconds to check fills...")
        time.sleep(5)
        attempt += 1
        
        # Print remaining positions after each attempt
        remaining = []
        for symbol in TOKENS_TO_ANALYZE:
            positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = n.get_position(symbol, account)
            if im_in_pos:
                remaining.append(f"{symbol} ({'LONG' if is_long else 'SHORT'})")
        
        if remaining:
            print(f"{Fore.YELLOW}⚠️ Still trying to close: {', '.join(remaining)}")
            print(f"{Fore.YELLOW}🔄 Starting next attempt...")
        else:
            print(f"{Fore.GREEN}✅ All positions closed successfully!")
            return True

def get_recent_liquidations():
    """
    Get total recent liquidations from Moon Dev API
    Returns:
        float: Total liquidation amount in USD
    """
    try:
        # Fetch liquidation data with retry logic
        liquidations = api_call_with_retry(api.get_liquidation_data, limit=1000)
        if liquidations is None:
            print(f"{Fore.RED}❌ Failed to fetch liquidation data")
            return 0
        
        # Convert to milliseconds timestamp
        current_time_ms = int(datetime.now().timestamp() * 1000)
        cutoff_time_ms = current_time_ms - (LIQUIDATION_LOOKBACK_MINUTES * 60 * 1000)
        
        # Filter liquidations within the lookback period
        recent_liquidations = liquidations[liquidations.iloc[:, 10].astype(float) >= cutoff_time_ms]
        
        if recent_liquidations.empty:
            return 0
        
        total_liquidations = recent_liquidations.iloc[:, 11].astype(float).sum()
        
        print(f"\n{Fore.CYAN}💧 Total Liquidations in the last {LIQUIDATION_LOOKBACK_MINUTES} minutes:")
        print(f"{Fore.YELLOW}💰 Total: ${total_liquidations:,.2f}")
        
        return total_liquidations
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error getting liquidations: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return 0

def manage_positions(best_long, best_short):
    """Manage both long and short positions based on liquidation analysis"""
    print(f"\n{Fore.CYAN}{'='*100}")
    print(f"{Fore.CYAN}🔄 Managing Stat Arb Positions Based on Liquidations")
    print(f"{Fore.CYAN}{'='*100}")
    
    print(f"{Fore.YELLOW}📊 Position Management Settings:")
    print(f"{Fore.YELLOW}Combined Stop Loss: {COMBINED_STOP_LOSS}%")
    print(f"{Fore.YELLOW}Combined Take Profit: {COMBINED_TAKE_PROFIT}%")
    
    # First check all current positions
    total_pnl = 0
    current_positions = []
    
    # Get all current positions first with delay between checks
    for symbol in TOKENS_TO_ANALYZE:
        try:
            print(f"\n{Fore.CYAN}{'='*50}")
            print(f"{Fore.CYAN}🔍 Checking {symbol} position and price data...")
            
            # Get position data with detailed error handling
            positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = get_position_safely(symbol, account)
            
            if positions is None:
                print(f"{Fore.YELLOW}⚠️ No position data for {symbol}, continuing to next symbol")
                continue
                
            if im_in_pos:
                current_positions.append({
                    'symbol': symbol,
                    'size': pos_size,
                    'is_long': is_long,
                    'pnl': pnl_perc
                })
                total_pnl += pnl_perc
                direction = "LONG 🚀" if is_long else "SHORT 📉"
                print(f"{Fore.YELLOW}Found active position: {direction} {symbol}, Size={pos_size}, PnL={pnl_perc:.2f}%")
            else:
                print(f"{Fore.YELLOW}No active position for {symbol}")
                
        except Exception as e:
            print(f"{Fore.RED}❌ Error checking position for {symbol}: {str(e)}")
            print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
            continue
        
        time.sleep(1)  # Increased delay between position checks
    
    print(f"\n{Fore.YELLOW}💰 Total Combined PnL: {total_pnl:.2f}%")
    print(f"{Fore.YELLOW}📊 Current Position Count: {len(current_positions)}")
    
    # SAFETY CHECK: If we have more than 2 positions, close everything and return
    if len(current_positions) > 2:
        print(f"{Fore.RED}⚠️ SAFETY TRIGGERED: Found {len(current_positions)} positions (max allowed: 2)")
        print(f"{Fore.RED}🚨 Closing all positions immediately...")
        success = close_positions_safely(account)
        if success:
            print(f"{Fore.GREEN}✅ Successfully closed all positions")
        else:
            print(f"{Fore.RED}❌ Failed to close all positions, please check manually!")
        return
    
    # Check for take profit or stop loss if we have any positions
    if len(current_positions) > 0:
        print(f"\n{Fore.CYAN}📊 Checking Combined PnL against TP/SL...")
        print(f"{Fore.YELLOW}Current PnL: {total_pnl:.2f}% | SL: {COMBINED_STOP_LOSS}% | TP: {COMBINED_TAKE_PROFIT}%")
        
        # Check if we hit stop loss or take profit
        if total_pnl <= COMBINED_STOP_LOSS:
            print(f"{Fore.RED}🛑 Stop Loss hit! Combined PnL ({total_pnl:.2f}%) <= Stop Loss ({COMBINED_STOP_LOSS}%)")
            print(f"{Fore.RED}🔄 Closing all positions safely...")
            success = close_positions_safely(account)
            if not success:
                print(f"{Fore.RED}❌ Failed to close positions on stop loss, please check manually!")
            return
            
        elif total_pnl >= COMBINED_TAKE_PROFIT:
            print(f"{Fore.GREEN}🎯 Take Profit hit! Combined PnL ({total_pnl:.2f}%) >= Take Profit ({COMBINED_TAKE_PROFIT}%)")
            print(f"{Fore.GREEN}🔄 Closing all positions safely...")
            success = close_positions_safely(account)
            if not success:
                print(f"{Fore.RED}❌ Failed to close positions on take profit, please check manually!")
            return
    
    # If we already have exactly 2 positions, just monitor
    if len(current_positions) == 2:
        print(f"{Fore.YELLOW}📊 Have maximum allowed positions (2) - monitoring only")
        print(f"{Fore.GREEN}✅ Both positions active, monitoring PnL...")
        print(f"{Fore.YELLOW}📊 PnL Status: {total_pnl:.2f}% | SL: {COMBINED_STOP_LOSS}% | TP: {COMBINED_TAKE_PROFIT}%")
        return
    
    # Check total liquidations before attempting any entries
    total_liquidations = get_recent_liquidations()
    if total_liquidations < LIQUIDATION_THRESHOLD:
        print(f"{Fore.YELLOW}⚠️ Total liquidations (${total_liquidations:,.2f}) below threshold (${LIQUIDATION_THRESHOLD:,.2f})")
        print(f"{Fore.YELLOW}🚫 Skipping entries until more liquidation activity")
        return
    
    print(f"{Fore.GREEN}✅ Total liquidations (${total_liquidations:,.2f}) above threshold - proceeding with entries")
    
    # If we have one position, only try to enter the opposite type
    if len(current_positions) == 1:
        current_pos = current_positions[0]
        print(f"{Fore.YELLOW}🔍 Have one {'LONG' if current_pos['is_long'] else 'SHORT'} position, looking for opposite...")
        
        # If we're in a long, only try to enter short and vice versa
        if current_pos['is_long']:
            if best_short is None or best_short['symbol'] == current_pos['symbol']:
                print(f"{Fore.YELLOW}⚠️ No valid short opportunity found, monitoring current position")
                return
            try_enter_position(best_short, False)
        else:
            if best_long is None or best_long['symbol'] == current_pos['symbol']:
                print(f"{Fore.YELLOW}⚠️ No valid long opportunity found, monitoring current position")
                return
            try_enter_position(best_long, True)
        return
    
    # If we have no positions, try to enter both if available
    if len(current_positions) == 0:
        print(f"{Fore.GREEN}🎯 No current positions, attempting to enter both trades...")
        if best_long is not None:
            try_enter_position(best_long, True)
            time.sleep(2)  # Add delay between entries
        if best_short is not None:
            try_enter_position(best_short, False)
        return

def try_enter_position(position, is_long):
    """Helper function to try entering a position"""
    if position is None:
        return
        
    try:
        symbol_str = str(position['symbol'])
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"{Fore.CYAN}🎯 Attempting to enter {'LONG' if is_long else 'SHORT'} position for {symbol_str}")
        
        # Cancel any existing orders first
        print(f"{Fore.YELLOW}🗑️ Canceling existing orders for {symbol_str}...")
        n.cancel_symbol_orders(account, symbol_str)
        time.sleep(1)  # Increased delay after cancel
        
        # Get current price with detailed debugging
        print(f"\n{Fore.CYAN}📊 Fetching current prices for {symbol_str}...")
        ask, bid, _ = get_price_safely(symbol_str)
        
        if None in (ask, bid):
            print(f"{Fore.RED}❌ Invalid price data for {symbol_str}:")
            print(f"{Fore.RED}Ask: {ask}")
            print(f"{Fore.RED}Bid: {bid}")
            return
            
        time.sleep(1)  # Delay between API calls
        
        # Get leverage and position size with debugging
        print(f"\n{Fore.CYAN}⚙️ Adjusting leverage for {symbol_str}...")
        lev, pos_size = adjust_leverage_safely(symbol_str, POSITION_SIZE_USD, LEVERAGE, account)
        
        if None in (lev, pos_size):
            print(f"{Fore.RED}❌ Failed to adjust leverage for {symbol_str}")
            print(f"{Fore.RED}Leverage: {lev}")
            print(f"{Fore.RED}Position Size: {pos_size}")
            return
            
        time.sleep(1)  # Delay between API calls
        
        # Debug prints
        print(f"\n{Fore.CYAN}🔍 ORDER DETAILS:")
        print(f"Symbol: {symbol_str}")
        print(f"Direction: {'LONG 🚀' if is_long else 'SHORT 📉'}")
        print(f"Position Size: {pos_size}")
        print(f"Entry Price: ${bid if is_long else ask}")
        print(f"Leverage: {lev}x")
        
        # Place the order with retry logic
        entry_price = bid if is_long else ask
        print(f"\n{Fore.GREEN if is_long else Fore.RED}🚀 Moon Dev placing {'LONG' if is_long else 'SHORT'} order...")
        result = api_call_with_retry(n.limit_order, symbol_str, is_long, pos_size, entry_price, False, account)
        
        if result is None:
            print(f"{Fore.RED}❌ Failed to place order")
            return
            
        print(f"{Fore.GREEN}✅ Limit order placed successfully!")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error placing {'long' if is_long else 'short'} order: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        
    print(f"{Fore.YELLOW}⏳ Waiting 10 seconds to check fill... 🌙")
    time.sleep(10)

def check_pnl_and_close_if_needed():
    """Check combined PnL and close positions if TP/SL hit"""
    print(f"\n{Fore.CYAN}{'='*100}")
    print(f"{Fore.CYAN}🔍 MOON DEV CHECKING COMBINED PNL FIRST")
    print(f"{Fore.CYAN}{'='*100}")
    
    total_pnl = 0
    current_positions = []
    
    # Get all current positions first
    for symbol in TOKENS_TO_ANALYZE:
        try:
            positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = get_position_safely(symbol, account)
            if im_in_pos:
                current_positions.append({
                    'symbol': symbol,
                    'size': pos_size,
                    'is_long': is_long,
                    'pnl': pnl_perc
                })
                total_pnl += pnl_perc
                direction = "LONG 🚀" if is_long else "SHORT 📉"
                print(f"{Fore.YELLOW}Active position: {direction} {symbol}, Size={pos_size}, PnL={pnl_perc:.2f}%")
        except Exception as e:
            print(f"{Fore.RED}❌ Error checking position for {symbol}: {str(e)}")
            continue
        time.sleep(1)
    
    if not current_positions:
        print(f"{Fore.YELLOW}No active positions to check")
        return False
        
    print(f"\n{Fore.YELLOW}💰 Total Combined PnL: {total_pnl:.2f}%")
    print(f"{Fore.YELLOW}📊 Stop Loss: {COMBINED_STOP_LOSS}% | Take Profit: {COMBINED_TAKE_PROFIT}%")
    
    # Check if we need to close positions
    if total_pnl <= COMBINED_STOP_LOSS:
        print(f"{Fore.RED}🛑 Stop Loss hit! Combined PnL ({total_pnl:.2f}%) <= Stop Loss ({COMBINED_STOP_LOSS}%)")
        print(f"{Fore.RED}🔄 Closing all positions safely...")
        success = close_positions_safely(account)
        if success:
            print(f"{Fore.GREEN}✅ Successfully closed all positions on Stop Loss")
        else:
            print(f"{Fore.RED}❌ Failed to close positions on Stop Loss!")
        return True
        
    elif total_pnl >= COMBINED_TAKE_PROFIT:
        print(f"{Fore.GREEN}🎯 Take Profit hit! Combined PnL ({total_pnl:.2f}%) >= Take Profit ({COMBINED_TAKE_PROFIT}%)")
        print(f"{Fore.GREEN}🔄 Closing all positions safely...")
        success = close_positions_safely(account)
        if success:
            print(f"{Fore.GREEN}✅ Successfully closed all positions on Take Profit")
        else:
            print(f"{Fore.RED}❌ Failed to close positions on Take Profit!")
        return True
    
    print(f"{Fore.GREEN}✅ PnL within bounds, continuing with analysis...")
    return False

def main():
    """Main function to run the liquidation analysis"""
    try:
        print(f"\n{Fore.CYAN}{'='*100}")
        print(f"{Fore.CYAN}🌙 Moon Dev's Liquidation Analysis Bot Starting... 🚀")
        print(f"{Fore.CYAN}{'='*100}")
        
        # First thing: Check PnL and close positions if needed
        if check_pnl_and_close_if_needed():
            print(f"{Fore.YELLOW}Positions closed on TP/SL - skipping analysis for this cycle")
            return
        
        # Add delay before continuing with analysis
        time.sleep(random.uniform(0.5, 1.5))
        
        # Continue with regular analysis only if we didn't close positions
        print(f"\n{Fore.CYAN}{'='*100}")
        print(f"{Fore.CYAN}🔍 CONTINUING WITH LIQUIDATION ANALYSIS")
        print(f"{Fore.CYAN}{'='*100}")
        
        # Fetch positions data
        positions_df = fetch_positions_from_api()
        
        if positions_df is not None:
            # Process positions
            processed_df = process_positions(positions_df)
            
            if not processed_df.empty:
                # Display liquidation risk analysis
                display_liquidation_risk(processed_df)
            else:
                print(f"{Fore.RED}⚠️ No positions found after filtering!")
        else:
            print(f"{Fore.RED}⚠️ Could not fetch positions data!")
        
        # Always print final PnL status
        print_final_status()
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error in main function: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        time.sleep(5)  # Wait before next cycle on error

def print_final_status():
    """Print final PnL status with safe position checking"""
    print(f"\n{Fore.CYAN}{'='*100}")
    print(f"{Fore.CYAN}🌙 MOON DEV'S CURRENT POSITION STATUS 🌙")
    print(f"{Fore.CYAN}{'='*100}")
    
    total_pnl = 0
    active_positions = []
    
    for symbol in TOKENS_TO_ANALYZE:
        try:
            positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = get_position_safely(symbol, account)
            if im_in_pos:
                total_pnl += pnl_perc
                direction = "LONG 🚀" if is_long else "SHORT 📉"
                active_positions.append(f"{direction} {symbol}: Size={pos_size}, PnL={pnl_perc:.2f}%")
        except Exception as e:
            print(f"{Fore.RED}❌ Error checking final status for {symbol}: {str(e)}")
            continue
        
        time.sleep(0.5)  # Small delay between position checks
    
    if active_positions:
        for pos in active_positions:
            print(f"{Fore.YELLOW}{pos}")
        print(f"\n{Fore.MAGENTA}💰 Total Combined PnL: {total_pnl:.2f}%")
        print(f"{Fore.CYAN}📊 Stop Loss: {COMBINED_STOP_LOSS}% | Take Profit: {COMBINED_TAKE_PROFIT}%")
    else:
        print(f"{Fore.YELLOW}🔍 No active positions found")
    
    print(f"{Fore.CYAN}{'='*100}\n")

if __name__ == "__main__":
    print(f"{Fore.CYAN}🌙 Moon Dev's Liquidation Analysis Bot Starting... 🚀")
    print(f"{Fore.CYAN}Running initial analysis...")
    main()
    
    print(f"{Fore.CYAN}Setting up schedule to run every 30 seconds...")
    schedule.every(30).seconds.do(main)
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print(f"{Fore.YELLOW}⚠️ Bot stopped by user")
            break
        except Exception as e:
            print(f"{Fore.RED}❌ Error in main loop: {str(e)}")
            print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
            time.sleep(10)  # Increased wait time on error
            continue