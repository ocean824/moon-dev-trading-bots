'''
This is looking for tiny gains when huge liquidations happened, 
The premise behind this is Liquidations proved to back test well to just buy them. 
That being said, the back test will never match up because as liquidation, you'll never get the entry at that point. 
so the back tests aren't that good in my opinion but the returns are nuts
So, instead of trying to take big wins on liquidations, wait for huge liquidations and take tiny wins. 
like .5% - 1% gains. 
This compounded over 365 days is disgusting. Let's run it. 


TODO 
- get hyperliquid orderbook data and see where the biggest orders are
- simple 4 hours MA to gauge the direction of the market
- 
'''
import sys
import os

# Add the parent directory to the Python path so we can import modules from there
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

from eth_account.signers.local import LocalAccount
import eth_account
import json
import time 
import schedule 
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import ccxt
import pandas as pd
import datetime
import schedule 
import requests 
import nice_funcs as n 
import numpy as np
from dotenv import load_dotenv
from api import MoonDevAPI
from datetime import datetime, timedelta
import pytz

# Load environment variables from .env file
load_dotenv()

# Get the Hyperliquid key from environment variables
HYPER_LIQUID_KEY = os.getenv('HYPER_LIQUID_KEY')

# Symbol to trade
symbol = 'BTC'  # Default symbol, can be changed as needed
LEVERAGE = 5    # Leverage to use for trading
POSITION_SIZE_USD = 10  # Position size in USD

# Constants
LIQUIDATION_LOOKBACK_MINUTES = 10  # Time period to look back for liquidations
SMA_PERIOD = 20  # Number of periods for SMA calculation
TIMEFRAME = '4h'  # Timeframe for OHLCV data
LOOKBACK_DAYS = 10  # Number of days to look back for OHLCV data
LIQUIDATION_TRIGGER_AMOUNT = 5000000  # $10 million trigger amount for liquidations

MAX_SMA_DISTANCE_PERCENT = 3.0  # Maximum allowed distance from SMA in percent (works for both above and below SMA)
TAKE_PROFIT_PERCENT = 0.6  # Take profit percentage (close position when P&L reaches this percentage)
STOP_LOSS_PERCENT = -6.0  # Stop loss percentage (close position when P&L falls below this percentage)


# Trading hours (Eastern Time)
MORNING_OPEN_HOUR = 9   # 9:00 AM ET
MORNING_CLOSE_HOUR = 10  # 10:00 AM ET
AFTERNOON_OPEN_HOUR = 15  # 3:00 PM ET
AFTERNOON_CLOSE_HOUR = 16  # 4:00 PM ET

# Initialize API
api = MoonDevAPI()


account1 = LocalAccount = eth_account.Account.from_key(HYPER_LIQUID_KEY)



def get_market_trend():
    """
    Get the market trend based on the SMA
    Returns: str - 'uptrend', 'downtrend', or 'neutral'
    """
    # Fetch OHLCV data
    snapshot_data = n.get_ohlcv2(symbol, TIMEFRAME, LOOKBACK_DAYS)
    
    if snapshot_data:
        # Process data to DataFrame
        df = n.process_data_to_df(snapshot_data)
        
        if not df.empty:
            # Calculate SMA
            df['sma'] = df['close'].rolling(window=SMA_PERIOD).mean()
            
            # Get the last close price and SMA value
            last_close = float(df['close'].iloc[-1])
            last_sma = float(df['sma'].iloc[-1])
            
            # Determine trend
            if last_close > last_sma * 1.01:  # 1% above SMA
                return 'uptrend', last_close, last_sma
            elif last_close < last_sma * 0.99:  # 1% below SMA
                return 'downtrend', last_close, last_sma
            else:
                return 'neutral', last_close, last_sma
    
    return 'unknown', None, None

