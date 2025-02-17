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
    # Define strategy parameters
    adx_threshold = 25        # Increased from 20 for stronger trends
    di_threshold = 25         # Increased from 20 for stronger signals
    profit_target = 0.03      # 3% profit target
    stop_loss = 0.015        # 1.5% stop loss
    
    def init(self):
        print("🎯 Moon Dev's ADX Star Strategy Initialization")
        
        # INDICATORS 
        # Trend following indicators
        self.sma_20 = self.I(talib.SMA, self.data.Close, timeperiod=20)
        self.sma_50 = self.I(talib.SMA, self.data.Close, timeperiod=50)
        self.sma_200 = self.I(talib.SMA, self.data.Close, timeperiod=200)

        # ADX and DI indicators
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, timeperiod=14)
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, timeperiod=14)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, timeperiod=14)

        # PSAR for additional confirmation
        self.psar = self.I(talib.SAR, self.data.High, self.data.Low, acceleration=0.02, maximum=0.2)
        
        print("✨ Moon Dev's Indicators Created Successfully!")

    def next(self):
        price = self.data.Close[-1]
        
        # Skip if price is invalid
        if price <= 0:
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
                
                print(f"🎯 Closing LONG position at ${price:.2f}")
                print(f"   Reason: Trend weakening")
                print(f"   ADX: {self.adx[-1]:.2f}")
                print(f"   +DI: {self.plus_di[-1]:.2f}")
                print(f"   -DI: {self.minus_di[-1]:.2f}")
                
                self.position.close()

print("📊 Loading data...")
# load in the data 
data = pd.read_csv('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/yahoo_daily/AMZN_stock_1d.csv')

# Normalize the data to handle different  formats
data = normalize_data(data)

print(f"📈 Data loaded: {len(data)} candles from {data.index[0]} to {data.index[-1]}")
print(f"💰 Price range: ${data['Low'].min():.4f} - ${data['High'].max():.4f}")

bt = Backtest(data, ADXParabolicSARStrategy, cash=1000000, commission=0.002, exclusive_orders=True)

print("\n🎮 Starting backtest...")
stats = bt.run()
print(stats)

print("\n📈 Generating plot...")
bt.plot()
print("✨ Moon Dev's ADX Star Strategy Complete! ✨")


