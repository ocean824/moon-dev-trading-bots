'''
LEAPs option strategy 

Hand traders can't really trade options very well because they always turn into short-term options. 
Leaps are a solid way to get a little bit of leverage. It's just hard to do as a human. 
So I'm going to use interactive brokers here in order to build out a leap strategy that can go long or short. 
'''

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from datetime import datetime, timedelta
import pandas as pd
import time
import threading

# Trading Configuration
SYMBOL = "NVDA"           # Default symbol to trade
MONTHS_OUT = 6           # Target months out for LEAP options
MAX_WAIT_TIME = 10        # Maximum time to wait for option chain data in seconds
USE_DELAYED_DATA = True   # Use delayed data instead of real-time
NUM_STRIKES = 15          # Number of strikes to show (N/2 above and N/2 below current price)

# Connection Configuration
PAPER_PORT = 7497         # Paper trading port
LIVE_PORT = 7496          # Live trading port
IS_PAPER_TRADING = True   # Set to False for live trading

class LeapOptionsTrader(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
        self.option_data = []
        self.chain_received = False
        self.nextValidOrderId = None
        self.connected = False
        self.contract_details = None
        self.contract_details_received = False
        self.current_price = None
        self.price_received = False
        self.options_prices = {}  # Store option prices
        self.current_reqId = 0  # For tracking market data requests
        print("🌙 Moon Dev's LEAP Options Trader initialized! 🚀")
        
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        """Error handling with proper signature matching IB API"""
        # Ignore certain non-critical errors
        ignored_errors = [2104, 2106, 2158]  # Normal disconnection, already connected, etc
        delayed_data_errors = [10091, 10167]  # Delayed data related messages
        
        if errorCode not in ignored_errors:
            if errorCode in delayed_data_errors:
                # Mark the request as received if we get delayed data message
                if reqId in self.options_prices:
                    self.options_prices[reqId]['received'] = True
            elif errorCode in [200, 300, 322]:  # Common errors with delayed data
                pass  # Ignore these errors as they're common with delayed data
            else:
                print(f"❌ Error {errorCode}: {errorString}")
            
    def nextValidId(self, orderId):
        super().nextValidId(orderId)
        self.nextValidOrderId = orderId
        self.connected = True
        print(f"🎯 Moon Dev's Next Valid Order ID: {orderId}")

    def tickPrice(self, reqId, tickType, price, attrib):
        """Handle price data"""
        if reqId == 2:  # Stock price
            if (tickType == 4 or  # Last price
                tickType == 68 or # Delayed last price
                tickType == 67):  # Delayed bid price
                self.current_price = price
                self.price_received = True
                print(f"📈 Got {'delayed' if tickType in [67, 68] else 'real-time'} price: ${price}")
        else:  # Option prices
            try:
                if reqId in self.options_prices:  # Check if reqId exists
                    # Handle delayed data types
                    if tickType in [66, 67]:  # Delayed bid
                        self.options_prices[reqId]['bid'] = price
                        self.options_prices[reqId]['received'] = True
                    elif tickType in [69, 70]:  # Delayed ask
                        self.options_prices[reqId]['ask'] = price
                        self.options_prices[reqId]['received'] = True
                    elif tickType in [68, 71]:  # Delayed last
                        self.options_prices[reqId]['last'] = price
                        self.options_prices[reqId]['received'] = True
            except Exception as e:
                print(f"\n❌ Error processing tick: {str(e)}")

    def contractDetails(self, reqId, contractDetails):
        """Called when contract details are received"""
        self.contract_details = contractDetails
        print(f"📝 Got contract details for {contractDetails.contract.symbol}")
        
    def contractDetailsEnd(self, reqId):
        """Called when all contract details have been received"""
        self.contract_details_received = True
        print("✅ Contract details request complete!")
        
    def securityDefinitionOptionParameter(self, reqId, exchange, underlyingConId, tradingClass,
                                        multiplier, expirations, strikes):
        """Handle the option chain data"""
        target_date = datetime.now() + timedelta(days=MONTHS_OUT * 30)
        
        # Find the expiration closest to but AFTER our target date
        valid_expiration = None
        min_diff = float('inf')
        
        for exp in expirations:
            exp_date = datetime.strptime(exp, '%Y%m%d')
            # Only consider dates after our target
            if exp_date >= target_date:
                diff = abs((exp_date - target_date).days)
                if diff < min_diff:
                    min_diff = diff
                    valid_expiration = exp
        
        if valid_expiration and exchange == "SMART":  # Only store SMART exchange data
            self.option_data = {
                'exchange': exchange,
                'expirations': [valid_expiration],  # Only store the closest expiration
                'strikes': sorted(strikes),
                'tradingClass': tradingClass,
                'multiplier': multiplier
            }
            exp_date = datetime.strptime(valid_expiration, '%Y%m%d')
            months = round((exp_date - datetime.now()).days / 30, 1)
            print(f"🎯 Found LEAP expiration {exp_date.strftime('%Y-%m-%d')} ({months} months out)")
            print(f"📈 Trading Class: {tradingClass}")
        
    def securityDefinitionOptionParameterEnd(self, reqId):
        """Called when all option chain data has been received"""
        self.chain_received = True
        print("✨ Option chain data collection complete! Thanks Moon Dev! ✨")

    def get_current_price(self, symbol):
        """Get current stock price"""
        print(f"💰 Getting {'delayed' if USE_DELAYED_DATA else 'real-time'} price for {symbol}")
        
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        
        self.price_received = False
        self.current_price = None
        
        # Request delayed data if specified
        if USE_DELAYED_DATA:
            self.reqMarketDataType(3)  # Switch to delayed data
            print("🕒 Using delayed market data (15-20 minutes delay)")
        else:
            self.reqMarketDataType(1)  # Real-time data
            
        self.reqMktData(2, contract, "", False, False, [])
        
        # Wait for price data
        start_time = time.time()
        while not self.price_received and time.time() - start_time < MAX_WAIT_TIME:
            time.sleep(0.1)
            
        if not self.current_price:
            print("⚠️ Could not get price data. Make sure you have market data permissions.")
            print("💡 Tip: If you don't have a market data subscription, set USE_DELAYED_DATA = True")
            
        return self.current_price

    def get_contract_details(self, symbol):
        """Get contract details for a symbol"""
        print(f"🔎 Getting contract details for {symbol}")
        
        # Create contract object
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        contract.primaryExch = "NASDAQ"  # Add primary exchange
        
        # Reset flags
        self.contract_details = None
        self.contract_details_received = False
        
        # Request contract details
        self.reqContractDetails(1, contract)
        
        # Wait for response
        start_time = time.time()
        while not self.contract_details_received and time.time() - start_time < MAX_WAIT_TIME:
            time.sleep(0.1)
            
        if not self.contract_details:
            print(f"⚠️ Could not get contract details for {symbol}")
            return None
            
        return self.contract_details
        
    def get_option_price(self, symbol, strike, right, expiration):
        """Get option price data"""
        try:
            # Cancel previous request if exists
            if self.current_reqId > 0:
                try:
                    self.cancelMktData(self.current_reqId)
                except:
                    pass
                time.sleep(0.5)  # Increased delay between requests
                
            self.current_reqId += 1
            reqId = self.current_reqId
            
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "OPT"
            contract.exchange = "SMART"
            contract.currency = "USD"
            contract.strike = strike
            contract.right = right
            contract.lastTradeDateOrContractMonth = expiration
            contract.multiplier = self.option_data.get('multiplier', "100")
            
            # Use trading class from option chain data
            if self.option_data and 'tradingClass' in self.option_data:
                contract.tradingClass = self.option_data['tradingClass']
            
            self.options_prices[reqId] = {
                'contract': contract,
                'bid': None,  # Initialize as None to track if we got data
                'ask': None,
                'last': None,
                'received': False
            }
            
            # Request delayed data
            self.reqMarketDataType(3)  # Switch to delayed data
            time.sleep(0.1)  # Small delay after switching market data type
            
            # Request generic ticks for delayed data
            generic_ticks = "100,101,104,106,165,221,225,233,236,258,293,294,295,318"
            self.reqMktData(reqId, contract, generic_ticks, False, False, [])
            
            # Wait for price data with longer timeout
            start_time = time.time()
            timeout = 5  # Increased timeout for delayed data
            while not self.options_prices[reqId]['received'] and time.time() - start_time < timeout:
                time.sleep(0.1)
                
            # If we didn't get any data, try one more time
            if not self.options_prices[reqId]['received']:
                time.sleep(0.5)  # Wait a bit before retrying
                self.reqMktData(reqId, contract, generic_ticks, False, False, [])
                start_time = time.time()
                while not self.options_prices[reqId]['received'] and time.time() - start_time < timeout:
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"\n❌ Error getting price for {symbol} {right} {strike} {expiration}: {str(e)}")
            return {'bid': None, 'ask': None, 'last': None, 'received': False}
            
        finally:
            # Always try to cancel the request
            try:
                self.cancelMktData(reqId)
                time.sleep(0.1)  # Small delay after canceling
            except:
                pass
            
        # Return actual values or 0 if None
        return {
            'bid': self.options_prices[reqId]['bid'] if self.options_prices[reqId]['bid'] is not None else 0,
            'ask': self.options_prices[reqId]['ask'] if self.options_prices[reqId]['ask'] is not None else 0,
            'last': self.options_prices[reqId]['last'] if self.options_prices[reqId]['last'] is not None else 0,
            'received': self.options_prices[reqId]['received']
        }
        
    def get_leap_options(self, symbol):
        """Request option chain data for a given symbol"""
        if not self.connected:
            print("⚠️ Not connected to TWS/IB Gateway!")
            return None
            
        print(f"🔍 Fetching LEAP options for {symbol} ({MONTHS_OUT} months out)")
        
        # Get current stock price
        current_price = self.get_current_price(symbol)
        if not current_price:
            return None
            
        # First get contract details
        contract_details = self.get_contract_details(symbol)
        if not contract_details:
            return None
            
        # Reset data containers and ensure we're using delayed data
        self.option_data = []
        self.chain_received = False
        self.current_reqId = 0  # Reset request ID counter
        self.options_prices = {}  # Reset options prices
        self.reqMarketDataType(3)  # Ensure we're using delayed data
        time.sleep(0.1)  # Small delay after switching market data type
        
        # Request option chain using contract ID
        self.reqSecDefOptParams(0, symbol, "", "STK", contract_details.contract.conId)
        
        # Wait for data
        start_time = time.time()
        while not self.chain_received and time.time() - start_time < MAX_WAIT_TIME:
            time.sleep(0.1)
            
        if not self.chain_received:
            print("⚠️ Timeout waiting for option chain data!")
            return None
            
        # Create DataFrame with relevant strikes
        if self.option_data:
            all_strikes = sorted(self.option_data['strikes'])
            
            # Find the strikes closest to current price
            strikes_array = pd.Series(all_strikes)
            closest_idx = (strikes_array - current_price).abs().argsort()
            
            # Get N/2 strikes above and below current price
            half_num = NUM_STRIKES // 2
            
            # Find center index (closest to current price)
            center_idx = closest_idx[0]
            center_strike = all_strikes[center_idx]
            
            # Get indices below center
            start_idx = max(0, center_idx - half_num)
            # Get indices above center
            end_idx = min(len(all_strikes), center_idx + half_num + (NUM_STRIKES % 2))
            
            # Get the exact number of strikes we want
            relevant_strikes = all_strikes[start_idx:end_idx]
            if len(relevant_strikes) > NUM_STRIKES:
                relevant_strikes = relevant_strikes[:NUM_STRIKES]
            
            print(f"🎯 Moon Dev found the {len(relevant_strikes)} most relevant strikes around ${current_price}:")
            for strike in relevant_strikes:
                distance = round((strike - current_price) / current_price * 100, 1)
                print(f"   • ${strike} ({'+' if distance > 0 else ''}{distance}%)")
            
            data = []
            total_options = len(relevant_strikes) * len(self.option_data['expirations']) * 2  # Both calls and puts
            processed = 0
            
            for expiration in self.option_data['expirations']:
                exp_date = datetime.strptime(expiration, '%Y%m%d')
                months_out = (exp_date - datetime.now()).days / 30
                
                # Include both CALL and PUT options
                for strike in relevant_strikes:
                    processed += 2  # One call, one put
                    print(f"\r📊 Processing option prices... {processed}/{total_options}", end="")
                    
                    # Get CALL price
                    call_price = self.get_option_price(symbol, strike, "C", expiration)
                    # Get PUT price
                    put_price = self.get_option_price(symbol, strike, "P", expiration)
                    
                    # Add CALL
                    data.append({
                        'Expiration': exp_date.strftime('%Y-%m-%d'),
                        'Strike': strike,
                        'Months Out': round(months_out, 1),
                        'Type': 'CALL',
                        'Distance': round((strike - current_price) / current_price * 100, 1),  # % from current price
                        'Bid': call_price['bid'] if call_price['bid'] else 0,
                        'Ask': call_price['ask'] if call_price['ask'] else 0,
                        'Last': call_price['last'] if call_price['last'] else 0
                    })
                    # Add PUT
                    data.append({
                        'Expiration': exp_date.strftime('%Y-%m-%d'),
                        'Strike': strike,
                        'Months Out': round(months_out, 1),
                        'Type': 'PUT',
                        'Distance': round((strike - current_price) / current_price * 100, 1),  # % from current price
                        'Bid': put_price['bid'] if put_price['bid'] else 0,
                        'Ask': put_price['ask'] if put_price['ask'] else 0,
                        'Last': put_price['last'] if put_price['last'] else 0
                    })
            
            print("\n")  # Clear the progress line
            
            df = pd.DataFrame(data)
            
            # Sort and organize the data
            df = df.sort_values(['Type', 'Months Out', 'Strike']).reset_index(drop=True)
            
            # Add a visual separator between CALLs and PUTs
            call_df = df[df['Type'] == 'CALL'].copy()
            put_df = df[df['Type'] == 'PUT'].copy()
            
            # Format the columns
            for df in [call_df, put_df]:
                df['Distance'] = df['Distance'].apply(lambda x: f"+{x}%" if x > 0 else f"{x}%")
                df['Bid'] = df['Bid'].apply(lambda x: f"${x:.2f}")
                df['Ask'] = df['Ask'].apply(lambda x: f"${x:.2f}")
                df['Last'] = df['Last'].apply(lambda x: f"${x:.2f}")
            
            return {'CALLS': call_df, 'PUTS': put_df}
            
        return None

