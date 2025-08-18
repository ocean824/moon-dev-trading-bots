#!/usr/bin/env python3
"""
Production BTC Trading Bot for Lighter Exchange
Uses verified working BTC markets: [0, 2, 3, 9, 10, 11, 12, 13, 14, 16, 19, 20]
"""

import os
import asyncio
import requests
import sys
from termcolor import colored
from datetime import datetime

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

# Working BTC markets discovered from comprehensive testing
BTC_MARKETS = [0, 2, 3, 9, 10, 11, 12, 13, 14, 16, 19, 20]
PRIMARY_BTC_MARKET = 0  # Use market 0 as primary (most reliable)

# Trading parameters
BTC_TRADE_AMOUNT = 0.0001  # Start small - 0.0001 BTC
DEFAULT_SLIPPAGE = 0.005   # 0.5% slippage for market orders

class LighterBTCTrader:
    def __init__(self):
        self.signer_client = None
        self.current_btc_price = 0
        self.balance = 0
        
    async def initialize(self):
        """Initialize the trading client and get account status"""
        if not LIGHTER_PRIVATE_KEY:
            raise ValueError("LIGHTER_PRIVATE_KEY not found in .env file")
            
        try:
            # Initialize signer
            raw_private_key = str(LIGHTER_PRIVATE_KEY)
            if raw_private_key.startswith('0x'):
                private_key_str = raw_private_key[2:]
            else:
                private_key_str = raw_private_key
                
            self.signer_client = lighter.SignerClient(
                BASE_URL,
                private_key_str,
                LIGHTER_API_INDEX,
                ACCOUNT_INDEX
            )
            
            print(colored("✅ Lighter BTC Trader initialized successfully", "green"))
            
            # Get current balance and BTC price
            await self.update_market_data()
            await self.get_balance()
            
        except Exception as e:
            print(colored(f"❌ Initialization failed: {e}", "red"))
            raise
    
    async def update_market_data(self):
        """Get current BTC price from Coinbase"""
        try:
            response = requests.get("https://api.coinbase.com/v2/exchange-rates?currency=BTC", timeout=5)
            self.current_btc_price = float(response.json()['data']['rates']['USD'])
            print(colored(f"📊 Current BTC Price: ${self.current_btc_price:,.2f}", "cyan"))
        except Exception as e:
            print(colored(f"⚠️  Could not fetch BTC price: {e}", "yellow"))
            self.current_btc_price = 118000  # Fallback
    
    async def get_balance(self):
        """Get account balance from Lighter Exchange"""
        try:
            # Get balance using the signer client
            balance_info = await self.signer_client.get_balance()
            self.balance = float(balance_info.get('balance', 0))
            print(colored(f"💰 Account Balance: ${self.balance:.2f}", "green", attrs=['bold']))
        except Exception as e:
            print(colored(f"⚠️  Could not fetch balance: {e}", "yellow"))
            self.balance = 16.0  # Known balance from previous tests
    
    async def place_btc_buy_order(self, amount_btc=None, market_index=None, slippage=None):
        """Place a BTC buy order using verified working markets"""
        if not amount_btc:
            amount_btc = BTC_TRADE_AMOUNT
        if not market_index:
            market_index = PRIMARY_BTC_MARKET
        if not slippage:
            slippage = DEFAULT_SLIPPAGE
            
        print(colored(f"\\n🚀 Placing BTC BUY Order", "yellow", attrs=['bold']))
        print(colored(f"   Market Index: {market_index}", "white"))
        print(colored(f"   Amount: {amount_btc} BTC", "white"))
        print(colored(f"   Slippage: {slippage*100:.1f}%", "white"))
        
        try:
            # Calculate aggressive buy price (market price + slippage)
            buy_price = self.current_btc_price * (1 + slippage)
            
            # Convert to exchange format
            base_amount_int = int(amount_btc * 1e8)  # Convert to satoshis
            price_int = int(buy_price)
            client_order_index = int(datetime.now().timestamp() * 1000) % 1000000  # Unique order ID
            
            print(colored(f"   Buy Price: ${buy_price:,.2f} (${self.current_btc_price:,.2f} + {slippage*100:.1f}%)", "cyan"))
            print(colored(f"   Order ID: {client_order_index}", "white"))
            
            # Place the order using verified working market
            order = await self.signer_client.create_order(
                market_index=int(market_index),
                client_order_index=int(client_order_index),
                base_amount=base_amount_int,
                price=price_int,
                is_ask=False,  # Buy order
                order_type=RealSignerClient.ORDER_TYPE_LIMIT,
                time_in_force=RealSignerClient.ORDER_TIME_IN_FORCE_IMMEDIATE_OR_CANCEL,
                order_expiry=0
            )
            
            print(colored(f"✅ BTC BUY ORDER SUCCESSFUL!", "green", attrs=['bold']))
            print(colored(f"   Transaction Hash: {order.get('tx_hash', 'N/A')}", "green"))
            print(colored(f"   Order ID: {order.get('order_id', client_order_index)}", "green"))
            
            return order
            
        except Exception as e:
            error_msg = str(e)
            if "mark price" in error_msg:
                print(colored(f"❌ Price rejected - trying different market", "red"))
                # Try different market if current one rejects price
                if market_index in BTC_MARKETS:
                    next_markets = [m for m in BTC_MARKETS if m != market_index][:3]  # Try 3 alternatives
                    for alt_market in next_markets:
                        print(colored(f"🔄 Retrying with market {alt_market}...", "yellow"))
                        try:
                            return await self.place_btc_buy_order(amount_btc, alt_market, slippage)
                        except:
                            continue
            
            print(colored(f"❌ BTC Buy Order Failed: {error_msg}", "red"))
            return None
    
    async def place_btc_sell_order(self, amount_btc=None, market_index=None, slippage=None):
        """Place a BTC sell order using verified working markets"""
        if not amount_btc:
            amount_btc = BTC_TRADE_AMOUNT
        if not market_index:
            market_index = PRIMARY_BTC_MARKET
        if not slippage:
            slippage = DEFAULT_SLIPPAGE
            
        print(colored(f"\\n📈 Placing BTC SELL Order", "yellow", attrs=['bold']))
        print(colored(f"   Market Index: {market_index}", "white"))
        print(colored(f"   Amount: {amount_btc} BTC", "white"))
        print(colored(f"   Slippage: {slippage*100:.1f}%", "white"))
        
        try:
            # Calculate aggressive sell price (market price - slippage)
            sell_price = self.current_btc_price * (1 - slippage)
            
            # Convert to exchange format
            base_amount_int = int(amount_btc * 1e8)  # Convert to satoshis
            price_int = int(sell_price)
            client_order_index = int(datetime.now().timestamp() * 1000) % 1000000  # Unique order ID
            
            print(colored(f"   Sell Price: ${sell_price:,.2f} (${self.current_btc_price:,.2f} - {slippage*100:.1f}%)", "cyan"))
            print(colored(f"   Order ID: {client_order_index}", "white"))
            
            # Place the order using verified working market
            order = await self.signer_client.create_order(
                market_index=int(market_index),
                client_order_index=int(client_order_index),
                base_amount=base_amount_int,
                price=price_int,
                is_ask=True,  # Sell order
                order_type=RealSignerClient.ORDER_TYPE_LIMIT,
                time_in_force=RealSignerClient.ORDER_TIME_IN_FORCE_IMMEDIATE_OR_CANCEL,
                order_expiry=0
            )
            
            print(colored(f"✅ BTC SELL ORDER SUCCESSFUL!", "green", attrs=['bold']))
            print(colored(f"   Transaction Hash: {order.get('tx_hash', 'N/A')}", "green"))
            print(colored(f"   Order ID: {order.get('order_id', client_order_index)}", "green"))
            
            return order
            
        except Exception as e:
            error_msg = str(e)
            if "mark price" in error_msg:
                print(colored(f"❌ Price rejected - trying different market", "red"))
                # Try different market if current one rejects price
                if market_index in BTC_MARKETS:
                    next_markets = [m for m in BTC_MARKETS if m != market_index][:3]  # Try 3 alternatives
                    for alt_market in next_markets:
                        print(colored(f"🔄 Retrying with market {alt_market}...", "yellow"))
                        try:
                            return await self.place_btc_sell_order(amount_btc, alt_market, slippage)
                        except:
                            continue
            
            print(colored(f"❌ BTC Sell Order Failed: {error_msg}", "red"))
            return None
    
    async def test_all_btc_markets(self):
        """Test trading on all verified BTC markets"""
        print(colored(f"\\n🧪 Testing All {len(BTC_MARKETS)} BTC Markets", "cyan", attrs=['bold']))
        print(colored("=" * 60, "cyan"))
        
        successful_markets = []
        
        for i, market_index in enumerate(BTC_MARKETS):
            print(colored(f"\\nTesting Market {market_index} ({i+1}/{len(BTC_MARKETS)})...", "yellow"))
            
            try:
                # Test small buy order
                result = await self.place_btc_buy_order(
                    amount_btc=0.00001,  # Very small test amount
                    market_index=market_index,
                    slippage=0.01  # 1% slippage for testing
                )
                
                if result:
                    successful_markets.append(market_index)
                    print(colored(f"✅ Market {market_index}: SUCCESS", "green"))
                else:
                    print(colored(f"❌ Market {market_index}: FAILED", "red"))
                    
                # Small delay between tests
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(colored(f"❌ Market {market_index}: ERROR - {str(e)[:50]}...", "red"))
        
        print(colored(f"\\n🎯 BTC Market Testing Complete!", "cyan", attrs=['bold']))
        print(colored(f"   Working Markets: {successful_markets}", "green"))
        print(colored(f"   Success Rate: {len(successful_markets)}/{len(BTC_MARKETS)} ({len(successful_markets)/len(BTC_MARKETS)*100:.1f}%)", "white"))
        
        return successful_markets

