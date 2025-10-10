import os
import time
import logging
from decimal import Decimal
from typing import Optional, Tuple, Dict, Any
# Use the nice_funcs_real module that has proper imports
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nice_funcs_real import HibachiAPI as BaseHibachiAPI

# Try to import Side from the Hibachi SDK
try:
    from hibachi_xyz import Side
except ImportError:
    # Define Side enum locally if not available
    from enum import Enum
    class Side(Enum):
        BUY = "BUY"
        SELL = "SELL"
from security_utils import sanitize_error_for_logging

class HibachiAPI(BaseHibachiAPI):
    """
    Hibachi Exchange API wrapper providing simplified trading functions
    Inherits from the base implementation
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
    
    def buy_limit(self, symbol: str, quantity: float, price: float, leverage: int = 1):
        """Place a buy limit order - leverage is automatic based on market risk factors"""
        
        print(f"🔄 Calling place_limit_order with: symbol={symbol}, side=BUY, quantity={quantity}, price={price}")
        print(f"📊 Parameters: symbol='{symbol}', quantity={quantity}, price={price}, side=Side.BUY, max_fees_percent=0.1")
        
        # Absolutely prevent scientific notation - multiple formatting approaches
        from decimal import Decimal
        
        print(f"🔧 Market order input quantity: {quantity}")
        print(f"🔧 Input quantity repr: {repr(quantity)}")
        
        # Method 1: Decimal approach
        decimal_qty = Decimal(str(quantity))
        decimal_formatted = float(decimal_qty.quantize(Decimal('0.00000001')))
        
        # Method 2: String formatting approach
        string_formatted = float(f"{quantity:.8f}")
        
        # Use the decimal method as it's most precise
        formatted_quantity = decimal_formatted
        
        print(f"🔧 Decimal formatted: {decimal_formatted}")
        print(f"🔧 String formatted: {string_formatted}")
        print(f"🔧 Final quantity: {formatted_quantity}")
        print(f"🔧 Final repr: {repr(formatted_quantity)}")
        print(f"🔧 Sending to API: {formatted_quantity:.8f}")
        
        # Correct API call with proper types and parameter order
        nonce, order_id = self.client.place_limit_order(
            symbol=symbol,
            quantity=formatted_quantity,  # float, properly formatted
            price=price,                  # float, not string  
            side=Side.BUY,                # Side enum, not string
            max_fees_percent=0.1          # float, not string
        )
        
        # Return order info in expected format
        response = {'nonce': nonce, 'id': order_id, 'orderId': order_id}
        
        print(f"✅ Got response from API: {type(response)}")
        print(f"📊 Response content: {response}")
        return response
    
    def sell_limit(self, symbol: str, quantity: float, price: float, leverage: int = 1):
        """Place a sell limit order - leverage is automatic based on market risk factors"""
        
        # Absolutely prevent scientific notation - multiple formatting approaches
        from decimal import Decimal
        
        print(f"🔧 Market order input quantity: {quantity}")
        print(f"🔧 Input quantity repr: {repr(quantity)}")
        
        # Method 1: Decimal approach
        decimal_qty = Decimal(str(quantity))
        decimal_formatted = float(decimal_qty.quantize(Decimal('0.00000001')))
        
        # Method 2: String formatting approach
        string_formatted = float(f"{quantity:.8f}")
        
        # Use the decimal method as it's most precise
        formatted_quantity = decimal_formatted
        
        print(f"🔧 Decimal formatted: {decimal_formatted}")
        print(f"🔧 String formatted: {string_formatted}")
        print(f"🔧 Final quantity: {formatted_quantity}")
        print(f"🔧 Final repr: {repr(formatted_quantity)}")
        print(f"🔧 Sending to API: {formatted_quantity:.8f}")
        
        # Correct API call with proper types
        nonce, order_id = self.client.place_limit_order(
            symbol=symbol,
            quantity=formatted_quantity,  # float, properly formatted
            price=price,                  # float, not string
            side=Side.SELL,               # Side enum, not string
            max_fees_percent=0.1          # float, not string
        )
        
        # Return order info in expected format
        response = {'nonce': nonce, 'id': order_id, 'orderId': order_id}
        return response
    
    def buy_market(self, symbol: str, quantity: float, leverage: int = 1):
        """Place a buy market order - leverage is automatic based on market risk factors"""
        
        # SOLUTION: Force quantities above scientific notation threshold (0.0001)
        print(f"🔧 Market order input quantity: {quantity}")
        print(f"🔧 Input quantity repr: {repr(quantity)}")
        
        # Python uses scientific notation for numbers < 0.0001
        # So round up tiny quantities to the minimum safe value
        MIN_SAFE_QUANTITY = 0.0001
        
        if quantity < MIN_SAFE_QUANTITY:
            print(f"🔧 Quantity {quantity} is below safe threshold {MIN_SAFE_QUANTITY}")
            print(f"🔧 Rounding UP to minimum safe quantity")
            clean_quantity = MIN_SAFE_QUANTITY
        else:
            clean_quantity = quantity
            
        print(f"🔧 FINAL quantity going to API: {clean_quantity}")
        print(f"🔧 FINAL repr: {repr(clean_quantity)}")
        print(f"🔧 Uses scientific notation: {'e' in repr(clean_quantity)}")
        
        # Correct API call with proper types - add debugging for signature issues
        print(f"🔧 Calling API with:")
        print(f"   symbol: {symbol}")
        print(f"   quantity: {clean_quantity}")
        print(f"   side: {Side.BUY}")
        print(f"   max_fees_percent: 0.1")
        
        try:
            nonce, order_id = self.client.place_market_order(
                symbol=symbol,
                quantity=clean_quantity,      # float, guaranteed clean
                side=Side.BUY,                # Side enum, not string  
                max_fees_percent=0.1          # float, not string
            )
            print(f"🔧 API call succeeded: nonce={nonce}, order_id={order_id}")
        except Exception as api_error:
            print(f"🔧 API call failed: {api_error}")
            print(f"🔧 Error type: {type(api_error)}")
            raise  # Re-raise the error
        
        # Return order info in expected format
        response = {'nonce': nonce, 'id': order_id, 'orderId': order_id}
        return response
    
    def sell_market(self, symbol: str, quantity: float, leverage: int = 1):
        """Place a sell market order - leverage is automatic based on market risk factors"""
        
        # Absolutely prevent scientific notation - multiple formatting approaches
        from decimal import Decimal
        
        print(f"🔧 Market order input quantity: {quantity}")
        print(f"🔧 Input quantity repr: {repr(quantity)}")
        
        # Method 1: Decimal approach
        decimal_qty = Decimal(str(quantity))
        decimal_formatted = float(decimal_qty.quantize(Decimal('0.00000001')))
        
        # Method 2: String formatting approach
        string_formatted = float(f"{quantity:.8f}")
        
        # Use the decimal method as it's most precise
        formatted_quantity = decimal_formatted
        
        print(f"🔧 Decimal formatted: {decimal_formatted}")
        print(f"🔧 String formatted: {string_formatted}")
        print(f"🔧 Final quantity: {formatted_quantity}")
        print(f"🔧 Final repr: {repr(formatted_quantity)}")
        print(f"🔧 Sending to API: {formatted_quantity:.8f}")
        
        # Correct API call with proper types
        nonce, order_id = self.client.place_market_order(
            symbol=symbol,
            quantity=formatted_quantity,  # float, properly formatted
            side=Side.SELL,               # Side enum, not string
            max_fees_percent=0.1          # float, not string
        )
        
        # Return order info in expected format
        response = {'nonce': nonce, 'id': order_id, 'orderId': order_id}
        return response
    
    def buy_limit_reduce_only(self, symbol: str, quantity: float, price: float):
        """Place a buy limit order with REDUCE_ONLY flag - only closes existing short positions"""
        
        # Ensure quantity is not in scientific notation - use Decimal for precision
        from decimal import Decimal, ROUND_DOWN
        
        print(f"🔧 REDUCE-ONLY buy limit order - quantity: {quantity}")
        print(f"🔧 Input quantity repr: {repr(quantity)}")
        
        # For reduce-only orders, use EXACT quantity - no minimum size limits
        # Use Decimal to avoid any scientific notation issues
        decimal_quantity = Decimal(str(quantity))
        # Round to 8 decimal places to avoid precision issues
        decimal_quantity = decimal_quantity.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
        
        # Convert back to float but ensure it's not in scientific notation
        formatted_quantity = float(decimal_quantity)
        
        print(f"🔧 Decimal quantity: {decimal_quantity}")
        print(f"🔧 FINAL reduce-only quantity: {formatted_quantity}")
        print(f"🔧 FINAL repr: {repr(formatted_quantity)}")
        print(f"🔧 Uses scientific notation: {'e' in repr(formatted_quantity)}")
        
        # CRITICAL FIX: The Hibachi API cannot handle scientific notation
        # We need to pass the Decimal object itself, not a float
        print(f"🔧 CRITICAL: Using Decimal object to avoid scientific notation")
        print(f"🔧 Decimal object: {decimal_quantity}")
        print(f"🔧 Decimal type: {type(decimal_quantity)}")
        
        # Use the Decimal directly - many APIs can handle Decimal objects in JSON serialization
        final_quantity = decimal_quantity
        
        # Place reduce-only limit order
        nonce, order_id = self.client.place_limit_order(
            symbol=symbol,
            quantity=final_quantity,          # Use properly formatted float
            price=price,                      # float, not string  
            side=Side.BUY,                    # Side enum, not string
            max_fees_percent=0.1,             # float, not string
            order_flags=OrderFlags.ReduceOnly # REDUCE ONLY FLAG!
        )
        
        # Return order info in expected format
        response = {'nonce': nonce, 'id': order_id, 'orderId': order_id}
        return response
    
    def sell_limit_reduce_only(self, symbol: str, quantity: float, price: float):
        """Place a sell limit order with REDUCE_ONLY flag - only closes existing long positions"""
        
        # Ensure quantity is not in scientific notation - use Decimal for precision
        from decimal import Decimal, ROUND_DOWN
        
        print(f"🔧 REDUCE-ONLY sell limit order - quantity: {quantity}")
        print(f"🔧 Input quantity repr: {repr(quantity)}")
        
        # For reduce-only orders, use EXACT quantity - no minimum size limits
        # Use Decimal to avoid any scientific notation issues
        decimal_quantity = Decimal(str(quantity))
        # Round to 8 decimal places to avoid precision issues
        decimal_quantity = decimal_quantity.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
        
        # Convert back to float but ensure it's not in scientific notation
        formatted_quantity = float(decimal_quantity)
        
        print(f"🔧 Decimal quantity: {decimal_quantity}")
        print(f"🔧 FINAL reduce-only quantity: {formatted_quantity}")
        print(f"🔧 FINAL repr: {repr(formatted_quantity)}")
        print(f"🔧 Uses scientific notation: {'e' in repr(formatted_quantity)}")
        
        # CRITICAL FIX: The Hibachi API cannot handle scientific notation
        # We need to pass the Decimal object itself, not a float
        print(f"🔧 CRITICAL: Using Decimal object to avoid scientific notation")
        print(f"🔧 Decimal object: {decimal_quantity}")
        print(f"🔧 Decimal type: {type(decimal_quantity)}")
        
        # Use the Decimal directly - many APIs can handle Decimal objects in JSON serialization
        final_quantity = decimal_quantity
        
        # Place reduce-only limit order
        nonce, order_id = self.client.place_limit_order(
            symbol=symbol,
            quantity=final_quantity,          # Use properly formatted float
            price=price,                      # float, not string
            side=Side.SELL,                   # Side enum, not string
            max_fees_percent=0.1,             # float, not string
            order_flags=OrderFlags.ReduceOnly # REDUCE ONLY FLAG!
        )
        
        # Return order info in expected format
        response = {'nonce': nonce, 'id': order_id, 'orderId': order_id}
        return response
    
    def cancel_order(self, order_id: str):
        """Cancel a specific order"""
        # Convert to int since API expects integer order_id
        response = self.client.cancel_order(order_id=int(order_id))
        return response
    
    def cancel_all_orders_market(self, symbol: str):
        """Cancel all orders for a specific market"""
        # Get all open orders for the symbol
        orders = self.client.get_open_orders(symbol=symbol)
        cancelled_orders = []
        
        for order in orders:
            cancel_response = self.cancel_order(order['id'])
            if cancel_response:
                cancelled_orders.append(order['id'])
        
        return cancelled_orders
    
    def get_position(self, symbol: str) -> Tuple[list, bool, float, str, float, float, bool]:
        """
        Get position information for a symbol
        Returns: (positions, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long)
        """
        account_info = self.client.get_account_info()
        
        if not account_info or not hasattr(account_info, 'positions'):
            return [], False, 0.0, "", 0.0, 0.0, False
        
        positions = account_info.positions
        
        # Find position for the symbol
        current_position = None
        for position in positions:
            if hasattr(position, 'symbol') and position.symbol == symbol:
                current_position = position
                break
        
        if current_position and hasattr(current_position, 'quantity') and abs(float(current_position.quantity)) > 0.000001:
            im_in_pos = True
            mypos_size = float(current_position.quantity)
            pos_sym = current_position.symbol
            entry_px = float(current_position.openPrice)
            
            # Calculate PnL percentage
            if hasattr(current_position, 'unrealizedTradingPnl'):
                unrealized_pnl = float(current_position.unrealizedTradingPnl)
                notional = float(current_position.notionalValue)
                pnl_perc = (unrealized_pnl / notional * 100) if notional != 0 else 0.0
            else:
                pnl_perc = 0.0
            
            # Determine direction - case insensitive check
            is_long = hasattr(current_position, 'direction') and current_position.direction.lower() == 'long'
            
            return positions, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long
        else:
            return positions, False, 0.0, "", 0.0, 0.0, False
    
    def get_account_info(self):
        """Get account information"""
        return self.client.get_account_info()
    
    def get_bid_ask(self, symbol: str) -> Tuple[float, float]:
        """Get current bid and ask prices"""
        # Use get_prices method instead of orderbook
        prices = self.client.get_prices(symbol)
        if prices:
            bid = float(prices.bidPrice)
            ask = float(prices.askPrice)
            return bid, ask
        else:
            return 0.0, 0.0
    
    def get_orderbook_levels(self, symbol: str, levels: int = 5):
        """Get orderbook with specified number of levels"""
        # Use valid granularity - '0.1' is the smallest allowed
        orderbook = self.client.get_orderbook(symbol, depth=levels, granularity='0.1')
        
        # Convert Hibachi's OrderBook format to standard dict format for compatibility
        if orderbook and hasattr(orderbook, 'bid') and hasattr(orderbook, 'ask'):
            formatted_orderbook = {
                'bids': [[level.price, level.quantity] for level in orderbook.bid] if orderbook.bid else [],
                'asks': [[level.price, level.quantity] for level in orderbook.ask] if orderbook.ask else []
            }
            return formatted_orderbook
        else:
            return orderbook
    
    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage for a symbol - check all possible methods"""
        print(f"🔍 Checking for leverage methods...")
        
        # List all methods to see what's available
        leverage_methods = [method for method in dir(self.client) if 'leverage' in method.lower()]
        if leverage_methods:
            print(f"🎯 Found leverage methods: {leverage_methods}")
            
            # Try each method
            for method_name in leverage_methods:
                method = getattr(self.client, method_name)
                print(f"🧪 Trying {method_name}...")
                response = method(symbol, leverage)
                print(f"✅ {method_name} worked: {response}")
                return response
        else:
            print("❌ No leverage methods found in client")
            
        # Also check for any margin or position methods
        margin_methods = [method for method in dir(self.client) if any(word in method.lower() for word in ['margin', 'position', 'account'])]
        print(f"📊 Related methods found: {margin_methods}")
        
        return None
    
    def close_position(self, symbol: str):
        """Close entire position for a symbol"""
        positions, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long = self.get_position(symbol)
        
        if im_in_pos:
            print(f"🔧 Closing position: {abs(mypos_size):.8f} BTC ({'LONG' if is_long else 'SHORT'})")
            
            # Round position size to exchange's step size precision
            raw_asset_size = abs(mypos_size)
            asset_size = self.round_to_step_size(symbol, raw_asset_size)
            
            print(f"🔧 Raw position size: {raw_asset_size:.10f} BTC")
            print(f"🔧 Step-size rounded: {asset_size:.10f} BTC")
            
            # This should match what the exchange UI shows exactly
            
            # Get current market price
            bid, ask = self.get_bid_ask(symbol)
            
            if is_long:
                # Close long with market sell (immediate fill)
                print(f"🔧 Closing LONG with market sell order")
                return self.sell_market(symbol, asset_size)
            else:
                # Close short with market buy (immediate fill)
                print(f"🔧 Closing SHORT with market buy order")
                return self.buy_market(symbol, asset_size)
        else:
            print(f"No position to close for {symbol}")
            return None
    
    def pnl_close(self, symbol: str, target: float, max_loss: float, leverage: float = 1.0):
        """Close position if PnL reaches target profit or max loss
        
        Args:
            symbol: Trading symbol
            target: Target profit percentage (leveraged)
            max_loss: Maximum loss percentage (leveraged)
            leverage: Market leverage to convert unleveraged P&L to leveraged P&L
        """
        positions, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long = self.get_position(symbol)
        
        if im_in_pos:
            # Convert unleveraged P&L to leveraged P&L for comparison
            leveraged_pnl = pnl_perc * leverage
            print(f"🔧 PnL Check: Current {leveraged_pnl:.2f}%, Target: {target}%, Max Loss: {max_loss}%")
            
            if leveraged_pnl >= target:
                print(f"🎯 TAKING PROFIT at {leveraged_pnl:.2f}% (target: {target}%)")
                try:
                    response = self.close_position(symbol)
                    if response:
                        print(f"✅ Profit close order placed successfully!")
                        return True
                    else:
                        print(f"❌ Failed to place profit close order")
                        return False
                except Exception as close_error:
                    print(f"❌ Error during profit close: {close_error}")
                    print(f"🔧 Error type: {type(close_error)}")
                    print(f"🔧 Error details: {str(close_error)}")
                    return False
                    
            elif leveraged_pnl <= max_loss:
                print(f"🛑 STOPPING LOSS at {leveraged_pnl:.2f}% (max loss: {max_loss}%)")
                try:
                    response = self.close_position(symbol)
                    if response:
                        print(f"✅ Stop loss close order placed successfully!")
                        return True
                    else:
                        print(f"❌ Failed to place stop loss close order")
                        return False
                except Exception as close_error:
                    print(f"❌ Error during stop loss close: {close_error}")
                    print(f"🔧 Error type: {type(close_error)}")
                    print(f"🔧 Error details: {str(close_error)}")
                    return False
            else:
                print(f"📊 PnL within targets - no action needed")
                return False
        else:
            return False
    
    def usd_to_asset_size(self, symbol: str, usd_amount: float) -> float:
        """Convert USD amount to asset size for position sizing"""
        # Get current price
        bid, ask = self.get_bid_ask(symbol)
        mid_price = (bid + ask) / 2
        
        # Calculate asset size based on USD amount
        asset_size = usd_amount / mid_price
        
        return asset_size
    
    def get_current_price(self, symbol: str) -> float:
        """Get current market price"""
        bid, ask = self.get_bid_ask(symbol)
        return (bid + ask) / 2
    
    def get_market_leverage(self, symbol: str) -> float:
        """Get the automatic leverage for a specific market"""
        exchange_info = self.client.get_exchange_info()
        if hasattr(exchange_info, 'futureContracts'):
            for contract in exchange_info.futureContracts:
                if hasattr(contract, 'symbol') and contract.symbol == symbol:
                    if hasattr(contract, 'riskFactorForOrders'):
                        risk_factor = float(contract.riskFactorForOrders)
                        leverage = 1.0 / risk_factor
                        return leverage
        return 1.0  # Default to 1x if not found
    
    def get_max_position_value(self, symbol: str) -> float:
        """Get maximum position value for a symbol (balance × leverage)"""
        account_info = self.get_account_info()
        if account_info and hasattr(account_info, 'balance'):
            balance = float(account_info.balance)
            leverage = self.get_market_leverage(symbol)
            return balance * leverage
        return 0.0
    
    def get_symbol_step_size(self, symbol: str) -> float:
        """Get the step size (quantity precision) for a symbol"""
        exchange_info = self.client.get_exchange_info()
        if hasattr(exchange_info, 'futureContracts'):
            for contract in exchange_info.futureContracts:
                if hasattr(contract, 'symbol') and contract.symbol == symbol:
                    if hasattr(contract, 'stepSize'):
                        return float(contract.stepSize)
        return 0.0000000001  # Default to 10 decimal places
    
    def round_to_step_size(self, symbol: str, quantity: float) -> float:
        """Round quantity to the symbol's step size precision"""
        step_size = self.get_symbol_step_size(symbol)
        
        print(f"🔧 Rounding quantity {quantity} to step size {step_size}")
        
        # Round to the nearest step size
        rounded_quantity = round(quantity / step_size) * step_size
        
        print(f"🔧 Rounded quantity: {rounded_quantity}")
        print(f"🔧 Rounded repr: {repr(rounded_quantity)}")
        
        return rounded_quantity