def websocket_con():
    app.run()

def main():
    """Test function"""
    global app
    
    # Initialize connection
    app = LeapOptionsTrader()
    port = PAPER_PORT if IS_PAPER_TRADING else LIVE_PORT
    print(f"🚀 Moon Dev connecting to {'Paper' if IS_PAPER_TRADING else 'Live'} trading on port {port}")
    app.connect("127.0.0.1", port, clientId=1)

    # Start connection thread
    con_thread = threading.Thread(target=websocket_con, daemon=True)
    con_thread.start()
    
    try:
        # Wait for connection and nextValidId
        timeout = 15  # Increased timeout for better connection chance
        start_time = time.time()
        while not app.connected and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        if not app.connected:
            raise Exception("❌ Could not connect to TWS/IB Gateway")
            
        # Get LEAP options data
        option_data = app.get_leap_options(SYMBOL)
        if isinstance(option_data, dict):
            print(f"\n📊 LEAP Options for {SYMBOL} (sorted by months out)")
            print(f"Only showing strikes within 20% of current price")
            print(f"Distance column shows % away from current price")
            
            # Print CALLS
            print("\n🟢 Moon Dev's Curated CALL Options 📈:")
            print("=" * 80)
            pd.set_option('display.max_rows', None)
            print(option_data['CALLS'])
            
            # Print PUTS
            print("\n🔴 Moon Dev's Curated PUT Options 📉:")
            print("=" * 80)
            print(option_data['PUTS'])
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("💡 Tips:")
        print("   1. Check TWS is running and connected")
        print("   2. Verify market data permissions")
        print("   3. Check if options trading is enabled")
        print("   4. Verify the symbol is valid")
        
    finally:
        time.sleep(2)  # Give time for any pending operations
        app.disconnect()
        print("👋 Moon Dev has disconnected safely")

if __name__ == "__main__":
    main()
