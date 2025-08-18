import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

print("🚀 Moon Dev's Wave Trend + MACD + Volume Weighted Strategy Loading... 🌙")

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

class WaveTrendMACDVolumeStrategy(Strategy):
    # Wave Trend parameters
    wt_channel_len = 10
    wt_average_len = 21
    wt_ma_len = 4
    wt_oversold = -60
    wt_overbought = 60
    
    # MACD parameters
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    
    # Volume-weighted parameters
    vwma_period = 20
    volume_threshold = 2.0
    obv_period = 14
    
    # Risk management
    take_profit = 0.03
    stop_loss = 0.018
    atr_multiplier = 1.5
    
    def init(self):
        # Calculate Wave Trend Oscillator
        hlc3 = (self.data.High + self.data.Low + self.data.Close) / 3
        esa = talib.EMA(hlc3, self.wt_channel_len)
        d = talib.EMA(np.abs(hlc3 - esa), self.wt_channel_len)
        ci = (hlc3 - esa) / (0.015 * d)
        wt1 = talib.EMA(ci, self.wt_average_len)
        wt2 = talib.SMA(wt1, self.wt_ma_len)
        
        self.wt1 = self.I(lambda: wt1)
        self.wt2 = self.I(lambda: wt2)
        
        # Calculate MACD
        macd, macd_signal, macd_hist = talib.MACD(
            self.data.Close,
            fastperiod=self.macd_fast,
            slowperiod=self.macd_slow,
            signalperiod=self.macd_signal
        )
        self.macd = self.I(lambda: macd)
        self.macd_signal = self.I(lambda: macd_signal)
        self.macd_hist = self.I(lambda: macd_hist)
        
        # Volume-weighted moving average (VWMA)
        self.vwma = self.I(self.calculate_vwma)
        
        # On-Balance Volume with EMA
        self.obv = self.I(talib.OBV, self.data.Close, self.data.Volume)
        self.obv_ema = self.I(talib.EMA, self.obv, self.obv_period)
        
        # Chaikin Money Flow
        self.cmf = self.I(self.calculate_cmf)
        
        # Volume analysis
        self.volume_ma = self.I(talib.SMA, self.data.Volume, 20)
        self.volume_std = self.I(lambda: pd.Series(self.data.Volume).rolling(20).std().values)
        
        # ATR for dynamic stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)
        
        # Keltner Channels for squeeze detection
        kc_middle = talib.EMA(hlc3, 20)
        kc_range = talib.ATR(self.data.High, self.data.Low, self.data.Close, 10)
        self.kc_upper = self.I(lambda: kc_middle + (kc_range * 2))
        self.kc_lower = self.I(lambda: kc_middle - (kc_range * 2))
    
    def calculate_vwma(self):
        """Calculate Volume Weighted Moving Average"""
        vwma_values = []
        for i in range(len(self.data)):
            if i < self.vwma_period - 1:
                vwma_values.append(np.nan)
            else:
                start_idx = i - self.vwma_period + 1
                end_idx = i + 1
                prices = self.data.Close[start_idx:end_idx]
                volumes = self.data.Volume[start_idx:end_idx]
                
                if np.sum(volumes) > 0:
                    vwma = np.sum(prices * volumes) / np.sum(volumes)
                    vwma_values.append(vwma)
                else:
                    vwma_values.append(np.nan)
        
        return np.array(vwma_values)
    
    def calculate_cmf(self):
        """Calculate Chaikin Money Flow"""
        cmf_values = []
        period = 21
        
        for i in range(len(self.data)):
            if i < period - 1:
                cmf_values.append(np.nan)
            else:
                start_idx = i - period + 1
                end_idx = i + 1
                
                high = self.data.High[start_idx:end_idx]
                low = self.data.Low[start_idx:end_idx]
                close = self.data.Close[start_idx:end_idx]
                volume = self.data.Volume[start_idx:end_idx]
                
                # Money Flow Multiplier
                mfm = ((close - low) - (high - close)) / (high - low + 1e-10)
                
                # Money Flow Volume
                mfv = mfm * volume
                
                # CMF
                cmf = np.sum(mfv) / (np.sum(volume) + 1e-10)
                cmf_values.append(cmf)
        
        return np.array(cmf_values)
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.wt_average_len, self.macd_slow, self.vwma_period, 21):
            return
        
        current_price = self.data.Close[-1]
        current_wt1 = self.wt1[-1]
        current_wt2 = self.wt2[-1]
        prev_wt1 = self.wt1[-2] if len(self.wt1) > 1 else current_wt1
        current_macd = self.macd[-1]
        current_macd_signal = self.macd_signal[-1]
        current_macd_hist = self.macd_hist[-1]
        prev_macd_hist = self.macd_hist[-2] if len(self.macd_hist) > 1 else current_macd_hist
        current_vwma = self.vwma[-1]
        current_obv = self.obv[-1]
        current_obv_ema = self.obv_ema[-1]
        current_cmf = self.cmf[-1]
        current_volume = self.data.Volume[-1]
        current_volume_ma = self.volume_ma[-1]
        current_atr = self.atr[-1]
        
        # Skip if invalid values
        if pd.isna(current_wt1) or pd.isna(current_macd) or pd.isna(current_vwma) or pd.isna(current_cmf) or pd.isna(current_atr):
            return
        
        # Volume analysis
        volume_surge = current_volume > current_volume_ma * self.volume_threshold
        obv_bullish = current_obv > current_obv_ema
        obv_bearish = current_obv < current_obv_ema
        cmf_bullish = current_cmf > 0.1
        cmf_bearish = current_cmf < -0.1
        
        # Wave Trend signals
        wt_bullish_cross = crossover(self.wt1, self.wt2) and current_wt1 < self.wt_oversold
        wt_bearish_cross = crossover(self.wt2, self.wt1) and current_wt1 > self.wt_overbought
        wt_momentum_up = current_wt1 > prev_wt1 and current_wt1 < 0
        wt_momentum_down = current_wt1 < prev_wt1 and current_wt1 > 0
        
        # MACD signals
        macd_bullish_cross = crossover(self.macd, self.macd_signal)
        macd_bearish_cross = crossover(self.macd_signal, self.macd)
        macd_histogram_rising = current_macd_hist > prev_macd_hist
        macd_histogram_falling = current_macd_hist < prev_macd_hist
        
        # Price relative to VWMA
        above_vwma = current_price > current_vwma
        below_vwma = current_price < current_vwma
        
        # Calculate entry scores
        long_score = sum([
            wt_bullish_cross * 2,          # Weight WT cross heavily
            wt_momentum_up,
            macd_bullish_cross * 1.5,      # Weight MACD cross
            macd_histogram_rising,
            above_vwma,
            obv_bullish,
            cmf_bullish * 1.5,              # Weight money flow
            volume_surge * 2                # Weight volume surge heavily
        ])
        
        short_score = sum([
            wt_bearish_cross * 2,           # Weight WT cross heavily
            wt_momentum_down,
            macd_bearish_cross * 1.5,       # Weight MACD cross
            macd_histogram_falling,
            below_vwma,
            obv_bearish,
            cmf_bearish * 1.5,              # Weight money flow
            volume_surge * 2                # Weight volume surge heavily
        ])
        
        # Long Entry
        if not self.position and long_score >= 5:
            sl_price = max(
                current_price * (1 - self.stop_loss),
                current_price - (current_atr * self.atr_multiplier)
            )
            
            self.buy(
                sl=sl_price,
                tp=current_price * (1 + self.take_profit)
            )
        
        # Short Entry
        elif not self.position and short_score >= 5:
            sl_price = min(
                current_price * (1 + self.stop_loss),
                current_price + (current_atr * self.atr_multiplier)
            )
            
            self.sell(
                sl=sl_price,
                tp=current_price * (1 - self.take_profit)
            )
        
        # Dynamic exits
        elif self.position:
            if self.position.is_long:
                # Exit on WT overbought, MACD bearish cross, or CMF turning negative
                exit_conditions = [
                    current_wt1 > 80,
                    wt_bearish_cross,
                    macd_bearish_cross,
                    current_cmf < -0.2,
                    current_price < current_vwma * 0.98
                ]
                if sum(exit_conditions) >= 2:
                    self.position.close()
                    
            elif self.position.is_short:
                # Exit on WT oversold, MACD bullish cross, or CMF turning positive
                exit_conditions = [
                    current_wt1 < -80,
                    wt_bullish_cross,
                    macd_bullish_cross,
                    current_cmf > 0.2,
                    current_price > current_vwma * 1.02
                ]
                if sum(exit_conditions) >= 2:
                    self.position.close()

