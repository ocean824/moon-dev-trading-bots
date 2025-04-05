# ===== MOON DEV XRP LIQUIDATION HUNTER =====
# Main configuration constant - adjust this to change the liquidation threshold
LIQUIDATION_THRESHOLD_PERCENT = 20  # Percentage price move to analyze for potential pending liquidations

'''
Everyone talks about cults, but they leave out the original cult 
The XRP army is one of the greatest collaborations of people who believe in something. 
This gives me an opportunity to build a trading bot that is trading against emotional people 
Most people who are trading by hand are emotional regardless, but these XRP people, they truly believe up only 
So I'm going to build a bot that trades up and down based on liquidations. 

I've gotten to this point, this to a point where we can change the liquidation threshold above and then get a bias for the bot. 
Now that we have a bias for the bot, the next thing I would look for is the amount of liquidations to enter and take over their position. 
So if I wanted to go long, I would wait for some longs to get liquidated and then enter. 
'''

import sys
import os
import time
import schedule
import json
import requests
import pandas as pd
import numpy as np
import traceback
from termcolor import colored
import colorama
from colorama import Fore, Back, Style
from datetime import datetime, timedelta
import pytz
from eth_account.signers.local import LocalAccount
import eth_account
from dotenv import load_dotenv
import uuid
import pathlib
import io
import contextlib

# Add the parent directory to the Python path so we can import modules from there
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

# Import local modules
import nice_funcs as n
from api import MoonDevAPI

# ===== QUIET WRAPPERS =====
def quiet_pnl_close(symbol, target, max_loss, account):
    """
    Wrapper for pnl_close that suppresses verbose output.
    """
    # Capture stdout to prevent printing
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout
    
    # Call the original function
    result = n.pnl_close(symbol, target, max_loss, account)
    
    # Reset stdout
    sys.stdout = old_stdout
    
    # Extract only the results we need from the captured output
    captured_output = new_stdout.getvalue()
    
    # Check if position was closed
    if "closing position WIN" in captured_output:
        print(f"{Fore.GREEN}✅ Position closed for profit target reached ({target}%)")
        return True
    elif "closing position LOSS" in captured_output:
        print(f"{Fore.RED}⛔ Position closed for stop loss reached ({max_loss}%)")
        return True
    else:
        return False

def quiet_get_position(symbol, account):
    """
    Wrapper for get_position that suppresses verbose output.
    """
    # Capture stdout to prevent printing
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout
    
    # Call the original function
    result = n.get_position(symbol, account)
    
    # Reset stdout
    sys.stdout = old_stdout
    
    return result

# Initialize colorama for terminal colors
colorama.init(autoreset=True)

# Load environment variables from .env file
load_dotenv()

# Get the Hyperliquid key from environment variables
HYPER_LIQUID_KEY = os.getenv('HYPER_LIQUID_KEY')
#HYPER_LIQUID_KEY = os.getenv('HYPER_LIQUID_KEY_COLLECTOR')

# ===== CONFIGURATION =====
# Symbol to trade
symbol = 'XRP'  # Changed to XRP
LEVERAGE = 10     # Leverage to use for trading
POSITION_SIZE_USD = 10  # Position size in USD

# Range validation settings
RANGE_TIMEFRAME = '5m'  # Timeframe for range calculation
RANGE_BARS = 20  # Number of bars to calculate range from
RANGE_THIRD = 0.333  # One-third of the range for validation

# Constants
LIQUIDATION_LOOKBACK_MINUTES = 5  # Time period to look back for liquidations
LIQUIDATION_TRIGGER_AMOUNT = 100000  # $500k trigger amount for liquidations

# Take profit and stop loss settings
TAKE_PROFIT_PERCENT = 10  # Take profit percentage
STOP_LOSS_PERCENT = -19  # Stop loss percentage

# InBalance direction check setting
ENABLE_IMBALANCE_CHECK = False  # Set to True to enable InBalance direction checks, False to disable

# Market hours restriction setting
ENABLE_MARKET_HOURS = False  # Set to True to only allow trading during market hours (9:30 AM - 4:30 PM Eastern), False to allow 24/7 trading

# Add these constants near the top with other constants
# ===== CONFIGURATION =====
MIN_POSITION_VALUE = 25000  # Only track positions with value >= $25,000
TOP_N_POSITIONS = 25  # Number of top positions to display
HIGHLIGHT_THRESHOLD = 1000000  # $1 million
TOKENS_TO_ANALYZE = ['XRP']  # Changed to only analyze XRP

# Time-based profit tracking settings
PROFIT_PER_MINUTE_TARGET = 1000  # Take profit at 0.2% profit per minute
PROFIT_PER_MINUTE_STOP = -2000  # Stop loss at -1.0% profit per minute
MIN_TIME_IN_POSITION = 1  # Minimum minutes to hold position (avoid premature exit)
MAX_TIME_IN_POSITION = 120000  # Maximum minutes to hold position (force exit)

# Data storage for position tracking
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
POSITIONS_FILE = os.path.join(DATA_DIR, "xrp_position_history.csv")  # Changed to XRP specific file

# Global variable to track position entry time
position_entry_time = None
position_entry_value = None
position_entry_price = None

# Initialize account
account = LocalAccount = eth_account.Account.from_key(HYPER_LIQUID_KEY)

# Initialize API
api = MoonDevAPI()

def get_spot_position_usd(address):
    """
    Get the USDC balance for a given address
    """
    try:
        # Get token balances using direct API call
        url = "https://api.hyperliquid.xyz/info"
        headers = {"Content-Type": "application/json"}
        balance_response = requests.post(url, headers=headers, json={
            "type": "spotClearinghouseState",
            "user": address
        })
        
        balance_data = balance_response.json()
        
        # Find USDC balance
        usdc_balance = 0
        for balance in balance_data['balances']:
            if balance['coin'] == 'USDC':
                usdc_balance = float(balance['total'])
                break
        
        return usdc_balance
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error getting USDC spot balance: {str(e)}")
        return 0

# Trading recommendation state
trading_bias = None  # 'long' or 'short'
recommendation_text = "Waiting for initial analysis..."
last_analysis_time = None
ANALYSIS_INTERVAL_MINUTES = 1  # How often to refresh the bias analysis

# DataFrame to track positions
positions_df = None

