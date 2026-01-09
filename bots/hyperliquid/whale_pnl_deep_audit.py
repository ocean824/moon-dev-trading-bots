"""
🌙 Moon Dev's DEEP P&L Audit 🔬
================================
This script does a DEEP investigation of P&L accuracy.

Key checks:
1. Are we hitting API limits? (2000 event max)
2. What event types are we missing?
3. Do internal transfers significantly affect P&L?
4. Cross-check the math multiple ways

Moon Dev 🌙
"""

import requests
import time
import os
from datetime import datetime
from termcolor import colored
import colorama
from colorama import Fore, Style

colorama.init(autoreset=True)

# Configuration
API_URL = "https://api.hyperliquid.xyz/info"
HEADERS = {"Content-Type": "application/json"}
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
INPUT_FILE = os.path.join(DATA_DIR, 'whales_to_clean.txt')

MOON_DEV_BANNER = f"""{Fore.CYAN}
🔬 MOON DEV'S DEEP P&L AUDIT 🔬
================================
Checking for data accuracy issues!
{Fore.RESET}"""


def get_user_balance(address: str) -> dict:
    """Get detailed balance info."""
    payload = {"type": "clearinghouseState", "user": address}
    response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def get_full_ledger(address: str) -> list:
    """Get ALL ledger events (or as many as API allows)."""
    payload = {
        "type": "userNonFundingLedgerUpdates",
        "user": address,
        "startTime": 0
    }
    response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def analyze_wallet_deeply(address: str, num: int):
    """
    Deep analysis of a single wallet to check for data accuracy.
    Moon Dev's forensic audit! 🔬
    """
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.MAGENTA}DEEP AUDIT #{num}: {Fore.YELLOW}{address}")
    print(f"{Fore.CYAN}{'='*80}")

    # Get balance
    balance_data = get_user_balance(address)
    time.sleep(0.3)

    # Get ledger
    ledger = get_full_ledger(address)
    time.sleep(0.3)

    current_balance = float(balance_data.get('marginSummary', {}).get('accountValue', 0))
    total_events = len(ledger)

    print(f"\n{Fore.WHITE}Current Balance: {Fore.GREEN}${current_balance:,.2f}")
    print(f"{Fore.WHITE}Total Events: {Fore.CYAN}{total_events}")

    # Check for API limit
    if total_events >= 2000:
        print(f"\n{Fore.RED}⚠️ WARNING: HIT API LIMIT OF 2000 EVENTS!")
        print(f"{Fore.RED}   This wallet likely has MORE transactions we're not seeing!")
        print(f"{Fore.RED}   P&L calculation may be INCOMPLETE!")

    # Categorize ALL events and sum values
    event_sums = {}
    event_counts = {}

    for event in ledger:
        delta = event.get('delta', {})
        delta_type = delta.get('type', 'unknown')
        timestamp = event.get('time', 0)

        event_counts[delta_type] = event_counts.get(delta_type, 0) + 1

        # Try to extract USDC value from various fields
        usdc_value = 0
        if 'usdc' in delta:
            usdc_value = float(delta['usdc'])
        elif 'amount' in delta:
            # For spot transfers, check if it's USDC
            if delta.get('token', '') == 'USDC':
                usdc_value = float(delta['amount'])

        if delta_type not in event_sums:
            event_sums[delta_type] = {'positive': 0, 'negative': 0, 'count': 0}

        if usdc_value > 0:
            event_sums[delta_type]['positive'] += usdc_value
        else:
            event_sums[delta_type]['negative'] += abs(usdc_value)
        event_sums[delta_type]['count'] += 1

    # Print detailed breakdown
    print(f"\n{Fore.WHITE}📊 DETAILED EVENT BREAKDOWN:")
    print(f"{Fore.WHITE}{'─'*80}")
    print(f"{Fore.WHITE}{'Event Type':<30} {'Count':>8} {'Positive $':>18} {'Negative $':>18}")
    print(f"{Fore.WHITE}{'─'*80}")

    total_money_in = 0
    total_money_out = 0

    for event_type in sorted(event_sums.keys()):
        data = event_sums[event_type]
        print(f"{Fore.CYAN}{event_type:<30} {data['count']:>8} "
              f"{Fore.GREEN}${data['positive']:>16,.2f} "
              f"{Fore.RED}${data['negative']:>16,.2f}")

        # Track totals
        if event_type == 'deposit':
            total_money_in += data['positive']
        elif event_type == 'withdraw':
            total_money_out += data['positive']  # withdrawals are stored as positive
        elif event_type == 'internalTransfer':
            # Could be in or out depending on direction
            total_money_in += data['positive']
            total_money_out += data['negative']
        elif event_type == 'subAccountTransfer':
            total_money_in += data['positive']
            total_money_out += data['negative']

    print(f"{Fore.WHITE}{'─'*80}")

    # Calculate P&L multiple ways
    deposits = event_sums.get('deposit', {}).get('positive', 0)
    withdrawals = event_sums.get('withdraw', {}).get('positive', 0) + event_sums.get('withdraw', {}).get('negative', 0)

    print(f"\n{Fore.WHITE}📐 P&L CALCULATION METHODS:")
    print(f"{Fore.WHITE}{'─'*60}")

    # Method 1: Simple (what we're using)
    simple_pnl = current_balance + withdrawals - deposits
    simple_pct = (simple_pnl / deposits * 100) if deposits > 0 else 0
    print(f"\n{Fore.WHITE}Method 1 (Simple): Balance + Withdrawals - Deposits")
    print(f"   ${current_balance:,.2f} + ${withdrawals:,.2f} - ${deposits:,.2f}")
    print(f"   = {Fore.GREEN if simple_pnl > 0 else Fore.RED}${simple_pnl:,.2f} ({simple_pct:+.2f}%)")

    # Method 2: Check if internal transfers matter
    internal_in = event_sums.get('internalTransfer', {}).get('positive', 0)
    internal_out = event_sums.get('internalTransfer', {}).get('negative', 0)
    subacct_in = event_sums.get('subAccountTransfer', {}).get('positive', 0)
    subacct_out = event_sums.get('subAccountTransfer', {}).get('negative', 0)

    adjusted_deposits = deposits + internal_in + subacct_in
    adjusted_withdrawals = withdrawals + internal_out + subacct_out

    adjusted_pnl = current_balance + adjusted_withdrawals - adjusted_deposits
    adjusted_pct = (adjusted_pnl / adjusted_deposits * 100) if adjusted_deposits > 0 else 0

    print(f"\n{Fore.WHITE}Method 2 (Including Internal/SubAccount Transfers):")
    print(f"   Deposits + Internal IN: ${deposits:,.2f} + ${internal_in:,.2f} + ${subacct_in:,.2f} = ${adjusted_deposits:,.2f}")
    print(f"   Withdrawals + Internal OUT: ${withdrawals:,.2f} + ${internal_out:,.2f} + ${subacct_out:,.2f} = ${adjusted_withdrawals:,.2f}")
    print(f"   Adjusted P&L = {Fore.GREEN if adjusted_pnl > 0 else Fore.RED}${adjusted_pnl:,.2f} ({adjusted_pct:+.2f}%)")

    # Difference
    diff = simple_pnl - adjusted_pnl
    if abs(diff) > 100:
        print(f"\n{Fore.YELLOW}⚠️ DIFFERENCE: ${diff:,.2f} - Internal transfers affected result!")
    else:
        print(f"\n{Fore.GREEN}✅ Internal transfers had minimal effect (${diff:,.2f})")

    # Check for API limit issue impact
    if total_events >= 2000:
        print(f"\n{Fore.RED}🚨 API LIMIT WARNING:")
        print(f"{Fore.RED}   We only got {total_events} events but there may be more!")
        print(f"{Fore.RED}   Oldest event we saw: {datetime.fromtimestamp(ledger[-1]['time']/1000).strftime('%Y-%m-%d')}")
        print(f"{Fore.RED}   We might be missing older deposits/withdrawals!")

    return {
        'address': address,
        'balance': current_balance,
        'events': total_events,
        'hit_limit': total_events >= 2000,
        'deposits': deposits,
        'withdrawals': withdrawals,
        'simple_pnl': simple_pnl,
        'simple_pct': simple_pct,
        'internal_in': internal_in,
        'internal_out': internal_out,
        'adjusted_pnl': adjusted_pnl,
        'adjusted_pct': adjusted_pct,
        'event_types': list(event_counts.keys())
    }