# Prepare data
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.dropna()
print(f"✅ Data cleaned! {len(data)} valid rows remaining 🚀")

# Create and run backtest
bt = Backtest(data, WaveTrendMACDVolumeStrategy, cash=100000, commission=0.002)

# Run with default parameters
print("\n🌙 ===== WAVE TREND + MACD + VOLUME - DEFAULT PARAMETERS ===== 🌙")
stats_default = bt.run()
print(stats_default)

# Optimize for Sortino ratio
print("\n🚀 Optimizing for Sortino Ratio...")
optimization_results = bt.optimize(
    wt_channel_len=range(8, 13, 2),
    wt_average_len=range(18, 25, 3),
    wt_ma_len=[3, 4, 5],
    wt_oversold=range(-70, -50, 10),
    wt_overbought=range(50, 71, 10),
    macd_fast=range(10, 15, 2),
    macd_slow=range(24, 29, 2),
    macd_signal=range(7, 11, 2),
    vwma_period=range(15, 26, 5),
    volume_threshold=[1.5, 2.0, 2.5],
    take_profit=[i / 1000 for i in range(25, 36, 5)],
    stop_loss=[i / 1000 for i in range(15, 21, 3)],
    maximize='Sortino Ratio',
    constraint=lambda p: (p.take_profit > p.stop_loss and
                         p.wt_oversold < p.wt_overbought and
                         p.macd_fast < p.macd_slow)
)

print("\n🚀 ===== WAVE TREND + MACD + VOLUME OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"Wave Trend Channel: {optimization_results._strategy.wt_channel_len}")
print(f"Wave Trend Average: {optimization_results._strategy.wt_average_len}")
print(f"Wave Trend MA: {optimization_results._strategy.wt_ma_len}")
print(f"WT Oversold: {optimization_results._strategy.wt_oversold}")
print(f"WT Overbought: {optimization_results._strategy.wt_overbought}")
print(f"MACD Fast: {optimization_results._strategy.macd_fast}")
print(f"MACD Slow: {optimization_results._strategy.macd_slow}")
print(f"MACD Signal: {optimization_results._strategy.macd_signal}")
print(f"VWMA Period: {optimization_results._strategy.vwma_period}")
print(f"Volume Threshold: {optimization_results._strategy.volume_threshold:.1f}x")
print(f"Take Profit: {optimization_results._strategy.take_profit:.3f}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.3f}")