def init_positions_tracker():
    """Initialize the positions tracker and load existing data"""
    global positions_df
    
    # Create data directory if it doesn't exist
    pathlib.Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    
    # If positions file exists, load it
    if os.path.exists(POSITIONS_FILE):
        try:
            positions_df = pd.read_csv(POSITIONS_FILE)
            # Convert string timestamps back to datetime objects
            positions_df['entry_time'] = pd.to_datetime(positions_df['entry_time'])
            positions_df['exit_time'] = pd.to_datetime(positions_df['exit_time'])
            print(f"{Fore.GREEN}🗄️ Loaded {len(positions_df)} XRP position records from {POSITIONS_FILE}")
        except Exception as e:
            print(f"{Fore.RED}❌ Error loading positions file: {str(e)}")
            positions_df = create_empty_positions_df()
    else:
        positions_df = create_empty_positions_df()
        save_positions()
        print(f"{Fore.GREEN}📝 Created new XRP positions tracker file at {POSITIONS_FILE}")

def create_empty_positions_df():
    """Create an empty positions DataFrame with the correct columns"""
    return pd.DataFrame(columns=[
        'position_id',         # Unique ID for the position
        'symbol',              # Trading symbol (XRP)
        'side',                # 'long' or 'short'
        'entry_time',          # When position was opened
        'exit_time',           # When position was closed (NaT if still open)
        'entry_price',         # Entry price
        'exit_price',          # Exit price (NaN if still open)
        'size',                # Position size
        'leverage',            # Leverage used
        'entry_value_usd',     # Position value in USD at entry
        'exit_value_usd',      # Position value in USD at exit (NaN if still open)
        'pnl_percent',         # PnL percentage (NaN if still open)
        'pnl_usd',             # PnL in USD (NaN if still open)
        'time_in_position_min',# Time in position in minutes (NaN if still open)
        'ppm',                 # Profit per minute (NaN if still open)
        'is_active'            # Whether position is still active
    ])

def save_positions():
    """Save positions DataFrame to CSV file"""
    try:
        positions_df.to_csv(POSITIONS_FILE, index=False)
        print(f"{Fore.GREEN}💾 Saved XRP positions data to {POSITIONS_FILE}")
    except Exception as e:
        print(f"{Fore.RED}❌ Error saving positions file: {str(e)}")

def get_active_position(symbol_to_check=None):
    """Get the currently active position for XRP"""
    global positions_df
    
    if positions_df is None:
        init_positions_tracker()
    
    # Filter for active positions
    active_positions = positions_df[positions_df['is_active'] == True]
    
    # If symbol is specified, filter for that symbol
    if symbol_to_check:
        active_positions = active_positions[active_positions['symbol'] == symbol_to_check]
    
    if len(active_positions) > 0:
        return active_positions.iloc[0]
    else:
        return None

def record_position_entry(symbol, side, entry_price, size, leverage, entry_value_usd):
    """Record a new XRP position entry"""
    global positions_df
    
    if positions_df is None:
        init_positions_tracker()
    
    # Create a new position record
    new_position = {
        'position_id': str(uuid.uuid4()),
        'symbol': symbol,
        'side': side,
        'entry_time': datetime.now(),
        'exit_time': pd.NaT,
        'entry_price': entry_price,
        'exit_price': np.nan,
        'size': size,
        'leverage': leverage,
        'entry_value_usd': entry_value_usd,
        'exit_value_usd': np.nan,
        'pnl_percent': np.nan,
        'pnl_usd': np.nan,
        'time_in_position_min': np.nan,
        'ppm': np.nan,
        'is_active': True
    }
    
    # Add to DataFrame
    positions_df = pd.concat([positions_df, pd.DataFrame([new_position])], ignore_index=True)
    
    # Save to file
    save_positions()
    
    print(f"{Fore.GREEN}📊 Recorded new XRP position entry: {'LONG' if side == 'long' else 'SHORT'} {size} @ ${entry_price}")
    return new_position

def record_position_exit(position_id, exit_price, pnl_percent, pnl_usd):
    """Record an XRP position exit"""
    global positions_df
    
    if positions_df is None:
        init_positions_tracker()
    
    # Find the position by ID
    if position_id not in positions_df['position_id'].values:
        print(f"{Fore.RED}❌ Position ID not found: {position_id}")
        return False
    
    # Get index of position
    idx = positions_df[positions_df['position_id'] == position_id].index[0]
    
    # Update position data
    positions_df.loc[idx, 'exit_time'] = datetime.now()
    positions_df.loc[idx, 'exit_price'] = exit_price
    positions_df.loc[idx, 'pnl_percent'] = pnl_percent
    positions_df.loc[idx, 'pnl_usd'] = pnl_usd
    positions_df.loc[idx, 'is_active'] = False
    
    # Calculate time in position
    entry_time = positions_df.loc[idx, 'entry_time']
    exit_time = positions_df.loc[idx, 'exit_time']
    time_in_position_min = (exit_time - entry_time).total_seconds() / 60
    positions_df.loc[idx, 'time_in_position_min'] = time_in_position_min
    
    # Calculate profit per minute
    if time_in_position_min > 0:
        positions_df.loc[idx, 'ppm'] = pnl_percent / time_in_position_min
    
    # Save to file
    save_positions()
    
    print(f"{Fore.GREEN}📊 Recorded XRP position exit: {'LONG' if positions_df.loc[idx, 'side'] == 'long' else 'SHORT'}")
    print(f"{Fore.GREEN}⏱️ Time in position: {time_in_position_min:.2f} minutes")
    print(f"{Fore.GREEN}💰 PnL: {pnl_percent:.2f}% (${pnl_usd:.2f})")
    
    if time_in_position_min > 0:
        print(f"{Fore.GREEN}🚀 Profit Per Minute: {positions_df.loc[idx, 'ppm']:.4f}%/min")
    
    return True

