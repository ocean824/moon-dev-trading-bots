"""
🌙 Moon Dev's Whale Cleaner with Withdrawals 🐋💰
=================================================
This script analyzes whale P&L by tracking deposits AND withdrawals.

The key insight: A wallet with $0 balance might have withdrawn $2M profit!
We calculate TRUE P&L:
    Net P&L = Current Balance + Total Withdrawals - Total Deposits

Categories:
    - Winners: Made money (P&L > 0)
    - REKT: Lost >90% of deposits

Moon Dev 🌙
"""

import requests
import time
import os
import csv
from datetime import datetime
from termcolor import colored
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init(autoreset=True)

# ===== CONFIGURATION =====
TEST_MODE = True  # Set to False for full 5,004 wallet analysis
TEST_SAMPLE_SIZE = 100  # Number of wallets to test in TEST_MODE
DELAY_BETWEEN_REQUESTS = 0.3  # Seconds between API calls (increased to avoid rate limits)
REKT_THRESHOLD = 0.90  # Lost >90% = REKT
MAX_RETRIES = 3  # Max retries on rate limit
# ==========================

# API Configuration
API_URL = "https://api.hyperliquid.xyz/info"
HEADERS = {"Content-Type": "application/json"}

# File paths
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(DATA_DIR, 'data')
INPUT_FILE = os.path.join(DATA_DIR, 'whales_to_clean.txt')
OUTPUT_CSV = os.path.join(DATA_DIR, 'whale_pnl_analysis.csv')

# Moon Dev Banner
MOON_DEV_BANNER = f"""{Fore.CYAN}
   __  ___                    ____
  /  |/  /___  ____  ____    / __ \\___  _  __
 / /|_/ / __ \\/ __ \\/ __ \\  / / / / _ \\| |/_/
/ /  / / /_/ / /_/ / / / / / /_/ /  __/>  <
/_/  /_/\\____/\\____/_/ /_(_)____/\\___/_/|_|

{Fore.MAGENTA}🐋 WHALE P&L ANALYZER 💰{Fore.RESET}
{Fore.YELLOW}Tracking deposits AND withdrawals for TRUE P&L! 📊{Fore.RESET}
"""

# Stats tracking
stats = {
    'total_analyzed': 0,
    'winners': 0,
    'small_loss': 0,
    'medium_loss': 0,
    'big_loss': 0,
    'rekt': 0,
    'errors': 0,
    'total_deposits': 0,
    'total_withdrawals': 0,
    'total_current_balance': 0,
    'biggest_winner_pnl': 0,
    'biggest_winner_address': '',
    'biggest_loser_pnl': 0,
    'biggest_loser_address': '',
    'all_pnl_percents': []
}

# Results storage for CSV
results = []


def get_user_balance(address: str) -> float:
    """
    Get user's perp equity (account value) from Hyperliquid API.
    Moon Dev's balance checker! 💰
    """
    payload = {
        "type": "clearinghouseState",
        "user": address
    }

    for retry in range(MAX_RETRIES):
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=10)

        # Handle rate limiting
        if response.status_code == 429:
            wait_time = 2 * (retry + 1)  # Exponential backoff
            print(f"{Fore.YELLOW}⚠️ Rate limited on balance, waiting {wait_time}s... (retry {retry+1}/{MAX_RETRIES})")
            time.sleep(wait_time)
            continue

        response.raise_for_status()
        data = response.json()

        # Get account value from marginSummary
        if 'marginSummary' in data and 'accountValue' in data['marginSummary']:
            return float(data['marginSummary']['accountValue'])

        return 0.0

    # If all retries failed, return 0
    print(f"{Fore.RED}❌ Failed to get balance for {address[:10]}... after {MAX_RETRIES} retries")
    return 0.0


