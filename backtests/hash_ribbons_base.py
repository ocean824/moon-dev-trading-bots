import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

print("🚀 Moon Dev's Hash Ribbons Strategy (Base) Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/tc/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-1000wks-data.csv'

# Strategy parameters based on Hash Ribbons concept
HASH_SHORT_PERIOD = 30  # 30-day MA as proxy for 1-month hash rate
HASH_LONG_PERIOD = 60   # 60-day MA as proxy for 2-month hash rate
PRICE_SHORT_PERIOD = 10 # 10-day price MA
PRICE_LONG_PERIOD = 20  # 20-day price MA

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class HashRibbonsStrategy(Strategy):
    # Strategy parameters
    hash_short_period = HASH_SHORT_PERIOD
    hash_long_period = HASH_LONG_PERIOD
    price_short_period = PRICE_SHORT_PERIOD
    price_long_period = PRICE_LONG_PERIOD
    
    # Risk management
    stop_loss = 0.05  # 5% stop loss
    take_profit = 0.15  # 15% take profit
    
    # Recovery parameters
    recovery_bars = 3  # Number of bars to confirm recovery
    
    def init(self):
        print("🔧 Hash Ribbons Strategy Initializing... 🌙")
        
        # Using volume-weighted price as proxy for hash rate
        # Higher volume * price indicates more mining activity/network health
        volume_price = self.data.Close * self.data.Volume
        
        # Hash rate proxies (volume-weighted MAs)
        self.hash_short = self.I(talib.SMA, volume_price, self.hash_short_period)
        self.hash_long = self.I(talib.SMA, volume_price, self.hash_long_period)
        
        # Price MAs for buy signal confirmation
        self.price_short = self.I(talib.SMA, self.data.Close, self.price_short_period)
        self.price_long = self.I(talib.SMA, self.data.Close, self.price_long_period)
        
        # Market states
        self.capitulation = self.I(self.detect_capitulation)
        self.miner_capitulation = self.I(lambda: self.hash_short < self.hash_long)
        self.recovering = self.I(self.detect_recovery)
        self.recovered = self.I(self.detect_recovered)
        
        print("📈 Hash Ribbons indicators calculated! Ready to identify miner capitulation! 🚀")
    
    def detect_capitulation(self):
        """Detect when hash rate short MA crosses under long MA"""
        result = np.zeros(len(self.data))
        hash_short = self.hash_short.values if hasattr(self.hash_short, 'values') else self.hash_short
        hash_long = self.hash_long.values if hasattr(self.hash_long, 'values') else self.hash_long
        
        for i in range(1, len(self.data)):
            if hash_short[i] < hash_long[i] and hash_short[i-1] >= hash_long[i-1]:
                result[i] = 1
        
        return result
    
    def detect_recovery(self):
        """Detect when hash rate starts recovering during capitulation"""
        result = np.zeros(len(self.data))
        hash_short = self.hash_short.values if hasattr(self.hash_short, 'values') else self.hash_short
        hash_long = self.hash_long.values if hasattr(self.hash_long, 'values') else self.hash_long
        
        for i in range(self.recovery_bars, len(self.data)):
            # Check if in capitulation and hash rate is increasing
            if hash_short[i] < hash_long[i]:  # Still in capitulation
                recovering = True
                for j in range(1, self.recovery_bars + 1):
                    if i - j < 0 or hash_short[i] <= hash_short[i - j]:
                        recovering = False
                        break
                result[i] = 1 if recovering else 0
        
        return result
    
    def detect_recovered(self):
        """Detect when hash rate short MA crosses back over long MA"""
        result = np.zeros(len(self.data))
        hash_short = self.hash_short.values if hasattr(self.hash_short, 'values') else self.hash_short
        hash_long = self.hash_long.values if hasattr(self.hash_long, 'values') else self.hash_long
        
        for i in range(1, len(self.data)):
            if hash_short[i] > hash_long[i] and hash_short[i-1] <= hash_long[i-1]:
                result[i] = 1
        
        return result
    
    def bars_since(self, signal_array, current_idx):
        """Helper function to count bars since last signal"""
        for i in range(current_idx - 1, -1, -1):
            if signal_array[i] == 1:
                return current_idx - i
        return current_idx
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.hash_long_period, self.price_long_period):
            return
        
        current_idx = len(self.data) - 1
        current_price = self.data.Close[-1]
        
        # Get indicator values
        hash_short_val = self.hash_short[-1]
        hash_long_val = self.hash_long[-1]
        price_short_val = self.price_short[-1]
        price_long_val = self.price_long[-1]
        
        # Skip if invalid values
        if np.isnan(hash_short_val) or np.isnan(hash_long_val):
            return
        
        # Get signal arrays
        capitulation_arr = self.capitulation.values if hasattr(self.capitulation, 'values') else self.capitulation
        recovered_arr = self.recovered.values if hasattr(self.recovered, 'values') else self.recovered
        
        # Entry logic based on Hash Ribbons
        # Buy signal conditions:
        # 1. Price MA cross over (10 > 20) AND recently recovered from capitulation
        # 2. OR hash rate just recovered (crossed back over)
        if not self.position:
            # Calculate bars since signals
            bars_since_recovered = self.bars_since(recovered_arr, current_idx)
            bars_since_capitulation = self.bars_since(capitulation_arr, current_idx)
            
            # Price MA crossover
            price_cross = price_short_val > price_long_val
            price_was_below = len(self.data) > 1 and self.price_short[-2] <= self.price_long[-2]
            price_crossover = price_cross and price_was_below
            
            # Buy condition 1: Price crossover after recovery
            buy_signal_1 = (price_crossover and 
                           bars_since_recovered < bars_since_capitulation and
                           bars_since_recovered < 30)  # Within 30 bars of recovery
            
            # Buy condition 2: Hash rate recovery OR price already above MA when recovery happens
            buy_signal_2 = (recovered_arr[current_idx] == 1 and price_short_val > price_long_val)
            
            if buy_signal_1 or buy_signal_2:
                signal_type = "Price Cross + Recovery" if buy_signal_1 else "Hash Recovery"
                print(f"🚀 {signal_type} BUY Signal! Price: ${current_price:.2f} 🌙")
                
                # Calculate stop loss and take profit
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                
                self.buy(sl=sl_price, tp=tp_price)
        
        # Exit logic
        # Exit if new capitulation starts
        elif self.position and capitulation_arr[current_idx] == 1:
            print(f"📉 New Capitulation! Exiting position at ${current_price:.2f}")
            self.position.close()

# Run single backtest
bt = Backtest(data, HashRibbonsStrategy, cash=10000000, commission=0.00045)

print("\n🌙 ===== HASH RIBBONS STRATEGY - BASE ===== 🌙")
print(f"Hash Short Period: {HASH_SHORT_PERIOD} days")
print(f"Hash Long Period: {HASH_LONG_PERIOD} days")
print(f"Price Short Period: {PRICE_SHORT_PERIOD} days")
print(f"Price Long Period: {PRICE_LONG_PERIOD} days")

stats_default = bt.run()
print(stats_default)

# Optional: Show plot (commented out for multi-data testing)
# bt.plot()

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING HASH RIBBONS BASE STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(HashRibbonsStrategy, 'HashRibbons_Base')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/HashRibbons_Base.csv")