def analyze_market():
    """
    Analyze market conditions and set trading bias based on XRP liquidation risk analysis
    """
    global trading_bias, recommendation_text, last_analysis_time
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'='*25} 🔍 XRP MARKET ANALYSIS 🔍 {'='*25}")
    print(f"{Fore.CYAN}{'='*80}")
    
    try:
        # Fetch positions data from Moon Dev API
        print(f"{Fore.YELLOW}🌙 Moon Dev API: Fetching XRP positions data...")
        positions_df = api.get_positions_hlp()
        
        if positions_df is None or positions_df.empty:
            print(f"{Fore.RED}❌ Failed to get positions data from API")
            return False
        
        print(f"{Fore.GREEN}✅ Successfully fetched {len(positions_df)} positions")
        
        # Filter out small positions
        positions_df = positions_df[positions_df['position_value'] >= MIN_POSITION_VALUE].copy()
        print(f"{Fore.GREEN}📊 Found {len(positions_df)} positions after filtering (min value: ${MIN_POSITION_VALUE:,})")
        
        # Convert numeric columns
        numeric_cols = ['entry_price', 'position_value', 'unrealized_pnl', 'liquidation_price', 'leverage']
        for col in numeric_cols:
            if col in positions_df.columns:
                positions_df[col] = pd.to_numeric(positions_df[col], errors='coerce')
        
        # Validate and correct position types
        valid_liq_df = positions_df[positions_df['liquidation_price'] > 0].copy()
        if not valid_liq_df.empty:
            valid_liq_df['is_long_corrected'] = valid_liq_df['liquidation_price'] < valid_liq_df['entry_price']
            valid_liq_df['is_long'] = valid_liq_df['is_long_corrected']
            positions_df.loc[valid_liq_df.index, 'is_long'] = valid_liq_df['is_long']
        
        # Get current XRP price
        current_price = n.get_current_price(symbol)
        print(f"{Fore.YELLOW}💰 Current XRP price: ${current_price:,.2f}")
        
        # Display top 30 positions closest to liquidation
        print(f"\n{Fore.CYAN}{'='*120}")
        print(f"{Fore.CYAN}{'='*35} 🚀 TOP 30 XRP POSITIONS CLOSEST TO LIQUIDATION 💥 {'='*35}")
        print(f"{Fore.CYAN}{'='*120}")

        # Print column names for debugging
        print(f"{Fore.YELLOW}📊 Positions data columns: {positions_df.columns.tolist()}")
        
        # Filter for XRP positions only
        xrp_positions = positions_df[positions_df['coin'] == 'XRP'].copy()
        print(f"{Fore.GREEN}📊 Found {len(xrp_positions)} XRP positions")
        
        # Add current price to positions
        xrp_positions['current_price'] = current_price
        
        # Calculate distance to liquidation
        xrp_positions['distance_to_liq_pct'] = np.where(
            xrp_positions['is_long'],
            abs((xrp_positions['current_price'] - xrp_positions['liquidation_price']) / xrp_positions['current_price'] * 100),
            abs((xrp_positions['liquidation_price'] - xrp_positions['current_price']) / xrp_positions['current_price'] * 100)
        )
        
        # Get top 30 longs and shorts closest to liquidation (using nsmallest instead of nlargest)
        top_longs = xrp_positions[xrp_positions['is_long']].nsmallest(30, 'distance_to_liq_pct')
        top_shorts = xrp_positions[~xrp_positions['is_long']].nsmallest(30, 'distance_to_liq_pct')
        
        print(f"\n{Fore.GREEN}📈 TOP 30 LONG POSITIONS CLOSEST TO LIQUIDATION:")
        print(f"{Fore.GREEN}{'='*120}")
        
        # Calculate total long positions
        total_long_value = top_longs['position_value'].sum()
        max_long_distance = top_longs['distance_to_liq_pct'].max() if not top_longs.empty else 0
        
        # Group positions by every 10 for highlighting
        for idx, pos in top_longs.iterrows():
            # Highlight large positions in yellow
            if pos['position_value'] >= HIGHLIGHT_THRESHOLD:
                print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}#{idx+1} XRP ${pos['position_value']:,.2f} | Entry: ${pos['entry_price']:.2f} | Liq: ${pos['liquidation_price']:.2f} | Current: ${pos['current_price']:.2f} | Distance: {pos['distance_to_liq_pct']:.2f}% | Leverage: {pos['leverage']}x{Style.RESET_ALL}")
                print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}   Address: {pos['address']}{Style.RESET_ALL}")
            else:
                print(f"#{idx+1} XRP ${pos['position_value']:,.2f} | Entry: ${pos['entry_price']:.2f} | Liq: ${pos['liquidation_price']:.2f} | Current: ${pos['current_price']:.2f} | Distance: {pos['distance_to_liq_pct']:.2f}% | Leverage: {pos['leverage']}x")
                print(f"   Address: {pos['address']}")
        
        print(f"\n{Fore.GREEN}📊 AGGREGATE (1-30): Total Long Positions: ${total_long_value:,.2f} | All Liquidated Within: {max_long_distance:.2f}%")
        print(f"{Fore.GREEN}{'-'*120}")
        
        print(f"\n{Fore.RED}📉 TOP 30 SHORT POSITIONS CLOSEST TO LIQUIDATION:")
        print(f"{Fore.RED}{'='*120}")
        
        # Calculate total short positions
        total_short_value = top_shorts['position_value'].sum()
        max_short_distance = top_shorts['distance_to_liq_pct'].max() if not top_shorts.empty else 0
        
        # Group positions by every 10 for highlighting
        for idx, pos in top_shorts.iterrows():
            # Highlight large positions in yellow
            if pos['position_value'] >= HIGHLIGHT_THRESHOLD:
                print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}#{idx+1} XRP ${pos['position_value']:,.2f} | Entry: ${pos['entry_price']:.2f} | Liq: ${pos['liquidation_price']:.2f} | Current: ${pos['current_price']:.2f} | Distance: {pos['distance_to_liq_pct']:.2f}% | Leverage: {pos['leverage']}x{Style.RESET_ALL}")
                print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}   Address: {pos['address']}{Style.RESET_ALL}")
            else:
                print(f"#{idx+1} XRP ${pos['position_value']:,.2f} | Entry: ${pos['entry_price']:.2f} | Liq: ${pos['liquidation_price']:.2f} | Current: ${pos['current_price']:.2f} | Distance: {pos['distance_to_liq_pct']:.2f}% | Leverage: {pos['leverage']}x")
                print(f"   Address: {pos['address']}")
        
        print(f"\n{Fore.RED}📊 AGGREGATE (1-30): Total Short Positions: ${total_short_value:,.2f} | All Liquidated Within: {max_short_distance:.2f}%")
        print(f"{Fore.RED}{'-'*120}")
        
        print(f"{Fore.CYAN}{'='*120}")
        
        # Now we can safely use the distance_to_liq_pct column since it's been created
        long_liquidations = xrp_positions[
            (xrp_positions['is_long']) & 
            (xrp_positions['distance_to_liq_pct'] <= LIQUIDATION_THRESHOLD_PERCENT)
        ]['position_value'].sum()
        
        short_liquidations = xrp_positions[
            (~xrp_positions['is_long']) & 
            (xrp_positions['distance_to_liq_pct'] <= LIQUIDATION_THRESHOLD_PERCENT)
        ]['position_value'].sum()
        
        # Generate trading recommendations
        print(f"\n{Fore.CYAN}{'='*120}")
        print(f"{Fore.CYAN}{'='*35} 🚀 XRP TRADING RECOMMENDATIONS 🚀 {'='*35}")
        print(f"{Fore.CYAN}{'='*120}")
        
        # Overall market recommendation based on current threshold
        if long_liquidations == 0 and short_liquidations == 0:
            trading_bias = None
            recommendation_text = f"NEUTRAL XRP (No liquidations within {LIQUIDATION_THRESHOLD_PERCENT}% move)"
            print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}MARKET RECOMMENDATION: {recommendation_text}{Style.RESET_ALL}")
        elif long_liquidations > short_liquidations:
            trading_bias = 'short'
            recommendation_text = f"SHORT XRP (${long_liquidations:,.2f} long liquidations vs ${short_liquidations:,.2f} short liquidations within a {LIQUIDATION_THRESHOLD_PERCENT}% move)"
            print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}MARKET RECOMMENDATION: {recommendation_text}{Style.RESET_ALL}")
        else:
            trading_bias = 'long'
            recommendation_text = f"LONG XRP (${short_liquidations:,.2f} short liquidations vs ${long_liquidations:,.2f} long liquidations within a {LIQUIDATION_THRESHOLD_PERCENT}% move)"
            print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}MARKET RECOMMENDATION: {recommendation_text}{Style.RESET_ALL}")
        
        # Update last analysis time
        last_analysis_time = datetime.now()
        
        # Display top 3 closest liquidations with USDC balances
        print(f"\n{Fore.CYAN}{'='*120}")
        print(f"{Fore.CYAN}{'='*35} 🚨 XRP POSITIONS CLOSEST TO LIQUIDATION (>$2,000,000) 🚨 {'='*35}")
        print(f"{Fore.CYAN}{'='*120}")
        
        # Get top 2 longs and shorts closest to liquidation
        top_2_longs = xrp_positions[xrp_positions['is_long']].nsmallest(2, 'distance_to_liq_pct')
        top_2_shorts = xrp_positions[~xrp_positions['is_long']].nsmallest(2, 'distance_to_liq_pct')
        
        # Print header
        print(f"{Fore.CYAN}Position   | Coin |             Value |        Entry |          Liq |  Distance | Leverage |                                    Address |         USDC")
        print(f"{Fore.CYAN}-----------+------+-------------------+--------------+--------------+-----------+----------+--------------------------------------------+-------------")
        
        # Print long positions
        for idx, pos in top_2_longs.iterrows():
            # Get USDC balance for this address
            usdc_balance = get_spot_position_usd(pos['address'])
            
            # Format the position row
            position_type = f"LONG #{idx+1}"
            print(f"{Fore.GREEN}{position_type:<10} | {pos['coin']:<4} | ${pos['position_value']:>15,.2f} | ${pos['entry_price']:.2f} | ${pos['liquidation_price']:.2f} | {pos['distance_to_liq_pct']:>7.2f}% | {pos['leverage']:>6}x | {pos['address']:<40} | ${usdc_balance:>10,.2f}")
        
        # Print short positions
        for idx, pos in top_2_shorts.iterrows():
            # Get USDC balance for this address
            usdc_balance = get_spot_position_usd(pos['address'])
            
            # Format the position row
            position_type = f"SHORT #{idx+1}"
            print(f"{Fore.RED}{position_type:<10} | {pos['coin']:<4} | ${pos['position_value']:>15,.2f} | ${pos['entry_price']:.2f} | ${pos['liquidation_price']:.2f} | {pos['distance_to_liq_pct']:>7.2f}% | {pos['leverage']:>6}x | {pos['address']:<40} | ${usdc_balance:>10,.2f}")
        
        print(f"{Fore.CYAN}{'='*120}")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error during market analysis: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return False

