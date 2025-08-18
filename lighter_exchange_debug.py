#!/usr/bin/env python3
"""
🌙 Moon Dev's Lighter Exchange Account Balance Debug Script
This will help identify why your account shows $3.59 collateral instead of $16
"""

import os
import json
import requests
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://mainnet.zklighter.elliot.ai/api/v1"

class LighterDebugger:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        
    def make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            print(f"\n🔍 DEBUG: Calling {url}")
            if params:
                print(f"📋 Parameters: {json.dumps(params, indent=2)}")
            
            response = self.session.get(url, params=params)
            print(f"📡 Response Status: {response.status_code}")
            print(f"📝 Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Response received successfully")
                return data
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            print(f"💥 Request failed: {str(e)}")
            return {}
    
    def get_all_accounts(self, address: str) -> None:
        """Get all accounts for an address"""
        print("\n" + "="*80)
        print("🔍 FETCHING ALL ACCOUNTS FOR ADDRESS")
        print("="*80)
        
        # Try different endpoints
        endpoints = [
            "/accounts",
            "/account",
            "/user/accounts"
        ]
        
        for endpoint in endpoints:
            print(f"\n🎯 Trying endpoint: {endpoint}")
            
            # Try with address parameter
            data = self.make_request(endpoint, {"address": address})
            if data:
                self.display_account_data(data, f"{endpoint} with address")
            
            # Try with l1_address parameter
            data = self.make_request(endpoint, {"l1_address": address})
            if data:
                self.display_account_data(data, f"{endpoint} with l1_address")
                
            # Try without parameters
            data = self.make_request(endpoint)
            if data:
                self.display_account_data(data, f"{endpoint} without params")
    
    def get_account_by_index(self, index: int) -> None:
        """Get account by index using different methods"""
        print("\n" + "="*80)
        print(f"🔍 FETCHING ACCOUNT BY INDEX: {index}")
        print("="*80)
        
        # Method 1: Direct index
        params_list = [
            {"index": index},
            {"account_index": index},
            {"by": "index", "value": str(index)},
            {"by": "account_index", "value": str(index)}
        ]
        
        for params in params_list:
            print(f"\n🎯 Trying params: {params}")
            data = self.make_request("/accounts", params)
            if data:
                self.display_account_data(data, f"Method with params {params}")
    
    def get_balance_info(self, address: str) -> None:
        """Try to get balance information through various endpoints"""
        print("\n" + "="*80)
        print("🔍 FETCHING BALANCE INFORMATION")
        print("="*80)
        
        balance_endpoints = [
            "/balance",
            "/balances", 
            "/account/balance",
            "/user/balance",
            "/collateral",
            "/margin",
            "/wallet/balance"
        ]
        
        for endpoint in balance_endpoints:
            print(f"\n🎯 Trying balance endpoint: {endpoint}")
            
            # Try different parameter names
            param_names = ["address", "l1_address", "user_address", "wallet"]
            for param_name in param_names:
                data = self.make_request(endpoint, {param_name: address})
                if data:
                    print(f"✅ Got response with {param_name}:")
                    print(json.dumps(data, indent=2))
    
    def display_account_data(self, data: Dict[str, Any], method: str) -> None:
        """Display account data in a formatted way"""
        print(f"\n📊 Results from {method}:")
        print("-" * 60)
        
        if isinstance(data, dict):
            # Check if it's a single account or list of accounts
            if 'accounts' in data:
                accounts = data.get('accounts', [])
                print(f"Found {len(accounts)} account(s)")
                for i, acc in enumerate(accounts):
                    self.display_single_account(acc, i)
            else:
                # Single account
                self.display_single_account(data, 0)
        elif isinstance(data, list):
            print(f"Found {len(data)} account(s)")
            for i, acc in enumerate(data):
                self.display_single_account(acc, i)
    
    def display_single_account(self, acc: Dict[str, Any], index: int) -> None:
        """Display a single account's information"""
        print(f"\n💼 Account {index}:")
        
        # Display key fields
        fields_to_show = [
            'index', 'account_index', 'l1_address', 'collateral', 
            'total_asset_value', 'cross_asset_value', 'available_balance',
            'free_collateral', 'margin_balance', 'balance', 'equity',
            'unrealized_pnl', 'realized_pnl', 'maintenance_margin'
        ]
        
        for field in fields_to_show:
            if field in acc:
                value = acc[field]
                if isinstance(value, (int, float, str)) and str(value).replace('.', '').isdigit():
                    print(f"   {field}: ${value}")
                else:
                    print(f"   {field}: {value}")
        
        # Check for positions
        if 'positions' in acc and acc['positions']:
            print(f"   Positions: {len(acc['positions'])}")
            for pos in acc['positions']:
                symbol = pos.get('symbol', 'Unknown')
                size = pos.get('position', 0)
                value = pos.get('position_value', 0)
                pnl = pos.get('unrealized_pnl', 0)
                print(f"      - {symbol}: Size={size}, Value=${value}, PnL=${pnl}")
    
    def check_api_info(self) -> None:
        """Get general API information"""
        print("\n" + "="*80)
        print("🔍 CHECKING API GENERAL INFORMATION")
        print("="*80)
        
        info_endpoints = ["/", "/info", "/status", "/health"]
        
        for endpoint in info_endpoints:
            print(f"\n🎯 Checking {endpoint}")
            data = self.make_request(endpoint)
            if data:
                print(json.dumps(data, indent=2))

def main():
    """Main debug function"""
    print("🌙 Moon Dev's Lighter Exchange Balance Debugger")
    print("=" * 80)
    
    # Your wallet address from the debug output
    wallet_address = "0x3d652556b404E2c03Ff63D234619B408446BB49c"
    account_index = 7
    
    debugger = LighterDebugger()
    
    # 1. Check API info
    debugger.check_api_info()
    
    # 2. Get all accounts for the address
    debugger.get_all_accounts(wallet_address)
    
    # 3. Get account by index
    debugger.get_account_by_index(account_index)
    
    # 4. Try balance endpoints
    debugger.get_balance_info(wallet_address)
    
    print("\n" + "="*80)
    print("🎯 DIAGNOSIS SUMMARY")
    print("="*80)
    print(f"""
    Your situation:
    - Exchange UI shows: $16.00 available balance
    - API returns: $3.599203 collateral
    - Account Index: 7
    - Wallet: {wallet_address}
    
    Possible issues:
    1. The API might be showing 'collateral' (margin) vs 'available balance'
    2. There might be pending orders or positions affecting available balance
    3. The account index might be pointing to a sub-account
    4. There could be a delay in balance updates between UI and API
    
    Next steps:
    1. Check if there are any open orders reducing available balance
    2. Look for other balance fields in the API response
    3. Verify this is the correct account by checking the wallet address
    """)
    
    print("\n💤 Sleeping as requested...")
    time.sleep(30)  # Keep the sleep as requested

if __name__ == "__main__":
    main()