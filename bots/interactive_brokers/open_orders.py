# This should go ahead and see our current open orders. 

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
import threading
import time
import pandas as pd

# Connection Configuration
PAPER_PORT = 7497        # Paper trading port
LIVE_PORT = 7496         # Live trading port
IS_PAPER_TRADING = True  # Set to False for live trading
WAIT_TIME = 5           # Time to wait for orders data

class TradeApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.order_df = pd.DataFrame(columns=['PermId', 'ClientId', 'OrderId', 
                                            'Account', 'Symbol', 'SecType', 
                                            'Exchange', 'Action', 'OrderType', 
                                            'TotalQty', 'CashQty', 'LmtPrice', 
                                            'AuxPrice', 'Status'])
        self.orders_received = False
        self.orders_event = threading.Event()

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode != 2106 and errorCode != 2104 and errorCode != 2158:
            print(f"❌ Error {errorCode}: {errorString}")

    def openOrder(self, orderId, contract, order, orderState):
        super().openOrder(orderId, contract, order, orderState)
        dictionary = {
            "PermId": order.permId, 
            "ClientId": order.clientId, 
            "OrderId": orderId, 
            "Account": order.account, 
            "Symbol": contract.symbol, 
            "SecType": contract.secType,
            "Exchange": contract.exchange, 
            "Action": order.action, 
            "OrderType": order.orderType,
            "TotalQty": order.totalQuantity, 
            "CashQty": order.cashQty, 
            "LmtPrice": order.lmtPrice, 
            "AuxPrice": order.auxPrice, 
            "Status": orderState.status
        }
        # Use concat instead of append
        new_row = pd.DataFrame([dictionary])
        self.order_df = pd.concat([self.order_df, new_row], ignore_index=True)
        print(f"🔄 Order found: {order.action} {order.totalQuantity} {contract.symbol} @ {order.lmtPrice if order.lmtPrice else order.auxPrice}")

    def openOrderEnd(self):
        print("🎯 Moon Dev has extracted all open orders")
        self.orders_received = True
        self.orders_event.set()

def websocket_con():
    app.run()

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
    print("🔍 Moon Dev is fetching your open orders...")
    app.reqOpenOrders()
    
    # Wait for orders
    if app.orders_event.wait(timeout=WAIT_TIME):
        if app.orders_received:
            if not app.order_df.empty:
                # Format the DataFrame for display
                display_df = app.order_df.copy()
                
                # Format price columns
                for col in ['LmtPrice', 'AuxPrice']:
                    display_df[col] = display_df[col].apply(lambda x: f'${x:,.2f}' if x != 0 else '-')
                
                # Format quantity as plain number
                display_df['TotalQty'] = display_df['TotalQty'].apply(lambda x: f'{x:,.0f}')
                
                print("\n📊 Moon Dev's Open Orders Summary:")
                print("=" * 120)
                print(display_df[['Symbol', 'Action', 'OrderType', 'TotalQty', 'LmtPrice', 'AuxPrice', 'Status']].to_string(index=False))
                print("=" * 120)
            else:
                print("📭 No open orders found")
    else:
        print("⚠️ Timeout waiting for orders")
            
except Exception as e:
    print(f"❌ Error: {str(e)}")
    
finally:
    time.sleep(2)  # Give time for any pending operations
    app.disconnect()
    print("👋 Moon Dev has disconnected safely")

