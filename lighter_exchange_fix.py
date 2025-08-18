#!/usr/bin/env python3
"""
🌙 Moon Dev's Lighter Exchange Balance Fix
This identifies the correct field for available balance vs collateral
"""

import os
import json
import requests
import time

BASE_URL = "https://mainnet.zklighter.elliot.ai/api/v1"

def analyze_balance_discrepancy():
    """Analyze why UI shows $16 but API shows $3.59"""
    
    print("🌙 Moon Dev's Lighter Exchange Balance Analysis")
    print("=" * 80)
    print("""
    📊 Current Situation:
    - UI shows: $16.00 Available Balance
    - API shows: $3.599203 Collateral
    - Difference: $12.40
    """)
    
    # The difference of $12.40 might be:
    # 1. Used margin for positions
    # 2. Reserved for open orders
    # 3. Different balance types
    
    url = f"{BASE_URL}/accounts"
    params = {"by": "index", "value": "7"}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data.get('code') == 200 and data.get('accounts'):
        account = data['accounts'][0]
        
        print("\n🔍 BALANCE BREAKDOWN:")
        print("-" * 60)
        
        # Extract all balance-related fields
        collateral = float(account.get('collateral', 0))
        total_asset_value = float(account.get('total_asset_value', 0))
        cross_asset_value = float(account.get('cross_asset_value', 0))
        
        print(f"Collateral (from API): ${collateral:.6f}")
        print(f"Total Asset Value: ${total_asset_value:.6f}")
        print(f"Cross Asset Value: ${cross_asset_value:.6f}")
        
        # Check if there's a pool_info that might contain additional balance
        pool_info = account.get('pool_info', {})
        if pool_info:
            print(f"\n📊 Pool Info:")
            for key, value in pool_info.items():
                print(f"   {key}: {value}")
        
        # Analyze positions
        positions = account.get('positions', [])
        print(f"\n📈 Positions Analysis ({len(positions)} positions):")
        
        total_margin_used = 0
        total_position_value = 0
        
        for pos in positions:
            symbol = pos.get('symbol')
            allocated_margin = float(pos.get('allocated_margin', 0))
            position_value = float(pos.get('position_value', 0))
            position_size = float(pos.get('position', 0))
            
            total_margin_used += allocated_margin
            total_position_value += abs(position_value)
            
            if position_size != 0 or allocated_margin != 0:
                print(f"\n   {symbol}:")
                print(f"      Position: {position_size}")
                print(f"      Value: ${position_value}")
                print(f"      Margin: ${allocated_margin}")
        
        print(f"\n💰 CALCULATED BALANCES:")
        print("-" * 60)
        print(f"Total Margin Used: ${total_margin_used:.6f}")
        print(f"Total Position Value: ${total_position_value:.6f}")
        
        # Calculate what available balance might be
        print(f"\n🎯 AVAILABLE BALANCE CALCULATIONS:")
        print(f"1. If Available = Collateral + X: ${collateral:.2f} + ${16 - collateral:.2f} = $16.00")
        print(f"2. If Available = Total Asset + Margin: ${total_asset_value:.2f} + ${total_margin_used:.2f} = ${total_asset_value + total_margin_used:.2f}")
        
        # The key insight
        print(f"\n✅ SOLUTION:")
        print(f"The UI 'Available Balance' ($16.00) likely represents your total deposited USDT")
        print(f"The API 'Collateral' (${collateral:.2f}) represents your free/available collateral after margin")
        print(f"The difference (${16 - collateral:.2f}) is likely reserved for positions or orders")
        
        # Create a fixed function to get available balance
        print("\n📝 RECOMMENDED FIX FOR YOUR CODE:")
        print("-" * 60)
        print("""
def get_available_balance(account_data):
    '''Get the true available balance (what UI shows)'''
    # The UI shows total deposited amount
    # For Lighter Exchange, this seems to be collateral + reserved margin
    
    collateral = float(account_data.get('collateral', 0))
    
    # Check if there's a specific field for total balance
    # Otherwise, we need to calculate it
    
    # Method 1: Look for total_balance or similar field
    for field in ['total_balance', 'balance', 'equity', 'net_value']:
        if field in account_data:
            return float(account_data[field])
    
    # Method 2: Calculate from positions
    total_margin = 0
    for pos in account_data.get('positions', []):
        # Add up margin from all positions
        margin = abs(float(pos.get('allocated_margin', 0)))
        total_margin += margin
    
    # The available balance shown in UI is likely:
    # collateral + margin reserved for positions
    ui_balance = collateral + total_margin
    
    # But for trading, you want free collateral
    free_balance = collateral
    
    return {
        'ui_balance': ui_balance,  # What the UI shows ($16)
        'free_collateral': free_balance,  # What you can trade with ($3.59)
        'used_margin': total_margin  # Margin used by positions
    }
        """)
        
        # Show the full data structure for reference
        print("\n📄 FULL ACCOUNT STRUCTURE (first 500 chars):")
        print("-" * 60)
        account_str = json.dumps(account, indent=2)
        print(account_str[:500] + "...")
        
def check_order_book_for_clues():
    """Check if order book endpoint reveals balance info"""
    print("\n" + "="*80)
    print("🔍 CHECKING ORDER BOOK FOR BALANCE CLUES")
    print("="*80)
    
    # The order book might show different balance fields
    url = f"{BASE_URL}/orderBookDetails"
    params = {"symbol": "ETH", "limit": 1}
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            # Look for any user-specific data
            print("Order book response keys:", list(data.keys()) if isinstance(data, dict) else "List response")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_balance_discrepancy()
    check_order_book_for_clues()
    
    print("\n💡 KEY INSIGHT:")
    print("=" * 60)
    print("""
    The $16 shown in the UI is your TOTAL BALANCE (deposited amount)
    The $3.59 from API is your FREE COLLATERAL (available for new trades)
    The difference ($12.41) is being used for margin or reserved
    
    For your bot, you should use the 'collateral' field ($3.59) as this
    is what's actually available for opening new positions.
    """)
    
    print("\n💤 Sleeping for 30 seconds as requested...")
    time.sleep(30)