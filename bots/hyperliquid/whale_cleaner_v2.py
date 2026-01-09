"""
🌙 Moon Dev's Whale Cleaner V2 - CLEAN DATA ONLY 🐋✨
=====================================================
This version ONLY analyzes wallets with COMPLETE transaction history.

Key improvements:
1. SKIP wallets with 2000+ events (API limit = incomplete data)
2. Internal transfers IN = deposits (money from other wallets)
3. Internal transfers OUT = withdrawals (money to other wallets)

This gives us ACCURATE P&L for wallets we can fully verify!

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

colorama.init(autoreset=True)

# ===== CONFIGURATION =====
TEST_MODE = True  # Set to False for full analysis
TEST_SAMPLE_SIZE = 100  # Wallets to attempt (will skip incomplete ones)
DELAY_BETWEEN_REQUESTS = 0.3
MAX_RETRIES = 3
REKT_THRESHOLD = 0.90  # Lost >90% = REKT
EVENT_LIMIT = 2000  # API limit - skip wallets at or above this
# ==========================

API_URL = "https://api.hyperliquid.xyz/info"
HEADERS = {"Content-Type": "application/json"}

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
INPUT_FILE = os.path.join(DATA_DIR, 'whales_to_clean.txt')
OUTPUT_CSV = os.path.join(DATA_DIR, 'whale_pnl_v2_clean.csv')

MOON_DEV_BANNER = f"""{Fore.CYAN}
   __  ___                    ____
  /  |/  /___  ____  ____    / __ \\___  _  __
 / /|_/ / __ \\/ __ \\/ __ \\  / / / / _ \\| |/_/
/ /  / / /_/ / /_/ / / / / / /_/ /  __/>  <
/_/  /_/\\____/\\____/_/ /_(_)____/\\___/_/|_|

