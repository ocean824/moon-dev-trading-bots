#!/usr/bin/env python3
"""
Dr. Data Dawg's Exchange Functionality Test Suite
Tests all core functions: balance, orders, positions, cancellations
"""

import os
import asyncio
import requests
import time
import logging
from dotenv import load_dotenv
from termcolor import colored
import lighter_wrapper as lighter

# Disable debug logging to prevent sensitive info from showing
logging.getLogger().setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

# Load environment variables
load_dotenv()

# Configuration
ETH_ADDRESS = os.getenv('ETH_ADDRESS')
LIGHTER_API_INDEX = int(os.getenv('LIGHTER_API_INDEX', 0))
LIGHTER_PRIVATE_KEY = os.getenv('LIGHTER_PRIVATE_KEY')
BASE_URL = "https://mainnet.zklighter.elliot.ai"
ACCOUNT_INDEX = 59501

# Test configuration
BTC_MARKET_INDEX = 1
TEST_SYMBOL = "BTC"
BALANCE_PERCENTAGE = 0.55  # Use 55% for orders (same as your successful order)
LEVERAGE = 50  # Use 50x leverage to meet minimum sizes

class ExchangeTester:
    def __init__(self):
        self.signer_client = None
        self.account_index = ACCOUNT_INDEX
        self.buy_order_id = None
        self.sell_order_id = None
        self.balance = 0
        self.btc_price = 0

    async def initialize(self):
        """Initialize signer client"""
        try:
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

            print(colored("✅ Signer initialized successfully", "green"))
            return True
        except Exception as e:
            print(colored(f"❌ Failed to initialize: {e}", "red"))
            return False

    def get_account_info(self):
        """Get account information"""
        try:
            # Mask ETH address for privacy
            masked_address = f"{ETH_ADDRESS[:6]}...{ETH_ADDRESS[-4:]}" if ETH_ADDRESS else "****"

            response = requests.get(
                f"{BASE_URL}/api/v1/account",
                params={"by": "l1_address", "value": ETH_ADDRESS}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('accounts'):
                    return data['accounts'][0]
            return None
        except Exception as e:
            # Don't print the full error as it may contain sensitive info
            print(colored(f"❌ Error getting account info", "red"))
            return None

    def print_balance(self):
        """Step 1: Get and print balance (no sensitive info)"""
        print(colored("\n" + "="*60, "cyan"))
        print(colored("📊 STEP 1: CHECK BALANCE", "cyan", attrs=['bold']))
        print(colored("="*60, "cyan"))

        account = self.get_account_info()
        if account:
            collateral = float(account.get('collateral', 0))
            total_asset_value = float(account.get('total_asset_value', 0))

            self.balance = collateral  # Store for later calculations

            print(colored(f"💰 Account Balance: ${collateral:.2f}", "green", attrs=['bold']))
            if total_asset_value != collateral:
                print(colored(f"📊 Total Asset Value: ${total_asset_value:.2f}", "cyan"))

            # Calculate amounts for trading
            order_size_usd = collateral * BALANCE_PERCENTAGE
            print(colored(f"📈 Will use {BALANCE_PERCENTAGE*100:.0f}% of balance: ${order_size_usd:.2f} per order", "white"))
        else:
            print(colored("❌ Could not retrieve balance", "red"))

        print(colored("="*60 + "\n", "cyan"))

    def get_btc_price(self):
        """Get real BTC price from Coinbase"""
        try:
            response = requests.get("https://api.coinbase.com/v2/exchange-rates?currency=BTC", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.btc_price = float(data['data']['rates']['USD'])
                return self.btc_price
        except Exception as e:
            print(f"Warning: Could not get BTC price: {e}")
            self.btc_price = 100000  # Fallback
        return self.btc_price

    async def place_limit_orders(self):
        """Step 2: Place limit buy and sell orders (won't fill)"""
        print(colored("\n" + "="*60, "cyan"))
        print(colored("📝 STEP 2: PLACE LIMIT ORDERS", "cyan", attrs=['bold']))
        print(colored("="*60, "cyan"))

        # Get current BTC price from Coinbase
        btc_price = self.get_btc_price()
        print(colored(f"💲 Current BTC Price (Coinbase): ${btc_price:,.2f}", "white"))

        # Get the last trade price from Lighter exchange
        try:
            import requests
            response = requests.get(f"{BASE_URL}/api/v1/orderBookDetails?market_id=1")
            if response.status_code == 200:
                data = response.json()
                if data.get('order_book_details'):
                    last_trade = data['order_book_details'][0].get('last_trade_price', btc_price)
                    print(colored(f"💲 Last Trade Price (Lighter): ${last_trade:,.1f}", "white"))
                    # Use Lighter's last trade price as reference
                    btc_price = last_trade
        except:
            pass

        # Place orders VERY close to current price (just $1 away)
        safe_bid = btc_price - 1
        safe_ask = btc_price + 1

        print(colored(f"\n📊 Placing limit orders VERY close to market:", "yellow"))
        print(colored(f"   Buy Limit:  ${safe_bid:,.1f} ($1 below last trade)", "green"))
        print(colored(f"   Sell Limit: ${safe_ask:,.1f} ($1 above last trade)", "red"))

        # Calculate BTC amount using 55% - leverage is applied by exchange
        order_size_usd = self.balance * BALANCE_PERCENTAGE
        btc_amount = order_size_usd / btc_price

        # Ensure minimum size
        min_btc = 0.00020
        if btc_amount < min_btc:
            btc_amount = min_btc
            order_size_usd = btc_amount * btc_price

        print(colored(f"📏 Order Size: {btc_amount:.5f} BTC (${order_size_usd:.2f})", "white"))

        from lighter import SignerClient as RealSignerClient

        try:
            # Place BUY order
            print(colored("\n🟢 Placing BUY limit order...", "green"))
            buy_order_id = int(time.time() * 1000) % 100000
            base_amount_int = int(btc_amount * 1e8)
            # IMPORTANT: price_decimals=1 means multiply by 10!
            price_int = int(safe_bid * 10)

            print(colored(f"DEBUG: market_index={BTC_MARKET_INDEX}", "cyan"))
            print(colored(f"DEBUG: order_id={buy_order_id}", "cyan"))
            print(colored(f"DEBUG: base_amount={base_amount_int} (from {btc_amount:.5f} BTC)", "cyan"))
            print(colored(f"DEBUG: price={price_int} (from ${safe_bid:,.1f} * 10 for decimals=1)", "cyan"))
            print(colored(f"DEBUG: is_ask=False (BUY)", "cyan"))

            # Use POST_ONLY to ensure it won't fill (becomes maker order)
            await self.signer_client.create_order(
                market_index=BTC_MARKET_INDEX,
                client_order_index=buy_order_id,
                base_amount=base_amount_int,
                price=price_int,
                is_ask=False,  # Buy
                order_type=RealSignerClient.ORDER_TYPE_LIMIT,
                time_in_force=RealSignerClient.ORDER_TIME_IN_FORCE_POST_ONLY,  # POST_ONLY won't fill
                order_expiry=RealSignerClient.DEFAULT_28_DAY_ORDER_EXPIRY
            )

            self.buy_order_id = buy_order_id
            print(colored(f"✅ BUY Order Placed! ID: {buy_order_id}", "green", attrs=['bold']))

            # Small delay between orders
            await asyncio.sleep(1)

            # Place SELL order
            print(colored("\n🔴 Placing SELL limit order...", "red"))
            sell_order_id = int(time.time() * 1000) % 100000
            # IMPORTANT: price_decimals=1 means multiply by 10!
            price_int_sell = int(safe_ask * 10)

            print(colored(f"DEBUG: market_index={BTC_MARKET_INDEX}", "cyan"))
            print(colored(f"DEBUG: order_id={sell_order_id}", "cyan"))
            print(colored(f"DEBUG: base_amount={base_amount_int}", "cyan"))
            print(colored(f"DEBUG: price={price_int_sell} (from ${safe_ask:,.1f} * 10 for decimals=1)", "cyan"))
            print(colored(f"DEBUG: is_ask=True (SELL)", "cyan"))

            # Use POST_ONLY to ensure it won't fill (becomes maker order)
            await self.signer_client.create_order(
                market_index=BTC_MARKET_INDEX,
                client_order_index=sell_order_id,
                base_amount=base_amount_int,
                price=price_int_sell,
                is_ask=True,  # Sell
                order_type=RealSignerClient.ORDER_TYPE_LIMIT,
                time_in_force=RealSignerClient.ORDER_TIME_IN_FORCE_POST_ONLY,  # POST_ONLY won't fill
                order_expiry=RealSignerClient.DEFAULT_28_DAY_ORDER_EXPIRY
            )

            self.sell_order_id = sell_order_id
            print(colored(f"✅ SELL Order Placed! ID: {sell_order_id}", "green", attrs=['bold']))

        except Exception as e:
            print(colored(f"❌ Error placing orders: {e}", "red"))
            import traceback
            traceback.print_exc()

        print(colored("\n💡 WARNING: Orders are $1 away from market - may fill!", "yellow"))
        print(colored("="*60 + "\n", "cyan"))

    async def wait_and_cancel(self):
        """Step 3: Wait 5 seconds and cancel orders"""
        print(colored("\n" + "="*60, "cyan"))
        print(colored("⏰ STEP 3: WAIT AND CANCEL ORDERS", "cyan", attrs=['bold']))
        print(colored("="*60, "cyan"))

        print(colored("⏳ Waiting 5 seconds to view orders on exchange...", "yellow"))
        for i in range(5, 0, -1):
            print(colored(f"   {i}...", "white"))
            await asyncio.sleep(1)

        # Cancel both orders
        try:
            if self.buy_order_id:
                print(colored(f"\n🚫 Cancelling BUY order {self.buy_order_id}...", "yellow"))
                await self.signer_client.cancel_order(
                    market_index=BTC_MARKET_INDEX,
                    order_index=self.buy_order_id
                )
                print(colored(f"✅ BUY order cancelled!", "green"))

            await asyncio.sleep(1)

            if self.sell_order_id:
                print(colored(f"\n🚫 Cancelling SELL order {self.sell_order_id}...", "yellow"))
                await self.signer_client.cancel_order(
                    market_index=BTC_MARKET_INDEX,
                    order_index=self.sell_order_id
                )
                print(colored(f"✅ SELL order cancelled!", "green"))

        except Exception as e:
            print(colored(f"❌ Error cancelling orders: {e}", "red"))

        print(colored("="*60 + "\n", "cyan"))

    async def place_market_buy(self):
        """Step 4: Place market buy order (40% of balance)"""
        print(colored("\n" + "="*60, "cyan"))
        print(colored("🚀 STEP 4: MARKET BUY ORDER", "cyan", attrs=['bold']))
        print(colored("="*60, "cyan"))

        # DON'T multiply by leverage - exchange applies leverage automatically
        # Just use the USD amount you want to risk
        order_size_usd = self.balance * BALANCE_PERCENTAGE
        btc_amount = order_size_usd / self.btc_price

        # Ensure minimum (0.00020 BTC ~= $24)
        min_btc_amount = 0.00020
        if btc_amount < min_btc_amount:
            btc_amount = min_btc_amount
            order_size_usd = btc_amount * self.btc_price
            print(colored(f"⚠️  Balance too low - using minimum: {min_btc_amount} BTC", "yellow"))

        print(colored(f"📊 Opening LONG position", "green", attrs=['bold']))
        print(colored(f"💰 Using ${order_size_usd:.2f} ({BALANCE_PERCENTAGE*100:.0f}% of balance)", "white"))
        print(colored(f"📏 Amount: {btc_amount:.5f} BTC", "white"))

        try:
            from lighter import SignerClient as RealSignerClient

            market_order_id = int(time.time() * 1000) % 100000
            base_amount_int = int(btc_amount * 1e8)
            # IMPORTANT: price_decimals=1 means multiply by 10!
            price_int = int(self.btc_price * 10)

            print(colored(f"\n🔥 Executing market buy...", "yellow", attrs=['bold']))
            print(colored(f"   Amount: {btc_amount:.5f} BTC", "white"))
            print(colored(f"   Price: {price_int:,} (${self.btc_price:,.2f} * 10)", "white"))

            await self.signer_client.create_market_order(
                market_index=BTC_MARKET_INDEX,
                client_order_index=market_order_id,
                base_amount=base_amount_int,
                avg_execution_price=price_int,
                is_ask=False  # Buy
            )

            print(colored(f"✅ Market BUY executed! ID: {market_order_id}", "green", attrs=['bold']))

        except Exception as e:
            print(colored(f"❌ Error placing market buy: {e}", "red"))

        print(colored("="*60 + "\n", "cyan"))

    def get_position(self):
        """Step 5: Get and print position"""
        print(colored("\n" + "="*60, "cyan"))
        print(colored("📊 STEP 5: CHECK POSITION", "cyan", attrs=['bold']))
        print(colored("="*60, "cyan"))

        account = self.get_account_info()
        if account:
            positions = account.get('positions', [])
            position_found = False

            for pos in positions:
                if pos.get('symbol') == TEST_SYMBOL:
                    position_found = True
                    size = float(pos.get('position', 0))
                    entry_price = pos.get('avg_entry_price', 'N/A')
                    unrealized_pnl = pos.get('unrealized_pnl', '0')

                    side = "LONG" if size > 0 else "SHORT" if size < 0 else "FLAT"
                    side_color = "green" if size > 0 else "red" if size < 0 else "yellow"

                    print(colored(f"📈 Symbol: {TEST_SYMBOL}", "white"))
                    print(colored(f"📊 Side: {side}", side_color, attrs=['bold']))
                    print(colored(f"📏 Size: {abs(size):.6f} BTC", "white"))
                    print(colored(f"💲 Entry Price: ${entry_price}", "white"))
                    print(colored(f"💸 Unrealized PnL: ${unrealized_pnl}", "yellow"))

                    break

            if not position_found:
                print(colored("📭 No active BTC position", "yellow"))
        else:
            print(colored("❌ Could not retrieve position", "red"))

        print(colored("="*60 + "\n", "cyan"))

    async def close_position(self):
        """Step 6: Wait and close position"""
        print(colored("\n" + "="*60, "cyan"))
        print(colored("🔄 STEP 6: CLOSE POSITION", "cyan", attrs=['bold']))
        print(colored("="*60, "cyan"))

        print(colored("⏳ Waiting 2 seconds...", "yellow"))
        await asyncio.sleep(2)

        # Get current position
        account = self.get_account_info()
        if account:
            positions = account.get('positions', [])

            for pos in positions:
                if pos.get('symbol') == TEST_SYMBOL:
                    size = float(pos.get('position', 0))

                    if size == 0:
                        print(colored("📭 No position to close", "yellow"))
                        break

                    # Close with opposite market order
                    try:
                        from lighter import SignerClient as RealSignerClient

                        close_order_id = int(time.time() * 1000) % 100000
                        base_amount_int = int(abs(size) * 1e8)
                        # IMPORTANT: price_decimals=1 means multiply by 10!
                        price_int = int(self.btc_price * 10)

                        is_long = size > 0
                        side_text = "SELL" if is_long else "BUY"

                        print(colored(f"\n🔥 Closing {('LONG' if is_long else 'SHORT')} with market {side_text}...", "yellow", attrs=['bold']))
                        print(colored(f"   Amount: {abs(size):.5f} BTC", "white"))
                        print(colored(f"   Price: {price_int:,} (${self.btc_price:,.2f} * 10)", "white"))

                        await self.signer_client.create_market_order(
                            market_index=BTC_MARKET_INDEX,
                            client_order_index=close_order_id,
                            base_amount=base_amount_int,
                            avg_execution_price=price_int,
                            is_ask=is_long  # Sell if long, buy if short
                        )

                        print(colored(f"✅ Position CLOSED! ID: {close_order_id}", "green", attrs=['bold']))

                    except Exception as e:
                        print(colored(f"❌ Error closing position: {e}", "red"))

                    break

        print(colored("="*60 + "\n", "cyan"))

async def run_test():
    """Run the complete test suite"""
    print(colored("\n" + "="*60, "magenta"))
    print(colored("🌙 DR. DATA DAWG'S EXCHANGE FUNCTIONALITY TEST", "magenta", attrs=['bold']))
    print(colored("="*60 + "\n", "magenta"))

    tester = ExchangeTester()

    if not await tester.initialize():
        return

    try:
        # Step 1: Check balance
        tester.print_balance()

        # Step 2: Place limit orders (won't fill)
        await tester.place_limit_orders()

        # Step 3: Wait and cancel
        await tester.wait_and_cancel()

        # Step 4: Market buy
        await tester.place_market_buy()

        # Wait a moment for order to process
        await asyncio.sleep(2)

        # Step 5: Check position
        tester.get_position()

        # Step 6: Close position
        await tester.close_position()

        # Wait and verify closed
        await asyncio.sleep(2)

        # Final position check
        print(colored("\n" + "="*60, "cyan"))
        print(colored("✅ FINAL VERIFICATION", "cyan", attrs=['bold']))
        print(colored("="*60, "cyan"))
        tester.get_position()

        print(colored("\n" + "="*60, "green"))
        print(colored("🎉 TEST SUITE COMPLETE!", "green", attrs=['bold']))
        print(colored("="*60 + "\n", "green"))

    except Exception as e:
        print(colored(f"\n❌ Test failed: {e}", "red", attrs=['bold']))
        import traceback
        traceback.print_exc()

def main():
    """Main entry point"""
    if not ETH_ADDRESS or not LIGHTER_PRIVATE_KEY:
        print(colored("❌ Missing required environment variables", "red"))
        print(colored("   Please check .env file for ETH_ADDRESS and LIGHTER_PRIVATE_KEY", "yellow"))
        return

    asyncio.run(run_test())

if __name__ == "__main__":
    main()
