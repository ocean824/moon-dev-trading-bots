from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
import threading
import time
import pandas as pd
from datetime import datetime, timedelta

# Trading Configuration
SYMBOL = "ES"          # Futures symbol to trade - Available symbols:
                        # ES  - E-mini S&P 500 (Most liquid)
                        # MES - Micro E-mini S&P 500 (1/10th of ES)
                        # NQ  - E-mini NASDAQ-100
                        # CL  - Crude Oil
                        # ZN  - 10-Year T-Note
                        # ZB  - 30-Year T-Bond
                        # GC  - Gold # not liquid f that
                        # SI  - Silver
                        # YM  - E-mini Dow ($5 Dow)
                        # RTY - E-mini Russell 2000
                        # 6E  - Euro FX
                        # ZC  - Corn
DIRECTION = "BUY"        # "BUY" or "SELL"
QUANTITY = 2            # Number of contracts to trade

# Connection Configuration
PAPER_PORT = 7497        # Paper trading port
LIVE_PORT = 7496         # Live trading port
IS_PAPER_TRADING = True  # Set to False for live trading

class TradeApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.nextValidOrderId = None
        self.order_placed = False
        self.order_event = threading.Event()
        self.contract_details = []
        self.contract_details_event = threading.Event()
        self.last_contract = None  # Store the last contract for error handling
        
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode != 2106 and errorCode != 2104 and errorCode != 2158:
            print(f"❌ Error {errorCode}: {errorString}")
            if errorCode == 200 and self.last_contract:
                print(f"   • Contract details:")
                print(f"     Symbol: {self.last_contract.symbol}")
                print(f"     Exchange: {self.last_contract.exchange if hasattr(self.last_contract, 'exchange') else 'Not set'}")
                print(f"     Trading Class: {self.last_contract.tradingClass if hasattr(self.last_contract, 'tradingClass') else 'Not set'}")
                print(f"     Multiplier: {self.last_contract.multiplier if hasattr(self.last_contract, 'multiplier') else 'Not set'}")
            
    def nextValidId(self, orderId):
        super().nextValidId(orderId)
        self.nextValidOrderId = orderId
        print(f"🎯 Moon Dev's Next Valid Order ID: {orderId}")

    def contractDetails(self, reqId, contractDetails):
        """Called when contract details are received"""
        self.contract_details.append(contractDetails)
        print(f"📋 Found contract: {contractDetails.contract.localSymbol}")
        
    def contractDetailsEnd(self, reqId):
        """Called when all contract details have been received"""
        print(f"✅ Contract details search completed")
        self.contract_details_event.set()
        
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, 
                   permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f"🔄 Order {orderId} status: {status}")
        if status == "Filled":
            print(f"✨ Order filled at ${avgFillPrice}")
            self.order_placed = True
            self.order_event.set()

def websocket_con():
    app.run()

def get_contract_month_code():
    """
    Returns the contract month code for the next available contract.
    Month codes: F(Jan) G(Feb) H(Mar) J(Apr) K(May) M(Jun) N(Jul) Q(Aug) U(Sep) V(Oct) X(Nov) Z(Dec)
    """
    current_date = datetime.now()
    month_codes = {
        1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M',
        7: 'N', 8: 'Q', 9: 'U', 10: 'V', 11: 'X', 12: 'Z'
    }
    
    # Start with next month
    target_date = current_date + timedelta(days=30)
    year_code = str(target_date.year)[-1]  # Last digit of year
    month_code = month_codes[target_date.month]
    
    return f"{month_code}{year_code}"

def get_full_contract_symbol(symbol):
    """
    Converts a simple symbol to its full contract code
    Example: "CL" -> "CLH4" (Crude Oil March 2024)
    """
    contract_month = get_contract_month_code()
    return f"{symbol}{contract_month}"

def get_futures_contract(symbol, local_symbol):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "FUT"
    contract.exchange = "GLOBEX"
    contract.currency = "USD"
    contract.localSymbol = local_symbol
    return contract

def create_market_order(direction, quantity):
    order = Order()
    order.action = direction
    order.orderType = "MKT"
    order.totalQuantity = quantity
    return order

