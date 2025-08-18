import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

print("🚀 Moon Dev's StochRSI Strategy Loading... 🌙")

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

class StochRSIStrategy(Strategy):
    # Strategy parameters
    rsi_period = 14          # RSI calculation period
    stoch_period = 14        # Stochastic period
    smooth_k = 3             # K smoothing
    smooth_d = 3             # D smoothing
    oversold = 20            # Oversold threshold
    overbought = 80          # Overbought threshold
    take_profit = 0.025      # 2.5% take profit
    stop_loss = 0.015        # 1.5% stop loss
    
    def init(self):
        # Calculate RSI
        rsi = talib.RSI(self.data.Close, self.rsi_period)
        
        # Calculate StochRSI
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
        
        # Add EMA for trend filter
        self.ema_fast = self.I(talib.EMA, self.data.Close, 20)
        self.ema_slow = self.I(talib.EMA, self.data.Close, 50)
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.rsi_period, self.stoch_period, 50):
            return
        
        current_price = self.data.Close[-1]
        current_k = self.stoch_k[-1]
        current_d = self.stoch_d[-1]
        prev_k = self.stoch_k[-2] if len(self.stoch_k) > 1 else current_k
        prev_d = self.stoch_d[-2] if len(self.stoch_d) > 1 else current_d
        
        # Skip if invalid values
        if pd.isna(current_k) or pd.isna(current_d) or pd.isna(self.ema_fast[-1]) or pd.isna(self.ema_slow[-1]):
            return
        
        # Long Entry: StochRSI oversold with bullish crossover and uptrend
        if (not self.position and 
            current_k < self.oversold and
            current_k > prev_k and
            crossover(self.stoch_k, self.stoch_d) and
            self.ema_fast[-1] > self.ema_slow[-1]):
            
            self.buy(
                sl=current_price * (1 - self.stop_loss),
                tp=current_price * (1 + self.take_profit)
            )
        
        # Short Entry: StochRSI overbought with bearish crossover and downtrend
        elif (not self.position and 
              current_k > self.overbought and
              current_k < prev_k and
              crossover(self.stoch_d, self.stoch_k) and
              self.ema_fast[-1] < self.ema_slow[-1]):
            
            self.sell(
                sl=current_price * (1 + self.stop_loss),
                tp=current_price * (1 - self.take_profit)
            )
        
        # Exit on extreme readings
        elif self.position:
            if self.position.is_long and current_k > 90:
                self.position.close()
            elif self.position.is_short and current_k < 10:
                self.position.close()

# Prepare data
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.dropna()
print(f"✅ Data cleaned! {len(data)} valid rows remaining 🚀")

# Create and run backtest
bt = Backtest(data, StochRSIStrategy, cash=100000, commission=0.002)

# Run with default parameters
print("\n🌙 ===== STOCHRSI STRATEGY - DEFAULT PARAMETERS ===== 🌙")
stats_default = bt.run()
print(stats_default)

# Optimize for Sortino ratio
print("\n🚀 Optimizing for Sortino Ratio...")
optimization_results = bt.optimize(
    rsi_period=range(10, 21, 2),
    stoch_period=range(10, 21, 2),
    smooth_k=range(2, 6),
    smooth_d=range(2, 6),
    oversold=range(15, 31, 5),
    overbought=range(70, 86, 5),
    take_profit=[i / 1000 for i in range(15, 41, 5)],
    stop_loss=[i / 1000 for i in range(10, 26, 5)],
    maximize='Sortino Ratio',
    constraint=lambda p: p.take_profit > p.stop_loss
)

print("\n🚀 ===== STOCHRSI OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"RSI Period: {optimization_results._strategy.rsi_period}")
print(f"Stoch Period: {optimization_results._strategy.stoch_period}")
print(f"Smooth K: {optimization_results._strategy.smooth_k}")
print(f"Smooth D: {optimization_results._strategy.smooth_d}")
print(f"Oversold: {optimization_results._strategy.oversold}")
print(f"Overbought: {optimization_results._strategy.overbought}")
print(f"Take Profit: {optimization_results._strategy.take_profit:.3f}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.3f}")