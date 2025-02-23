'''
Parabolic SAR with StochRSI Strategy by Moon Dev 🌙
Source: https://alchemymarkets.com/education/indicators/parabolic-sar/
'''

import numpy as np 
import talib 
from backtesting import Backtest, Strategy 
from backtesting.lib import crossover 
import pandas as pd   

print("🌟 Moon Dev's SAR StochRSI Strategy Loading... 🚀")

def normalize_data(df):
    """Normalize different data formats to a standard format"""
    print("🔄 Normalizing data format...")
    
    column_maps = {
        'Open': ['Open', 'open'],
        'High': ['High', 'high'],
        'Low': ['Low', 'low'],
        'Close': ['Close', 'close'],
        'Volume': ['Volume', 'volume'],
        'datetime': ['Datetime', 'datetime', 'Date', 'date']
    }
    
    normalized_df = pd.DataFrame()
    
    for standard_name, possible_names in column_maps.items():
        found_col = next((col for col in possible_names if col in df.columns), None)
        if found_col:
            normalized_df[standard_name] = df[found_col]
    
    # Drop any support/resistance columns if they exist
    if 'Support' in df.columns:
        normalized_df['Support'] = df['Support']
    if 'Resistance' in df.columns:
        normalized_df['Resistance'] = df['Resistance']
    
    # Set the index
    if 'datetime' in normalized_df.columns:
        normalized_df.index = pd.to_datetime(normalized_df['datetime'])
        normalized_df = normalized_df.drop('datetime', axis=1)
    else:
        raise ValueError("Could not find date information in the data")
        
    print(f"✅ Data normalized successfully with columns: {list(normalized_df.columns)}")
    return normalized_df

class PSARStochRSIStrategy(Strategy):
    # Strategy parameters for optimization
    psar_step = 0.02    # Will optimize: 0.01-0.04
    psar_max = 0.2      # Will optimize: 0.1-0.3
    stoch_rsi_k = 3     # Will optimize: 3-9
    rsi_length = 14     # Will optimize: 10-20

    # Fixed parameters
    psar_start = 0.01   # Keep fixed
    stoch_rsi_d = 3     # Keep fixed
    stoch_length = 14   # Keep fixed

    def init(self):
        if not hasattr(self, '_optimization_in_progress'):
            print("🎯 Moon Dev's SAR StochRSI Strategy Initializing...")
            print(f"🔧 SAR Parameters: Start={self.psar_start}, Step={self.psar_step}, Max={self.psar_max}")
            print(f"📊 StochRSI: K={self.stoch_rsi_k}, D={self.stoch_rsi_d}, RSI={self.rsi_length}")

        close = self.data.Close 
        high = self.data.High 
        low = self.data.Low 

        # parabolic sar 
        self.sar = self.I(talib.SAR, high, low, self.psar_step, self.psar_max)

        # stochastic RSI 
        stoch_rsi_k, stoch_rsi_d = talib.STOCHRSI(close, 
                                                  timeperiod=self.rsi_length,
                                                  fastk_period=self.stoch_rsi_k, 
                                                  fastd_period=self.stoch_rsi_d, 
                                                  fastd_matype=0)

        self.stoch_rsi_k = self.I(lambda x: x, stoch_rsi_k)
        self.stoch_rsi_d = self.I(lambda x: x, stoch_rsi_d)
        
        if not hasattr(self, '_optimization_in_progress'):
            print("✨ Moon Dev's Indicators Created Successfully!")

    def next(self):
        k, d = self.stoch_rsi_k, self.stoch_rsi_d 
        close, sar = self.data.Close, self.sar 

        # Print current analysis for debugging (only if not optimizing)
        if not hasattr(self, '_optimization_in_progress'):
            print(f"🔍 Moon Dev Analysis - Price: {close[-1]:.2f}, SAR: {sar[-1]:.2f}")
            print(f"📊 StochRSI - K: {k[-1]:.2f}, D: {d[-1]:.2f}")

        # detect double bottom 
        if (k[-3] < 20 and k[-2] > k[-3] and k[-1] > k[-2] and close[-1] > sar[-1] and sar[-2] > close[-2]):
            if not hasattr(self, '_optimization_in_progress'):
                print("🌕 Moon Dev Says: Double Bottom Detected! Going LONG!")
            self.buy()

        # detect double top 
        elif (k[-3] > 80 and k[-2] < k[-3] and k[-1] < k[-2] and close[-1] < sar[-1] and sar[-2] < close[-2]):
            if not hasattr(self, '_optimization_in_progress'):
                print("🌑 Moon Dev Says: Double Top Detected! Going SHORT!")
            self.sell()

# Load the data
print("📊 Loading Moon Dev's Trading Data...")
data = pd.read_csv('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/ge_data/ES_F_future_1d.csv')

# Normalize the data
data = normalize_data(data)

print(f"📈 Data loaded: {len(data)} candles")
print(f"💰 Price range: ${data['Low'].min():.2f} - ${data['High'].max():.2f}")

# Define focused optimization ranges (fewer combinations for faster runtime)
optimization_params = {
    'psar_step': [0.01, 0.02, 0.03, 0.04],     # 4 values
    'psar_max': [0.1, 0.2, 0.3],               # 3 values
    'stoch_rsi_k': [3, 6, 9],                  # 3 values
    'rsi_length': [10, 14, 20]                 # 3 values
}

# Run optimization
print("\n🎲 Running Moon Dev's Quick Strategy Optimizer...")
print("🔍 Testing 108 combinations (4 × 3 × 3 × 3)...")

bt = Backtest(data, PSARStochRSIStrategy, 
              cash=1000000, 
              commission=.002,
              exclusive_orders=True)

# Run optimization
optimization_results = bt.optimize(**optimization_params,
                                 maximize='Equity Final [$]',
                                 constraint=lambda p: p.psar_step < p.psar_max)

print("\n🏆 Moon Dev's Optimal Strategy Parameters:")
print(optimization_results._strategy)
print("\n📊 Performance with Optimal Parameters:")
print(optimization_results)

print("\n🚀 Running Final Backtest with Original Parameters...")
stats = bt.run()
print("\n🎭 Original Strategy Stats:")
print(stats)

# Show the plot
bt.plot()
print("✨ Moon Dev's SAR StochRSI Strategy Complete! ✨")


        