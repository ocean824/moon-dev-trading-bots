"""
🌙 Moon Dev's Whale Cleaner 🧹
================================
Cleans the whale list by removing addresses with < $10,000 perp equity.

Reads whales_to_clean.txt and creates clean_whale_list.txt with only
the whales that still have $10k+ in their accounts.

Moon Dev 🌙
"""

import requests
import time
import os
from datetime import datetime
from termcolor import colored
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init(autoreset=True)

# ===== CONFIGURATION =====
MIN_BALANCE_USD = 10000  # Minimum balance to keep whale on list
DELAY_BETWEEN_REQUESTS = 0.1  # Seconds between API calls (avoid rate limiting)
# ==========================

# API Configuration
API_URL = "https://api.hyperliquid.xyz/info"
HEADERS = {"Content-Type": "application/json"}

# File paths
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(DATA_DIR, 'data')
INPUT_FILE = os.path.join(DATA_DIR, 'whales_to_clean.txt')
OUTPUT_FILE = os.path.join(DATA_DIR, 'clean_whale_list.txt')

# Moon Dev Banner
MOON_DEV_BANNER = f"""{Fore.CYAN}
   __  ___                    ____
  /  |/  /___  ____  ____    / __ \\___  _  __
 / /|_/ / __ \\/ __ \\/ __ \\  / / / / _ \\| |/_/
/ /  / / /_/ / /_/ / / / / / /_/ /  __/>  <
/_/  /_/\\____/\\____/_/ /_(_)____/\\___/_/|_|

{Fore.MAGENTA}🧹 WHALE CLEANER 🐋{Fore.RESET}
{Fore.YELLOW}Filtering out the broke whales! 💸{Fore.RESET}
"""

# Stats tracking
stats = {
    'total_checked': 0,
    'kept': 0,
    'removed': 0,
    'errors': 0,
    'total_balance_kept': 0,
    'largest_balance': 0,
    'largest_whale': '',
    'smallest_kept': float('inf'),
    'removed_addresses': []
}


def get_user_balance(address: str) -> float:
    """
    Get user's perp equity (account value) from Hyperliquid API.
    Moon Dev's balance checker! 💰
    """
    payload = {
        "type": "clearinghouseState",
        "user": address
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=10)

        # Handle rate limiting
        if response.status_code == 429:
            print(f"{Fore.YELLOW}⚠️ Rate limited, waiting 2s...")
            time.sleep(2)
            response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=10)

        response.raise_for_status()
        data = response.json()

        # Get account value from marginSummary
        if 'marginSummary' in data and 'accountValue' in data['marginSummary']:
            return float(data['marginSummary']['accountValue'])

        return 0.0

    except Exception as e:
        stats['errors'] += 1
        return -1  # Return -1 to indicate error (will keep address to be safe)


def clean_whale_list():
    """
    Main function to clean the whale list.
    Moon Dev's whale audit! 🐋🧹
    """
    print(MOON_DEV_BANNER)

    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"{Fore.RED}❌ Input file not found: {INPUT_FILE}")
        return

    # Read all addresses
    with open(INPUT_FILE, 'r') as f:
        addresses = [line.strip() for line in f if line.strip().startswith('0x')]

    total_addresses = len(addresses)
    print(f"\n{Fore.CYAN}📊 Found {Fore.GREEN}{total_addresses:,}{Fore.CYAN} whale addresses to check")
    print(f"{Fore.CYAN}💰 Minimum balance to keep: {Fore.GREEN}${MIN_BALANCE_USD:,}")
    print(f"{Fore.CYAN}📁 Input: {Fore.WHITE}{INPUT_FILE}")
    print(f"{Fore.CYAN}📁 Output: {Fore.WHITE}{OUTPUT_FILE}")
    print(f"\n{Fore.YELLOW}🚀 Starting whale audit... Moon Dev says let's clean house! 🌙\n")

    start_time = datetime.now()
    clean_whales = []

    for i, address in enumerate(addresses):
        stats['total_checked'] += 1

        # Get balance
        balance = get_user_balance(address)

        # Progress update every 50 addresses
        if (i + 1) % 50 == 0 or i == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (total_addresses - i - 1) / rate if rate > 0 else 0
            print(f"{Fore.CYAN}📊 Progress: {i+1:,}/{total_addresses:,} ({(i+1)/total_addresses*100:.1f}%) | "
                  f"Kept: {Fore.GREEN}{stats['kept']}{Fore.CYAN} | "
                  f"Removed: {Fore.RED}{stats['removed']}{Fore.CYAN} | "
                  f"ETA: {Fore.YELLOW}{eta/60:.1f}m")

        # Handle errors (keep address to be safe)
        if balance == -1:
            clean_whales.append(address)
            stats['kept'] += 1
            continue

        # Check if whale meets minimum balance
        if balance >= MIN_BALANCE_USD:
            clean_whales.append(address)
            stats['kept'] += 1
            stats['total_balance_kept'] += balance

            if balance > stats['largest_balance']:
                stats['largest_balance'] = balance
                stats['largest_whale'] = address

            if balance < stats['smallest_kept']:
                stats['smallest_kept'] = balance
        else:
            stats['removed'] += 1
            stats['removed_addresses'].append((address, balance))

            # Show removed whales occasionally
            if stats['removed'] <= 10 or stats['removed'] % 100 == 0:
                print(f"{Fore.RED}🗑️ Removed: {address[:10]}...{address[-6:]} - ${balance:,.2f}")

        # Small delay to avoid rate limiting
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Write clean list
    with open(OUTPUT_FILE, 'w') as f:
        for address in clean_whales:
            f.write(f"{address}\n")

    # Print final stats
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n{Fore.GREEN}{'='*60}")
    print(f"{Fore.CYAN}🌙 MOON DEV'S WHALE CLEANING COMPLETE! 🧹🐋")
    print(f"{Fore.GREEN}{'='*60}")
    print(f"\n{Fore.WHITE}📊 FINAL STATS:")
    print(f"{Fore.WHITE}   Total checked: {Fore.CYAN}{stats['total_checked']:,}")
    print(f"{Fore.WHITE}   Whales KEPT (>=${MIN_BALANCE_USD:,}): {Fore.GREEN}{stats['kept']:,}")
    print(f"{Fore.WHITE}   Whales REMOVED (<${MIN_BALANCE_USD:,}): {Fore.RED}{stats['removed']:,}")
    print(f"{Fore.WHITE}   Errors (kept anyway): {Fore.YELLOW}{stats['errors']:,}")
    print(f"\n{Fore.WHITE}💰 BALANCE STATS:")
    print(f"{Fore.WHITE}   Total balance of kept whales: {Fore.GREEN}${stats['total_balance_kept']:,.2f}")
    print(f"{Fore.WHITE}   Largest whale: {Fore.GREEN}${stats['largest_balance']:,.2f}")
    print(f"{Fore.WHITE}   Largest whale address: {Fore.YELLOW}{stats['largest_whale']}")
    if stats['smallest_kept'] != float('inf'):
        print(f"{Fore.WHITE}   Smallest kept balance: {Fore.CYAN}${stats['smallest_kept']:,.2f}")
    print(f"\n{Fore.WHITE}⏱️ Time elapsed: {Fore.CYAN}{elapsed/60:.1f} minutes")
    print(f"{Fore.WHITE}📁 Clean whale list saved to: {Fore.GREEN}{OUTPUT_FILE}")
    print(f"\n{Fore.MAGENTA}🌙 Moon Dev says: {stats['removed']:,} broke whales removed! 🐋💸\n")


if __name__ == "__main__":
    clean_whale_list()