def get_recent_liquidations():
    """
    Get recent XRP liquidations from Moon Dev API
    """
    try:
        # Fetch liquidation data
        liquidations = api.get_liquidation_data(limit=1000)
        if liquidations is None:
            print(f"{Fore.RED}❌ Failed to fetch liquidation data")
            return None, 0, 0
        
        # Print column names for debugging
        print(f"\n{Fore.CYAN}📊 Liquidation data columns: {liquidations.columns.tolist()}")
        
        # Filter to XRP only
        xrp_liquidations = liquidations[liquidations.iloc[:, 0] == symbol]
        
        if xrp_liquidations.empty:
            print(f"{Fore.YELLOW}⚠️ No liquidations found for XRP")
            return None, 0, 0
        
        # Convert to milliseconds timestamp
        current_time_ms = int(datetime.now().timestamp() * 1000)
        cutoff_time_ms = current_time_ms - (LIQUIDATION_LOOKBACK_MINUTES * 60 * 1000)
        
        # Filter liquidations within the lookback period using the timestamp column (index 10)
        recent_liquidations = xrp_liquidations[xrp_liquidations.iloc[:, 10].astype(float) >= cutoff_time_ms]
        
        if recent_liquidations.empty:
            return None, 0, 0
        
        # Separate long and short liquidations
        # Long liquidations have side == "SELL", Short liquidations have side == "BUY"
        long_liqs = recent_liquidations[recent_liquidations.iloc[:, 1] == "SELL"]
        short_liqs = recent_liquidations[recent_liquidations.iloc[:, 1] == "BUY"]
        
        # Calculate totals
        long_liq_amount = long_liqs.iloc[:, 11].astype(float).sum() if not long_liqs.empty else 0
        short_liq_amount = short_liqs.iloc[:, 11].astype(float).sum() if not short_liqs.empty else 0
        
        return recent_liquidations, long_liq_amount, short_liq_amount
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error getting liquidations: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
        return None, 0, 0

