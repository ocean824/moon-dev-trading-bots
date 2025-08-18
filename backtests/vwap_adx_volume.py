import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

print("🚀 Moon Dev's VWAP + ADX + Volume Breakout Strategy Loading... 🌙")

# Load the filtered data
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/btc_1min_test_1.csv'
print(f"📊 Loading Moon Dev's crypto data from: {data_path}")

# Adaptive header detection for Moon Dev's data
try:
    # Try reading first few rows to detect headers
    sample = pd.read_csv(data_path, nrows=5)
    
    # Check if first row contains headers (non-numeric values in price columns)
    if sample.iloc[0].dtype == 'object' or any(isinstance(val, str) for val in sample.iloc[0].values):
        data = pd.read_csv(data_path, parse_dates=[0], index_col=0)
    else:
        # No headers, create them
        data = pd.read_csv(data_path, header=None, parse_dates=[0], index_col=0)
        data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
except:
    # Fallback to standard loading
    data = pd.read_csv(data_path, parse_dates=[0], index_col=0)

print(f"✅ Data loaded successfully! Moon Dev's dataset has {len(data)} rows 🌙")

# VWAP + ADX + Volume Breakout Strategy
class VWAPADXVolumeStrategy(Strategy):
    # Strategy parameters
    vwap_period = 20        # VWAP calculation period
    adx_period = 14         # ADX period
    adx_threshold = 25      # ADX threshold for trend strength
    volume_period = 20      # Period for average volume calculation
    volume_multiplier = 1.5 # Volume spike multiplier
    take_profit = 0.03      # 3% take profit
    stop_loss = 0.02        # 2% stop loss
    
    def init(self):
        # Calculate VWAP
        self.vwap = self.I(self.calculate_vwap)
        
        # Calculate ADX using talib
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        
        # Calculate average volume
        self.avg_volume = self.I(talib.SMA, self.data.Volume, self.volume_period)
        
    def calculate_vwap(self):
        """Calculate VWAP using rolling window approach"""
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
        if len(self.data) < max(self.vwap_period, self.adx_period, self.volume_period):
            return
        
        current_price = self.data.Close[-1]
        current_vwap = self.vwap[-1]
        current_adx = self.adx[-1]
        current_volume = self.data.Volume[-1]
        current_avg_volume = self.avg_volume[-1]
        
        # Skip if we don't have valid indicator values
        if pd.isna(current_vwap) or pd.isna(current_adx) or pd.isna(current_avg_volume):
            return
        
        # Check for volume breakout
        volume_breakout = current_volume > (current_avg_volume * self.volume_multiplier)
        
        # Long Entry Conditions:
        # 1. Price is above VWAP
        # 2. ADX > 25 (trending market)
        # 3. Volume > 1.5x average volume
        if (not self.position and 
            current_price > current_vwap and
            current_adx > self.adx_threshold and
            volume_breakout):
            
            self.buy(
                sl=current_price * (1 - self.stop_loss),
                tp=current_price * (1 + self.take_profit)
            )
        
        # Short Entry Conditions:
        # 1. Price is below VWAP
        # 2. ADX > 25 (trending market)
        # 3. Volume > 1.5x average volume
        elif (not self.position and 
              current_price < current_vwap and
              current_adx > self.adx_threshold and
              volume_breakout):
            
            self.sell(
                sl=current_price * (1 + self.stop_loss),
                tp=current_price * (1 - self.take_profit)
            )
        
        # Exit conditions: price crosses back to other side of VWAP
        elif self.position:
            if self.position.is_long and current_price < current_vwap:
                self.position.close()
            elif self.position.is_short and current_price > current_vwap:
                self.position.close()

# Ensure data columns are correctly formatted
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Remove any invalid data
data = data.dropna()
print(f"✅ Moon Dev's data cleaned! {len(data)} valid rows remaining 🚀")

# Create and configure the backtest
bt = Backtest(data, VWAPADXVolumeStrategy, cash=100000, commission=0.002)

# Run the backtest with default parameters
stats_default = bt.run()
print("\n🌙 ===== MOON DEV'S DEFAULT PARAMETERS RESULTS ===== 🌙")
print(stats_default)
print("🌙 ================================================== 🌙\n")

# Optimization
optimization_results = bt.optimize(
    vwap_period=range(15, 31, 5),                                    # VWAP periods: 15, 20, 25, 30
    adx_period=range(10, 21, 2),                                     # ADX periods: 10, 12, 14, 16, 18, 20
    adx_threshold=range(20, 36, 5),                                  # ADX thresholds: 20, 25, 30, 35
    volume_period=range(15, 31, 5),                                  # Volume periods: 15, 20, 25, 30
    volume_multiplier=[1.2, 1.5, 1.8, 2.0, 2.5],                   # Volume multipliers
    take_profit=[i / 100 for i in range(2, 5, 1)],                 # TP: 2%, 3%, 4%
    stop_loss=[i / 100 for i in range(1, 4, 1)],                   # SL: 1%, 2%, 3%
    maximize='Equity Final [$]',
    constraint=lambda param: (param.vwap_period > 0 and 
                             param.adx_period > 0 and 
                             param.adx_threshold > 0 and
                             param.volume_period > 0 and
                             param.volume_multiplier > 1 and
                             param.take_profit > param.stop_loss)
)

print("\n🚀 ===== MOON DEV'S OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)
print("🚀 ========================================== 🚀\n")

# Print the best optimized parameters
print("🏆 Moon Dev's BEST PARAMETERS DISCOVERED! 🏆")
print(f"🌙 VWAP Period: {optimization_results._strategy.vwap_period}")
print(f"🌙 ADX Period: {optimization_results._strategy.adx_period}")
print(f"🌙 ADX Threshold: {optimization_results._strategy.adx_threshold}")
print(f"🌙 Volume Period: {optimization_results._strategy.volume_period}")
print(f"🌙 Volume Multiplier: {optimization_results._strategy.volume_multiplier:.1f}x")
print(f"🌙 Take Profit: {optimization_results._strategy.take_profit:.4f} ({optimization_results._strategy.take_profit*100:.2f}%)")
print(f"🌙 Stop Loss: {optimization_results._strategy.stop_loss:.4f} ({optimization_results._strategy.stop_loss*100:.2f}%)")

print("\n🌙 Moon Dev's VWAP + ADX + Volume Strategy Analysis Complete! 🚀")
print("💰 May your trades be profitable and your rockets reach the moon! 🌙")