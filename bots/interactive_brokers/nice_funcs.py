from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading
import time
import queue
import pandas as pd
import os
from datetime import datetime
import pytz

# Connection Configuration
PAPER_PORT = 7497        # Paper trading port
LIVE_PORT = 7496         # Live trading port
IS_PAPER_TRADING = True  # Set to False for live trading
DATA_PATH = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/IB_data"

# Timeout Configuration
BASE_TIMEOUT = 12000        # Base timeout in seconds for data requests
TIMEOUT_PER_DAY = 2      # Additional seconds of timeout per day of data
CONNECT_TIMEOUT = 5      # Timeout for initial connection

class IBApi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.nextValidOrderId = None
        self.data = queue.Queue()
        self.contract_details = []
        self.bid_ask = {}
        self.ohlcv_data = {}
        self.historical_data_end = False
        self.error_messages = []  # Store error messages
        
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        error_msg = f"Error {errorCode}: {errorString}"
        self.error_messages.append(error_msg)  # Store the error
        if errorCode != 2106 and errorCode != 2104 and errorCode != 2158:
            print(f"❌ {error_msg}")

    def nextValidId(self, orderId):
        super().nextValidId(orderId)
        self.nextValidOrderId = orderId
        print(f"🔑 Moon Dev's Next Valid Order ID: {orderId}")

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, 
                   permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        if status == "Cancelled":
            print(f"✨ Order {orderId} has been cancelled by Moon Dev!")
            
    def openOrder(self, orderId, contract, order, orderState):
        self.data.put({"orderId": orderId, "contract": contract, "order": order})
        
    def tickPrice(self, reqId, tickType, price, attrib):
        if tickType == 1:  # Bid
            if reqId not in self.bid_ask:
                self.bid_ask[reqId] = {"bid": 0, "ask": 0}
            self.bid_ask[reqId]["bid"] = price
        elif tickType == 2:  # Ask
            if reqId not in self.bid_ask:
                self.bid_ask[reqId] = {"bid": 0, "ask": 0}
            self.bid_ask[reqId]["ask"] = price

    def historicalData(self, reqId, bar):
        if reqId not in self.ohlcv_data:
            self.ohlcv_data[reqId] = []
            print(f"🎬 Starting to receive data for request {reqId}...")
        
        self.ohlcv_data[reqId].append({
            'date': bar.date,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume
        })
        
        # Print progress every 100 bars
        if len(self.ohlcv_data[reqId]) % 100 == 0:
            print(f"📊 Received {len(self.ohlcv_data[reqId])} bars so far...")

    def historicalDataEnd(self, reqId, start, end):
        print(f"✨ Moon Dev has received all historical data!")
        self.historical_data_end = True

def connect_ib(port=7497):
    """Connect to Interactive Brokers TWS/Gateway
    
    Args:
        port (int): Port number (7497 for paper, 7496 for live)
        
    Returns:
        tuple: (app instance, connection thread)
    """
    app = IBApi()
    app.connect("127.0.0.1", port, clientId=1)
    
    con_thread = threading.Thread(target=lambda: app.run(), daemon=True)
    con_thread.start()
    time.sleep(1)  # Give time for connection
    
    timeout = 5
    start_time = time.time()
    while app.nextValidOrderId is None and time.time() - start_time < timeout:
        time.sleep(0.1)
        
    if app.nextValidOrderId is None:
        raise Exception("🔴 Timeout waiting for valid order ID")
        
    return app, con_thread

def create_contract(symbol, sec_type="STK", exchange="SMART", currency="USD"):
    """Create an IB contract object
    
    Args:
        symbol (str): Trading symbol
        sec_type (str): Security type (STK, FUT, etc)
        exchange (str): Exchange name
        currency (str): Currency code
        
    Returns:
        Contract: IB Contract object
    """
    contract = Contract()
    contract.symbol = symbol
    contract.secType = sec_type
    contract.exchange = exchange
    contract.currency = currency
    return contract

def cancel_all_orders(port=7497):
    """Cancel all open orders
    
    Args:
        port (int): Port number (7497 for paper, 7496 for live)
    """
    print("🔄 Moon Dev is canceling all open orders...")
    app, _ = connect_ib(port)
    
    try:
        app.reqGlobalCancel()
        time.sleep(1)  # Give time for cancellations
        print("✅ All orders cancelled successfully!")
        
    except Exception as e:
        print(f"❌ Error cancelling orders: {str(e)}")
        
    finally:
        app.disconnect()
        print("👋 Moon Dev has disconnected safely!")

