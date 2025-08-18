import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

print("🚀 Moon Dev's Market Cipher-Inspired Strategy Loading... 🌙")

# Load the data
# Load the data
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/btc_1min_test_1.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/BTC-USD-1h-2018-1-01T00_00.csv'
#data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/crypto_data/ETH-6h-1000wks-data.csv'
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-1000wks-data.csv'
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

class MarketCipherStrategy(Strategy):
    # Wave Trend parameters
    wt_channel_len = 9
    wt_average_len = 12
    wt_ma_len = 3
    
    # StochRSI parameters
    rsi_period = 14
    stoch_period = 14
    smooth_k = 3
    smooth_d = 3
    
    # MFI parameters
    mfi_period = 14
    
    # Thresholds
    wt_oversold = -60
    wt_overbought = 60
    stoch_oversold = 20
    stoch_overbought = 80
    mfi_oversold = 25
    mfi_overbought = 75
    
    # Risk management
    take_profit = 0.035
    stop_loss = 0.02
    
    # Divergence detection
    divergence_lookback = 10
    
    def init(self):
        # Calculate Wave Trend Oscillator (simplified version)
        hlc3 = (self.data.High + self.data.Low + self.data.Close) / 3
        esa = talib.EMA(hlc3, self.wt_channel_len)
        d = talib.EMA(np.abs(hlc3 - esa), self.wt_channel_len)
        ci = (hlc3 - esa) / (0.015 * d)
        wt1 = talib.EMA(ci, self.wt_average_len)
        wt2 = talib.SMA(wt1, self.wt_ma_len)
        
        self.wt1 = self.I(lambda: wt1)
        self.wt2 = self.I(lambda: wt2)
        
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
        
        # Calculate MFI
        self.mfi = self.I(talib.MFI, 
                          self.data.High, 
                          self.data.Low, 
                          self.data.Close, 
                          self.data.Volume, 
                          self.mfi_period)
        
        # VWAP for trend context
        self.vwap = self.I(self.calculate_vwap)
        
        # ATR for volatility-based stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)
        
        # Volume analysis
        self.volume_ma = self.I(talib.SMA, self.data.Volume, 20)
        self.volume_std = self.I(lambda: pd.Series(self.data.Volume).rolling(20).std().values)
    
    def calculate_vwap(self):
        typical_price = (self.data.High + self.data.Low + self.data.Close) / 3
        volume_price = typical_price * self.data.Volume
        vwap_values = []
        
        for i in range(len(self.data)):
            if i < 20:
                vwap_values.append(np.nan)
            else:
                start_idx = max(0, i - 19)
                end_idx = i + 1
                volume_sum = np.sum(self.data.Volume[start_idx:end_idx])
                volume_price_sum = np.sum(volume_price[start_idx:end_idx])
                
                if volume_sum > 0:
                    vwap_values.append(volume_price_sum / volume_sum)
                else:
                    vwap_values.append(np.nan)
        
        return np.array(vwap_values)
    
    def detect_divergence(self, price_data, indicator_data, lookback):
        """Detect bullish and bearish divergences"""
        if len(price_data) < lookback * 2:
            return 0, 0
        
        # Find recent swing highs and lows
        price_recent = price_data[-lookback:]
        indicator_recent = indicator_data[-lookback:]
        price_previous = price_data[-lookback*2:-lookback]
        indicator_previous = indicator_data[-lookback*2:-lookback]
        
        # Bullish divergence: price makes lower low, indicator makes higher low
        if (min(price_recent) < min(price_previous) and 
            min(indicator_recent) > min(indicator_previous)):
            return 1, 0
        
        # Bearish divergence: price makes higher high, indicator makes lower high
        if (max(price_recent) > max(price_previous) and 
            max(indicator_recent) < max(indicator_previous)):
            return 0, 1
        
        return 0, 0
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.wt_average_len, self.rsi_period, self.mfi_period, 20):
            return
        
        current_price = self.data.Close[-1]
        current_wt1 = self.wt1[-1]
        current_wt2 = self.wt2[-1]
        current_stoch_k = self.stoch_k[-1]
        current_mfi = self.mfi[-1]
        current_vwap = self.vwap[-1]
        current_volume = self.data.Volume[-1]
        current_atr = self.atr[-1]
        
        # Skip if invalid values
        if pd.isna(current_wt1) or pd.isna(current_stoch_k) or pd.isna(current_mfi) or pd.isna(current_vwap) or pd.isna(current_atr):
            return
        
        # Volume analysis
        volume_surge = False
        if not pd.isna(self.volume_ma[-1]) and not pd.isna(self.volume_std[-1]):
            volume_z_score = (current_volume - self.volume_ma[-1]) / (self.volume_std[-1] + 1e-10)
            volume_surge = volume_z_score > 2
        
        # Detect divergences
        bullish_div, bearish_div = self.detect_divergence(
            self.data.Close, 
            self.wt1, 
            self.divergence_lookback
        )
        
        # Calculate signal confluence
        long_signals = 0
        short_signals = 0
        
        # Wave Trend signals
        if current_wt1 < self.wt_oversold and crossover(self.wt1, self.wt2):
            long_signals += 2  # Weight WT signals more heavily
        if current_wt1 > self.wt_overbought and crossover(self.wt2, self.wt1):
            short_signals += 2
        
        # StochRSI signals
        if current_stoch_k < self.stoch_oversold:
            long_signals += 1
        if current_stoch_k > self.stoch_overbought:
            short_signals += 1
        
        # MFI signals
        if current_mfi < self.mfi_oversold:
            long_signals += 1
        if current_mfi > self.mfi_overbought:
            short_signals += 1
        
        # VWAP position
        if current_price > current_vwap:
            long_signals += 1
        else:
            short_signals += 1
        
        # Divergence signals (strongest)
        if bullish_div:
            long_signals += 3
        if bearish_div:
            short_signals += 3
        
        # Dynamic position sizing based on ATR
        atr_multiplier = 2.5 if volume_surge else 2.0
        dynamic_sl = current_atr * atr_multiplier
        
        # Long Entry: Strong confluence of signals
        if (not self.position and 
            long_signals >= 4 and
            (volume_surge or bullish_div)):
            
            sl_price = max(
                current_price * (1 - self.stop_loss),
                current_price - dynamic_sl
            )
            
            self.buy(
                sl=sl_price,
                tp=current_price * (1 + self.take_profit)
            )
        
        # Short Entry: Strong confluence of signals
        elif (not self.position and 
              short_signals >= 4 and
              (volume_surge or bearish_div)):
            
            sl_price = min(
                current_price * (1 + self.stop_loss),
                current_price + dynamic_sl
            )
            
            self.sell(
                sl=sl_price,
                tp=current_price * (1 - self.take_profit)
            )
        
        # Advanced exit conditions
        elif self.position:
            if self.position.is_long:
                # Exit on bearish WT cross in overbought or strong MFI overbought
                if (current_wt1 > 70 and crossover(self.wt2, self.wt1)) or current_mfi > 85:
                    self.position.close()
                # Trailing stop based on VWAP
                elif current_price < current_vwap * 0.995:
                    self.position.close()
                    
            elif self.position.is_short:
                # Exit on bullish WT cross in oversold or strong MFI oversold
                if (current_wt1 < -70 and crossover(self.wt1, self.wt2)) or current_mfi < 15:
                    self.position.close()
                # Trailing stop based on VWAP
                elif current_price > current_vwap * 1.005:
                    self.position.close()

