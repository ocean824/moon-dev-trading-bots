"""
🌙 Moon Dev's Whale P&L Auditor 🔍
==================================
This script AUDITS the P&L calculations by showing EVERY transaction.

The goal: PROVE the math is correct (or find the bug!)

For each wallet we show:
1. ALL ledger events (deposits, withdrawals, transfers, etc.)
2. Raw transaction data
3. Step-by-step P&L calculation
4. Verification that nothing is missed

Moon Dev 🌙
"""

import requests
import time
import os
import json
from datetime import datetime
from termcolor import colored
import colorama
from colorama import Fore, Style

# Initialize colorama
colorama.init(autoreset=True)

# ===== CONFIGURATION =====
SAMPLE_SIZE = 20  # Number of wallets to audit
DELAY_BETWEEN_REQUESTS = 0.3  # Seconds between API calls
MAX_RETRIES = 3
# ==========================

# API Configuration
API_URL = "https://api.hyperliquid.xyz/info"
HEADERS = {"Content-Type": "application/json"}

# File paths
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(DATA_DIR, 'data')
INPUT_FILE = os.path.join(DATA_DIR, 'whales_to_clean.txt')

# Moon Dev Banner
MOON_DEV_BANNER = f"""{Fore.CYAN}
   __  ___                    ____
  /  |/  /___  ____  ____    / __ \\___  _  __
 / /|_/ / __ \\/ __ \\/ __ \\  / / / / _ \\| |/_/
/ /  / / /_/ / /_/ / / / / / /_/ /  __/>  <
/_/  /_/\\____/\\____/_/ /_(_)____/\\___/_/|_|

{Fore.MAGENTA}🔍 WHALE P&L AUDITOR 🧮{Fore.RESET}
{Fore.YELLOW}Verifying EVERY transaction - Trust but VERIFY! 📊{Fore.RESET}
"""


def get_user_balance(address: str) -> float:
    """Get user's current balance from Hyperliquid API."""
    payload = {
        "type": "clearinghouseState",
        "user": address
    }

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
    """
    Get the COMPLETE ledger for a wallet - ALL events, not just deposits/withdrawals.
    Moon Dev's full audit! 🔍
    """
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


