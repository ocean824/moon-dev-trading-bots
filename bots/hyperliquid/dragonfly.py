'''
This is a trading bot that will be looking at people's positions in an aggregate and also individually. 
That are on hyperliquid since we get all of the hyperliquid positions, that's great. 
And then if it's super lopsided, it is going to trade towards the majority. 
so the example right now is there is about 490 million dollars in shorts on 
hyperliquid an aggregate and one player has 430 million of them so this algo 
would trade to the short side very quickly not often but when the opportunity arises 
If the majority is short, we will look for short liquidations to enter on 
We may also look at small-long liquidations to enter on to assume there may be continuation 
The measurement we're going to do here is not PNL 
but rather ppm, which would be profit per minute. 
I want to build out some sort of new tracking system, new KPI per se, that instead of looking at P&L, we're looking at profit per minute. 
which obviously could be a positive or negative number and the way i see this formula would be this would be profit divided by minutes 
Then we could figure out what the standard is and trade around those numbers. So at the top of this code, we'll have constants for close on TP PPM and SL PPM. 

'''

import sys
import os
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import schedule
from termcolor import colored
import warnings
warnings.filterwarnings('ignore')

# Add the parent directory to the Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

from eth_account.signers.local import LocalAccount
import eth_account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from dotenv import load_dotenv
import nice_funcs as n
from ppls_positions import main as get_positions

# Load environment variables
load_dotenv()

# Constants
HYPER_LIQUID_KEY = os.getenv('HYPER_LIQUID_KEY')
SYMBOL = 'BTC'
LEVERAGE = 5
POSITION_SIZE_USD = 100

# PPM (Profit Per Minute) Settings
TARGET_PPM = 0.5  # Target $0.50 per minute
STOP_PPM = -0.2   # Stop if losing more than $0.20 per minute
MAX_TRADE_TIME = 15  # Maximum minutes to hold a trade

# Position Skew Thresholds
MIN_TOTAL_POSITION_VALUE = 10_000_000  # $10M minimum total position value to consider
SKEW_THRESHOLD = 0.7  # 70% of positions in one direction to consider it skewed
SINGLE_PLAYER_THRESHOLD = 0.5  # If one player has 50% of total positions

# Liquidation Thresholds
LIQUIDATION_TRIGGER_AMOUNT = 1_000_000  # $1M in liquidations to trigger entry
LIQUIDATION_LOOKBACK_MINUTES = 10

# File paths
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
POSITIONS_FILE = os.path.join(DATA_DIR, "dragonfly_positions.csv")

