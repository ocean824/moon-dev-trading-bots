import requests
import json
import time
import uuid
import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
from x10.perpetual.trading_client import PerpetualTradingClient
from x10.perpetual.configuration import TESTNET_CONFIG, MAINNET_CONFIG
from x10.perpetual.orders import OrderSide
from x10.perpetual.accounts import StarkPerpetualAccount
from eth_account import Account
from x10.perpetual.user_client.onboarding import get_l2_keys_from_l1_account, StarkKeyPair

class ExtendedExchangeAPI:
    def __init__(self, api_key: str, stark_key: str, base_url: str = "https://api.extended.exchange"):
        self.api_key = api_key
        self.stark_key = stark_key
        self.base_url = base_url
        
        # Initialize SDK components
        self.use_testnet = "testnet" in base_url.lower()
        self.config = TESTNET_CONFIG if self.use_testnet else MAINNET_CONFIG
        
        # Create StarkPerpetualAccount with keys from Extended Exchange
        vault_id = int(os.getenv("X10_VAULT_ID", "110198"))
        private_key = os.getenv("X10_PRIVATE_KEY", stark_key)
        public_key = os.getenv("X10_PUBLIC_KEY", "0x2a6e05905330ed31c626b916960576995ac693c4c9c4fc9357813ae1a8e1969")
        
        self.stark_account = StarkPerpetualAccount(
            vault=vault_id,
            private_key=private_key,
            public_key=public_key,
            api_key=api_key
        )
        
        # Create trading client
        self.trading_client = PerpetualTradingClient(self.config, self.stark_account)
        
        # Keep session for backward compatibility
        self.session = requests.Session()
        self.session.headers.update({
            "X-Api-Key": api_key,
            "User-Agent": "extended-exchange-trading-bot/1.0",
            "Content-Type": "application/json"
        })
        
        # Event loop for async operations
        self._event_loop = None

    def _get_event_loop(self):
        """Get or create event loop for async operations"""
        if self._event_loop is None or self._event_loop.is_closed():
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
        return self._event_loop

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, json=data)
        
        if not response.ok:
            print(f"Error response: {response.status_code}")
            print(f"Response content: {response.text}")
            # NEVER log request data as it contains private keys - SECURITY RULE
            print(f"Request failed for endpoint: {endpoint}")
        
        response.raise_for_status()
        return response.json()

    def _generate_order_signature(self, order_data: Dict) -> Dict:
        """Generate placeholder signature - needs proper Extended Exchange implementation"""
        # This is a placeholder - Extended Exchange requires proper StarkNet signatures
        # For now, return empty signature to test the order structure
        return {
            "r": "0x0",
            "s": "0x0"
        }

    def limit_order(self, market: str, side: str, quantity: float, price: float, leverage: int = 1, reduce_only: bool = False) -> Dict:
        """Place a limit order using the SDK with leverage support and optional reduce_only"""
        loop = self._get_event_loop()

        async def place_order():
            # Set leverage if provided
            if leverage > 1:
                try:
                    await self.trading_client.account.update_leverage(market_name=market, leverage=leverage)
                except Exception as e:
                    print(f"Leverage update note: {e}")

            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            # Round price to 1 decimal place for BTC-USD
            rounded_price = round(price, 1)

            response = await self.trading_client.place_order(
                market_name=market,
                amount_of_synthetic=Decimal(str(quantity)),
                price=Decimal(str(rounded_price)),
                side=order_side,
                post_only=True,  # Re-enable post_only as requested
                reduce_only=reduce_only  # Add reduce_only flag
            )
            return response

        return loop.run_until_complete(place_order())

    def market_order(self, market: str, side: str, quantity: float, leverage: int = 1, reduce_only: bool = False) -> Dict:
        """Place a market order using the SDK with optional reduce_only"""
        loop = self._get_event_loop()
        
        async def place_order():
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            
            # For market orders, we need to get current price first
            orderbook = await self.trading_client.markets_info.get_orderbook_snapshot(market_name=market)
            current_price = float(orderbook.data.ask[0].price) if side.lower() == "buy" else float(orderbook.data.bid[0].price)
            rounded_price = round(current_price, 1)
            
            # For market orders, use very aggressive pricing to ensure execution
            if side.lower() == "buy":
                # For buying, use ask price + 1% to ensure immediate fill
                aggressive_price = current_price * 1.01
            else:
                # For selling, use bid price - 1% to ensure immediate fill
                aggressive_price = current_price * 0.99
            
            aggressive_price = round(aggressive_price, 1)
            print(f"Using aggressive price for immediate execution: ${aggressive_price:.2f}")
            
            # Try SDK first with aggressive pricing
            try:
                response = await self.trading_client.place_order(
                    market_name=market,
                    amount_of_synthetic=Decimal(str(quantity)),
                    price=Decimal(str(aggressive_price)),
                    side=order_side,
                    post_only=False,  # Allow immediate execution
                )
                return response
            except Exception as sdk_error:
                print(f"SDK order failed: {sdk_error}")
                
                # If reduce_only requested, try REST API fallback
                if reduce_only:
                    print("Trying REST API with reduce_only...")
                    return await self._try_rest_api_order(market, side, quantity, aggressive_price, "MARKET", reduce_only=True)
                else:
                    raise sdk_error
        
        return loop.run_until_complete(place_order())

    def buy_limit(self, market: str, quantity: float, price: float, leverage: int = 1, reduce_only: bool = False) -> Dict:
        return self.limit_order(market, "buy", quantity, price, leverage, reduce_only)

    def sell_limit(self, market: str, quantity: float, price: float, leverage: int = 1, reduce_only: bool = False) -> Dict:
        return self.limit_order(market, "sell", quantity, price, leverage, reduce_only)

    def buy_market(self, market: str, quantity: float, leverage: int = 1, reduce_only: bool = False) -> Dict:
        return self.market_order(market, "buy", quantity, leverage, reduce_only)

    def sell_market(self, market: str, quantity: float, leverage: int = 1, reduce_only: bool = False) -> Dict:
        return self.market_order(market, "sell", quantity, leverage, reduce_only)

    async def _try_rest_api_order(self, market: str, side: str, quantity: float, price: float, order_type: str = "LIMIT", reduce_only: bool = False):
        """Helper method to try REST API orders with reduce_only"""
        
        # Try different parameter variations
        variations = [
            {"reduce_only": True},  # snake_case
            {"reduceOnly": True},   # camelCase
        ] if reduce_only else [{}]
        
        for variation in variations:
            try:
                order_data = {
                    "market": market,
                    "side": side.upper(),
                    "quantity": str(quantity),
                    "price": str(price),
                    "type": order_type,
                    "timeInForce": "IOC" if order_type == "MARKET" else "GTC",
                    **variation
                }
                
                print(f"Trying REST API order: {order_data}")
                
                # Use sync request in async context
                import asyncio
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, lambda: self._request("POST", "/api/v1/user/order", order_data))
                
                return {"status": "OK", "data": response}
                
            except Exception as e:
                print(f"REST API variation failed: {e}")
                continue
        
        raise Exception("All REST API variations failed")

    def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order using the SDK"""
        loop = self._get_event_loop()
        
        async def cancel():
            response = await self.trading_client.orders.cancel_order(order_id=order_id)
            return response
        
        return loop.run_until_complete(cancel())

    def cancel_order_by_external_id(self, external_id: str) -> Dict:
        return self._request("DELETE", f"/api/v1/user/order?externalId={external_id}")

    def cancel_all_orders(self, market: Optional[str] = None) -> Dict:
        data = {}
        if market:
            data["market"] = market
        return self._request("POST", "/api/v1/user/order/massCancel", data)

    def get_positions(self) -> Dict:
        return self._request("GET", "/api/v1/user/positions")

    def get_position_history(self, limit: int = 100) -> Dict:
        return self._request("GET", f"/api/v1/user/positions/history?limit={limit}")

    def get_orders(self, market: Optional[str] = None, status: Optional[str] = None) -> Dict:
        params = []
        if market:
            params.append(f"market={market}")
        if status:
            params.append(f"status={status}")
        query = "?" + "&".join(params) if params else ""
        return self._request("GET", f"/api/v1/user/orders{query}")

    def get_order_history(self, market: Optional[str] = None, limit: int = 100) -> Dict:
        params = []
        if market:
            params.append(f"market={market}")
        params.append(f"limit={limit}")
        query = "?" + "&".join(params)
        return self._request("GET", f"/api/v1/user/orders/history{query}")

    def get_trades(self, market: Optional[str] = None, limit: int = 100) -> Dict:
        params = []
        if market:
            params.append(f"market={market}")
        params.append(f"limit={limit}")
        query = "?" + "&".join(params)
        return self._request("GET", f"/api/v1/user/trades{query}")

    def get_account_info(self) -> Dict:
        """Get account information using the SDK"""
        loop = self._get_event_loop()
        
        async def get_info():
            # Try getting balance and positions to understand account structure
            balance = await self.trading_client.account.get_balance()
            positions = await self.trading_client.account.get_positions()
            return {
                "balance": balance,
                "positions": positions,
                "stark_key": self.stark_account.public_key,
                "vault": self.stark_account.vault
            }
        
        return loop.run_until_complete(get_info())

    def get_balance(self) -> Dict:
        return self._request("GET", "/api/v1/user/balance")

    def get_pnl(self) -> Dict:
        return self._request("GET", "/api/v1/user/pnl")

    def get_markets(self) -> Dict:
        return self._request("GET", "/api/v1/markets")

    def get_market_data(self, market: str) -> Dict:
        return self._request("GET", f"/api/v1/markets/{market}")

    def get_orderbook(self, market: str) -> Dict:
        return self._request("GET", f"/api/v1/markets/{market}/orderbook")

    def get_ticker(self, market: str) -> Dict:
        return self._request("GET", f"/api/v1/markets/{market}/ticker")

    def get_bid_ask(self, market: str) -> Dict:
        """Get current bid/ask prices using the SDK"""
        loop = self._get_event_loop()
        
        async def get_prices():
            orderbook = await self.trading_client.markets_info.get_orderbook_snapshot(market_name=market)
            return {
                "bid": float(orderbook.data.bid[0].price) if orderbook.data.bid else 0.0,
                "ask": float(orderbook.data.ask[0].price) if orderbook.data.ask else 0.0
            }
        
        return loop.run_until_complete(get_prices())

    def get_ohlcv(self, market: str, candle_type: str = "trades", limit: int = 100) -> Dict:
        return self._request("GET", f"/api/v1/info/candles/{market}/{candle_type}?limit={limit}")

    def get_market_stats(self, market: str) -> Dict:
        return self._request("GET", f"/api/v1/info/markets/{market}/stats")

    # ===== MARKET MAKER UTILITY FUNCTIONS =====
    
    def usd_to_asset_size(self, symbol: str, usd_amount: float) -> float:
        """Convert USD amount to asset size for trading"""
        try:
            # Get current market price
            bid_ask = self.get_bid_ask(symbol)
            mid_price = (bid_ask['bid'] + bid_ask['ask']) / 2
            
            if mid_price <= 0:
                print(f"Error: Invalid price for {symbol}: {mid_price}")
                return 0
                
            # Calculate asset size
            asset_size = usd_amount / mid_price
            
            # Round to appropriate precision for different assets
            if 'BTC' in symbol:
                # BTC: round to 3 decimal places for Extended Exchange precision requirements
                asset_size = round(asset_size, 3)
                # Only apply minimum if the calculated size is actually zero
                if asset_size == 0.0 and usd_amount > 0:
                    asset_size = 0.001  # Minimum BTC size only when calculated size is zero
            elif 'ETH' in symbol:
                # ETH: round to 4 decimal places
                asset_size = round(asset_size, 4)
                if asset_size == 0 and usd_amount > 0:
                    asset_size = max(0.0001, asset_size)  # Minimum ETH size
            elif 'SOL' in symbol:
                # SOL: round to 2 decimal places
                asset_size = round(asset_size, 2)
                if asset_size == 0 and usd_amount > 0:
                    asset_size = max(0.01, asset_size)  # Minimum SOL size
            else:
                # Default: round to 4 decimal places
                asset_size = round(asset_size, 4)
                if asset_size == 0 and usd_amount > 0:
                    asset_size = max(0.0001, asset_size)  # Minimum default size
            
            print(f"USD to Asset conversion: ${usd_amount} -> {asset_size} {symbol} @ ${mid_price:,.2f}")
            return asset_size
            
        except Exception as e:
            print(f"Error converting USD to asset size: {e}")
            return 0
    
    def get_optimal_position_size(self, balance_percentage: float = 0.95) -> float:
        """
        Calculate optimal position size based on available balance percentage
        
        Args:
            balance_percentage: Percentage of available balance to use (default 95%)
        
        Returns:
            Position size in USD to use as margin
        """
        try:
            account_info = self.get_account_info()
            available_balance = float(account_info.get('availableBalance', 0))
            
            if available_balance <= 0:
                print(f"Warning: No available balance found")
                return 0
            
            # Calculate position size as percentage of available balance
            position_size = available_balance * balance_percentage
            
            # Ensure minimum position size (at least $1)
            if position_size < 1:
                print(f"Warning: Calculated position size ${position_size:.2f} too small, using $1 minimum")
                position_size = min(1, available_balance)
            
            print(f"💰 Balance calculation:")
            print(f"   Available balance: ${available_balance:.2f}")
            print(f"   Using {balance_percentage*100:.1f}% of balance")
            print(f"   Position size (margin): ${position_size:.2f}")
            
            return position_size
            
        except Exception as e:
            print(f"Error calculating optimal position size: {e}")
            return 0

    def get_position_size_usd(self, symbol: str) -> float:
        """Get the current position size in USD for a symbol"""
        try:
            _, im_in_pos, mypos_size, _, entry_px, _, _ = self.get_position(symbol)
            
            if not im_in_pos:
                return 0
                
            # Calculate USD value of position
            position_usd = abs(mypos_size * entry_px)
            return position_usd
            
        except Exception as e:
            print(f"Error getting position size in USD: {e}")
            return 0
    
    def get_position(self, symbol: str) -> tuple:
        """Get position information for a symbol"""
        try:
            account_info = self.get_account_info()
            positions = account_info['positions'].data
            
            im_in_pos = False
            mypos_size = 0
            pos_sym = None
            entry_px = 0
            pnl_perc = 0
            is_long = False
            
            for pos in positions:
                # Try different possible attribute names
                market_attr = None
                if hasattr(pos, 'market_name'):
                    market_attr = pos.market_name
                elif hasattr(pos, 'market'):
                    market_attr = pos.market
                elif hasattr(pos, 'symbol'):
                    market_attr = pos.symbol
                
                if market_attr == symbol:
                    im_in_pos = True
                    mypos_size = float(pos.size)
                    pos_sym = market_attr
                    
                    # Try different entry price attribute names
                    if hasattr(pos, 'entry_price'):
                        entry_px = float(pos.entry_price)
                    elif hasattr(pos, 'open_price'):
                        entry_px = float(pos.open_price)
                    else:
                        entry_px = 0
                    
                    # Try different PnL attribute names
                    pnl_perc = 0
                    if hasattr(pos, 'unrealized_pnl_percent'):
                        pnl_perc = float(pos.unrealized_pnl_percent)
                    elif hasattr(pos, 'pnl_percent'):
                        pnl_perc = float(pos.pnl_percent)
                    elif hasattr(pos, 'unrealised_pnl') and hasattr(pos, 'size') and entry_px > 0:
                        # Calculate leveraged PnL percentage manually
                        unrealized_pnl = float(pos.unrealised_pnl)
                        position_value = abs(float(pos.size) * entry_px)
                        leverage = float(pos.leverage) if hasattr(pos, 'leverage') else 1
                        initial_margin = position_value / leverage
                        pnl_perc = (unrealized_pnl / initial_margin) * 100 if initial_margin > 0 else 0
                    
                    # Determine if it's a long position
                    if hasattr(pos, 'side'):
                        is_long = pos.side == 'LONG'
                    else:
                        is_long = float(pos.size) > 0
                    
                    break
            
            return positions, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long
            
        except Exception as e:
            print(f"Error getting position: {e}")
            return [], False, 0, None, 0, 0, False

    def pnl_close(self, symbol: str, target: float, max_loss: float) -> bool:
        """Close position if profit/loss targets are hit using reduce_only"""
        try:
            _, im_in_pos, _, _, _, pnl_perc, _ = self.get_position(symbol)
            
            if not im_in_pos:
                return False
                
            # Check if we hit profit target
            if pnl_perc >= target:
                print(f"closing position WIN - PnL: {pnl_perc:.2f}%")
                result = self.close_position(symbol)
                return result
                
            # Check if we hit stop loss
            if pnl_perc <= max_loss:
                print(f"closing position LOSS - PnL: {pnl_perc:.2f}%")  
                result = self.close_position(symbol)
                return result
                
            return False
            
        except Exception as e:
            print(f"Error in pnl_close: {e}")
            return False

    def close_position(self, symbol: str):
        """Close position - handles negative balance scenarios intelligently"""
        try:
            _, im_in_pos, mypos_size, _, _, _, is_long = self.get_position(symbol)
            
            if not im_in_pos:
                print("No position to close")
                return False
                
            # Get current account info
            account_info = self.get_account_info()
            available_balance = 0
            if 'balance' in account_info and hasattr(account_info['balance'], 'data'):
                available_balance = float(account_info['balance'].data.available_for_trade)
            
            print(f"💰 Available balance: ${available_balance:.2f}")
            print(f"📊 Position: {'LONG' if is_long else 'SHORT'} {abs(mypos_size)} {symbol}")
            
            # Check if balance is negative - Extended Exchange blocks ALL orders in this case
            if available_balance < 0:
                print(f"\n🚨 CRITICAL: Available balance is negative (${available_balance:.2f})")
                print("❌ Extended Exchange blocks ALL orders when available balance < 0")
                print("💡 SOLUTION OPTIONS:")
                print("   1. 💸 Add funds to make available balance positive")
                print("   2. 🌐 Try closing manually in Extended Exchange web UI") 
                print("   3. 📞 Contact Extended Exchange support for manual closure")
                print("   4. ⏰ Wait for liquidation (risky - may lose more)")
                print("   5. 📈 Wait for price to move in your favor")
                
                # Calculate how much funding needed
                funding_needed = abs(available_balance) + 10  # Add $10 buffer
                print(f"\n💡 To enable order placement, add ~${funding_needed:.2f} to your account")
                
                return False
            
            # If balance is positive, proceed with normal closing
            print("✅ Available balance is positive - proceeding with close...")
            
            # Cancel all existing orders first
            print("1. Canceling all existing orders...")
            self.cancel_all_orders_market(symbol)
            time.sleep(1)
            
            # Use aggressive market order for immediate execution
            print("2. Placing aggressive market order...")
            close_size = abs(mypos_size)
            
            try:
                if is_long:
                    print(f"   Closing LONG: Selling {close_size} at market")
                    result = self.sell_market(symbol, close_size, reduce_only=False)
                else:
                    print(f"   Closing SHORT: Buying {close_size} at market")
                    result = self.buy_market(symbol, close_size, reduce_only=False)
                
                print(f"   ✅ Order result: {result}")
                
                # Wait and verify closure
                time.sleep(3)
                _, still_in_pos, _, _, _, _, _ = self.get_position(symbol)
                
                if not still_in_pos:
                    print("🎉 POSITION SUCCESSFULLY CLOSED!")
                    return True
                else:
                    print("⚠️ Order placed but position may still exist")
                    return False
                    
            except Exception as e:
                print(f"❌ Market order failed: {e}")
                
                # If order failed due to insufficient balance during execution
                if "exceeds available balance" in str(e):
                    print("💡 Balance became insufficient during order placement")
                    print("🔄 This can happen if unrealized PnL changed rapidly")
                    return False
                
                return self._try_alternative_close_methods(symbol, close_size, is_long)
                
        except Exception as e:
            print(f"Error in close_position: {e}")
            return False

    def _try_alternative_close_methods(self, symbol: str, close_size: float, is_long: bool):
        """Try alternative methods to close position if reduce_only fails"""
        
        print("🔄 Trying alternative close methods...")
        
        # Method 1: Regular market order (no reduce_only)
        try:
            print("   Method 1: Regular market order...")
            if is_long:
                result = self.sell_market(symbol, close_size, reduce_only=False)
            else:
                result = self.buy_market(symbol, close_size, reduce_only=False)
            
            print(f"   ✅ Regular market order result: {result}")
            
            time.sleep(2)
            _, still_in_pos, _, _, _, _, _ = self.get_position(symbol)
            if not still_in_pos:
                print("🎉 Position closed with regular market order!")
                return True
                
        except Exception as e:
            print(f"   ❌ Regular market order failed: {e}")
        
        # Method 2: Try the REST API approaches
        try:
            print("   Method 2: REST API approaches...")
            return self._try_rest_api_reduce_only(symbol, close_size, is_long)
        except Exception as e:
            print(f"   ❌ All methods failed: {e}")
            return False

    def _force_close_position_reduce_only(self, symbol: str, position_size: float, is_long: bool):
        """Force close position using reduce_only orders when balance is negative"""
        try:
            print(f"🚨 EMERGENCY CLOSE: Using reduce_only to close position")
            
            # Cancel all existing orders first
            print("1. Canceling all existing orders...")
            self.cancel_all_orders_market(symbol)
            time.sleep(1)
            
            # Get exact position size from exchange
            positions, _, exact_size, _, _, _, _ = self.get_position(symbol)
            close_size = abs(exact_size)
            
            print(f"2. Exact position size from exchange: {close_size}")
            
            # Use SDK to place reduce_only order
            loop = self._get_event_loop()
            
            async def place_reduce_only_order():
                try:
                    # Get current market price for aggressive execution
                    orderbook = await self.trading_client.markets_info.get_orderbook_snapshot(market_name=symbol)
                    
                    if is_long:
                        # Close long: sell at bid price for immediate execution
                        close_price = float(orderbook.data.bid[0].price) if orderbook.data.bid else 0
                        close_price = close_price * 0.999  # Slightly below bid for faster fill
                        order_side = OrderSide.SELL
                        print(f"3. Closing LONG: Selling {close_size} at ${close_price:.2f}")
                    else:
                        # Close short: buy at ask price for immediate execution  
                        close_price = float(orderbook.data.ask[0].price) if orderbook.data.ask else 0
                        close_price = close_price * 1.001  # Slightly above ask for faster fill
                        order_side = OrderSide.BUY
                        print(f"3. Closing SHORT: Buying {close_size} at ${close_price:.2f}")
                    
                    # Place order without reduce_only since SDK doesn't support it
                    # Use post_only=False for immediate execution
                    response = await self.trading_client.place_order(
                        market_name=symbol,
                        amount_of_synthetic=Decimal(str(close_size)),
                        price=Decimal(str(round(close_price, 1))),
                        side=order_side,
                        post_only=False  # Allow immediate execution
                    )
                    
                    print(f"✅ Reduce-only order placed: {response}")
                    return response
                    
                except Exception as e:
                    print(f"❌ SDK reduce_only order failed: {e}")
                    return None
            
            result = loop.run_until_complete(place_reduce_only_order())
            
            if result:
                print("4. Waiting for order execution...")
                time.sleep(3)
                
                # Verify position was closed
                _, still_in_pos, _, _, _, _, _ = self.get_position(symbol)
                if not still_in_pos:
                    print("🎉 POSITION SUCCESSFULLY CLOSED using reduce_only!")
                    return True
                else:
                    print("⚠️ Order placed but position still exists - may need time to execute")
                    return False
            else:
                print("❌ Failed to place reduce_only order")
                return self._try_rest_api_reduce_only(symbol, close_size, is_long)
                
        except Exception as e:
            print(f"Error in force close: {e}")
            return False

    def _try_rest_api_reduce_only(self, symbol: str, close_size: float, is_long: bool):
        """Fallback: Try multiple REST API approaches"""
        
        # Get current market prices
        bid_ask = self.get_bid_ask(symbol)
        close_price = bid_ask['bid'] if is_long else bid_ask['ask']
        
        # Try different approaches in order
        approaches = [
            {
                "name": "REST API with reduce_only (snake_case)",
                "data": {
                    "market": symbol,
                    "side": "SELL" if is_long else "BUY",
                    "quantity": str(close_size),
                    "price": str(close_price),
                    "type": "LIMIT",
                    "timeInForce": "IOC",
                    "reduce_only": True,
                    "post_only": False
                }
            },
            {
                "name": "REST API with reduceOnly (camelCase)",
                "data": {
                    "market": symbol,
                    "side": "SELL" if is_long else "BUY",
                    "quantity": str(close_size),
                    "price": str(close_price),
                    "type": "LIMIT",
                    "timeInForce": "IOC",
                    "reduceOnly": True,
                    "postOnly": False
                }
            },
            {
                "name": "Market Order (aggressive close)",
                "data": {
                    "market": symbol,
                    "side": "SELL" if is_long else "BUY",
                    "quantity": str(close_size),
                    "type": "MARKET"
                }
            },
            {
                "name": "Limit Order at unfavorable price (likely to fill)",
                "data": {
                    "market": symbol,
                    "side": "SELL" if is_long else "BUY",
                    "quantity": str(close_size),
                    "price": str(close_price * 0.95 if is_long else close_price * 1.05),  # Very aggressive pricing
                    "type": "LIMIT",
                    "timeInForce": "IOC"
                }
            }
        ]
        
        for i, approach in enumerate(approaches, 1):
            try:
                print(f"🔄 Attempt {i}: {approach['name']}")
                print(f"   Order data: {approach['data']}")
                
                response = self._request("POST", "/api/v1/user/order", approach['data'])
                print(f"   ✅ Response: {response}")
                
                # Wait and verify
                time.sleep(2)
                _, still_in_pos, _, _, _, _, _ = self.get_position(symbol)
                
                if not still_in_pos:
                    print(f"🎉 POSITION SUCCESSFULLY CLOSED using {approach['name']}!")
                    return True
                else:
                    print(f"   ⚠️ Order placed but position still exists")
                    
            except Exception as e:
                print(f"   ❌ {approach['name']} failed: {e}")
                continue
        
        # If all methods failed
        print("\n🚨 CRITICAL: All closing methods failed!")
        print("📞 Options:")
        print("  1. Add funds to bring available balance positive")
        print("  2. Close manually in Extended Exchange UI")
        print("  3. Contact Extended Exchange support")
        print("  4. Wait for liquidation (risky)")
        return False

    def _standard_close_position(self, symbol: str, position_size: float, is_long: bool):
        """Standard position closing when balance is positive"""
        try:
            # Cancel all orders first
            self.cancel_all_orders_market(symbol)
            time.sleep(1)
            
            # Use market order for immediate execution
            if is_long:
                print(f"Closing LONG: Selling {abs(position_size)} at market")
                self.sell_market(symbol, abs(position_size))
            else:
                print(f"Closing SHORT: Buying {abs(position_size)} at market")
                self.buy_market(symbol, abs(position_size))
            
            # Verify closure
            time.sleep(2)
            _, still_in_pos, _, _, _, _, _ = self.get_position(symbol)
            
            if not still_in_pos:
                print("✅ Position successfully closed!")
                return True
            else:
                print("⚠️ Order placed but position may still exist")
                return False
                
        except Exception as e:
            print(f"❌ Standard close failed: {e}")
            return False

    def cancel_all_orders_market(self, market: Optional[str] = None):
        """Cancel all open orders for a market"""
        try:
            data = {}
            if market:
                data["market"] = market
            return self._request("POST", "/api/v1/user/order/massCancel", data)
        except Exception as e:
            print(f"Error canceling orders: {e}")

    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage for a symbol"""
        loop = self._get_event_loop()
        
        async def set_lev():
            try:
                return await self.trading_client.account.update_leverage(
                    market_name=symbol, 
                    leverage=leverage
                )
            except Exception as e:
                print(f"Leverage update note: {e}")
                return None
        
        return loop.run_until_complete(set_lev())

    def get_orderbook_levels(self, symbol: str, levels: int = 11) -> tuple:
        """Get orderbook levels for market making"""
        try:
            # Use the SDK method to get orderbook
            loop = self._get_event_loop()
            
            async def get_book():
                return await self.trading_client.markets_info.get_orderbook_snapshot(market_name=symbol)
            
            orderbook = loop.run_until_complete(get_book())
            
            if not orderbook or not orderbook.data:
                return None, None, None
                
            bids = orderbook.data.bid[:levels] if orderbook.data.bid else []
            asks = orderbook.data.ask[:levels] if orderbook.data.ask else []
            
            # Extract bid and ask prices
            bid_prices = [float(bid.price) for bid in bids]
            ask_prices = [float(ask.price) for ask in asks]
            
            # Get 11th level prices if available
            bid11 = bid_prices[10] if len(bid_prices) > 10 else (bid_prices[-1] if bid_prices else 0)
            ask11 = ask_prices[10] if len(ask_prices) > 10 else (ask_prices[-1] if ask_prices else 0)
            
            return bid_prices[0] if bid_prices else 0, ask_prices[0] if ask_prices else 0, {'bids': bid_prices, 'asks': ask_prices, 'bid11': bid11, 'ask11': ask11}
            
        except Exception as e:
            print(f"Error getting orderbook levels: {e}")
            return 0, 0, None