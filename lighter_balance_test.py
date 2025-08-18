#!/usr/bin/env python3
"""
🌙 Moon Dev's Lighter Exchange Balance Field Explorer
This script explores all balance-related fields in the API response
"""

import os
import json
import requests
import time
from datetime import datetime

BASE_URL = "https://mainnet.zklighter.elliot.ai/api/v1"

def explore_account_fields():
    """Explore all fields in the account response to find where $16 is stored"""
    
    print("🌙 Moon Dev's Balance Field Explorer")
    print("=" * 80)
    
    # Make the same request as your test suite
    url = f"{BASE_URL}/accounts"
    params = {"by": "index", "value": "7"}
    
    print(f"🔍 Requesting: {url}")
    print(f"📋 Parameters: {json.dumps(params, indent=2)}")
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('code') == 200 and data.get('accounts'):
            account = data['accounts'][0]
            
            print("\n📊 EXPLORING ALL NUMERIC FIELDS IN ACCOUNT:")
            print("-" * 80)
            
            # Recursively find all numeric fields
            numeric_fields = find_numeric_fields(account)
            
            # Sort by value to see which might be $16
            sorted_fields = sorted(numeric_fields, key=lambda x: abs(float(x[1]) - 16.0))
            
            print("\n🎯 Fields sorted by proximity to $16.00:")
            print("-" * 60)
            for path, value in sorted_fields[:20]:  # Show top 20 closest
                diff = abs(float(value) - 16.0)
                if diff < 0.01:
                    print(f"✅ {path}: ${value} (EXACT MATCH!)")
                elif diff < 1.0:
                    print(f"🔸 {path}: ${value} (close: diff=${diff:.2f})")
                else:
                    print(f"   {path}: ${value}")
            
            # Also check for any fields that might be hiding the balance
            print("\n🔍 Checking special balance calculations:")
            print("-" * 60)
            
            # Common balance calculations
            collateral = float(account.get('collateral', 0))
            total_asset = float(account.get('total_asset_value', 0))
            cross_asset = float(account.get('cross_asset_value', 0))
            
            # Check positions for margin usage
            positions_margin = 0
            positions_value = 0
            for pos in account.get('positions', []):
                positions_margin += abs(float(pos.get('allocated_margin', 0)))
                positions_value += abs(float(pos.get('position_value', 0)))
            
            print(f"Collateral: ${collateral}")
            print(f"Total Asset Value: ${total_asset}")
            print(f"Cross Asset Value: ${cross_asset}")
            print(f"Positions Margin: ${positions_margin}")
            print(f"Positions Value: ${positions_value}")
            
            # Calculate possible available balance
            print("\n💡 Possible calculations for available balance:")
            print(f"Total - Positions Margin: ${total_asset - positions_margin}")
            print(f"Collateral + something?: ${collateral + 12.40} = $16.00?")
            
            # Display full account data for manual inspection
            print("\n📄 FULL ACCOUNT DATA (for manual inspection):")
            print("-" * 80)
            print(json.dumps(account, indent=2))
            
        else:
            print("❌ Failed to get account data")
            print(json.dumps(data, indent=2))
            
    except Exception as e:
        print(f"💥 Error: {str(e)}")

def find_numeric_fields(obj, path=""):
    """Recursively find all numeric fields in an object"""
    numeric_fields = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            if isinstance(value, (int, float, str)):
                try:
                    # Try to convert to float
                    num_val = float(value)
                    if num_val > 0:  # Only positive values
                        numeric_fields.append((new_path, str(value)))
                except:
                    pass
            elif isinstance(value, (dict, list)):
                numeric_fields.extend(find_numeric_fields(value, new_path))
                
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            numeric_fields.extend(find_numeric_fields(item, new_path))
    
    return numeric_fields

def check_wallet_endpoint():
    """Check if there's a separate wallet/balance endpoint"""
    print("\n" + "="*80)
    print("🔍 CHECKING WALLET/BALANCE ENDPOINTS")
    print("="*80)
    
    wallet_address = "0x3d652556b404E2c03Ff63D234619B408446BB49c"
    
    # Try various endpoints that might show wallet balance
    endpoints = [
        f"/wallet/{wallet_address}",
        f"/balance/{wallet_address}",
        f"/user/{wallet_address}/balance",
        f"/address/{wallet_address}",
        "/wallet/balance",
        "/account/free_balance"
    ]
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        print(f"\n🎯 Trying: {url}")
        
        try:
            # Try GET request
            response = requests.get(url)
            if response.status_code == 200:
                print("✅ Success!")
                data = response.json()
                print(json.dumps(data, indent=2))
            else:
                print(f"❌ Status: {response.status_code}")
                
            # Also try with address as parameter
            response = requests.get(f"{BASE_URL}{endpoint.split('/')[1]}", 
                                  params={"address": wallet_address})
            if response.status_code == 200:
                print("✅ Success with address param!")
                data = response.json()
                print(json.dumps(data, indent=2))
                
        except Exception as e:
            print(f"💥 Error: {str(e)}")

if __name__ == "__main__":
    # Run the field explorer
    explore_account_fields()
    
    # Check wallet endpoints
    check_wallet_endpoint()
    
    print("\n💤 Keeping script alive for 30 seconds as requested...")
    time.sleep(30)