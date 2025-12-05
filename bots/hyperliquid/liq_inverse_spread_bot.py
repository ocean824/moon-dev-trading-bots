"""
🌙 Moon Dev's Inverse Liquidation Spread Bot 🚀
===============================================
Live trading bot for Hyperliquid based on the Inverse Liquidation Spread Strategy.

Strategy Logic (CONTRARIAN - Trade AGAINST liquidations with SPREAD):
- When long positions are liquidated → BUY (catch the bounce after cascade)
- When short positions are liquidated → SELL (catch the reversal after squeeze)

SPREAD FEATURE: Wait for price to move X% from liquidation price before entering.
- For longs liquidated: wait for price to DROP spread_pct% then BUY
- For shorts liquidated: wait for price to RISE spread_pct% then SELL

Example: If longs liquidated at $100k with 0.5% spread, we buy at $99,500

Theory: Liquidations create oversold/overbought conditions that tend to reverse.

Risk Controls:
1. P&L Close - Check TP/SL on every loop
2. Position check before any action
3. Cancel previous orders before new ones
4. Never double order if already in position
5. Loop until exit complete
6. Spread-based entry for better prices

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

{Fore.MAGENTA}🚀 Inverse Liquidation SPREAD Bot 🌙{Fore.RESET}
{Fore.YELLOW}Contrarian play - Fade the liquidation cascade! 📈📉{Fore.RESET}
"""

# ===== CONFIGURATION =====
# Symbol to trade
SYMBOL = 'BTC'
LEVERAGE = 5

# Position size - START SMALL!
POSITION_SIZE_USD = 10  # Moon Dev says: Always start with $10!

# Strategy Parameters (from backtest)
LIQUIDATION_THRESHOLD = 975000  # $975k minimum liquidation volume to trigger
SPREAD_PCT = 0.5  # 0.5% spread - wait for price to move this % before entry
TAKE_PROFIT_PERCENT = 1.0  # 1% take profit
STOP_LOSS_PERCENT = -2.0  # 2% stop loss (negative for the pnl_close function)
MAX_HOLD_HOURS = 2  # Maximum holding period

# Liquidation lookback window (in minutes)
LIQUIDATION_LOOKBACK_MINUTES = 5

# Signal expiry - how long a pending signal stays valid (in minutes)
SIGNAL_EXPIRY_MINUTES = 30

# Loop interval
LOOP_INTERVAL_SECONDS = 15  # Run every 15 seconds

# Initialize account
account = LocalAccount = eth_account.Account.from_key(HYPER_LIQUID_KEY)

# Initialize API
api = MoonDevAPI()

# Track entry time for time-based exit
position_entry_time = None

# Track pending signals (contrarian with spread)
pending_long_signal = False
pending_short_signal = False
long_target_price = 0
short_target_price = 0
signal_timestamp = None