def get_user_ledger(address: str) -> tuple:
    """
    Get user's deposit and withdrawal history from Hyperliquid API.
    Moon Dev's ledger fetcher! 📒

    Returns: (total_deposits, total_withdrawals)
    """
    payload = {
        "type": "userNonFundingLedgerUpdates",
        "user": address,
        "startTime": 0  # Get all history
    }

    for retry in range(MAX_RETRIES):
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)

        # Handle rate limiting
        if response.status_code == 429:
            wait_time = 2 * (retry + 1)  # Exponential backoff
            print(f"{Fore.YELLOW}⚠️ Rate limited on ledger, waiting {wait_time}s... (retry {retry+1}/{MAX_RETRIES})")
            time.sleep(wait_time)
            continue

        response.raise_for_status()
        data = response.json()

        total_deposits = 0.0
        total_withdrawals = 0.0

        # Parse ledger events
        if isinstance(data, list):
            for event in data:
                delta = event.get('delta', {})
                delta_type = delta.get('type', '')

                if delta_type == 'deposit':
                    usdc = float(delta.get('usdc', 0))
                    total_deposits += usdc
                elif delta_type == 'withdraw':
                    usdc = abs(float(delta.get('usdc', 0)))
                    total_withdrawals += usdc

        return total_deposits, total_withdrawals

    # If all retries failed, return zeros
    print(f"{Fore.RED}❌ Failed to get ledger for {address[:10]}... after {MAX_RETRIES} retries")
    return 0.0, 0.0


def categorize_pnl(pnl_percent: float) -> str:
    """
    Categorize the P&L percentage into loss buckets.
    Moon Dev's P&L categorizer! 📊
    """
    if pnl_percent > 0:
        return 'winner'
    elif pnl_percent >= -10:
        return 'small_loss'
    elif pnl_percent >= -50:
        return 'medium_loss'
    elif pnl_percent >= -90:
        return 'big_loss'
    else:
        return 'rekt'


def analyze_whales():
    """
    Main function to analyze whale P&L with deposits and withdrawals.
    Moon Dev's whale audit! 🐋📊
    """
    global results

    print(MOON_DEV_BANNER)

    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"{Fore.RED}❌ Input file not found: {INPUT_FILE}")
        return

    # Read all addresses
    with open(INPUT_FILE, 'r') as f:
        addresses = [line.strip() for line in f if line.strip().startswith('0x')]

    total_addresses = len(addresses)

    # Apply test mode limit
    if TEST_MODE:
        addresses = addresses[:TEST_SAMPLE_SIZE]
        print(f"\n{Fore.YELLOW}🧪 TEST MODE: Analyzing {TEST_SAMPLE_SIZE} wallets (set TEST_MODE=False for full analysis)")

    print(f"\n{Fore.CYAN}📊 Found {Fore.GREEN}{len(addresses):,}{Fore.CYAN} whale addresses to analyze")
    print(f"{Fore.CYAN}📁 Input: {Fore.WHITE}{INPUT_FILE}")
    print(f"\n{Fore.YELLOW}🚀 Starting P&L analysis... Moon Dev says let's see who got REKT! 🌙\n")

    start_time = datetime.now()

    for i, address in enumerate(addresses):
        stats['total_analyzed'] += 1

        # Progress update every 10 addresses
        if (i + 1) % 10 == 0 or i == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(addresses) - i - 1) / rate if rate > 0 else 0
            print(f"{Fore.CYAN}📊 Progress: {i+1:,}/{len(addresses):,} ({(i+1)/len(addresses)*100:.1f}%) | "
                  f"Winners: {Fore.GREEN}{stats['winners']}{Fore.CYAN} | "
                  f"REKT: {Fore.RED}{stats['rekt']}{Fore.CYAN} | "
                  f"ETA: {Fore.YELLOW}{eta/60:.1f}m")

        # Fetch balance
        balance = get_user_balance(address)
        time.sleep(DELAY_BETWEEN_REQUESTS)

        # Fetch deposits/withdrawals
        deposits, withdrawals = get_user_ledger(address)
        time.sleep(DELAY_BETWEEN_REQUESTS)

        # Skip if no deposits (can't calculate P&L)
        if deposits == 0:
            continue

        # Calculate P&L
        net_pnl = balance + withdrawals - deposits
        pnl_percent = (net_pnl / deposits) * 100

        # Update stats
        stats['total_deposits'] += deposits
        stats['total_withdrawals'] += withdrawals
        stats['total_current_balance'] += balance
        stats['all_pnl_percents'].append(pnl_percent)

        # Categorize
        category = categorize_pnl(pnl_percent)
        if category == 'winner':
            stats['winners'] += 1
        elif category == 'small_loss':
            stats['small_loss'] += 1
        elif category == 'medium_loss':
            stats['medium_loss'] += 1
        elif category == 'big_loss':
            stats['big_loss'] += 1
        elif category == 'rekt':
            stats['rekt'] += 1

        # Track biggest winner/loser
        if net_pnl > stats['biggest_winner_pnl']:
            stats['biggest_winner_pnl'] = net_pnl
            stats['biggest_winner_address'] = address
        if net_pnl < stats['biggest_loser_pnl']:
            stats['biggest_loser_pnl'] = net_pnl
            stats['biggest_loser_address'] = address

        # Store result for CSV
        results.append({
            'address': address,
            'deposits': deposits,
            'withdrawals': withdrawals,
            'current_balance': balance,
            'net_pnl': net_pnl,
            'pnl_percent': pnl_percent,
            'category': category
        })

        # Show some interesting finds
        if category == 'rekt' and (stats['rekt'] <= 5 or stats['rekt'] % 50 == 0):
            print(f"{Fore.RED}💀 REKT: {address[:10]}...{address[-6:]} | "
                  f"Deposited: ${deposits:,.0f} | Lost: {pnl_percent:.1f}%")
        elif category == 'winner' and net_pnl > 100000:
            print(f"{Fore.GREEN}🏆 BIG WINNER: {address[:10]}...{address[-6:]} | "
                  f"P&L: ${net_pnl:,.0f} (+{pnl_percent:.1f}%)")

    # Print final results
    print_results()

    # Save to CSV
    save_results()


