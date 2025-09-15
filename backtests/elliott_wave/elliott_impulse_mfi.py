"""
Moon Dev's Elliott Wave Impulse + MFI Strategy
==============================================
Impulse wave pattern trading with MFI volume confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("Loading Moon Dev's Elliott Wave Impulse + MFI Strategy...")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
ZIGZAG_PERCENT = 5.0
FIBONACCI_TOLERANCE = 0.15
MIN_WAVE_BARS = 10
MFI_PERIOD = 14
MFI_OVERBOUGHT = 80
MFI_OVERSOLD = 20
POSITION_SIZE = 0.95

print(f"Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"Data loaded! {len(data)} rows")

class ElliottImpulseMFI(Strategy):
    """
    Elliott Wave Impulse + MFI Strategy
    - Identifies 5-wave impulse patterns
    - Confirms with MFI for volume flow
    - Avoids overbought/oversold extremes
    - Uses MFI divergence for extra confirmation
    """
    
    # Zigzag parameters
    zigzag_pct = ZIGZAG_PERCENT / 100
    
    # Wave parameters
    min_wave_bars = MIN_WAVE_BARS
    fib_tolerance = FIBONACCI_TOLERANCE
    
    # MFI parameters
    mfi_period = MFI_PERIOD
    mfi_overbought = MFI_OVERBOUGHT
    mfi_oversold = MFI_OVERSOLD
    
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
    
    def detect_mfi_divergence(self, prices, mfi_values, lookback=20):
        """Detect divergence between price and MFI"""
        if len(prices) < lookback or len(mfi_values) < lookback:
            return None
            
        # Find recent highs and lows
        recent_prices = prices[-lookback:]
        recent_mfi = mfi_values[-lookback:]
        
        price_high_idx = np.argmax(recent_prices)
        price_low_idx = np.argmin(recent_prices)
        mfi_high_idx = np.argmax(recent_mfi)
        mfi_low_idx = np.argmin(recent_mfi)
        
        # Bullish divergence: price makes lower low, MFI makes higher low
        if price_low_idx > lookback//2:  # Recent low
            prev_price_low_idx = np.argmin(recent_prices[:price_low_idx-2])
            if recent_prices[price_low_idx] < recent_prices[prev_price_low_idx]:
                if recent_mfi[price_low_idx] > recent_mfi[prev_price_low_idx]:
                    return 'bullish'
        
        # Bearish divergence: price makes higher high, MFI makes lower high
        if price_high_idx > lookback//2:  # Recent high
            prev_price_high_idx = np.argmax(recent_prices[:price_high_idx-2])
            if recent_prices[price_high_idx] > recent_prices[prev_price_high_idx]:
                if recent_mfi[price_high_idx] < recent_mfi[prev_price_high_idx]:
                    return 'bearish'
        
        return None
    
    def init(self):
        # Calculate indicators
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # ATR for stop loss
        atr = ta.atr(high, low, close, length=self.atr_period)
        self.atr = self.I(lambda: atr.fillna(method='bfill').values)
        
        # MFI for volume flow
        mfi = ta.mfi(high, low, close, volume, length=self.mfi_period)
        self.mfi = self.I(lambda: mfi.fillna(50).values)
        
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
        current_mfi = self.mfi[-1]
        
        # Update zigzag points periodically
        if current_idx % 10 == 0:
            close_prices = self.data.Close[:current_idx+1]
            self.zigzag_points = self.calculate_zigzag(close_prices, self.zigzag_pct)
            
            # Identify impulse patterns
            pattern = self.identify_impulse_waves(self.zigzag_points)
            if pattern and pattern['end_idx'] >= current_idx - 20:
                self.impulse_pattern = pattern
        
        # Check for MFI divergence
        divergence = self.detect_mfi_divergence(
            self.data.Close[-30:], 
            self.mfi[-30:]
        )
        
        # Trading logic
        if not self.position:
            # Look for entry opportunities with MFI confirmation
            if self.impulse_pattern:
                pattern = self.impulse_pattern
                
                if pattern['type'] == 'bullish':
                    # Confirm not overbought and preferably oversold or divergence
                    if current_mfi < self.mfi_overbought:
                        wave2 = pattern['waves'][2]
                        wave3 = pattern['waves'][3]
                        
                        # Check if we're in a good entry zone
                        if current_price > wave2 and current_price < wave3:
                            # Best entry: oversold or bullish divergence
                            if current_mfi < self.mfi_oversold or divergence == 'bullish':
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
                            # Good entry: MFI rising from low
                            elif current_mfi < 50 and self.mfi[-1] > self.mfi[-2]:
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
                    # Confirm not oversold and preferably overbought or divergence
                    if current_mfi > self.mfi_oversold:
                        wave2 = pattern['waves'][2]
                        wave3 = pattern['waves'][3]
                        
                        if current_price < wave2 and current_price > wave3:
                            # Best entry: overbought or bearish divergence
                            if current_mfi > self.mfi_overbought or divergence == 'bearish':
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
                            # Good entry: MFI falling from high
                            elif current_mfi > 50 and self.mfi[-1] < self.mfi[-2]:
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
                
                # Exit if MFI extremely overbought or bearish divergence
                if current_mfi > 85 or divergence == 'bearish':
                    self.position.close()
                    self.impulse_pattern = None
            
            elif self.position.is_short:
                # Update trailing stop for short position
                new_trailing_stop = current_price * (1 + self.trailing_stop)
                if new_trailing_stop < self.trailing_stop_price:
                    self.trailing_stop_price = new_trailing_stop
                    self.position.sl = self.trailing_stop_price
                
                # Exit if MFI extremely oversold or bullish divergence
                if current_mfi < 15 or divergence == 'bullish':
                    self.position.close()
                    self.impulse_pattern = None

# Run single backtest
bt = Backtest(data, ElliottImpulseMFI, cash=100000, commission=0.00045)

print("\n===== ELLIOTT WAVE IMPULSE + MFI - DEFAULT PARAMETERS =====")
print(f"Zigzag Percent: {ZIGZAG_PERCENT}%")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Overbought: {MFI_OVERBOUGHT}")
print(f"MFI Oversold: {MFI_OVERSOLD}")

stats_default = bt.run()
print(stats_default)

# Skip optimization for now to avoid issues
print("\nSkipping optimization for stability...")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ELLIOTT WAVE IMPULSE + MFI ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(ElliottImpulseMFI, 'ElliottImpulseMFI')
    
    if results is not None:
        print("\nTesting complete! Results saved in: ./results/ElliottImpulseMFI.csv")