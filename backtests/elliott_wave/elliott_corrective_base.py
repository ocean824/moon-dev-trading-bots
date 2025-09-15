"""
Moon Dev's Elliott Wave Corrective Trading Strategy
===================================================
Pure corrective wave (A-B-C) pattern trading strategy
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("Loading Moon Dev's Elliott Wave Corrective Strategy...")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ZIGZAG_PERCENT = 4.0  # Percentage for zigzag reversal
FIBONACCI_TOLERANCE = 0.15  # Tolerance for fibonacci ratios
MIN_WAVE_BARS = 8  # Minimum bars for a wave
POSITION_SIZE = 0.95  # Use 95% of capital per trade

print(f"Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"Data loaded! {len(data)} rows")

class ElliottCorrectiveBase(Strategy):
    """
    Elliott Wave Corrective Trading Strategy
    - Identifies 3-wave corrective patterns (A-B-C)
    - Enters after impulse wave completion
    - Trades the corrective move
    - Uses Fibonacci extensions for targets
    """
    
    # Zigzag parameters
    zigzag_pct = ZIGZAG_PERCENT / 100
    
    # Wave parameters
    min_wave_bars = MIN_WAVE_BARS
    fib_tolerance = FIBONACCI_TOLERANCE
    
    # Risk management
    atr_period = 14
    atr_multiplier = 1.5
    trailing_stop = 0.025
    
    def calculate_zigzag(self, prices, pct):
        """Calculate zigzag points for wave identification"""
        zigzag_points = []
        current_trend = None
        last_pivot = prices[0]
        last_pivot_idx = 0
        
        for i in range(1, len(prices)):
            # Check for reversal
            if current_trend == 'up':
                if prices[i] <= last_pivot * (1 - pct):
                    zigzag_points.append((last_pivot_idx, last_pivot, 'high'))
                    last_pivot = prices[i]
                    last_pivot_idx = i
                    current_trend = 'down'
                elif prices[i] > last_pivot:
                    last_pivot = prices[i]
                    last_pivot_idx = i
            elif current_trend == 'down':
                if prices[i] >= last_pivot * (1 + pct):
                    zigzag_points.append((last_pivot_idx, last_pivot, 'low'))
                    last_pivot = prices[i]
                    last_pivot_idx = i
                    current_trend = 'up'
                elif prices[i] < last_pivot:
                    last_pivot = prices[i]
                    last_pivot_idx = i
            else:
                # Initialize trend
                if prices[i] >= last_pivot * (1 + pct):
                    current_trend = 'up'
                    last_pivot = prices[i]
                    last_pivot_idx = i
                elif prices[i] <= last_pivot * (1 - pct):
                    current_trend = 'down'
                    last_pivot = prices[i]
                    last_pivot_idx = i
        
        return zigzag_points
    
    def identify_corrective_waves(self, zigzag_points):
        """Identify potential A-B-C corrective patterns"""
        if len(zigzag_points) < 4:
            return None
        
        corrective_patterns = []
        
        # Look for 3-wave patterns (need 4 points: start + 3 waves)
        for i in range(len(zigzag_points) - 3):
            points = zigzag_points[i:i+4]
            
            # Check if pattern alternates correctly
            if points[0][2] == 'high':
                # Bearish corrective pattern (down correction after up move)
                if (points[1][2] == 'low' and points[2][2] == 'high' and 
                    points[3][2] == 'low'):
                    
                    # Extract wave points
                    start = points[0][1]  # Start (end of impulse)
                    wave_a = points[1][1]  # Wave A low
                    wave_b = points[2][1]  # Wave B high
                    wave_c = points[3][1]  # Wave C low
                    
                    # Corrective wave rules
                    # Wave B typically retraces 38.2%, 50%, or 61.8% of Wave A
                    wave_b_retrace = (wave_b - wave_a) / (start - wave_a) if start != wave_a else 0
                    
                    # Wave C often equals Wave A or is 1.618x Wave A
                    wave_a_length = abs(start - wave_a)
                    wave_c_length = abs(wave_b - wave_c)
                    wave_c_ratio = wave_c_length / wave_a_length if wave_a_length > 0 else 0
                    
                    # Check Fibonacci relationships
                    fib_retracements = [0.382, 0.5, 0.618]
                    fib_extensions = [1.0, 1.618]
                    
                    b_valid = any(abs(wave_b_retrace - level) < self.fib_tolerance for level in fib_retracements)
                    c_valid = any(abs(wave_c_ratio - level) < self.fib_tolerance * 2 for level in fib_extensions)
                    
                    # More lenient validation for corrective waves
                    if b_valid or c_valid or (wave_b < start and wave_c < wave_a):
                        corrective_patterns.append({
                            'type': 'bearish_corrective',
                            'start_idx': points[0][0],
                            'end_idx': points[3][0],
                            'waves': [start, wave_a, wave_b, wave_c],
                            'current_wave': 'C'
                        })
            
            elif points[0][2] == 'low':
                # Bullish corrective pattern (up correction after down move)
                if (points[1][2] == 'high' and points[2][2] == 'low' and 
                    points[3][2] == 'high'):
                    
                    # Extract wave points
                    start = points[0][1]  # Start (end of impulse)
                    wave_a = points[1][1]  # Wave A high
                    wave_b = points[2][1]  # Wave B low
                    wave_c = points[3][1]  # Wave C high
                    
                    # Corrective wave rules
                    wave_b_retrace = (wave_a - wave_b) / (wave_a - start) if wave_a != start else 0
                    
                    wave_a_length = abs(wave_a - start)
                    wave_c_length = abs(wave_c - wave_b)
                    wave_c_ratio = wave_c_length / wave_a_length if wave_a_length > 0 else 0
                    
                    # Check Fibonacci relationships
                    fib_retracements = [0.382, 0.5, 0.618]
                    fib_extensions = [1.0, 1.618]
                    
                    b_valid = any(abs(wave_b_retrace - level) < self.fib_tolerance for level in fib_retracements)
                    c_valid = any(abs(wave_c_ratio - level) < self.fib_tolerance * 2 for level in fib_extensions)
                    
                    if b_valid or c_valid or (wave_b > start and wave_c > wave_a):
                        corrective_patterns.append({
                            'type': 'bullish_corrective',
                            'start_idx': points[0][0],
                            'end_idx': points[3][0],
                            'waves': [start, wave_a, wave_b, wave_c],
                            'current_wave': 'C'
                        })
        
        return corrective_patterns[-1] if corrective_patterns else None
    
    def init(self):
        # Calculate indicators
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # ATR for stop loss
        atr = ta.atr(high, low, close, length=self.atr_period)
        self.atr = self.I(lambda: atr.fillna(method='bfill').values)
        
        # Volume for confirmation
        volume = pd.Series(self.data.Volume)
        self.volume_sma = self.I(lambda: ta.sma(volume, length=20).fillna(method='bfill').values)
        
        # Calculate zigzag points
        self.zigzag_points = self.calculate_zigzag(close.values, self.zigzag_pct)
        
        # Track corrective patterns
        self.corrective_pattern = None
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trailing_stop_price = 0
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < 50:
            return
        
        current_idx = len(self.data) - 1
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        
        # Update zigzag points periodically
        if current_idx % 5 == 0:
            close_prices = self.data.Close[:current_idx+1]
            self.zigzag_points = self.calculate_zigzag(close_prices, self.zigzag_pct)
            
            # Identify corrective patterns
            pattern = self.identify_corrective_waves(self.zigzag_points)
            if pattern and pattern['end_idx'] >= current_idx - 15:
                self.corrective_pattern = pattern
        
        # Trading logic
        if not self.position:
            # Look for entry opportunities
            if self.corrective_pattern:
                pattern = self.corrective_pattern
                
                if pattern['type'] == 'bearish_corrective':
                    # Trade the bearish correction
                    # Enter short on Wave B rally or early Wave C
                    wave_b = pattern['waves'][2]
                    wave_c = pattern['waves'][3]
                    
                    # Check if we're in a good entry zone
                    if current_price < wave_b and current_price > wave_c:
                        # Volume confirmation - should be declining in corrections
                        if current_volume < self.volume_sma[-1] * 1.2:
                            # Calculate stops
                            self.stop_loss = wave_b + self.atr[-1] * self.atr_multiplier
                            
                            # Use Fibonacci extension for target
                            wave_a_length = abs(pattern['waves'][0] - pattern['waves'][1])
                            # For bearish corrective, we expect price to go DOWN from current position
                            self.take_profit = current_price - wave_a_length * 0.618  # Use more conservative target
                            
                            # Ensure TP < current price < SL for short orders
                            min_profit_distance = self.atr[-1] * 2
                            if self.take_profit >= current_price - min_profit_distance:
                                self.take_profit = current_price - min_profit_distance
                            if self.stop_loss <= current_price:
                                self.stop_loss = current_price + self.atr[-1] * 2
                            
                            # Enter short position
                            self.sell(sl=self.stop_loss, tp=self.take_profit, size=POSITION_SIZE)
                            self.entry_price = current_price
                            self.trailing_stop_price = self.stop_loss
                
                elif pattern['type'] == 'bullish_corrective':
                    # Trade the bullish correction
                    wave_b = pattern['waves'][2]
                    wave_c = pattern['waves'][3]
                    
                    if current_price > wave_b and current_price < wave_c:
                        # Volume confirmation
                        if current_volume < self.volume_sma[-1] * 1.2:
                            # Calculate stops
                            self.stop_loss = wave_b - self.atr[-1] * self.atr_multiplier
                            
                            # Use Fibonacci extension for target
                            wave_a_length = abs(pattern['waves'][1] - pattern['waves'][0])
                            # For bullish corrective, we expect price to go UP from current position
                            self.take_profit = current_price + wave_a_length * 0.618  # Use more conservative target
                            
                            # Ensure SL < current price < TP for long orders
                            if self.stop_loss >= current_price:
                                self.stop_loss = current_price - self.atr[-1] * 2
                            # Always ensure TP is meaningfully above current price
                            min_profit_distance = self.atr[-1] * 2
                            if self.take_profit <= current_price + min_profit_distance:
                                self.take_profit = current_price + min_profit_distance
                            
                            # Enter long position
                            self.buy(sl=self.stop_loss, tp=self.take_profit, size=POSITION_SIZE)
                            self.entry_price = current_price
                            self.trailing_stop_price = self.stop_loss
        
        else:
            # Manage existing position with trailing stop
            if self.position.is_long:
                # Update trailing stop for long position
                new_trailing_stop = current_price * (1 - self.trailing_stop)
                if new_trailing_stop > self.trailing_stop_price:
                    self.trailing_stop_price = new_trailing_stop
                    self.position.sl = self.trailing_stop_price
                
                # Exit if pattern completion
                if self.corrective_pattern and current_idx >= self.corrective_pattern['end_idx'] + 5:
                    self.position.close()
                    self.corrective_pattern = None
            
            elif self.position.is_short:
                # Update trailing stop for short position
                new_trailing_stop = current_price * (1 + self.trailing_stop)
                if new_trailing_stop < self.trailing_stop_price:
                    self.trailing_stop_price = new_trailing_stop
                    self.position.sl = self.trailing_stop_price
                
                # Exit if pattern completion
                if self.corrective_pattern and current_idx >= self.corrective_pattern['end_idx'] + 5:
                    self.position.close()
                    self.corrective_pattern = None

# Run single backtest
bt = Backtest(data, ElliottCorrectiveBase, cash=100000, commission=0.00045)

print("\n===== ELLIOTT WAVE CORRECTIVE - DEFAULT PARAMETERS =====")
print(f"Zigzag Percent: {ZIGZAG_PERCENT}%")
print(f"Fibonacci Tolerance: {FIBONACCI_TOLERANCE}")
print(f"Min Wave Bars: {MIN_WAVE_BARS}")

stats_default = bt.run()
print(stats_default)

# Skip optimization for now to avoid issues
print("\nSkipping optimization for stability...")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ELLIOTT WAVE CORRECTIVE ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(ElliottCorrectiveBase, 'ElliottCorrectiveBase')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/ElliottCorrectiveBase.csv")