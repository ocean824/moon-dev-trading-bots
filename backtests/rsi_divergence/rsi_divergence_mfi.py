"""
Moon Dev's RSI Divergence MFI Strategy
=======================================
RSI divergence detection with Money Flow Index volume confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's RSI Divergence MFI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - FIXED, NO OPTIMIZATION
RSI_PERIOD = 14
MFI_PERIOD = 14
LOOKBACK_PERIOD = 10  # Simplified lookback
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
MFI_OVERSOLD = 20
MFI_OVERBOUGHT = 80
STOP_LOSS_PERCENT = 2.0
TAKE_PROFIT_PERCENT = 3.5

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class RSIDivergenceMFI(Strategy):
    """
    RSI Divergence with MFI Volume Confirmation - Simplified
    - Detect RSI divergences using rolling windows
    - Confirm with MFI for volume-backed moves
    - Enter with stop-loss and take-profit
    """
    
    # Fixed parameters
    rsi_period = RSI_PERIOD
    mfi_period = MFI_PERIOD
    lookback_period = LOOKBACK_PERIOD
    rsi_oversold = RSI_OVERSOLD
    rsi_overbought = RSI_OVERBOUGHT
    mfi_oversold = MFI_OVERSOLD
    mfi_overbought = MFI_OVERBOUGHT
    stop_loss = STOP_LOSS_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Calculate RSI
        rsi = ta.rsi(close, length=self.rsi_period)
        
        # Calculate MFI (Money Flow Index)
        mfi = ta.mfi(high, low, close, volume, length=self.mfi_period)
        
        # Ensure arrays are same length as data
        rsi_full = np.full(len(close), np.nan)
        rsi_full[-len(rsi):] = rsi.values
        
        mfi_full = np.full(len(close), np.nan)
        mfi_full[-len(mfi):] = mfi.values
        
        self.rsi = self.I(lambda: rsi_full, name='RSI')
        self.mfi = self.I(lambda: mfi_full, name='MFI')
        
        # Calculate rolling max/min for simple divergence detection
        price_roll_max = close.rolling(window=self.lookback_period, min_periods=self.lookback_period).max()
        price_roll_min = close.rolling(window=self.lookback_period, min_periods=self.lookback_period).min()
        
        rsi_series = pd.Series(rsi_full)
        rsi_roll_max = rsi_series.rolling(window=self.lookback_period, min_periods=self.lookback_period).max()
        rsi_roll_min = rsi_series.rolling(window=self.lookback_period, min_periods=self.lookback_period).min()
        
        mfi_series = pd.Series(mfi_full)
        mfi_roll_max = mfi_series.rolling(window=self.lookback_period, min_periods=self.lookback_period).max()
        mfi_roll_min = mfi_series.rolling(window=self.lookback_period, min_periods=self.lookback_period).min()
        
        # Store as indicators
        self.price_max = self.I(lambda: price_roll_max.values, name='Price_Max')
        self.price_min = self.I(lambda: price_roll_min.values, name='Price_Min')
        self.rsi_max = self.I(lambda: rsi_roll_max.values, name='RSI_Max')
        self.rsi_min = self.I(lambda: rsi_roll_min.values, name='RSI_Min')
        self.mfi_max = self.I(lambda: mfi_roll_max.values, name='MFI_Max')
        self.mfi_min = self.I(lambda: mfi_roll_min.values, name='MFI_Min')
    
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.rsi[-1]) or np.isnan(self.mfi[-1]) or np.isnan(self.price_max[-1]):
            return
        
        # Skip if we need more data for comparison
        if len(self.data) < self.lookback_period * 2:
            return
        
        current_price = self.data.Close[-1]
        current_rsi = self.rsi[-1]
        current_mfi = self.mfi[-1]
        
        # Get previous extremes (from lookback_period bars ago)
        prev_idx = -self.lookback_period
        if abs(prev_idx) >= len(self.data):
            return
            
        prev_price_high = self.price_max[prev_idx]
        prev_price_low = self.price_min[prev_idx]
        prev_rsi_high = self.rsi_max[prev_idx]
        prev_rsi_low = self.rsi_min[prev_idx]
        prev_mfi_high = self.mfi_max[prev_idx]
        prev_mfi_low = self.mfi_min[prev_idx]
        
        # Current extremes
        curr_price_high = self.price_max[-1]
        curr_price_low = self.price_min[-1]
        curr_rsi_high = self.rsi_max[-1]
        curr_rsi_low = self.rsi_min[-1]
        curr_mfi_high = self.mfi_max[-1]
        curr_mfi_low = self.mfi_min[-1]
        
        if not self.position:
            # Bullish divergence: Price makes lower low, RSI makes higher low
            # Confirm with MFI also showing divergence or oversold
            price_at_low = abs(current_price - curr_price_low) / current_price < 0.005
            price_lower_low = curr_price_low < prev_price_low * 0.995
            rsi_higher_low = curr_rsi_low > prev_rsi_low + 1
            rsi_oversold = current_rsi < self.rsi_oversold + 5
            
            # MFI confirmation: either divergence or oversold
            mfi_higher_low = curr_mfi_low > prev_mfi_low + 2
            mfi_oversold = current_mfi < self.mfi_oversold + 10
            mfi_confirms = mfi_higher_low or mfi_oversold
            
            if price_at_low and price_lower_low and rsi_higher_low and rsi_oversold and mfi_confirms:
                # Enter long position
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
            
            # Bearish divergence: Price makes higher high, RSI makes lower high
            # Confirm with MFI also showing divergence or overbought
            price_at_high = abs(current_price - curr_price_high) / current_price < 0.005
            price_higher_high = curr_price_high > prev_price_high * 1.005
            rsi_lower_high = curr_rsi_high < prev_rsi_high - 1
            rsi_overbought = current_rsi > self.rsi_overbought - 5
            
            # MFI confirmation: either divergence or overbought
            mfi_lower_high = curr_mfi_high < prev_mfi_high - 2
            mfi_overbought = current_mfi > self.mfi_overbought - 10
            mfi_confirms = mfi_lower_high or mfi_overbought
            
            if price_at_high and price_higher_high and rsi_lower_high and rsi_overbought and mfi_confirms:
                # Enter short position
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)

# Run single backtest - NO OPTIMIZATION
bt = Backtest(data, RSIDivergenceMFI, cash=100000, commission=0.00045)

print("\n🌙 ===== RSI DIVERGENCE MFI - FIXED PARAMETERS ===== 🌙")
print(f"RSI Period: {RSI_PERIOD}")
print(f"MFI Period: {MFI_PERIOD}")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"RSI Oversold: {RSI_OVERSOLD}")
print(f"RSI Overbought: {RSI_OVERBOUGHT}")
print(f"MFI Oversold: {MFI_OVERSOLD}")
print(f"MFI Overbought: {MFI_OVERBOUGHT}")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING RSI DIVERGENCE MFI ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(RSIDivergenceMFI, 'RSIDivergenceMFI')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/RSIDivergenceMFI.csv")