def is_within_trading_hours():
    """
    Check if the current time is within either of the two trading windows in Eastern Time:
    1. Morning window: 9:00 AM - 10:00 AM ET
    2. Afternoon window: 3:00 PM - 4:00 PM ET
    
    Returns: bool - True if within trading hours, False otherwise
    """
    # Get current time in Eastern Time
    et_timezone = pytz.timezone('US/Eastern')
    current_time_et = datetime.now(pytz.utc).astimezone(et_timezone)
    
    # Extract hour
    current_hour = current_time_et.hour
    
    # Check if current hour is within either trading window
    is_morning_window = MORNING_OPEN_HOUR <= current_hour < MORNING_CLOSE_HOUR
    is_afternoon_window = AFTERNOON_OPEN_HOUR <= current_hour < AFTERNOON_CLOSE_HOUR
    
    is_trading_time = is_morning_window or is_afternoon_window
    
    if is_trading_time:
        window_name = "morning" if is_morning_window else "afternoon"
        print(f"✅ Current time ({current_time_et.strftime('%H:%M:%S ET')}) is within the {window_name} trading window")
        print(f"   Trading windows: {MORNING_OPEN_HOUR}:00-{MORNING_CLOSE_HOUR}:00 AM ET and {AFTERNOON_OPEN_HOUR-12}:00-{AFTERNOON_CLOSE_HOUR-12}:00 PM ET")
    else:
        print(f"⏰ Current time ({current_time_et.strftime('%H:%M:%S ET')}) is outside trading hours")
        print(f"   Trading windows: {MORNING_OPEN_HOUR}:00-{MORNING_CLOSE_HOUR}:00 AM ET and {AFTERNOON_OPEN_HOUR-12}:00-{AFTERNOON_CLOSE_HOUR-12}:00 PM ET")
    
    return is_trading_time