def run_deep_audit():
    """Run deep audit on sample wallets."""
    print(MOON_DEV_BANNER)

    # Read addresses
    with open(INPUT_FILE, 'r') as f:
        addresses = [line.strip() for line in f if line.strip().startswith('0x')]

    # Audit first 10 wallets
    sample_size = 10
    sample = addresses[:sample_size]

    results = []
    for i, addr in enumerate(sample, 1):
        result = analyze_wallet_deeply(addr, i)
        results.append(result)

    # Summary
    print(f"\n\n{Fore.GREEN}{'='*80}")
    print(f"{Fore.CYAN}🌙 MOON DEV'S DEEP AUDIT SUMMARY 🔬")
    print(f"{Fore.GREEN}{'='*80}")

    hit_limit_count = sum(1 for r in results if r['hit_limit'])
    winners_simple = sum(1 for r in results if r['simple_pnl'] > 0)
    winners_adjusted = sum(1 for r in results if r['adjusted_pnl'] > 0)

    print(f"\n{Fore.WHITE}📊 KEY FINDINGS:")
    print(f"   {Fore.RED}Wallets hitting 2000 event limit: {hit_limit_count}/{sample_size}")
    print(f"   {Fore.GREEN}Winners (simple method): {winners_simple}/{sample_size}")
    print(f"   {Fore.CYAN}Winners (adjusted method): {winners_adjusted}/{sample_size}")

    # Check if results differ
    changed = sum(1 for r in results if (r['simple_pnl'] > 0) != (r['adjusted_pnl'] > 0))
    print(f"   {Fore.YELLOW}Results changed after adjustment: {changed}/{sample_size}")

    # Show wallets hitting limit
    if hit_limit_count > 0:
        print(f"\n{Fore.RED}⚠️ WALLETS HITTING API LIMIT (incomplete data!):")
        for r in results:
            if r['hit_limit']:
                print(f"   {r['address'][:20]}... - {r['events']} events")

    # All event types found
    all_types = set()
    for r in results:
        all_types.update(r['event_types'])

    print(f"\n{Fore.WHITE}📋 ALL EVENT TYPES FOUND:")
    for t in sorted(all_types):
        print(f"   • {t}")

    print(f"\n{Fore.MAGENTA}🌙 Moon Dev says: Check the API limit issue! 🔍\n")


if __name__ == "__main__":
    run_deep_audit()