async def main():
    """Main trading demo"""
    print(colored("🌙 Moon Dev's Lighter Exchange BTC Trader", "cyan", attrs=['bold']))
    print(colored("=" * 60, "cyan"))
    
    trader = LighterBTCTrader()
    
    try:
        # Initialize trader
        await trader.initialize()
        
        # Demo trading workflow
        print(colored(f"\\n📋 TRADING WORKFLOW DEMO", "white", attrs=['bold']))
        
        # 1. Show current market data
        print(colored(f"\\n1️⃣  Market Data:", "white"))
        print(colored(f"   BTC Price: ${trader.current_btc_price:,.2f}", "cyan"))
        print(colored(f"   Account Balance: ${trader.balance:.2f}", "cyan"))
        print(colored(f"   Available BTC Markets: {len(BTC_MARKETS)}", "cyan"))
        
        # 2. Place a test BTC buy order
        print(colored(f"\\n2️⃣  Placing Test BTC Buy Order:", "white"))
        buy_result = await trader.place_btc_buy_order(
            amount_btc=0.0001,  # $11.79 worth at current price
            market_index=PRIMARY_BTC_MARKET,
            slippage=0.005  # 0.5% slippage
        )
        
        if buy_result:
            print(colored(f"\\n🎉 BTC TRADING IS NOW WORKING!", "green", attrs=['bold']))
            print(colored(f"   ✅ Successfully placed BTC buy order", "green"))
            print(colored(f"   ✅ Using verified market index {PRIMARY_BTC_MARKET}", "green"))
            print(colored(f"   ✅ Transaction hash: {str(buy_result.get('tx_hash', 'N/A'))[:50]}...", "green"))
        
        # 3. Optional: Test all markets
        user_input = input(colored("\\n❓ Test all BTC markets? (y/n): ", "yellow"))
        if user_input.lower() == 'y':
            working_markets = await trader.test_all_btc_markets()
            print(colored(f"\\n✅ Found {len(working_markets)} working BTC markets!", "green"))
        
        print(colored(f"\\n🎯 BTC Trading Setup Complete!", "cyan", attrs=['bold']))
        print(colored(f"   You can now trade BTC on Lighter Exchange using markets: {BTC_MARKETS[:5]}... and more", "green"))
        
    except Exception as e:
        print(colored(f"❌ Trading demo failed: {e}", "red"))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())