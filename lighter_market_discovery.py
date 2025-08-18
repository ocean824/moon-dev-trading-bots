#!/usr/bin/env python3
"""
Comprehensive market discovery for Lighter Exchange to find BTC trading options
"""

import os
import asyncio
import requests
import sys
from termcolor import colored

# Add the Lighter Exchange directory to Python path
sys.path.append('/Users/md/Dropbox/dev/github/Lighter-Exchange-Bots')

try:
    from dotenv import load_dotenv
    import lighter_wrapper as lighter
    from lighter import SignerClient as RealSignerClient
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you have the required dependencies and .env file in the Lighter-Exchange-Bots directory")
    sys.exit(1)

# Load environment variables from Lighter Exchange directory
env_path = '/Users/md/Dropbox/dev/github/Lighter-Exchange-Bots/.env'
load_dotenv(dotenv_path=env_path)

# Configuration
LIGHTER_API_INDEX = int(os.getenv('LIGHTER_API_INDEX', 0))
LIGHTER_PRIVATE_KEY = os.getenv('LIGHTER_PRIVATE_KEY')
BASE_URL = "https://mainnet.zklighter.elliot.ai"
ACCOUNT_INDEX = 59501

async def discover_btc_markets():
    """Comprehensive search for BTC trading markets on Lighter Exchange"""
    print(colored("🚀 BTC Market Discovery for Lighter Exchange", "cyan", attrs=['bold']))
    print(colored("=" * 60, "cyan"))
    
    if not LIGHTER_PRIVATE_KEY:
        print(colored("❌ LIGHTER_PRIVATE_KEY not found in .env file", "red"))
        return
    
    try:
        # Initialize signer
        raw_private_key = str(LIGHTER_PRIVATE_KEY)
        if raw_private_key.startswith('0x'):
            private_key_str = raw_private_key[2:]
        else:
            private_key_str = raw_private_key
            
        signer_client = lighter.SignerClient(
            BASE_URL,
            private_key_str,
            LIGHTER_API_INDEX,
            ACCOUNT_INDEX
        )
        
        print(colored("✅ Signer initialized successfully", "green"))
        
        # Get current BTC price for reference
        try:
            response = requests.get("https://api.coinbase.com/v2/exchange-rates?currency=BTC", timeout=5)
            coinbase_btc_price = float(response.json()['data']['rates']['USD'])
            print(colored(f"📊 Current BTC Price: ${coinbase_btc_price:,.2f}", "white"))
        except Exception as e:
            print(colored(f"⚠️  Could not fetch BTC price: {e}", "yellow"))
            coinbase_btc_price = 118000  # Fallback price
        
        # Test extended range of market indices to find BTC
        markets_to_test = list(range(0, 21))  # Test 0-20
        active_markets = []
        btc_candidates = []
        
        print(colored(f"\\n🔍 Testing {len(markets_to_test)} market indices...", "yellow"))
        
        for market_index in markets_to_test:
            print(colored(f"\\n🧪 Testing Market Index {market_index}...", "yellow"))
            
            try:
                # Use varied test parameters to detect different market types
                client_order_index = 30000 + market_index
                
                # Test with BTC-like amount and pricing
                base_amount_int = int(0.0001 * 1e8)  # 0.0001 BTC in satoshis
                price_int = int(coinbase_btc_price * 0.99)  # 1% below market for quick IoC
                
                order = await signer_client.create_order(
                    market_index=int(market_index),
                    client_order_index=int(client_order_index),
                    base_amount=base_amount_int,
                    price=price_int,
                    is_ask=False,  # Buy order
                    order_type=RealSignerClient.ORDER_TYPE_LIMIT,
                    time_in_force=RealSignerClient.ORDER_TIME_IN_FORCE_IMMEDIATE_OR_CANCEL,
                    order_expiry=0
                )
                
                print(colored(f"✅ Market {market_index}: ACTIVE! BTC-like order accepted", "green", attrs=['bold']))
                print(colored(f"   Order Result: {str(order)[:100]}...", "green"))
                active_markets.append(market_index)
                btc_candidates.append(market_index)
                
            except Exception as e:
                error_msg = str(e)
                
                # Analyze error types to understand market characteristics
                if "mark price" in error_msg or "too far" in error_msg:
                    print(colored(f"⚠️  Market {market_index}: EXISTS but rejected BTC price", "yellow"))
                    active_markets.append(market_index)
                    
                    # Try ETH-like parameters to see if it's ETH market
                    try:
                        eth_response = requests.get("https://api.coinbase.com/v2/exchange-rates?currency=ETH", timeout=5)
                        eth_price = float(eth_response.json()['data']['rates']['USD'])
                        
                        # Test with ETH parameters
                        eth_amount = int(0.001 * 1e8)  # Smaller amount
                        eth_price_int = int(eth_price * 1.01)  # ETH price with slippage
                        
                        await signer_client.create_order(
                            market_index=int(market_index),
                            client_order_index=int(client_order_index + 1000),
                            base_amount=eth_amount,
                            price=eth_price_int,
                            is_ask=False,
                            order_type=RealSignerClient.ORDER_TYPE_LIMIT,
                            time_in_force=RealSignerClient.ORDER_TIME_IN_FORCE_IMMEDIATE_OR_CANCEL,
                            order_expiry=0
                        )
                        print(colored(f"   ✅ Market {market_index}: Accepts ETH-like orders", "cyan"))
                        
                    except Exception as eth_e:
                        print(colored(f"   ❓ Market {market_index}: Neither BTC nor ETH params work", "magenta"))
                        
                elif "BaseAmount" in error_msg:
                    print(colored(f"✅ Market {market_index}: ACTIVE! (amount validation failed but market exists)", "green"))
                    active_markets.append(market_index)
                    
                elif "market" in error_msg.lower() or "invalid" in error_msg.lower():
                    print(colored(f"❌ Market {market_index}: NOT ACTIVE", "red"))
                    
                else:
                    print(colored(f"💥 Market {market_index}: Unexpected error - {error_msg[:80]}...", "red"))
        
        # Summary report
        print(colored(f"\\n🎯 DISCOVERY COMPLETE!", "cyan", attrs=['bold']))
        print(colored("=" * 60, "cyan"))
        
        print(colored(f"\\n📊 RESULTS SUMMARY:", "white", attrs=['bold']))
        print(colored(f"   Active Markets Found: {len(active_markets)}", "green"))
        print(colored(f"   BTC Candidate Markets: {len(btc_candidates)}", "cyan"))
        
        if active_markets:
            print(colored(f"\\n✅ Active Market Indices: {active_markets}", "green"))
            
        if btc_candidates:
            print(colored(f"\\n🪙 BTC Trading Candidates: {btc_candidates}", "cyan", attrs=['bold']))
            print(colored(f"   These markets accepted BTC-like orders successfully!", "cyan"))
        else:
            print(colored(f"\\n⚠️  NO BTC MARKETS FOUND", "red", attrs=['bold']))
            print(colored(f"   Consider using ETH market (likely index 0) or check for higher market indices", "yellow"))
            
        # Specific recommendations
        print(colored(f"\\n💡 RECOMMENDATIONS:", "yellow", attrs=['bold']))
        if btc_candidates:
            print(colored(f"   → Use market index {btc_candidates[0]} for BTC trading", "green"))
        elif active_markets:
            print(colored(f"   → BTC trading may not be available. Consider ETH (likely index 0)", "yellow"))
            print(colored(f"   → Or test higher market indices beyond 20", "yellow"))
        else:
            print(colored(f"   → No active markets found. Check API connectivity and credentials", "red"))
        
    except Exception as e:
        print(colored(f"❌ Discovery failed: {e}", "red"))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(discover_btc_markets())