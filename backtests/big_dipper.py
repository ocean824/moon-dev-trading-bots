'''
Big Dipper Strategy by Moon Dev 🌙
Accumulation strategy that buys on dips with configurable position sizing
'''
import time 
import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import talib
import os

print("🌙 Moon Dev's Big Dipper Strategy Loading... 🚀")

def normalize_data(df):
    """Normalize different data formats to a standard format"""
    print("🔄 Normalizing data format...")
    
    column_maps = {
        'Open': ['Open', 'open'],
        'High': ['High', 'high'],
        'Low': ['Low', 'low'],
        'Close': ['Close', 'close'],
        'Volume': ['Volume', 'volume']
    }
    
    normalized_df = pd.DataFrame()
    
    for standard_name, possible_names in column_maps.items():
        found_col = next((col for col in possible_names if col in df.columns), None)
        if found_col:
            normalized_df[standard_name] = df[found_col]
        else:
            raise ValueError(f"Could not find a column matching {standard_name} in the data")
    
    if isinstance(df.index, pd.DatetimeIndex):
        normalized_df.index = df.index
    elif 'Date' in df.columns:
        normalized_df.index = pd.to_datetime(df['Date'])
    elif 'datetime' in df.columns:
        normalized_df.index = pd.to_datetime(df['datetime'])
    else:
        raise ValueError("Could not find date information in the data")
        
    print(f"✅ Data normalized successfully with columns: {list(normalized_df.columns)}")
    return normalized_df

class BigDipperStrategy(Strategy):
    # Define strategy parameters
    dip_percentage = 5.0  # Percentage drop to trigger a buy
    position_size_percent = 5.0  # Percentage of capital to use per trade
    take_profit_percent = 40.0  # Percentage gain to trigger take profit
    
    def init(self):
        print("🎯 Moon Dev's Big Dipper Strategy Initialization")
        print(f"🔧 Parameters: Dip={self.dip_percentage}%, Position Size={self.position_size_percent}%, TP={self.take_profit_percent}%")
        
        # Calculate rolling high for dip measurement
        self.rolling_high = self.I(lambda x: pd.Series(x).rolling(window=20).max(), self.data.High)
        
        # Calculate percentage drop from rolling high
        self.dip_size = self.I(lambda: ((self.rolling_high - self.data.Close) / self.rolling_high) * 100)
        
        # Track our positions and their entry prices
        self.positions = []  # List of (size, entry_price) tuples
        
        print("✨ Moon Dev's Indicators Created Successfully!")

    def next(self):
        price = self.data.Close[-1]
        
        # Skip if price is invalid
        if price <= 0:
            print(f"⚠️ Warning: Invalid price detected: {price}")
            return
        
        # Check existing positions for take profit
        new_positions = []
        total_position_size = sum(pos[0] for pos in self.positions) if self.positions else 0
        
        for pos_size, entry_price in self.positions:
            current_profit = ((price - entry_price) / entry_price) * 100
            if current_profit >= self.take_profit_percent:
                if not hasattr(self, '_optimization_in_progress'):
                    print(f"🎯 TAKE PROFIT Hit!")
                    print(f"   Entry: ${entry_price:.2f}")
                    print(f"   Exit: ${price:.2f}")
                    print(f"   Profit: {current_profit:.2f}%")
                    print(f"   Size: {pos_size}")
                
                # Calculate what percentage of our total position this trade represents
                if total_position_size > 0:
                    pos_percentage = pos_size / total_position_size
                    self.position.close(pos_percentage)
            else:
                new_positions.append((pos_size, entry_price))
        self.positions = new_positions
        
        # Calculate current dip size
        current_dip = self.dip_size[-1]
        
        # Calculate position size based on current equity
        position_value = self.equity * (self.position_size_percent / 100)
        position_size = position_value / price
        # Round to whole units
        position_size = round(position_size)
        
        # Buy when we see a dip of specified percentage
        if current_dip >= self.dip_percentage and position_size > 0:
            if not hasattr(self, '_optimization_in_progress'):
                print(f"🎯 BUY Signal Detected!")
                print(f"   Price: ${price:.2f}")
                print(f"   Dip Size: {current_dip:.2f}%")
                print(f"   Position Value: ${position_value:.2f}")
                print(f"   Position Size (units): {position_size}")
            
            # Execute the buy
            self.buy(size=position_size)
            
            # Track this position
            self.positions.append((position_size, price))
            
            if not hasattr(self, '_optimization_in_progress'):
                print(f"   Total Positions: {len(self.positions)}")
                print(f"   Average Entry: ${sum(p[0]*p[1] for p in self.positions)/sum(p[0] for p in self.positions):.2f}")

print("🔄 Loading data...")
# Load in the data 
data = pd.read_csv('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-104wks-data.csv')

# Normalize the data to handle different formats
data = normalize_data(data)

print(f"📈 Data loaded: {len(data)} candles from {data.index[0]} to {data.index[-1]}")
print(f"💰 Price range: ${data['Low'].min():.4f} - ${data['High'].max():.4f}")

bt = Backtest(data, BigDipperStrategy, cash=1000000, commission=0.002, exclusive_orders=True)

print("\n🚀 Running Initial Backtest with Default Parameters...")
print(f"💫 Default Parameters:")
print(f"   Dip Percentage: 5%")
print(f"   Position Size: 5%")
print(f"   Take Profit: 40%")
stats = bt.run()
print("\n🎭 Original Strategy Stats:")
print(stats)
time.sleep(5)

print("\n📈 Generating initial results plot...")
bt.plot()

print("\n🎲 Starting Moon Dev's Strategy Optimizer...")
print("🔍 This might take a while - searching for the perfect combination...")
print("💫 You can review the stats above while optimization runs!")

# Define optimization ranges
optimization_params = {
    'dip_percentage': range(3, 40, 1),  # 3-40% step 1
    'position_size_percent': range(1, 30, 1),  # 1-30% step 1
    'take_profit_percent': range(40, 155, 5)  # 40-150% step 5
}

# Run optimization
optimization_results = bt.optimize(**optimization_params,
                                 maximize='Equity Final [$]')

print("\n🏆 Moon Dev's Optimal Strategy Parameters:")
print(optimization_results._strategy)
print("\n📊 Performance with Optimal Parameters:")
print(optimization_results)

print("✨ Moon Dev's Big Dipper Strategy Complete! ✨")
