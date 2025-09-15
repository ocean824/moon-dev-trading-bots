"""
Moon Dev's Elliott Wave Impulse + ADX Strategy
==============================================
Impulse wave pattern trading with ADX trend strength confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("Loading Moon Dev's Elliott Wave Impulse + ADX Strategy...")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ZIGZAG_PERCENT = 5.0
FIBONACCI_TOLERANCE = 0.15
MIN_WAVE_BARS = 10
ADX_PERIOD = 14
ADX_THRESHOLD = 25  # Minimum ADX for trend strength
POSITION_SIZE = 0.95

print(f"Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"Data loaded! {len(data)} rows")

class ElliottImpulseADX(Strategy):
    """
    Elliott Wave Impulse + ADX Strategy
    - Identifies 5-wave impulse patterns
    - Confirms with ADX for trend strength
    - Only trades when ADX > threshold
    - Uses +DI/-DI for direction confirmation
    """
    
    # Zigzag parameters
    zigzag_pct = ZIGZAG_PERCENT / 100
    
    # Wave parameters
    min_wave_bars = MIN_WAVE_BARS
    fib_tolerance = FIBONACCI_TOLERANCE
    
    # ADX parameters
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    
    # Risk management
    atr_period = 14
    atr_multiplier = 2.0
    trailing_stop = 0.03
    
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
        
        # ADX for trend strength
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        self.adx = self.I(lambda: adx_result[f'ADX_{self.adx_period}'].fillna(0).values)
        self.plus_di = self.I(lambda: adx_result[f'DMP_{self.adx_period}'].fillna(0).values)
        self.minus_di = self.I(lambda: adx_result[f'DMN_{self.adx_period}'].fillna(0).values)
        
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
        
        # Trading logic
        if not self.position:
            # Look for entry opportunities with ADX confirmation
            if self.impulse_pattern and self.adx[-1] > self.adx_threshold:
                pattern = self.impulse_pattern
                
                if pattern['type'] == 'bullish':
                    # Confirm bullish trend with +DI > -DI
                    if self.plus_di[-1] > self.minus_di[-1]:
                        wave2 = pattern['waves'][2]
                        wave3 = pattern['waves'][3]
                        
                        # Check if we're in a good entry zone
                        if current_price > wave2 and current_price < wave3:
                            # Strong trend confirmation: ADX rising
                            if self.adx[-1] > self.adx[-2]:
                                self.stop_loss = wave2 - self.atr[-1] * self.atr_multiplier
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
                    # Confirm bearish trend with -DI > +DI
                    if self.minus_di[-1] > self.plus_di[-1]:
                        wave2 = pattern['waves'][2]
                        wave3 = pattern['waves'][3]
                        
                        if current_price < wave2 and current_price > wave3:
                            # Strong trend confirmation: ADX rising
                            if self.adx[-1] > self.adx[-2]:
                                self.stop_loss = wave2 + self.atr[-1] * self.atr_multiplier
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
                new_trailing_stop = current_price * (1 - self.trailing_stop)
                if new_trailing_stop > self.trailing_stop_price:
                    self.trailing_stop_price = new_trailing_stop
                    self.position.sl = self.trailing_stop_price
                
                # Exit if trend weakens (ADX falling or DI cross)
                if self.adx[-1] < self.adx_threshold or self.minus_di[-1] > self.plus_di[-1]:
                    self.position.close()
                    self.impulse_pattern = None
            
            elif self.position.is_short:
                # Update trailing stop for short position
                new_trailing_stop = current_price * (1 + self.trailing_stop)
                if new_trailing_stop < self.trailing_stop_price:
                    self.trailing_stop_price = new_trailing_stop
                    self.position.sl = self.trailing_stop_price
                
                # Exit if trend weakens
                if self.adx[-1] < self.adx_threshold or self.plus_di[-1] > self.minus_di[-1]:
                    self.position.close()
                    self.impulse_pattern = None

# Run single backtest
bt = Backtest(data, ElliottImpulseADX, cash=100000, commission=0.00045)

print("\n===== ELLIOTT WAVE IMPULSE + ADX - DEFAULT PARAMETERS =====")
print(f"Zigzag Percent: {ZIGZAG_PERCENT}%")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Threshold: {ADX_THRESHOLD}")

stats_default = bt.run()
print(stats_default)

# Skip optimization for now to avoid issues
print("\nSkipping optimization for stability...")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ELLIOTT WAVE IMPULSE + ADX ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(ElliottImpulseADX, 'ElliottImpulseADX')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/ElliottImpulseADX.csv")