def print_results():
    """
    Print formatted analysis results.
    Moon Dev's results display! 📊
    """
    total = stats['total_analyzed']
    if total == 0:
        print(f"{Fore.RED}❌ No wallets analyzed!")
        return

    # Calculate percentages
    winners_pct = (stats['winners'] / total) * 100 if total > 0 else 0
    small_loss_pct = (stats['small_loss'] / total) * 100 if total > 0 else 0
    medium_loss_pct = (stats['medium_loss'] / total) * 100 if total > 0 else 0
    big_loss_pct = (stats['big_loss'] / total) * 100 if total > 0 else 0
    rekt_pct = (stats['rekt'] / total) * 100 if total > 0 else 0

    # Calculate median and average P&L
    pnl_list = stats['all_pnl_percents']
    if pnl_list:
        pnl_list_sorted = sorted(pnl_list)
        median_pnl = pnl_list_sorted[len(pnl_list_sorted) // 2]
        avg_pnl = sum(pnl_list) / len(pnl_list)
    else:
        median_pnl = 0
        avg_pnl = 0

    print(f"\n{Fore.GREEN}{'='*70}")
    print(f"{Fore.CYAN}🌙 MOON DEV'S WHALE P&L ANALYSIS COMPLETE! 🐋💰")
    print(f"{Fore.GREEN}{'='*70}")

    print(f"\n{Fore.WHITE}📊 P&L BREAKDOWN:")
    print(f"{Fore.WHITE}{'─'*50}")
    print(f"{Fore.WHITE}| {'Category':<20} | {'Count':>8} | {'Pct':>8} |")
    print(f"{Fore.WHITE}{'─'*50}")
    print(f"{Fore.GREEN}| {'🏆 Winners':<20} | {stats['winners']:>8,} | {winners_pct:>7.1f}% |")
    print(f"{Fore.YELLOW}| {'📉 Small Loss (<10%)':<20} | {stats['small_loss']:>8,} | {small_loss_pct:>7.1f}% |")
    print(f"{Fore.YELLOW}| {'📉📉 Medium Loss':<20} | {stats['medium_loss']:>8,} | {medium_loss_pct:>7.1f}% |")
    print(f"{Fore.RED}| {'📉📉📉 Big Loss':<20} | {stats['big_loss']:>8,} | {big_loss_pct:>7.1f}% |")
    print(f"{Fore.RED}| {'💀 REKT (>90% loss)':<20} | {stats['rekt']:>8,} | {rekt_pct:>7.1f}% |")
    print(f"{Fore.WHITE}{'─'*50}")
    print(f"{Fore.WHITE}| {'TOTAL':<20} | {total:>8,} | {'100.0%':>8} |")
    print(f"{Fore.WHITE}{'─'*50}")

    print(f"\n{Fore.WHITE}💰 MONEY FLOW:")
    print(f"{Fore.WHITE}   Total Deposited:    {Fore.GREEN}${stats['total_deposits']:>15,.2f}")
    print(f"{Fore.WHITE}   Total Withdrawn:    {Fore.CYAN}${stats['total_withdrawals']:>15,.2f}")
    net_flow = stats['total_withdrawals'] - stats['total_deposits']
    flow_color = Fore.GREEN if net_flow > 0 else Fore.RED
    print(f"{Fore.WHITE}   Net Cashflow:       {flow_color}${net_flow:>15,.2f}")
    print(f"{Fore.WHITE}   Current Balances:   {Fore.YELLOW}${stats['total_current_balance']:>15,.2f}")

    print(f"\n{Fore.WHITE}📈 P&L STATS:")
    if stats['biggest_winner_address']:
        print(f"{Fore.WHITE}   Biggest Winner:     {Fore.GREEN}${stats['biggest_winner_pnl']:>15,.2f}")
        print(f"{Fore.WHITE}   Biggest Winner Addr: {Fore.GREEN}{stats['biggest_winner_address']}")
    if stats['biggest_loser_address']:
        print(f"{Fore.WHITE}   Biggest Loser:      {Fore.RED}${stats['biggest_loser_pnl']:>15,.2f}")
        print(f"{Fore.WHITE}   Biggest Loser Addr:  {Fore.RED}{stats['biggest_loser_address']}")
    print(f"{Fore.WHITE}   Median P&L:         {Fore.YELLOW}{median_pnl:>15.1f}%")
    print(f"{Fore.WHITE}   Average P&L:        {Fore.YELLOW}{avg_pnl:>15.1f}%")

    print(f"\n{Fore.GREEN}{'='*70}")
    print(f"{Fore.MAGENTA}🔥 THE VERDICT:")
    print(f"{Fore.WHITE}   \"Even accounting for withdrawals, {Fore.RED}{rekt_pct:.1f}%{Fore.WHITE} of whales got {Fore.RED}REKT{Fore.WHITE} (lost >90%)\"")
    print(f"{Fore.WHITE}   \"Only {Fore.GREEN}{winners_pct:.1f}%{Fore.WHITE} of whales are actually profitable\"")
    print(f"{Fore.GREEN}{'='*70}")

    print(f"\n{Fore.MAGENTA}🌙 Moon Dev says: The numbers don't lie! 📊🐋\n")


def save_results():
    """
    Save results to CSV file.
    Moon Dev's CSV saver! 💾
    """
    if not results:
        print(f"{Fore.YELLOW}⚠️ No results to save!")
        return

    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['address', 'deposits', 'withdrawals',
                                                'current_balance', 'net_pnl', 'pnl_percent', 'category'])
        writer.writeheader()
        writer.writerows(results)

    print(f"{Fore.GREEN}💾 Results saved to: {OUTPUT_CSV}")
    print(f"{Fore.GREEN}   Total rows: {len(results):,}")


if __name__ == "__main__":
    analyze_whales()
