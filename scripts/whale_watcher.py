"""
Moon Dev's HLP Whale Watcher
============================
Beautiful terminal dashboard for tracking Hyperliquid HLP positions

Tracks all HLP component strategies and shows NET combined positions.
Auto-refreshes to keep you updated on HLP moves!

Moon Dev

Usage: python scripts/whale_watcher.py
"""

import os
import sys
import time
import requests
from datetime import datetime
from colorama import Fore, Back, Style, init

init(autoreset=True)

# ===== CONFIGURATION =====
REFRESH_MINUTES = 5  # How often to refresh data
API_URL = "https://api.hyperliquid.xyz/info"

# HLP Component Strategies - named per Hyperliquid website
HLP_ADDRESSES = {
    "HLP Strategy A": "0x010461c14e146ac35fe42271bdc1134ee31c703a",   # ends in 03a
    "HLP Liquidator": "0x2e3d94f0562703b25c83308a05046ddaf9a8dd14",   # ends in d14
    "HLP Liquidator 4": "0x2ed5c4484ea3ff8b57d5f2fb152a40d9f2b68308", # ends in 308
    "HLP Strategy B": "0x31ca8395cf837de08b24da3f660e77761dfb974b",   # ends in 74b
    "HLP Strategy X": "0x469f690213c467c39a23efacfd2816896009d7d8",   # ends in 7d8
    "HLP Liquidator 3": "0x5e177e5e39c0f4e421f5865a6d8beed8d921cb70", # ends in b70
    "HLP Liquidator 2": "0xb0a55f13d22f66e6d495ac98113841b2326e9540", # ends in 540
}


def get_user_positions(address):
    """Fetch positions for a specific Hyperliquid wallet address"""
    payload = {"type": "clearinghouseState", "user": address}
    response = requests.post(API_URL, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def format_usd(value):
    """Format USD value with commas"""
    if value is None or value == 0:
        return "$0"
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:,.2f}M"
    elif abs(value) >= 1_000:
        return f"${value/1_000:,.1f}K"
    else:
        return f"${value:,.2f}"


def format_pnl(value):
    """Format PnL with color"""
    if value is None or value == 0:
        return f"{Fore.WHITE}$0"
    if value > 0:
        return f"{Fore.GREEN}+{format_usd(value)}"
    else:
        return f"{Fore.RED}-{format_usd(abs(value))}"


def print_banner():
    """Print Moon Dev's banner"""
    banner = f"""
{Fore.CYAN}{'='*90}
{Fore.MAGENTA}
    ██╗  ██╗██╗     ██████╗     ██╗    ██╗ █████╗ ████████╗ ██████╗██╗  ██╗███████╗██████╗
    ██║  ██║██║     ██╔══██╗    ██║    ██║██╔══██╗╚══██╔══╝██╔════╝██║  ██║██╔════╝██╔══██╗
    ███████║██║     ██████╔╝    ██║ █╗ ██║███████║   ██║   ██║     ███████║█████╗  ██████╔╝
    ██╔══██║██║     ██╔═══╝     ██║███╗██║██╔══██║   ██║   ██║     ██╔══██║██╔══╝  ██╔══██╗
    ██║  ██║███████╗██║         ╚███╔███╔╝██║  ██║   ██║   ╚██████╗██║  ██║███████╗██║  ██║
    ╚═╝  ╚═╝╚══════╝╚═╝          ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
{Fore.CYAN}{'='*90}
{Fore.WHITE}  Moon Dev's Hyperliquid HLP Position Tracker
{Fore.YELLOW}  Tracking {len(HLP_ADDRESSES)} HLP strategies | Refresh every {REFRESH_MINUTES} min
{Fore.CYAN}{'='*90}
"""
    print(banner)


def parse_positions(positions_data):
    """Parse position data and return structured list"""
    if not isinstance(positions_data, dict):
        return [], 0, 0

    margin = positions_data.get('marginSummary', {})
    account_value = float(margin.get('accountValue', 0))

    asset_positions = positions_data.get('assetPositions', [])
    positions = []
    total_pnl = 0

    for pos in asset_positions:
        if 'position' not in pos:
            continue
        p = pos['position']
        size = float(p.get('szi', 0))
        if size == 0:
            continue

        pos_value = float(p.get('positionValue', 0))
        pnl = float(p.get('unrealizedPnl', 0))
        entry = float(p.get('entryPx', 0))
        liq = float(p.get('liquidationPx', 0) or 0)
        leverage = p.get('leverage', {})
        lev_val = leverage.get('value', 0) if isinstance(leverage, dict) else 0

        total_pnl += pnl

        positions.append({
            'coin': p.get('coin', '?'),
            'size': size,
            'is_long': size > 0,
            'position_value': pos_value,
            'pnl': pnl,
            'entry': entry,
            'liq': liq,
            'leverage': lev_val
        })

    # Sort by position value
    positions.sort(key=lambda x: abs(x['position_value']), reverse=True)

    return positions, account_value, total_pnl


