#!/usr/bin/env python3
"""
🌙 Moon Dev's Lighter Exchange Mystery Balance Investigator
Why is $12.40 missing when you have no orders or positions?
"""

import os
import json
import requests
import time
from datetime import datetime

BASE_URL = "https://mainnet.zklighter.elliot.ai/api/v1"

class MysteryBalanceInvestigator:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.wallet_address = "0x3d652556b404E2c03Ff63D234619B408446BB49c"
        self.account_index = 7
        
    def make_request(self, endpoint: str, params=None):
        """Make API request"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"❌ Error calling {endpoint}: {e}")
            return None
    
    def investigate_missing_funds(self):
        """Main investigation of the missing $12.40"""
        print("🕵️ MOON DEV'S MYSTERY BALANCE INVESTIGATION")
        print("=" * 80)
        print(f"""
        🔍 The Mystery:
        - UI shows: $16.00 available
        - API shows: $3.59 collateral  
        - Missing: $12.40
        - No open orders or order history
        """)
        
        # 1. Check main account
        print("\n1️⃣ CHECKING MAIN ACCOUNT DATA")
        print("-" * 60)
        account_data = self.make_request("/accounts", {"by": "index", "value": str(self.account_index)})
        
        if account_data and account_data.get('accounts'):
            account = account_data['accounts'][0]
            self.analyze_account(account)
        
        # 2. Check all accounts for this wallet
        print("\n2️⃣ CHECKING ALL ACCOUNTS FOR WALLET")
        print("-" * 60)
        all_accounts = self.make_request("/accounts", {"l1_address": self.wallet_address})
        if all_accounts:
            self.check_multiple_accounts(all_accounts)
        
        # 3. Check order history more thoroughly
        print("\n3️⃣ DEEP DIVE INTO ORDER HISTORY")
        print("-" * 60)
        self.check_order_history()
        
        # 4. Check for pending/cancelled orders
        print("\n4️⃣ CHECKING PENDING/CANCELLED ORDERS")
        print("-" * 60)
        self.check_pending_orders()
        
        # 5. Check deposit/withdrawal history
        print("\n5️⃣ CHECKING DEPOSIT/WITHDRAWAL HISTORY")
        print("-" * 60)
        self.check_transaction_history()
        
        # 6. Check if it's a sub-account issue
        print("\n6️⃣ CHECKING SUB-ACCOUNT STRUCTURE")
        print("-" * 60)
        self.check_subaccounts()
        
        # 7. Check market/trading fees
        print("\n7️⃣ CHECKING FEES AND RESERVES")
        print("-" * 60)
        self.check_fees_and_reserves()
        
    def analyze_account(self, account):
        """Detailed account analysis"""
        print(f"Account Index: {account.get('index', 'N/A')}")
        print(f"Account Type: {account.get('account_type', 'N/A')}")
        print(f"Status: {account.get('status', 'N/A')}")
        print(f"L1 Address: {account.get('l1_address', 'N/A')}")
        
        print(f"\n💰 Balance Fields:")
        balance_fields = [
            'collateral', 'total_asset_value', 'cross_asset_value',
            'available_balance', 'free_balance', 'locked_balance',
            'margin_balance', 'wallet_balance', 'account_balance',
            'net_value', 'equity', 'balance', 'total_balance',
            'usdt_balance', 'cash_balance', 'spot_balance'
        ]
        
        found_balances = {}
        for field in balance_fields:
            if field in account:
                value = account[field]
                found_balances[field] = value
                print(f"  {field}: ${value}")
        
        # Check nested structures
        print(f"\n🔍 Checking nested structures:")
        
        # Pool info might contain locked funds
        pool_info = account.get('pool_info', {})
        if pool_info:
            print(f"\n  Pool Info:")
            for key, value in pool_info.items():
                print(f"    {key}: {value}")
        
        # Check shares (might be staked/locked funds)
        shares = account.get('shares', [])
        if shares:
            print(f"\n  Shares: {len(shares)} found")
            total_share_value = sum(float(s.get('value', 0)) for s in shares if isinstance(s, dict))
            print(f"    Total share value: ${total_share_value}")
        
        # Check positions more carefully
        positions = account.get('positions', [])
        print(f"\n📊 Positions Analysis:")
        for pos in positions:
            print(f"\n  Symbol: {pos.get('symbol')}")
            for key, value in pos.items():
                if 'margin' in key.lower() or 'value' in key.lower() or 'collateral' in key.lower():
                    print(f"    {key}: {value}")
    
    def check_multiple_accounts(self, data):
        """Check if there are multiple accounts"""
        accounts = data.get('accounts', [])
        print(f"Found {len(accounts)} account(s) for this wallet")
        
        total_balance = 0
        for i, acc in enumerate(accounts):
            index = acc.get('index', 'N/A')
            collateral = float(acc.get('collateral', 0))
            total_balance += collateral
            print(f"\n  Account {i} (Index: {index}):")
            print(f"    Collateral: ${collateral}")
            print(f"    Status: {acc.get('status', 'N/A')}")
        
        print(f"\n  Total across all accounts: ${total_balance}")
        if abs(total_balance - 16.0) < 0.01:
            print("  ✅ FOUND IT! The $16 is split across multiple accounts!")
    
    def check_order_history(self):
        """Check order history with various endpoints"""
        endpoints = [
            f"/orders?account_index={self.account_index}",
            f"/order_history?account_index={self.account_index}",
            f"/trades?account_index={self.account_index}",
            f"/account/{self.account_index}/orders",
            f"/account/{self.account_index}/order_history",
            "/orders/history",
            "/orders/all"
        ]
        
        for endpoint in endpoints:
            print(f"\nTrying: {endpoint}")
            data = self.make_request(endpoint)
            if data:
                if isinstance(data, list):
                    print(f"  Found {len(data)} orders")
                elif isinstance(data, dict) and 'orders' in data:
                    print(f"  Found {len(data['orders'])} orders")
                else:
                    print(f"  Response type: {type(data).__name__}")
    
    def check_pending_orders(self):
        """Check for pending or cancelled orders that might lock funds"""
        endpoints = [
            f"/orders/pending?account_index={self.account_index}",
            f"/orders/open?account_index={self.account_index}",
            f"/orders/cancelled?account_index={self.account_index}",
            f"/account/{self.account_index}/pending_orders"
        ]
        
        for endpoint in endpoints:
            print(f"\nChecking: {endpoint}")
            data = self.make_request(endpoint)
            if data:
                print(f"  Found data: {json.dumps(data, indent=2)[:200]}...")
    
    def check_transaction_history(self):
        """Check deposits and withdrawals"""
        endpoints = [
            f"/deposits?address={self.wallet_address}",
            f"/withdrawals?address={self.wallet_address}",
            f"/transactions?address={self.wallet_address}",
            f"/account/{self.account_index}/transactions",
            "/deposit_history",
            "/withdrawal_history"
        ]
        
        for endpoint in endpoints:
            print(f"\nChecking: {endpoint}")
            data = self.make_request(endpoint)
            if data:
                print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
    
    def check_subaccounts(self):
        """Check if this is a sub-account of a main account"""
        # Try to get parent account
        endpoints = [
            f"/account/{self.account_index}/parent",
            f"/main_account?sub_account={self.account_index}",
            f"/accounts/hierarchy?address={self.wallet_address}"
        ]
        
        for endpoint in endpoints:
            print(f"\nChecking: {endpoint}")
            data = self.make_request(endpoint)
            if data:
                print(f"  Found: {json.dumps(data, indent=2)[:200]}...")
    
    def check_fees_and_reserves(self):
        """Check if there are any reserved amounts for fees"""
        # Get market info to check fee structures
        market_data = self.make_request("/orderBookDetails", {"symbol": "ETH", "limit": 1})
        
        if market_data and market_data.get('order_book_details'):
            details = market_data['order_book_details'][0]
            print(f"\nMarket fees for ETH:")
            print(f"  Taker fee: {details.get('taker_fee', 'N/A')}")
            print(f"  Maker fee: {details.get('maker_fee', 'N/A')}")
            print(f"  Liquidation fee: {details.get('liquidation_fee', 'N/A')}")
        
        # Check if there's a fee reserve
        print(f"\n💡 Hypothesis: Maybe Lighter Exchange reserves funds for:")
        print(f"  - Trading fees")
        print(f"  - Potential liquidation fees") 
        print(f"  - Minimum balance requirements")
        print(f"  - Gas fees for L2 operations")

def main():
    print("🌙 Moon Dev's Lighter Exchange Mystery Balance Investigation")
    print("=" * 80)
    print("Starting deep investigation of the missing $12.40...")
    
    investigator = MysteryBalanceInvestigator()
    investigator.investigate_missing_funds()
    
    print("\n" + "="*80)
    print("🎯 INVESTIGATION SUMMARY")
    print("="*80)
    print("""
    Possible explanations for the missing $12.40:
    
    1. MULTIPLE ACCOUNTS: The $16 might be split across multiple sub-accounts
    2. RESERVED FUNDS: Exchange might reserve funds for fees/liquidation
    3. PENDING SETTLEMENT: Funds might be in settlement from a previous action
    4. L2/L1 SPLIT: Some funds might be on L1 vs L2
    5. MINIMUM BALANCE: Exchange might enforce minimum balance requirements
    6. HIDDEN ORDERS: Orders might exist but not show in regular queries
    7. STAKING/POOL: Funds might be in a staking pool or liquidity provision
    8. API BUG: The API might have a bug showing incorrect collateral
    
    Next steps:
    - Contact Lighter Exchange support with these findings
    - Try depositing a small amount to see how balances change
    - Check if withdrawing the $3.59 is possible (don't do it, just check)
    """)
    
    print("\n💤 Sleeping for 30 seconds as requested...")
    time.sleep(30)

if __name__ == "__main__":
    main()