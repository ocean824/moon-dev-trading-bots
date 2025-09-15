"""
Moon Dev's Fibonacci Retracement + Bollinger Bands Strategy
===========================================================
Fibonacci retracement with Bollinger Bands for volatility confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Fibonacci Retracement + Bollinger Bands Strategy Loading... 🌙")

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
BB_PERIOD = 20  # Bollinger Bands period
BB_STD = 2.0  # Bollinger Bands standard deviation

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class FibonacciRetracementBollinger(Strategy):
    """
    Fibonacci Retracement + Bollinger Bands Strategy
    - Identify swing highs and lows using rolling windows
    - Calculate Fibonacci levels between swings
    - Use Bollinger Bands for volatility confirmation
    - Enter when Fib levels align with BB signals
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
    
    # Trend and volatility filters
    trend_ma_period = TREND_MA_PERIOD
    bb_period = BB_PERIOD
    bb_std = BB_STD
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Calculate trend MA
        ma = ta.sma(close, length=self.trend_ma_period)
        ma_full = np.full(len(close), np.nan)
        ma_full[-len(ma):] = ma.values
        self.ma = self.I(lambda: ma_full, name='MA')
        
        # Calculate Bollinger Bands
        bb_result = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        if bb_result is not None and not bb_result.empty:
            bb_upper = bb_result[f'BBU_{self.bb_period}_{self.bb_std}']
            bb_middle = bb_result[f'BBM_{self.bb_period}_{self.bb_std}']
            bb_lower = bb_result[f'BBL_{self.bb_period}_{self.bb_std}']
            bb_width = bb_result[f'BBB_{self.bb_period}_{self.bb_std}']
            
            bb_upper_full = np.full(len(close), np.nan)
            bb_middle_full = np.full(len(close), np.nan)
            bb_lower_full = np.full(len(close), np.nan)
            bb_width_full = np.full(len(close), np.nan)
            
            bb_upper_full[-len(bb_upper):] = bb_upper.values
            bb_middle_full[-len(bb_middle):] = bb_middle.values
            bb_lower_full[-len(bb_lower):] = bb_lower.values
            bb_width_full[-len(bb_width):] = bb_width.values
            
            self.bb_upper = self.I(lambda: bb_upper_full, name='BB_Upper')
            self.bb_middle = self.I(lambda: bb_middle_full, name='BB_Middle')
            self.bb_lower = self.I(lambda: bb_lower_full, name='BB_Lower')
            self.bb_width = self.I(lambda: bb_width_full, name='BB_Width')
        else:
            self.bb_upper = self.I(lambda: np.full(len(close), np.nan), name='BB_Upper')
            self.bb_middle = self.I(lambda: np.full(len(close), np.nan), name='BB_Middle')
            self.bb_lower = self.I(lambda: np.full(len(close), np.nan), name='BB_Lower')
            self.bb_width = self.I(lambda: np.full(len(close), np.nan), name='BB_Width')
        
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
    
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.ma[-1]) or np.isnan(self.swing_high[-1]) or np.isnan(self.swing_low[-1]):
            return
        
        if np.isnan(self.bb_upper[-1]) or np.isnan(self.bb_lower[-1]):
            return
        
        # Skip if we need more data
        if len(self.data) < self.swing_lookback * 2:
            return
        
        current_price = self.data.Close[-1]
        current_ma = self.ma[-1]
        current_bb_upper = self.bb_upper[-1]
        current_bb_middle = self.bb_middle[-1]
        current_bb_lower = self.bb_lower[-1]
        
        # Determine trend
        is_uptrend = current_price > current_ma
        
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
                # In uptrend, buy at retracements when price touches lower BB
                near_lower_bb = abs(current_price - current_bb_lower) / current_price < 0.01
                above_lower_bb = current_price > current_bb_lower
                
                # Check if price is at 61.8% retracement and near lower BB
                if self.fib_618 is not None:
                    at_618 = abs(current_price - self.fib_618) / current_price < 0.01
                    
                    if at_618 and (near_lower_bb or above_lower_bb):
                        sl_price = current_price * (1 - self.stop_loss)
                        tp_price = current_price * (1 + self.take_profit)
                        self.buy(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
                
                # Check if price is at 38.2% retracement and BB conditions
                if self.fib_382 is not None:
                    at_382 = abs(current_price - self.fib_382) / current_price < 0.01
                    below_middle_bb = current_price < current_bb_middle
                    
                    if at_382 and below_middle_bb and above_lower_bb:
                        sl_price = current_price * (1 - self.stop_loss)
                        tp_price = current_price * (1 + self.take_profit)
                        self.buy(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
            
            else:
                # In downtrend, sell at retracements when price touches upper BB
                near_upper_bb = abs(current_price - current_bb_upper) / current_price < 0.01
                below_upper_bb = current_price < current_bb_upper
                
                # Check if price is at 61.8% retracement and near upper BB
                if self.fib_618 is not None:
                    at_618 = abs(current_price - self.fib_618) / current_price < 0.01
                    
                    if at_618 and (near_upper_bb or below_upper_bb):
                        sl_price = current_price * (1 + self.stop_loss)
                        tp_price = current_price * (1 - self.take_profit)
                        self.sell(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
                
                # Check if price is at 38.2% retracement and BB conditions
                if self.fib_382 is not None:
                    at_382 = abs(current_price - self.fib_382) / current_price < 0.01
                    above_middle_bb = current_price > current_bb_middle
                    
                    if at_382 and above_middle_bb and below_upper_bb:
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
bt = Backtest(data, FibonacciRetracementBollinger, cash=100000, commission=0.00045)

print("\n🌙 ===== FIBONACCI RETRACEMENT + BOLLINGER BANDS - FIXED PARAMETERS ===== 🌙")
print(f"Swing Lookback: {SWING_LOOKBACK}")
print(f"Min Swing Difference: {MIN_SWING_DIFF * 100}%")
print(f"Primary Entry Level: {FIB_ENTRY_LEVEL * 100}%")
print(f"Secondary Entry Level: {FIB_SECONDARY_LEVEL * 100}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Trend MA Period: {TREND_MA_PERIOD}")
print(f"Bollinger Bands Period: {BB_PERIOD}")
print(f"Bollinger Bands Std Dev: {BB_STD}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FIBONACCI RETRACEMENT + BOLLINGER BANDS ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(FibonacciRetracementBollinger, 'FibonacciRetracementBollinger')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FibonacciRetracementBollinger.csv")