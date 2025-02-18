#get position details


from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading
import time
import pandas as pd

# Connection Configuration
PAPER_PORT = 7497         # Paper trading port
LIVE_PORT = 7496          # Live trading port
IS_PAPER_TRADING = True   # Set to False for live trading

class TradeApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        # Initialize DataFrame with proper dtypes to avoid warnings
        self.pos_df = pd.DataFrame({
            'Symbol': pd.Series(dtype='str'),
            'SecType': pd.Series(dtype='str'),
            'Position': pd.Series(dtype='float'),
            'Market Value': pd.Series(dtype='float'),
            'Unrealized PnL': pd.Series(dtype='float'),
            'Avg Cost': pd.Series(dtype='float')
        })
        self.positions_received = False
        self.position_event = threading.Event()
        self.account = None
        self.total_value = 0.0
        self.total_unrealized_pnl = 0.0

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode not in [2104, 2106, 2158]:  # Filter out common connection messages
            print(f"❌ Error {errorCode}: {errorString}")

    def updatePortfolio(self, contract: Contract, position: float, 
                       marketPrice: float, marketValue: float, 
                       averageCost: float, unrealizedPNL: float, 
                       realizedPNL: float, accountName: str):
        """Called when portfolio position updates are received"""
        
        # Update existing position or add new one
        mask = self.pos_df['Symbol'] == contract.symbol
        if len(self.pos_df[mask]) > 0:
            self.pos_df.loc[mask, 'Position'] = float(position)
            self.pos_df.loc[mask, 'Market Value'] = float(marketValue)
            self.pos_df.loc[mask, 'Unrealized PnL'] = float(unrealizedPNL)
            self.pos_df.loc[mask, 'Avg Cost'] = float(averageCost)
        else:
            new_row = pd.DataFrame([{
                'Symbol': contract.symbol,
                'SecType': contract.secType,
                'Position': float(position),
                'Market Value': float(marketValue),
                'Unrealized PnL': float(unrealizedPNL),
                'Avg Cost': float(averageCost)
            }])
            self.pos_df = pd.concat([self.pos_df, new_row], ignore_index=True)
        
        print(f"💼 Position: {position} {contract.symbol} @ ${marketPrice:.2f} | Value: ${marketValue:.2f} | PnL: ${unrealizedPNL:.2f}")

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        """Called when account values are updated"""
        if key == "NetLiquidation" and currency == "USD":
            self.total_value = float(val)
        elif key == "UnrealizedPnL" and currency == "USD":
            self.total_unrealized_pnl = float(val)

    def accountDownloadEnd(self, accountName: str):
        """Called when all account data has been received"""
        print("🏁 All positions received!")
        self.positions_received = True
        self.position_event.set()

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
    print("🔍 Moon Dev is fetching your positions...")
    app.reqAccountUpdates(True, "")  # Subscribe to account updates
    
    # Wait for positions
    if app.position_event.wait(timeout=10):
        if app.positions_received:
            if not app.pos_df.empty:
                # Format the DataFrame for display
                display_df = app.pos_df.copy()
                pd.options.display.float_format = '${:,.2f}'.format
                
                print("\n📊 Moon Dev's Position Summary:")
                print("=" * 100)
                print(display_df.to_string(index=False))
                print("=" * 100)
                
                # Display account totals
                print(f"\n💰 Total Portfolio Value: ${app.total_value:,.2f}")
                print(f"📈 Total Unrealized P&L: ${app.total_unrealized_pnl:,.2f}")
            else:
                print("📭 No positions found in this account")
    else:
        print("⚠️ Timeout waiting for positions")
            
except Exception as e:
    print(f"❌ Error: {str(e)}")
    
finally:
    # Unsubscribe from account updates
    app.reqAccountUpdates(False, "")
    time.sleep(2)
    app.disconnect()
    print("👋 Moon Dev has disconnected safely")