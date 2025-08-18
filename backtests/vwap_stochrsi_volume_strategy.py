import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

print("🚀 Moon Dev's VWAP + StochRSI + Volume Profile Strategy Loading... 🌙")

# Load the data
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/btc_1min_test_1.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/BTC-USD-1h-2018-1-01T00_00.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/ETH-6h-1000wks-data.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-1000wks-data.csv'
print(f"📊 Loading Moon Dev's crypto data from: {data_path}")

# Adaptive header detection
try:
    sample = pd.read_csv(data_path, nrows=5)
    if sample.iloc[0].dtype == 'object' or any(isinstance(val, str) for val in sample.iloc[0].values):
        data = pd.read_csv(data_path, parse_dates=[0], index_col=0)
    else:
        data = pd.read_csv(data_path, header=None, parse_dates=[0], index_col=0)
        data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
except:
    data = pd.read_csv(data_path, parse_dates=[0], index_col=0)

print(f"✅ Data loaded successfully! Dataset has {len(data)} rows 🌙")

class VWAPStochRSIVolumeStrategy(Strategy):
    # VWAP parameters
    vwap_period = 20
    vwap_deviation = 0.02
    
    # StochRSI parameters
    rsi_period = 14
    stoch_period = 14
    smooth_k = 3
    smooth_d = 3
    stoch_oversold = 30
    stoch_overbought = 70
    
    # Volume Profile parameters
    volume_lookback = 50
    volume_threshold = 1.8
    poc_sensitivity = 0.005  # Point of Control sensitivity
    
    # Risk management
    take_profit = 0.028
    stop_loss = 0.018
    
    def init(self):
        # Calculate VWAP with standard deviation bands
        self.vwap = self.I(self.calculate_vwap)
        self.vwap_upper = self.I(self.calculate_vwap_bands, upper=True)
        self.vwap_lower = self.I(self.calculate_vwap_bands, upper=False)
        
        # Calculate StochRSI
        rsi = talib.RSI(self.data.Close, self.rsi_period)
        stoch_k, stoch_d = talib.STOCH(
            rsi, rsi, rsi,
            fastk_period=self.stoch_period,
            slowk_period=self.smooth_k,
            slowk_matype=0,
            slowd_period=self.smooth_d,
            slowd_matype=0
        )
        
        self.stoch_k = self.I(lambda: stoch_k)
        self.stoch_d = self.I(lambda: stoch_d)
        
        # Volume analysis
        self.volume_ma = self.I(talib.SMA, self.data.Volume, 20)
        self.volume_profile_poc = self.I(self.calculate_volume_profile_poc)
        
        # OBV for volume confirmation
        self.obv = self.I(talib.OBV, self.data.Close, self.data.Volume)
        self.obv_ma = self.I(talib.EMA, self.obv, 20)
    
    def calculate_vwap(self):
        typical_price = (self.data.High + self.data.Low + self.data.Close) / 3
        volume_price = typical_price * self.data.Volume
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
    
    def calculate_vwap_bands(self, upper=True):
        vwap = self.calculate_vwap()
        typical_price = (self.data.High + self.data.Low + self.data.Close) / 3
        band_values = []
        
        for i in range(len(self.data)):
            if i < self.vwap_period - 1:
                band_values.append(np.nan)
            else:
                start_idx = max(0, i - self.vwap_period + 1)
                end_idx = i + 1
                
                # Calculate standard deviation
                prices = typical_price[start_idx:end_idx]
                volumes = self.data.Volume[start_idx:end_idx]
                vwap_val = vwap[i]
                
                if not pd.isna(vwap_val):
                    squared_diff = (prices - vwap_val) ** 2
                    weighted_variance = np.sum(squared_diff * volumes) / np.sum(volumes)
                    std_dev = np.sqrt(weighted_variance)
                    
                    if upper:
                        band_values.append(vwap_val + (std_dev * 2))
                    else:
                        band_values.append(vwap_val - (std_dev * 2))
                else:
                    band_values.append(np.nan)
        
        return np.array(band_values)
    
    def calculate_volume_profile_poc(self):
        """Calculate Point of Control (price level with highest volume)"""
        poc_values = []
        
        for i in range(len(self.data)):
            if i < self.volume_lookback:
                poc_values.append(np.nan)
            else:
                start_idx = i - self.volume_lookback + 1
                end_idx = i + 1
                
                # Create price bins
                prices = self.data.Close[start_idx:end_idx]
                volumes = self.data.Volume[start_idx:end_idx]
                
                price_min = np.min(prices)
                price_max = np.max(prices)
                n_bins = 20
                
                bins = np.linspace(price_min, price_max, n_bins)
                volume_profile = np.zeros(n_bins - 1)
                
                # Accumulate volume in each price bin
                for j, price in enumerate(prices):
                    bin_idx = np.searchsorted(bins, price) - 1
                    if 0 <= bin_idx < len(volume_profile):
                        volume_profile[bin_idx] += volumes[j]
                
                # Find POC
                poc_idx = np.argmax(volume_profile)
                poc = (bins[poc_idx] + bins[poc_idx + 1]) / 2
                poc_values.append(poc)
        
        return np.array(poc_values)
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.vwap_period, self.rsi_period, self.volume_lookback):
            return
        
        current_price = self.data.Close[-1]
        current_vwap = self.vwap[-1]
        current_vwap_upper = self.vwap_upper[-1]
        current_vwap_lower = self.vwap_lower[-1]
        current_stoch_k = self.stoch_k[-1]
        current_stoch_d = self.stoch_d[-1]
        current_volume = self.data.Volume[-1]
        current_volume_ma = self.volume_ma[-1]
        current_poc = self.volume_profile_poc[-1]
        current_obv = self.obv[-1]
        current_obv_ma = self.obv_ma[-1]
        
        # Skip if invalid values
        if pd.isna(current_vwap) or pd.isna(current_stoch_k) or pd.isna(current_poc):
            return
        
        # Volume analysis
        volume_spike = current_volume > current_volume_ma * self.volume_threshold
        obv_bullish = current_obv > current_obv_ma
        obv_bearish = current_obv < current_obv_ma
        
        # Price relative to VWAP and POC
        near_poc = abs(current_price - current_poc) / current_price < self.poc_sensitivity
        at_vwap_lower = current_price <= current_vwap_lower
        at_vwap_upper = current_price >= current_vwap_upper
        
        # Long Entry Conditions
        if (not self.position and 
            at_vwap_lower and
            current_stoch_k < self.stoch_oversold and
            crossover(self.stoch_k, self.stoch_d) and
            volume_spike and
            obv_bullish):
            
            self.buy(
                sl=current_price * (1 - self.stop_loss),
                tp=current_price * (1 + self.take_profit)
            )
        
        # Short Entry Conditions
        elif (not self.position and 
              at_vwap_upper and
              current_stoch_k > self.stoch_overbought and
              crossover(self.stoch_d, self.stoch_k) and
              volume_spike and
              obv_bearish):
            
            self.sell(
                sl=current_price * (1 + self.stop_loss),
                tp=current_price * (1 - self.take_profit)
            )
        
        # Mean reversion exits
        elif self.position:
            if self.position.is_long:
                # Exit at VWAP or if StochRSI becomes overbought
                if current_price >= current_vwap or current_stoch_k > 85:
                    self.position.close()
            elif self.position.is_short:
                # Exit at VWAP or if StochRSI becomes oversold
                if current_price <= current_vwap or current_stoch_k < 15:
                    self.position.close()

