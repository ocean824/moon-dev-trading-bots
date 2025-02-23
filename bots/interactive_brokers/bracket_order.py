# This will allow us to put a bracket order where we can have a stop-loss and take profit all at the same time 

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

                        
DIRECTION = "BUY"        # "BUY" or "SELL"
QUANTITY = 100           # Number of shares to trade
ENTRY_PRICE = 10.50      # Limit price for entry
STOP_LOSS = 10       # Stop loss price
TAKE_PROFIT = 12.00     # Take profit price

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
        if status == "Submitted":
            self.order_placed = True
            self.order_event.set()

def websocket_con():
    app.run()

def get_contract(symbol, sectype="STK", currency="USD", exchange="SMART"):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = sectype
    contract.currency = currency
    contract.exchange = exchange
    return contract

def create_bracket_order(order_id, direction, quantity, entry_price, stop_loss_price, take_profit_price):
    # Parent Entry Order
    parent = Order()
    parent.orderId = order_id
    parent.action = direction
    parent.orderType = "LMT"
    parent.totalQuantity = quantity
    parent.lmtPrice = entry_price
    parent.transmit = False  # Don't send until we have all pieces
    print(f"🎮 Parent Order: {direction} {quantity} {SYMBOL} @ ${entry_price}")

    # Stop Loss Order
    stop_loss = Order()
    stop_loss.orderId = parent.orderId + 1
    stop_loss.action = "SELL" if direction == "BUY" else "BUY"
    stop_loss.orderType = "STP"
    stop_loss.totalQuantity = quantity
    stop_loss.auxPrice = stop_loss_price
    stop_loss.parentId = order_id
    stop_loss.transmit = False
    print(f"🛑 Stop Loss: {stop_loss.action} {quantity} {SYMBOL} @ ${stop_loss_price}")

    # Take Profit Order
    take_profit = Order()
    take_profit.orderId = parent.orderId + 2
    take_profit.action = "SELL" if direction == "BUY" else "BUY"
    take_profit.orderType = "LMT"
    take_profit.totalQuantity = quantity
    take_profit.lmtPrice = take_profit_price
    take_profit.parentId = order_id
    take_profit.transmit = True  # This is the last order, so we can transmit the whole bracket
    print(f"💰 Take Profit: {take_profit.action} {quantity} {SYMBOL} @ ${take_profit_price}")

    return [parent, stop_loss, take_profit]

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
    
    # Create and place bracket order
    print(f"\n🎯 Moon Dev creating bracket order for {SYMBOL}:")
    print(f"Entry: ${ENTRY_PRICE} | Stop Loss: ${STOP_LOSS} | Take Profit: ${TAKE_PROFIT}")
    
    bracket = create_bracket_order(
        app.nextValidOrderId,
        DIRECTION,
        QUANTITY,
        ENTRY_PRICE,
        STOP_LOSS,
        TAKE_PROFIT
    )
    
    # Place all orders in the bracket
    for order in bracket:
        app.placeOrder(order.orderId, get_contract(SYMBOL), order)
        time.sleep(0.1)  # Small delay between orders
    
    # Wait for order placement confirmation
    if app.order_event.wait(timeout=5):
        if app.order_placed:
            print(f"\n✨ Moon Dev successfully placed bracket order for {SYMBOL}!")
            print(f"🎯 Entry Price: ${ENTRY_PRICE}")
            print(f"📉 Stop Loss: ${STOP_LOSS} (Risk: ${ENTRY_PRICE - STOP_LOSS:.2f} per share)")
            print(f"📈 Take Profit: ${TAKE_PROFIT} (Reward: ${TAKE_PROFIT - ENTRY_PRICE:.2f} per share)")
            print(f"📊 Risk/Reward Ratio: 1:{(TAKE_PROFIT - ENTRY_PRICE)/(ENTRY_PRICE - STOP_LOSS):.2f}")
    else:
        print("⚠️ Timeout waiting for order confirmation")
            
except Exception as e:
    print(f"❌ Error: {str(e)}")
    
finally:
    time.sleep(2)  # Give time for any pending operations
    app.disconnect()
    print("👋 Moon Dev has disconnected safely") 