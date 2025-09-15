"""
Moon Dev's RSI Divergence Bollinger Strategy
=============================================
RSI divergence detection with Bollinger Bands volatility filtering
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's RSI Divergence Bollinger Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - FIXED, NO OPTIMIZATION
RSI_PERIOD = 14
BB_PERIOD = 20
BB_STD = 2.0
LOOKBACK_PERIOD = 10  # Simplified lookback
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
STOP_LOSS_PERCENT = 2.0
TAKE_PROFIT_PERCENT = 3.5

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class RSIDivergenceBollinger(Strategy):
    """
    RSI Divergence with Bollinger Bands Strategy - Simplified
    - Detect RSI divergences using rolling windows
    - Use Bollinger Bands for volatility context
    - Take divergence signals at band extremes
    - Enter with stop-loss and take-profit
    """
    
    # Fixed parameters
    rsi_period = RSI_PERIOD
    bb_period = BB_PERIOD
    bb_std = BB_STD
    lookback_period = LOOKBACK_PERIOD
    rsi_oversold = RSI_OVERSOLD
    rsi_overbought = RSI_OVERBOUGHT
    stop_loss = STOP_LOSS_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    
    def init(self):
        close = pd.Series(self.data.Close)
        
        # Calculate RSI
        rsi = ta.rsi(close, length=self.rsi_period)
        
        # Calculate Bollinger Bands
        bb_result = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        bb_upper = bb_result[f'BBU_{self.bb_period}_{self.bb_std}']
        bb_middle = bb_result[f'BBM_{self.bb_period}_{self.bb_std}']
        bb_lower = bb_result[f'BBL_{self.bb_period}_{self.bb_std}']
        
        # Calculate bandwidth (volatility measure)
        bb_bandwidth = (bb_upper - bb_lower) / bb_middle * 100
        
        # Ensure arrays are same length as data
        rsi_full = np.full(len(close), np.nan)
        rsi_full[-len(rsi):] = rsi.values
        
        bb_upper_full = np.full(len(close), np.nan)
        bb_upper_full[-len(bb_upper):] = bb_upper.values
        
        bb_middle_full = np.full(len(close), np.nan)
        bb_middle_full[-len(bb_middle):] = bb_middle.values
        
        bb_lower_full = np.full(len(close), np.nan)
        bb_lower_full[-len(bb_lower):] = bb_lower.values
        
        bb_bandwidth_full = np.full(len(close), np.nan)
        bb_bandwidth_full[-len(bb_bandwidth):] = bb_bandwidth.values
        
        self.rsi = self.I(lambda: rsi_full, name='RSI')
        self.bb_upper = self.I(lambda: bb_upper_full, name='BB_Upper')
        self.bb_middle = self.I(lambda: bb_middle_full, name='BB_Middle')
        self.bb_lower = self.I(lambda: bb_lower_full, name='BB_Lower')
        self.bb_bandwidth = self.I(lambda: bb_bandwidth_full, name='BB_Bandwidth')
        
        # Calculate rolling max/min for simple divergence detection
        price_roll_max = close.rolling(window=self.lookback_period, min_periods=self.lookback_period).max()
        price_roll_min = close.rolling(window=self.lookback_period, min_periods=self.lookback_period).min()
        
        rsi_series = pd.Series(rsi_full)
        rsi_roll_max = rsi_series.rolling(window=self.lookback_period, min_periods=self.lookback_period).max()
        rsi_roll_min = rsi_series.rolling(window=self.lookback_period, min_periods=self.lookback_period).min()
        
        # Store as indicators
        self.price_max = self.I(lambda: price_roll_max.values, name='Price_Max')
        self.price_min = self.I(lambda: price_roll_min.values, name='Price_Min')
        self.rsi_max = self.I(lambda: rsi_roll_max.values, name='RSI_Max')
        self.rsi_min = self.I(lambda: rsi_roll_min.values, name='RSI_Min')
    
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.rsi[-1]) or np.isnan(self.bb_upper[-1]) or np.isnan(self.price_max[-1]):
            return
        
        # Skip if we need more data for comparison
        if len(self.data) < self.lookback_period * 2:
            return
        
        current_price = self.data.Close[-1]
        current_rsi = self.rsi[-1]
        
        # Get previous extremes (from lookback_period bars ago)
        prev_idx = -self.lookback_period
        if abs(prev_idx) >= len(self.data):
            return
            
        prev_price_high = self.price_max[prev_idx]
        prev_price_low = self.price_min[prev_idx]
        prev_rsi_high = self.rsi_max[prev_idx]
        prev_rsi_low = self.rsi_min[prev_idx]
        
        # Current extremes
        curr_price_high = self.price_max[-1]
        curr_price_low = self.price_min[-1]
        curr_rsi_high = self.rsi_max[-1]
        curr_rsi_low = self.rsi_min[-1]
        
        # Bollinger Band position
        price_near_lower_band = current_price <= self.bb_lower[-1] * 1.01  # Within 1% of lower band
        price_near_upper_band = current_price >= self.bb_upper[-1] * 0.99  # Within 1% of upper band
        
        # Volatility check - higher volatility means stronger signals
        high_volatility = self.bb_bandwidth[-1] > 4  # Bandwidth > 4%
        
        if not self.position:
            # Bullish divergence: Price makes lower low, RSI makes higher low
            # Best at lower Bollinger Band
            price_at_low = abs(current_price - curr_price_low) / current_price < 0.005
            price_lower_low = curr_price_low < prev_price_low * 0.995
            rsi_higher_low = curr_rsi_low > prev_rsi_low + 1
            rsi_oversold = current_rsi < self.rsi_oversold + 5
            
            if price_at_low and price_lower_low and rsi_higher_low and rsi_oversold and price_near_lower_band:
                # Enter long position with better risk/reward in high volatility
                sl_multiplier = 1.5 if high_volatility else 1.0
                tp_multiplier = 1.5 if high_volatility else 1.0
                sl_price = current_price * (1 - self.stop_loss * sl_multiplier)
                tp_price = current_price * (1 + self.take_profit * tp_multiplier)
                self.buy(sl=sl_price, tp=tp_price)
            
            # Bearish divergence: Price makes higher high, RSI makes lower high
            # Best at upper Bollinger Band
            price_at_high = abs(current_price - curr_price_high) / current_price < 0.005
            price_higher_high = curr_price_high > prev_price_high * 1.005
            rsi_lower_high = curr_rsi_high < prev_rsi_high - 1
            rsi_overbought = current_rsi > self.rsi_overbought - 5
            
            if price_at_high and price_higher_high and rsi_lower_high and rsi_overbought and price_near_upper_band:
                # Enter short position with better risk/reward in high volatility
                sl_multiplier = 1.5 if high_volatility else 1.0
                tp_multiplier = 1.5 if high_volatility else 1.0
                sl_price = current_price * (1 + self.stop_loss * sl_multiplier)
                tp_price = current_price * (1 - self.take_profit * tp_multiplier)
                self.sell(sl=sl_price, tp=tp_price)

# Run single backtest - NO OPTIMIZATION
bt = Backtest(data, RSIDivergenceBollinger, cash=100000, commission=0.00045)

print("\n🌙 ===== RSI DIVERGENCE BOLLINGER - FIXED PARAMETERS ===== 🌙")
print(f"RSI Period: {RSI_PERIOD}")
print(f"Bollinger Period: {BB_PERIOD}")
print(f"Bollinger Std Dev: {BB_STD}")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"RSI Oversold: {RSI_OVERSOLD}")
print(f"RSI Overbought: {RSI_OVERBOUGHT}")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING RSI DIVERGENCE BOLLINGER ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(RSIDivergenceBollinger, 'RSIDivergenceBollinger')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/RSIDivergenceBollinger.csv")