class DragonflyBot:
    def __init__(self):
        self.account = eth_account.Account.from_key(HYPER_LIQUID_KEY)
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        self.exchange = Exchange(self.account, constants.MAINNET_API_URL)
        
        # Ensure data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Initialize or load positions DataFrame
        self.load_positions()
        
    def load_positions(self):
        """Load positions from CSV or create new DataFrame"""
        try:
            if os.path.exists(POSITIONS_FILE):
                self.positions_df = pd.read_csv(POSITIONS_FILE)
                # Convert timestamp string back to datetime
                self.positions_df['entry_time'] = pd.to_datetime(self.positions_df['entry_time'])
            else:
                self.positions_df = pd.DataFrame(columns=[
                    'order_id', 'symbol', 'direction', 'size', 'entry_price',
                    'entry_time', 'position_value', 'is_active'
                ])
                self.save_positions()
        except Exception as e:
            print(f"❌ Error loading positions: {str(e)}")
            self.positions_df = pd.DataFrame(columns=[
                'order_id', 'symbol', 'direction', 'size', 'entry_price',
                'entry_time', 'position_value', 'is_active'
            ])
            
    def save_positions(self):
        """Save positions to CSV"""
        try:
            self.positions_df.to_csv(POSITIONS_FILE, index=False)
        except Exception as e:
            print(f"❌ Error saving positions: {str(e)}")
            
    def get_active_position(self):
        """Get the currently active position if any"""
        active_positions = self.positions_df[self.positions_df['is_active']]
        if not active_positions.empty:
            return active_positions.iloc[0]
        return None
        
    def get_ppm(self, position_row):
        """Calculate current Profit Per Minute for a position"""
        if position_row is None:
            return 0
            
        positions, in_pos, size, pos_sym, current_price, pnl, is_long = n.get_position(SYMBOL, self.account)
        if not in_pos:
            return 0
            
        # Calculate minutes elapsed
        minutes_elapsed = (datetime.now() - position_row['entry_time']).total_seconds() / 60
        if minutes_elapsed < 1:
            return 0
            
        # Calculate profit
        profit = float(pnl) * position_row['position_value']
        
        return profit / minutes_elapsed
        
    def analyze_positions(self):
        """Analyze aggregate positions from Hyperliquid"""
        print("🔍 Analyzing positions...")
        
        try:
            positions_df, agg_df = get_positions()
            
            if agg_df is None or agg_df.empty:
                print("❌ No position data available")
                return None, 0, 0
                
            # Filter for our symbol
            symbol_positions = agg_df[agg_df['coin'] == SYMBOL].copy()
            
            if symbol_positions.empty:
                print(f"❌ No positions found for {SYMBOL}")
                return None, 0, 0
                
            # Calculate total position value and direction skew
            total_value = symbol_positions['total_value'].sum()
            long_value = symbol_positions[symbol_positions['direction'] == 'LONG']['total_value'].sum()
            short_value = symbol_positions[symbol_positions['direction'] == 'SHORT']['total_value'].sum()
            
            # Calculate skew
            if total_value > 0:
                long_skew = long_value / total_value
                short_skew = short_value / total_value
            else:
                long_skew = short_skew = 0
                
            # Find largest single position
            max_single_position = positions_df[positions_df['coin'] == SYMBOL]['position_value'].max()
            single_player_dominance = max_single_position / total_value if total_value > 0 else 0
            
            print(f"💰 Total Position Value: ${total_value:,.2f}")
            print(f"📈 Long Skew: {long_skew:.2%}")
            print(f"📉 Short Skew: {short_skew:.2%}")
            print(f"🐋 Largest Single Position: ${max_single_position:,.2f} ({single_player_dominance:.2%} of total)")
            
            # Determine if market is significantly skewed
            if total_value < MIN_TOTAL_POSITION_VALUE:
                print("⚠️ Total position value below threshold")
                return None, 0, 0
                
            if single_player_dominance > SINGLE_PLAYER_THRESHOLD:
                print("🐋 Single player dominance detected")
                if long_skew > SKEW_THRESHOLD:
                    return "long", long_skew, single_player_dominance
                elif short_skew > SKEW_THRESHOLD:
                    return "short", short_skew, single_player_dominance
                    
            return None, 0, 0
            
        except Exception as e:
            print(f"❌ Error analyzing positions: {str(e)}")
            return None, 0, 0
            
    def check_liquidations(self, skewed_direction):
        """Check for significant liquidations in the opposite direction"""
        try:
            liquidations = n.get_liquidations()
            liquidations_data = json.loads(liquidations)
            
            # Look at 10-minute liquidations
            recent_liqs = liquidations_data.get('10min', {})
            long_liqs = float(recent_liqs.get('Long Liquidations', 0))
            short_liqs = float(recent_liqs.get('Short Liquidations', 0))
            
            print(f"💥 Recent Liquidations - Longs: ${long_liqs:,.2f}, Shorts: ${short_liqs:,.2f}")
            
            # If market is skewed long, look for long liquidations
            if skewed_direction == "long" and long_liqs > LIQUIDATION_TRIGGER_AMOUNT:
                return True
            # If market is skewed short, look for short liquidations
            elif skewed_direction == "short" and short_liqs > LIQUIDATION_TRIGGER_AMOUNT:
                return True
                
            return False
            
        except Exception as e:
            print(f"❌ Error checking liquidations: {str(e)}")
            return False
            
    def manage_position(self):
        """Manage existing position based on PPM"""
        positions, in_pos, size, pos_sym, current_price, pnl, is_long = n.get_position(SYMBOL, self.account)
        active_position = self.get_active_position()
        
        if not in_pos or active_position is None:
            # Mark position as inactive if we're not in it anymore
            if active_position is not None:
                self.positions_df.loc[self.positions_df['is_active'], 'is_active'] = False
                self.save_positions()
            return
            
        current_ppm = self.get_ppm(active_position)
        minutes_elapsed = (datetime.now() - active_position['entry_time']).total_seconds() / 60
        
        print(f"📊 Current PPM: ${current_ppm:.2f}/minute")
        print(f"⏱️ Time in trade: {minutes_elapsed:.1f} minutes")
        
        # Check if we should close based on PPM or time
        if current_ppm <= STOP_PPM:
            print(f"🛑 Closing position - PPM below stop threshold: ${current_ppm:.2f}/minute")
            n.kill_switch(SYMBOL, self.account)
            self.positions_df.loc[self.positions_df['is_active'], 'is_active'] = False
            self.save_positions()
            
        elif current_ppm >= TARGET_PPM:
            print(f"🎯 Closing position - PPM target reached: ${current_ppm:.2f}/minute")
            n.kill_switch(SYMBOL, self.account)
            self.positions_df.loc[self.positions_df['is_active'], 'is_active'] = False
            self.save_positions()
            
        elif minutes_elapsed >= MAX_TRADE_TIME:
            print(f"⏰ Closing position - Maximum trade time reached: {minutes_elapsed:.1f} minutes")
            n.kill_switch(SYMBOL, self.account)
            self.positions_df.loc[self.positions_df['is_active'], 'is_active'] = False
            self.save_positions()
            
    def enter_position(self, direction):
        """Enter a new position"""
        positions, in_pos, size, pos_sym, current_price, pnl, is_long = n.get_position(SYMBOL, self.account)
        
        if in_pos:
            print("⚠️ Already in position, skipping entry")
            return
            
        # Get current price
        ask, bid, _ = n.ask_bid(SYMBOL)
        
        # Adjust position size based on leverage
        lev, pos_size = n.adjust_leverage_usd_size(SYMBOL, POSITION_SIZE_USD, LEVERAGE, self.account)
        
        # Place the order
        if direction == "short":
            print(f"📉 Entering SHORT position - Size: {pos_size}, Price: {ask}")
            order_result = n.limit_order(SYMBOL, False, pos_size, ask, False, self.account)
        else:
            print(f"📈 Entering LONG position - Size: {pos_size}, Price: {bid}")
            order_result = n.limit_order(SYMBOL, True, pos_size, bid, False, self.account)
            
        # Extract order ID from result and store position info
        try:
            order_id = order_result['response']['data']['statuses'][0]['oid']
            
            # Add new position to DataFrame
            new_position = {
                'order_id': order_id,
                'symbol': SYMBOL,
                'direction': direction,
                'size': pos_size,
                'entry_price': ask if direction == "short" else bid,
                'entry_time': datetime.now(),
                'position_value': POSITION_SIZE_USD,
                'is_active': True
            }
            
            self.positions_df = pd.concat([self.positions_df, pd.DataFrame([new_position])], ignore_index=True)
            self.save_positions()
            
            print(f"✅ Position stored with order ID: {order_id}")
            
        except Exception as e:
            print(f"❌ Error storing position: {str(e)}")
            
    def run(self):
        """Main bot loop"""
        print("\n" + "="*50)
        print("🐉 Dragonfly Bot Starting...")
        print("="*50)
        
        try:
            # First check if we're in a position
            positions, in_pos, size, pos_sym, current_price, pnl, is_long = n.get_position(SYMBOL, self.account)
            
            if in_pos:
                print("📊 Managing existing position...")
                self.manage_position()
                return
                
            # Analyze market positions
            skewed_direction, skew_amount, single_player_dominance = self.analyze_positions()
            
            if not skewed_direction:
                print("📊 No significant position skew detected")
                return
                
            print(f"📊 Market skewed {skewed_direction.upper()} - {skew_amount:.2%}")
            
            # Check for liquidations
            if self.check_liquidations(skewed_direction):
                print(f"💥 Significant liquidations detected - Entering {skewed_direction.upper()} position")
                self.enter_position(skewed_direction)
            else:
                print("📉 No significant liquidations detected")
                
        except Exception as e:
            print(f"❌ Error in main loop: {str(e)}")
            
def bot():
    """Initialize and run the bot"""
    dragon = DragonflyBot()
    dragon.run()
    
# Initial run
bot()

# Schedule the bot to run every minute
schedule.every(1).minutes.do(bot)

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        time.sleep(10)