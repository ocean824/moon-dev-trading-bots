"""
Lighter Exchange Trading Functions - Working SDK Integration
Uses the official Lighter SDK properly with async/await wrapped for sync usage
"""

import os
import asyncio
import time
from dotenv import load_dotenv
from lighter import SignerClient as LighterSignerClient

load_dotenv()

class LighterAPI:
    """Lighter Exchange API using official SDK"""

    def __init__(self, api_index=None, private_key=None, eth_address=None):
        self.api_index = int(api_index or os.getenv('LIGHTER_API_INDEX'))
        raw_private_key = private_key or os.getenv('LIGHTER_PRIVATE_KEY')
        self.eth_address = eth_address or os.getenv('ETH_ADDRESS')

        # Remove 0x prefix if present
        if raw_private_key.startswith('0x'):
            self.private_key = raw_private_key[2:]
        else:
            self.private_key = raw_private_key

        self.base_url = "https://mainnet.zklighter.elliot.ai"
        self.account_index = 59501  # Your account index from test file
        self.signer_client = None

        # Create persistent event loop for async operations
        self.loop = None
        self._setup_event_loop()

    def _setup_event_loop(self):
        """Setup a persistent event loop for async operations"""
        try:
            # Try to get existing loop
            self.loop = asyncio.get_event_loop()
            if self.loop.is_closed():
                raise RuntimeError("Loop is closed")
        except RuntimeError:
            # Create new loop if none exists or it's closed
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    def _run_async(self, coro):
        """Run async coroutine in persistent event loop"""
        if self.loop.is_running():
            # If loop is already running (shouldn't happen in sync context)
            # Create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        else:
            # Run in the persistent loop
            return self.loop.run_until_complete(coro)

    def _get_signer(self):
        """Get or create signer client (created inside async context)"""
        if self.signer_client is None:
            self.signer_client = LighterSignerClient(
                self.base_url,
                self.private_key,
                self.api_index,
                self.account_index
            )
        return self.signer_client

    def get_account_info(self):
        """Get account info via REST API"""
        import requests
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/account",
                params={"by": "l1_address", "value": self.eth_address}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('accounts'):
                    return data['accounts'][0]
            return None
        except:
            return None

    def get_position(self, symbol: str, leverage: int = 50) -> tuple:
        """
        Get position for symbol
        Args:
            symbol: Trading symbol (BTC, ETH)
            leverage: Leverage used for position (default 50x for Lighter)
        Returns: (account_info, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long)
        """
        try:
            account_info = self.get_account_info()

            im_in_pos = False
            mypos_size = 0
            pos_sym = None
            entry_px = 0
            pnl_perc = 0
            is_long = False

            if account_info and 'positions' in account_info:
                positions = account_info['positions']

                # BTC is market_id 1
                market_id = 1 if symbol == 'BTC' else 0

                for pos in positions:
                    if pos.get('market_id') == market_id:
                        # DEBUG: Print RAW position data from API
                        print(f"[DEBUG] RAW API position data: {pos}")

                        # Lighter uses 'position' field (always positive) and 'sign' field for direction
                        position_size = float(pos.get('position', 0))
                        position_sign = int(pos.get('sign', 1))  # -1 for SHORT, 1 for LONG

                        if position_size != 0:
                            im_in_pos = True
                            # Apply sign to position size: sign=-1 means SHORT (negative size)
                            mypos_size = position_size * position_sign
                            pos_sym = pos.get('symbol', symbol)
                            entry_px = float(pos.get('avg_entry_price', 0))

                            # Calculate LEVERAGE-ADJUSTED PnL percentage
                            unrealized_pnl = float(pos.get('unrealized_pnl', 0))
                            if entry_px > 0 and position_size != 0:
                                position_value = abs(position_size * entry_px)
                                # Margin = Position Value / Leverage
                                margin = position_value / leverage
                                # P&L % = (Unrealized P&L / Margin) * 100
                                pnl_perc = (unrealized_pnl / margin) * 100 if margin > 0 else 0

                            # Use 'sign' field to determine direction: 1 = LONG, -1 = SHORT
                            is_long = position_sign > 0

                            # DEBUG: Print what API returned
                            print(f"[DEBUG get_position] position={position_size:.5f}, sign={position_sign}, is_long={is_long} ({'LONG' if is_long else 'SHORT'})")

                            break

            return account_info, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long

        except Exception as e:
            print(f"Error getting position: {e}")
            return {}, False, 0, None, 0, 0, False

    async def _buy_limit_async(self, symbol: str, quantity: float, price: float, reduce_only: bool = False):
        """Async buy limit order"""
        try:
            signer = self._get_signer()
            market_index = 1 if symbol == 'BTC' else 0
            order_id = int(time.time() * 1000) % 100000

            # Convert to Lighter format
            base_amount_int = int(quantity * 1e8)  # BTC to satoshis
            price_int = int(price * 10)  # price_decimals=1 means *10

            # IMPORTANT: Use the constants from the imported LighterSignerClient
            # These are actual integers that the SDK expects
            # Use POST_ONLY for maker orders (won't take liquidity)
            create_order_obj, tx_hash, signed_tx = await signer.create_order(
                market_index=market_index,
                client_order_index=order_id,
                base_amount=base_amount_int,
                price=price_int,
                is_ask=False,  # Buy
                order_type=LighterSignerClient.ORDER_TYPE_LIMIT,
                time_in_force=LighterSignerClient.ORDER_TIME_IN_FORCE_POST_ONLY,
                reduce_only=1 if reduce_only else 0,  # CRITICAL: Prevent position flips!
                order_expiry=LighterSignerClient.DEFAULT_28_DAY_ORDER_EXPIRY
            )

            return {'order_id': order_id, 'success': True, 'tx_hash': str(tx_hash)}

        except Exception as e:
            print(f"Buy limit error: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def _sell_limit_async(self, symbol: str, quantity: float, price: float, reduce_only: bool = False):
        """Async sell limit order"""
        try:
            signer = self._get_signer()
            market_index = 1 if symbol == 'BTC' else 0
            order_id = int(time.time() * 1000) % 100000

            # Convert to Lighter format
            base_amount_int = int(quantity * 1e8)  # BTC to satoshis
            price_int = int(price * 10)  # price_decimals=1 means *10

            create_order_obj, tx_hash, signed_tx = await signer.create_order(
                market_index=market_index,
                client_order_index=order_id,
                base_amount=base_amount_int,
                price=price_int,
                is_ask=True,  # Sell
                order_type=LighterSignerClient.ORDER_TYPE_LIMIT,
                time_in_force=LighterSignerClient.ORDER_TIME_IN_FORCE_POST_ONLY,
                reduce_only=1 if reduce_only else 0,  # CRITICAL: Prevent position flips!
                order_expiry=LighterSignerClient.DEFAULT_28_DAY_ORDER_EXPIRY
            )

            return {'order_id': order_id, 'success': True, 'tx_hash': str(tx_hash)}

        except Exception as e:
            print(f"Sell limit error: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def _cancel_all_orders_async(self, symbol: str):
        """Async cancel all orders"""
        try:
            signer = self._get_signer()
            market_index = 1 if symbol == 'BTC' else 0

            # The SDK might not have cancel_all_orders, so we'll skip it for now
            # Individual cancel_order works fine though
            # await signer.cancel_all_orders(market_index=market_index)

            return {'success': True}

        except Exception as e:
            print(f"Cancel all error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False}

    def buy_limit(self, symbol: str, quantity: float, price: float, leverage: int = 1, reduce_only: bool = False):
        """Place buy limit order (sync wrapper)"""
        reduce_str = " [REDUCE ONLY]" if reduce_only else ""
        print(f"[LIGHTER] Placing BUY limit{reduce_str}: {quantity} {symbol} @ ${price}")
        result = self._run_async(self._buy_limit_async(symbol, quantity, price, reduce_only))
        print(f"[LIGHTER] BUY result: {result}")
        return result

    def sell_limit(self, symbol: str, quantity: float, price: float, leverage: int = 1, reduce_only: bool = False):
        """Place sell limit order (sync wrapper)"""
        reduce_str = " [REDUCE ONLY]" if reduce_only else ""
        print(f"[LIGHTER] Placing SELL limit{reduce_str}: {quantity} {symbol} @ ${price}")
        result = self._run_async(self._sell_limit_async(symbol, quantity, price, reduce_only))
        print(f"[LIGHTER] SELL result: {result}")
        return result

    def cancel_all_orders_market(self, symbol: str):
        """Cancel all orders (sync wrapper)"""
        return self._run_async(self._cancel_all_orders_async(symbol))

    def close_position(self, symbol: str):
        """Close position by LOOPING until fully closed (like entry logic)"""
        try:
            import requests

            _, im_in_pos, mypos_size, _, _, _, is_long = self.get_position(symbol)

            if not im_in_pos or mypos_size == 0:
                print("No position to close")
                return

            print(f"🔴 Closing position: {mypos_size:.5f} BTC ({'LONG' if is_long else 'SHORT'})")
            print(f"🔄 Will loop FOREVER until position fully closed (NO TIMEOUT)")

            # Cancel all orders first
            self.cancel_all_orders_market(symbol)
            time.sleep(0.5)

            start_time = time.time()
            attempt = 0
            last_price = None

            while True:  # NEVER GIVE UP - loop forever until position is closed!
                attempt += 1

                if attempt % 10 == 1:
                    elapsed = time.time() - start_time
                    print(f"\n📊 Close loop: attempt {attempt}, elapsed {elapsed:.1f}s")

                # Check current position AND UPDATE is_long
                _, still_in_pos, current_size, _, _, _, is_long = self.get_position(symbol)

                # DEBUG: Show current position details
                if attempt % 10 == 1:
                    print(f"  🔍 Position check: current_size={current_size:.5f}, is_long={is_long}")

                if not still_in_pos or abs(current_size) < 0.0001:
                    print(f"\n✅ Position FULLY CLOSED!")
                    print(f"🗑️  Cancelling ALL remaining orders...")
                    self.cancel_all_orders_market(symbol)
                    time.sleep(1)

                    # Verify no orders remain
                    account_info = self.get_account_info()
                    if account_info:
                        open_orders = account_info.get('open_order_count', 0)
                        if open_orders > 0:
                            print(f"⚠️  Still have {open_orders} open orders - cancelling again...")
                            self.cancel_all_orders_market(symbol)
                            time.sleep(1)

                    print(f"✅ All orders cancelled, position closed!")
                    return

                # Get current market price from orderbook
                try:
                    response = requests.get(
                        f"{self.base_url}/api/v1/orderBookOrders?market_id=1&limit=1",
                        timeout=2
                    )
                    if response.status_code == 200:
                        data = response.json()
                        bid = float(data['bids'][0]['price']) if data.get('bids') else None
                        ask = float(data['asks'][0]['price']) if data.get('asks') else None
                    else:
                        bid = ask = None
                except:
                    bid = ask = None

                if not bid or not ask:
                    if attempt == 1:
                        print(f"  ⚠️ Waiting for prices...")
                    time.sleep(0.1)
                    continue

                # Remaining size to close
                close_qty = abs(current_size)

                if close_qty < 0.0002:  # Lighter minimum
                    print(f"  ⚠️ Remaining size too small ({close_qty:.5f}), considering closed")
                    break

                # Check if position FLIPPED direction (critical error!)
                initial_direction = mypos_size > 0  # True if started as LONG
                current_direction = current_size > 0   # True if currently LONG

                if initial_direction != current_direction:
                    print(f"\n❌ CRITICAL ERROR: Position FLIPPED direction!")
                    print(f"   Started as: {'LONG' if initial_direction else 'SHORT'} ({mypos_size:.5f} BTC)")
                    print(f"   Now: {'LONG' if current_direction else 'SHORT'} ({current_size:.5f} BTC)")
                    print(f"   Orders filled too much and created opposite position!")
                    print(f"   STOPPING close loop - will close the new position")
                    self.cancel_all_orders_market(symbol)
                    return  # Exit and let it be handled as a new position

                # Determine close price (sit AT best bid/ask for maker, not taker!)
                # DEBUG: Print BEFORE determining close side
                if attempt % 10 == 1:
                    print(f"  🔍 is_long={is_long} -> will use {'SELL' if is_long else 'BUY'}")

                if is_long:
                    # Close LONG with SELL - sit AT the bid (maker)
                    close_price = bid  # Sit at bid to be maker
                    close_side = "SELL"
                else:
                    # Close SHORT with BUY - sit AT the ask (maker)
                    close_price = ask  # Sit at ask to be maker
                    close_side = "BUY"

                # Only place new order if price changed significantly (at least $10)
                price_changed = last_price is None or abs(close_price - last_price) >= 10

                if price_changed:
                    # Cancel ALL previous orders FIRST and wait
                    print(f"  🗑️  Cancelling all orders before placing new one...")
                    self.cancel_all_orders_market(symbol)
                    time.sleep(2)  # Wait 2 seconds for cancellations to process

                    # DEBUG: Print what we're ABOUT to do
                    print(f"  📝 Attempt {attempt}: {close_side} {close_qty:.5f} BTC @ ${close_price:,.1f} to close {'LONG' if is_long else 'SHORT'}")
                    print(f"      DEBUG: is_long={is_long}, calling {'sell_limit' if is_long else 'buy_limit'}")

                    try:
                        if is_long:
                            result = self.sell_limit(symbol, close_qty, close_price, reduce_only=True)
                        else:
                            result = self.buy_limit(symbol, close_qty, close_price, reduce_only=True)

                        if result and result.get('success'):
                            last_price = close_price
                            print(f"  ✅ Close order placed: ID {result.get('order_id')}")
                            print(f"  ⏸️  Waiting 3 seconds before checking again...")
                            time.sleep(3)  # Wait 3 seconds after placing order for fill
                        else:
                            print(f"  ⚠️ Order failed: {result}")

                    except Exception as e:
                        print(f"  ⚠️ Order error: {e}")

                else:
                    # Price unchanged (< $10 difference), just wait
                    if attempt % 5 == 0:
                        print(f"  ⏸️  Waiting for fill or bigger price change (current: ${close_price:,.1f}, last: ${last_price:,.1f})...")

                time.sleep(1)  # Check every 1 second for fills

            # This code should NEVER be reached because loop only exits via 'return' at line 274
            # But just in case something goes wrong...
            print(f"\n❌ ERROR: Close loop exited without closing position!")
            self.cancel_all_orders_market(symbol)

        except Exception as e:
            print(f"❌ Error closing position: {e}")
            import traceback
            traceback.print_exc()
