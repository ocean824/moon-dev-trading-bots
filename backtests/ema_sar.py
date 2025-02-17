'''
EMA SAR Strategy 📈 - Moon Dev's Trend Following System
'''

from backtesting import Backtest, Strategy 
from backtesting.lib import crossover
import numpy as np 
import pandas as pd 
import os

print("🌙 Moon Dev's EMA SAR Strategy Loading... 🚀")

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

class EmaSarStrategy(Strategy):
    n1 = 20  # Fast EMA period
    n2 = 55  # Slow EMA period
    sar_af = 0.02  # SAR acceleration factor
    sar_max = 0.2  # SAR maximum acceleration
    risk_multiplier = 2
    min_stop_distance = 0.002  # 0.2% minimum stop distance

    def init(self):
        print("🎯 Moon Dev's Strategy Initialization")
        # compute moving averages using the closing price
        self.ema1 = self.I(self.calculate_ema, self.data.Close, self.n1)
        self.ema2 = self.I(self.calculate_ema, self.data.Close, self.n2)

        # compute parabolic sar 
        high, low = self.data.High, self.data.Low 
        self.sar = self.I(self.calculate_psar, high, low)
        print("✨ EMA and SAR Indicators Created Successfully!")

    def calculate_ema(self, data, period):
        """Calculate exponential moving average (EMA) using numpy"""
        print(f"📊 Calculating EMA{period}...")
        ema = np.zeros(len(data))
        multiplier = 2 / (period + 1)
        ema[period-1] = np.mean(data[0:period])

        for i in range(period, len(data)):
            ema[i] = ((data[i] - ema[i-1]) * multiplier) + ema[i-1]
        
        return ema 
    
    def calculate_psar(self, high, low):
        """Calculate parabolic SAR"""
        print("🎯 Calculating Parabolic SAR...")
        length = len(high)
        psar = np.zeros(length)
        psar_bull = True 
        af = self.sar_af 
        ep = high[0]

        for i in range(2, length):
            if psar_bull:
                psar[i] = min(psar[i-1], low[i-1], low[i-2])
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + self.sar_af, self.sar_max)
            else:
                psar[i] = max(psar[i-1], high[i-1], high[i-2])
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + self.sar_af, self.sar_max)

            psar[i] += af * (ep-psar[i])

            reverse = (psar_bull and low[i] < psar[i]) or (not psar_bull and high[i] > psar[i])
            if reverse:
                psar_bull = not psar_bull
                psar[i] = ep 
                af = self.sar_af
                ep = low[i] if psar_bull else high[i]

        return psar 
    
    def next(self):
        price = self.data.Close[-1]

        if price <= 0:
            print(f"⚠️ Warning: Invalid price detected: {price}")
            return

        # Calculate stop loss and take profit levels
        sl_distance = max(self.min_stop_distance * price, abs(price - self.sar[-1]))
        tp_distance = sl_distance * self.risk_multiplier

        # Buy signal: Fast EMA crosses above slow EMA and price above SAR
        if crossover(self.ema1, self.ema2) and price > self.sar[-1]:
            sl_price = min(price - sl_distance, self.sar[-1])  # Use SAR as dynamic stop loss
            tp_price = price + tp_distance
            print(f"🚀 LONG Entry - Price: {price:.4f}, SL: {sl_price:.4f}, TP: {tp_price:.4f}")
            print(f"📊 Indicators - EMA1: {self.ema1[-1]:.4f}, EMA2: {self.ema2[-1]:.4f}, SAR: {self.sar[-1]:.4f}")
            self.buy(sl=sl_price, tp=tp_price)

        # Exit signal: Slow EMA crosses above fast EMA or price below SAR
        elif self.position and (crossover(self.ema2, self.ema1) or price < self.sar[-1]):
            print(f"🎯 Closing position at {price:.4f}")
            print(f"📊 Indicators - EMA1: {self.ema1[-1]:.4f}, EMA2: {self.ema2[-1]:.4f}, SAR: {self.sar[-1]:.4f}")
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
    bt = Backtest(data, EmaSarStrategy, cash=cash, commission=commission, exclusive_orders=True)
    
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
    
    print("✨ Moon Dev's EMA SAR Strategy Complete! ✨")
    
    return stats

if __name__ == "__main__":
    # Example usage with different data sources
    crypto_data = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/SOL-1d-1000wks-data.csv'
    stats = run_backtest(crypto_data)
    print("\n📊 Full Backtest Statistics:")
    print(stats)

