'''
ADX, Parabolic SAR strategy by Moon Dev 🌙
'''

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import talib
import os

print("🌟 Moon Dev's ADX Star Strategy Loading... 🚀")

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

class ADXParabolicSARStrategy(Strategy):
    # Define strategy parameters for optimization
    adx_threshold = 25        # Will optimize: 20-35
    di_threshold = 25         # Will optimize: 20-35
    profit_target = 0.03      # Will optimize: 0.02-0.05
    stop_loss = 0.015        # Will optimize: 0.01-0.03
    sma_short = 20           # Will optimize: 10-30
    sma_medium = 50          # Will optimize: 40-60
    sma_long = 200           # Will optimize: 150-250
    psar_accel = 0.02        # Will optimize: 0.01-0.03
    psar_max = 0.2          # Will optimize: 0.1-0.3
    
    def init(self):
        if not hasattr(self, '_optimization_in_progress'):
            print("🎯 Moon Dev's ADX Star Strategy Initialization")
            print(f"🔧 Parameters: ADX={self.adx_threshold}, DI={self.di_threshold}, PT={self.profit_target}, SL={self.stop_loss}")
            print(f"📊 SMAs: {self.sma_short}/{self.sma_medium}/{self.sma_long}")
        
        # INDICATORS 
        # Trend following indicators
        self.sma_20 = self.I(talib.SMA, self.data.Close, timeperiod=self.sma_short)
        self.sma_50 = self.I(talib.SMA, self.data.Close, timeperiod=self.sma_medium)
        self.sma_200 = self.I(talib.SMA, self.data.Close, timeperiod=self.sma_long)

        # ADX and DI indicators
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, timeperiod=14)
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, timeperiod=14)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, timeperiod=14)

        # PSAR for additional confirmation
        self.psar = self.I(talib.SAR, self.data.High, self.data.Low, 
                          acceleration=self.psar_accel, maximum=self.psar_max)
        
        if not hasattr(self, '_optimization_in_progress'):
            print("✨ Moon Dev's Indicators Created Successfully!")

    def next(self):
        price = self.data.Close[-1]
        
        # Skip if price is invalid
        if price <= 0:
            if not hasattr(self, '_optimization_in_progress'):
                print(f"⚠️ Warning: Invalid price detected: {price}")
            return

        # Check if we're in a strong uptrend
        strong_uptrend = (
            price > self.sma_20[-1] > self.sma_50[-1] > self.sma_200[-1] and  # Price above all MAs
            self.sma_20[-1] > self.sma_20[-2] and  # 20 SMA rising
            self.data.Low[-1] > self.psar[-1]  # Price above PSAR
        )

        # ADX and DI conditions
        strong_momentum = (
            self.adx[-1] > self.adx_threshold and  # Strong trend
            self.plus_di[-1] > self.di_threshold and  # Strong bullish momentum
            self.plus_di[-1] > self.minus_di[-1] and  # Bullish over bearish
            self.adx[-1] > self.adx[-2]  # ADX rising
        )

        # Volume confirmation (optional but recommended)
        volume_confirms = self.data.Volume[-1] > self.data.Volume[-2]

        # Long entry conditions
        if not self.position:
            if strong_uptrend and strong_momentum and volume_confirms:
                # Calculate position size (1% risk per trade)
                stop_price = price * (1 - self.stop_loss)
                target_price = price * (1 + self.profit_target)
                
                if not hasattr(self, '_optimization_in_progress'):
                    print(f"🚀 LONG Entry Signal:")
                    print(f"   Price: ${price:.2f}")
                    print(f"   Stop Loss: ${stop_price:.2f}")
                    print(f"   Target: ${target_price:.2f}")
                    print(f"   ADX: {self.adx[-1]:.2f}")
                    print(f"   +DI: {self.plus_di[-1]:.2f}")
                
                self.buy(sl=stop_price, tp=target_price)

        # Exit conditions (in addition to SL/TP)
        elif self.position.is_long:
            # Exit if trend weakens
            if (self.adx[-1] < 20 or  # Trend becoming weak
                self.minus_di[-1] > self.plus_di[-1] or  # Bearish crossover
                price < self.sma_50[-1]):  # Price below 50 SMA
                
                if not hasattr(self, '_optimization_in_progress'):
                    print(f"🎯 Closing LONG position at ${price:.2f}")
                    print(f"   Reason: Trend weakening")
                    print(f"   ADX: {self.adx[-1]:.2f}")
                    print(f"   +DI: {self.plus_di[-1]:.2f}")
                    print(f"   -DI: {self.minus_di[-1]:.2f}")
                
                self.position.close()

print("📊 Loading data...")
# load in the data 
data = pd.read_csv('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/yahoo_daily/AMZN_stock_1d.csv')

# Normalize the data to handle different formats
data = normalize_data(data)

print(f"📈 Data loaded: {len(data)} candles from {data.index[0]} to {data.index[-1]}")
print(f"💰 Price range: ${data['Low'].min():.4f} - ${data['High'].max():.4f}")

bt = Backtest(data, ADXParabolicSARStrategy, cash=1000000, commission=0.002, exclusive_orders=True)

# Define optimization ranges
optimization_params = {
    'adx_threshold': range(20, 36, 2),       # 20-35 step 2
    'di_threshold': range(20, 36, 2),        # 20-35 step 2
    'profit_target': [0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05],  # 2-5% step 0.5%
    'stop_loss': [0.01, 0.015, 0.02, 0.025, 0.03],      # 1-3% step 0.5%
    'sma_short': range(10, 31, 5),           # 10-30 step 5
    'sma_medium': range(40, 61, 5),          # 40-60 step 5
    'sma_long': range(150, 251, 25),         # 150-250 step 25
    'psar_accel': [0.01, 0.015, 0.02, 0.025, 0.03],    # 0.01-0.03 step 0.005
    'psar_max': [0.1, 0.15, 0.2, 0.25, 0.3]          # 0.1-0.3 step 0.05
}

print("\n🎲 Running Moon Dev's Strategy Optimizer...")
print("🔍 This might take a while - searching for the perfect combination...")

# Run optimization
optimization_results = bt.optimize(**optimization_params,
                                 maximize='Equity Final [$]',
                                 constraint=lambda p: (p.sma_short < p.sma_medium < p.sma_long 
                                                    and p.stop_loss < p.profit_target))

print("\n🏆 Moon Dev's Optimal Strategy Parameters:")
print(optimization_results._strategy)
print("\n📊 Performance with Optimal Parameters:")
print(optimization_results)

# print("\n🚀 Running Final Backtest with Original Parameters...")
# stats = bt.run()
# print("\n🎭 Original Strategy Stats:")
# print(stats)

# print("\n📈 Generating plot for original parameters...")
# bt.plot(show_plot=True, save_plot=False)
# print("✨ Moon Dev's ADX Star Strategy Optimization Complete! ✨")