def print_account_no_positions(label, address, account_value):
    """Print account with no positions on single line"""
    short_addr = f"{address[:6]}...{address[-4:]}"
    print(f"{Fore.YELLOW}  {label:<18} {Fore.CYAN}{short_addr} {Fore.WHITE}| Acc Value: {Fore.YELLOW}{format_usd(account_value)} {Fore.WHITE}| {Fore.YELLOW}No open positions")


def print_account_with_positions(label, address, positions, account_value, total_pnl):
    """Print account with positions"""
    short_addr = f"{address[:6]}...{address[-4:]}"

    # Calculate long/short totals
    long_value = sum(p['position_value'] for p in positions if p['is_long'])
    short_value = sum(p['position_value'] for p in positions if not p['is_long'])
    long_count = sum(1 for p in positions if p['is_long'])
    short_count = sum(1 for p in positions if not p['is_long'])
    long_pnl = sum(p['pnl'] for p in positions if p['is_long'])
    short_pnl = sum(p['pnl'] for p in positions if not p['is_long'])

    # Header
    print(f"\n{Fore.CYAN}{'─'*90}")
    print(f"{Back.BLUE}{Fore.WHITE}  {label}: {short_addr}  {Style.RESET_ALL} "
          f"{Fore.WHITE}Acc: {Fore.YELLOW}{format_usd(account_value)} {Fore.WHITE}| "
          f"PnL: {format_pnl(total_pnl)} {Fore.WHITE}| "
          f"Positions: {Fore.CYAN}{len(positions)}")

    # Long/Short breakdown
    print(f"{Fore.GREEN}  LONGS:  {long_count:>3} positions | Value: {format_usd(long_value):>12} | PnL: {format_pnl(long_pnl)}")
    print(f"{Fore.RED}  SHORTS: {short_count:>3} positions | Value: {format_usd(short_value):>12} | PnL: {format_pnl(short_pnl)}")
    print(f"{Fore.CYAN}{'─'*90}")

    # Position header
    print(f"{Fore.WHITE}  {'COIN':<8} {'SIDE':<6} {'VALUE':>12} {'ENTRY':>12} {'LIQ':>12} {'LEV':>6} {'PnL':>14}")
    print(f"{Fore.CYAN}  {'-'*8} {'-'*6} {'-'*12} {'-'*12} {'-'*12} {'-'*6} {'-'*14}")

    # Print positions
    for pos in positions[:12]:  # Show top 12 positions
        coin = pos['coin']
        is_long = pos['is_long']

        if is_long:
            side = f"{Back.GREEN}{Fore.WHITE} LONG {Style.RESET_ALL}"
            row_color = Fore.GREEN
        else:
            side = f"{Back.RED}{Fore.WHITE} SHORT{Style.RESET_ALL}"
            row_color = Fore.RED

        value_str = format_usd(pos['position_value'])
        entry_str = f"${pos['entry']:,.2f}" if pos['entry'] else "N/A"
        liq_str = f"${pos['liq']:,.2f}" if pos['liq'] > 0 else "N/A"
        lev_str = f"{pos['leverage']:.0f}x" if pos['leverage'] else "N/A"
        pnl_str = format_pnl(pos['pnl'])

        print(f"{row_color}  {coin:<8} {side} {value_str:>12} {entry_str:>12} "
              f"{Fore.RED}{liq_str:>12}{row_color} {lev_str:>6} {pnl_str:>14}")

    if len(positions) > 12:
        print(f"{Fore.YELLOW}  ... and {len(positions) - 12} more positions")


def calculate_net_positions(all_positions_by_account):
    """Calculate NET positions across all accounts (HLP_LONG style)"""
    net_positions = {}

    for label, positions in all_positions_by_account.items():
        for pos in positions:
            coin = pos['coin']
            if coin not in net_positions:
                net_positions[coin] = {
                    'coin': coin,
                    'net_size': 0,
                    'net_value': 0,
                    'net_pnl': 0,
                    'long_value': 0,
                    'short_value': 0,
                    'sources': []
                }

            size = pos['size']
            value = pos['position_value']
            pnl = pos['pnl']

            # Track direction
            if size > 0:
                net_positions[coin]['long_value'] += value
                net_positions[coin]['sources'].append(f"{label[:10]}+")
            else:
                net_positions[coin]['short_value'] += value
                net_positions[coin]['sources'].append(f"{label[:10]}-")

            net_positions[coin]['net_size'] += size
            net_positions[coin]['net_pnl'] += pnl

    # Calculate net value based on net direction
    for coin, data in net_positions.items():
        if data['net_size'] > 0:
            data['net_value'] = data['long_value'] - data['short_value']
            data['is_long'] = True
        elif data['net_size'] < 0:
            data['net_value'] = data['short_value'] - data['long_value']
            data['is_long'] = False
        else:
            data['net_value'] = 0
            data['is_long'] = None

    # Convert to list and sort by absolute net value
    net_list = list(net_positions.values())
    net_list.sort(key=lambda x: abs(x['net_value']), reverse=True)

    return net_list


