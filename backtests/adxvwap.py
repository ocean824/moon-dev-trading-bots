import pandas as pd
import numpy as np
import talib
import pandas_ta as ta
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

print("🚀 Moon Dev's VWAP + ADX Strategy Loading... 🌙")

# Load the filtered data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/btc_1min_test_1.csv'
print(f"📊 Loading Moon Dev's crypto data from: {data_path}")

data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')
print(f"✅ Data loaded successfully! Moon Dev's dataset has {len(data)} rows 🌙")

# VWAP + ADX Strategy
class VWAPADXStrategy(Strategy):
    # Strategy parameters
    vwap_period = 20        # VWAP calculation period
    adx_period = 14         # ADX period
    adx_threshold = 25      # ADX threshold for trend strength
    vwap_deviation = 0.002  # Deviation from VWAP for entry (0.2%)
    take_profit = 0.015     # 1.5% take profit
    stop_loss = 0.01        # 1% stop loss
    
    def init(self):
        print("🔧 Moon Dev's VWAP + ADX Strategy Initializing... 🌙")
        
        # Calculate VWAP using pandas_ta
        self.vwap = self.I(self.calculate_vwap)
        
        # Calculate ADX using talib
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        
        # Calculate +DI and -DI for directional movement
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        
        print("📈 Moon Dev's indicators calculated! VWAP + ADX ready to rock! 🚀")
    
    def calculate_vwap(self):
        """Calculate VWAP using numpy approach for Moon Dev 🌙"""
        # Get the typical price (HLC/3)
        typical_price = (self.data.High + self.data.Low + self.data.Close) / 3
        
        # Calculate volume-weighted typical price
        volume_price = typical_price * self.data.Volume
        
        # Calculate rolling VWAP
        vwap_values = []
        for i in range(len(self.data)):
            if i < self.vwap_period - 1:
                vwap_values.append(np.nan)
            else:
                start_idx = max(0, i - self.vwap_period + 1)
                end_idx = i + 1
                
                volume_sum = np.sum(self.data.Volume[start_idx:end_idx])
                volume_price_sum = np.sum(volume_price[start_idx:end_idx])
                
                if volume_sum > 0:
                    vwap_values.append(volume_price_sum / volume_sum)
                else:
                    vwap_values.append(np.nan)
        
        return np.array(vwap_values)
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.vwap_period, self.adx_period):
            return
        
        current_price = self.data.Close[-1]
        current_vwap = self.vwap[-1]
        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]
        
        # Skip if we don't have valid indicator values
        if pd.isna(current_vwap) or pd.isna(current_adx):
            return
        
        # Long Entry Conditions:
        # 1. Price is above VWAP with some deviation
        # 2. ADX shows strong trend (> threshold)
        # 3. +DI > -DI (bullish momentum)
        if (not self.position and 
            current_price > current_vwap * (1 + self.vwap_deviation) and
            current_adx > self.adx_threshold and
            current_plus_di > current_minus_di):
            
            print(f"🚀 Moon Dev LONG Entry! Price: ${current_price:.2f}, VWAP: ${current_vwap:.2f}, ADX: {current_adx:.2f} 🌙")
            self.buy(
                sl=current_price * (1 - self.stop_loss),
                tp=current_price * (1 + self.take_profit)
            )
        
        # Short Entry Conditions:
        # 1. Price is below VWAP with some deviation
        # 2. ADX shows strong trend (> threshold)
        # 3. -DI > +DI (bearish momentum)
        elif (not self.position and 
              current_price < current_vwap * (1 - self.vwap_deviation) and
              current_adx > self.adx_threshold and
              current_minus_di > current_plus_di):
            
            print(f"🔻 Moon Dev SHORT Entry! Price: ${current_price:.2f}, VWAP: ${current_vwap:.2f}, ADX: {current_adx:.2f} 🌙")
            self.sell(
                sl=current_price * (1 + self.stop_loss),
                tp=current_price * (1 - self.take_profit)
            )

# Ensure data columns are correctly formatted
print("🔄 Moon Dev's data preprocessing in progress... 🌙")
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
print(f"📋 Column names set: {list(data.columns)}")

# Remove any invalid data
data = data.dropna()
print(f"✅ Moon Dev's data cleaned! {len(data)} valid rows remaining 🚀")

# Create and configure the backtest
print("⚙️ Moon Dev's backtesting engine starting up... 🌙")
bt = Backtest(data, VWAPADXStrategy, cash=100000, commission=0.002)

# Run the backtest with default parameters
print("🎯 Moon Dev's default parameter backtest running... 🚀")
stats_default = bt.run()
print("\n🌙 ===== MOON DEV'S DEFAULT PARAMETERS RESULTS ===== 🌙")
print(stats_default)
print("🌙 ================================================== 🌙\n")

# Optimization - Moon Dev style!
print("🔍 Moon Dev's optimization process initiating... 🌙")
optimization_results = bt.optimize(
    vwap_period=range(15, 31, 5),                                    # VWAP periods: 15, 20, 25, 30
    adx_period=range(10, 21, 2),                                     # ADX periods: 10, 12, 14, 16, 18, 20
    adx_threshold=range(20, 36, 5),                                  # ADX thresholds: 20, 25, 30, 35
    vwap_deviation=[i / 1000 for i in range(1, 6, 1)],             # Deviations: 0.1% to 0.5%
    take_profit=[i / 100 for i in range(1, 4, 1)],                 # TP: 1%, 2%, 3%
    stop_loss=[i / 100 for i in range(1, 3, 1)],                   # SL: 1%, 2%
    maximize='Equity Final [$]',
    constraint=lambda param: (param.vwap_period > 0 and 
                             param.adx_period > 0 and 
                             param.adx_threshold > 0 and
                             param.take_profit > param.stop_loss)     # Ensure TP > SL
)

print("\n🚀 ===== MOON DEV'S OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)
print("🚀 ========================================== 🚀\n")

# Print the best optimized parameters - Moon Dev style!
print("🏆 Moon Dev's BEST PARAMETERS DISCOVERED! 🏆")
print(f"🌙 VWAP Period: {optimization_results._strategy.vwap_period}")
print(f"🌙 ADX Period: {optimization_results._strategy.adx_period}")
print(f"🌙 ADX Threshold: {optimization_results._strategy.adx_threshold}")
print(f"🌙 VWAP Deviation: {optimization_results._strategy.vwap_deviation:.4f} ({optimization_results._strategy.vwap_deviation*100:.2f}%)")
print(f"🌙 Take Profit: {optimization_results._strategy.take_profit:.4f} ({optimization_results._strategy.take_profit*100:.2f}%)")
print(f"🌙 Stop Loss: {optimization_results._strategy.stop_loss:.4f} ({optimization_results._strategy.stop_loss*100:.2f}%)")

print("\n🌙 Moon Dev's VWAP + ADX Strategy Analysis Complete! 🚀")
print("💰 May your trades be profitable and your rockets reach the moon! 🌙")
