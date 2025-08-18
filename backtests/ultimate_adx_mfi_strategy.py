import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

print("🚀 Moon Dev's Ultimate Oscillator + ADX + MFI Strategy Loading... 🌙")

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

class UltimateADXMFIStrategy(Strategy):
    # Ultimate Oscillator parameters
    uo_period1 = 7
    uo_period2 = 14
    uo_period3 = 28
    uo_oversold = 30
    uo_overbought = 70
    
    # ADX parameters
    adx_period = 14
    adx_threshold = 25
    adx_strong = 40
    
    # MFI parameters
    mfi_period = 14
    mfi_oversold = 30
    mfi_overbought = 70
    
    # Williams %R for additional confirmation
    williams_period = 14
    williams_oversold = -80
    williams_overbought = -20
    
    # Risk management
    take_profit = 0.035
    stop_loss = 0.02
    
    # Trend strength multiplier
    trend_multiplier = 1.5
    
    def init(self):
        # Calculate Ultimate Oscillator
        self.uo = self.I(talib.ULTOSC,
                        self.data.High,
                        self.data.Low,
                        self.data.Close,
                        self.uo_period1,
                        self.uo_period2,
                        self.uo_period3)
        
        # Calculate ADX and DI+/DI-
        self.adx = self.I(talib.ADX,
                          self.data.High,
                          self.data.Low,
                          self.data.Close,
                          self.adx_period)
        
        self.plus_di = self.I(talib.PLUS_DI,
                              self.data.High,
                              self.data.Low,
                              self.data.Close,
                              self.adx_period)
        
        self.minus_di = self.I(talib.MINUS_DI,
                               self.data.High,
                               self.data.Low,
                               self.data.Close,
                               self.adx_period)
        
        # Calculate MFI
        self.mfi = self.I(talib.MFI,
                          self.data.High,
                          self.data.Low,
                          self.data.Close,
                          self.data.Volume,
                          self.mfi_period)
        
        # Calculate Williams %R
        self.williams = self.I(talib.WILLR,
                               self.data.High,
                               self.data.Low,
                               self.data.Close,
                               self.williams_period)
        
        # Calculate Parabolic SAR for trend confirmation
        self.sar = self.I(talib.SAR,
                          self.data.High,
                          self.data.Low,
                          acceleration=0.02,
                          maximum=0.2)
        
        # Calculate ATR for volatility-adjusted stops
        self.atr = self.I(talib.ATR,
                          self.data.High,
                          self.data.Low,
                          self.data.Close,
                          14)
        
        # Calculate Commodity Channel Index for momentum
        self.cci = self.I(talib.CCI,
                          self.data.High,
                          self.data.Low,
                          self.data.Close,
                          20)
        
        # Volume analysis
        self.volume_ma = self.I(talib.SMA, self.data.Volume, 20)
        self.volume_ratio = self.I(lambda: self.data.Volume / self.volume_ma)
    
    def calculate_trend_strength(self):
        """Calculate overall trend strength score"""
        if pd.isna(self.adx[-1]) or pd.isna(self.plus_di[-1]) or pd.isna(self.minus_di[-1]):
            return 0
        
        trend_score = 0
        
        # ADX strength
        if self.adx[-1] > self.adx_strong:
            trend_score += 2
        elif self.adx[-1] > self.adx_threshold:
            trend_score += 1
        
        # DI direction
        if self.plus_di[-1] > self.minus_di[-1]:
            trend_score += 1  # Bullish
        else:
            trend_score -= 1  # Bearish
        
        return trend_score
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < max(self.uo_period3, self.adx_period, self.mfi_period):
            return
        
        current_price = self.data.Close[-1]
        current_uo = self.uo[-1]
        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]
        current_mfi = self.mfi[-1]
        current_williams = self.williams[-1]
        current_sar = self.sar[-1]
        current_atr = self.atr[-1]
        current_cci = self.cci[-1]
        current_volume_ratio = self.volume_ratio[-1]
        
        # Skip if invalid values
        if (pd.isna(current_uo) or pd.isna(current_adx) or 
            pd.isna(current_mfi) or pd.isna(current_williams) or 
            pd.isna(current_atr)):
            return
        
        # Calculate trend strength
        trend_strength = self.calculate_trend_strength()
        
        # Check for divergences
        uo_divergence_bull = False
        uo_divergence_bear = False
        
        if len(self.data) >= 20:
            # Simple divergence check
            price_change = (current_price - self.data.Close[-10]) / self.data.Close[-10]
            uo_change = current_uo - self.uo[-10]
            
            # Bullish divergence: price down, UO up
            if price_change < -0.01 and uo_change > 5:
                uo_divergence_bull = True
            
            # Bearish divergence: price up, UO down
            if price_change > 0.01 and uo_change < -5:
                uo_divergence_bear = True
        
        # Dynamic position sizing based on ADX
        position_size_multiplier = 1.0
        if current_adx > self.adx_strong:
            position_size_multiplier = self.trend_multiplier
        
        # Long Entry Conditions
        long_conditions = {
            'uo_oversold': current_uo < self.uo_oversold,
            'mfi_oversold': current_mfi < self.mfi_oversold,
            'williams_oversold': current_williams < self.williams_oversold,
            'adx_trending': current_adx > self.adx_threshold,
            'di_bullish': current_plus_di > current_minus_di,
            'sar_bullish': current_price > current_sar if not pd.isna(current_sar) else False,
            'cci_oversold': current_cci < -100 if not pd.isna(current_cci) else False,
            'volume_surge': current_volume_ratio > 1.5 if not pd.isna(current_volume_ratio) else False,
            'uo_divergence': uo_divergence_bull
        }
        
        long_score = sum([
            long_conditions['uo_oversold'] * 2,
            long_conditions['mfi_oversold'] * 1.5,
            long_conditions['williams_oversold'],
            long_conditions['adx_trending'] * 2,
            long_conditions['di_bullish'] * 1.5,
            long_conditions['sar_bullish'],
            long_conditions['cci_oversold'],
            long_conditions['volume_surge'] * 1.5,
            long_conditions['uo_divergence'] * 3
        ])
        
        # Short Entry Conditions
        short_conditions = {
            'uo_overbought': current_uo > self.uo_overbought,
            'mfi_overbought': current_mfi > self.mfi_overbought,
            'williams_overbought': current_williams > self.williams_overbought,
            'adx_trending': current_adx > self.adx_threshold,
            'di_bearish': current_minus_di > current_plus_di,
            'sar_bearish': current_price < current_sar if not pd.isna(current_sar) else False,
            'cci_overbought': current_cci > 100 if not pd.isna(current_cci) else False,
            'volume_surge': current_volume_ratio > 1.5 if not pd.isna(current_volume_ratio) else False,
            'uo_divergence': uo_divergence_bear
        }
        
        short_score = sum([
            short_conditions['uo_overbought'] * 2,
            short_conditions['mfi_overbought'] * 1.5,
            short_conditions['williams_overbought'],
            short_conditions['adx_trending'] * 2,
            short_conditions['di_bearish'] * 1.5,
            short_conditions['sar_bearish'],
            short_conditions['cci_overbought'],
            short_conditions['volume_surge'] * 1.5,
            short_conditions['uo_divergence'] * 3
        ])
        
        # Long Entry
        if not self.position and long_score >= 6:
            # Dynamic stop loss based on ATR and ADX
            atr_multiplier = 2.5 if current_adx > self.adx_strong else 2.0
            sl_price = max(
                current_price * (1 - self.stop_loss),
                current_price - (current_atr * atr_multiplier)
            )
            
            # Dynamic take profit based on trend strength
            tp_multiplier = position_size_multiplier
            tp_price = current_price * (1 + self.take_profit * tp_multiplier)
            
            self.buy(sl=sl_price, tp=tp_price)
        
        # Short Entry
        elif not self.position and short_score >= 6:
            # Dynamic stop loss based on ATR and ADX
            atr_multiplier = 2.5 if current_adx > self.adx_strong else 2.0
            sl_price = min(
                current_price * (1 + self.stop_loss),
                current_price + (current_atr * atr_multiplier)
            )
            
            # Dynamic take profit based on trend strength
            tp_multiplier = position_size_multiplier
            tp_price = current_price * (1 - self.take_profit * tp_multiplier)
            
            self.sell(sl=sl_price, tp=tp_price)
        
        # Advanced exit conditions
        elif self.position:
            if self.position.is_long:
                exit_conditions = [
                    current_uo > 75,                    # UO extreme overbought
                    current_mfi > 85,                   # MFI extreme overbought
                    current_williams > -10,             # Williams extreme overbought
                    current_adx < 20,                   # Trend weakening
                    current_minus_di > current_plus_di * 1.2,  # DI bearish cross
                    current_price < current_sar if not pd.isna(current_sar) else False
                ]
                
                if sum(exit_conditions) >= 2:
                    self.position.close()
                    
            elif self.position.is_short:
                exit_conditions = [
                    current_uo < 25,                    # UO extreme oversold
                    current_mfi < 15,                   # MFI extreme oversold
                    current_williams < -90,             # Williams extreme oversold
                    current_adx < 20,                   # Trend weakening
                    current_plus_di > current_minus_di * 1.2,  # DI bullish cross
                    current_price > current_sar if not pd.isna(current_sar) else False
                ]
                
                if sum(exit_conditions) >= 2:
                    self.position.close()