def cancel_symbol_orders(symbol, port=7497):
    """Cancel all open orders for a specific symbol
    
    Args:
        symbol (str): Trading symbol
        port (int): Port number (7497 for paper, 7496 for live)
    """
    print(f"🔄 Moon Dev is canceling all orders for {symbol}...")
    app, _ = connect_ib(port)
    
    try:
        # Get all open orders
        app.reqAllOpenOrders()
        time.sleep(1)  # Wait for orders to arrive
        
        # Process open orders
        cancelled_count = 0
        while not app.data.empty():
            order_data = app.data.get()
            if order_data["contract"].symbol == symbol:
                app.cancelOrder(order_data["orderId"], "")  # Empty string for manualCancelOrderTime
                cancelled_count += 1
                print(f"✨ Cancelled order {order_data['orderId']} for {symbol}")
        
        if cancelled_count > 0:
            print(f"✅ Successfully cancelled {cancelled_count} orders for {symbol}!")
        else:
            print(f"ℹ️ No open orders found for {symbol}")
        
    except Exception as e:
        print(f"❌ Error cancelling orders for {symbol}: {str(e)}")
        
    finally:
        app.disconnect()
        print("👋 Moon Dev has disconnected safely!")

def get_bid_ask(symbol, port=7497):
    """Get current bid/ask prices for a symbol
    
    Args:
        symbol (str): Trading symbol
        port (int): Port number (7497 for paper, 7496 for live)
        
    Returns:
        dict: Dictionary with bid and ask prices
    """
    print(f"🔍 Moon Dev is fetching bid/ask for {symbol}...")
    app, _ = connect_ib(port)
    
    try:
        contract = create_contract(symbol)
        req_id = app.nextValidOrderId
        app.reqMktData(req_id, contract, "", False, False, [])
        
        # Wait for bid/ask data
        timeout = 5
        start_time = time.time()
        while (req_id not in app.bid_ask or 
               app.bid_ask[req_id]["bid"] == 0 or 
               app.bid_ask[req_id]["ask"] == 0) and time.time() - start_time < timeout:
            time.sleep(0.1)
            
        if req_id in app.bid_ask:
            bid_ask = app.bid_ask[req_id]
            print(f"💰 {symbol} Bid: ${bid_ask['bid']:.2f} Ask: ${bid_ask['ask']:.2f}")
            return bid_ask
        else:
            print(f"⚠️ Could not get bid/ask for {symbol}")
            return {"bid": 0, "ask": 0}
            
    except Exception as e:
        print(f"❌ Error getting bid/ask for {symbol}: {str(e)}")
        return {"bid": 0, "ask": 0}
        
    finally:
        app.disconnect()
        print("👋 Moon Dev has disconnected safely!")

