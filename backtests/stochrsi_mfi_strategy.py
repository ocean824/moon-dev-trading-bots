import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

print("🚀 Moon Dev's StochRSI + MFI Combined Strategy Loading... 🌙")

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

class StochRSIMFIStrategy(Strategy):
    # StochRSI parameters
    rsi_period = 14
    stoch_period = 14
    smooth_k = 3
    smooth_d = 3
    stoch_oversold = 25
    stoch_overbought = 75
    
    # MFI parameters
    mfi_period = 14
    mfi_oversold = 30
    mfi_overbought = 70
    
    # Risk management
    take_profit = 0.03
    stop_loss = 0.02
    
    # Confirmation threshold
    confirmation_threshold = 2  # Need 2 out of 3 signals
    
    def init(self):
        # Calculate RSI and StochRSI
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
        
        # Add Bollinger Bands for volatility context
        bb_upper, bb_middle, bb_lower = talib.BBANDS(
            self.data.Close, 
            timeperiod=20, 
            nbdevup=2, 
            nbdevdn=2, 
            matype=0
        )
        self.bb_upper = self.I(lambda: bb_upper)
        self.bb_lower = self.I(lambda: bb_lower)
        self.bb_middle = self.I(lambda: bb_middle)
        
        # Volume moving average
        self.volume_ma = self.I(talib.SMA, self.data.Volume, 20)
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.rsi_period, self.mfi_period, 20):
            return
        
        current_price = self.data.Close[-1]
        current_stoch_k = self.stoch_k[-1]
        current_stoch_d = self.stoch_d[-1]
        current_mfi = self.mfi[-1]
        current_volume = self.data.Volume[-1]
        
        # Skip if invalid values
        if pd.isna(current_stoch_k) or pd.isna(current_mfi) or pd.isna(self.bb_upper[-1]) or pd.isna(self.volume_ma[-1]):
            return
        
        # Calculate signal strengths
        long_signals = 0
        short_signals = 0
        
        # StochRSI signals
        if current_stoch_k < self.stoch_oversold and crossover(self.stoch_k, self.stoch_d):
            long_signals += 1
        if current_stoch_k > self.stoch_overbought and crossover(self.stoch_d, self.stoch_k):
            short_signals += 1
        
        # MFI signals
        if current_mfi < self.mfi_oversold:
            long_signals += 1
        if current_mfi > self.mfi_overbought:
            short_signals += 1
        
        # Bollinger Band signals
        if current_price < self.bb_lower[-1]:
            long_signals += 1
        if current_price > self.bb_upper[-1]:
            short_signals += 1
        
        # Volume confirmation
        volume_surge = current_volume > self.volume_ma[-1] * 1.5
        
        # Long Entry: Multiple oversold signals with volume
        if (not self.position and 
            long_signals >= self.confirmation_threshold and
            volume_surge):
            
            self.buy(
                sl=current_price * (1 - self.stop_loss),
                tp=current_price * (1 + self.take_profit)
            )
        
        # Short Entry: Multiple overbought signals with volume
        elif (not self.position and 
              short_signals >= self.confirmation_threshold and
              volume_surge):
            
            self.sell(
                sl=current_price * (1 + self.stop_loss),
                tp=current_price * (1 - self.take_profit)
            )
        
        # Dynamic exits based on MFI divergence
        elif self.position:
            if self.position.is_long:
                # Exit long if MFI shows overbought or StochRSI crosses down from overbought
                if current_mfi > 80 or (current_stoch_k > 80 and crossover(self.stoch_d, self.stoch_k)):
                    self.position.close()
            elif self.position.is_short:
                # Exit short if MFI shows oversold or StochRSI crosses up from oversold
                if current_mfi < 20 or (current_stoch_k < 20 and crossover(self.stoch_k, self.stoch_d)):
                    self.position.close()

# Prepare data
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.dropna()
print(f"✅ Data cleaned! {len(data)} valid rows remaining 🚀")

# Create and run backtest
bt = Backtest(data, StochRSIMFIStrategy, cash=100000, commission=0.002)

# Run with default parameters
print("\n🌙 ===== STOCHRSI + MFI STRATEGY - DEFAULT PARAMETERS ===== 🌙")
stats_default = bt.run()
print(stats_default)

# Optimize for Sortino ratio
print("\n🚀 Optimizing for Sortino Ratio...")
optimization_results = bt.optimize(
    rsi_period=range(10, 21, 5),
    stoch_period=range(10, 21, 5),
    smooth_k=range(2, 5),
    smooth_d=range(2, 5),
    stoch_oversold=range(20, 36, 5),
    stoch_overbought=range(65, 81, 5),
    mfi_period=range(10, 21, 5),
    mfi_oversold=range(20, 36, 5),
    mfi_overbought=range(65, 81, 5),
    take_profit=[i / 100 for i in range(2, 5)],
    stop_loss=[i / 100 for i in range(1, 3)],
    confirmation_threshold=[2, 3],
    maximize='Sortino Ratio',
    constraint=lambda p: (p.take_profit > p.stop_loss and 
                         p.stoch_oversold < p.stoch_overbought and
                         p.mfi_oversold < p.mfi_overbought)
)

print("\n🚀 ===== STOCHRSI + MFI OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"RSI Period: {optimization_results._strategy.rsi_period}")
print(f"Stoch Period: {optimization_results._strategy.stoch_period}")
print(f"Stoch Oversold: {optimization_results._strategy.stoch_oversold}")
print(f"Stoch Overbought: {optimization_results._strategy.stoch_overbought}")
print(f"MFI Period: {optimization_results._strategy.mfi_period}")
print(f"MFI Oversold: {optimization_results._strategy.mfi_oversold}")
print(f"MFI Overbought: {optimization_results._strategy.mfi_overbought}")
print(f"Confirmation Threshold: {optimization_results._strategy.confirmation_threshold}")
print(f"Take Profit: {optimization_results._strategy.take_profit:.3f}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.3f}")