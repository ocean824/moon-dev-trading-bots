"""
Nice Functions for Pacifica Exchange
Provides a clean interface for trading on Pacifica
"""

import os
import sys
import time
import json
import base58
import uuid
import requests
from typing import Optional, Tuple, List, Dict, Any
from dotenv import load_dotenv
from solders.keypair import Keypair
from termcolor import colored
import logging

# Load environment variables
load_dotenv()

# Add Pacifica SDK path if available
sys.path.insert(0, '/tmp/pacifica-sdk')

# Try to import sign_message utility
try:
    from common.utils import sign_message
except:
    # Define locally if not available
    def sort_json(obj):
        if isinstance(obj, dict):
            return {k: sort_json(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [sort_json(item) for item in obj]
        else:
            return obj

    def sign_message(signature_header: dict, signature_payload: dict, keypair: Keypair) -> tuple:
        # According to Pacifica docs, combine header and data into a single object
        # The structure should be: {timestamp, expiry_window, type, data: {...}}
        message_obj = {
            **signature_header,  # This includes timestamp, expiry_window, type
            "data": signature_payload  # Wrap the payload in "data"
        }
        sorted_json_obj = sort_json(message_obj)
        compact_json = json.dumps(sorted_json_obj, separators=(",", ":"))
        message_bytes = compact_json.encode("utf-8")
        signature = keypair.sign_message(message_bytes)
        signature_base58 = base58.b58encode(bytes(signature)).decode("utf-8")
        return compact_json, signature_base58


class PacificaAPI:
    """Pacifica Exchange API wrapper"""

    def __init__(self):
        """Initialize Pacifica API with credentials from environment"""
        self.logger = logging.getLogger(__name__)

        # Get credentials
        private_key = os.getenv("PACIFICA_PRIVATE_KEY")
        self.api_key = os.getenv("PACIFICA_API_KEY")
        use_testnet = os.getenv("PACIFICA_USE_TESTNET", "false").lower() == "true"

        if not private_key:
            raise ValueError("PACIFICA_PRIVATE_KEY must be set in .env file")

        # Initialize keypair
        try:
            self.keypair = Keypair.from_base58_string(private_key)
            self.public_key = str(self.keypair.pubkey())
        except Exception as e:
            raise ValueError(f"Failed to initialize keypair: {e}")

        # Set base URL
        if use_testnet:
            self.base_url = "https://test-api.pacifica.fi"
        else:
            self.base_url = "https://api.pacifica.fi"

        print(f"🌊 Pacifica API initialized successfully")

    def _make_request(self, method: str, endpoint: str, params: dict = None, json_data: dict = None, signed: bool = False) -> Optional[dict]:
        """Make HTTP request to Pacifica API"""
        url = f"{self.base_url}{endpoint}"
        headers = {"Accept": "*/*", "Content-Type": "application/json"}

        if signed:
            # Add signature for authenticated endpoints
            timestamp = int(time.time() * 1000)

            # Create signature header and payload exactly as SDK does
            endpoint_type = endpoint.split('/')[-1]
            if "/orders/create" in endpoint:
                endpoint_type = "create_order"
            elif "/orders/cancel_all" in endpoint:
                endpoint_type = "cancel_all_orders"
            elif "/orders/cancel" in endpoint:
                endpoint_type = "cancel_order"

            signature_header = {
                "timestamp": timestamp,
                "expiry_window": 5000,
                "type": endpoint_type
            }

            # IMPORTANT: For Pacifica, we sign ONLY the order data
            # The account, timestamp, expiry_window go in the request but not in the signature payload
            signature_payload = json_data or {}

            message, signature = sign_message(signature_header, signature_payload, self.keypair)

            # Build final request with all fields
            request_data = {
                "account": self.public_key,
                "timestamp": timestamp,
                "expiry_window": 5000,
                **(json_data or {}),
                "signature": signature
            }

            # Debug output (uncomment to debug signature issues)
            # print(f"🔍 DEBUG Signature:")
            # print(f"  Endpoint: {endpoint}")
            # print(f"  Type: {endpoint_type}")
            # print(f"  Timestamp: {timestamp}")
            # print(f"  Order data: {json_data}")
            # print(f"  Request data keys: {list(request_data.keys())}")

            if method == "POST":
                response = requests.post(url, json=request_data, headers=headers, timeout=10)
            else:
                response = requests.get(url, params=params, headers=headers, timeout=10)
        else:
            if method == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                response = requests.post(url, json=json_data, headers=headers, timeout=10)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            # Rate limit hit - handle with extended wait
            print(colored(f"⏳ Rate limit hit (429) - waiting 15 seconds before retry...", 'yellow'))
            time.sleep(15)  # Wait 15 seconds on first rate limit

            # Keep retrying until successful
            retry_count = 0
            while True:
                retry_count += 1
                print(colored(f"  🔄 Retry attempt {retry_count} after rate limit...", 'yellow'))
                try:
                    if method == "POST":
                        if signed:
                            # Re-sign for retry
                            timestamp = int(time.time() * 1000)
                            signature_header = {
                                "timestamp": timestamp,
                                "expiry_window": 5000,
                                "type": endpoint_type
                            }
                            signature_payload = json_data or {}
                            message, signature = sign_message(signature_header, signature_payload, self.keypair)

                            request_data = {
                                "account": self.public_key,
                                "timestamp": timestamp,
                                "expiry_window": 5000,
                                **(json_data or {}),
                                "signature": signature
                            }
                            response = requests.post(url, json=request_data, headers=headers, timeout=10)
                        else:
                            response = requests.post(url, json=json_data, headers=headers, timeout=10)
                    else:
                        response = requests.get(url, params=params, headers=headers, timeout=10)

                    if response.status_code == 200:
                        print(colored(f"✅ Retry {retry_count} successful after rate limit", 'green'))
                        return response.json()
                    elif response.status_code == 429:
                        # Still rate limited - wait and continue
                        print(colored(f"  ⏳ Still rate limited - waiting 5s before retry {retry_count + 1}...", 'yellow'))
                        time.sleep(5)
                        continue
                    elif response.status_code >= 500:
                        # Server error - wait and retry
                        print(colored(f"  ⚠️ Server error {response.status_code} - waiting 3s before retry {retry_count + 1}...", 'yellow'))
                        time.sleep(3)
                        continue
                    else:
                        # Client error - still return rate limit flag since we're in retry loop
                        error_msg = f"API request failed after {retry_count} retries: {response.status_code} - {response.text}"
                        print(f"❌ {error_msg}")
                        self.logger.error(error_msg)
                        return {"rate_limit_error": True, "status_code": response.status_code}
                except Exception as e:
                    print(colored(f"  ⚠️ Retry {retry_count} exception: {e} - waiting 3s...", 'yellow'))
                    time.sleep(3)
                    continue
        elif response.status_code >= 500:
            # Server error on initial request - treat like rate limit
            print(colored(f"⚠️ Server error {response.status_code} - waiting 5s before retry...", 'yellow'))
            time.sleep(5)

            # Keep retrying until successful
            retry_count = 0
            while True:
                retry_count += 1
                print(colored(f"  🔄 Retry attempt {retry_count} after server error...", 'yellow'))
                try:
                    if method == "POST":
                        if signed:
                            # Re-sign for retry
                            timestamp = int(time.time() * 1000)
                            signature_header = {
                                "timestamp": timestamp,
                                "expiry_window": 5000,
                                "type": endpoint_type
                            }
                            signature_payload = json_data or {}
                            message, signature = sign_message(signature_header, signature_payload, self.keypair)

                            request_data = {
                                "account": self.public_key,
                                "timestamp": timestamp,
                                "expiry_window": 5000,
                                **(json_data or {}),
                                "signature": signature
                            }
                            response = requests.post(url, json=request_data, headers=headers, timeout=10)
                        else:
                            response = requests.post(url, json=json_data, headers=headers, timeout=10)
                    else:
                        response = requests.get(url, params=params, headers=headers, timeout=10)

                    if response.status_code == 200:
                        print(colored(f"✅ Retry {retry_count} successful after server error", 'green'))
                        return response.json()
                    elif response.status_code == 429:
                        print(colored(f"  ⏳ Rate limit hit - waiting 15s...", 'yellow'))
                        time.sleep(15)
                        continue
                    elif response.status_code >= 500:
                        print(colored(f"  ⚠️ Still server error {response.status_code} - waiting 3s before retry {retry_count + 1}...", 'yellow'))
                        time.sleep(3)
                        continue
                    else:
                        # Client error after server error retries
                        error_msg = f"API request failed after {retry_count} server error retries: {response.status_code} - {response.text}"
                        print(f"❌ {error_msg}")
                        self.logger.error(error_msg)
                        # Return error flag so caller knows
                        return {"server_error": True, "status_code": response.status_code}
                except Exception as e:
                    print(colored(f"  ⚠️ Retry {retry_count} exception: {e} - waiting 3s...", 'yellow'))
                    time.sleep(3)
                    continue
        else:
            error_msg = f"API request failed: {response.status_code} - {response.text}"
            print(f"❌ {error_msg}")
            self.logger.error(error_msg)
            return None

    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        params = {"account": self.public_key}
        result = self._make_request("GET", "/api/v1/account", params=params)

        if result and "data" in result:
            return result["data"]
        return {}

    def get_balance(self) -> float:
        """Get account balance"""
        account_info = self.get_account_info()
        return float(account_info.get("balance", 0))

    def get_orderbook(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get orderbook for a symbol"""
        # Pacifica uses book endpoint with symbol parameter
        # Remove -USD suffix if present for Pacifica format
        clean_symbol = symbol.replace("-USD", "").replace("/", "")
        params = {"symbol": clean_symbol, "agg_level": "1"}
        result = self._make_request("GET", "/api/v1/book", params=params)
        return result

    def get_orderbook_levels(self, symbol: str, levels: int = 5) -> Tuple[Optional[List], Optional[List], Optional[Dict]]:
        """Get orderbook levels with bids and asks"""
        orderbook = self.get_orderbook(symbol)

        if not orderbook or "data" not in orderbook:
            return None, None, None

        data = orderbook["data"]

        # Pacifica format: {"s": "BTC", "l": [[bids], [asks]]}
        if "l" in data and isinstance(data["l"], list) and len(data["l"]) >= 2:
            raw_bids = data["l"][0][:levels]  # First array is bids
            raw_asks = data["l"][1][:levels]  # Second array is asks

            # Format: [{"p": price, "a": amount, "n": num_orders}, ...]
            formatted_bids = []
            for bid in raw_bids:
                if isinstance(bid, dict):
                    price = float(bid.get("p", 0))
                    amount = float(bid.get("a", 0))
                    formatted_bids.append([price, amount])

            formatted_asks = []
            for ask in raw_asks:
                if isinstance(ask, dict):
                    price = float(ask.get("p", 0))
                    amount = float(ask.get("a", 0))
                    formatted_asks.append([price, amount])

            summary = {
                "bids": formatted_bids,
                "asks": formatted_asks,
                "best_bid": formatted_bids[0][0] if formatted_bids else None,
                "best_ask": formatted_asks[0][0] if formatted_asks else None
            }

            return formatted_bids, formatted_asks, summary

        return None, None, None

    def get_bid_ask(self, symbol: str) -> Tuple[Optional[float], Optional[float]]:
        """Get best bid and ask prices"""
        bids, asks, _ = self.get_orderbook_levels(symbol, 1)

        if bids and asks:
            return bids[0][0], asks[0][0]

        # Fallback to prices endpoint
        clean_symbol = symbol.replace("-USD", "").replace("/", "")
        params = {"symbol": clean_symbol}
        prices = self._make_request("GET", "/api/v1/prices", params=params)
        if prices and "data" in prices:
            data = prices["data"]
            # Prices endpoint might return different format
            if isinstance(data, dict) and clean_symbol in data:
                price_info = data[clean_symbol]
                return float(price_info.get("bid", 0)), float(price_info.get("ask", 0))

        return None, None

    def place_limit_order(self, symbol: str, side: str, size: float, price: float, leverage: int = 2) -> Optional[str]:
        """Place a limit order"""
        # Clean symbol for Pacifica format
        clean_symbol = symbol.replace("-USD", "").replace("/", "")

        # Determine lot size based on symbol
        if "ETH" in symbol.upper():
            lot_size = 0.0001  # ETH lot size
            decimals = 4
        else:
            lot_size = 0.00001  # BTC lot size
            decimals = 5

        rounded_size = round(size / lot_size) * lot_size

        order_data = {
            "symbol": clean_symbol,
            "side": side.lower(),  # "bid" or "ask"
            "amount": f"{rounded_size:.{decimals}f}",  # Format with correct decimals
            "price": str(int(price)),  # Price must be integer (tick size = 1)
            "reduce_only": False,
            "tif": "GTC",  # Good Till Canceled
            "client_order_id": str(uuid.uuid4()),
        }

        # Note: Pacifica uses account-wide leverage, not per-order
        # Leverage must be set separately via account settings

        result = self._make_request("POST", "/api/v1/orders/create", json_data=order_data, signed=True)

        if result and "data" in result:
            order_id = result["data"].get("order_id")
            print(f"🌊 Pacifica {side} order placed: {size} {symbol} @ ${price:.2f}")
            return order_id

        return None

    def buy_limit(self, symbol: str, size: float, price: float, leverage: int = 1) -> Optional[str]:
        """Place a buy limit order"""
        return self.place_limit_order(symbol, "bid", size, price, leverage)

    def sell_limit(self, symbol: str, size: float, price: float, leverage: int = 1) -> Optional[str]:
        """Place a sell limit order"""
        return self.place_limit_order(symbol, "ask", size, price, leverage)

    def place_market_order(self, symbol: str, side: str, size: float, leverage: int = 1) -> Optional[str]:
        """Place a market order"""
        # Clean symbol for Pacifica format
        clean_symbol = symbol.replace("-USD", "").replace("/", "")

        # Market orders in Pacifica don't need price but use slippage
        order_data = {
            "symbol": clean_symbol,
            "side": side.lower(),  # "bid" or "ask"
            "amount": str(size),
            "slippage_percent": "0.5",  # 0.5% slippage tolerance
            "reduce_only": False,
            "client_order_id": str(uuid.uuid4()),
        }

        result = self._make_request("POST", "/api/v1/orders/create", json_data=order_data, signed=True)

        if result and "data" in result:
            order_id = result["data"].get("order_id")
            print(f"🌊 Pacifica market {side} order placed: {size} {symbol}")
            return order_id

        return None

    def buy_market(self, symbol: str, size: float, leverage: int = 1) -> Optional[str]:
        """Place a buy market order"""
        return self.place_market_order(symbol, "bid", size, leverage)

    def sell_market(self, symbol: str, size: float, leverage: int = 1) -> Optional[str]:
        """Place a sell market order"""
        return self.place_market_order(symbol, "ask", size, leverage)

    def cancel_order(self, order_id: str, symbol: str = None) -> bool:
        """Cancel an order"""
        if not symbol:
            print(f"⚠️ Symbol required for Pacifica order cancellation")
            return False

        # Clean symbol for Pacifica format
        clean_symbol = symbol.replace("-USD", "").replace("/", "")

        # Order ID should be numeric for Pacifica
        try:
            numeric_order_id = int(order_id)
        except ValueError:
            numeric_order_id = order_id  # Keep as is if not numeric

        order_data = {
            "symbol": clean_symbol,
            "order_id": numeric_order_id
        }

        result = self._make_request("POST", "/api/v1/orders/cancel", json_data=order_data, signed=True)

        if result and result.get("success"):
            print(f"🌊 Order {order_id} canceled")
            return True

        return False

    def cancel_all_orders_market(self, symbol: str = None) -> bool:
        """Cancel all orders for a market (or all markets if no symbol)"""
        if symbol:
            # Cancel for specific symbol
            clean_symbol = symbol.replace("-USD", "").replace("/", "")
            order_data = {
                "symbol": clean_symbol,
                "all_symbols": False,
                "exclude_reduce_only": False
            }
        else:
            # Cancel all orders across all symbols
            order_data = {
                "all_symbols": True,
                "exclude_reduce_only": False
            }

        result = self._make_request("POST", "/api/v1/orders/cancel_all", json_data=order_data, signed=True)

        if result and result.get("success"):
            if symbol:
                print(f"🌊 All {symbol} orders canceled")
            else:
                print(f"🌊 All orders canceled across all markets")
            return True

        return False

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for a symbol"""
        # Clean symbol for Pacifica format
        clean_symbol = symbol.replace("-USD", "").replace("/", "")

        leverage_data = {
            "symbol": clean_symbol,
            "leverage": leverage
        }

        result = self._make_request("POST", "/api/v1/account/leverage", json_data=leverage_data, signed=True)

        if result and result.get("success"):
            print(f"🌊 Leverage set to {leverage}x for {symbol}")
            return True
        else:
            print(f"🌊 Could not set leverage for {symbol} (might use cross-margin)")
            return True  # Return True anyway as Pacifica might use account-wide leverage

    def get_position(self, symbol: str) -> Tuple[str, bool, float, float, float, float, bool]:
        """
        Get position for a symbol
        Returns: (symbol, in_position, size, side, entry_price, pnl_percent, is_long)

        IMPORTANT: Returns None for the in_position flag if rate limited
        """
        # Clean symbol for Pacifica format
        clean_symbol = symbol.replace("-USD", "").replace("/", "")

        params = {"account": self.public_key}
        result = self._make_request("GET", "/api/v1/positions", params=params)

        # Check for rate limit or server error
        if isinstance(result, dict) and (result.get("rate_limit_error") or result.get("server_error")):
            print(colored("⚠️ Error on position check - cannot confirm position status!", 'red'))
            # Return special value to indicate we don't know the position status
            # Using None for in_position flag to distinguish from True/False
            return symbol, None, 0, 0, 0, 0, False

        if result and "data" in result:
            positions = result["data"]
            for pos in positions:
                pos_symbol = pos.get("symbol")
                if pos_symbol == clean_symbol:
                    # Pacifica uses "amount" not "size"
                    size = float(pos.get("amount", pos.get("size", 0)))
                    entry_price = float(pos.get("entry_price", 0))
                    mark_price = float(pos.get("mark_price", entry_price))
                    # Pacifica uses "bid" for long, "ask" for short
                    side = pos.get("side", "").lower()
                    is_long = side in ["bid", "long"]

                    # Calculate PnL percentage
                    if entry_price > 0:
                        if is_long:
                            pnl_percent = ((mark_price - entry_price) / entry_price) * 100
                        else:
                            pnl_percent = ((entry_price - mark_price) / entry_price) * 100
                    else:
                        pnl_percent = 0

                    return symbol, True, size, "long" if is_long else "short", entry_price, pnl_percent, is_long

        return symbol, False, 0, 0, 0, 0, False

    def get_open_orders(self) -> List[Dict]:
        """Get all open orders"""
        params = {"account": self.public_key}
        result = self._make_request("GET", "/api/v1/orders", params=params)

        if result and "data" in result:
            return result["data"]

        return []

    def usd_to_asset_size(self, symbol: str, usd_amount: float) -> float:
        """Convert USD amount to asset size"""
        # For crypto pairs like BTC-USD
        if "-USD" in symbol:
            base_asset = symbol.replace("-USD", "")
            bid, ask = self.get_bid_ask(symbol)

            if bid and ask:
                avg_price = (bid + ask) / 2
                size = usd_amount / avg_price
                return size

        return 0

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for a symbol"""
        # Clean symbol for Pacifica format
        clean_symbol = symbol.replace("-USD", "").replace("/", "")

        leverage_data = {
            "symbol": clean_symbol,
            "leverage": leverage
        }

        result = self._make_request("POST", "/api/v1/account/leverage", json_data=leverage_data, signed=True)

        if result and result.get("success"):
            print(f"🌊 Leverage set to {leverage}x for {symbol}")
            return True
        else:
            print(f"🌊 Could not set leverage for {symbol} (might use cross-margin)")
            return True  # Return True anyway as Pacifica might use account-wide leverage

    def get_markets(self) -> List[Dict]:
        """Get all available markets"""
        result = self._make_request("GET", "/api/v1/markets")

        if result and "data" in result:
            return result["data"]

        return []

    def get_funding_rate(self, symbol: str) -> Optional[float]:
        """Get current funding rate for a symbol"""
        # Clean symbol for Pacifica format
        clean_symbol = symbol.replace("-USD", "").replace("/", "")

        params = {"symbol": clean_symbol}
        result = self._make_request("GET", "/api/v1/funding", params=params)

        if result and "data" in result:
            data = result["data"]
            if isinstance(data, list) and len(data) > 0:
                # Return the latest funding rate
                return float(data[0].get("funding_rate", 0))
            elif isinstance(data, dict):
                return float(data.get("funding_rate", 0))

        return None

    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100) -> List[List]:
        """Get kline/candlestick data"""
        # Clean symbol for Pacifica format
        clean_symbol = symbol.replace("-USD", "").replace("/", "")

        params = {
            "symbol": clean_symbol,
            "interval": interval,
            "limit": limit
        }

        result = self._make_request("GET", "/api/v1/klines", params=params)

        if result and "data" in result:
            return result["data"]

        return []

    def get_24hr_stats(self, symbol: str) -> Dict[str, Any]:
        """Get 24hr statistics for a symbol"""
        # Clean symbol for Pacifica format
        clean_symbol = symbol.replace("-USD", "").replace("/", "")

        params = {"symbol": clean_symbol}
        result = self._make_request("GET", "/api/v1/stats", params=params)

        if result and "data" in result:
            return result["data"]

        return {}

    def close_position(self, symbol: str) -> bool:
        """Close position for a symbol"""
        # Get current position
        _, in_position, size, _, _, _, is_long = self.get_position(symbol)

        if not in_position:
            print(f"🌊 No position to close for {symbol}")
            return True

        # Get current prices
        bid, ask = self.get_bid_ask(symbol)
        if not bid or not ask:
            print(f"🌊 Could not get prices to close position")
            return False

        # Place aggressive limit order to close
        if is_long:
            # Close long by selling at bid * 0.995 (slightly below bid for quick fill)
            order_id = self.sell_limit(symbol, size, bid * 0.995, 1)
        else:
            # Close short by buying at ask * 1.005 (slightly above ask for quick fill)
            order_id = self.buy_limit(symbol, size, ask * 1.005, 1)

        if order_id:
            print(f"🌊 Closing position for {symbol}")
            return True

        return False

    def get_trade_history(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """Get trade history"""
        params = {
            "account": self.public_key,
            "limit": limit
        }

        if symbol:
            # Clean symbol for Pacifica format
            clean_symbol = symbol.replace("-USD", "").replace("/", "")
            params["symbol"] = clean_symbol

        result = self._make_request("GET", "/api/v1/trades", params=params)

        if result and "data" in result:
            return result["data"]

        return []


# ==========================
# Standalone Helper Functions
# ==========================

# Initialize global Pacifica API instance
_pacifica_api = None

def get_pacifica_api():
    """Get or create Pacifica API instance"""
    global _pacifica_api
    if _pacifica_api is None:
        _pacifica_api = PacificaAPI()
    return _pacifica_api

def get_pacifica_balance() -> float:
    """Get Pacifica balance"""
    api = get_pacifica_api()
    return api.get_balance()

def get_pacifica_orderbook(symbol: str) -> Optional[Dict[str, float]]:
    """Get Pacifica orderbook with bid/ask"""
    api = get_pacifica_api()
    bid, ask = api.get_bid_ask(symbol)
    if bid and ask:
        return {"bid": bid, "ask": ask}
    return None

def place_pacifica_limit_order(symbol: str, side: str, amount: float, price: float, leverage: int = 2) -> Optional[str]:
    """Place a limit order on Pacifica"""
    api = get_pacifica_api()
    if side.lower() == 'buy':
        return api.buy_limit(symbol, amount, price, leverage)
    else:
        return api.sell_limit(symbol, amount, price, leverage)

def place_pacifica_market_order(symbol: str, side: str, amount: float) -> Optional[str]:
    """Place a market order on Pacifica"""
    api = get_pacifica_api()
    if side.lower() == 'buy':
        return api.buy_market(symbol, amount)
    else:
        return api.sell_market(symbol, amount)

def cancel_pacifica_order(symbol: str, order_id: str) -> bool:
    """Cancel a Pacifica order"""
    api = get_pacifica_api()
    return api.cancel_order(order_id, symbol)

def get_pacifica_positions() -> List[Dict]:
    """Get all open positions on Pacifica"""
    api = get_pacifica_api()
    positions = []

    # Check common symbols
    for symbol in ['BTC-USD', 'ETH-USD']:
        _, in_position, size, side, entry_price, pnl, is_long = api.get_position(symbol)
        if in_position:
            positions.append({
                'symbol': symbol,
                'side': side,
                'contracts': size,
                'entry_price': entry_price,
                'unrealizedPnl': pnl,
                'is_long': is_long
            })

    return positions

def get_pacifica_position(symbol: str) -> Tuple[bool, float, str, float, float]:
    """
    Get position details for a specific symbol
    Returns: (in_position, size, side, entry_price, pnl_percent)
    """
    api = get_pacifica_api()
    _, in_position, size, side, entry_price, pnl_percent, _ = api.get_position(symbol)
    return in_position, size, side, entry_price, pnl_percent

def set_pacifica_leverage(symbol: str, leverage: int) -> bool:
    """Set leverage for a symbol"""
    api = get_pacifica_api()
    return api.set_leverage(symbol, leverage)

def close_pacifica_position(symbol: str) -> bool:
    """Close position for a symbol"""
    api = get_pacifica_api()
    return api.close_position(symbol)

def cancel_all_pacifica_orders(symbol: str) -> bool:
    """Cancel all orders for a symbol"""
    api = get_pacifica_api()
    return api.cancel_all_orders_market(symbol)

def get_pacifica_open_orders(symbol: str = None) -> List[Dict]:
    """Get open orders"""
    api = get_pacifica_api()
    orders = api.get_open_orders()

    if symbol:
        # Filter by symbol if provided
        clean_symbol = symbol.replace("-USD", "").replace("/", "")
        return [o for o in orders if o.get('symbol') == clean_symbol]

    return orders

# Alias for compatibility
PacificaTrader = PacificaAPI