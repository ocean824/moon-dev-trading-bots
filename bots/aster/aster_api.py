import requests
import json
import time
import hmac
import hashlib
from urllib.parse import urlencode
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime, timedelta

class AsterAPI:
    """
    Aster Exchange API wrapper for futures trading
    """

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """
        Initialize Aster API client

        Args:
            api_key: API key from Aster Exchange
            api_secret: API secret from Aster Exchange
            testnet: Whether to use testnet (not implemented yet)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://fapi.asterdex.com"
        self.headers = {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

    def _generate_signature(self, params: dict) -> str:
        """Generate HMAC SHA256 signature for authenticated requests"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _get_timestamp(self) -> int:
        """Get current timestamp in milliseconds"""
        return int(time.time() * 1000)

    def _request(self, method: str, endpoint: str, params: dict = None, signed: bool = False) -> dict:
        """
        Make a request to the API

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            params: Request parameters
            signed: Whether the request needs to be signed
        """
        url = f"{self.base_url}{endpoint}"

        if params is None:
            params = {}

        if signed:
            params['timestamp'] = self._get_timestamp()
            params['recvWindow'] = 5000
            params['signature'] = self._generate_signature(params)

        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=self.headers)
            elif method == 'POST':
                response = requests.post(url, data=params, headers=self.headers)
            elif method == 'DELETE':
                response = requests.delete(url, params=params, headers=self.headers)
            else:
                raise ValueError(f"Invalid method: {method}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise

    # Market Data Methods
    def get_exchange_info(self) -> dict:
        """Get exchange information including trading rules and symbols"""
        return self._request('GET', '/fapi/v1/exchangeInfo')

    def get_orderbook(self, symbol: str, limit: int = 100) -> dict:
        """Get order book for a symbol"""
        params = {'symbol': symbol, 'limit': limit}
        return self._request('GET', '/fapi/v1/depth', params)

    def get_ticker_24hr(self, symbol: str = None) -> dict:
        """Get 24hr ticker price change statistics"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._request('GET', '/fapi/v1/ticker/24hr', params)

    def get_price(self, symbol: str = None) -> dict:
        """Get latest price for a symbol or all symbols"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._request('GET', '/fapi/v1/ticker/price', params)

    def get_klines(self, symbol: str, interval: str, limit: int = 500) -> list:
        """
        Get kline/candlestick data

        Args:
            symbol: Trading pair symbol
            interval: Kline interval (1m, 5m, 15m, 1h, etc.)
            limit: Number of klines to fetch
        """
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        return self._request('GET', '/fapi/v1/klines', params)

    def get_mark_price(self, symbol: str = None) -> dict:
        """Get mark price and funding rate"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._request('GET', '/fapi/v1/premiumIndex', params)

    # Account Methods
    def get_account_info(self) -> dict:
        """Get current account information"""
        return self._request('GET', '/fapi/v2/account', signed=True)

    def get_balance(self) -> dict:
        """Get account balance"""
        return self._request('GET', '/fapi/v2/balance', signed=True)

    def get_positions(self, symbol: str = None) -> list:
        """Get current position information"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._request('GET', '/fapi/v2/positionRisk', params, signed=True)

    # Order Methods
    def place_order(self, symbol: str, side: str, order_type: str,
                   quantity: float, price: float = None,
                   time_in_force: str = 'GTC',
                   reduce_only: bool = False,
                   position_side: str = 'BOTH',
                   stop_price: float = None,
                   working_type: str = 'CONTRACT_PRICE') -> dict:
        """
        Place a new order

        Args:
            symbol: Trading pair symbol
            side: BUY or SELL
            order_type: LIMIT, MARKET, STOP, STOP_MARKET, TAKE_PROFIT, TAKE_PROFIT_MARKET, etc.
            quantity: Order quantity
            price: Order price (required for LIMIT orders)
            time_in_force: GTC, IOC, FOK, GTX
            reduce_only: Whether this is a reduce-only order
            position_side: BOTH, LONG, or SHORT
            stop_price: Stop price for STOP/TAKE_PROFIT orders
            working_type: MARK_PRICE or CONTRACT_PRICE (default)
        """
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
            'positionSide': position_side,
            'reduceOnly': str(reduce_only).lower()
        }

        # Only add timeInForce for non-MARKET orders
        if order_type != 'MARKET':
            params['timeInForce'] = time_in_force

        if price is not None:
            params['price'] = price

        if stop_price is not None:
            params['stopPrice'] = stop_price
            params['workingType'] = working_type

        return self._request('POST', '/fapi/v1/order', params, signed=True)

    def place_batch_orders(self, orders: list) -> list:
        """
        Place multiple orders in batch (max 5 orders)

        Args:
            orders: List of order dictionaries, each containing order parameters

        Returns:
            List of order responses
        """
        if len(orders) > 5:
            raise ValueError("Maximum 5 orders allowed in batch")

        # Convert orders list to JSON string for batchOrders parameter
        import json
        params = {
            'batchOrders': json.dumps(orders)
        }

        return self._request('POST', '/fapi/v1/batchOrders', params, signed=True)

    def cancel_order(self, symbol: str, order_id: int = None,
                    orig_client_order_id: str = None) -> dict:
        """Cancel an active order"""
        params = {'symbol': symbol}

        if order_id:
            params['orderId'] = order_id
        elif orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
        else:
            raise ValueError("Either orderId or origClientOrderId must be provided")

        return self._request('DELETE', '/fapi/v1/order', params, signed=True)

    def cancel_all_orders(self, symbol: str) -> dict:
        """Cancel all open orders for a symbol"""
        params = {'symbol': symbol}
        return self._request('DELETE', '/fapi/v1/allOpenOrders', params, signed=True)

    def get_open_orders(self, symbol: str = None) -> list:
        """Get all open orders"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._request('GET', '/fapi/v1/openOrders', params, signed=True)

    def get_order(self, symbol: str, order_id: int = None,
                 orig_client_order_id: str = None) -> dict:
        """Query order status"""
        params = {'symbol': symbol}

        if order_id:
            params['orderId'] = order_id
        elif orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
        else:
            raise ValueError("Either orderId or origClientOrderId must be provided")

        return self._request('GET', '/fapi/v1/order', params, signed=True)

    # Leverage and Margin Methods
    def change_leverage(self, symbol: str, leverage: int) -> dict:
        """Change initial leverage for a symbol"""
        params = {
            'symbol': symbol,
            'leverage': leverage
        }
        return self._request('POST', '/fapi/v1/leverage', params, signed=True)

    def change_margin_type(self, symbol: str, margin_type: str) -> dict:
        """
        Change margin type

        Args:
            symbol: Trading pair symbol
            margin_type: ISOLATED or CROSSED
        """
        params = {
            'symbol': symbol,
            'marginType': margin_type
        }
        return self._request('POST', '/fapi/v1/marginType', params, signed=True)

    # Helper Methods
    def get_ask_bid(self, symbol: str) -> Tuple[float, float, dict]:
        """
        Get best ask and bid prices

        Returns:
            (ask_price, bid_price, full_orderbook)
        """
        orderbook = self.get_orderbook(symbol, limit=5)

        if orderbook['asks'] and orderbook['bids']:
            ask = float(orderbook['asks'][0][0])
            bid = float(orderbook['bids'][0][0])
            return ask, bid, orderbook
        else:
            raise ValueError(f"No orderbook data for {symbol}")

    def get_current_price(self, symbol: str) -> float:
        """Get current mark price for a symbol"""
        mark_price_data = self.get_mark_price(symbol)
        return float(mark_price_data['markPrice'])

    def get_position(self, symbol: str) -> Optional[dict]:
        """Get position details for a specific symbol"""
        positions = self.get_positions(symbol)

        if positions:
            for pos in positions:
                if float(pos['positionAmt']) != 0:
                    # Calculate PnL percentage safely
                    pnl_percentage = 0
                    if 'initialMargin' in pos and float(pos.get('initialMargin', 0)) != 0:
                        pnl_percentage = float(pos['unRealizedProfit']) / float(pos['initialMargin']) * 100
                    elif 'notional' in pos and float(pos.get('notional', 0)) != 0:
                        # Use notional value if initialMargin not available
                        pnl_percentage = float(pos['unRealizedProfit']) / abs(float(pos['notional'])) * 100

                    return {
                        'symbol': pos['symbol'],
                        'position_amount': float(pos['positionAmt']),
                        'entry_price': float(pos.get('entryPrice', 0)),
                        'mark_price': float(pos.get('markPrice', 0)),
                        'pnl': float(pos.get('unRealizedProfit', 0)),
                        'pnl_percentage': pnl_percentage,
                        'is_long': float(pos['positionAmt']) > 0
                    }
        return None

    def kill_switch(self, symbol: str):
        """Emergency close all positions for a symbol"""
        # Cancel all orders first
        self.cancel_all_orders(symbol)

        # Get current position
        position = self.get_position(symbol)

        if position:
            # Place market order to close position
            side = 'SELL' if position['is_long'] else 'BUY'
            quantity = abs(position['position_amount'])

            self.place_order(
                symbol=symbol,
                side=side,
                order_type='MARKET',
                quantity=quantity,
                reduce_only=True
            )
            print(f"Kill switch activated: Closing {symbol} position")