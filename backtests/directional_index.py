"""
https://commodity.com/technical-analysis/dmi/
Moon Dev's DMI Strategy 🎯
"""

import talib 
import pandas as pd 
from backtesting import Backtest, Strategy 
from backtesting.lib import crossover 
import os
import time

print("🌙 Moon Dev's DMI Strategy Loading... 🚀")

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

class DMIStrategy(Strategy):
    """
    Directional Movement Index (DMI) Strategy
    Uses DMI crossovers with ADX filter for trend strength
    """
    dmi_period = 14 
    adx_threshold = 25
    risk_multiplier = 2
    min_stop_distance = 0.002  # 0.2% minimum stop distance

    def init(self):
        print("🎯 Moon Dev's Strategy Initialization")
        # calculate dmi+ dmi - and adx 
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, self.dmi_period)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, self.dmi_period)
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, self.dmi_period)
        print("✨ DMI Indicators Created Successfully!")

    def next(self):
        price = self.data.Close[-1]

        if price <= 0:
            print(f"⚠️ Warning: Invalid price detected: {price}")
            return

        # Calculate stop loss and take profit levels
        sl_distance = self.min_stop_distance * price
        tp_distance = sl_distance * self.risk_multiplier

        # entry conditions with strong trend
        if crossover(self.plus_di, self.minus_di) and self.adx[-1] > self.adx_threshold:
            sl_price = price - sl_distance
            tp_price = price + tp_distance
            print(f"🚀 LONG Entry - Price: {price:.4f}, SL: {sl_price:.4f}, TP: {tp_price:.4f}, ADX: {self.adx[-1]:.2f}")
            self.buy(sl=sl_price, tp=tp_price)

        elif crossover(self.minus_di, self.plus_di) and self.adx[-1] > self.adx_threshold:
            sl_price = price + sl_distance
            tp_price = price - tp_distance
            print(f"🔻 SHORT Entry - Price: {price:.4f}, SL: {sl_price:.4f}, TP: {tp_price:.4f}, ADX: {self.adx[-1]:.2f}")
            self.sell(sl=sl_price, tp=tp_price)

        # exit conditions
        if self.position.is_long and crossover(self.minus_di, self.plus_di):
            print(f"🎯 Closing LONG position at {price:.4f}")
            self.position.close()
        elif self.position.is_short and crossover(self.plus_di, self.minus_di):
            print(f"🎯 Closing SHORT position at {price:.4f}")
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
    bt = Backtest(data, DMIStrategy, cash=cash, commission=commission, exclusive_orders=True)
    
    print("\n🎮 Starting backtest...")
    stats = bt.run()
    
    # Print full stats
    print("\n🎭 Moon Dev's Backtest Results 🎭")
    print(stats)
    
    print("\n📈 Showing plot...")
    # Create plot and show in browser
    bt.plot(open_browser=True)
    
    # Wait a moment for the browser to open
    time.sleep(2)
    
    # Clean up the HTML file
    try:
        os.remove("DMIStrategy.html")
        print("🧹 Cleaned up plot file")
    except:
        pass
    
    print("✨ Moon Dev's DMI Strategy Complete! ✨")
    
    return stats

if __name__ == "__main__":
    # Example usage with different data sources
    crypto_data = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/ETH-6h-1000wks-data.csv'
    stats = run_backtest(crypto_data)





# load data 
