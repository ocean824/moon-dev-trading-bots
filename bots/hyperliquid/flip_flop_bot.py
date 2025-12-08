"""
🌙 Moon Dev's Flip Flop Bot 🚀
===============================
Live trading bot for Hyperliquid based on the Flip Flop Liquidation Strategy.

Strategy Logic:
1. BUY when LONG liquidations exceed threshold (buy the dip)
2. When LONG hits TP or SL, FLIP to SHORT
3. Hold SHORT until it hits TP or SL
4. Done - two trades per signal, back to waiting

OPTIMIZED PARAMETERS (529% backtest return):
- Liquidation Threshold: $500,000
- Lookback: 15 minutes (3 x 5min bars)
- Take Profit: 1.5%
- Stop Loss: 10%

Risk Controls:
1. P&L Close - Check TP/SL on every loop FIRST
2. Position check before any action
3. Cancel previous orders before new ones
4. Never double order if already in position
5. Loop until limit orders filled
6. Proper decimal handling for Hyperliquid

State Machine:
WAITING -> TRADE1_LONG -> TRADE2_SHORT -> WAITING

Moon Dev 🌙
"""

import sys
import os
import time
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
import io

# Add the parent directory to the Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

# Import local modules
from bots.hyperliquid import nice_funcs as n
from api import MoonDevAPI

# Initialize colorama
colorama.init(autoreset=True)

# Load environment variables
load_dotenv()

# Get the Hyperliquid key
HYPER_LIQUID_KEY = os.getenv('HYPER_LIQUID_KEY')

# Moon Dev ASCII Art Banner
MOON_DEV_BANNER = f"""{Fore.CYAN}
   __  ___                    ____
  /  |/  /___  ____  ____    / __ \___  _  __
 / /|_/ / __ \/ __ \/ __ \  / / / / _ \| |/_/
/ /  / / /_/ / /_/ / / / / / /_/ /  __/>  <
/_/  /_/\____/\____/_/ /_(_)____/\___/_/|_|

{Fore.MAGENTA}🚀 FLIP FLOP Liquidation Bot 🌙{Fore.RESET}
{Fore.YELLOW}Buy the dip, flip to short, profit twice! 📈📉{Fore.RESET}
"""

# ===== CONFIGURATION =====
# Symbol to trade
SYMBOL = 'BTC'
LEVERAGE = 5

# Position size - START SMALL!
POSITION_SIZE_USD = 10  # Moon Dev says: Always start with $10!

# Strategy Parameters (OPTIMIZED from backtest - 529% return!)
LIQUIDATION_THRESHOLD = 500000  # $500k minimum long liquidation volume
TAKE_PROFIT_PERCENT = 1.5  # 1.5% take profit
STOP_LOSS_PERCENT = -10.0  # 10% stop loss (negative for pnl_close function)

# Liquidation lookback window (15 minutes = 3 x 5min bars from backtest)
LIQUIDATION_LOOKBACK_MINUTES = 15

# Loop interval
LOOP_INTERVAL_SECONDS = 30  # Run every 30 seconds

# Max retries for order fills
MAX_FILL_RETRIES = 10
FILL_CHECK_INTERVAL = 3  # seconds between fill checks

# Initialize account
account = LocalAccount = eth_account.Account.from_key(HYPER_LIQUID_KEY)

# Initialize API
api = MoonDevAPI()

# State tracking
# States: 'waiting', 'trade1_long', 'trade2_short'
bot_state = 'waiting'
trade1_entry_price = 0
trade2_entry_price = 0