def get_active_futures_contract():
    """
    Fetches all available futures contracts and returns the most active one
    """
    print(f"\n🔍 Moon Dev trying futures contract: {SYMBOL}")
    print("=" * 50)
    
    # Create base contract
    contract = Contract()
    contract.symbol = "MES"  # Always use MES for Micro E-mini
    contract.secType = "FUT"
    contract.currency = "USD"
    contract.exchange = "CME"  # Use CME instead of GLOBEX for contract lookup
    
    # Special handling for certain symbols
    if SYMBOL == "6E":
        print("🔄 Special handling for Euro FX futures")
        contract.symbol = "EUR"
        contract.exchange = "GLOBEX"
    elif SYMBOL == "YM":
        print("🔄 Special handling for E-mini Dow futures")
        contract.exchange = "ECBOT"
    elif SYMBOL == "RTY":
        print("🔄 Special handling for Russell 2000 futures")
        contract.exchange = "GLOBEX"
        contract.tradingClass = "M2K"  # RTY uses M2K trading class
    elif SYMBOL == "ZC":
        print("🔄 Special handling for Corn futures")
        contract.exchange = "ECBOT"
    elif SYMBOL == "MES":
        print("🔄 Special handling for Micro E-mini S&P 500")
        contract.exchange = "CME"
        contract.tradingClass = "MES"
        print(f"   • Setting exchange to: {contract.exchange}")
        print(f"   • Setting trading class to: {contract.tradingClass}")
        print(f"   • Verifying symbol: {contract.symbol}")
    else:
        # Map symbols to their proper exchanges
        exchanges = {
            "ES": "CME",     # E-mini S&P 500 -> CME
            "MES": "CME",    # Micro E-mini S&P 500 -> CME
            "NQ": "CME",     # E-mini NASDAQ -> CME
            "CL": "NYMEX",   # Crude Oil -> NYMEX
            "GC": "COMEX",   # Gold -> COMEX
            "SI": "COMEX",   # Silver -> COMEX
            "ZB": "ECBOT",   # 30Y T-Bond -> ECBOT
            "ZN": "ECBOT"    # 10Y Note -> ECBOT
        }
        contract.exchange = exchanges.get(SYMBOL, "CME")
        print(f"📍 Using standard exchange mapping: {contract.exchange}")
    
    # Store contract for error handling
    app.last_contract = contract
    
    # Add multiplier based on symbol
    multipliers = {
        "ES": "50",     # E-mini S&P 500
        "MES": "5",     # Micro E-mini S&P 500 (1/10th of ES)
        "NQ": "20",     # E-mini NASDAQ
        "CL": "1000",   # Crude Oil (1000 barrels)
        "GC": "100",    # Gold (100 oz)
        "SI": "5000",   # Silver (5000 oz)
        "ZB": "1000",   # 30Y T-Bond
        "ZN": "1000",   # 10Y Note
        "YM": "5",      # E-mini Dow ($5 x Dow)
        "RTY": "50",    # E-mini Russell 2000
        "6E": "125000", # Euro FX (125,000 euros)
        "ZC": "5000"    # Corn (5000 bushels)
    }
    if SYMBOL in multipliers:
        contract.multiplier = multipliers[SYMBOL]
        print(f"💰 Setting multiplier to: {contract.multiplier}")
    
    # Set trading class for certain products
    if SYMBOL == "6E":
        contract.tradingClass = "EUR"
    elif SYMBOL == "RTY":
        contract.tradingClass = "M2K"
    elif SYMBOL == "MES":
        contract.tradingClass = "MES"
    else:
        trading_classes = {
            "ES": "ES",
            "NQ": "NQ",
            "CL": "CL",
            "GC": "GC",
            "SI": "SI",
            "ZB": "ZB",
            "ZN": "ZN",
            "YM": "YM",
            "ZC": "ZC"
        }
        if SYMBOL in trading_classes:
            contract.tradingClass = trading_classes[SYMBOL]
            print(f"🏷️ Setting trading class to: {contract.tradingClass}")
    
    print(f"\n📝 Contract details:")
    print("=" * 50)
    print(f"   Symbol: {contract.symbol}")
    print(f"   Type: {contract.secType}")
    print(f"   Exchange: {contract.exchange}")
    print(f"   Currency: {contract.currency}")
    if hasattr(contract, 'multiplier'):
        print(f"   Multiplier: {contract.multiplier}")
    if hasattr(contract, 'tradingClass'):
        print(f"   Trading Class: {contract.tradingClass}")
    print("=" * 50)
    
    # Clear previous results
    app.contract_details = []
    app.contract_details_event.clear()
    
    print("\n🔄 Requesting contract details from IB...")
    # Request contract details
    app.reqContractDetails(1, contract)
    
    # Wait for contract details
    print("⏳ Waiting for response...")
    if app.contract_details_event.wait(timeout=5):
        if app.contract_details:
            print(f"\n✅ Found {len(app.contract_details)} contracts for {SYMBOL}")
            
            # Sort contracts by expiration date
            sorted_contracts = sorted(app.contract_details, 
                                   key=lambda x: x.contract.lastTradeDateOrContractMonth)
            
            print("\n📋 Available contracts:")
            print("=" * 50)
            for detail in sorted_contracts:
                print(f"   • {detail.contract.localSymbol} - Expires: {detail.contract.lastTradeDateOrContractMonth}")
                print(f"     Exchange: {detail.contract.exchange}")
                print(f"     Trading Class: {detail.contract.tradingClass}")
                print(f"     Multiplier: {detail.contract.multiplier}")
                print("-" * 40)
            
            # Select the first contract that's not expiring too soon
            current_date = datetime.now()
            for contract_detail in sorted_contracts:
                expiry = contract_detail.contract.lastTradeDateOrContractMonth
                if len(expiry) == 8:  # Should be YYYYMMDD format
                    try:
                        expiry_date = datetime.strptime(expiry, "%Y%m%d")
                        days_to_expiry = (expiry_date - current_date).days
                        
                        if days_to_expiry > 5:  # More than 5 days until expiration
                            selected_contract = contract_detail.contract
                            print(f"\n🎯 Selected active contract: {selected_contract.localSymbol}")
                            print(f"   Exchange: {selected_contract.exchange}")
                            print(f"   Trading Class: {selected_contract.tradingClass}")
                            print(f"   Multiplier: {selected_contract.multiplier}")
                            print(f"   Expiration: {expiry_date.strftime('%Y-%m-%d')}")
                            print(f"   Days to expiry: {days_to_expiry}")
                            return selected_contract
                    except ValueError as e:
                        print(f"⚠️ Error parsing date {expiry}: {str(e)}")
                        continue
            
            # If we get here, just take the contract with the furthest expiration
            selected_contract = sorted_contracts[-1].contract
            print(f"\n⚠️ Using furthest contract: {selected_contract.localSymbol}")
            return selected_contract
        else:
            print("❌ No contracts found in response")
    else:
        print("❌ Timeout waiting for contract details")
    
    print(f"❌ No contracts found for {SYMBOL}")
    raise Exception(f"Could not find any valid contracts for {SYMBOL}")