def should_enter_trade(long_liq_amount, short_liq_amount):
    """
    Determine if we should enter an XRP trade based on liquidation amounts and trading bias
    """
    if trading_bias is None:
        print(f"{Fore.YELLOW}⚠️ No trading bias set yet - run market analysis first")
        return False, "No trading bias set"
    
    # If our bias is short, we want to enter when SHORT liquidations exceed our threshold
    # This gives us a better entry as shorts are forced to cover, causing temporary spikes
    if trading_bias == 'short' and short_liq_amount >= LIQUIDATION_TRIGGER_AMOUNT:
        return True, f"ENTER SHORT - Short liquidations (${short_liq_amount:,.2f}) exceeding threshold (${LIQUIDATION_TRIGGER_AMOUNT:,.2f})"
    
    # If our bias is long, we want to enter when LONG liquidations exceed our threshold
    # This gives us a better entry as longs are forced to sell, causing temporary dips
    if trading_bias == 'long' and long_liq_amount >= LIQUIDATION_TRIGGER_AMOUNT:
        return True, f"ENTER LONG - Long liquidations (${long_liq_amount:,.2f}) exceeding threshold (${LIQUIDATION_TRIGGER_AMOUNT:,.2f})"
    
    # Be specific about which type of liquidations we're waiting for
    if trading_bias == 'short':
        return False, f"Waiting for SHORT liquidations of ${LIQUIDATION_TRIGGER_AMOUNT:,.2f} or more to enter SHORT position"
    else:
        return False, f"Waiting for LONG liquidations of ${LIQUIDATION_TRIGGER_AMOUNT:,.2f} or more to enter LONG position"

def ppm_close(symbol, target_ppm, stop_ppm, min_time, max_time, account):
    """
    Close XRP position based on Profit Per Minute (PPM) metrics
    """
    print(f'{Fore.CYAN}🕒 Checking time-based PnL conditions...')
    
    # Get current position info
    positions, im_in_pos, pos_size, pos_sym, current_price, pnl_perc, is_long = quiet_get_position(symbol, account)
    
    if not im_in_pos:
        print(f'{Fore.YELLOW}⚠️ No active position')
        return False
    
    # Get active position data from our tracker
    active_position = get_active_position(symbol)
    
    if active_position is None:
        print(f'{Fore.YELLOW}⚠️ No active position in tracker, but found one on exchange!')
        print(f'{Fore.YELLOW}⚠️ Recording position now with estimated entry time')
        
        # Record position with current time (approximate)
        side = 'long' if is_long else 'short'
        entry_value = abs(pos_size * current_price)
        record_position_entry(symbol, side, current_price, pos_size, LEVERAGE, entry_value)
        
        # Get the position again
        active_position = get_active_position(symbol)
        
        # Exit early as we just recorded it
        print(f'{Fore.YELLOW}⏱️ Position just recorded, will check PPM metrics on next cycle')
        return False
    
    # Calculate time in position
    current_time = datetime.now()
    elapsed_minutes = (current_time - active_position['entry_time']).total_seconds() / 60
    
    # Calculate profit per minute
    ppm = pnl_perc / elapsed_minutes if elapsed_minutes > 0 else 0
    
    # Print status in a highlighted box
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'='*30} 📊 XRP POSITION METRICS 📊 {'='*30}")
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}🪙 XRP {'LONG' if is_long else 'SHORT'} | Size: {pos_size} | Entry: ${active_position['entry_price']:.2f}")
    print(f"{Fore.CYAN}⏱️ Time in position: {elapsed_minutes:.2f} minutes")
    print(f"{Fore.MAGENTA}📊 Current PnL: {pnl_perc:.2f}%")
    print(f"{Fore.GREEN}🚀 Profit Per Minute: {ppm:.4f}%/min")
    print(f"{Fore.YELLOW}🎯 Target: {target_ppm}%/min | 🛑 Stop: {stop_ppm}%/min")
    print(f"{Fore.CYAN}{'='*80}\n")
    
    # Check if we need to close based on time or PPM metrics
    if elapsed_minutes >= max_time:
        print(f'{Fore.YELLOW}⏰ Max time in position reached ({max_time} minutes), closing position')
        n.kill_switch(pos_sym, account)
        
        # Record position exit
        position_id = active_position['position_id']
        pnl_usd = pnl_perc * active_position['entry_value_usd'] / 100
        record_position_exit(position_id, current_price, pnl_perc, pnl_usd)
        
        return True
    
    if elapsed_minutes < min_time:
        print(f'{Fore.YELLOW}⏱️ Position held for less than minimum time ({min_time} minutes), holding...')
        return False
    
    if ppm >= target_ppm:
        print(f'{Fore.GREEN}✨ Profit Per Minute target reached! PPM: {ppm:.4f}%/min, Target: {target_ppm}%/min')
        print(f'{Fore.GREEN}💰 Taking profit after {elapsed_minutes:.2f} minutes - Thanks Moon Dev! 🌙')
        n.kill_switch(pos_sym, account)
        
        # Record position exit
        position_id = active_position['position_id']
        pnl_usd = pnl_perc * active_position['entry_value_usd'] / 100
        record_position_exit(position_id, current_price, pnl_perc, pnl_usd)
        
        return True
    
    if ppm <= stop_ppm:
        print(f'{Fore.RED}🔥 Profit Per Minute below stop threshold! PPM: {ppm:.4f}%/min, Stop: {stop_ppm}%/min')
        print(f'{Fore.RED}🛑 Stopping loss after {elapsed_minutes:.2f} minutes')
        n.kill_switch(pos_sym, account)
        
        # Record position exit
        position_id = active_position['position_id']
        pnl_usd = pnl_perc * active_position['entry_value_usd'] / 100
        record_position_exit(position_id, current_price, pnl_perc, pnl_usd)
        
        return True
    
    print(f'{Fore.YELLOW}⏳ PPM metrics within acceptable range, maintaining position')
    return False

