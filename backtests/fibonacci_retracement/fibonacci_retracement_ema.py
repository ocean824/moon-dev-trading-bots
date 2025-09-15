"""
Moon Dev's Fibonacci Retracement + EMA Strategy
===============================================
Fibonacci retracement with EMA crossovers for trend confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Fibonacci Retracement + EMA Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - FIXED, NO OPTIMIZATION
SWING_LOOKBACK = 30  # Periods to identify swing highs/lows
MIN_SWING_DIFF = 0.02  # Minimum 2% difference for valid swing
FIB_ENTRY_LEVEL = 0.618  # Enter at 61.8% retracement
FIB_SECONDARY_LEVEL = 0.382  # Secondary entry at 38.2%
STOP_LOSS_PERCENT = 3.0  # Stop loss percentage
TAKE_PROFIT_PERCENT = 5.0  # Take profit percentage
EMA_FAST = 12  # Fast EMA period
EMA_SLOW = 26  # Slow EMA period
EMA_SIGNAL = 50  # Signal EMA for trend

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class FibonacciRetracementEMA(Strategy):
    """
    Fibonacci Retracement + EMA Strategy
    - Identify swing highs and lows using rolling windows
    - Calculate Fibonacci levels between swings
    - Use EMA crossovers to confirm trend direction
    - Enter when Fib levels align with EMA signals
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
    
    # EMA parameters
    ema_fast = EMA_FAST
    ema_slow = EMA_SLOW
    ema_signal = EMA_SIGNAL
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Calculate EMAs
        ema_fast = ta.ema(close, length=self.ema_fast)
        ema_slow = ta.ema(close, length=self.ema_slow)
        ema_signal = ta.ema(close, length=self.ema_signal)
        
        ema_fast_full = np.full(len(close), np.nan)
        ema_slow_full = np.full(len(close), np.nan)
        ema_signal_full = np.full(len(close), np.nan)
        
        ema_fast_full[-len(ema_fast):] = ema_fast.values
        ema_slow_full[-len(ema_slow):] = ema_slow.values
        ema_signal_full[-len(ema_signal):] = ema_signal.values
        
        self.ema_fast = self.I(lambda: ema_fast_full, name='EMA_Fast')
        self.ema_slow = self.I(lambda: ema_slow_full, name='EMA_Slow')
        self.ema_signal = self.I(lambda: ema_signal_full, name='EMA_Signal')
        
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
        self.last_ema_cross = 0  # Track bars since last EMA cross
    
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
        if np.isnan(self.ema_fast[-1]) or np.isnan(self.ema_slow[-1]) or np.isnan(self.ema_signal[-1]):
            return
        
        if np.isnan(self.swing_high[-1]) or np.isnan(self.swing_low[-1]):
            return
        
        # Skip if we need more data
        if len(self.data) < self.swing_lookback * 2:
            return
        
        current_price = self.data.Close[-1]
        current_ema_fast = self.ema_fast[-1]
        current_ema_slow = self.ema_slow[-1]
        current_ema_signal = self.ema_signal[-1]
        
        # Track EMA crossovers
        if len(self.data) > 1:
            prev_ema_fast = self.ema_fast[-2]
            prev_ema_slow = self.ema_slow[-2]
            
            # Check for crossover
            if prev_ema_fast <= prev_ema_slow and current_ema_fast > current_ema_slow:
                self.last_ema_cross = 1  # Bullish cross
            elif prev_ema_fast >= prev_ema_slow and current_ema_fast < current_ema_slow:
                self.last_ema_cross = -1  # Bearish cross
        
        # Determine trend using EMAs
        bullish_emas = current_ema_fast > current_ema_slow and current_price > current_ema_signal
        bearish_emas = current_ema_fast < current_ema_slow and current_price < current_ema_signal
        
        # Get current swing levels
        current_swing_high = self.swing_high[-1]
        current_swing_low = self.swing_low[-1]
        
        # Check if we have a significant swing range
        swing_range = (current_swing_high - current_swing_low) / current_swing_low
        if swing_range < self.min_swing_diff:
            return
        
        # Calculate Fibonacci levels based on EMA trend
        self.calculate_fib_levels(current_swing_high, current_swing_low, bullish_emas)
        
        if not self.position:
            if bullish_emas:
                # Bullish setup: Buy at Fibonacci retracements
                # Check if price is at 61.8% retracement
                if self.fib_618 is not None:
                    at_618 = abs(current_price - self.fib_618) / current_price < 0.01
                    above_618 = current_price > self.fib_618 * 0.995
                    recent_cross = self.last_ema_cross == 1
                    
                    if at_618 and above_618:
                        sl_price = current_price * (1 - self.stop_loss)
                        tp_price = current_price * (1 + self.take_profit)
                        self.buy(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
                
                # Check if price is at 38.2% retracement
                if self.fib_382 is not None:
                    at_382 = abs(current_price - self.fib_382) / current_price < 0.01
                    above_382 = current_price > self.fib_382 * 0.995
                    above_fast_ema = current_price > current_ema_fast
                    
                    if at_382 and above_382 and above_fast_ema:
                        sl_price = current_price * (1 - self.stop_loss)
                        tp_price = current_price * (1 + self.take_profit)
                        self.buy(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
            
            elif bearish_emas:
                # Bearish setup: Sell at Fibonacci retracements
                # Check if price is at 61.8% retracement
                if self.fib_618 is not None:
                    at_618 = abs(current_price - self.fib_618) / current_price < 0.01
                    below_618 = current_price < self.fib_618 * 1.005
                    recent_cross = self.last_ema_cross == -1
                    
                    if at_618 and below_618:
                        sl_price = current_price * (1 + self.stop_loss)
                        tp_price = current_price * (1 - self.take_profit)
                        self.sell(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
                
                # Check if price is at 38.2% retracement
                if self.fib_382 is not None:
                    at_382 = abs(current_price - self.fib_382) / current_price < 0.01
                    below_382 = current_price < self.fib_382 * 1.005
                    below_fast_ema = current_price < current_ema_fast
                    
                    if at_382 and below_382 and below_fast_ema:
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
                self.last_ema_cross = 0

# Run single backtest (default behavior)
bt = Backtest(data, FibonacciRetracementEMA, cash=100000, commission=0.00045)

print("\n🌙 ===== FIBONACCI RETRACEMENT + EMA - FIXED PARAMETERS ===== 🌙")
print(f"Swing Lookback: {SWING_LOOKBACK}")
print(f"Min Swing Difference: {MIN_SWING_DIFF * 100}%")
print(f"Primary Entry Level: {FIB_ENTRY_LEVEL * 100}%")
print(f"Secondary Entry Level: {FIB_SECONDARY_LEVEL * 100}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Fast EMA: {EMA_FAST}")
print(f"Slow EMA: {EMA_SLOW}")
print(f"Signal EMA: {EMA_SIGNAL}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FIBONACCI RETRACEMENT + EMA ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(FibonacciRetracementEMA, 'FibonacciRetracementEMA')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FibonacciRetracementEMA.csv")