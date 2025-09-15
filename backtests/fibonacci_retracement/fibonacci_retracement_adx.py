"""
Moon Dev's Fibonacci Retracement + ADX Strategy
================================================
Fibonacci retracement with ADX trend strength filtering
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Fibonacci Retracement + ADX Strategy Loading... 🌙")

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
ADX_PERIOD = 14  # ADX period
ADX_THRESHOLD = 25  # Minimum ADX for strong trend

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class FibonacciRetracementADX(Strategy):
    """
    Fibonacci Retracement + ADX Strategy
    - Identify swing highs and lows using rolling windows
    - Calculate Fibonacci levels between swings
    - Use ADX to confirm trend strength before entry
    - Enter trades only in strong trends (ADX > threshold)
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
    
    # Trend filter
    trend_ma_period = TREND_MA_PERIOD
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Calculate trend MA
        ma = ta.sma(close, length=self.trend_ma_period)
        ma_full = np.full(len(close), np.nan)
        ma_full[-len(ma):] = ma.values
        self.ma = self.I(lambda: ma_full, name='MA')
        
        # Calculate ADX
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        if adx_result is not None and not adx_result.empty:
            adx = adx_result[f'ADX_{self.adx_period}']
            dmi_plus = adx_result[f'DMP_{self.adx_period}']
            dmi_minus = adx_result[f'DMN_{self.adx_period}']
            
            adx_full = np.full(len(close), np.nan)
            dmi_plus_full = np.full(len(close), np.nan)
            dmi_minus_full = np.full(len(close), np.nan)
            
            adx_full[-len(adx):] = adx.values
            dmi_plus_full[-len(dmi_plus):] = dmi_plus.values
            dmi_minus_full[-len(dmi_minus):] = dmi_minus.values
            
            self.adx = self.I(lambda: adx_full, name='ADX')
            self.dmi_plus = self.I(lambda: dmi_plus_full, name='DMI+')
            self.dmi_minus = self.I(lambda: dmi_minus_full, name='DMI-')
        else:
            self.adx = self.I(lambda: np.full(len(close), np.nan), name='ADX')
            self.dmi_plus = self.I(lambda: np.full(len(close), np.nan), name='DMI+')
            self.dmi_minus = self.I(lambda: np.full(len(close), np.nan), name='DMI-')
        
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
        
        if np.isnan(self.adx[-1]) or np.isnan(self.dmi_plus[-1]) or np.isnan(self.dmi_minus[-1]):
            return
        
        # Skip if we need more data
        if len(self.data) < self.swing_lookback * 2:
            return
        
        current_price = self.data.Close[-1]
        current_ma = self.ma[-1]
        current_adx = self.adx[-1]
        current_dmi_plus = self.dmi_plus[-1]
        current_dmi_minus = self.dmi_minus[-1]
        
        # Determine trend
        is_uptrend = current_price > current_ma
        
        # Check if trend is strong enough (ADX filter)
        strong_trend = current_adx > self.adx_threshold
        
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
            # Only trade in strong trends
            if not strong_trend:
                return
            
            if is_uptrend and current_dmi_plus > current_dmi_minus:
                # In uptrend with bullish DMI, buy at retracements
                # Check if price is at 61.8% retracement (primary)
                if self.fib_618 is not None:
                    at_618 = abs(current_price - self.fib_618) / current_price < 0.01
                    above_618 = current_price > self.fib_618 * 0.995
                    
                    if at_618 and above_618:
                        sl_price = current_price * (1 - self.stop_loss)
                        tp_price = current_price * (1 + self.take_profit)
                        self.buy(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
                
                # Check if price is at 38.2% retracement (secondary)
                if self.fib_382 is not None:
                    at_382 = abs(current_price - self.fib_382) / current_price < 0.01
                    above_382 = current_price > self.fib_382 * 0.995
                    
                    if at_382 and above_382:
                        sl_price = current_price * (1 - self.stop_loss)
                        tp_price = current_price * (1 + self.take_profit)
                        self.buy(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
            
            elif not is_uptrend and current_dmi_minus > current_dmi_plus:
                # In downtrend with bearish DMI, sell at retracements
                # Check if price is at 61.8% retracement (primary)
                if self.fib_618 is not None:
                    at_618 = abs(current_price - self.fib_618) / current_price < 0.01
                    below_618 = current_price < self.fib_618 * 1.005
                    
                    if at_618 and below_618:
                        sl_price = current_price * (1 + self.stop_loss)
                        tp_price = current_price * (1 - self.take_profit)
                        self.sell(sl=sl_price, tp=tp_price)
                        self.entry_price = current_price
                        self.in_position = True
                        return
                
                # Check if price is at 38.2% retracement (secondary)
                if self.fib_382 is not None:
                    at_382 = abs(current_price - self.fib_382) / current_price < 0.01
                    below_382 = current_price < self.fib_382 * 1.005
                    
                    if at_382 and below_382:
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
bt = Backtest(data, FibonacciRetracementADX, cash=100000, commission=0.00045)

print("\n🌙 ===== FIBONACCI RETRACEMENT + ADX - FIXED PARAMETERS ===== 🌙")
print(f"Swing Lookback: {SWING_LOOKBACK}")
print(f"Min Swing Difference: {MIN_SWING_DIFF * 100}%")
print(f"Primary Entry Level: {FIB_ENTRY_LEVEL * 100}%")
print(f"Secondary Entry Level: {FIB_SECONDARY_LEVEL * 100}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Trend MA Period: {TREND_MA_PERIOD}")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Threshold: {ADX_THRESHOLD}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING FIBONACCI RETRACEMENT + ADX ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(FibonacciRetracementADX, 'FibonacciRetracementADX')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/FibonacciRetracementADX.csv")