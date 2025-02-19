# This file will close all positions and cancel any open orders good for the end of the day. 

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
import threading
import time
import pandas as pd
import numpy as np
from datetime import datetime

# Connection Configuration
PAPER_PORT = 7497        # Paper trading port
LIVE_PORT = 7496         # Live trading port
IS_PAPER_TRADING = True  # Set to False for live trading
WAIT_TIME = 2           # Time to wait for position data

class TradeApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.pos_df = pd.DataFrame(columns=['Account', 'Symbol', 'SecType', 'Position', 'Avg cost', 'LocalSymbol'])
        self.nextValidOrderId = None
        self.positions_loaded = threading.Event()
        self.contract_details = []
        self.contract_details_event = threading.Event()
        self.order_filled = {}  # Track filled orders
        
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode != 2106 and errorCode != 2104 and errorCode != 2158:
            print(f"❌ Error {errorCode}: {errorString}")

    def contractDetails(self, reqId, contractDetails):
        self.contract_details.append(contractDetails)
        
    def contractDetailsEnd(self, reqId):
        self.contract_details_event.set()

    def position(self, account, contract, position, avgCost):
        super().position(account, contract, position, avgCost)
        dictionary = {
            "Account": account,
            "Symbol": contract.symbol,
            "SecType": contract.secType,
            "Position": position,
            "Avg cost": avgCost,
            "LocalSymbol": contract.localSymbol if hasattr(contract, 'localSymbol') else contract.symbol
        }
        new_row = pd.DataFrame([dictionary])
        self.pos_df = pd.concat([self.pos_df, new_row], ignore_index=True)

    def positionEnd(self):
        print("🎯 Moon Dev has extracted all position data")
        self.positions_loaded.set()

    def nextValidId(self, orderId):
        super().nextValidId(orderId)
        self.nextValidOrderId = orderId
        print(f"🔑 Moon Dev's Next Valid Order ID: {orderId}")

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, 
                   permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f"🔄 Order {orderId} status: {status}")
        if status == "Filled":
            self.order_filled[orderId] = True
            print(f"✅ Order {orderId} filled at ${avgFillPrice}")

def websocket_con():
    app.run()

def get_active_futures_contract(symbol, local_symbol=None):
    """Get the active futures contract details"""
    contract = Contract()
    contract.symbol = symbol
    contract.secType = "FUT"
    contract.currency = "USD"
    
    # Map symbols to their proper exchanges
    exchanges = {
        "ES": "CME",      # E-mini S&P 500 -> CME
        "NQ": "CME",      # E-mini NASDAQ -> CME
        "CL": "NYMEX",    # Crude Oil -> NYMEX
        "GC": "COMEX",    # Gold -> COMEX
        "SI": "COMEX",    # Silver -> COMEX
        "ZB": "CBOT",     # 30Y T-Bond -> CBOT
        "ZN": "CBOT",     # 10Y Note -> CBOT
        "6E": "CME",      # Euro FX -> CME
        "LBR": "CME"      # Lumber -> CME
    }
    contract.exchange = exchanges.get(symbol, "CME")
    
    # If we have a local symbol, use it directly
    if local_symbol:
        contract.localSymbol = local_symbol
        return contract
    
    # Otherwise, get the active contract details
    app.contract_details = []
    app.contract_details_event.clear()
    app.reqContractDetails(1, contract)
    
    if app.contract_details_event.wait(timeout=5):
        if app.contract_details:
            sorted_contracts = sorted(app.contract_details, 
                                   key=lambda x: x.contract.lastTradeDateOrContractMonth)
            return sorted_contracts[-1].contract
            
    raise Exception(f"Could not find active contract for {symbol}")

def get_contract(symbol, sec_type, local_symbol=None, exchange="SMART"):
    if sec_type == "STK":
        contract = Contract()
        contract.symbol = symbol
        contract.secType = sec_type
        contract.currency = "USD"
        contract.exchange = exchange
        return contract
    elif sec_type == "FUT":
        return get_active_futures_contract(symbol, local_symbol)
    else:
        raise Exception(f"Unsupported security type: {sec_type}")

def create_market_order(direction, quantity):
    order = Order()
    order.action = direction
    order.orderType = "MKT"
    order.totalQuantity = quantity
    order.tif = "GTC"  # Good Till Cancel
    order.transmit = True  # Make sure order is transmitted immediately
    return order

# Initialize connection
app = TradeApp()
port = PAPER_PORT if IS_PAPER_TRADING else LIVE_PORT
print(f"🚀 Moon Dev connecting to {'Paper' if IS_PAPER_TRADING else 'Live'} trading on port {port}")
app.connect("127.0.0.1", port, clientId=1)

# Start connection thread
con_thread = threading.Thread(target=websocket_con, daemon=True)
con_thread.start()
time.sleep(1)  # Give time for connection

try:
    # Wait for nextValidId
    timeout = 5
    start_time = time.time()
    while app.nextValidOrderId is None and time.time() - start_time < timeout:
        time.sleep(0.1)
    
    if app.nextValidOrderId is None:
        raise Exception("Timeout waiting for valid order ID")
    
    # Cancel all open orders
    print("🔄 Moon Dev is canceling all open orders...")
    app.reqGlobalCancel()
    time.sleep(1)  # Give time for cancellations
    
    # Request and wait for positions
    print("📊 Moon Dev is fetching all open positions...")
    app.reqPositions()
    
    if not app.positions_loaded.wait(timeout=WAIT_TIME):
        print("⚠️ Timeout waiting for positions data")
    
    # Process positions
    pos_df = app.pos_df
    
    # Drop duplicates based on all columns except Account and Avg cost
    pos_df = pos_df.drop_duplicates(subset=['Symbol', 'SecType', 'Position', 'LocalSymbol'], keep='first')
    
    if len(pos_df) == 0:
        print("✨ No open positions found - Moon Dev is already in cash!")
    else:
        print(f"🔍 Found {len(pos_df)} open position(s) to close:")
        order_id = app.nextValidOrderId
        
        for _, row in pos_df.iterrows():
            ticker = row["Symbol"]
            sec_type = row["SecType"]
            local_symbol = row["LocalSymbol"] if "LocalSymbol" in row else None
            quantity = abs(float(row["Position"]))
            
            if quantity == 0:
                print(f"⚠️ Skipping {ticker} - zero position size")
                continue
                
            direction = "SELL" if float(row["Position"]) > 0 else "BUY"
            
            print(f"📉 Closing {quantity} {'contracts' if sec_type == 'FUT' else 'shares'} of {local_symbol or ticker}")
            contract = get_contract(ticker, sec_type, local_symbol)
            
            # Place the order and wait for fill
            app.order_filled[order_id] = False
            app.placeOrder(order_id, contract, create_market_order(direction, quantity))
            
            # Wait for fill confirmation
            wait_start = time.time()
            while not app.order_filled.get(order_id, False) and time.time() - wait_start < 5:
                time.sleep(0.1)
            
            if app.order_filled.get(order_id, False):
                print(f"✅ Successfully closed position in {local_symbol or ticker}")
            else:
                print(f"⚠️ Order placed but fill not confirmed for {local_symbol or ticker}")
            
            order_id += 1
            time.sleep(0.5)  # Small delay between orders
        
        print("🎉 Moon Dev has initiated closing of all positions!")
        
except Exception as e:
    print(f"❌ Error: {str(e)}")
    
finally:
    time.sleep(2)  # Give time for any pending operations
    app.disconnect()
    print("👋 Moon Dev has disconnected safely - Portfolio should be 100% cash soon!")

