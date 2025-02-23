'''
Trend Flow Strategy 🌊 - Moon Dev's Trend Following System
'''

import pandas as pd
import numpy as np 
from backtesting import Backtest, Strategy
from backtesting.lib import crossover, barssince
from backtesting.test import SMA
import talib

print("🌙 Moon Dev's Trend Flow Strategy Loading... 🚀")

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

def EMA(series, period=50):
    return series.ewm(span=period, adjust=False).mean()

def MACD(close, fast=12, slow=26, signal=9):
    macd_line = EMA(close, fast) - EMA(close, slow)
    signal_line = EMA(macd_line, signal)
    return macd_line, signal_line

def TrendBands(close, period=20, mult=2):
    sma = close.rolling(period).mean()
    std_dev = close.rolling(period).std()
    lower_band = sma - (mult * std_dev)
    upper_band = sma + (mult * std_dev)
    return lower_band, upper_band

def ATR(high, low, close, period=14):
    tr = np.maximum(high - low, np.maximum(abs(high - close.shift()), abs(low-close.shift())))
    return tr.rolling(period).mean()

class AdaptiveTrendFlow(Strategy):
    # Strategy parameters for optimization
    fast_ema_period = 12      # Will optimize: 8-16
    slow_ema_period = 26      # Will optimize: 20-40
    signal_macd_period = 9    # Will optimize: 7-13
    trend_sma_period = 50     # Will optimize: 40-60
    band_period = 20          # Will optimize: 15-25
    band_mult = 2             # Will optimize: 1.5-2.5
    atr_period = 12           # Will optimize: 10-20
    risk_reward_ratio = 2     # Will optimize: 1.5-3

    def init(self):
        if not hasattr(self, '_optimization_in_progress'):
            print("🎯 Moon Dev's Trend Flow Strategy Initialization")
            print(f"🔧 Parameters:")
            print(f"  EMA: Fast={self.fast_ema_period}, Slow={self.slow_ema_period}")
            print(f"  MACD Signal: {self.signal_macd_period}")
            print(f"  Trend SMA: {self.trend_sma_period}")
            print(f"  Bands: Period={self.band_period}, Mult={self.band_mult}")
            print(f"  ATR: Period={self.atr_period}, R:R={self.risk_reward_ratio}")

        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # trend indis 
        self.fast_ema = self.I(EMA, close, self.fast_ema_period)
        self.slow_ema = self.I(EMA, close, self.slow_ema_period)
        self.trend_sma = self.I(SMA, close, self.trend_sma_period)

        # MACD confirmation 
        self.macd_line, self.signal_line = self.I(MACD, close, self.fast_ema_period, self.slow_ema_period, self.signal_macd_period)

        #volatility bands 
        self.low_band, self.upp_band = self.I(TrendBands, close, self.band_period, self.band_mult)

        #ATR for stop los calculation 
        self.atr = self.I(ATR, high, low, close, self.atr_period)
        
        if not hasattr(self, '_optimization_in_progress'):
            print("✨ Moon Dev's Indicators Created Successfully!")

    def next(self):
        price = self.data.Close[-1]

        # trend recognition 
        trend_now = 1 if self.fast_ema[-1] > self.slow_ema[-1] else -1
        trend_prev = 1 if self.fast_ema[-2] > self.slow_ema[-2] else -1
        trend_shift = trend_now != trend_prev

        # macd confirmation 
        macd_signal = self.macd_line[-1] > self.signal_line[-1]

        # breakout confirmation 
        breakout_above = price > self.low_band[-1]
        breakout_below = price < self.upp_band[-1]

        # atr based stop loss
        atr_value = self.atr[-1]
        sl_distance = 1.5 * atr_value 

        # Print current analysis (only if not optimizing)
        if not hasattr(self, '_optimization_in_progress'):
            print(f"🔍 Moon Dev Analysis - Price: {price:.2f}, Trend: {'UP' if trend_now == 1 else 'DOWN'}")
            print(f"📊 MACD Signal: {'Bullish' if macd_signal else 'Bearish'}, ATR: {atr_value:.2f}")

        # long entry 
        if trend_shift and trend_now == 1 and macd_signal and breakout_above and price > self.trend_sma[-1]:
            sl = price - sl_distance
            tp = price + (self.risk_reward_ratio * sl_distance)
            if not hasattr(self, '_optimization_in_progress'):
                print(f"🌕 Moon Dev Says: Strong Uptrend Detected! Going LONG!")
                print(f"💰 Entry: {price:.2f}, SL: {sl:.2f}, TP: {tp:.2f}")
            self.buy(sl=sl, tp=tp)

        # short entry 
        elif trend_shift and trend_now == -1 and not macd_signal and breakout_below and price < self.trend_sma[-1]:
            sl = price + sl_distance
            tp = price - (self.risk_reward_ratio * sl_distance)
            if not hasattr(self, '_optimization_in_progress'):
                print(f"🌑 Moon Dev Says: Strong Downtrend Detected! Going SHORT!")
                print(f"💰 Entry: {price:.2f}, SL: {sl:.2f}, TP: {tp:.2f}")
            self.sell(sl=sl, tp=tp)

# Load the data
print("📊 Loading Moon Dev's Trading Data...")
data = pd.read_csv('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/BNB_30m_5000.csv')

# Normalize the data
data = normalize_data(data)

print(f"📈 Data loaded: {len(data)} candles")
print(f"💰 Price range: ${data['Low'].min():.2f} - ${data['High'].max():.2f}")

# Define optimization ranges
optimization_params = {
    'fast_ema_period': range(8, 17, 2),       # 8-16 step 2
    'slow_ema_period': range(20, 41, 4),      # 20-40 step 4
    'signal_macd_period': range(7, 14, 2),    # 7-13 step 2
    'trend_sma_period': range(40, 61, 5),     # 40-60 step 5
    'band_period': range(15, 26, 5),          # 15-25 step 5
    'band_mult': [1.5, 2.0, 2.5],            # 1.5-2.5 step 0.5
    'atr_period': range(10, 21, 5),          # 10-20 step 5
    'risk_reward_ratio': [1.5, 2.0, 2.5, 3.0] # 1.5-3.0 step 0.5
}

print("\n🎲 Running Moon Dev's Strategy Optimizer...")
print("🔍 Testing multiple parameter combinations...")

bt = Backtest(data, AdaptiveTrendFlow, 
              cash=1000000, 
              commission=.002,
              exclusive_orders=True)

# Run optimization
optimization_results = bt.optimize(**optimization_params,
                                 maximize='Equity Final [$]',
                                 constraint=lambda p: (p.fast_ema_period < p.slow_ema_period 
                                                    and p.band_period < p.trend_sma_period))

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
print("✨ Moon Dev's Trend Flow Strategy Complete! ✨")