def is_price_in_valid_range(current_price, trading_bias):
    """
    Check if current XRP price is in a valid range for entry based on trading bias
    """
    try:
        # Get OHLCV data for range calculation
        snapshot_data = n.get_ohlcv2(symbol, RANGE_TIMEFRAME, RANGE_BARS)
        if not snapshot_data:
            print(f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}❌ Failed to get OHLCV data for range validation{Style.RESET_ALL}")
            return False
            
        # Process data into DataFrame
        df = n.process_data_to_df(snapshot_data)
        if df.empty:
            print(f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}❌ No data available for range validation{Style.RESET_ALL}")
            return False
            
        # Print DataFrame columns for debugging
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}📊 Available columns: {df.columns.tolist()}{Style.RESET_ALL}")
            
        # Convert price columns to numeric
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['low'] = pd.to_numeric(df['low'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        
        # Remove any rows with NaN values
        df = df.dropna(subset=['high', 'low', 'close', 'volume'])
        
        if df.empty:
            print(f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}❌ No valid price data after conversion{Style.RESET_ALL}")
            return False
            
        # Ensure we only use exactly RANGE_BARS bars
        if len(df) > RANGE_BARS:
            print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}⚠️ Got {len(df)} bars, limiting to {RANGE_BARS} bars for range calculation{Style.RESET_ALL}")
            df = df.tail(RANGE_BARS)
        elif len(df) < RANGE_BARS:
            print(f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}❌ Not enough bars for range calculation (got {len(df)}, need {RANGE_BARS}){Style.RESET_ALL}")
            return False
            
        # Calculate range
        highest_high = df['high'].max()
        lowest_low = df['low'].min()
        total_range = highest_high - lowest_low
        
        if total_range <= 0:
            print(f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}❌ Invalid range calculated (highest: {highest_high}, lowest: {lowest_low}){Style.RESET_ALL}")
            return False
        
        # Calculate price position in range
        price_position = (current_price - lowest_low) / total_range
        
        # Print range information with yellow background
        print(f"\n{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}{'='*80}")
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}📊 XRP RANGE VALIDATION")
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}{'='*80}")
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}🕒 Timeframe: {RANGE_TIMEFRAME} | Bars: {RANGE_BARS}")
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}💰 Current Price: ${current_price:,.2f}")
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}📈 Highest High: ${highest_high:,.2f}")
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}📉 Lowest Low: ${lowest_low:,.2f}")
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}📏 Total Range: ${total_range:,.2f}")
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}📊 Price Position in Range: {price_position:.2%}")
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}🎯 Trading Bias: {trading_bias.upper()}")
        
        # Print the actual bars data
        print(f"\n{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}📈 LAST {RANGE_BARS} BARS DATA:")
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}{'='*80}")
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}High | Low | Close | Volume")
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}{'-'*80}")
        
        # Sort by index in descending order (newest first)
        for idx in range(len(df)-1, -1, -1):
            row = df.iloc[idx]
            print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}${row['high']:,.2f} | ${row['low']:,.2f} | ${row['close']:,.2f} | {row['volume']:,.2f}")
        
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}{'='*80}")
        
        # Validate price position based on trading bias
        if trading_bias == 'short':
            is_valid = price_position >= 0.667  # Top third of range
            print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}✅ Valid for SHORT: {'Yes' if is_valid else 'No'} (Need to be in top third)")
        else:  # trading_bias == 'long'
            is_valid = price_position <= 0.333  # Bottom third of range
            print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}✅ Valid for LONG: {'Yes' if is_valid else 'No'} (Need to be in bottom third)")
        
        print(f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT}{'='*80}{Style.RESET_ALL}\n")
        
        return is_valid
        
    except Exception as e:
        print(f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}❌ Error in range validation: {str(e)}{Style.RESET_ALL}")
        print(f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}📋 Stack trace:\n{traceback.format_exc()}{Style.RESET_ALL}")
        return False

