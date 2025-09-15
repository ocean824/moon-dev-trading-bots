"""
Moon Dev's Elliott Wave Combined Trading Strategy
=================================================
Combined impulse and corrective wave pattern trading
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("Loading Moon Dev's Elliott Wave Combined Strategy...")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ZIGZAG_PERCENT = 4.5  # Percentage for zigzag reversal
FIBONACCI_TOLERANCE = 0.18  # Tolerance for fibonacci ratios
MIN_WAVE_BARS = 7  # Minimum bars for a wave
POSITION_SIZE = 0.95  # Use 95% of capital per trade

print(f"Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"Data loaded! {len(data)} rows")

class ElliottCombinedBase(Strategy):
    """
    Elliott Wave Combined Trading Strategy
    - Identifies both 5-wave impulse and 3-wave corrective patterns
    - Trades impulse waves in trend direction
    - Trades corrective waves as counter-trend
    - Switches between patterns based on market structure
    """
    
    # Zigzag parameters
    zigzag_pct = ZIGZAG_PERCENT / 100
    
    # Wave parameters
    min_wave_bars = MIN_WAVE_BARS
    fib_tolerance = FIBONACCI_TOLERANCE
    
    # Risk management
    atr_period = 14
    atr_multiplier = 1.8
    trailing_stop = 0.028
    
    # Pattern preference
    prefer_impulse = True  # Prefer impulse over corrective when both present
    
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
    
    def identify_impulse_waves(self, zigzag_points):
        """Identify potential 5-wave impulse patterns"""
        if len(zigzag_points) < 6:
            return None
        
        impulse_patterns = []
        
        # Look for 5-wave patterns
        for i in range(max(0, len(zigzag_points) - 10), len(zigzag_points) - 5):
            points = zigzag_points[i:i+6]
            
            # Check if pattern alternates correctly
            if points[0][2] == 'low':
                # Bullish impulse pattern
                if (points[1][2] == 'high' and points[2][2] == 'low' and 
                    points[3][2] == 'high' and points[4][2] == 'low' and 
                    points[5][2] == 'high'):
                    
                    # Extract wave points
                    wave0 = points[0][1]
                    wave1 = points[1][1]
                    wave2 = points[2][1]
                    wave3 = points[3][1]
                    wave4 = points[4][1]
                    wave5 = points[5][1]
                    
                    # Elliott Wave Rules
                    if (wave2 >= wave0 and  # Wave 2 doesn't go below start
                        wave4 > wave1 and    # Wave 4 doesn't overlap Wave 1
                        wave3 > wave1 and wave3 > wave5):  # Wave 3 not shortest
                        
                        # Check Fibonacci relationships
                        wave2_retrace = (wave1 - wave2) / (wave1 - wave0) if wave1 != wave0 else 0
                        if 0.3 <= wave2_retrace <= 0.8:  # Reasonable retracement
                            impulse_patterns.append({
                                'type': 'bullish_impulse',
                                'start_idx': points[0][0],
                                'end_idx': points[5][0],
                                'waves': [wave0, wave1, wave2, wave3, wave4, wave5],
                                'strength': wave3 / wave1 if wave1 > 0 else 1  # Wave 3 strength
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
                    
                    if (wave2 <= wave0 and  # Wave 2 doesn't exceed start
                        wave4 < wave1 and    # Wave 4 doesn't overlap Wave 1
                        wave3 < wave1 and wave3 < wave5):  # Wave 3 not shortest
                        
                        wave2_retrace = (wave2 - wave1) / (wave0 - wave1) if wave0 != wave1 else 0
                        if 0.3 <= wave2_retrace <= 0.8:
                            impulse_patterns.append({
                                'type': 'bearish_impulse',
                                'start_idx': points[0][0],
                                'end_idx': points[5][0],
                                'waves': [wave0, wave1, wave2, wave3, wave4, wave5],
                                'strength': abs(wave3 / wave1) if wave1 != 0 else 1
                            })
        
        # Return the most recent and strongest pattern
        if impulse_patterns:
            return max(impulse_patterns, key=lambda x: x['strength'])
        return None
    
    def identify_corrective_waves(self, zigzag_points):
        """Identify potential A-B-C corrective patterns"""
        if len(zigzag_points) < 4:
            return None
        
        corrective_patterns = []
        
        # Look for 3-wave patterns
        for i in range(max(0, len(zigzag_points) - 8), len(zigzag_points) - 3):
            points = zigzag_points[i:i+4]
            
            if points[0][2] == 'high':
                # Bearish corrective pattern
                if (points[1][2] == 'low' and points[2][2] == 'high' and 
                    points[3][2] == 'low'):
                    
                    start = points[0][1]
                    wave_a = points[1][1]
                    wave_b = points[2][1]
                    wave_c = points[3][1]
                    
                    # Check basic structure
                    if wave_b < start and wave_c < wave_a:
                        wave_b_retrace = (wave_b - wave_a) / (start - wave_a) if start != wave_a else 0
                        if 0.3 <= wave_b_retrace <= 0.9:  # Reasonable B wave
                            corrective_patterns.append({
                                'type': 'bearish_corrective',
                                'start_idx': points[0][0],
                                'end_idx': points[3][0],
                                'waves': [start, wave_a, wave_b, wave_c],
                                'depth': abs(wave_c - start) / start if start > 0 else 0
                            })
            
            elif points[0][2] == 'low':
                # Bullish corrective pattern
                if (points[1][2] == 'high' and points[2][2] == 'low' and 
                    points[3][2] == 'high'):
                    
                    start = points[0][1]
                    wave_a = points[1][1]
                    wave_b = points[2][1]
                    wave_c = points[3][1]
                    
                    if wave_b > start and wave_c > wave_a:
                        wave_b_retrace = (wave_a - wave_b) / (wave_a - start) if wave_a != start else 0
                        if 0.3 <= wave_b_retrace <= 0.9:
                            corrective_patterns.append({
                                'type': 'bullish_corrective',
                                'start_idx': points[0][0],
                                'end_idx': points[3][0],
                                'waves': [start, wave_a, wave_b, wave_c],
                                'depth': abs(wave_c - start) / start if start > 0 else 0
                            })
        
        # Return the most recent pattern with good depth
        if corrective_patterns:
            return max(corrective_patterns, key=lambda x: x['depth'])
        return None
    
    def init(self):
        # Calculate indicators
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # ATR for stop loss
        atr = ta.atr(high, low, close, length=self.atr_period)
        self.atr = self.I(lambda: atr.fillna(method='bfill').values)
        
        # RSI for overbought/oversold
        rsi = ta.rsi(close, length=14)
        self.rsi = self.I(lambda: rsi.fillna(50).values)
        
        # Moving average for trend
        self.sma_50 = self.I(lambda: ta.sma(close, length=50).fillna(method='bfill').values)
        self.sma_200 = self.I(lambda: ta.sma(close, length=200).fillna(method='bfill').values)
        
        # Calculate zigzag points
        self.zigzag_points = self.calculate_zigzag(close.values, self.zigzag_pct)
        
        # Track patterns
        self.impulse_pattern = None
        self.corrective_pattern = None
        self.active_pattern = None
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trailing_stop_price = 0
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < 200:
            return
        
        current_idx = len(self.data) - 1
        current_price = self.data.Close[-1]
        
        # Update zigzag points periodically
        if current_idx % 5 == 0:
            close_prices = self.data.Close[:current_idx+1]
            self.zigzag_points = self.calculate_zigzag(close_prices, self.zigzag_pct)
            
            # Identify both pattern types
            self.impulse_pattern = self.identify_impulse_waves(self.zigzag_points)
            self.corrective_pattern = self.identify_corrective_waves(self.zigzag_points)
        
        # Determine market trend
        is_uptrend = self.sma_50[-1] > self.sma_200[-1]
        
        # Trading logic
        if not self.position:
            # Decide which pattern to trade
            pattern_to_trade = None
            
            if self.impulse_pattern and self.corrective_pattern:
                # Both patterns present - choose based on preference and recency
                if self.prefer_impulse:
                    pattern_to_trade = self.impulse_pattern
                else:
                    # Choose more recent pattern
                    if self.impulse_pattern['end_idx'] > self.corrective_pattern['end_idx']:
                        pattern_to_trade = self.impulse_pattern
                    else:
                        pattern_to_trade = self.corrective_pattern
            elif self.impulse_pattern:
                pattern_to_trade = self.impulse_pattern
            elif self.corrective_pattern:
                pattern_to_trade = self.corrective_pattern
            
            if pattern_to_trade:
                # Trade impulse patterns
                if 'impulse' in pattern_to_trade['type']:
                    if pattern_to_trade['type'] == 'bullish_impulse':
                        # Enter long on bullish impulse
                        wave2 = pattern_to_trade['waves'][2]
                        wave3 = pattern_to_trade['waves'][3]
                        
                        # Check if we're in entry zone and RSI not overbought
                        if current_price > wave2 and current_price < wave3 and self.rsi[-1] < 70:
                            # Confirm with trend
                            if is_uptrend or self.rsi[-1] < 30:  # Oversold bounce acceptable
                                self.stop_loss = wave2 - self.atr[-1] * self.atr_multiplier
                                # Calculate realistic take profit from current position
                                wave1_length = abs(pattern_to_trade['waves'][1] - pattern_to_trade['waves'][0])
                                self.take_profit = current_price + wave1_length * 0.618
                                
                                # Ensure proper order for long
                                if self.stop_loss >= current_price:
                                    self.stop_loss = current_price - self.atr[-1] * 2
                                min_profit_distance = self.atr[-1] * 2
                                if self.take_profit <= current_price + min_profit_distance:
                                    self.take_profit = current_price + min_profit_distance
                                
                                self.buy(sl=self.stop_loss, tp=self.take_profit, size=POSITION_SIZE)
                                self.entry_price = current_price
                                self.trailing_stop_price = self.stop_loss
                                self.active_pattern = 'bullish_impulse'
                    
                    elif pattern_to_trade['type'] == 'bearish_impulse':
                        # Enter short on bearish impulse
                        wave2 = pattern_to_trade['waves'][2]
                        wave3 = pattern_to_trade['waves'][3]
                        
                        if current_price < wave2 and current_price > wave3 and self.rsi[-1] > 30:
                            # Confirm with trend
                            if not is_uptrend or self.rsi[-1] > 70:  # Overbought reversal acceptable
                                self.stop_loss = wave2 + self.atr[-1] * self.atr_multiplier
                                # Calculate realistic take profit from current position
                                wave1_length = abs(pattern_to_trade['waves'][0] - pattern_to_trade['waves'][1])
                                self.take_profit = current_price - wave1_length * 0.618
                                
                                # Ensure proper order for short
                                min_profit_distance = self.atr[-1] * 2
                                if self.take_profit >= current_price - min_profit_distance:
                                    self.take_profit = current_price - min_profit_distance
                                if self.stop_loss <= current_price:
                                    self.stop_loss = current_price + self.atr[-1] * 2
                                
                                self.sell(sl=self.stop_loss, tp=self.take_profit, size=POSITION_SIZE)
                                self.entry_price = current_price
                                self.trailing_stop_price = self.stop_loss
                                self.active_pattern = 'bearish_impulse'
                
                # Trade corrective patterns
                elif 'corrective' in pattern_to_trade['type']:
                    if pattern_to_trade['type'] == 'bearish_corrective':
                        # Short the correction
                        wave_b = pattern_to_trade['waves'][2]
                        wave_c = pattern_to_trade['waves'][3]
                        
                        if current_price < wave_b and current_price > wave_c and self.rsi[-1] > 50:
                            self.stop_loss = wave_b + self.atr[-1] * self.atr_multiplier
                            # Target Wave C completion
                            wave_a_length = abs(pattern_to_trade['waves'][0] - pattern_to_trade['waves'][1])
                            self.take_profit = current_price - wave_a_length * 0.618  # Conservative target from current price
                            
                            # Ensure TP < current price < SL for short orders
                            min_profit_distance = self.atr[-1] * 2
                            if self.take_profit >= current_price - min_profit_distance:
                                self.take_profit = current_price - min_profit_distance
                            if self.stop_loss <= current_price:
                                self.stop_loss = current_price + self.atr[-1] * 2
                            
                            self.sell(sl=self.stop_loss, tp=self.take_profit, size=POSITION_SIZE)
                            self.entry_price = current_price
                            self.trailing_stop_price = self.stop_loss
                            self.active_pattern = 'bearish_corrective'
                    
                    elif pattern_to_trade['type'] == 'bullish_corrective':
                        # Long the correction
                        wave_b = pattern_to_trade['waves'][2]
                        wave_c = pattern_to_trade['waves'][3]
                        
                        if current_price > wave_b and current_price < wave_c and self.rsi[-1] < 50:
                            self.stop_loss = wave_b - self.atr[-1] * self.atr_multiplier
                            wave_a_length = abs(pattern_to_trade['waves'][1] - pattern_to_trade['waves'][0])
                            self.take_profit = current_price + wave_a_length * 0.618  # Conservative target from current price
                            
                            # Ensure SL < current price < TP for long orders
                            if self.stop_loss >= current_price:
                                self.stop_loss = current_price - self.atr[-1] * 2
                            min_profit_distance = self.atr[-1] * 2
                            if self.take_profit <= current_price + min_profit_distance:
                                self.take_profit = current_price + min_profit_distance
                            
                            self.buy(sl=self.stop_loss, tp=self.take_profit, size=POSITION_SIZE)
                            self.entry_price = current_price
                            self.trailing_stop_price = self.stop_loss
                            self.active_pattern = 'bullish_corrective'
        
        else:
            # Manage existing position with trailing stop
            if self.position.is_long:
                # Update trailing stop for long position
                new_trailing_stop = current_price * (1 - self.trailing_stop)
                if new_trailing_stop > self.trailing_stop_price:
                    self.trailing_stop_price = new_trailing_stop
                    self.position.sl = self.trailing_stop_price
                
                # Exit on RSI overbought in strong move
                if self.rsi[-1] > 80:
                    self.position.close()
                    self.active_pattern = None
            
            elif self.position.is_short:
                # Update trailing stop for short position
                new_trailing_stop = current_price * (1 + self.trailing_stop)
                if new_trailing_stop < self.trailing_stop_price:
                    self.trailing_stop_price = new_trailing_stop
                    self.position.sl = self.trailing_stop_price
                
                # Exit on RSI oversold in strong move
                if self.rsi[-1] < 20:
                    self.position.close()
                    self.active_pattern = None

# Run single backtest
bt = Backtest(data, ElliottCombinedBase, cash=100000, commission=0.00045)

print("\n===== ELLIOTT WAVE COMBINED - DEFAULT PARAMETERS =====")
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
    print("TESTING ELLIOTT WAVE COMBINED ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(ElliottCombinedBase, 'ElliottCombinedBase')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/ElliottCombinedBase.csv")