# Prepare data
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.dropna()
print(f"✅ Data cleaned! {len(data)} valid rows remaining 🚀")

# Create and run backtest
bt = Backtest(data, MarketCipherStrategy, cash=100000, commission=0.002)

# Run with default parameters
print("\n🌙 ===== MARKET CIPHER-INSPIRED STRATEGY - DEFAULT PARAMETERS ===== 🌙")
stats_default = bt.run()
print(stats_default)

# Optimize for Sortino ratio
print("\n🚀 Optimizing for Sortino Ratio...")
optimization_results = bt.optimize(
    wt_channel_len=range(7, 12, 2),
    wt_average_len=range(10, 15, 2),
    wt_ma_len=[3, 4],
    rsi_period=range(12, 18, 3),
    stoch_period=range(12, 18, 3),
    mfi_period=range(12, 18, 3),
    wt_oversold=range(-70, -50, 10),
    wt_overbought=range(50, 71, 10),
    mfi_oversold=range(20, 31, 5),
    mfi_overbought=range(70, 81, 5),
    take_profit=[i / 100 for i in range(3, 5)],
    stop_loss=[i / 100 for i in range(1, 3)],
    divergence_lookback=range(8, 13, 2),
    maximize='Sortino Ratio',
    constraint=lambda p: (p.take_profit > p.stop_loss and 
                         p.wt_oversold < p.wt_overbought and
                         p.mfi_oversold < p.mfi_overbought)
)

print("\n🚀 ===== MARKET CIPHER OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"Wave Trend Channel: {optimization_results._strategy.wt_channel_len}")
print(f"Wave Trend Average: {optimization_results._strategy.wt_average_len}")
print(f"Wave Trend MA: {optimization_results._strategy.wt_ma_len}")
print(f"RSI Period: {optimization_results._strategy.rsi_period}")
print(f"MFI Period: {optimization_results._strategy.mfi_period}")
print(f"WT Oversold: {optimization_results._strategy.wt_oversold}")
print(f"WT Overbought: {optimization_results._strategy.wt_overbought}")
print(f"MFI Oversold: {optimization_results._strategy.mfi_oversold}")
print(f"MFI Overbought: {optimization_results._strategy.mfi_overbought}")
print(f"Divergence Lookback: {optimization_results._strategy.divergence_lookback}")
print(f"Take Profit: {optimization_results._strategy.take_profit:.3f}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.3f}")