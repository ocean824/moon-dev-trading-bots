'''
NOT TESTED, PUT YOUR OWN IDEAS IN -- NON OF THIS IS TESTED OR FINANCIAL ADVICE

Ethereum foundation has 100,000 eth on maker with a liquidation price of 1,127
they have 169,000 eth they can add to lower it but that would be super risky for them so idk if they will add it

The max they'll probably add is 50,000 more ETH, which would bring their liquidation down to about 754 dollars. 
Technically they would have 110,000 more ETH. But risking it all? Just when it makes sense. And would probably kill Ethereum forever. 

big liq points -
- eth long liq at 1750 - 3.5m 
- eth long liq at 1835 - 1.5m 
- eth long liq at 1798 - 1.21m
- eth long liq at 1996 - 3m
- eth short liq 2189 - 1.5m

TODO
- build a bot that shorts eth when it pops to the 4 hour SMA and liquidations of Short Happen
- api.moondev.com to grab the liquidation data
- enter in on 2m+ ETH specific short liquidation 
- wait for exchanges to beg for shorts, meaning the funding rate is super high
   - close when they are begging for longs
'''

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ETH Short Bot for Hyperliquid
🌙 Created by Moon Dev 🚀
This bot shorts ETH when specific conditions are met:
1. Short liquidations exceed threshold
2. Price is near 4h SMA (above or slightly below)
3. Funding rate is favorable
"""

import sys
import os

# Add the parent directory to the Python path so we can import modules from there
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

import time
import json
import schedule 
import requests 
import pandas as pd
import numpy as np
import datetime
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv
from eth_account.signers.local import LocalAccount
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import ccxt
import nice_funcs as n 
from api import MoonDevAPI

# Load environment variables from .env file
load_dotenv()

# Get the Hyperliquid key from environment variables
HYPER_LIQUID_KEY = os.getenv('HYPER_LIQUID_KEY')

# Symbol to trade
symbol = 'ETH'  # Default symbol, can be changed as needed
LEVERAGE = 5    # Leverage to use for trading
POSITION_SIZE_USD = 10  # Position size in USD


# Constants
LIQUIDATION_LOOKBACK_MINUTES = 10  # Time period to look back for liquidations
SMA_PERIOD = 20  # Number of periods for SMA calculation
TIMEFRAME = '4h'  # Timeframe for OHLCV data
LOOKBACK_DAYS = 10  # Number of days to look back for OHLCV data
SHORT_LIQUIDATION_TRIGGER_AMOUNT = 2000000  # $2 million trigger amount for short liquidations

# SMA distance parameters
MAX_SMA_DISTANCE_ABOVE = 6.0  # Maximum allowed distance above SMA in percent
MAX_SMA_DISTANCE_BELOW = 1.5  # Maximum allowed distance below SMA in percent

# Funding rate threshold (positive value means shorts pay longs)
MIN_YEARLY_FUNDING_RATE = 20.0  # Minimum acceptable yearly funding rate (20% annualized)

# Take profit and stop loss
TAKE_PROFIT_PERCENT = 2.5  # Take profit percentage (close position when P&L reaches this percentage)
STOP_LOSS_PERCENT = -5.0  # Stop loss percentage (close position when P&L falls below this percentage)

# Initialize API
api = MoonDevAPI()

# Initialize account
account = Account.from_key(HYPER_LIQUID_KEY)

def get_market_data():
    """
    Get the market data including SMA, current price, and distance from SMA
    Returns: dict with market data
    """
    print('🔮 Getting market data for ETH... 🌙')
    
    # Fetch OHLCV data
    snapshot_data = n.get_ohlcv2(symbol, TIMEFRAME, LOOKBACK_DAYS)
    
    if not snapshot_data:
        print('⚠️ Failed to fetch OHLCV data!')
        return None
    
    # Process data to DataFrame
    df = n.process_data_to_df(snapshot_data)
    
    if df.empty:
        print('⚠️ Empty DataFrame after processing OHLCV data!')
        return None
    
    # Calculate SMA
    df['sma'] = df['close'].rolling(window=SMA_PERIOD).mean()
    
    # Get the last close price and SMA value
    last_close = float(df['close'].iloc[-1])
    last_sma = float(df['sma'].iloc[-1])
    
    # Calculate distance from SMA as a percentage
    sma_distance_percent = ((last_close/last_sma) - 1) * 100
    
    # Determine if price is within acceptable range of SMA
    above_sma = sma_distance_percent > 0 and sma_distance_percent <= MAX_SMA_DISTANCE_ABOVE
    below_sma = sma_distance_percent < 0 and abs(sma_distance_percent) <= MAX_SMA_DISTANCE_BELOW
    within_sma_range = above_sma or below_sma
    
    # Print market data
    print(f'📊 Last Close: ${last_close:.2f}, SMA({SMA_PERIOD}): ${last_sma:.2f}')
    print(f'📏 Distance from SMA: {sma_distance_percent:.2f}%')
    
    if within_sma_range:
        if above_sma:
            print(f'🎯 Price is ABOVE SMA by {sma_distance_percent:.2f}% (max allowed: {MAX_SMA_DISTANCE_ABOVE:.2f}%)')
        else:
            print(f'🎯 Price is BELOW SMA by {abs(sma_distance_percent):.2f}% (max allowed: {MAX_SMA_DISTANCE_BELOW:.2f}%)')
    else:
        if sma_distance_percent > 0:
            print(f'⚠️ Price is TOO FAR ABOVE SMA: {sma_distance_percent:.2f}% (max allowed: {MAX_SMA_DISTANCE_ABOVE:.2f}%)')
        else:
            print(f'⚠️ Price is TOO FAR BELOW SMA: {abs(sma_distance_percent):.2f}% (max allowed: {MAX_SMA_DISTANCE_BELOW:.2f}%)')
    
    return {
        'last_close': last_close,
        'last_sma': last_sma,
        'sma_distance_percent': sma_distance_percent,
        'within_sma_range': within_sma_range,
        'df': df
    }

def get_liquidation_data():
    """
    Get and analyze liquidation data for ETH only
    Returns: dict with liquidation data
    """
    print('💧 Checking for ETH liquidations... 🌊')
    
    # Fetch liquidation data
    liquidations = api.get_liquidation_data(limit=1000)
    
    if liquidations is None:
        print('⚠️ Failed to fetch liquidation data!')
        return None
    
    # Convert to milliseconds timestamp
    current_time_ms = int(datetime.now().timestamp() * 1000)
    cutoff_time_ms = current_time_ms - (LIQUIDATION_LOOKBACK_MINUTES * 60 * 1000)
    
    # Filter liquidations within the lookback period using the timestamp column (index 10)
    recent_liquidations = liquidations[liquidations.iloc[:, 10].astype(float) >= cutoff_time_ms]
    
    if recent_liquidations.empty:
        print(f"🔍 No liquidations found in the last {LIQUIDATION_LOOKBACK_MINUTES} minutes")
        return {
            'short_liq_amount': 0,
            'long_liq_amount': 0,
            'short_liq_trigger_hit': False
        }
    
    # Filter for ETH liquidations only (column 0 contains the symbol)
    eth_liquidations = recent_liquidations[recent_liquidations.iloc[:, 0].str.contains('ETH')]
    
    if eth_liquidations.empty:
        print(f"🔍 No ETH liquidations found in the last {LIQUIDATION_LOOKBACK_MINUTES} minutes")
        return {
            'short_liq_amount': 0,
            'long_liq_amount': 0,
            'short_liq_trigger_hit': False
        }
    
    # Separate long and short liquidations
    # Following the logic: "L LIQ" if side == "SELL" else "S LIQ"
    long_liqs = eth_liquidations[eth_liquidations.iloc[:, 1] == "SELL"]
    short_liqs = eth_liquidations[eth_liquidations.iloc[:, 1] == "BUY"]
    
    # Calculate totals
    total_liquidation_amount = eth_liquidations.iloc[:, 11].astype(float).sum()
    long_liq_amount = long_liqs.iloc[:, 11].astype(float).sum() if not long_liqs.empty else 0
    short_liq_amount = short_liqs.iloc[:, 11].astype(float).sum() if not short_liqs.empty else 0
    
    # Print summary
    print(f'💧 ETH Liquidations in the last {LIQUIDATION_LOOKBACK_MINUTES} minutes: ${total_liquidation_amount:,.2f}')
    print(f'🔢 Number of ETH liquidation events: {len(eth_liquidations)}')
    print(f'📉 ETH LONG Liquidations: ${long_liq_amount:,.2f} ({len(long_liqs)} events)')
    print(f'📈 ETH SHORT Liquidations: ${short_liq_amount:,.2f} ({len(short_liqs)} events)')
    
    # Check if short liquidations exceed the trigger amount
    short_liq_trigger_hit = short_liq_amount >= SHORT_LIQUIDATION_TRIGGER_AMOUNT
    
    if short_liq_trigger_hit:
        print(f'🚨 ETH SHORT LIQUIDATIONS TRIGGER HIT! ${short_liq_amount:,.2f} > ${SHORT_LIQUIDATION_TRIGGER_AMOUNT:,.2f}')
    else:
        print(f'⏳ Waiting for ETH SHORT liquidations to exceed ${SHORT_LIQUIDATION_TRIGGER_AMOUNT:,.2f}')
    
    # Show the largest ETH liquidations
    if not eth_liquidations.empty:
        largest_liquidations = eth_liquidations.sort_values(by=eth_liquidations.columns[11], ascending=False).head(5)
        print(f'\n💥 Top 5 largest ETH liquidations:')
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
    
    # Also print total liquidations for context
    print(f'\n📊 For reference - Total liquidations across all assets: ${recent_liquidations.iloc[:, 11].astype(float).sum():,.2f}')
    
    return {
        'short_liq_amount': short_liq_amount,
        'long_liq_amount': long_liq_amount,
        'short_liq_trigger_hit': short_liq_trigger_hit
    }

def get_funding_rate_data():
    """
    Get and analyze funding rate data
    Returns: dict with funding rate data
    """
    print('💰 Checking funding rates... 💸')
    
    try:
        # Get funding rate data directly from API
        funding_df = api.get_funding_data()
        
        if funding_df is None or funding_df.empty:
            print('⚠️ Failed to fetch funding data or empty data returned')
            return {
                'funding_rate': 0,
                'yearly_funding_rate': 0,
                'funding_favorable': False
            }
        
        # Filter for ETH
        eth_funding = funding_df[funding_df['symbol'] == 'ETH']
        
        if eth_funding.empty:
            print('⚠️ No ETH funding data found')
            return {
                'funding_rate': 0,
                'yearly_funding_rate': 0,
                'funding_favorable': False
            }
        
        # Get the latest ETH funding data
        latest_eth_funding = eth_funding.iloc[0]
        
        # Extract funding rates (API returns annualized rates)
        funding_rate = float(latest_eth_funding.get('funding_rate', 0))
        yearly_funding_rate = float(latest_eth_funding.get('yearly_funding_rate', 0))
        
        print(f'💰 ETH Funding Rate: {funding_rate:.6f} (8h) | {yearly_funding_rate:.2f}% (yearly)')
        
        # Check if funding rate is favorable for shorts (above minimum threshold)
        # A positive funding rate means longs pay shorts, so we want a high positive value
        funding_favorable = yearly_funding_rate >= MIN_YEARLY_FUNDING_RATE
        
        if funding_favorable:
            print(f'✅ Funding rate is favorable for shorts: {yearly_funding_rate:.2f}% >= {MIN_YEARLY_FUNDING_RATE:.2f}% (yearly)')
        else:
            print(f'⚠️ Funding rate is unfavorable for shorts: {yearly_funding_rate:.2f}% < {MIN_YEARLY_FUNDING_RATE:.2f}% (yearly)')
        
        return {
            'funding_rate': funding_rate,
            'yearly_funding_rate': yearly_funding_rate,
            'funding_favorable': funding_favorable
        }
    except Exception as e:
        print(f'⚠️ Error getting funding rate: {e}')
        return {
            'funding_rate': 0,
            'yearly_funding_rate': 0,
            'funding_favorable': False
        }

def bot():
    """
    Main bot function
    """
    print('🌙 Moon Dev ETH Short Bot Starting... 🚀')
    print(f'⏰ {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    # Initialize trigger variables
    trigger_hit = False
    trigger_message = ""
    
    # Check for existing positions
    print('🔍 Checking for existing positions...')
    positions, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, long = n.get_position(symbol, account)
    print(f'📊 Current positions: {positions}')
    
    # First action: Check P&L and close positions if needed
    if im_in_pos:
        print('📈 In position, so check PnL close')
        n.pnl_close(symbol, TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, account)
    else:
        print('📉 Not in position, so no PnL close')
    
    # Get market data
    market_data = get_market_data()
    if not market_data:
        print('⚠️ Failed to get market data, aborting this cycle')
        return
    
    # Get liquidation data
    liquidation_data = get_liquidation_data()
    if not liquidation_data:
        print('⚠️ Failed to get liquidation data, aborting this cycle')
        return
    
    # Get funding rate data
    funding_data = get_funding_rate_data()
    
    # Check if all conditions are met for a short entry
    conditions_met = (
        market_data['within_sma_range'] and
        liquidation_data['short_liq_trigger_hit'] and
        funding_data['funding_favorable']
    )
    
    if conditions_met:
        trigger_hit = True
        trigger_message = f"🚨 ALL CONDITIONS MET FOR ETH SHORT ENTRY! 🚨"
        print(trigger_message)
        print('✅ Price is within acceptable range of SMA')
        print(f'✅ Short liquidations (${liquidation_data["short_liq_amount"]:,.2f}) exceed threshold (${SHORT_LIQUIDATION_TRIGGER_AMOUNT:,.2f})')
        print(f'✅ Funding rate ({funding_data["yearly_funding_rate"]:.2f}%) is favorable (≥ {MIN_YEARLY_FUNDING_RATE:.2f}%)')
    else:
        trigger_message = '⏳ Not all conditions met for short entry:'
        print(trigger_message)
        print(f'{"✅" if market_data["within_sma_range"] else "❌"} Price within SMA range')
        print(f'{"✅" if liquidation_data["short_liq_trigger_hit"] else "❌"} Short liquidations threshold')
        print(f'{"✅" if funding_data["funding_favorable"] else "❌"} Favorable funding rate')
    
    # Get orderbook data using ask_bid function
    print("\n📚 Fetching orderbook data...")
    ask, bid, l2_data = n.ask_bid(symbol)
    print(f"💰 Current price - Ask: ${ask:.2f}, Bid: ${bid:.2f}")
    
    # Get price decimals for proper rounding
    sz_decimals, px_decimals = n.get_sz_px_decimals(symbol)
    
    # Calculate entry price for short (slightly below current bid)
    sell_price = round(bid * 0.999, px_decimals)  # 0.1% below the current bid
    
    # Adjust position size based on leverage
    lev, pos_size = n.adjust_leverage_usd_size(symbol, POSITION_SIZE_USD, LEVERAGE, account)
    
    # Check if we already have a position and adjust size if needed
    should_place_order = True
    if im_in_pos:
        if not long:  # If we're already short
            if mypos_size >= pos_size:
                print(f'📊 Already in full short position (current size: {mypos_size}, target size: {pos_size})')
                print(f'⚠️ Not placing new orders as we are already at or above target position size')
                should_place_order = False
            else:
                print(f'📏 Current short position size: {mypos_size}')
                adjusted_pos_size = pos_size - mypos_size
                print(f'🔄 Adjusted size for new order: {adjusted_pos_size}')
                pos_size = adjusted_pos_size
        else:  # If we're long, don't place a short
            print(f'⚠️ Currently in a LONG position. Not placing SHORT orders.')
            should_place_order = False
    
    print(f"💰 Current Price - Ask: ${ask:.2f}, Bid: ${bid:.2f}")
    print(f"💸 Short Entry Price: ${sell_price}")
    print(f"📊 Leverage: {lev}x")
    print(f"📏 Position Size: {pos_size}")
    
    # Place orders based on trigger conditions
    if trigger_hit and should_place_order:
        print("\n🚀 Trigger conditions met!")
        
        # Cancel any existing orders first
        n.cancel_all_orders(account)
        print('🚫 Canceled all existing orders')
        
        # Place short order
        n.limit_order(symbol, False, pos_size, sell_price, False, account)
        print(f'💸 Placed SHORT order for {pos_size} {symbol} at ${sell_price}')
    elif trigger_hit and not should_place_order:
        print("\n🚀 Trigger conditions met, but not placing orders due to existing position")
    else:
        print("\n⏳ Waiting for trigger conditions before placing orders")
    
    # Easter egg
    print('\n🌕 Thanks for using Moon Dev Trading Bots! 🌕')
    print('🌙 Moon Dev ETH Short Bot cycle completed! 🚀')

# Initial run
if __name__ == "__main__":
    print("🌙 sup dawg, Moon Dev ETH Short Bot initializing... 🚀")
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