def bot():
    """
    Main bot function that runs on each cycle
    """
    try:
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}🌙 Moon Dev's XRP Liquidation Hunter - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 🚀")
        print(f"{Fore.CYAN}{'='*80}")
        
        # Display InBalance check status with clear background
        if ENABLE_IMBALANCE_CHECK:
            print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}🔄 INBALANCE CHECK: ENABLED - Bot will close positions when InBalance direction changes{Style.RESET_ALL}")
        else:
            print(f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}⛔ INBALANCE CHECK: DISABLED - Bot will not check InBalance direction for position exits{Style.RESET_ALL}")
            
        # Display market hours status with clear background
        if ENABLE_MARKET_HOURS:
            print(f"{Back.GREEN}{Fore.BLACK}{Style.BRIGHT}⏰ MARKET HOURS: ENABLED - Bot will only trade during 9:30 AM - 4:30 PM Eastern{Style.RESET_ALL}")
        else:
            print(f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}🌐 MARKET HOURS: DISABLED - Bot will trade 24/7{Style.RESET_ALL}")
        
        # First action: Check for existing positions and close if profit/loss targets hit
        print(f"\n{Fore.CYAN}🔍 Checking for existing XRP positions...")
        positions, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long = quiet_get_position(symbol, account)
        
        # Get active position from our tracker
        active_position = get_active_position(symbol)
        
        # If we're in a position but don't have it in our tracker, add it
        if im_in_pos and active_position is None:
            side = 'long' if is_long else 'short'
            entry_value = abs(mypos_size * entry_px)
            record_position_entry(symbol, side, entry_px, mypos_size, LEVERAGE, entry_value)
            active_position = get_active_position(symbol)
        
        if im_in_pos:
            print(f"{Fore.GREEN}📈 In XRP position, checking PnL for close conditions...")
            
            # First check time-based PPM close conditions
            ppm_closed = ppm_close(symbol, 
                                   PROFIT_PER_MINUTE_TARGET, 
                                   PROFIT_PER_MINUTE_STOP, 
                                   MIN_TIME_IN_POSITION, 
                                   MAX_TIME_IN_POSITION, 
                                   account)
            
            # If position wasn't closed by PPM, check traditional TP/SL
            if not ppm_closed:
                # Check if we need to close based on profit/loss targets
                positions_before = quiet_get_position(symbol, account)[0]
                print(f"{Fore.YELLOW}💹 Checking traditional take profit/stop loss...")
                quiet_pnl_close(symbol, TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, account)
                positions_after, im_in_pos_after, _, _, _, pnl_perc_after, _ = quiet_get_position(symbol, account)
                
                # Check if position was closed by pnl_close
                if positions_before and not positions_after and active_position is not None:
                    # Record position exit if closed by traditional TP/SL
                    position_id = active_position['position_id']
                    current_price = entry_px  # Approximate since we don't have exact exit price
                    pnl_usd = pnl_perc * active_position['entry_value_usd'] / 100
                    record_position_exit(position_id, current_price, pnl_perc, pnl_usd)
            
            # After pnl_close may have closed the position, check again if we're still in position
            positions, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long = quiet_get_position(symbol, account)
            
            if im_in_pos:
                # Calculate time in position for the summary at the end
                if active_position is not None:
                    current_time = datetime.now()
                    elapsed_minutes = (current_time - active_position['entry_time']).total_seconds() / 60
                    ppm = pnl_perc / elapsed_minutes if elapsed_minutes > 0 else 0
                    
                    # Display position metrics at the end
                    print(f"\n{Fore.CYAN}{'='*80}")
                    print(f"{Fore.CYAN}{'='*30} 📊 XRP POSITION SUMMARY 📊 {'='*30}")
                    print(f"{Fore.CYAN}{'='*80}")
                    print(f"{Fore.YELLOW}🪙 XRP {'LONG' if is_long else 'SHORT'} | Size: {mypos_size} | Entry: ${active_position['entry_price']:.2f}")
                    print(f"{Fore.CYAN}⏱️ Time in position: {elapsed_minutes:.2f} minutes (Min: {MIN_TIME_IN_POSITION} min, Max: {MAX_TIME_IN_POSITION} min)")
                    print(f"{Fore.MAGENTA}📊 Current PnL: {pnl_perc:.2f}% (Take profit: {TAKE_PROFIT_PERCENT}%, Stop loss: {STOP_LOSS_PERCENT}%)")
                    print(f"{Fore.GREEN}🚀 Profit Per Minute: {ppm:.4f}%/min")
                    print(f"{Fore.YELLOW}🎯 PPM Target: {PROFIT_PER_MINUTE_TARGET}%/min | 🛑 PPM Stop: {PROFIT_PER_MINUTE_STOP}%/min")
                    print(f"{Fore.CYAN}{'='*80}\n")
                
                return  # Exit early since we're already in a position
        else:
            print(f"{Fore.YELLOW}📉 Not in XRP position, looking for entry opportunities...")
            
            # If we're not in a position but have an active one in our tracker, close it
            if active_position is not None:
                print(f"{Fore.YELLOW}⚠️ Position not found on exchange but tracked in our system. Marking as closed.")
                position_id = active_position['position_id']
                # Use last known entry price since we don't have exit price
                exit_price = active_position['entry_price']
                record_position_exit(position_id, exit_price, 0, 0)
        
        # Check if we need to refresh our market analysis
        global last_analysis_time
        if last_analysis_time is None or (datetime.now() - last_analysis_time).total_seconds() / 60 >= ANALYSIS_INTERVAL_MINUTES:
            print(f"{Fore.YELLOW}🔄 Time to refresh market analysis...")
            analyze_market()
        else:
            minutes_since_analysis = (datetime.now() - last_analysis_time).total_seconds() / 60
            print(f"{Fore.YELLOW}ℹ️ Using existing analysis from {minutes_since_analysis:.1f} minutes ago")
            print(f"{Fore.YELLOW}🎯 Current bias: {trading_bias.upper() if trading_bias else 'None'}")
            print(f"{Fore.YELLOW}💡 {recommendation_text}")
        
        # Get recent liquidations
        print(f"\n{Fore.CYAN}🔍 Looking for XRP liquidations...")
        recent_liquidations, long_liq_amount, short_liq_amount = get_recent_liquidations()
        
        if recent_liquidations is not None:
            # Print summary of liquidations
            print(f"\n{Fore.CYAN}💧 Total XRP Liquidations in the last {LIQUIDATION_LOOKBACK_MINUTES} minutes:")
            print(f"{Fore.GREEN}📉 LONG Liquidations: ${long_liq_amount:,.2f}")
            print(f"{Fore.RED}📈 SHORT Liquidations: ${short_liq_amount:,.2f}")
            
            # Show the largest liquidations
            if not recent_liquidations.empty:
                largest_liquidations = recent_liquidations.sort_values(by=recent_liquidations.columns[11], ascending=False).head(5)
                print(f"\n{Fore.CYAN}💥 Top 5 largest XRP liquidations:")
                for idx, row in largest_liquidations.iterrows():
                    side_val = row.iloc[1]    # Side at index 1
                    usd_size_val = float(row.iloc[11])  # USD Size at index 11
                    
                    # Classify liquidation type
                    liq_type = "LONG LIQ" if side_val == "SELL" else "SHORT LIQ"
                    
                    # Format timestamp
                    timestamp_ms = int(float(row.iloc[10]))
                    time_str = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%H:%M:%S')
                    
                    print(f"   {time_str} | {liq_type} | ${usd_size_val:,.2f}")
        else:
            print(f"{Fore.YELLOW}⚠️ No liquidation data available")
            return
        
        # Determine if we should enter a trade
        should_enter, entry_message = should_enter_trade(long_liq_amount, short_liq_amount)
        print(f"\n{Fore.YELLOW}🎯 {entry_message}")
        
        if should_enter and not im_in_pos:
            # Get current price for range validation
            current_price = n.get_current_price(symbol)
            
            # Validate price is in correct range for entry
            if not is_price_in_valid_range(current_price, trading_bias):
                print(f"{Back.RED}{Fore.WHITE}{Style.BRIGHT}❌ Price not in valid range for {trading_bias.upper()} entry{Style.RESET_ALL}")
                return
            
            # Get orderbook data
            print(f"\n{Fore.CYAN}📚 Fetching XRP orderbook data...")
            ask, bid, l2_data = n.ask_bid(symbol)
            print(f"{Fore.GREEN}💰 Current price - Ask: ${ask:.2f}, Bid: ${bid:.2f}")
            
            # Adjust leverage and position size
            lev, pos_size = n.adjust_leverage_usd_size(symbol, POSITION_SIZE_USD, LEVERAGE, account)
            print(f"{Fore.YELLOW}📊 Leverage: {lev}x | Position size: {pos_size}")
            
            # Place appropriate order based on trading bias
            n.cancel_all_orders(account)
            print(f"{Fore.YELLOW}🚫 Canceled all existing orders")
            
            if trading_bias == 'short':
                # Place a sell order at the current ask price (market-like limit order)
                n.limit_order(symbol, False, pos_size, ask, False, account)
                print(f"{Fore.RED}💸 Placed SELL order for {pos_size} XRP at ${ask}")
                print(f"{Fore.RED}📉 Looking to profit from long liquidations cascade")
                
                # Record entry in our position tracker
                entry_value = pos_size * ask
                record_position_entry(symbol, 'short', ask, pos_size, lev, entry_value)
            else:  # trading_bias == 'long'
                # Place a buy order at the current bid price (market-like limit order)
                n.limit_order(symbol, True, pos_size, bid, False, account)
                print(f"{Fore.GREEN}🛒 Placed BUY order for {pos_size} XRP at ${bid}")
                print(f"{Fore.GREEN}📈 Looking to profit from short liquidations cascade")
                
                # Record entry in our position tracker
                entry_value = pos_size * bid
                record_position_entry(symbol, 'long', bid, pos_size, lev, entry_value)
            
            print(f"{Fore.YELLOW}⏳ Order placed, waiting for fill...")
            
            # Summary of entry parameters
            print(f"\n{Fore.CYAN}{'='*80}")
            print(f"{Fore.CYAN}{'='*30} 📊 XRP ENTRY PARAMETERS 📊 {'='*30}")
            print(f"{Fore.CYAN}{'='*80}")
            print(f"{Fore.YELLOW}🪙 XRP {'LONG' if trading_bias == 'long' else 'SHORT'} | Size: {pos_size}")
            print(f"{Fore.CYAN}⏱️ Min time in position: {MIN_TIME_IN_POSITION} min, Max time: {MAX_TIME_IN_POSITION} min")
            print(f"{Fore.MAGENTA}📊 Take profit: {TAKE_PROFIT_PERCENT}%, Stop loss: {STOP_LOSS_PERCENT}%")
            print(f"{Fore.GREEN}🚀 PPM Target: {PROFIT_PER_MINUTE_TARGET}%/min | 🛑 PPM Stop: {PROFIT_PER_MINUTE_STOP}%/min")
            print(f"{Fore.CYAN}{'='*80}\n")
        else:
            print(f"{Fore.YELLOW}⏳ Conditions not met for entry, continuing to monitor...")
        
        # Easter egg
        print(f"\n{Fore.MAGENTA}🌕 Thanks for using Moon Dev Trading Bots! 🤖")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error in bot execution: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")

