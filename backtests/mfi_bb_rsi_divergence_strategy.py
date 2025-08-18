import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

print("🚀 Moon Dev's MFI + Bollinger Bands + RSI Divergence Strategy Loading... 🌙")

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

class MFIBBRSIDivergenceStrategy(Strategy):
    # MFI parameters
    mfi_period = 14
    mfi_oversold = 25
    mfi_overbought = 75
    
    # Bollinger Bands parameters
    bb_period = 20
    bb_dev = 2.0
    bb_squeeze_threshold = 0.015  # BB width threshold for squeeze
    
    # RSI parameters
    rsi_period = 14
    rsi_oversold = 30
    rsi_overbought = 70
    
    # Divergence parameters
    divergence_lookback = 12
    divergence_threshold = 0.02  # Minimum price movement for divergence
    
    # Risk management
    take_profit = 0.032
    stop_loss = 0.018
    
    def init(self):
        # Calculate MFI
        self.mfi = self.I(talib.MFI,
                          self.data.High,
                          self.data.Low,
                          self.data.Close,
                          self.data.Volume,
                          self.mfi_period)
        
        # Calculate Bollinger Bands
        bb_upper, bb_middle, bb_lower = talib.BBANDS(
            self.data.Close,
            timeperiod=self.bb_period,
            nbdevup=self.bb_dev,
            nbdevdn=self.bb_dev,
            matype=0
        )
        self.bb_upper = self.I(lambda: bb_upper)
        self.bb_middle = self.I(lambda: bb_middle)
        self.bb_lower = self.I(lambda: bb_lower)
        
        # BB width for squeeze detection
        self.bb_width = self.I(lambda: (bb_upper - bb_lower) / bb_middle)
        
        # Calculate RSI
        self.rsi = self.I(talib.RSI, self.data.Close, self.rsi_period)
        
        # Calculate MACD for additional confirmation
        macd, macd_signal, macd_hist = talib.MACD(
            self.data.Close,
            fastperiod=12,
            slowperiod=26,
            signalperiod=9
        )
        self.macd = self.I(lambda: macd)
        self.macd_signal = self.I(lambda: macd_signal)
        self.macd_hist = self.I(lambda: macd_hist)
        
        # ATR for dynamic stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)
    
    def detect_rsi_divergence(self):
        """Detect bullish and bearish RSI divergences"""
        if len(self.data) < self.divergence_lookback * 2:
            return False, False
        
        # Get recent data
        prices = self.data.Close
        rsi_values = self.rsi
        
        # Find local extremes
        bullish_div = False
        bearish_div = False
        
        # Look for swing points
        for i in range(-self.divergence_lookback, -2):
            # Check for valid RSI values
            if pd.isna(rsi_values[i]) or pd.isna(rsi_values[-1]):
                continue
            
            # Bullish divergence: price lower low, RSI higher low
            if (prices[-1] < prices[i] * (1 - self.divergence_threshold) and
                rsi_values[-1] > rsi_values[i] and
                rsi_values[i] < self.rsi_oversold):
                bullish_div = True
            
            # Bearish divergence: price higher high, RSI lower high
            if (prices[-1] > prices[i] * (1 + self.divergence_threshold) and
                rsi_values[-1] < rsi_values[i] and
                rsi_values[i] > self.rsi_overbought):
                bearish_div = True
        
        return bullish_div, bearish_div
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.mfi_period, self.bb_period, self.rsi_period, self.divergence_lookback * 2):
            return
        
        current_price = self.data.Close[-1]
        current_mfi = self.mfi[-1]
        current_bb_upper = self.bb_upper[-1]
        current_bb_lower = self.bb_lower[-1]
        current_bb_middle = self.bb_middle[-1]
        current_bb_width = self.bb_width[-1]
        current_rsi = self.rsi[-1]
        current_macd_hist = self.macd_hist[-1]
        current_atr = self.atr[-1]
        
        # Skip if invalid values
        if pd.isna(current_mfi) or pd.isna(current_rsi) or pd.isna(current_bb_upper) or pd.isna(current_atr):
            return
        
        # Detect divergences
        bullish_div, bearish_div = self.detect_rsi_divergence()
        
        # BB squeeze detection
        bb_squeeze = current_bb_width < self.bb_squeeze_threshold
        
        # Calculate BB position
        bb_pct = (current_price - current_bb_lower) / (current_bb_upper - current_bb_lower) if current_bb_upper != current_bb_lower else 0.5
        
        # Dynamic position sizing based on ATR
        atr_multiplier = 2.0 if bb_squeeze else 1.5
        
        # Long Entry Conditions
        long_conditions = [
            current_price <= current_bb_lower,  # Price at lower band
            current_mfi < self.mfi_oversold,     # MFI oversold
            current_rsi < self.rsi_oversold,     # RSI oversold
            bullish_div,                         # RSI bullish divergence
            current_macd_hist > 0 or (current_macd_hist > self.macd_hist[-2] if len(self.macd_hist) > 1 else False)  # MACD improving
        ]
        
        if not self.position and sum(long_conditions) >= 3:
            sl_price = min(
                current_price * (1 - self.stop_loss),
                current_price - (current_atr * atr_multiplier)
            )
            
            # Dynamic TP based on BB width
            tp_multiplier = 1.5 if bb_squeeze else 1.0
            tp_price = current_price * (1 + self.take_profit * tp_multiplier)
            
            self.buy(sl=sl_price, tp=tp_price)
        
        # Short Entry Conditions
        short_conditions = [
            current_price >= current_bb_upper,    # Price at upper band
            current_mfi > self.mfi_overbought,    # MFI overbought
            current_rsi > self.rsi_overbought,    # RSI overbought
            bearish_div,                          # RSI bearish divergence
            current_macd_hist < 0 or (current_macd_hist < self.macd_hist[-2] if len(self.macd_hist) > 1 else False)  # MACD weakening
        ]
        
        if not self.position and sum(short_conditions) >= 3:
            sl_price = max(
                current_price * (1 + self.stop_loss),
                current_price + (current_atr * atr_multiplier)
            )
            
            # Dynamic TP based on BB width
            tp_multiplier = 1.5 if bb_squeeze else 1.0
            tp_price = current_price * (1 - self.take_profit * tp_multiplier)
            
            self.sell(sl=sl_price, tp=tp_price)
        
        # Advanced exit conditions
        elif self.position:
            if self.position.is_long:
                # Exit if price reaches middle band or MFI becomes overbought
                if current_price >= current_bb_middle or current_mfi > 80 or bearish_div:
                    self.position.close()
            elif self.position.is_short:
                # Exit if price reaches middle band or MFI becomes oversold
                if current_price <= current_bb_middle or current_mfi < 20 or bullish_div:
                    self.position.close()