def quiet_get_position(symbol, account):
    """Wrapper for get_position that suppresses verbose output."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    result = n.get_position(symbol, account)
    sys.stdout = old_stdout
    return result


def quiet_pnl_close(symbol, target, max_loss, account):
    """Wrapper for pnl_close that suppresses verbose output and returns status."""
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout

    n.pnl_close(symbol, target, max_loss, account)

    sys.stdout = old_stdout
    captured_output = new_stdout.getvalue()

    if "closing position WIN" in captured_output:
        print(f"{Fore.GREEN}✅ Moon Dev: Position closed for PROFIT! Target {target}% reached 🎯")
        return True
    elif "closing position LOSS" in captured_output:
        print(f"{Fore.RED}⛔ Moon Dev: Position closed for STOP LOSS at {max_loss}% 🛑")
        return True
    return False


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


def check_time_based_exit(entry_time):
    """Check if we should exit based on max hold time."""
    if entry_time is None:
        return False

    elapsed_hours = (datetime.now() - entry_time).total_seconds() / 3600
    if elapsed_hours >= MAX_HOLD_HOURS:
        print(f"{Fore.YELLOW}⏰ Moon Dev: Max hold time ({MAX_HOLD_HOURS}h) reached! Time to exit.")
        return True
    return False


def check_signal_expiry():
    """Check if pending signal has expired."""
    global pending_long_signal, pending_short_signal, signal_timestamp

    if signal_timestamp is None:
        return

    elapsed_minutes = (datetime.now() - signal_timestamp).total_seconds() / 60
    if elapsed_minutes >= SIGNAL_EXPIRY_MINUTES:
        print(f"{Fore.YELLOW}⏰ Moon Dev: Pending signal expired after {SIGNAL_EXPIRY_MINUTES} minutes")
        pending_long_signal = False
        pending_short_signal = False
        signal_timestamp = None


def print_banner():
    """Print Moon Dev banner."""
    print(MOON_DEV_BANNER)
    print(f"{Fore.CYAN}{'='*70}")
    print(f"{Fore.YELLOW}🚀 Moon Dev's Inverse Liquidation SPREAD Bot Starting!")
    print(f"{Fore.YELLOW}💰 Trading {SYMBOL} with {LEVERAGE}x leverage")
    print(f"{Fore.YELLOW}💵 Position size: ${POSITION_SIZE_USD}")
    print(f"{Fore.YELLOW}📊 Liquidation Threshold: ${LIQUIDATION_THRESHOLD:,}")
    print(f"{Fore.YELLOW}📏 Entry Spread: {SPREAD_PCT}%")
    print(f"{Fore.YELLOW}🎯 Take Profit: {TAKE_PROFIT_PERCENT}% | Stop Loss: {abs(STOP_LOSS_PERCENT)}%")
    print(f"{Fore.YELLOW}⏰ Max Hold: {MAX_HOLD_HOURS} hours")
    print(f"{Fore.CYAN}{'='*70}\n")


def bot():
    """Main bot loop - Moon Dev's Inverse Liquidation Spread Strategy."""
    global position_entry_time
    global pending_long_signal, pending_short_signal
    global long_target_price, short_target_price, signal_timestamp

    try:
        print(f"\n{Fore.CYAN}{'='*70}")
        print(f"{Fore.YELLOW}🌙 Moon Dev Inverse Spread Bot - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.CYAN}{'='*70}")

        # STEP 1: Get current position
        print(f"{Fore.CYAN}📍 Step 1: Checking current position...")
        positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = quiet_get_position(SYMBOL, account)

        # STEP 2: If in position, check P&L close first
        if im_in_pos:
            print(f"{Fore.GREEN}📈 Moon Dev: In position! Checking exit conditions...")
            print(f"{Fore.YELLOW}   Side: {'LONG' if is_long else 'SHORT'} | Size: {pos_size} | PnL: {pnl_perc:.2f}%")

            # Clear pending signals when in position
            pending_long_signal = False
            pending_short_signal = False

            # Check time-based exit first
            if check_time_based_exit(position_entry_time):
                print(f"{Fore.YELLOW}🕐 Moon Dev: Time exit triggered! Closing position...")
                n.cancel_all_orders(account)
                n.kill_switch(SYMBOL, account)
                position_entry_time = None
                print(f"{Fore.GREEN}✅ Position closed due to max hold time")
                return

            # Check P&L exit (TP/SL)
            closed = quiet_pnl_close(SYMBOL, TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, account)

            if closed:
                position_entry_time = None
                return

            # Still in position, just monitoring
            elapsed = (datetime.now() - position_entry_time).total_seconds() / 60 if position_entry_time else 0
            print(f"{Fore.CYAN}⏳ Moon Dev: Position open for {elapsed:.1f} minutes. Monitoring...")
            return

        # STEP 3: Not in position - check for pending signals or new signals
        print(f"{Fore.YELLOW}📉 Moon Dev: Not in position. Checking signals...")

        # Check signal expiry
        check_signal_expiry()

        # Get current price
        ask, bid, l2_data = n.ask_bid(SYMBOL)
        current_price = (ask + bid) / 2
        print(f"{Fore.CYAN}💰 Current price: ${current_price:,.2f} (Ask: ${ask:,.2f}, Bid: ${bid:,.2f})")

        # Check if we have pending signals that have reached target
        if pending_long_signal and current_price <= long_target_price:
            print(f"{Fore.GREEN}🎯 Moon Dev: LONG target price ${long_target_price:,.2f} reached!")
            print(f"{Fore.GREEN}📈 Executing contrarian LONG entry!")

            # Cancel any existing orders
            n.cancel_all_orders(account)

            # Adjust leverage and size
            lev, pos_size = n.adjust_leverage_usd_size(SYMBOL, POSITION_SIZE_USD, LEVERAGE, account)

            # Place BUY order at bid
            entry_price = bid
            print(f"{Fore.GREEN}🛒 Moon Dev: Placing BUY order for {pos_size} {SYMBOL} @ ${entry_price:,.2f}")
            n.limit_order(SYMBOL, True, pos_size, entry_price, False, account)

            # Wait for fill
            time.sleep(3)
            positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = quiet_get_position(SYMBOL, account)

            if im_in_pos:
                position_entry_time = datetime.now()
                print(f"{Fore.GREEN}✅ Moon Dev: LONG Position OPENED! Entry: ${entry_px:,.2f}")

            # Clear signal
            pending_long_signal = False
            long_target_price = 0
            signal_timestamp = None
            return

        if pending_short_signal and current_price >= short_target_price:
            print(f"{Fore.RED}🎯 Moon Dev: SHORT target price ${short_target_price:,.2f} reached!")
            print(f"{Fore.RED}📉 Executing contrarian SHORT entry!")

            # Cancel any existing orders
            n.cancel_all_orders(account)

            # Adjust leverage and size
            lev, pos_size = n.adjust_leverage_usd_size(SYMBOL, POSITION_SIZE_USD, LEVERAGE, account)

            # Place SELL order at ask
            entry_price = ask
            print(f"{Fore.RED}💸 Moon Dev: Placing SELL order for {pos_size} {SYMBOL} @ ${entry_price:,.2f}")
            n.limit_order(SYMBOL, False, pos_size, entry_price, False, account)

            # Wait for fill
            time.sleep(3)
            positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = quiet_get_position(SYMBOL, account)

            if im_in_pos:
                position_entry_time = datetime.now()
                print(f"{Fore.GREEN}✅ Moon Dev: SHORT Position OPENED! Entry: ${entry_px:,.2f}")

            # Clear signal
            pending_short_signal = False
            short_target_price = 0
            signal_timestamp = None
            return

        # STEP 4: Check for new liquidation signals
        long_liq_amount, short_liq_amount = get_recent_liquidations()

        print(f"{Fore.CYAN}💧 Liquidations (last {LIQUIDATION_LOOKBACK_MINUTES} min):")
        print(f"{Fore.RED}   📉 LONG liquidations: ${long_liq_amount:,.2f}")
        print(f"{Fore.GREEN}   📈 SHORT liquidations: ${short_liq_amount:,.2f}")

        # INVERSE/CONTRARIAN STRATEGY with SPREAD:
        # - BUY when longs are liquidated (catch the bounce)
        # - But wait for price to DROP spread_pct% first for better entry
        # - SELL when shorts are liquidated (catch the reversal)
        # - But wait for price to RISE spread_pct% first for better entry

        if long_liq_amount >= LIQUIDATION_THRESHOLD:
            # Set target price: current price minus spread
            long_target_price = current_price * (1 - SPREAD_PCT / 100)
            pending_long_signal = True
            pending_short_signal = False  # Cancel any pending short
            signal_timestamp = datetime.now()

            print(f"{Fore.GREEN}🔥 INVERSE SIGNAL: Long liquidations ${long_liq_amount:,.0f} >= ${LIQUIDATION_THRESHOLD:,}")
            print(f"{Fore.GREEN}📈 Setting LONG entry target: ${long_target_price:,.2f} ({SPREAD_PCT}% below current)")
            print(f"{Fore.YELLOW}⏳ Waiting for price to drop to target...")

        elif short_liq_amount >= LIQUIDATION_THRESHOLD:
            # Set target price: current price plus spread
            short_target_price = current_price * (1 + SPREAD_PCT / 100)
            pending_short_signal = True
            pending_long_signal = False  # Cancel any pending long
            signal_timestamp = datetime.now()

            print(f"{Fore.RED}🔥 INVERSE SIGNAL: Short liquidations ${short_liq_amount:,.0f} >= ${LIQUIDATION_THRESHOLD:,}")
            print(f"{Fore.RED}📉 Setting SHORT entry target: ${short_target_price:,.2f} ({SPREAD_PCT}% above current)")
            print(f"{Fore.YELLOW}⏳ Waiting for price to rise to target...")

        else:
            # No new signal
            if pending_long_signal:
                distance = ((current_price - long_target_price) / current_price) * 100
                print(f"{Fore.YELLOW}⏳ Moon Dev: Pending LONG signal. Target: ${long_target_price:,.2f} ({distance:.2f}% away)")
            elif pending_short_signal:
                distance = ((short_target_price - current_price) / current_price) * 100
                print(f"{Fore.YELLOW}⏳ Moon Dev: Pending SHORT signal. Target: ${short_target_price:,.2f} ({distance:.2f}% away)")
            else:
                print(f"{Fore.YELLOW}⏳ Moon Dev: No signal. Waiting for liquidations >= ${LIQUIDATION_THRESHOLD:,}")

        print(f"\n{Fore.MAGENTA}🌕 Moon Dev's Inverse Spread Bot complete! See you next loop! 🤖")

    except Exception as e:
        print(f"{Fore.RED}❌ Moon Dev Bot Error: {str(e)}")
        print(f"{Fore.RED}📋 Stack trace:\n{traceback.format_exc()}")


if __name__ == "__main__":
    print_banner()

    print(f"{Fore.GREEN}✅ Moon Dev: Starting main loop (every {LOOP_INTERVAL_SECONDS} seconds)...")
    print(f"{Fore.YELLOW}Press Ctrl+C to stop\n")

    # Initial run
    bot()

    # Main loop
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
            time.sleep(10)  # Wait before retry
