#!/usr/bin/env python3
"""
Token Holder Analysis Script
Analyzes token holders, KOLs, and buyer percentages for Solana tokens
"""

import sys
import requests
import pandas as pd
import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv('BIRDEYE_KEY')
if not API_KEY:
    print("❌ Error: BIRDEYE_KEY not found in environment variables")
    print("Please set your Birdeye API key in a .env file")
    sys.exit(1)

BASE_URL = "https://public-api.birdeye.so"

# Sample KOL list (this would typically be loaded from a file or database)
KOL_LIST = [
    "2yXTyarttn2pTZ6cwt4DqmrRuBw1G7pmFv9oT6MStdKP",
    "AGWdoU4j4MGJTkSor7ZSkNiF8oPe15754hsuLmwcEyzC",
    "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",
    # Add more KOL addresses here as needed
]

def get_token_security_info(token_address):
    """Get token security information including holder data"""
    url = f"{BASE_URL}/defi/token_security?address={token_address}"
    headers = {"X-API-KEY": API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        if data.get('success'):
            return data.get('data', {})
        else:
            print(f"❌ API Error: {data.get('message', 'Unknown error')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return None

def get_token_overview(token_address):
    """Get token overview for additional metrics"""
    url = f"{BASE_URL}/defi/token_overview?address={token_address}"
    headers = {"X-API-KEY": API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        if data.get('success'):
            return data.get('data', {})
        else:
            print(f"❌ API Error: {data.get('message', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting token overview: {e}")
        return None

def get_token_holders(token_address):
    """Get token holder information (if available through API)"""
    # Note: This endpoint may not be available in all Birdeye API plans
    # This is a placeholder for holder data analysis
    url = f"{BASE_URL}/defi/token_holders?address={token_address}"
    headers = {"X-API-KEY": API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', {})
    except:
        pass
    
    return None

def analyze_kol_holdings(token_address, kol_addresses):
    """Analyze how many KOLs from the list are holding the token"""
    kol_holders = []
    total_kols = len(kol_addresses)
    
    print(f"🔍 Checking {total_kols} KOL addresses for token holdings...")
    
    for i, kol_address in enumerate(kol_addresses, 1):
        try:
            # Check if KOL holds the token using wallet API
            url = f"{BASE_URL}/v1/wallet/token_list?wallet={kol_address}"
            headers = {"x-chain": "solana", "X-API-KEY": API_KEY}
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'items' in data['data']:
                    for token in data['data']['items']:
                        if token.get('address') == token_address:
                            kol_holders.append({
                                'kol_address': kol_address,
                                'amount': token.get('uiAmount', 0),
                                'usd_value': token.get('valueUsd', 0)
                            })
                            break
            
            # Progress indicator
            if i % 10 == 0:
                print(f"   Checked {i}/{total_kols} KOLs...")
                
            # Rate limiting
            time.sleep(0.1)
            
        except Exception as e:
            print(f"   Error checking KOL {kol_address[:8]}...: {e}")
            continue
    
    return kol_holders

def format_number(num):
    """Format large numbers for display"""
    if num >= 1e9:
        return f"{num/1e9:.2f}B"
    elif num >= 1e6:
        return f"{num/1e6:.2f}M"
    elif num >= 1e3:
        return f"{num/1e3:.2f}K"
    else:
        return f"{num:.2f}"

def analyze_token_holders(token_address):
    """Main function to analyze token holders"""
    print(f"\n🌙 Token Holder Analysis for: {token_address}")
    print("=" * 80)
    
    # Get token security info
    print("\n📊 Fetching token security information...")
    security_info = get_token_security_info(token_address)
    
    if not security_info:
        print("❌ Could not retrieve token security information")
        return
    
    # Get token overview
    print("📊 Fetching token overview...")
    overview_info = get_token_overview(token_address)
    
    # Extract holder information
    total_supply = security_info.get('totalSupply', 0)
    top10_holder_balance = security_info.get('top10HolderBalance', 0)
    top10_holder_percent = security_info.get('top10HolderPercent', 0)
    top10_user_balance = security_info.get('top10UserBalance', 0)
    top10_user_percent = security_info.get('top10UserPercent', 0)
    creator_balance = security_info.get('creatorBalance', 0)
    creator_percentage = security_info.get('creatorPercentage', 0)
    
    # Display basic holder statistics
    print(f"\n📈 HOLDER STATISTICS")
    print(f"   Total Supply: {format_number(total_supply)}")
    print(f"   Creator Balance: {format_number(creator_balance)} ({creator_percentage:.2f}%)")
    print(f"   Top 10 Holder Balance: {format_number(top10_holder_balance)} ({top10_holder_percent:.2f}%)")
    print(f"   Top 10 User Balance: {format_number(top10_user_balance)} ({top10_user_percent:.2f}%)")
    
    # Calculate concentration metrics
    concentration_risk = "HIGH" if top10_holder_percent > 50 else "MEDIUM" if top10_holder_percent > 30 else "LOW"
    print(f"   Concentration Risk: {concentration_risk}")
    
    # Analyze KOL holdings
    print(f"\n👑 KOL ANALYSIS")
    kol_holders = analyze_kol_holdings(token_address, KOL_LIST)
    
    total_kols = len(KOL_LIST)
    kol_holding_count = len(kol_holders)
    kol_holding_percentage = (kol_holding_count / total_kols) * 100 if total_kols > 0 else 0
    
    print(f"   Total KOLs in list: {total_kols}")
    print(f"   KOLs holding token: {kol_holding_count}")
    print(f"   KOL holding percentage: {kol_holding_percentage:.2f}%")
    
    if kol_holders:
        print(f"\n   KOL HOLDERS DETAILS:")
        total_kol_usd_value = 0
        for holder in kol_holders:
            print(f"   • {holder['kol_address'][:8]}... - {format_number(holder['amount'])} tokens (${format_number(holder['usd_value'])})")
            total_kol_usd_value += holder.get('usd_value', 0)
        print(f"   Total KOL Holdings Value: ${format_number(total_kol_usd_value)}")
    
    # Buyer/Seller analysis from overview
    if overview_info:
        print(f"\n📊 TRADING ACTIVITY (Last 24h)")
        buy24h = overview_info.get('buy24h', 0)
        sell24h = overview_info.get('sell24h', 0)
        total_trades = buy24h + sell24h
        
        if total_trades > 0:
            buy_percentage = (buy24h / total_trades) * 100
            sell_percentage = (sell24h / total_trades) * 100
            
            print(f"   Total Trades: {total_trades}")
            print(f"   Buy Orders: {buy24h} ({buy_percentage:.2f}%)")
            print(f"   Sell Orders: {sell24h} ({sell_percentage:.2f}%)")
            print(f"   Buy/Sell Ratio: {buy_percentage/sell_percentage:.2f}" if sell_percentage > 0 else "   Buy/Sell Ratio: ∞")
        else:
            print("   No trading activity in last 24h")
        
        # Additional metrics
        unique_wallets = overview_info.get('uniqueWallet24h', 0)
        volume_usd = overview_info.get('v24hUSD', 0)
        liquidity = overview_info.get('liquidity', 0)
        
        print(f"   Unique Wallets (24h): {unique_wallets}")
        print(f"   Volume (24h): ${format_number(volume_usd)}")
        print(f"   Liquidity: ${format_number(liquidity)}")
    
    # Summary and recommendations
    print(f"\n📋 ANALYSIS SUMMARY")
    print(f"   • Token Address: {token_address}")
    print(f"   • Concentration Risk: {concentration_risk}")
    print(f"   • KOL Adoption: {kol_holding_percentage:.2f}% ({kol_holding_count}/{total_kols})")
    
    if kol_holding_percentage > 20:
        print(f"   • ✅ HIGH KOL adoption - {kol_holding_percentage:.2f}% of tracked KOLs are holding")
    elif kol_holding_percentage > 10:
        print(f"   • ⚠️ MODERATE KOL adoption - {kol_holding_percentage:.2f}% of tracked KOLs are holding")
    else:
        print(f"   • ❌ LOW KOL adoption - Only {kol_holding_percentage:.2f}% of tracked KOLs are holding")
    
    if overview_info and total_trades > 0:
        if buy_percentage > 60:
            print(f"   • 🚀 Strong buying pressure - {buy_percentage:.1f}% buy orders")
        elif buy_percentage < 40:
            print(f"   • 📉 Selling pressure - {sell_percentage:.1f}% sell orders")
        else:
            print(f"   • ⚖️ Balanced trading - {buy_percentage:.1f}% buy, {sell_percentage:.1f}% sell")

def main():
    """Main execution function"""
    if len(sys.argv) != 2:
        print("Usage: python token_holder_checker.py <TOKEN_ADDRESS>")
        print("Example: python token_holder_checker.py DitHyRMQiSDhn5cnKMJV2CDDt6sVct96YrECiM49pump")
        sys.exit(1)
    
    token_address = sys.argv[1]
    
    # Validate token address format (basic check)
    if len(token_address) < 32 or len(token_address) > 44:
        print("❌ Invalid token address format")
        sys.exit(1)
    
    try:
        analyze_token_holders(token_address)
        print(f"\n✅ Analysis complete!")
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️ Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()