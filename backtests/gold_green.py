'''
VWAP ema gold green strategy by Moon Dev 🌙
Source : https://atozmarkets.com/indicators/vwap-ema-gold-green-forex-trading-strategy/
'''

import talib 
import numpy as np 
import pandas as pd 
from backtesting import Backtest, Strategy 
from backtesting.lib import crossover 

print("🌟 Moon Dev's VWAP EMA Gold Green Strategy Loading... 🚀")

def normalize_data(df):
    """Normalize different data formats to a standard format"""
    print("🔄 Normalizing data format...")
    
    column_maps = {
        'Open': ['Open', 'open'],
        'High': ['High', 'high'],
        'Low': ['Low', 'low'],
        'Close': ['Close', 'close'],
        'Volume': ['Volume', 'volume'],
        'datetime': ['Datetime', 'datetime', 'Date', 'date']  # Added more datetime variants
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

class VWAP_EMA_Strategy(Strategy):
    # Define parameters for optimization
    fast_ema = 5        # Will optimize: 3-15
    slow_ema = 200      # Will optimize: 150-250
    vwap_fast = 20      # Will optimize: 10-30
    vwap_slow = 50      # Will optimize: 40-60
    
    def init(self):
        if not hasattr(self, '_optimization_in_progress'):
            print("🎯 Moon Dev's VWAP EMA Strategy Initializing...")
            print(f"🔧 Parameters: Fast EMA={self.fast_ema}, Slow EMA={self.slow_ema}")
            print(f"📊 VWAP Periods: Fast={self.vwap_fast}, Slow={self.vwap_slow}")
        
        # indicators
        self.ema5 = self.I(talib.EMA, self.data.Close, timeperiod=self.fast_ema)
        self.ema200 = self.I(talib.EMA, self.data.Close, timeperiod=self.slow_ema)
        self.vwap20 = self.I(talib.SMA, self.data.Volume * (self.data.High + self.data.Low + self.data.Close) / 3, timeperiod=self.vwap_fast)
        self.vwap50 = self.I(talib.SMA, self.data.Volume * (self.data.High + self.data.Low + self.data.Close) / 3, timeperiod=self.vwap_slow)
        
        if not hasattr(self, '_optimization_in_progress'):
            print("✨ Moon Dev's Indicators Created Successfully!")

    def next(self):
        price = self.data.Close[-1]
        vwap_midpoint = (self.vwap20[-1] + self.vwap50[-1]) / 2

        # Print current analysis for debugging (only if not optimizing)
        if not hasattr(self, '_optimization_in_progress'):
            print(f"🔍 Moon Dev Analysis - Price: {price:.2f}, EMA5: {self.ema5[-1]:.2f}, EMA200: {self.ema200[-1]:.2f}")
            print(f"📊 VWAP Analysis - VWAP20: {self.vwap20[-1]:.2f}, VWAP50: {self.vwap50[-1]:.2f}, Midpoint: {vwap_midpoint:.2f}")

        # buy condition 
        if (crossover(self.ema5, self.ema200) and price > self.ema200[-1]):
            if not hasattr(self, '_optimization_in_progress'):
                print("🌕 Moon Dev Says: Golden Cross Detected! Going LONG!")
            self.buy()

        # sell condition 
        elif (crossover(self.ema200, self.ema5) and price < self.ema200[-1]):
            if not hasattr(self, '_optimization_in_progress'):
                print("🌑 Moon Dev Says: Death Cross Detected! Going SHORT!")
            self.sell()

        # exit conditions 
        for trade in self.trades:
            if trade.is_long and price <= vwap_midpoint:
                if not hasattr(self, '_optimization_in_progress'):
                    print("💫 Moon Dev Says: Long Position Hit VWAP Midpoint - Exiting!")
                self.position.close()
            elif trade.is_short and price >= vwap_midpoint:
                if not hasattr(self, '_optimization_in_progress'):
                    print("💫 Moon Dev Says: Short Position Hit VWAP Midpoint - Exiting!")
                self.position.close()

# Load the data
print("📊 Loading Moon Dev's Trading Data...")
data = pd.read_csv('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/BNB_30m_5000.csv')

# Normalize the data
data = normalize_data(data)

print(f"📈 Data loaded: {len(data)} candles")
print(f"💰 Price range: ${data['Low'].min():.2f} - ${data['High'].max():.2f}")

# Define optimization ranges
optimization_params = {
    'fast_ema': range(3, 16, 2),        # 3-15 step 2
    'slow_ema': range(150, 251, 25),    # 150-250 step 25
    'vwap_fast': range(10, 31, 5),      # 10-30 step 5
    'vwap_slow': range(40, 61, 5)       # 40-60 step 5
}

# Run optimization
print("\n🎲 Running Moon Dev's Strategy Optimizer...")
print("🔍 This might take a while - searching for the perfect combination...")

bt = Backtest(data, VWAP_EMA_Strategy, 
              cash=1000000, 
              commission=.002,
              exclusive_orders=True)

# Run optimization
optimization_results = bt.optimize(**optimization_params,
                                 maximize='Equity Final [$]',
                                 constraint=lambda p: p.vwap_fast < p.vwap_slow 
                                                    and p.fast_ema < p.slow_ema)

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
print("✨ Moon Dev's VWAP EMA Strategy Complete! ✨")