def get_ohlcv(symbol, duration="1 D", bar_size="1 min", port=7497):
    """Get OHLCV (Open, High, Low, Close, Volume) data for a symbol and save to file
    
    Args:
        symbol (str): Trading symbol
        duration (str): Time duration (e.g., "1 D", "5 D", "1 M")
        bar_size (str): Bar size (e.g., "1 min", "5 mins", "1 hour", "1 day")
        port (int): Port number (7497 for paper, 7496 for live)
        
    Returns:
        pandas.DataFrame: DataFrame containing OHLCV data
    """
    print(f"📊 Moon Dev is fetching {duration} of {bar_size} OHLCV data for {symbol}...")
    app, _ = connect_ib(port)
    
    try:
        contract = create_contract(symbol)
        req_id = app.nextValidOrderId
        
        print(f"🔄 Requesting historical data for {symbol}...")
        print(f"📋 Contract details: {contract.symbol} {contract.secType} {contract.exchange}")
        
        # Reset historical data end flag and error messages
        app.historical_data_end = False
        app.error_messages = []
        
        # Calculate appropriate timeout based on duration
        duration_value = int(''.join(filter(str.isdigit, duration)))
        timeout = max(BASE_TIMEOUT, duration_value * TIMEOUT_PER_DAY)  # Scale timeout with duration
        print(f"⏳ Setting timeout to {timeout} seconds for {duration} of data...")
        
        # Request historical data
        app.reqHistoricalData(
            reqId=req_id,
            contract=contract,
            endDateTime="",  # Empty for latest data
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=1,  # Regular Trading Hours only
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )
        
        # Wait for data with progress updates
        start_time = time.time()
        last_count = 0
        
        while not app.historical_data_end and time.time() - start_time < timeout:
            current_time = time.time()
            elapsed = current_time - start_time
            
            if req_id in app.ohlcv_data:
                current_count = len(app.ohlcv_data[req_id])
                if current_count > last_count:
                    last_count = current_count
                    if current_count % 10 == 0:  # Update progress every 10 bars
                        print(f"⏳ {elapsed:.1f}s elapsed, received {current_count} bars...")
            
            time.sleep(0.1)
            
        # Check if we got any error messages
        if app.error_messages:
            print("❌ Errors received during data fetch:")
            for error in app.error_messages:
                print(f"   - {error}")
                
        if not app.historical_data_end:
            print("⚠️ Timeout waiting for historical data!")
            
        if req_id in app.ohlcv_data:
            data = app.ohlcv_data[req_id]
            print(f"💫 Got {len(data)} bars of data for {symbol}")
            
            if len(data) == 0:
                print("⚠️ Received empty data set!")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            print(f"📈 Data range: {df['date'].iloc[0]} to {df['date'].iloc[-1]}")
            
            # Clean and convert date column
            def clean_date(date_str):
                # Remove timezone info if present
                if 'America' in date_str:
                    date_str = date_str.split(' America')[0]
                return date_str
                
            df['date'] = df['date'].apply(clean_date)
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d %H:%M:%S')
            
            # Sort by date
            df = df.sort_values('date')
            
            # Create directory if it doesn't exist
            os.makedirs(DATA_PATH, exist_ok=True)
            
            # Create filename with current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            duration_str = duration.replace(" ", "")
            bar_size_str = bar_size.replace(" ", "")
            filename = f"{symbol}_{duration_str}_{bar_size_str}_{timestamp}.csv"
            filepath = os.path.join(DATA_PATH, filename)
            
            # Save to CSV
            df.to_csv(filepath, index=False)
            print(f"💾 Moon Dev saved data to: {filepath}")
            
            # Print the latest bar
            if not df.empty:
                latest = df.iloc[-1]
                print(f"📈 Latest Bar - O: ${latest['open']:.2f} H: ${latest['high']:.2f} L: ${latest['low']:.2f} C: ${latest['close']:.2f} V: {latest['volume']}")
            
            return df
        else:
            print(f"⚠️ No data received for {symbol}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"❌ Error getting OHLCV data for {symbol}: {str(e)}")
        print(f"🔍 Error type: {type(e).__name__}")
        import traceback
        print("🔍 Traceback:")
        print(traceback.format_exc())
        return pd.DataFrame()
        
    finally:
        app.disconnect()
        print("👋 Moon Dev has disconnected safely!")

def is_market_hours():
    """Check if current time is within market hours (9:30 AM - 4:00 PM Eastern)
    
    Returns:
        bool: True if within market hours, False otherwise
    """
    # Get current time in Eastern timezone
    et = pytz.timezone('US/Eastern')
    now = datetime.now(et)
    
    # Check if it's a weekday (0 = Monday, 6 = Sunday)
    if now.weekday() >= 5:
        print(f"🌙 Market is closed - It's {now.strftime('%A')}")
        return False
    
    # Create datetime objects for market open and close
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    
    # Check if current time is within market hours
    is_open = market_open <= now <= market_close
    
    if is_open:
        time_left = market_close - now
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        print(f"🌟 Market is OPEN! {hours}h {minutes}m until close")
    else:
        if now < market_open:
            time_to_open = market_open - now
            hours, remainder = divmod(time_to_open.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            print(f"🌅 Market is closed - Opens in {hours}h {minutes}m")
        else:
            next_open = market_open + pd.Timedelta(days=1)
            if next_open.weekday() >= 5:  # If next day is weekend
                days_to_add = 8 - next_open.weekday()  # Calculate days until Monday
                next_open = market_open + pd.Timedelta(days=days_to_add)
            time_to_open = next_open - now
            hours, remainder = divmod(time_to_open.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            print(f"🌙 Market is closed - Opens in {time_to_open.days}d {hours}h {minutes}m")
    
    return is_open

# Example usage:
if __name__ == "__main__":
    #Test cancel all orders
    #cancel_all_orders()
    
    # Test cancel symbol orders
    #cancel_symbol_orders("ROKU")
    
    # Test get bid/ask
    #prices = get_bid_ask("AAPL")
    
    # Test get OHLCV data
    data = get_ohlcv("AAPL", duration="30 Y", bar_size="15 mins")
    
    # # Test market hours
    # is_open = is_market_hours()
    # print(f"Market open: {is_open}")
    # pass
