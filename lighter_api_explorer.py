#!/usr/bin/env python3
"""
🌙 Moon Dev's Lighter Exchange API Explorer
Discovers all available endpoints to find where the true balance is stored
"""

import os
import json
import requests
import time
from datetime import datetime

BASE_URL = "https://mainnet.zklighter.elliot.ai/api/v1"

def explore_all_endpoints():
    """Try to discover all API endpoints"""
    print("🌙 Moon Dev's Lighter Exchange API Explorer")
    print("=" * 80)
    
    wallet = "0x3d652556b404E2c03Ff63D234619B408446BB49c"
    account_index = 7
    
    # Common API patterns to try
    endpoint_patterns = [
        # Account endpoints
        "/account",
        "/accounts", 
        f"/account/{account_index}",
        f"/accounts/{account_index}",
        f"/account/index/{account_index}",
        
        # Wallet/balance endpoints
        "/wallet",
        "/wallets",
        f"/wallet/{wallet}",
        f"/wallet/{wallet}/balance",
        f"/address/{wallet}",
        f"/address/{wallet}/balance",
        
        # Balance specific
        "/balance",
        "/balances",
        f"/balance/{wallet}",
        f"/balance/account/{account_index}",
        "/account/balance",
        f"/account/{account_index}/balance",
        
        # User endpoints
        "/user",
        f"/user/{wallet}",
        f"/user/account/{account_index}",
        "/user/info",
        "/user/balance",
        
        # Portfolio/assets
        "/portfolio",
        "/assets", 
        "/funds",
        "/equity",
        "/margin",
        "/collateral",
        
        # Maybe it's under a different name
        "/deposit_balance",
        "/available_funds",
        "/free_collateral",
        "/trading_balance",
        "/spot_balance",
        "/usdt_balance",
        
        # Check if there's a summary endpoint
        "/summary",
        "/account_summary",
        "/overview",
        "/dashboard",
        
        # L1/L2 specific
        "/l1_balance",
        "/l2_balance", 
        f"/l1/{wallet}",
        f"/l2/{wallet}",
        
        # Maybe version differences
        "/v1/account",
        "/v2/account",
        "/api/account",
    ]
    
    session = requests.Session()
    discovered_endpoints = []
    
    print("🔍 Testing endpoints...")
    print("-" * 60)
    
    for endpoint in endpoint_patterns:
        url = f"https://mainnet.zklighter.elliot.ai/api/v1{endpoint}"
        
        try:
            # Try without parameters
            response = session.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ Found: {endpoint}")
                discovered_endpoints.append(endpoint)
                
                # Check if response contains balance info
                try:
                    data = response.json()
                    check_for_balance(data, endpoint)
                except:
                    pass
            
            # Try with parameters
            params_list = [
                {"address": wallet},
                {"l1_address": wallet},
                {"wallet": wallet},
                {"account_index": account_index},
                {"index": account_index},
                {"by": "index", "value": str(account_index)}
            ]
            
            for params in params_list:
                response = session.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    endpoint_with_params = f"{endpoint}?{params}"
                    if endpoint_with_params not in discovered_endpoints:
                        print(f"✅ Found with params: {endpoint_with_params}")
                        discovered_endpoints.append(endpoint_with_params)
                        
                        try:
                            data = response.json()
                            check_for_balance(data, endpoint_with_params)
                        except:
                            pass
                        
        except requests.exceptions.Timeout:
            continue
        except Exception:
            continue
    
    print(f"\n📊 Summary: Found {len(discovered_endpoints)} working endpoints")
    
    # Now let's check the API documentation endpoint
    print("\n🔍 Checking for API documentation...")
    doc_endpoints = [
        "/",
        "/docs",
        "/documentation", 
        "/api-docs",
        "/swagger",
        "/help",
        "/info",
        "/spec",
        "/openapi"
    ]
    
    for endpoint in doc_endpoints:
        url = f"https://mainnet.zklighter.elliot.ai/api/v1{endpoint}"
        try:
            response = session.get(url, timeout=5)
            if response.status_code == 200:
                print(f"📚 Documentation found at: {endpoint}")
                # Try to parse response
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        print(f"   Keys: {list(data.keys())[:10]}")
                except:
                    print(f"   (HTML response)")
        except:
            continue

def check_for_balance(data, endpoint):
    """Check if response contains balance close to $16"""
    if isinstance(data, dict):
        for key, value in data.items():
            try:
                if isinstance(value, (int, float, str)):
                    num_val = float(value)
                    if 15.5 < num_val < 16.5:
                        print(f"   🎯 FOUND BALANCE! {key}: ${num_val} in {endpoint}")
                elif isinstance(value, dict):
                    check_for_balance(value, f"{endpoint}.{key}")
                elif isinstance(value, list) and value:
                    for item in value:
                        if isinstance(item, dict):
                            check_for_balance(item, f"{endpoint}[].{key}")
            except:
                continue