def quiet_get_position(symbol, account):
    """Wrapper for get_position that suppresses verbose output."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    result = n.get_position(symbol, account)
    sys.stdout = old_stdout
    return result


def get_recent_liquidations():
    """
    Get recent liquidations from Moon Dev API for BTC.
    Returns long_liq_amount, short_liq_amount
    """
    try:
        print(f"{Fore.CYAN}🔍 Moon Dev: Fetching liquidation data...")
        liquidations = api.get_liquidation_data(limit=1000)

        if liquidations is None or liquidations.empty:
            print(f"{Fore.YELLOW}⚠️ No liquidation data available")
            return 0, 0

        # Filter to BTC only
        symbol_liquidations = liquidations[liquidations.iloc[:, 0] == SYMBOL]

        if symbol_liquidations.empty:
            print(f"{Fore.YELLOW}⚠️ No liquidations found for {SYMBOL}")
            return 0, 0

        # Filter by time - last LIQUIDATION_LOOKBACK_MINUTES
        current_time_ms = int(datetime.now().timestamp() * 1000)
        cutoff_time_ms = current_time_ms - (LIQUIDATION_LOOKBACK_MINUTES * 60 * 1000)

        recent_liquidations = symbol_liquidations[symbol_liquidations.iloc[:, 10].astype(float) >= cutoff_time_ms]

        if recent_liquidations.empty:
            return 0, 0

        # Long liquidations have side == "SELL" (forced selling of longs)
        # Short liquidations have side == "BUY" (forced buying to cover shorts)
        long_liqs = recent_liquidations[recent_liquidations.iloc[:, 1] == "SELL"]
        short_liqs = recent_liquidations[recent_liquidations.iloc[:, 1] == "BUY"]

        long_liq_amount = long_liqs.iloc[:, 11].astype(float).sum() if not long_liqs.empty else 0
        short_liq_amount = short_liqs.iloc[:, 11].astype(float).sum() if not short_liqs.empty else 0

        return long_liq_amount, short_liq_amount

    except Exception as e:
        print(f"{Fore.RED}❌ Error getting liquidations: {str(e)}")
        return 0, 0


def wait_for_fill(symbol, account, max_retries=MAX_FILL_RETRIES):
    """Wait for order to fill, return True if filled."""
    for i in range(max_retries):
        time.sleep(FILL_CHECK_INTERVAL)
        positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = quiet_get_position(symbol, account)
        if im_in_pos:
            return True, entry_px, is_long
        print(f"{Fore.YELLOW}⏳ Moon Dev: Waiting for fill... attempt {i+1}/{max_retries}")
    return False, 0, False


def print_banner():
    """Print Moon Dev banner."""
    print(MOON_DEV_BANNER)
    print(f"{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}🚀 Moon Dev's FLIP FLOP Bot Starting!")
    print(f"{Fore.YELLOW}💰 Trading {SYMBOL} with {LEVERAGE}x leverage")
    print(f"{Fore.YELLOW}💵 Position size: ${POSITION_SIZE_USD}")
    print(f"{Fore.YELLOW}📊 Liquidation Threshold: ${LIQUIDATION_THRESHOLD:,}")
    print(f"{Fore.YELLOW}📊 Lookback: {LIQUIDATION_LOOKBACK_MINUTES} minutes")
    print(f"{Fore.YELLOW}🎯 Take Profit: {TAKE_PROFIT_PERCENT}% | Stop Loss: {abs(STOP_LOSS_PERCENT)}%")
    print(f"{Fore.CYAN}{'='*70}\n")


def bot():
    """Main bot loop - Moon Dev's Flip Flop Strategy."""
    global bot_state, trade1_entry_price, trade2_entry_price

    try:
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.YELLOW}🌙 Moon Dev Flip Flop Bot - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.YELLOW}📊 Current State: {bot_state.upper()}")
        print(f"{Fore.CYAN}{'='*70}")

        # ============================================
        # STEP 1: ALWAYS check position first
        # ============================================
        print(f"{Fore.CYAN}📍 Step 1: Checking current position...")
        positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = quiet_get_position(SYMBOL, account)

        # ============================================
        # STEP 2: If in position, check P&L FIRST
        # ============================================
        if im_in_pos:
            print(f"{Fore.GREEN}📈 Moon Dev: In position!")
            print(f"{Fore.YELLOW}   State: {bot_state} | Side: {'LONG' if is_long else 'SHORT'} | Size: {pos_size} | PnL: {pnl_perc:.2f}%")

            # STATE: TRADE1_LONG - Check for TP/SL to flip to short
            if bot_state == 'trade1_long' and is_long:
                # Check TP
                if pnl_perc >= TAKE_PROFIT_PERCENT:
                    print(f"{Fore.GREEN}🎯 Moon Dev: Trade 1 HIT TAKE PROFIT at {pnl_perc:.2f}%!")
                    print(f"{Fore.YELLOW}🔄 Flipping to SHORT...")

                    # Cancel orders and close position
                    n.cancel_all_orders(account)
                    n.kill_switch(SYMBOL, account)
                    time.sleep(2)

                    # Confirm closed
                    positions, im_in_pos, _, _, _, _, _ = quiet_get_position(SYMBOL, account)
                    if im_in_pos:
                        print(f"{Fore.YELLOW}⏳ Position still open, waiting...")
                        return

                    # Now flip to SHORT
                    print(f"{Fore.RED}📉 Moon Dev: Opening SHORT position...")
                    n.cancel_all_orders(account)
                    ask, bid, _ = n.ask_bid(SYMBOL)
                    lev, size = n.adjust_leverage_usd_size(SYMBOL, POSITION_SIZE_USD, LEVERAGE, account)

                    print(f"{Fore.RED}💸 Placing SELL order for {size} {SYMBOL} @ ${ask:,.2f}")
                    n.limit_order(SYMBOL, False, size, ask, False, account)

                    filled, entry, _ = wait_for_fill(SYMBOL, account)
                    if filled:
                        trade2_entry_price = entry
                        bot_state = 'trade2_short'
                        print(f"{Fore.GREEN}✅ Moon Dev: SHORT Position OPENED! Entry: ${entry:,.2f}")
                    else:
                        print(f"{Fore.YELLOW}⚠️ Short order not filled, will retry next loop")
                        bot_state = 'waiting'  # Reset if flip failed
                    return

                # Check SL
                elif pnl_perc <= STOP_LOSS_PERCENT:
                    print(f"{Fore.RED}🛑 Moon Dev: Trade 1 HIT STOP LOSS at {pnl_perc:.2f}%!")
                    print(f"{Fore.YELLOW}🔄 Flipping to SHORT...")

                    # Cancel orders and close position
                    n.cancel_all_orders(account)
                    n.kill_switch(SYMBOL, account)
                    time.sleep(2)

                    # Confirm closed
                    positions, im_in_pos, _, _, _, _, _ = quiet_get_position(SYMBOL, account)
                    if im_in_pos:
                        print(f"{Fore.YELLOW}⏳ Position still open, waiting...")
                        return

                    # Now flip to SHORT
                    print(f"{Fore.RED}📉 Moon Dev: Opening SHORT position...")
                    n.cancel_all_orders(account)
                    ask, bid, _ = n.ask_bid(SYMBOL)
                    lev, size = n.adjust_leverage_usd_size(SYMBOL, POSITION_SIZE_USD, LEVERAGE, account)

                    print(f"{Fore.RED}💸 Placing SELL order for {size} {SYMBOL} @ ${ask:,.2f}")
                    n.limit_order(SYMBOL, False, size, ask, False, account)

                    filled, entry, _ = wait_for_fill(SYMBOL, account)
                    if filled:
                        trade2_entry_price = entry
                        bot_state = 'trade2_short'
                        print(f"{Fore.GREEN}✅ Moon Dev: SHORT Position OPENED! Entry: ${entry:,.2f}")
                    else:
                        print(f"{Fore.YELLOW}⚠️ Short order not filled, will retry next loop")
                        bot_state = 'waiting'  # Reset if flip failed
                    return

                else:
                    print(f"{Fore.CYAN}⏳ Trade 1 LONG running. PnL: {pnl_perc:.2f}% | TP: {TAKE_PROFIT_PERCENT}% | SL: {STOP_LOSS_PERCENT}%")
                    return

            # STATE: TRADE2_SHORT - Check for TP/SL to complete cycle
            elif bot_state == 'trade2_short' and not is_long:
                # Check TP (for short, profit is when price drops)
                if pnl_perc >= TAKE_PROFIT_PERCENT:
                    print(f"{Fore.GREEN}🎯 Moon Dev: Trade 2 SHORT HIT TAKE PROFIT at {pnl_perc:.2f}%!")
                    print(f"{Fore.GREEN}🏆 Flip Flop cycle COMPLETE! Both trades profitable!")

                    n.cancel_all_orders(account)
                    n.kill_switch(SYMBOL, account)

                    bot_state = 'waiting'
                    trade1_entry_price = 0
                    trade2_entry_price = 0
                    print(f"{Fore.GREEN}✅ Moon Dev: Back to WAITING for next signal")
                    return

                # Check SL
                elif pnl_perc <= STOP_LOSS_PERCENT:
                    print(f"{Fore.RED}🛑 Moon Dev: Trade 2 SHORT HIT STOP LOSS at {pnl_perc:.2f}%!")

                    n.cancel_all_orders(account)
                    n.kill_switch(SYMBOL, account)

                    bot_state = 'waiting'
                    trade1_entry_price = 0
                    trade2_entry_price = 0
                    print(f"{Fore.YELLOW}⚠️ Moon Dev: Cycle ended with loss. Back to WAITING")
                    return

                else:
                    print(f"{Fore.CYAN}⏳ Trade 2 SHORT running. PnL: {pnl_perc:.2f}% | TP: {TAKE_PROFIT_PERCENT}% | SL: {STOP_LOSS_PERCENT}%")
                    return

            # STATE MISMATCH - position doesn't match expected state
            else:
                print(f"{Fore.YELLOW}⚠️ Moon Dev: State mismatch! State={bot_state}, is_long={is_long}")
                print(f"{Fore.YELLOW}   Resetting state to match position...")
                if is_long:
                    bot_state = 'trade1_long'
                    trade1_entry_price = entry_px
                else:
                    bot_state = 'trade2_short'
                    trade2_entry_price = entry_px
                return

        # ============================================
        # NOT IN POSITION
        # ============================================
        else:
            # If we think we should be in a position but we're not, reset
            if bot_state != 'waiting':
                print(f"{Fore.YELLOW}⚠️ Moon Dev: Expected to be in position (state={bot_state}) but not. Resetting...")
                bot_state = 'waiting'
                trade1_entry_price = 0
                trade2_entry_price = 0

            # STATE: WAITING - Look for liquidation signal
            print(f"{Fore.YELLOW}📉 Moon Dev: WAITING state. Looking for liquidation signals...")

            # Get recent liquidations
            long_liq_amount, short_liq_amount = get_recent_liquidations()

            print(f"{Fore.CYAN}💧 Liquidations (last {LIQUIDATION_LOOKBACK_MINUTES} min):")
            print(f"{Fore.RED}   📉 LONG liquidations: ${long_liq_amount:,.2f}")
            print(f"{Fore.GREEN}   📈 SHORT liquidations: ${short_liq_amount:,.2f}")

            # Check for entry signal - LONG liquidations trigger BUY
            if long_liq_amount >= LIQUIDATION_THRESHOLD:
                print(f"{Fore.GREEN}🔥 FLIP FLOP SIGNAL: Long liquidations ${long_liq_amount:,.0f} >= ${LIQUIDATION_THRESHOLD:,}")
                print(f"{Fore.GREEN}📈 Starting Trade 1: Going LONG!")

                # Cancel any existing orders first
                n.cancel_all_orders(account)

                # Get price and adjust leverage
                ask, bid, _ = n.ask_bid(SYMBOL)
                lev, size = n.adjust_leverage_usd_size(SYMBOL, POSITION_SIZE_USD, LEVERAGE, account)

                print(f"{Fore.CYAN}💰 Price - Ask: ${ask:,.2f}, Bid: ${bid:,.2f}")
                print(f"{Fore.YELLOW}📊 Leverage: {lev}x | Size: {size}")

                # Place BUY order at bid for better fill
                entry_price = bid
                print(f"{Fore.GREEN}🛒 Moon Dev: Placing BUY order for {size} {SYMBOL} @ ${entry_price:,.2f}")
                n.limit_order(SYMBOL, True, size, entry_price, False, account)

                # Wait for fill
                filled, entry, is_long = wait_for_fill(SYMBOL, account)
                if filled and is_long:
                    trade1_entry_price = entry
                    bot_state = 'trade1_long'
                    print(f"{Fore.GREEN}✅ Moon Dev: Trade 1 LONG Position OPENED! Entry: ${entry:,.2f}")
                else:
                    print(f"{Fore.YELLOW}⚠️ Order not filled. Will retry next loop.")
                    n.cancel_all_orders(account)

            else:
                print(f"{Fore.YELLOW}⏳ Moon Dev: No signal. Need ${LIQUIDATION_THRESHOLD:,} in long liquidations.")

        print(f"\n{Fore.MAGENTA}🌕 Moon Dev's Flip Flop Bot loop complete! 🤖")

    except Exception as e:
        print(f"{Fore.RED}❌ Moon Dev Bot Error: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")


if __name__ == "__main__":
    print_banner()

    print(f"{Fore.GREEN}✅ Moon Dev: Starting main loop (every {LOOP_INTERVAL_SECONDS} seconds)...")
    print(f"{Fore.YELLOW}Press Ctrl+C to stop\n")

    # Initial run
    bot()

    # Main loop with try/except for resilience
    while True:
        try:
            time.sleep(LOOP_INTERVAL_SECONDS)
            bot()
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}🌙 Moon Dev: Bot stopped by user. Goodbye! 👋")
            break
        except Exception as e:
            print(f"{Fore.RED}❌ Loop error: {e}")
            print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")
            print(f"{Fore.YELLOW}🔄 Moon Dev: Restarting in 10 seconds...")
            time.sleep(10)  # Wait before retry