def format_timestamp(ts_ms: int) -> str:
    """Convert millisecond timestamp to readable date."""
    return datetime.fromtimestamp(ts_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')


def audit_wallet(address: str, wallet_num: int) -> dict:
    """
    Perform a FULL AUDIT of a single wallet.
    Shows EVERY transaction and calculates P&L step by step.
    Moon Dev's detailed audit! 🔍
    """
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.MAGENTA}🔍 AUDITING WALLET #{wallet_num}: {Fore.YELLOW}{address}")
    print(f"{Fore.CYAN}{'='*80}")

    # Get current balance
    balance = get_user_balance(address)
    time.sleep(DELAY_BETWEEN_REQUESTS)

    # Get ALL ledger events
    ledger = get_full_ledger(address)
    time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n{Fore.WHITE}📊 Current Balance: {Fore.GREEN}${balance:,.2f}")
    print(f"{Fore.WHITE}📒 Total Ledger Events: {Fore.CYAN}{len(ledger)}")

    # Categorize ALL events
    event_counts = {}
    deposits = []
    withdrawals = []
    internal_transfers_in = []
    internal_transfers_out = []
    other_events = []

    for event in ledger:
        delta = event.get('delta', {})
        delta_type = delta.get('type', 'unknown')
        timestamp = event.get('time', 0)
        tx_hash = event.get('hash', 'N/A')

        # Count event types
        event_counts[delta_type] = event_counts.get(delta_type, 0) + 1

        # Categorize
        if delta_type == 'deposit':
            usdc = float(delta.get('usdc', 0))
            deposits.append({
                'time': timestamp,
                'date': format_timestamp(timestamp),
                'usdc': usdc,
                'hash': tx_hash,
                'raw': delta
            })
        elif delta_type == 'withdraw':
            usdc = float(delta.get('usdc', 0))
            withdrawals.append({
                'time': timestamp,
                'date': format_timestamp(timestamp),
                'usdc': abs(usdc),  # Make positive for display
                'fee': float(delta.get('fee', 0)),
                'hash': tx_hash,
                'raw': delta
            })
        elif delta_type == 'internalTransfer':
            usdc = float(delta.get('usdc', 0))
            destination = delta.get('destination', '')
            user = delta.get('user', '')
            # If destination matches our address, it's incoming
            if destination.lower() == address.lower():
                internal_transfers_in.append({
                    'time': timestamp,
                    'date': format_timestamp(timestamp),
                    'usdc': usdc,
                    'from': user,
                    'hash': tx_hash,
                    'raw': delta
                })
            else:
                internal_transfers_out.append({
                    'time': timestamp,
                    'date': format_timestamp(timestamp),
                    'usdc': usdc,
                    'to': destination,
                    'hash': tx_hash,
                    'raw': delta
                })
        elif delta_type == 'subAccountTransfer':
            usdc = float(delta.get('usdc', 0))
            destination = delta.get('destination', '')
            user = delta.get('user', '')
            # Track sub-account transfers
            if destination.lower() == address.lower():
                internal_transfers_in.append({
                    'time': timestamp,
                    'date': format_timestamp(timestamp),
                    'usdc': usdc,
                    'from': user,
                    'type': 'subAccountTransfer',
                    'hash': tx_hash,
                    'raw': delta
                })
            else:
                internal_transfers_out.append({
                    'time': timestamp,
                    'date': format_timestamp(timestamp),
                    'usdc': usdc,
                    'to': destination,
                    'type': 'subAccountTransfer',
                    'hash': tx_hash,
                    'raw': delta
                })
        else:
            other_events.append({
                'type': delta_type,
                'time': timestamp,
                'date': format_timestamp(timestamp),
                'hash': tx_hash,
                'raw': delta
            })

    # Print event type summary
    print(f"\n{Fore.WHITE}📋 EVENT TYPE BREAKDOWN:")
    print(f"{Fore.WHITE}{'─'*50}")
    for event_type, count in sorted(event_counts.items(), key=lambda x: -x[1]):
        print(f"   {Fore.CYAN}{event_type:<25} {Fore.WHITE}: {Fore.YELLOW}{count:>5}")
    print(f"{Fore.WHITE}{'─'*50}")

    # Print ALL deposits
    print(f"\n{Fore.GREEN}💰 DEPOSITS ({len(deposits)} total):")
    print(f"{Fore.WHITE}{'─'*70}")
    total_deposits = 0
    for i, dep in enumerate(deposits[:50], 1):  # Show first 50
        total_deposits += dep['usdc']
        print(f"   {Fore.WHITE}{i:>3}. {Fore.CYAN}{dep['date']} | {Fore.GREEN}+${dep['usdc']:>15,.2f}")
    if len(deposits) > 50:
        remaining = sum(d['usdc'] for d in deposits[50:])
        total_deposits += remaining - sum(d['usdc'] for d in deposits[:50]) + total_deposits
        print(f"   {Fore.YELLOW}... and {len(deposits)-50} more deposits totaling ${remaining:,.2f}")
    total_deposits = sum(d['usdc'] for d in deposits)
    print(f"{Fore.WHITE}{'─'*70}")
    print(f"   {Fore.GREEN}TOTAL DEPOSITS: ${total_deposits:>15,.2f}")

    # Print ALL withdrawals
    print(f"\n{Fore.RED}💸 WITHDRAWALS ({len(withdrawals)} total):")
    print(f"{Fore.WHITE}{'─'*70}")
    total_withdrawals = 0
    total_fees = 0
    for i, wd in enumerate(withdrawals[:50], 1):  # Show first 50
        total_withdrawals += wd['usdc']
        total_fees += wd['fee']
        print(f"   {Fore.WHITE}{i:>3}. {Fore.CYAN}{wd['date']} | {Fore.RED}-${wd['usdc']:>15,.2f} | fee: ${wd['fee']:.2f}")
    if len(withdrawals) > 50:
        print(f"   {Fore.YELLOW}... and {len(withdrawals)-50} more withdrawals")
    total_withdrawals = sum(w['usdc'] for w in withdrawals)
    total_fees = sum(w['fee'] for w in withdrawals)
    print(f"{Fore.WHITE}{'─'*70}")
    print(f"   {Fore.RED}TOTAL WITHDRAWALS: ${total_withdrawals:>15,.2f}")
    print(f"   {Fore.YELLOW}TOTAL FEES: ${total_fees:>15,.2f}")

    # Print internal transfers if any
    if internal_transfers_in or internal_transfers_out:
        print(f"\n{Fore.MAGENTA}🔄 INTERNAL TRANSFERS:")
        print(f"{Fore.WHITE}{'─'*70}")
        total_in = sum(t['usdc'] for t in internal_transfers_in)
        total_out = sum(t['usdc'] for t in internal_transfers_out)
        print(f"   {Fore.GREEN}Transfers IN:  ${total_in:>15,.2f} ({len(internal_transfers_in)} txns)")
        print(f"   {Fore.RED}Transfers OUT: ${total_out:>15,.2f} ({len(internal_transfers_out)} txns)")
        print(f"   {Fore.YELLOW}⚠️ NOTE: Internal transfers may affect P&L calculation!")

    # Print other events if any
    if other_events:
        print(f"\n{Fore.YELLOW}📝 OTHER EVENTS ({len(other_events)} total):")
        other_types = {}
        for e in other_events:
            other_types[e['type']] = other_types.get(e['type'], 0) + 1
        for etype, count in other_types.items():
            print(f"   {Fore.CYAN}{etype}: {Fore.WHITE}{count}")

    # Calculate P&L
    print(f"\n{Fore.WHITE}{'='*70}")
    print(f"{Fore.MAGENTA}🧮 P&L CALCULATION (Step by Step):")
    print(f"{Fore.WHITE}{'='*70}")

    print(f"\n   {Fore.WHITE}Formula: Net P&L = Current Balance + Withdrawals - Deposits")
    print(f"\n   {Fore.WHITE}Step 1: Current Balance    = {Fore.GREEN}${balance:>18,.2f}")
    print(f"   {Fore.WHITE}Step 2: + Total Withdrawals = {Fore.CYAN}${total_withdrawals:>18,.2f}")
    print(f"   {Fore.WHITE}Step 3: - Total Deposits    = {Fore.YELLOW}${total_deposits:>18,.2f}")
    print(f"   {Fore.WHITE}{'─'*50}")

    net_pnl = balance + total_withdrawals - total_deposits
    pnl_color = Fore.GREEN if net_pnl >= 0 else Fore.RED

    print(f"   {Fore.WHITE}Net P&L = ${balance:,.2f} + ${total_withdrawals:,.2f} - ${total_deposits:,.2f}")
    print(f"   {Fore.WHITE}Net P&L = {pnl_color}${net_pnl:>18,.2f}")

    if total_deposits > 0:
        pnl_percent = (net_pnl / total_deposits) * 100
        print(f"   {Fore.WHITE}P&L %   = {pnl_color}{pnl_percent:>18.2f}%")
    else:
        pnl_percent = 0
        print(f"   {Fore.YELLOW}P&L %   = N/A (no deposits)")

    # Verdict
    print(f"\n   {Fore.WHITE}{'─'*50}")
    if pnl_percent > 0:
        print(f"   {Fore.GREEN}🏆 VERDICT: WINNER (+{pnl_percent:.1f}%)")
    elif pnl_percent >= -10:
        print(f"   {Fore.YELLOW}📉 VERDICT: SMALL LOSS ({pnl_percent:.1f}%)")
    elif pnl_percent >= -50:
        print(f"   {Fore.YELLOW}📉📉 VERDICT: MEDIUM LOSS ({pnl_percent:.1f}%)")
    elif pnl_percent >= -90:
        print(f"   {Fore.RED}📉📉📉 VERDICT: BIG LOSS ({pnl_percent:.1f}%)")
    else:
        print(f"   {Fore.RED}💀 VERDICT: REKT ({pnl_percent:.1f}%)")

    # Warning about internal transfers
    if internal_transfers_in or internal_transfers_out:
        total_in = sum(t['usdc'] for t in internal_transfers_in)
        total_out = sum(t['usdc'] for t in internal_transfers_out)
        net_internal = total_in - total_out
        print(f"\n   {Fore.YELLOW}⚠️ WARNING: This wallet has internal transfers!")
        print(f"   {Fore.YELLOW}   Net internal transfer: ${net_internal:,.2f}")
        print(f"   {Fore.YELLOW}   This could be from/to sub-accounts or other wallets.")
        print(f"   {Fore.YELLOW}   The P&L calculation above may not tell the full story!")

    return {
        'address': address,
        'balance': balance,
        'deposits': total_deposits,
        'withdrawals': total_withdrawals,
        'net_pnl': net_pnl,
        'pnl_percent': pnl_percent,
        'num_deposits': len(deposits),
        'num_withdrawals': len(withdrawals),
        'internal_transfers_in': sum(t['usdc'] for t in internal_transfers_in),
        'internal_transfers_out': sum(t['usdc'] for t in internal_transfers_out),
        'event_counts': event_counts
    }