# Prepare data
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.dropna()
print(f"✅ Data cleaned! {len(data)} valid rows remaining 🚀")

# Create and run backtest
bt = Backtest(data, VWAPStochRSIVolumeStrategy, cash=100000, commission=0.002)

# Run with default parameters
print("\n🌙 ===== VWAP + STOCHRSI + VOLUME PROFILE - DEFAULT PARAMETERS ===== 🌙")
stats_default = bt.run()
print(stats_default)

# Optimize for Sortino ratio
print("\n🚀 Optimizing for Sortino Ratio...")
optimization_results = bt.optimize(
    vwap_period=range(15, 31, 5),
    rsi_period=range(12, 18, 3),
    stoch_period=range(12, 18, 3),
    smooth_k=[2, 3, 4],
    smooth_d=[2, 3, 4],
    stoch_oversold=range(25, 36, 5),
    stoch_overbought=range(65, 76, 5),
    volume_lookback=range(40, 61, 10),
    volume_threshold=[1.5, 1.8, 2.0, 2.2],
    take_profit=[i / 1000 for i in range(20, 36, 5)],
    stop_loss=[i / 1000 for i in range(10, 21, 5)],
    maximize='Sortino Ratio',
    constraint=lambda p: (p.take_profit > p.stop_loss and
                         p.stoch_oversold < p.stoch_overbought)
)

print("\n🚀 ===== VWAP + STOCHRSI + VOLUME OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"VWAP Period: {optimization_results._strategy.vwap_period}")
print(f"RSI Period: {optimization_results._strategy.rsi_period}")
print(f"Stoch Period: {optimization_results._strategy.stoch_period}")
print(f"Volume Lookback: {optimization_results._strategy.volume_lookback}")
print(f"Volume Threshold: {optimization_results._strategy.volume_threshold:.1f}x")
print(f"Take Profit: {optimization_results._strategy.take_profit:.3f}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.3f}")