# Prepare data
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.dropna()
print(f"✅ Data cleaned! {len(data)} valid rows remaining 🚀")

# Create and run backtest
bt = Backtest(data, UltimateADXMFIStrategy, cash=100000, commission=0.002)

# Run with default parameters
print("\n🌙 ===== ULTIMATE OSCILLATOR + ADX + MFI - DEFAULT PARAMETERS ===== 🌙")
stats_default = bt.run()
print(stats_default)

# Optimize for Sortino ratio - STREAMLINED FOR MOON DEV! 🚀
print("\n🚀 Optimizing for Sortino Ratio - Reduced Parameter Set...")
optimization_results = bt.optimize(
    uo_oversold=[25, 30, 35],                    # 3 options
    uo_overbought=[65, 70, 75],                  # 3 options  
    adx_threshold=[20, 25, 30],                  # 3 options
    mfi_oversold=[25, 30, 35],                   # 3 options
    mfi_overbought=[65, 70, 75],                 # 3 options
    take_profit=[0.030, 0.035, 0.040],          # 3 options
    stop_loss=[0.015, 0.020, 0.025],            # 3 options
    maximize='Sortino Ratio',
    constraint=lambda p: (p.take_profit > p.stop_loss and
                         p.uo_oversold < p.uo_overbought and
                         p.mfi_oversold < p.mfi_overbought)
)

print("\n🚀 ===== ULTIMATE + ADX + MFI OPTIMIZATION RESULTS ===== 🚀")
print(optimization_results)

print("\n🏆 BEST PARAMETERS:")
print(f"UO Periods: {optimization_results._strategy.uo_period1}/{optimization_results._strategy.uo_period2}/{optimization_results._strategy.uo_period3}")
print(f"UO Oversold: {optimization_results._strategy.uo_oversold}")
print(f"UO Overbought: {optimization_results._strategy.uo_overbought}")
print(f"ADX Period: {optimization_results._strategy.adx_period}")
print(f"ADX Threshold: {optimization_results._strategy.adx_threshold}")
print(f"MFI Period: {optimization_results._strategy.mfi_period}")
print(f"MFI Oversold: {optimization_results._strategy.mfi_oversold}")
print(f"MFI Overbought: {optimization_results._strategy.mfi_overbought}")
print(f"Take Profit: {optimization_results._strategy.take_profit:.3f}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss:.3f}")