def bot():
    print('🌙 Moon Dev Bot Starting... 🚀')
    
    # Initialize trigger variables
    trigger_hit = False
    trigger_message = ""
    trigger_color = "on_blue"  # Default to blue (do nothing)
    
    # Check for existing positions
    print('🔍 Checking for existing positions...')
    positions1, im_in_pos, mypos_size, pos_sym1, entry_px1, pnl_perc1, long1 = n.get_position(symbol, account1)
    print(f'📊 These are positions 1: {positions1}')
    
    # First action: Check P&L and close positions if needed
    if im_in_pos:
        print('📈 In position, so check PnL close')
        n.pnl_close(symbol, TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, account1)
    else:
        print('📉 Not in position, so no PnL close')
    
    print(f'🔍 Looking for liquidations on {symbol}... 🧐')
    
    # Get market trend
    trend, last_close, last_sma = get_market_trend()
    if last_close and last_sma:
        trend_emoji = '📈' if trend == 'uptrend' else '📉' if trend == 'downtrend' else '↔️'
        print(f"\n{trend_emoji} Market Trend: {trend.upper()} - Last Close: ${last_close:.2f}, SMA({SMA_PERIOD}): ${last_sma:.2f}")
        print(f"📊 Price to SMA Ratio: {(last_close/last_sma - 1) * 100:.2f}%")
    else:
        print("⚠️ Could not determine market trend")
        trend = "unknown"
    
    # Fetch liquidation data
    liquidations = api.get_liquidation_data(limit=1000)
    if liquidations is not None:
        # Print column names for debugging
        print("\n📊 Liquidation data columns:", liquidations.columns.tolist())
        
        # Based on the output, we can see:
        # - Column 0: Symbol (e.g., 'AMB')
        # - Column 1: Side (e.g., 'SELL')
        # - Column 10: Timestamp (e.g., '1717505218553')
        # - Column 11: USD Size (e.g., '207.21417599999998')
        
        # Convert to milliseconds timestamp
        current_time_ms = int(datetime.now().timestamp() * 1000)
        cutoff_time_ms = current_time_ms - (LIQUIDATION_LOOKBACK_MINUTES * 60 * 1000)
        
        # Filter liquidations within the lookback period using the timestamp column (index 10)
        recent_liquidations = liquidations[liquidations.iloc[:, 10].astype(float) >= cutoff_time_ms]
        
        # Calculate total liquidation amount using the USD size column (index 11)
        if not recent_liquidations.empty:
            # Separate long and short liquidations
            # Following the logic: "L LIQ" if side == "SELL" else "S LIQ"
            long_liqs = recent_liquidations[recent_liquidations.iloc[:, 1] == "SELL"]
            short_liqs = recent_liquidations[recent_liquidations.iloc[:, 1] == "BUY"]
            
            # Calculate totals
            total_liquidation_amount = recent_liquidations.iloc[:, 11].astype(float).sum()
            long_liq_amount = long_liqs.iloc[:, 11].astype(float).sum() if not long_liqs.empty else 0
            short_liq_amount = short_liqs.iloc[:, 11].astype(float).sum() if not short_liqs.empty else 0
            
            # Print summary
            print(f'\n💧 Total Liquidations in the last {LIQUIDATION_LOOKBACK_MINUTES} minutes: ${total_liquidation_amount:,.2f}')
            print(f'🔢 Number of liquidation events: {len(recent_liquidations)}')
            print(f'📉 LONG Liquidations: ${long_liq_amount:,.2f} ({len(long_liqs)} events)')
            print(f'📈 SHORT Liquidations: ${short_liq_amount:,.2f} ({len(short_liqs)} events)')
            
            # Calculate ratio if both types exist
            if long_liq_amount > 0 and short_liq_amount > 0:
                ratio = long_liq_amount / short_liq_amount
                if ratio > 1:
                    print(f'⚖️ Ratio: {ratio:.2f}x more LONG liquidations than SHORT')
                else:
                    print(f'⚖️ Ratio: {1/ratio:.2f}x more SHORT liquidations than LONG')
            
            # Calculate the distance from SMA as a percentage
            sma_distance_percent = abs((last_close/last_sma - 1) * 100) if last_close and last_sma else float('inf')
            
            # Check if price is within the allowed distance from SMA
            if sma_distance_percent <= MAX_SMA_DISTANCE_PERCENT:
                # If market is in downtrend, look for SHORT liquidations exceeding the trigger amount
                if trend == 'downtrend' and short_liq_amount >= LIQUIDATION_TRIGGER_AMOUNT:
                    trigger_hit = True
                    trigger_color = "on_green"
                    trigger_message = f"🔴 DOWNTREND + SHORT LIQUIDATIONS (${short_liq_amount:,.2f}) EXCEEDING TRIGGER (${LIQUIDATION_TRIGGER_AMOUNT:,.2f})"
                
                # If market is in uptrend, look for LONG liquidations exceeding the trigger amount
                elif trend == 'uptrend' and long_liq_amount >= LIQUIDATION_TRIGGER_AMOUNT:
                    trigger_hit = True
                    trigger_color = "on_green"
                    trigger_message = f"🟢 UPTREND + LONG LIQUIDATIONS (${long_liq_amount:,.2f}) EXCEEDING TRIGGER (${LIQUIDATION_TRIGGER_AMOUNT:,.2f})"
                else:
                    trigger_message = f"⏳ Waiting for trigger conditions | LONG LIQs: ${long_liq_amount:,.2f} | SHORT LIQs: ${short_liq_amount:,.2f} | Trigger threshold: ${LIQUIDATION_TRIGGER_AMOUNT:,.2f}"
            else:
                trigger_message = f"⚠️ Price too far from SMA: {sma_distance_percent:.2f}% (max allowed: {MAX_SMA_DISTANCE_PERCENT:.2f}%) | LONG LIQs: ${long_liq_amount:,.2f} | SHORT LIQs: ${short_liq_amount:,.2f}"
            
            # Show the largest liquidations
            if not recent_liquidations.empty:
                largest_liquidations = recent_liquidations.sort_values(by=recent_liquidations.columns[11], ascending=False).head(5)
                print(f'\n💥 Top 5 largest liquidations:')
                for idx, row in largest_liquidations.iterrows():
                    symbol_val = row.iloc[0]  # Symbol at index 0
                    side_val = row.iloc[1]    # Side at index 1
                    usd_size_val = float(row.iloc[11])  # USD Size at index 11
                    
                    # Classify liquidation type
                    liq_type = "LONG LIQ" if side_val == "SELL" else "SHORT LIQ"
                    
                    # Format timestamp
                    timestamp_ms = int(float(row.iloc[10]))
                    time_str = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%H:%M:%S')
                    
                    print(f"   {time_str} | {symbol_val} | {liq_type} | ${usd_size_val:,.2f}")
        else:
            print(f"\n🔍 No liquidations found in the last {LIQUIDATION_LOOKBACK_MINUTES} minutes")
            trigger_message = f"⚠️ No liquidations found in the last {LIQUIDATION_LOOKBACK_MINUTES} minutes | Current trend: {trend.upper()}"
    else:
        print('⚠️ Failed to fetch liquidation data.')
        trigger_message = "⚠️ Failed to fetch liquidation data"
    
    # Get orderbook data using ask_bid function
    print("\n📚 Fetching orderbook data...")
    ask, bid, l2_data = n.ask_bid(symbol)
    print(f"💰 Current price - Ask: ${ask:.2f}, Bid: ${bid:.2f}")
    
    # Split the orderbook into chunks of four
    bid_side = l2_data[0]  # Bid side of the orderbook
    ask_side = l2_data[1]  # Ask side of the orderbook
    
    # Function to split list into chunks of size n
    def chunk_list(lst, n):
        return [lst[i:i + n] for i in range(0, len(lst), n)]
    
    # Function to calculate total size of a chunk
    def chunk_total_size(chunk):
        return sum(float(order['sz']) for order in chunk)
    
    # Split orderbook into chunks of 4
    bid_chunks = chunk_list(bid_side, 4)
    ask_chunks = chunk_list(ask_side, 4)
    
    # Calculate total size for each chunk
    bid_chunk_sizes = []
    for i, chunk in enumerate(bid_chunks):
        total_size = chunk_total_size(chunk)
        bid_chunk_sizes.append((i, total_size))
        print(f"🟢 BID Chunk {i+1} (levels {i*4+1}-{i*4+len(chunk)}): Total size = {total_size:.4f}")
    
    ask_chunk_sizes = []
    for i, chunk in enumerate(ask_chunks):
        total_size = chunk_total_size(chunk)
        ask_chunk_sizes.append((i, total_size))
        print(f"🔴 ASK Chunk {i+1} (levels {i*4+1}-{i*4+len(chunk)}): Total size = {total_size:.4f}")
    
    # Find the biggest chunks
    biggest_bid_chunk = max(bid_chunk_sizes, key=lambda x: x[1])
    biggest_ask_chunk = max(ask_chunk_sizes, key=lambda x: x[1])
    
    print(f"\n🟢 Biggest BID Chunk: Chunk {biggest_bid_chunk[0]+1} (levels {biggest_bid_chunk[0]*4+1}-{biggest_bid_chunk[0]*4+4}) with total size {biggest_bid_chunk[1]:.4f}")
    print(f"🔴 Biggest ASK Chunk: Chunk {biggest_ask_chunk[0]+1} (levels {biggest_ask_chunk[0]*4+1}-{biggest_ask_chunk[0]*4+4}) with total size {biggest_ask_chunk[1]:.4f}")
    
    # Show price ranges for the biggest chunks
    biggest_bid_chunk_data = bid_chunks[biggest_bid_chunk[0]]
    biggest_ask_chunk_data = ask_chunks[biggest_ask_chunk[0]]
    
    if biggest_bid_chunk_data:
        bid_price_range = f"${float(biggest_bid_chunk_data[-1]['px']):.2f} - ${float(biggest_bid_chunk_data[0]['px']):.2f}"
        print(f"🟢 Biggest BID Chunk Price Range: {bid_price_range}")
    
    if biggest_ask_chunk_data:
        ask_price_range = f"${float(biggest_ask_chunk_data[0]['px']):.2f} - ${float(biggest_ask_chunk_data[-1]['px']):.2f}"
        print(f"🔴 Biggest ASK Chunk Price Range: {ask_price_range}")
    
    # Calculate entry prices based on the biggest chunks
    print("\n🎯 Calculating strategic entry prices...")
    
    # Get price decimals for proper rounding
    _, px_decimals = n.get_sz_px_decimals(symbol)
    
    # Calculate entry prices
    # For buy orders: Place just above the biggest bid chunk
    # For sell orders: Place just below the biggest ask chunk
    if biggest_bid_chunk_data and biggest_ask_chunk_data:
        # Get the top of the biggest bid chunk and bottom of the biggest ask chunk
        bid_top_price = float(biggest_bid_chunk_data[0]['px'])
        ask_bottom_price = float(biggest_ask_chunk_data[0]['px'])
        
        # Calculate entry prices with a small buffer (0.1%)
        buy_price = round(bid_top_price * 1.001, px_decimals)  # 0.1% above the top bid
        sell_price = round(ask_bottom_price * 0.999, px_decimals)  # 0.1% below the bottom ask
        
        # Adjust position size based on leverage
        lev, pos_size = n.adjust_leverage_usd_size(symbol, POSITION_SIZE_USD, LEVERAGE, account1)
        
        # Check if we already have a position and adjust size if needed
        should_place_order = True
        if mypos_size >= pos_size:
            print(f'📊 Already in full position (current size: {mypos_size}, target size: {pos_size})')
            print(f'⚠️ Not placing new orders as we are already at or above target position size')
            should_place_order = False
        elif mypos_size > 0:
            print(f'📏 Current position size: {mypos_size}')
            adjusted_pos_size = pos_size - mypos_size
            print(f'🔄 Adjusted size for new order: {adjusted_pos_size}')
            pos_size = adjusted_pos_size
        
        print(f"💰 Current Price - Ask: ${ask:.2f}, Bid: ${bid:.2f}")
        print(f"🛒 Buy Price: ${buy_price}")
        print(f"💸 Sell Price: ${sell_price}")
        print(f"📊 Leverage: {lev}x")
        print(f"📏 Position Size: {pos_size}")
        
        # Place orders based on market trend and trigger conditions
        if trigger_hit and should_place_order:
            print("\n🚀 Trigger conditions met!")
            
            # Check if within trading hours
            if is_within_trading_hours():
                # Cancel any existing orders first
                n.cancel_all_orders(account1)
                print('🚫 Canceled all existing orders')
                
                # Place appropriate order based on market trend
                if trend == 'downtrend' and short_liq_amount >= LIQUIDATION_TRIGGER_AMOUNT:
                    # In downtrend with short liquidations, we want to sell (go short)
                    # Short liquidations in a downtrend indicate a temporary pop in price - good shorting opportunity
                    n.limit_order(symbol, False, pos_size, sell_price, False, account1)
                    print(f'💸 Placed SELL order for {pos_size} {symbol} at ${sell_price}')
                    
                elif trend == 'uptrend' and long_liq_amount >= LIQUIDATION_TRIGGER_AMOUNT:
                    # In uptrend with long liquidations, we want to buy (go long)
                    # Long liquidations in an uptrend indicate a temporary dip - good buying opportunity
                    n.limit_order(symbol, True, pos_size, buy_price, False, account1)
                    print(f'🛒 Placed BUY order for {pos_size} {symbol} at ${buy_price}')
            else:
                print("⏰ Not placing orders outside of trading hours")
        elif trigger_hit and not should_place_order:
            print("\n🚀 Trigger conditions met, but not placing orders due to existing full position")
        else:
            print("\n⏳ Waiting for trigger conditions before placing orders")
    else:
        print("⚠️ Could not calculate entry prices - missing orderbook data")
    
    # Easter egg
    print('\n🌕 Thanks for using Moon Dev Trading Bots! 🌕')
    
    # Print trigger message with colored background as the last thing
    from termcolor import colored
    
    # Check if within trading hours
    trading_hours_status = is_within_trading_hours()
    
    # Prepare trigger header and message
    if trigger_hit:
        if trading_hours_status:
            trigger_header = "🚨 TRIGGER HIT! TIME TO ENTER! 🚨"
        else:
            trigger_header = "🚨 TRIGGER HIT! (WAITING FOR TRADING HOURS) 🚨"
            trigger_color = "on_blue"  # Use blue for waiting
    else:
        trigger_header = "🔍 MARKET STATUS"
    
    colored_header = colored(trigger_header, 'white', trigger_color, attrs=['bold'])
    print("\n" + "=" * 80)
    print(colored_header)
    
    # Add trading hours info to the trigger message
    if not trading_hours_status:
        trading_hours_info = f" | Outside trading hours ({MORNING_OPEN_HOUR}:00-{MORNING_CLOSE_HOUR}:00 AM ET and {AFTERNOON_OPEN_HOUR-12}:00-{AFTERNOON_CLOSE_HOUR-12}:00 PM ET)"
        trigger_message += trading_hours_info
    
    print(colored(trigger_message, 'white', trigger_color))
    print("=" * 80)

# Initial run
bot()

# Schedule the main function to run every minute
schedule.every(1).minutes.do(bot)

while True:
    try:
        # Run pending scheduled tasks
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        print(f"Encountered an error: {e}")
        # Wait before retrying to avoid rapid error logging
        time.sleep(10)