# Initialize connection
app = TradeApp()
port = PAPER_PORT if IS_PAPER_TRADING else LIVE_PORT
print(f"🚀 Moon Dev connecting to {'Paper' if IS_PAPER_TRADING else 'Live'} trading on port {port}")
app.connect("127.0.0.1", port, clientId=1)

# Start connection thread
con_thread = threading.Thread(target=websocket_con, daemon=True)
con_thread.start()
time.sleep(2)  # Give time for connection

try:
    # Wait for nextValidId
    timeout = 5
    start_time = time.time()
    while app.nextValidOrderId is None and time.time() - start_time < timeout:
        time.sleep(0.1)
    
    if app.nextValidOrderId is None:
        raise Exception("Timeout waiting for valid order ID")
    
    # Get the active contract
    contract = get_active_futures_contract()
    
    # Create and place market order
    print(f"\n🌲 Moon Dev creating futures market order:")
    print(f"Action: {DIRECTION} | Quantity: {QUANTITY} contract(s)")
    
    order = create_market_order(DIRECTION, QUANTITY)
    
    # Place the order
    app.placeOrder(app.nextValidOrderId, contract, order)
    print(f"🎮 Market order placed: {DIRECTION} {QUANTITY} {contract.localSymbol}")
    
    # Wait for order fill
    if app.order_event.wait(timeout=5):
        if app.order_placed:
            print(f"🎉 Moon Dev successfully executed futures market order!")
    else:
        print("⚠️ Timeout waiting for order confirmation")
            
except Exception as e:
    print(f"❌ Error: {str(e)}")
    
finally:
    time.sleep(2)  # Give time for any pending operations
    app.disconnect()
    print("👋 Moon Dev has disconnected safely")
