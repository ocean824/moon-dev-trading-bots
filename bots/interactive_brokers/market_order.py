from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
import threading
import time
import pandas as pd

# Trading Configuration
SYMBOL = "ROKU"           # Symbol to trade - Available symbols:
                         # SNAP, PLTR, RDDT, APP, NVDA, TSLA, COIN, GOOG, SMCI, SHOP, 
                         # HOOD, CRSPR, LLY, TMSC, MELI, CRWD, RBLX, CROX, XYZ, TTD,
                         # NTRA, ROKU, LVMH, ADBE, AMD, DE, TWST, PATH, BEAM, JD, TXG,
                         # GME, RKLB, CHWY, GTLB, DDOG, SNOW, CRM, PYPL, INTU, LMT,
                         # CAT, TEAM, NOW, AUR, PSTG, KMTUY, MSTR, MARA, HIMS
DIRECTION = "BUY"        # "BUY" or "SELL"
QUANTITY = 10             # Number of shares to trade

# Connection Configuration
PAPER_PORT = 7497         # Paper trading port
LIVE_PORT = 7496          # Live trading port
IS_PAPER_TRADING = True   # Set to False for live trading

class TradeApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.order_filled = False
        self.order_submitted = False
        self.nextValidOrderId = None
        self.order_event = threading.Event()
        self.last_price = None
        
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
        
        if status in ["PreSubmitted", "Submitted"]:
            self.order_submitted = True
            print(f"   Filled: {filled} | Remaining: {remaining}")
            if whyHeld:
                print(f"   Why Held: {whyHeld}")
            
        if status == "Filled":
            self.order_filled = True
            self.last_price = avgFillPrice
            print(f"✅ Order filled! {filled} shares at ${avgFillPrice}")
            self.order_event.set()
            
        if status == "Cancelled":
            print("❌ Order was cancelled")
            self.order_event.set()

def websocket_con():
    app.run()

def get_contract(symbol):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "STK"
    contract.currency = "USD"
    contract.exchange = "SMART"
    contract.primaryExch = "NASDAQ"  # Add primary exchange
    return contract

def create_market_order(direction, quantity):
    order = Order()
    order.action = direction
    order.orderType = "MKT"
    order.totalQuantity = quantity
    order.tif = "DAY"  # Day order
    order.eTradeOnly = False
    order.firmQuoteOnly = False
    order.outsideRth = True  # Allow trades outside regular trading hours
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
    
    # Place the trade
    print(f"🎮 Moon Dev placing {DIRECTION} order for {QUANTITY} shares of {SYMBOL}")
    contract = get_contract(SYMBOL)
    order = create_market_order(DIRECTION, QUANTITY)
    app.placeOrder(app.nextValidOrderId, contract, order)
    
    # Wait for order to fill
    fill_timeout = 30  # 30 seconds timeout
    start_time = time.time()
    
    while time.time() - start_time < fill_timeout:
        if app.order_filled:
            print(f"🎉 Moon Dev successfully completed {DIRECTION} order for {SYMBOL} at ${app.last_price}")
            break
        elif app.order_submitted and time.time() - start_time > 20:
            print("⚠️ Order submitted but not filled after 20 seconds")
            break
        elif not app.order_submitted and time.time() - start_time > 10:
            print("⚠️ Order not submitted after 10 seconds - might be connection issues")
            break
        time.sleep(0.1)
    
    if not app.order_filled:
        if app.order_submitted:
            print("⏳ Order is working - check TWS for final status")
            print("💡 Tip: Make sure you have market data permissions for this symbol")
        else:
            print("❌ Order was not submitted successfully")
            print("💡 Tips:")
            print("   1. Check TWS is running and connected")
            print("   2. Verify market data permissions")
            print("   3. Ensure sufficient buying power")
            print("   4. Check if trading is allowed for this symbol")
            
except Exception as e:
    print(f"❌ Error: {str(e)}")
    
finally:
    time.sleep(2)  # Give time for any pending operations
    app.disconnect()
    print("👋 Moon Dev has disconnected safely")