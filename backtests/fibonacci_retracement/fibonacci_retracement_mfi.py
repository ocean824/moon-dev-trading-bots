"""
Moon Dev's Fibonacci Retracement + MFI Strategy
===============================================
Fibonacci retracement with Money Flow Index for volume confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Fibonacci Retracement + MFI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - FIXED, NO OPTIMIZATION
SWING_LOOKBACK = 30  # Periods to identify swing highs/lows
MIN_SWING_DIFF = 0.02  # Minimum 2% difference for valid swing
FIB_ENTRY_LEVEL = 0.618  # Enter at 61.8% retracement
FIB_SECONDARY_LEVEL = 0.382  # Secondary entry at 38.2%
STOP_LOSS_PERCENT = 3.0  # Stop loss percentage
TAKE_PROFIT_PERCENT = 5.0  # Take profit percentage
TREND_MA_PERIOD = 50  # MA period for trend determination
MFI_PERIOD = 14  # Money Flow Index period
MFI_OVERSOLD = 30  # MFI oversold level
MFI_OVERBOUGHT = 70  # MFI overbought level

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class FibonacciRetracementMFI(Strategy):
    """
    Fibonacci Retracement + MFI Strategy
    - Identify swing highs and lows using rolling windows
    - Calculate Fibonacci levels between swings
    - Use MFI to confirm volume-based momentum
    - Enter when Fib levels align with MFI conditions
    """
    
    # Swing detection parameters
    swing_lookback = SWING_LOOKBACK
    min_swing_diff = MIN_SWING_DIFF
    
    # Fibonacci levels
    fib_entry = FIB_ENTRY_LEVEL
    fib_secondary = FIB_SECONDARY_LEVEL
    
    # Risk management
    stop_loss = STOP_LOSS_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    
    # Indicator parameters
    trend_ma_period = TREND_MA_PERIOD
    mfi_period = MFI_PERIOD
    mfi_oversold = MFI_OVERSOLD
    mfi_overbought = MFI_OVERBOUGHT
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Calculate trend MA
        ma = ta.sma(close, length=self.trend_ma_period)
        ma_full = np.full(len(close), np.nan)
        ma_full[-len(ma):] = ma.values
        self.ma = self.I(lambda: ma_full, name='MA')
        
        # Calculate MFI
        mfi = ta.mfi(high, low, close, volume, length=self.mfi_period)
        mfi_full = np.full(len(close), np.nan)
        if mfi is not None and len(mfi) > 0:
            mfi_full[-len(mfi):] = mfi.values
        self.mfi = self.I(lambda: mfi_full, name='MFI')
        
        # Calculate rolling highs and lows for swing detection
        swing_high = high.rolling(window=self.swing_lookback, min_periods=self.swing_lookback).max()
        swing_low = low.rolling(window=self.swing_lookback, min_periods=self.swing_lookback).min()
        
        self.swing_high = self.I(lambda: swing_high.values, name='Swing_High')
        self.swing_low = self.I(lambda: swing_low.values, name='Swing_Low')
        
        # Track Fibonacci levels
        self.fib_0 = None
        self.fib_236 = None
        self.fib_382 = None
        self.fib_50 = None
        self.fib_618 = None
        self.fib_100 = None
        
        # Track entry info
        self.entry_price = None
        self.in_position = False
        self.mfi_divergence = False
    
    def calculate_fib_levels(self, swing_high, swing_low, is_uptrend):
        """Calculate Fibonacci retracement levels"""
        if is_uptrend:
            diff = swing_high - swing_low
            self.fib_0 = swing_low
            self.fib_236 = swing_low + diff * 0.236
            self.fib_382 = swing_low + diff * 0.382
            self.fib_50 = swing_low + diff * 0.5
            self.fib_618 = swing_low + diff * 0.618
            self.fib_100 = swing_high
        else:
            diff = swing_high - swing_low
            self.fib_0 = swing_high
            self.fib_236 = swing_high - diff * 0.236
            self.fib_382 = swing_high - diff * 0.382
            self.fib_50 = swing_high - diff * 0.5
            self.fib_618 = swing_high - diff * 0.618
            self.fib_100 = swing_low
    
    def check_mfi_divergence(self):
        """Check for MFI divergence with price"""
        if len(self.data) < self.swing_lookback * 2:
            return False
        
        # Get recent MFI values
        recent_mfi = self.mfi[-self.swing_lookback:]
        older_mfi = self.mfi[-self.swing_lookback*2:-self.swing_lookback]
        
        # Skip if MFI not ready
        if np.isnan(recent_mfi).any() or np.isnan(older_mfi).any():
            return False
        
        # Check for bullish divergence (price lower, MFI higher)
        price_lower = self.swing_low[-1] < self.swing_low[-self.swing_lookback]
        mfi_higher = np.mean(recent_mfi) > np.mean(older_mfi)
        
        if price_lower and mfi_higher:
            return 1  # Bullish divergence
        
        # Check for bearish divergence (price higher, MFI lower)
        price_higher = self.swing_high[-1] > self.swing_high[-self.swing_lookback]
        mfi_lower = np.mean(recent_mfi) < np.mean(older_mfi)
        
        if price_higher and mfi_lower:
            return -1  # Bearish divergence
        
        return 0
    
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.ma[-1]) or np.isnan(self.swing_high[-1]) or np.isnan(self.swing_low[-1]):
            return
        
        if np.isnan(self.mfi[-1]):
            return
        
        # Skip if we need more data
        if len(self.data) < self.swing_lookback * 2:
            return
        
        current_price = self.data.Close[-1]
        current_ma = self.ma[-1]
        current_mfi = self.mfi[-1]
        
        # Determine trend
        is_uptrend = current_price > current_ma
        
        # Check for MFI divergence
        divergence = self.check_mfi_divergence()
        
        # Get current swing levels
        current_swing_high = self.swing_high[-1]
        current_swing_low = self.swing_low[-1]
        
        # Check if we have a significant swing range
        swing_range = (current_swing_high - current_swing_low) / current_swing_low
        if swing_range < self.min_swing_diff:
            return
        
        # Calculate Fibonacci levels
        self.calculate_fib_levels(current_swing_high, current_swing_low, is_uptrend)
        
        if not self.position:
            if is_uptrend:
                # In uptrend, buy at retracements with MFI confirmation
                mfi_oversold = current_mfi < self.mfi_oversold + 10
                bullish_divergence = divergence == 1
                
                # Check if price is at 61.8% retracement with MFI support
                if self.fib_618 is not None:
                    at_618 = abs(current_price - self.fib_618) / current_price < 0.01
                    above_618 = current_price > self.fib_618 * 0.995
                    
                    if at_618 and above_618 and (mfi_oversold or bullish_divergence):
                        sl_price = current_price * (1 - self.stop_loss)
                        tp_price = current_price * (1 + self.take_profit)
                        self.buy(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
                
                # Check if price is at 38.2% retracement with moderate MFI
                if self.fib_382 is not None:
                    at_382 = abs(current_price - self.fib_382) / current_price < 0.01
                    above_382 = current_price > self.fib_382 * 0.995
                    mfi_neutral = 40 < current_mfi < 60
                    
                    if at_382 and above_382 and (mfi_neutral or mfi_oversold):
                        sl_price = current_price * (1 - self.stop_loss)
                        tp_price = current_price * (1 + self.take_profit)
                        self.buy(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
            
            else:
                # In downtrend, sell at retracements with MFI confirmation
                mfi_overbought = current_mfi > self.mfi_overbought - 10
                bearish_divergence = divergence == -1
                
                # Check if price is at 61.8% retracement with MFI resistance
                if self.fib_618 is not None:
                    at_618 = abs(current_price - self.fib_618) / current_price < 0.01
                    below_618 = current_price < self.fib_618 * 1.005
                    
                    if at_618 and below_618 and (mfi_overbought or bearish_divergence):
                        sl_price = current_price * (1 + self.stop_loss)
                        tp_price = current_price * (1 - self.take_profit)
                        self.sell(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
                
                # Check if price is at 38.2% retracement with moderate MFI
                if self.fib_382 is not None:
                    at_382 = abs(current_price - self.fib_382) / current_price < 0.01
                    below_382 = current_price < self.fib_382 * 1.005
                    mfi_neutral = 40 < current_mfi < 60
                    
                    if at_382 and below_382 and (mfi_neutral or mfi_overbought):
                        sl_price = current_price * (1 + self.stop_loss)
                        tp_price = current_price * (1 - self.take_profit)
                        self.sell(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
        else:
            # Reset position flag when out of position
            if not self.position:
                self.in_position = False

# Run single backtest (default behavior)
bt = Backtest(data, FibonacciRetracementMFI, cash=100000, commission=0.00045)

print("\n🌙 ===== FIBONACCI RETRACEMENT + MFI - FIXED PARAMETERS ===== 🌙")
print(f"Swing Lookback: {SWING_LOOKBACK}")
print(f"Min Swing Difference: {MIN_SWING_DIFF * 100}%")
print(f"Primary Entry Level: {FIB_ENTRY_LEVEL * 100}%")
print(f"Secondary Entry Level: {FIB_SECONDARY_LEVEL * 100}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Trend MA Period: {TREND_MA_PERIOD}")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Oversold: {MFI_OVERSOLD}")
print(f"MFI Overbought: {MFI_OVERBOUGHT}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FIBONACCI RETRACEMENT + MFI ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(FibonacciRetracementMFI, 'FibonacciRetracementMFI')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FibonacciRetracementMFI.csv")