'''
Absolute Price Oscillator (APO) Divergence Strategy 🌊
Source: https://forexbee.co/absolute-price-oscillator/
'''

import pandas as pd
import talib
from backtesting.lib import crossover 
from backtesting import Backtest, Strategy   
import os

print("🌙 Moon Dev's APO Strategy Loading... 🚀")

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

class APOStrategy(Strategy):
    """
    Absolute Price Oscillator Strategy
    Uses APO crossovers for trend detection
    """
    fast_period = 11
    slow_period = 21
    risk_multiplier = 2
    min_stop_distance = 0.002  # 0.2% minimum stop distance

    def init(self):
        print("🎯 Moon Dev's Strategy Initialization")
        # Calculate APO
        self.apo = self.I(talib.APO,
            self.data.Close,
            fastperiod=self.fast_period,
            slowperiod=self.slow_period,
            matype=0
        )
        print("✨ APO Indicator Created Successfully!")

    def next(self):
        price = self.data.Close[-1]

        if price <= 0:
            print(f"⚠️ Warning: Invalid price detected: {price}")
            return

        # Calculate stop loss and take profit levels
        sl_distance = self.min_stop_distance * price
        tp_distance = sl_distance * self.risk_multiplier

        # entry conditions
        if crossover(self.apo, 0):
            sl_price = price - sl_distance
            tp_price = price + tp_distance
            print(f"🚀 LONG Entry - Price: {price:.4f}, SL: {sl_price:.4f}, TP: {tp_price:.4f}, APO: {self.apo[-1]:.2f}")
            self.buy(sl=sl_price, tp=tp_price)

        elif crossover(0, self.apo):
            sl_price = price + sl_distance
            tp_price = price - tp_distance
            print(f"🔻 SHORT Entry - Price: {price:.4f}, SL: {sl_price:.4f}, TP: {tp_price:.4f}, APO: {self.apo[-1]:.2f}")
            self.sell(sl=sl_price, tp=tp_price)

        # exit conditions 
        if self.position:
            if self.position.is_long and crossover(0, self.apo):
                print(f"🎯 Closing LONG position at {price:.4f}")
                self.position.close()
            elif self.position.is_short and crossover(self.apo, 0):
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
    bt = Backtest(data, APOStrategy, cash=cash, commission=commission, exclusive_orders=True)
    
    print("\n🎮 Starting backtest...")
    stats = bt.run()
    
    # Print full stats
    print("\n🎭 Moon Dev's Backtest Results 🎭")
    print(f"💰 Return: {stats['Return [%]']:.2f}%")
    print(f"📉 Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")
    print(f"🎯 Win Rate: {stats['Win Rate [%]']:.2f}%")
    print(f"🔄 # Trades: {stats['# Trades']}")
    print(f"📊 Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
    
    print("\n📈 Showing plot...")
    # Show plot and clean up HTML file
    chart_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/charts/temp_chart.html'
    bt.plot(filename=chart_path)
    
    # Clean up the file after showing
    if os.path.exists(chart_path):
        os.remove(chart_path)
        print("🧹 Cleaned up chart file")
    
    print("✨ Moon Dev's APO Strategy Complete! ✨")
    
    return stats

if __name__ == "__main__":
    # Example usage with different data sources
    crypto_data = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/storage_SOL-USD1d2.csv'
    stats = run_backtest(crypto_data)
    print(stats)