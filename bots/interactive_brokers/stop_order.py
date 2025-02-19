from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
import threading
import time
import pandas as pd

# Trading Configuration
SYMBOL = "SNAP"           # Symbol to trade - Available symbols:
                         # SNAP, PLTR, RDDT, APP, NVDA, TSLA, COIN, GOOG, SMCI, SHOP, 
                         # HOOD, CRSPR, LLY, TMSC, MELI, CRWD, RBLX, CROX, XYZ, TTD
DIRECTION = "SELL"       # "BUY" or "SELL"
QUANTITY = 100           # Number of shares to trade
STOP_PRICE = 10.84      # Stop price for the order

# Connection Configuration
PAPER_PORT = 7497        # Paper trading port
LIVE_PORT = 7496         # Live trading port
IS_PAPER_TRADING = True  # Set to False for live trading

class TradeApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.order_filled = False
        self.nextValidOrderId = None
        self.order_event = threading.Event()
        
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode != 2106 and errorCode != 2104 and errorCode != 2158:
            print(f"❌ Error {errorCode}: {errorString}")
            
    def nextValidId(self, orderId):
        super().nextValidId(orderId)
        self.nextValidOrderId = orderId
        print(f"🎯 Moon Dev's Next Valid Order ID: {orderId}")
        
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, 
                   permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f"🔄 Order {orderId} status: {status}")
        if status == "Filled":
            self.order_filled = True
            self.order_event.set()
            print(f"✅ Stop order filled at ${avgFillPrice}")

def websocket_con():
    app.run()

def get_contract(symbol):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.currency = "USD"
    contract.exchange = "SMART"
    return contract

def create_stop_order(direction, quantity, stop_price):
    order = Order()
    order.action = direction
    order.orderType = "STP"
    order.totalQuantity = quantity
    order.auxPrice = stop_price  # For stop orders, we use auxPrice
    return order

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
    
    # Place the stop order
    print(f"🎮 Moon Dev placing {DIRECTION} stop order for {QUANTITY} shares of {SYMBOL} at ${STOP_PRICE}")
    contract = get_contract(SYMBOL)
    order = create_stop_order(DIRECTION, QUANTITY, STOP_PRICE)
    app.placeOrder(app.nextValidOrderId, contract, order)
    
    # Wait for order to fill
    if app.order_event.wait(timeout=30):
        if app.order_filled:
            print(f"🎉 Moon Dev successfully placed stop order for {SYMBOL}")
    else:
        print("⚠️ Order placement timeout - check TWS for status")
            
except Exception as e:
    print(f"❌ Error: {str(e)}")
    
finally:
    time.sleep(2)  # Give time for any pending operations
    app.disconnect()
    print("👋 Moon Dev has disconnected safely")
