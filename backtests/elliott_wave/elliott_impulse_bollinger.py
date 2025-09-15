"""
Moon Dev's Elliott Wave Impulse + Bollinger Bands Strategy
==========================================================
Impulse wave pattern trading with Bollinger Bands for volatility confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("Loading Moon Dev's Elliott Wave Impulse + Bollinger Bands Strategy...")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ZIGZAG_PERCENT = 5.0
FIBONACCI_TOLERANCE = 0.15
MIN_WAVE_BARS = 10
BB_LENGTH = 20
BB_STD = 2.0
POSITION_SIZE = 0.95

print(f"Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"Data loaded! {len(data)} rows")

class ElliottImpulseBollinger(Strategy):
    """
    Elliott Wave Impulse + Bollinger Bands Strategy
    - Identifies 5-wave impulse patterns
    - Uses Bollinger Bands for volatility context
    - Enters on band touches during wave patterns
    - Uses bandwidth for volatility confirmation
    """
    
    # Zigzag parameters
    zigzag_pct = ZIGZAG_PERCENT / 100
    
    # Wave parameters
    min_wave_bars = MIN_WAVE_BARS
    fib_tolerance = FIBONACCI_TOLERANCE
    
    # Bollinger Bands parameters
    bb_length = BB_LENGTH
    bb_std = BB_STD
    
    # Risk management
    atr_period = 14
    atr_multiplier = 1.8
    trailing_stop = 0.025
    
    def calculate_zigzag(self, prices, pct):
        """Calculate zigzag points for wave identification"""
        zigzag_points = []
        current_trend = None
        last_pivot = prices[0]
        last_pivot_idx = 0
        
        for i in range(1, len(prices)):
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
                if prices[i] >= last_pivot * (1 + pct):
                    current_trend = 'up'
                    last_pivot = prices[i]
                    last_pivot_idx = i
                elif prices[i] <= last_pivot * (1 - pct):
                    current_trend = 'down'
                    last_pivot = prices[i]
                    last_pivot_idx = i
        
        return zigzag_points
    
    def identify_impulse_waves(self, zigzag_points):
        """Identify potential 5-wave impulse patterns"""
        if len(zigzag_points) < 6:
            return None
        
        impulse_patterns = []
        
        for i in range(len(zigzag_points) - 5):
            points = zigzag_points[i:i+6]
            
            if points[0][2] == 'low':
                # Bullish impulse pattern
                if (points[1][2] == 'high' and points[2][2] == 'low' and 
                    points[3][2] == 'high' and points[4][2] == 'low' and 
                    points[5][2] == 'high'):
                    
                    wave0 = points[0][1]
                    wave1 = points[1][1]
                    wave2 = points[2][1]
                    wave3 = points[3][1]
                    wave4 = points[4][1]
                    wave5 = points[5][1]
                    
                    # Elliott Wave Rules
                    if wave2 >= wave0:
                        wave1_length = abs(wave1 - wave0)
                        wave3_length = abs(wave3 - wave2)
                        wave5_length = abs(wave5 - wave4)
                        
                        if wave3_length > min(wave1_length, wave5_length):
                            if wave4 > wave1:
                                wave2_retrace = (wave1 - wave2) / (wave1 - wave0) if wave1 != wave0 else 0
                                wave4_retrace = (wave3 - wave4) / (wave3 - wave2) if wave3 != wave2 else 0
                                
                                fib_levels = [0.382, 0.5, 0.618]
                                wave2_valid = any(abs(wave2_retrace - level) < self.fib_tolerance for level in fib_levels)
                                wave4_valid = any(abs(wave4_retrace - level) < self.fib_tolerance for level in fib_levels)
                                
                                if wave2_valid or wave4_valid:
                                    impulse_patterns.append({
                                        'type': 'bullish',
                                        'start_idx': points[0][0],
                                        'end_idx': points[5][0],
                                        'waves': [wave0, wave1, wave2, wave3, wave4, wave5],
                                        'current_wave': 5
                                    })
            
            elif points[0][2] == 'high':
                # Bearish impulse pattern
                if (points[1][2] == 'low' and points[2][2] == 'high' and 
                    points[3][2] == 'low' and points[4][2] == 'high' and 
                    points[5][2] == 'low'):
                    
                    wave0 = points[0][1]
                    wave1 = points[1][1]
                    wave2 = points[2][1]
                    wave3 = points[3][1]
                    wave4 = points[4][1]
                    wave5 = points[5][1]
                    
                    if wave2 <= wave0:
                        wave1_length = abs(wave0 - wave1)
                        wave3_length = abs(wave2 - wave3)
                        wave5_length = abs(wave4 - wave5)
                        
                        if wave3_length > min(wave1_length, wave5_length):
                            if wave4 < wave1:
                                wave2_retrace = (wave2 - wave1) / (wave0 - wave1) if wave0 != wave1 else 0
                                wave4_retrace = (wave4 - wave3) / (wave2 - wave3) if wave2 != wave3 else 0
                                
                                fib_levels = [0.382, 0.5, 0.618]
                                wave2_valid = any(abs(wave2_retrace - level) < self.fib_tolerance for level in fib_levels)
                                wave4_valid = any(abs(wave4_retrace - level) < self.fib_tolerance for level in fib_levels)
                                
                                if wave2_valid or wave4_valid:
                                    impulse_patterns.append({
                                        'type': 'bearish',
                                        'start_idx': points[0][0],
                                        'end_idx': points[5][0],
                                        'waves': [wave0, wave1, wave2, wave3, wave4, wave5],
                                        'current_wave': 5
                                    })
        
        return impulse_patterns[-1] if impulse_patterns else None
    
    def init(self):
        # Calculate indicators
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # ATR for stop loss
        atr = ta.atr(high, low, close, length=self.atr_period)
        self.atr = self.I(lambda: atr.fillna(method='bfill').values)
        
        # Bollinger Bands
        bb = ta.bbands(close, length=self.bb_length, std=self.bb_std)
        self.bb_upper = self.I(lambda: bb[f'BBU_{self.bb_length}_{self.bb_std}'].fillna(method='bfill').values)
        self.bb_middle = self.I(lambda: bb[f'BBM_{self.bb_length}_{self.bb_std}'].fillna(method='bfill').values)
        self.bb_lower = self.I(lambda: bb[f'BBL_{self.bb_length}_{self.bb_std}'].fillna(method='bfill').values)
        
        # Bollinger Band Width for volatility
        bb_width = (self.bb_upper.data - self.bb_lower.data) / self.bb_middle.data
        self.bb_width = self.I(lambda: bb_width)
        
        # Bollinger %B for position within bands
        bb_percent = (close - self.bb_lower.data) / (self.bb_upper.data - self.bb_lower.data)
        self.bb_percent = self.I(lambda: bb_percent.fillna(0.5).values)
        
        # Calculate zigzag points
        self.zigzag_points = self.calculate_zigzag(close.values, self.zigzag_pct)
        
        # Track impulse patterns
        self.impulse_pattern = None
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trailing_stop_price = 0
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < 100:
            return
        
        current_idx = len(self.data) - 1
        current_price = self.data.Close[-1]
        
        # Update zigzag points periodically
        if current_idx % 10 == 0:
            close_prices = self.data.Close[:current_idx+1]
            self.zigzag_points = self.calculate_zigzag(close_prices, self.zigzag_pct)
            
            # Identify impulse patterns
            pattern = self.identify_impulse_waves(self.zigzag_points)
            if pattern and pattern['end_idx'] >= current_idx - 20:
                self.impulse_pattern = pattern
        
        # Calculate Bollinger Band conditions
        bb_squeeze = self.bb_width[-1] < np.mean(self.bb_width[-20:]) * 0.8  # Volatility squeeze
        bb_expansion = self.bb_width[-1] > np.mean(self.bb_width[-20:]) * 1.2  # Volatility expansion
        
        # Trading logic
        if not self.position:
            # Look for entry opportunities with Bollinger Band confirmation
            if self.impulse_pattern:
                pattern = self.impulse_pattern
                
                if pattern['type'] == 'bullish':
                    wave2 = pattern['waves'][2]
                    wave3 = pattern['waves'][3]
                    
                    # Check if we're in a good entry zone
                    if current_price > wave2 and current_price < wave3:
                        # Best entry: price near lower band or middle band with squeeze
                        if self.bb_percent[-1] < 0.3 or (bb_squeeze and self.bb_percent[-1] < 0.6):
                            # Confirm momentum with band walk
                            if current_price > self.bb_lower[-1]:
                                self.stop_loss = max(wave2 - self.atr[-1] * self.atr_multiplier, 
                                                   self.bb_lower[-1] * 0.98)
                                # Calculate realistic take profit from current position
                                wave1_length = abs(pattern['waves'][1] - pattern['waves'][0])
                                self.take_profit = current_price + wave1_length * 0.618
                                
                                # Ensure SL < current price < TP for long orders
                                if self.stop_loss >= current_price:
                                    self.stop_loss = current_price - self.atr[-1] * 2
                                min_profit_distance = self.atr[-1] * 2
                                if self.take_profit <= current_price + min_profit_distance:
                                    self.take_profit = current_price + min_profit_distance
                                
                                self.buy(sl=self.stop_loss, tp=self.take_profit, size=POSITION_SIZE)
                                self.entry_price = current_price
                                self.trailing_stop_price = self.stop_loss
                
                elif pattern['type'] == 'bearish':
                    wave2 = pattern['waves'][2]
                    wave3 = pattern['waves'][3]
                    
                    if current_price < wave2 and current_price > wave3:
                        # Best entry: price near upper band or middle band with squeeze
                        if self.bb_percent[-1] > 0.7 or (bb_squeeze and self.bb_percent[-1] > 0.4):
                            # Confirm momentum with band walk
                            if current_price < self.bb_upper[-1]:
                                self.stop_loss = min(wave2 + self.atr[-1] * self.atr_multiplier,
                                                   self.bb_upper[-1] * 1.02)
                                # Calculate realistic take profit from current position
                                wave1_length = abs(pattern['waves'][0] - pattern['waves'][1])
                                self.take_profit = current_price - wave1_length * 0.618
                                
                                # Ensure TP < current price < SL for short orders
                                min_profit_distance = self.atr[-1] * 2
                                if self.take_profit >= current_price - min_profit_distance:
                                    self.take_profit = current_price - min_profit_distance
                                if self.stop_loss <= current_price:
                                    self.stop_loss = current_price + self.atr[-1] * 2
                                
                                self.sell(sl=self.stop_loss, tp=self.take_profit, size=POSITION_SIZE)
                                self.entry_price = current_price
                                self.trailing_stop_price = self.stop_loss
        
        else:
            # Manage existing position
            if self.position.is_long:
                # Update trailing stop for long position
                new_trailing_stop = max(current_price * (1 - self.trailing_stop),
                                       self.bb_lower[-1])
                if new_trailing_stop > self.trailing_stop_price:
                    self.trailing_stop_price = new_trailing_stop
                    self.position.sl = self.trailing_stop_price
                
                # Exit if price walks upper band with expansion (overextended)
                if self.bb_percent[-1] > 1.0 and bb_expansion:
                    self.position.close()
                    self.impulse_pattern = None
            
            elif self.position.is_short:
                # Update trailing stop for short position
                new_trailing_stop = min(current_price * (1 + self.trailing_stop),
                                       self.bb_upper[-1])
                if new_trailing_stop < self.trailing_stop_price:
                    self.trailing_stop_price = new_trailing_stop
                    self.position.sl = self.trailing_stop_price
                
                # Exit if price walks lower band with expansion (overextended)
                if self.bb_percent[-1] < 0.0 and bb_expansion:
                    self.position.close()
                    self.impulse_pattern = None

# Run single backtest
bt = Backtest(data, ElliottImpulseBollinger, cash=100000, commission=0.00045)

print("\n===== ELLIOTT WAVE IMPULSE + BOLLINGER - DEFAULT PARAMETERS =====")
print(f"Zigzag Percent: {ZIGZAG_PERCENT}%")
print(f"Bollinger Length: {BB_LENGTH}")
print(f"Bollinger Std: {BB_STD}")

stats_default = bt.run()
print(stats_default)

# Skip optimization for now to avoid issues
print("\nSkipping optimization for stability...")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ELLIOTT WAVE IMPULSE + BOLLINGER ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(ElliottImpulseBollinger, 'ElliottImpulseBollinger')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/ElliottImpulseBollinger.csv")