def check_websocket_endpoints():
    """Check if there are WebSocket endpoints for real-time balance"""
    print("\n🔍 Checking for WebSocket endpoints...")
    print("-" * 60)
    
    ws_endpoints = [
        "wss://mainnet.zklighter.elliot.ai/ws",
        "wss://mainnet.zklighter.elliot.ai/websocket",
        "wss://mainnet.zklighter.elliot.ai/stream",
        "wss://mainnet.zklighter.elliot.ai/api/v1/ws",
        "wss://mainnet.zklighter.elliot.ai/api/v1/stream"
    ]
    
    print("Potential WebSocket endpoints (not tested):")
    for ws in ws_endpoints:
        print(f"  - {ws}")
    
    print("\nWebSocket might provide real-time balance updates")

def analyze_existing_response():
    """Analyze the response we already have more carefully"""
    print("\n🔍 Re-analyzing existing account response...")
    print("-" * 60)
    
    # The response you showed
    response = {
        "code": 200,
        "total": 1,
        "accounts": [{
            "code": 0,
            "account_type": 0,
            "index": 7,
            "l1_address": "0x3d652556b404E2c03Ff63D234619B408446BB49c",
            "cancel_all_time": 0,
            "total_order_count": 0,
            "total_isolated_order_count": 0,
            "pending_order_count": 0,
            "status": 0,
            "collateral": "3.599203",
            "account_index": 7,
            "name": "",
            "description": "",
            "can_invite": False,
            "referral_points_percentage": "",
            "positions": [{
                "market_id": 0,
                "symbol": "ETH",
                "initial_margin_fraction": "5.00",
                "open_order_count": 0,
                "pending_order_count": 0,
                "position_tied_order_count": 0,
                "sign": 1,
                "position": "0.0000",
                "avg_entry_price": "0.00",
                "position_value": "-0.000000",
                "unrealized_pnl": "0.000000",
                "realized_pnl": "0.000000", 
                "margin_mode": 0,
                "allocated_margin": "0.000000"
            }],
            "total_asset_value": "3.599203",
            "cross_asset_value": "3.599203",
            "pool_info": {
                "status": 0,
                "operator_fee": "0.0000",
                "min_operator_share_rate": "0.0000",
                "total_shares": 0,
                "operator_shares": 0,
                "share_price_1d": 0.001,
                "share_price_7d": 0.001,
                "share_price_30d": 0.001,
                "annual_percentage_yield": 0,
                "daily_returns": []
            },
            "shares": []
        }]
    }
    
    account = response["accounts"][0]
    
    print("🎯 Key observations:")
    print(f"1. All balance fields show the same value: $3.599203")
    print(f"   - collateral: {account['collateral']}")
    print(f"   - total_asset_value: {account['total_asset_value']}") 
    print(f"   - cross_asset_value: {account['cross_asset_value']}")
    
    print(f"\n2. Account has ZERO order history:")
    print(f"   - total_order_count: {account['total_order_count']}")
    print(f"   - pending_order_count: {account['pending_order_count']}")
    
    print(f"\n3. ETH position shows all zeros:")
    print(f"   - position: {account['positions'][0]['position']}")
    print(f"   - allocated_margin: {account['positions'][0]['allocated_margin']}")
    
    print(f"\n4. Account status: {account['status']} (might be important)")
    print(f"5. Account type: {account['account_type']} (might indicate sub-account)")
    
    print("\n💡 THEORY: The missing $12.40 might be:")
    print("- In a different account (check all accounts for this wallet)")
    print("- Pending deposit that hasn't fully settled")
    print("- L1 vs L2 bridge funds")
    print("- Initial margin requirement held by exchange")
    print("- A display bug in the UI showing wrong balance")

if __name__ == "__main__":
    # Run all explorations
    explore_all_endpoints()
    check_websocket_endpoints()
    analyze_existing_response()
    
    print("\n" + "="*80)
    print("🎯 FINAL RECOMMENDATIONS")
    print("="*80)
    print("""
    1. Try calling /accounts without any parameters to list ALL accounts
    2. Check if there's a parent/child account relationship
    3. Contact Lighter Exchange support - this seems like an API issue
    4. For now, use the $3.59 as your available balance for safety
    5. Try making a tiny trade to see how balances update
    
    The fact that you have no order history but $12.40 is missing suggests:
    - Initial deposit handling issue
    - Multiple account confusion
    - API bug showing wrong collateral
    """)
    
    print("\n💤 Sleeping for 30 seconds...")
    time.sleep(30)

if __name__ == "__main__":
    main()