def print_combined_hlp(net_positions, totals):
    """Print combined HLP NET positions"""
    print(f"\n{Fore.CYAN}{'='*90}")
    print(f"{Back.MAGENTA}{Fore.WHITE}  HLP COMBINED NET POSITIONS (After Netting Long/Short)  {Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*90}")

    # Summary stats
    total_account_value = sum(t[0] for t in totals.values())
    total_pnl = sum(t[1] for t in totals.values())
    total_positions = sum(t[2] for t in totals.values())

    print(f"\n{Fore.WHITE}  Total Account Value: {Fore.YELLOW}{format_usd(total_account_value)} {Fore.WHITE}| "
          f"Total PnL: {format_pnl(total_pnl)} {Fore.WHITE}| "
          f"Total Positions: {Fore.CYAN}{total_positions}")

    # Filter to only show positions with significant net exposure
    significant_positions = [p for p in net_positions if abs(p['net_value']) > 1000]

    if not significant_positions:
        print(f"\n{Fore.YELLOW}  All positions are fully hedged (net exposure < $1K)")
        return

    # Header
    print(f"\n{Fore.WHITE}  {'COIN':<8} {'NET SIDE':<10} {'NET VALUE':>12} {'LONG VAL':>12} {'SHORT VAL':>12} {'NET PnL':>14}")
    print(f"{Fore.CYAN}  {'-'*8} {'-'*10} {'-'*12} {'-'*12} {'-'*12} {'-'*14}")

    long_net = 0
    short_net = 0

    for pos in significant_positions[:25]:
        coin = pos['coin']
        is_long = pos['is_long']

        if is_long is None:
            side = f"{Fore.WHITE}NEUTRAL   "
            row_color = Fore.WHITE
        elif is_long:
            side = f"{Back.GREEN}{Fore.WHITE} NET LONG {Style.RESET_ALL}"
            row_color = Fore.GREEN
            long_net += abs(pos['net_value'])
        else:
            side = f"{Back.RED}{Fore.WHITE} NET SHORT{Style.RESET_ALL}"
            row_color = Fore.RED
            short_net += abs(pos['net_value'])

        net_val = format_usd(abs(pos['net_value']))
        long_val = format_usd(pos['long_value'])
        short_val = format_usd(pos['short_value'])
        pnl_str = format_pnl(pos['net_pnl'])

        print(f"{row_color}  {coin:<8} {side} {net_val:>12} {Fore.GREEN}{long_val:>12} {Fore.RED}{short_val:>12} {pnl_str:>14}")

    if len(significant_positions) > 25:
        print(f"{Fore.YELLOW}  ... and {len(significant_positions) - 25} more net positions")

    # Net exposure summary
    print(f"\n{Fore.WHITE}  Net Long Exposure: {Fore.GREEN}{format_usd(long_net)} {Fore.WHITE}| "
          f"Net Short Exposure: {Fore.RED}{format_usd(short_net)} {Fore.WHITE}| "
          f"Net Delta: {Fore.YELLOW}{format_usd(long_net - short_net)}")


def main():
    """Main function - runs the HLP watcher on a loop"""
    while True:
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')

        print_banner()
        print(f"{Fore.WHITE}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.YELLOW}  Loading HLP positions...\n")

        # Collect all data
        accounts_no_positions = []
        accounts_with_positions = []
        all_positions_by_account = {}
        totals = {}  # (account_value, total_pnl, position_count)

        for label, address in HLP_ADDRESSES.items():
            try:
                positions_data = get_user_positions(address)
                positions, account_value, total_pnl = parse_positions(positions_data)

                totals[label] = (account_value, total_pnl, len(positions))
                all_positions_by_account[label] = positions

                if positions:
                    accounts_with_positions.append((label, address, positions, account_value, total_pnl))
                else:
                    accounts_no_positions.append((label, address, account_value))

            except Exception as e:
                print(f"{Fore.RED}  Error fetching {label}: {str(e)[:50]}")
                totals[label] = (0, 0, 0)
                all_positions_by_account[label] = []

        # Print accounts with NO positions first (at top, less important)
        if accounts_no_positions:
            print(f"{Fore.CYAN}{'─'*90}")
            print(f"{Fore.WHITE}  Idle Accounts (No Open Positions):")
            print(f"{Fore.CYAN}{'─'*90}")
            for label, address, account_value in accounts_no_positions:
                print_account_no_positions(label, address, account_value)

        # Print accounts WITH positions (more important, closer to bottom)
        for label, address, positions, account_value, total_pnl in accounts_with_positions:
            print_account_with_positions(label, address, positions, account_value, total_pnl)

        # Calculate and print combined NET positions (most important, at bottom)
        net_positions = calculate_net_positions(all_positions_by_account)
        print_combined_hlp(net_positions, totals)

        # Footer
        print(f"\n{Fore.CYAN}{'='*90}")
        print(f"{Fore.CYAN}  Moon Dev's HLP Watcher | Auto-refresh in {REFRESH_MINUTES} min | Ctrl+C to exit")
        print(f"{Fore.CYAN}{'='*90}\n")

        # Wait for refresh
        time.sleep(REFRESH_MINUTES * 60)


if __name__ == "__main__":
    main()