# Prepare data
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.dropna()
print(f"✅ Data cleaned! {len(data)} valid rows remaining 🚀")

# Create and run backtest
bt = Backtest(data, MFIBBRSIDivergenceStrategy, cash=100000, commission=0.002)

# Run with default parameters
print("\n🌙 ===== MFI + BB + RSI DIVERGENCE - DEFAULT PARAMETERS ===== 🌙")
stats_default = bt.run()
print(stats_default)

# Optimize for Sortino ratio
print("\n🚀 Optimizing for Sortino Ratio...")
optimization_results = bt.optimize(
    mfi_period=range(12, 18, 3),
    mfi_oversold=range(20, 31, 5),
    mfi_overbought=range(70, 81, 5),
    bb_period=range(15, 26, 5),
    bb_dev=[1.5, 2.0, 2.5],
    rsi_period=range(12, 18, 3),
    rsi_oversold=range(25, 36, 5),
    rsi_overbought=range(65, 76, 5),
    divergence_lookback=range(10, 16, 2),
    take_profit=[i / 1000 for i in range(25, 41, 5)],
    stop_loss=[i / 1000 for i in range(15, 26, 5)],
    maximize='Sortino Ratio',
    constraint=lambda p: (p.take_profit > p.stop_loss and
                         p.mfi_oversold < p.mfi_overbought and
                         p.rsi_oversold < p.rsi_overbought)
)

print("\n🚀 ===== MFI + BB + RSI DIVERGENCE OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"MFI Period: {optimization_results._strategy.mfi_period}")
print(f"MFI Oversold: {optimization_results._strategy.mfi_oversold}")
print(f"MFI Overbought: {optimization_results._strategy.mfi_overbought}")
print(f"BB Period: {optimization_results._strategy.bb_period}")
print(f"BB Deviation: {optimization_results._strategy.bb_dev:.1f}")
print(f"RSI Period: {optimization_results._strategy.rsi_period}")
print(f"RSI Oversold: {optimization_results._strategy.rsi_oversold}")
print(f"RSI Overbought: {optimization_results._strategy.rsi_overbought}")
print(f"Divergence Lookback: {optimization_results._strategy.divergence_lookback}")
print(f"Take Profit: {optimization_results._strategy.take_profit:.3f}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.3f}")