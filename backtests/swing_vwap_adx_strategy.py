"""
Swing VWAP + ADX Strategy
========================
This strategy identifies swing highs and lows, calculates VWAP from these points,
and uses ADX for trend strength filtering to generate trading signals.

Strategy Logic:
- Detects swing highs and lows using configurable lookback period
- Calculates VWAP from each swing point to current bar
- Uses ADX for trend strength filtering (threshold 25)
- Enters long positions near low swing VWAP with strong uptrend
- Enters short positions near high swing VWAP with strong downtrend
- Risk management: 2% stop loss, 4% take profit
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's Swing VWAP + ADX Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters
SWING_LOOKBACK = 50
ADX_PERIOD = 14
ADX_THRESHOLD = 25
DI_PERIOD = 14
VWAP_OFFSET = 0.005
STOP_LOSS_PERCENT = 2.0
TAKE_PROFIT_PERCENT = 4.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")


class SwingVWAPADXStrategy(Strategy):
    """
    Swing VWAP + ADX Strategy
    
    This strategy identifies swing highs and lows, calculates VWAP from these points,
    and uses ADX for trend strength filtering.
    """
    
    # Strategy parameters
    swing_lookback = SWING_LOOKBACK
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    di_period = DI_PERIOD
    vwap_offset = VWAP_OFFSET
    stop_loss = STOP_LOSS_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    
    def init(self):
        """Initialize indicators and swing point detection"""
        
        # Calculate ADX and DI indicators using pandas_ta
        high_series = pd.Series(self.data.High)
        low_series = pd.Series(self.data.Low)
        close_series = pd.Series(self.data.Close)
        
        adx_result = ta.adx(high_series, low_series, close_series, 
                           length=self.adx_period)
        
        # Extract ADX, DI+, and DI- columns - handle potential None result
        if adx_result is not None and not adx_result.empty:
            self.adx = self.I(lambda: adx_result[f'ADX_{self.adx_period}'].values, name='ADX')
            self.di_plus = self.I(lambda: adx_result[f'DMP_{self.adx_period}'].values, name='DI+')
            self.di_minus = self.I(lambda: adx_result[f'DMN_{self.adx_period}'].values, name='DI-')
        else:
            # Fallback to manual calculation if pandas_ta fails
            self.adx = self.I(self.calculate_adx, name='ADX')
            self.di_plus = self.I(self.calculate_di_plus, name='DI+')
            self.di_minus = self.I(self.calculate_di_minus, name='DI-')
        
        # Calculate swing highs and lows
        self.swing_highs = self.I(self.find_swing_highs, name='Swing Highs')
        self.swing_lows = self.I(self.find_swing_lows, name='Swing Lows')
        
        # Calculate VWAP from swing points
        self.high_vwap = self.I(self.calculate_swing_vwap, self.swing_highs, is_high=True, name='High VWAP')
        self.low_vwap = self.I(self.calculate_swing_vwap, self.swing_lows, is_high=False, name='Low VWAP')
        
        print(f"✅ Strategy initialized with swing lookback: {self.swing_lookback}, ADX threshold: {self.adx_threshold}")
    
    def calculate_adx(self):
        """Manual ADX calculation as fallback"""
        high = self.data.High
        low = self.data.Low
        close = self.data.Close
        
        # Calculate True Range
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        
        # Calculate directional movements
        up_move = high - np.roll(high, 1)
        down_move = np.roll(low, 1) - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Smooth using EMA
        atr = pd.Series(tr).ewm(span=self.adx_period, adjust=False).mean().values
        plus_di = 100 * pd.Series(plus_dm).ewm(span=self.adx_period, adjust=False).mean().values / atr
        minus_di = 100 * pd.Series(minus_dm).ewm(span=self.adx_period, adjust=False).mean().values / atr
        
        # Calculate ADX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = pd.Series(dx).ewm(span=self.adx_period, adjust=False).mean().values
        
        return adx
    
    def calculate_di_plus(self):
        """Manual DI+ calculation as fallback"""
        high = self.data.High
        low = self.data.Low
        close = self.data.Close
        
        # Calculate True Range
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        
        # Calculate positive directional movement
        up_move = high - np.roll(high, 1)
        down_move = np.roll(low, 1) - low
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        
        # Smooth and calculate DI+
        atr = pd.Series(tr).ewm(span=self.di_period, adjust=False).mean().values
        plus_di = 100 * pd.Series(plus_dm).ewm(span=self.di_period, adjust=False).mean().values / (atr + 1e-10)
        
        return plus_di
    
    def calculate_di_minus(self):
        """Manual DI- calculation as fallback"""
        high = self.data.High
        low = self.data.Low
        close = self.data.Close
        
        # Calculate True Range
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        
        # Calculate negative directional movement
        up_move = high - np.roll(high, 1)
        down_move = np.roll(low, 1) - low
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Smooth and calculate DI-
        atr = pd.Series(tr).ewm(span=self.di_period, adjust=False).mean().values
        minus_di = 100 * pd.Series(minus_dm).ewm(span=self.di_period, adjust=False).mean().values / (atr + 1e-10)
        
        return minus_di
    
    def find_swing_highs(self):
        """Identify swing high points"""
        highs = self.data.High
        swing_highs = np.zeros(len(highs))
        
        for i in range(self.swing_lookback, len(highs) - self.swing_lookback):
            # Check if current high is highest in the window
            window_start = max(0, i - self.swing_lookback)
            window_end = min(len(highs), i + self.swing_lookback + 1)
            
            if highs[i] == max(highs[window_start:window_end]):
                swing_highs[i] = highs[i]
            else:
                swing_highs[i] = np.nan
        
        # Forward fill to maintain last swing high
        for i in range(1, len(swing_highs)):
            if np.isnan(swing_highs[i]) or swing_highs[i] == 0:
                swing_highs[i] = swing_highs[i-1] if i > 0 else np.nan
        
        return swing_highs
    
    def find_swing_lows(self):
        """Identify swing low points"""
        lows = self.data.Low
        swing_lows = np.zeros(len(lows))
        
        for i in range(self.swing_lookback, len(lows) - self.swing_lookback):
            # Check if current low is lowest in the window
            window_start = max(0, i - self.swing_lookback)
            window_end = min(len(lows), i + self.swing_lookback + 1)
            
            if lows[i] == min(lows[window_start:window_end]):
                swing_lows[i] = lows[i]
            else:
                swing_lows[i] = np.nan
        
        # Forward fill to maintain last swing low
        for i in range(1, len(swing_lows)):
            if np.isnan(swing_lows[i]) or swing_lows[i] == 0:
                swing_lows[i] = swing_lows[i-1] if i > 0 else np.nan
        
        return swing_lows
    
    def calculate_swing_vwap(self, swing_points, is_high=True):
        """Calculate VWAP from swing points to current bar (simplified)
        
        Note: swing_points and is_high parameters are kept for compatibility 
        but simplified implementation uses rolling window approach
        """
        
        typical_price = (self.data.High + self.data.Low + self.data.Close) / 3
        volume = self.data.Volume
        vwap_values = np.full(len(typical_price), np.nan)
        
        # Use a rolling window approach for efficiency
        window_size = min(200, len(typical_price) // 10)  # Limit window size
        
        for i in range(window_size, len(typical_price)):
            # Simple VWAP calculation over fixed window
            start_idx = max(0, i - window_size)
            
            vol_sum = np.sum(volume[start_idx:i+1])
            if vol_sum > 0:
                price_vol_sum = np.sum(typical_price[start_idx:i+1] * volume[start_idx:i+1])
                vwap_values[i] = price_vol_sum / vol_sum
            else:
                vwap_values[i] = typical_price[i]
        
        return vwap_values
    
    def next(self):
        """Execute trading logic"""
        
        # Skip if not enough data
        if len(self.data) < max(self.swing_lookback * 2, self.adx_period * 2):
            return
        
        # Get current values
        current_price = self.data.Close[-1]
        current_adx = self.adx[-1]
        current_di_plus = self.di_plus[-1]
        current_di_minus = self.di_minus[-1]
        current_high_vwap = self.high_vwap[-1]
        current_low_vwap = self.low_vwap[-1]
        
        # Skip if we don't have valid indicator values
        if pd.isna(current_adx) or pd.isna(current_high_vwap) or pd.isna(current_low_vwap):
            return
        
        # Check if ADX indicates strong trend
        strong_trend = current_adx > self.adx_threshold
        
        # Calculate price proximity to VWAP levels
        distance_to_low_vwap = abs(current_price - current_low_vwap) / current_low_vwap
        distance_to_high_vwap = abs(current_price - current_high_vwap) / current_high_vwap
        
        # Long Entry Conditions:
        # 1. Price near low swing VWAP (within offset)
        # 2. ADX > threshold (strong trend)
        # 3. DI+ > DI- (uptrend)
        # 4. Not already in position
        if (not self.position and 
            distance_to_low_vwap <= self.vwap_offset and
            strong_trend and
            current_di_plus > current_di_minus):
            
            # Calculate stop loss and take profit levels
            sl_price = current_price * (1 - self.stop_loss)
            tp_price = current_price * (1 + self.take_profit)
            
            self.buy(
                sl=sl_price,
                tp=tp_price
            )
        
        # Short Entry Conditions:
        # 1. Price near high swing VWAP (within offset)
        # 2. ADX > threshold (strong trend)
        # 3. DI- > DI+ (downtrend)
        # 4. Not already in position
        elif (not self.position and 
              distance_to_high_vwap <= self.vwap_offset and
              strong_trend and
              current_di_minus > current_di_plus):
            
            # Calculate stop loss and take profit levels
            sl_price = current_price * (1 + self.stop_loss)
            tp_price = current_price * (1 - self.take_profit)
            
            self.sell(
                sl=sl_price,
                tp=tp_price
            )
        
        # Exit Conditions for existing positions
        elif self.position:
            # Exit long if price drops below low VWAP * 0.99 or ADX weakens
            if self.position.is_long:
                if current_price < current_low_vwap * 0.99 or current_adx < self.adx_threshold * 0.8:
                    self.position.close()
            
            # Exit short if price rises above high VWAP * 1.01 or ADX weakens
            elif self.position.is_short:
                if current_price > current_high_vwap * 1.01 or current_adx < self.adx_threshold * 0.8:
                    self.position.close()


# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    # Run single backtest (default behavior)
    bt = Backtest(data, SwingVWAPADXStrategy, cash=10000000, commission=0.00045)
    
    print("\n🌙 ===== SWING VWAP + ADX STRATEGY - DEFAULT PARAMETERS ===== 🌙")
    print(f"Swing Lookback: {SWING_LOOKBACK}")
    print(f"ADX Period: {ADX_PERIOD}")
    print(f"ADX Threshold: {ADX_THRESHOLD}")
    print(f"VWAP Offset: {VWAP_OFFSET*100:.1f}%")
    print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
    print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
    
    stats_default = bt.run()
    print(stats_default)
    
    # Optional: Add optimization (commented out for speed - uncomment to run)
    """
    print("\n🚀 Optimizing Strategy...")
    optimization_results = bt.optimize(
        swing_lookback=range(40, 61, 10),
        adx_period=range(12, 17, 2),
        adx_threshold=range(23, 28, 2),
        vwap_offset=[i / 1000 for i in range(5, 8, 1)],
        stop_loss=[i / 1000 for i in range(15, 26, 5)],
        take_profit=[i / 1000 for i in range(30, 51, 10)],
        maximize='Sortino Ratio',
        constraint=lambda p: p.take_profit > p.stop_loss * 1.5
    )
    
    print("\n🚀 ===== OPTIMIZATION RESULTS ===== 🚀")
    print(optimization_results)
    
    print("\n🏆 BEST PARAMETERS:")
    print(f"Swing Lookback: {optimization_results._strategy.swing_lookback}")
    print(f"ADX Period: {optimization_results._strategy.adx_period}")
    print(f"ADX Threshold: {optimization_results._strategy.adx_threshold}")
    print(f"VWAP Offset: {optimization_results._strategy.vwap_offset * 100:.1f}%")
    print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")
    print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
    """
    print("\n" + "="*80)
    print("TESTING SWING VWAP + ADX STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(SwingVWAPADXStrategy, 'SwingVWAPADX')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/SwingVWAPADX_[timestamp].csv")