def display_position_stats():
    """Display statistics for all closed XRP positions"""
    global positions_df
    
    if positions_df is None or len(positions_df) == 0:
        print(f"{Fore.YELLOW}📊 No XRP position history available yet")
        return
    
    # Get closed positions
    closed_positions = positions_df[positions_df['is_active'] == False].copy()
    
    if len(closed_positions) == 0:
        print(f"{Fore.YELLOW}📊 No closed XRP positions in history yet")
        return
    
    print(f"\n{Fore.CYAN}{'='*100}")
    print(f"{Fore.CYAN}{'='*35} 📊 XRP POSITION HISTORY SUMMARY 📊 {'='*35}")
    print(f"{Fore.CYAN}{'='*100}")
    
    # Calculate summary statistics
    total_trades = len(closed_positions)
    winning_trades = len(closed_positions[closed_positions['pnl_percent'] > 0])
    losing_trades = len(closed_positions[closed_positions['pnl_percent'] <= 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    avg_pnl = closed_positions['pnl_percent'].mean()
    avg_pnl_usd = closed_positions['pnl_usd'].mean()
    avg_time = closed_positions['time_in_position_min'].mean()
    avg_ppm = closed_positions['ppm'].mean()
    
    # Display summary
    print(f"{Fore.YELLOW}🏆 Total Trades: {total_trades}")
    print(f"{Fore.GREEN}✅ Winning Trades: {winning_trades} ({win_rate:.1f}%)")
    print(f"{Fore.RED}❌ Losing Trades: {losing_trades} ({100-win_rate:.1f}%)")
    print(f"{Fore.CYAN}💰 Average PnL: {avg_pnl:.2f}% (${avg_pnl_usd:.2f})")
    print(f"{Fore.CYAN}⏱️ Average Time in Position: {avg_time:.2f} minutes")
    print(f"{Fore.CYAN}🚀 Average Profit Per Minute: {avg_ppm:.4f}%/min")
    
    # Display recent trades
    print(f"\n{Fore.CYAN}{'='*35} 📈 RECENT CLOSED XRP POSITIONS 📉 {'='*35}")
    
    recent_positions = closed_positions.sort_values('exit_time', ascending=False).head(5)
    for idx, pos in recent_positions.iterrows():
        time_str = pos['exit_time'].strftime('%Y-%m-%d %H:%M:%S')
        time_in_pos = pos['time_in_position_min']
        pnl = pos['pnl_percent']
        pnl_usd = pos['pnl_usd']
        
        # Determine color based on profit/loss
        color = Fore.GREEN if pnl > 0 else Fore.RED
        
        print(f"{color}XRP {'LONG' if pos['side'] == 'long' else 'SHORT'} | " +
              f"PnL: {pnl:.2f}% (${pnl_usd:.2f}) | " +
              f"Time: {time_in_pos:.2f} min | " +
              f"PPM: {pos['ppm']:.4f}%/min | " +
              f"Closed: {time_str}")
    
    # Display active positions
    active_positions = positions_df[positions_df['is_active'] == True]
    if len(active_positions) > 0:
        print(f"\n{Fore.CYAN}{'='*35} 🔄 ACTIVE XRP POSITIONS 🔄 {'='*35}")
        
        for idx, pos in active_positions.iterrows():
            entry_time = pos['entry_time'].strftime('%Y-%m-%d %H:%M:%S')
            time_in_pos = (datetime.now() - pos['entry_time']).total_seconds() / 60
            
            print(f"{Fore.YELLOW}XRP {'LONG' if pos['side'] == 'long' else 'SHORT'} | " +
                  f"Size: {pos['size']} | " +
                  f"Entry: ${pos['entry_price']:.2f} | " +
                  f"Value: ${pos['entry_value_usd']:.2f} | " +
                  f"Time: {time_in_pos:.2f} min | " +
                  f"Entered: {entry_time}")

if __name__ == "__main__":
    # Initialize position tracker
    init_positions_tracker()
    
    # Display position statistics
    display_position_stats()
    
    # Initial market analysis
    print(f"{Fore.YELLOW}🔍 Performing initial market analysis...")
    analyze_market()
    
    # Initial bot run
    print(f"{Fore.YELLOW}🚀 Starting first bot cycle...")
    bot()
    
    # Schedule the bot to run every minute
    schedule.every(5).seconds.do(bot)
    
    # Schedule market analysis to run periodically
    schedule.every(ANALYSIS_INTERVAL_MINUTES).minutes.do(analyze_market)
    
    print(f"{Fore.GREEN}✅ Bot scheduled to run every minute")
    print(f"{Fore.GREEN}✅ Market analysis scheduled to run every {ANALYSIS_INTERVAL_MINUTES} minutes")
    
    while True:
        try:
            # Run pending scheduled tasks
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            print(f"{Fore.RED}❌ Encountered an error: {e}")
            print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
            # Wait before retrying to avoid rapid error logging
            time.sleep(10)