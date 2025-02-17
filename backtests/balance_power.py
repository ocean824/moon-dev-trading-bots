'''
Balance of Power (BOP) Strategy 🌊 - Long Only Version
Source: https://forexbee.co/balance-of-power-indicator/
'''

import talib 
import pandas as pd 
from backtesting import Backtest, Strategy 
from backtesting.lib import crossover 
import os

print("🌙 Moon Dev's Long-Only BOP Strategy Loading... 🚀")

def normalize_data(df):
    """Normalize different data formats to a standard format"""
    print("🔄 Normalizing data format...")
    
    # Create a mapping of expected columns to possible column names
    column_maps = {
        'Open': ['Open', 'open'],
        'High': ['High', 'high'],
        'Low': ['Low', 'low'],
        'Close': ['Close', 'close'],
        'Volume': ['Volume', 'volume']
    }
    
    # Create a new DataFrame with standardized column names
    normalized_df = pd.DataFrame()
    
    for standard_name, possible_names in column_maps.items():
        # Find the first matching column name that exists in the DataFrame
        found_col = next((col for col in possible_names if col in df.columns), None)
        if found_col:
            normalized_df[standard_name] = df[found_col]
        else:
            raise ValueError(f"Could not find a column matching {standard_name} in the data")
    
    # Handle different date formats
    if isinstance(df.index, pd.DatetimeIndex):
        normalized_df.index = df.index
    elif 'Date' in df.columns:
        normalized_df.index = pd.to_datetime(df['Date'])
    elif 'datetime' in df.columns:
        normalized_df.index = pd.to_datetime(df['datetime'])
    elif 'Datetime' in df.columns:
        normalized_df.index = pd.to_datetime(df['Datetime'])
    else:
        raise ValueError("Could not find date information in the data")
        
    print(f"✅ Data normalized successfully with columns: {list(normalized_df.columns)}")
    return normalized_df

class BOPStrategy(Strategy):
    risk_multiplier = 2
    min_stop_distance = 0.002  # 0.2% minimum stop distance
    bop_threshold = -0.5  # Threshold for strong bullish momentum

    def init(self):
        print("🎯 Moon Dev's Strategy Initialization")
        # calculate the balance of power BOP 
        self.bop = self.I(talib.BOP, self.data.Open, self.data.High, self.data.Low, self.data.Close)
        print("✨ BOP Indicator Created Successfully!")

    def next(self):
        price = self.data.Close[-1]

        if price <= 0:
            print(f"⚠️ Warning: Invalid price detected: {price}")
            return

        # Calculate stop loss and take profit levels
        sl_distance = self.min_stop_distance * price
        tp_distance = sl_distance * self.risk_multiplier

        # ensure there is enough data for the strategy logic 
        if len(self.data.Close) < 3:
            return 
        
        # Enhanced long entry conditions 
        long_conditions = (
            (crossover(self.bop, 0) and self.bop[-1] > self.bop_threshold) or  # BOP crosses above 0 with momentum
            (self.bop[-2] < -1 and self.bop[-1] > -1) or  # Strong reversal from oversold
            (self.data.Close[-2] < self.data.Close[-3] and  # Price momentum confirmation
             self.bop[-2] > self.bop[-3] and 
             self.bop[-1] > 0)  # Positive BOP confirmation
        )
        
        # long entry with enhanced conditions
        if long_conditions and not self.position:
            sl_price = price - sl_distance
            tp_price = price + tp_distance
            print(f"🚀 LONG Entry - Price: {price:.4f}, SL: {sl_price:.4f}, TP: {tp_price:.4f}, BOP: {self.bop[-1]:.2f}")
            self.buy(sl=sl_price, tp=tp_price)

        # exit conditions for long
        if self.position and self.position.is_long:
            if self.bop[-1] < -0.2 or (self.bop[-1] < 0 and self.data.Close[-1] < self.data.Close[-2]):
                print(f"🎯 Closing LONG position at {price:.4f}, BOP: {self.bop[-1]:.2f}")
                self.position.close()

def run_backtest(data_path, cash=1000000, commission=0.002):
    print("📊 Loading data...")
    # load in the data 
    data = pd.read_csv(data_path)
    
    # Normalize the data to handle different formats
    data = normalize_data(data)
    
    print(f"📈 Data loaded: {len(data)} candles from {data.index[0]} to {data.index[-1]}")
    print(f"💰 Price range: ${data['Low'].min():.4f} - ${data['High'].max():.4f}")
    
    # Initialize and run backtest
    bt = Backtest(data, BOPStrategy, cash=cash, commission=commission, exclusive_orders=True)
    
    print("\n🎮 Starting backtest...")
    stats = bt.run()
    
    # Print full stats
    print("\n🎭 Moon Dev's Backtest Results 🎭")
    print(stats)
    
    print("\n📈 Showing plot...")
    # Show plot and clean up HTML file
    chart_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/charts/temp_chart.html'
    bt.plot(filename=chart_path)
    
    # Clean up the file after showing
    if os.path.exists(chart_path):
        os.remove(chart_path)
        print("🧹 Cleaned up chart file")
    
    print("✨ Moon Dev's BOP Strategy Complete! ✨")
    
    return stats

if __name__ == "__main__":
    # Example usage with different data sources
    crypto_data = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/BTC-1h-1000wks-data.csv'
    stats = run_backtest(crypto_data)
    print("\n📊 Full Backtest Statistics:")
    print(stats)