def run_audit():
    """
    Main audit function - analyze sample wallets in detail.
    Moon Dev's trust but verify! 🔍
    """
    print(MOON_DEV_BANNER)

    # Check if input file exists
    if not os.path.exists(INPUT_FILE):
        print(f"{Fore.RED}❌ Input file not found: {INPUT_FILE}")
        return

    # Read addresses
    with open(INPUT_FILE, 'r') as f:
        addresses = [line.strip() for line in f if line.strip().startswith('0x')]

    # Take sample
    sample = addresses[:SAMPLE_SIZE]

    print(f"\n{Fore.CYAN}🔍 AUDITING {SAMPLE_SIZE} WALLETS")
    print(f"{Fore.WHITE}   This will show EVERY transaction for verification")
    print(f"{Fore.WHITE}   Moon Dev says: Trust but VERIFY! 🌙\n")

    results = []
    for i, address in enumerate(sample, 1):
        result = audit_wallet(address, i)
        results.append(result)

    # Final summary
    print(f"\n\n{Fore.GREEN}{'='*80}")
    print(f"{Fore.CYAN}🌙 MOON DEV'S AUDIT SUMMARY 🔍")
    print(f"{Fore.GREEN}{'='*80}")

    winners = sum(1 for r in results if r['pnl_percent'] > 0)
    losers = sum(1 for r in results if r['pnl_percent'] <= 0)
    rekt = sum(1 for r in results if r['pnl_percent'] < -90)
    has_internal = sum(1 for r in results if r['internal_transfers_in'] > 0 or r['internal_transfers_out'] > 0)

    print(f"\n{Fore.WHITE}📊 QUICK STATS:")
    print(f"   {Fore.GREEN}Winners: {winners}/{SAMPLE_SIZE} ({winners/SAMPLE_SIZE*100:.1f}%)")
    print(f"   {Fore.RED}Losers: {losers}/{SAMPLE_SIZE} ({losers/SAMPLE_SIZE*100:.1f}%)")
    print(f"   {Fore.RED}REKT (>90% loss): {rekt}/{SAMPLE_SIZE} ({rekt/SAMPLE_SIZE*100:.1f}%)")
    print(f"   {Fore.YELLOW}Has Internal Transfers: {has_internal}/{SAMPLE_SIZE}")

    total_deposits = sum(r['deposits'] for r in results)
    total_withdrawals = sum(r['withdrawals'] for r in results)
    total_balance = sum(r['balance'] for r in results)
    total_pnl = sum(r['net_pnl'] for r in results)

    print(f"\n{Fore.WHITE}💰 AGGREGATE NUMBERS:")
    print(f"   {Fore.WHITE}Total Deposits:    {Fore.GREEN}${total_deposits:>18,.2f}")
    print(f"   {Fore.WHITE}Total Withdrawals: {Fore.CYAN}${total_withdrawals:>18,.2f}")
    print(f"   {Fore.WHITE}Total Balances:    {Fore.YELLOW}${total_balance:>18,.2f}")
    print(f"   {Fore.WHITE}Total Net P&L:     {Fore.GREEN if total_pnl > 0 else Fore.RED}${total_pnl:>18,.2f}")

    # Check for potential issues
    print(f"\n{Fore.YELLOW}⚠️ POTENTIAL ISSUES TO INVESTIGATE:")
    if has_internal > 0:
        print(f"   {Fore.YELLOW}• {has_internal} wallets have internal transfers (sub-accounts, wallet-to-wallet)")
        print(f"   {Fore.YELLOW}  These could inflate/deflate apparent P&L!")

    # List all event types found
    all_event_types = set()
    for r in results:
        all_event_types.update(r['event_counts'].keys())

    print(f"\n{Fore.WHITE}📋 ALL EVENT TYPES FOUND:")
    for etype in sorted(all_event_types):
        print(f"   {Fore.CYAN}• {etype}")

    print(f"\n{Fore.MAGENTA}🌙 Moon Dev's Audit Complete! Review the data above carefully! 🔍\n")


if __name__ == "__main__":
    run_audit()