{Fore.MAGENTA}🐋 WHALE P&L ANALYZER V2 - CLEAN DATA ONLY ✨{Fore.RESET}
{Fore.YELLOW}Only analyzing wallets with COMPLETE history! 📊{Fore.RESET}
"""

# Stats
stats = {
    'total_attempted': 0,
    'skipped_incomplete': 0,
    'skipped_no_deposits': 0,
    'analyzed': 0,
    'winners': 0,
    'small_loss': 0,
    'medium_loss': 0,
    'big_loss': 0,
    'rekt': 0,
    'total_deposits': 0,
    'total_withdrawals': 0,
    'total_balance': 0,
    'biggest_winner_pnl': 0,
    'biggest_winner_addr': '',
    'biggest_winner_pct': 0,
    'biggest_loser_pnl': 0,
    'biggest_loser_addr': '',
    'biggest_loser_pct': 0,
    'all_pnl_pcts': []
}

results = []


def get_user_balance(address: str) -> float:
    """Get current balance."""
    payload = {"type": "clearinghouseState", "user": address}

    for retry in range(MAX_RETRIES):
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=10)
        if response.status_code == 429:
            time.sleep(2 * (retry + 1))
            continue
        response.raise_for_status()
        data = response.json()
        if 'marginSummary' in data and 'accountValue' in data['marginSummary']:
            return float(data['marginSummary']['accountValue'])
        return 0.0
    return 0.0


def get_full_ledger(address: str) -> list:
    """Get all ledger events."""
    payload = {
        "type": "userNonFundingLedgerUpdates",
        "user": address,
        "startTime": 0
    }

    for retry in range(MAX_RETRIES):
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
        if response.status_code == 429:
            time.sleep(2 * (retry + 1))
            continue
        response.raise_for_status()
        return response.json()
    return []


def analyze_wallet(address: str) -> dict:
    """
    Analyze a wallet's P&L with COMPLETE data verification.

    Returns None if wallet has incomplete data (2000+ events).

    Counts:
    - Deposits: deposit + internalTransfer IN + subAccountTransfer IN
    - Withdrawals: withdraw + internalTransfer OUT + subAccountTransfer OUT

    Moon Dev's clean analysis! ✨
    """
    # Get ledger first to check event count
    ledger = get_full_ledger(address)
    time.sleep(DELAY_BETWEEN_REQUESTS)

    # Check for API limit
    if len(ledger) >= EVENT_LIMIT:
        return {'status': 'incomplete', 'events': len(ledger)}

    # Get balance
    balance = get_user_balance(address)
    time.sleep(DELAY_BETWEEN_REQUESTS)

    # Calculate deposits and withdrawals including internal transfers
    total_deposits = 0.0
    total_withdrawals = 0.0
    deposit_count = 0
    withdrawal_count = 0
    internal_in = 0.0
    internal_out = 0.0

    for event in ledger:
        delta = event.get('delta', {})
        delta_type = delta.get('type', '')

        if delta_type == 'deposit':
            usdc = float(delta.get('usdc', 0))
            total_deposits += usdc
            deposit_count += 1

        elif delta_type == 'withdraw':
            usdc = abs(float(delta.get('usdc', 0)))
            total_withdrawals += usdc
            withdrawal_count += 1

        elif delta_type == 'internalTransfer':
            usdc = float(delta.get('usdc', 0))
            destination = delta.get('destination', '').lower()

            # If destination is this wallet, it's money IN (treat as deposit)
            if destination == address.lower():
                total_deposits += usdc
                internal_in += usdc
            else:
                # Money going OUT (treat as withdrawal)
                total_withdrawals += usdc
                internal_out += usdc

        elif delta_type == 'subAccountTransfer':
            usdc = float(delta.get('usdc', 0))
            destination = delta.get('destination', '').lower()

            if destination == address.lower():
                total_deposits += usdc
                internal_in += usdc
            else:
                total_withdrawals += usdc
                internal_out += usdc

    # Skip if no deposits
    if total_deposits == 0:
        return {'status': 'no_deposits'}

    # Calculate P&L
    net_pnl = balance + total_withdrawals - total_deposits
    pnl_pct = (net_pnl / total_deposits) * 100

    # Categorize
    if pnl_pct > 0:
        category = 'winner'
    elif pnl_pct >= -10:
        category = 'small_loss'
    elif pnl_pct >= -50:
        category = 'medium_loss'
    elif pnl_pct >= -90:
        category = 'big_loss'
    else:
        category = 'rekt'

    return {
        'status': 'complete',
        'address': address,
        'events': len(ledger),
        'balance': balance,
        'deposits': total_deposits,
        'withdrawals': total_withdrawals,
        'internal_in': internal_in,
        'internal_out': internal_out,
        'net_pnl': net_pnl,
        'pnl_pct': pnl_pct,
        'category': category,
        'deposit_count': deposit_count,
        'withdrawal_count': withdrawal_count
    }


def run_analysis():
    """Main analysis with clean data only."""
    global results

    print(MOON_DEV_BANNER)

    if not os.path.exists(INPUT_FILE):
        print(f"{Fore.RED}❌ Input file not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, 'r') as f:
        addresses = [line.strip() for line in f if line.strip().startswith('0x')]

    if TEST_MODE:
        addresses = addresses[:TEST_SAMPLE_SIZE]
        print(f"\n{Fore.YELLOW}🧪 TEST MODE: Checking up to {TEST_SAMPLE_SIZE} wallets")

    print(f"{Fore.CYAN}📊 Will skip wallets with {EVENT_LIMIT}+ events (incomplete data)")
    print(f"{Fore.CYAN}📊 Internal transfers IN = deposits, OUT = withdrawals")
    print(f"\n{Fore.YELLOW}🚀 Starting CLEAN analysis... Moon Dev says quality over quantity! 🌙\n")

    start_time = datetime.now()

    for i, address in enumerate(addresses):
        stats['total_attempted'] += 1

        # Progress
        if (i + 1) % 10 == 0 or i == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(addresses) - i - 1) / rate if rate > 0 else 0
            print(f"{Fore.CYAN}📊 Progress: {i+1}/{len(addresses)} | "
                  f"Clean: {Fore.GREEN}{stats['analyzed']}{Fore.CYAN} | "
                  f"Skipped: {Fore.YELLOW}{stats['skipped_incomplete']}{Fore.CYAN} | "
                  f"ETA: {eta/60:.1f}m")

        result = analyze_wallet(address)

        if result['status'] == 'incomplete':
            stats['skipped_incomplete'] += 1
            print(f"{Fore.YELLOW}⏭️ SKIP: {address[:12]}... ({result['events']} events = incomplete)")
            continue

        if result['status'] == 'no_deposits':
            stats['skipped_no_deposits'] += 1
            continue

        # Valid complete data!
        stats['analyzed'] += 1
        stats['total_deposits'] += result['deposits']
        stats['total_withdrawals'] += result['withdrawals']
        stats['total_balance'] += result['balance']
        stats['all_pnl_pcts'].append(result['pnl_pct'])

        # Categorize
        cat = result['category']
        if cat == 'winner':
            stats['winners'] += 1
        elif cat == 'small_loss':
            stats['small_loss'] += 1
        elif cat == 'medium_loss':
            stats['medium_loss'] += 1
        elif cat == 'big_loss':
            stats['big_loss'] += 1
        elif cat == 'rekt':
            stats['rekt'] += 1

        # Track extremes
        if result['net_pnl'] > stats['biggest_winner_pnl']:
            stats['biggest_winner_pnl'] = result['net_pnl']
            stats['biggest_winner_addr'] = address
            stats['biggest_winner_pct'] = result['pnl_pct']
        if result['net_pnl'] < stats['biggest_loser_pnl']:
            stats['biggest_loser_pnl'] = result['net_pnl']
            stats['biggest_loser_addr'] = address
            stats['biggest_loser_pct'] = result['pnl_pct']

        # Store for CSV
        results.append(result)

        # Show interesting finds
        if cat == 'rekt':
            print(f"{Fore.RED}💀 REKT: {address[:12]}... | Deposited ${result['deposits']:,.0f} | Lost {result['pnl_pct']:.1f}%")
        elif cat == 'winner' and result['net_pnl'] > 1000000:
            print(f"{Fore.GREEN}🏆 WINNER: {address[:12]}... | P&L ${result['net_pnl']:,.0f} (+{result['pnl_pct']:.1f}%)")

    print_results()
    save_results()


def print_results():
    """Print final results."""
    total = stats['analyzed']
    if total == 0:
        print(f"{Fore.RED}❌ No wallets with complete data found!")
        return

    winners_pct = stats['winners'] / total * 100
    small_loss_pct = stats['small_loss'] / total * 100
    medium_loss_pct = stats['medium_loss'] / total * 100
    big_loss_pct = stats['big_loss'] / total * 100
    rekt_pct = stats['rekt'] / total * 100

    pnl_list = sorted(stats['all_pnl_pcts'])
    median_pnl = pnl_list[len(pnl_list) // 2] if pnl_list else 0
    avg_pnl = sum(pnl_list) / len(pnl_list) if pnl_list else 0

    print(f"\n{Fore.GREEN}{'='*70}")
    print(f"{Fore.CYAN}🌙 MOON DEV'S CLEAN DATA ANALYSIS COMPLETE! ✨")
    print(f"{Fore.GREEN}{'='*70}")

    print(f"\n{Fore.WHITE}📊 DATA QUALITY:")
    print(f"   {Fore.WHITE}Wallets attempted: {Fore.CYAN}{stats['total_attempted']}")
    print(f"   {Fore.YELLOW}Skipped (incomplete data): {stats['skipped_incomplete']}")
    print(f"   {Fore.YELLOW}Skipped (no deposits): {stats['skipped_no_deposits']}")
    print(f"   {Fore.GREEN}CLEAN DATA ANALYZED: {stats['analyzed']}")

    print(f"\n{Fore.WHITE}📊 P&L BREAKDOWN (VERIFIED COMPLETE DATA ONLY):")
    print(f"{Fore.WHITE}{'─'*55}")
    print(f"{Fore.WHITE}| {'Category':<22} | {'Count':>8} | {'Pct':>10} |")
    print(f"{Fore.WHITE}{'─'*55}")
    print(f"{Fore.GREEN}| {'🏆 Winners':<22} | {stats['winners']:>8} | {winners_pct:>9.1f}% |")
    print(f"{Fore.YELLOW}| {'📉 Small Loss (<10%)':<22} | {stats['small_loss']:>8} | {small_loss_pct:>9.1f}% |")
    print(f"{Fore.YELLOW}| {'📉📉 Medium Loss (10-50%)':<22} | {stats['medium_loss']:>8} | {medium_loss_pct:>9.1f}% |")
    print(f"{Fore.RED}| {'📉📉📉 Big Loss (50-90%)':<22} | {stats['big_loss']:>8} | {big_loss_pct:>9.1f}% |")
    print(f"{Fore.RED}| {'💀 REKT (>90% loss)':<22} | {stats['rekt']:>8} | {rekt_pct:>9.1f}% |")
    print(f"{Fore.WHITE}{'─'*55}")
    print(f"{Fore.WHITE}| {'TOTAL ANALYZED':<22} | {total:>8} | {'100.0%':>10} |")
    print(f"{Fore.WHITE}{'─'*55}")

    print(f"\n{Fore.WHITE}💰 MONEY FLOW (CLEAN DATA):")
    print(f"   {Fore.GREEN}Total Deposited:    ${stats['total_deposits']:>18,.2f}")
    print(f"   {Fore.CYAN}Total Withdrawn:    ${stats['total_withdrawals']:>18,.2f}")
    net_flow = stats['total_withdrawals'] - stats['total_deposits']
    flow_color = Fore.GREEN if net_flow > 0 else Fore.RED
    print(f"   {flow_color}Net Cashflow:       ${net_flow:>18,.2f}")
    print(f"   {Fore.YELLOW}Current Balances:   ${stats['total_balance']:>18,.2f}")

    print(f"\n{Fore.WHITE}📈 P&L STATS:")
    if stats['biggest_winner_addr']:
        print(f"   {Fore.GREEN}Biggest Winner: ${stats['biggest_winner_pnl']:,.2f} (+{stats['biggest_winner_pct']:.1f}%)")
        print(f"   {Fore.GREEN}  → {stats['biggest_winner_addr']}")
    if stats['biggest_loser_addr']:
        print(f"   {Fore.RED}Biggest Loser: ${stats['biggest_loser_pnl']:,.2f} ({stats['biggest_loser_pct']:.1f}%)")
        print(f"   {Fore.RED}  → {stats['biggest_loser_addr']}")
    print(f"   {Fore.WHITE}Median P&L: {Fore.YELLOW}{median_pnl:>10.1f}%")
    print(f"   {Fore.WHITE}Average P&L: {Fore.YELLOW}{avg_pnl:>9.1f}%")

    # The key stat
    losers_total = stats['small_loss'] + stats['medium_loss'] + stats['big_loss'] + stats['rekt']
    losers_pct = losers_total / total * 100 if total > 0 else 0

    print(f"\n{Fore.GREEN}{'='*70}")
    print(f"{Fore.MAGENTA}🔥 THE VERDICT (CLEAN VERIFIED DATA):")
    print(f"{Fore.WHITE}   Out of {Fore.CYAN}{total}{Fore.WHITE} wallets with COMPLETE transaction history:")
    print(f"   • {Fore.GREEN}{stats['winners']}{Fore.WHITE} ({Fore.GREEN}{winners_pct:.1f}%{Fore.WHITE}) are profitable")
    print(f"   • {Fore.RED}{losers_total}{Fore.WHITE} ({Fore.RED}{losers_pct:.1f}%{Fore.WHITE}) lost money")
    print(f"   • {Fore.RED}{stats['rekt']}{Fore.WHITE} ({Fore.RED}{rekt_pct:.1f}%{Fore.WHITE}) got REKT (lost >90%)")
    print(f"{Fore.GREEN}{'='*70}")

    print(f"\n{Fore.MAGENTA}🌙 Moon Dev says: These numbers are from VERIFIED complete data! 📊\n")


def save_results():
    """Save to CSV."""
    if not results:
        return

    with open(OUTPUT_CSV, 'w', newline='') as f:
        fieldnames = ['address', 'events', 'balance', 'deposits', 'withdrawals',
                      'internal_in', 'internal_out', 'net_pnl', 'pnl_pct', 'category']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r[k] for k in fieldnames})

    print(f"{Fore.GREEN}💾 Results saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    run_analysis()
