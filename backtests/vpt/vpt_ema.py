"""
Moon Dev's Volume Price Trend (VPT) + EMA Crossover Strategy
=============================================================
VPT indicator combined with EMA crossovers for trend confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's VPT + EMA Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - FIXED, NO OPTIMIZATION
VPT_MA_PERIOD = 14  # Moving average for VPT smoothing
EMA_FAST = 12  # Fast EMA period
EMA_SLOW = 26  # Slow EMA period
EMA_SIGNAL = 9  # Signal line EMA period
VPT_SLOPE_LOOKBACK = 5  # Periods to calculate VPT slope
CROSSOVER_THRESHOLD = 0.001  # Minimum difference for valid crossover
STOP_LOSS_PERCENT = 2.5  # Stop loss percentage
TAKE_PROFIT_PERCENT = 4.0  # Take profit percentage
MIN_VOLUME_FACTOR = 0.8  # Minimum volume as factor of average

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class VPTEMA(Strategy):
    """
    VPT + EMA Crossover Strategy
    - Use VPT for volume-price trend analysis
    - EMA crossovers for trend confirmation
    - Triple confirmation: VPT trend, EMA crossover, price above/below EMAs
    - Enter on aligned signals with volume confirmation
    """
    
    # VPT parameters
    vpt_ma_period = VPT_MA_PERIOD
    vpt_slope_lookback = VPT_SLOPE_LOOKBACK
    
    # EMA parameters
    ema_fast = EMA_FAST
    ema_slow = EMA_SLOW
    ema_signal = EMA_SIGNAL
    crossover_threshold = CROSSOVER_THRESHOLD
    
    # Risk management
    stop_loss = STOP_LOSS_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    min_volume_factor = MIN_VOLUME_FACTOR
    
    def init(self):
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)
        
        # Calculate VPT manually
        price_change_pct = close.pct_change()
        vpt_raw = (volume * price_change_pct).cumsum()
        vpt_raw = vpt_raw.fillna(0)
        
        # Store raw VPT
        self.vpt = self.I(lambda: vpt_raw.values, name='VPT')
        
        # Calculate VPT moving average for smoothing
        vpt_ma = ta.sma(vpt_raw, length=self.vpt_ma_period)
        vpt_ma_full = np.full(len(close), np.nan)
        vpt_ma_full[-len(vpt_ma):] = vpt_ma.values
        self.vpt_ma = self.I(lambda: vpt_ma_full, name='VPT_MA')
        
        # Calculate EMAs for price
        ema_fast = ta.ema(close, length=self.ema_fast)
        ema_fast_full = np.full(len(close), np.nan)
        ema_fast_full[-len(ema_fast):] = ema_fast.values
        self.ema_fast = self.I(lambda: ema_fast_full, name='EMA_Fast')
        
        ema_slow = ta.ema(close, length=self.ema_slow)
        ema_slow_full = np.full(len(close), np.nan)
        ema_slow_full[-len(ema_slow):] = ema_slow.values
        self.ema_slow = self.I(lambda: ema_slow_full, name='EMA_Slow')
        
        # Calculate MACD-like signal from EMAs
        ema_diff = ema_fast - ema_slow
        ema_signal = ta.ema(ema_diff, length=self.ema_signal)
        ema_signal_full = np.full(len(close), np.nan)
        ema_signal_full[-len(ema_signal):] = ema_signal.values
        self.ema_signal = self.I(lambda: ema_signal_full, name='EMA_Signal')
        
        # Calculate EMAs for VPT as well
        vpt_ema_fast = ta.ema(vpt_raw, length=self.ema_fast)
        vpt_ema_fast_full = np.full(len(close), np.nan)
        vpt_ema_fast_full[-len(vpt_ema_fast):] = vpt_ema_fast.values
        self.vpt_ema_fast = self.I(lambda: vpt_ema_fast_full, name='VPT_EMA_Fast')
        
        vpt_ema_slow = ta.ema(vpt_raw, length=self.ema_slow)
        vpt_ema_slow_full = np.full(len(close), np.nan)
        vpt_ema_slow_full[-len(vpt_ema_slow):] = vpt_ema_slow.values
        self.vpt_ema_slow = self.I(lambda: vpt_ema_slow_full, name='VPT_EMA_Slow')
        
        # Calculate average volume for filtering
        volume_ma = ta.sma(volume, length=20)
        volume_ma_full = np.full(len(volume), np.nan)
        volume_ma_full[-len(volume_ma):] = volume_ma.values
        self.volume_ma = self.I(lambda: volume_ma_full, name='Volume_MA')
        
        # Track entry info
        self.entry_price = None
        self.in_position = False
    
    def calculate_vpt_slope(self):
        """Calculate the slope of VPT over recent periods"""
        if len(self.data) < self.vpt_slope_lookback + 1:
            return 0
        
        recent_vpt = self.vpt_ma[-self.vpt_slope_lookback:]
        if any(np.isnan(recent_vpt)):
            return 0
        
        # Calculate linear regression slope
        x = np.arange(len(recent_vpt))
        slope = np.polyfit(x, recent_vpt, 1)[0]
        
        # Normalize slope by average VPT value to make it relative
        avg_vpt = np.mean(np.abs(recent_vpt))
        if avg_vpt > 0:
            return slope / avg_vpt
        return 0
    
    def check_ema_crossover(self):
        """Check for EMA crossover signals"""
        if len(self.data) < 2:
            return None
        
        # Current and previous EMA values
        current_fast = self.ema_fast[-1]
        current_slow = self.ema_slow[-1]
        prev_fast = self.ema_fast[-2]
        prev_slow = self.ema_slow[-2]
        
        if np.isnan(current_fast) or np.isnan(current_slow) or np.isnan(prev_fast) or np.isnan(prev_slow):
            return None
        
        # Check for bullish crossover
        if prev_fast <= prev_slow and current_fast > current_slow:
            diff = (current_fast - current_slow) / current_slow
            if abs(diff) > self.crossover_threshold:
                return 'bullish'
        
        # Check for bearish crossover
        if prev_fast >= prev_slow and current_fast < current_slow:
            diff = (current_slow - current_fast) / current_fast
            if abs(diff) > self.crossover_threshold:
                return 'bearish'
        
        return None
    
    def check_vpt_ema_crossover(self):
        """Check for VPT EMA crossover signals"""
        if len(self.data) < 2:
            return None
        
        # Current and previous VPT EMA values
        current_fast = self.vpt_ema_fast[-1]
        current_slow = self.vpt_ema_slow[-1]
        prev_fast = self.vpt_ema_fast[-2]
        prev_slow = self.vpt_ema_slow[-2]
        
        if np.isnan(current_fast) or np.isnan(current_slow) or np.isnan(prev_fast) or np.isnan(prev_slow):
            return None
        
        # Check for bullish crossover
        if prev_fast <= prev_slow and current_fast > current_slow:
            return 'bullish'
        
        # Check for bearish crossover
        if prev_fast >= prev_slow and current_fast < current_slow:
            return 'bearish'
        
        return None
    
    def next(self):
        # Skip if indicators not ready
        if (np.isnan(self.vpt_ma[-1]) or np.isnan(self.ema_fast[-1]) or 
            np.isnan(self.ema_slow[-1]) or np.isnan(self.volume_ma[-1])):
            return
        
        # Skip if we need more data
        if len(self.data) < self.ema_slow * 2:
            return
        
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        current_vpt_ma = self.vpt_ma[-1]
        current_ema_fast = self.ema_fast[-1]
        current_ema_slow = self.ema_slow[-1]
        current_volume_ma = self.volume_ma[-1]
        
        # Calculate VPT slope
        vpt_slope = self.calculate_vpt_slope()
        
        # Determine trend conditions
        vpt_trend_up = vpt_slope > 0.001
        vpt_trend_down = vpt_slope < -0.001
        
        # Check EMA crossovers
        price_ema_crossover = self.check_ema_crossover()
        vpt_ema_crossover = self.check_vpt_ema_crossover()
        
        # Price position relative to EMAs
        price_above_both = current_price > current_ema_fast and current_price > current_ema_slow
        price_below_both = current_price < current_ema_fast and current_price < current_ema_slow
        ema_bullish = current_ema_fast > current_ema_slow
        ema_bearish = current_ema_fast < current_ema_slow
        
        # Volume filter
        volume_sufficient = current_volume > current_volume_ma * self.min_volume_factor
        
        if not self.position:
            # LONG ENTRY CONDITIONS
            
            # Primary: Price EMA bullish crossover with VPT confirmation
            if price_ema_crossover == 'bullish' and vpt_trend_up and volume_sufficient:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Secondary: VPT EMA bullish crossover with price confirmation
            if vpt_ema_crossover == 'bullish' and price_above_both and volume_sufficient:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Tertiary: All EMAs aligned bullish with VPT rising
            if ema_bullish and price_above_both and vpt_trend_up and volume_sufficient:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # SHORT ENTRY CONDITIONS
            
            # Primary: Price EMA bearish crossover with VPT confirmation
            if price_ema_crossover == 'bearish' and vpt_trend_down and volume_sufficient:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Secondary: VPT EMA bearish crossover with price confirmation
            if vpt_ema_crossover == 'bearish' and price_below_both and volume_sufficient:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Tertiary: All EMAs aligned bearish with VPT falling
            if ema_bearish and price_below_both and vpt_trend_down and volume_sufficient:
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
bt = Backtest(data, VPTEMA, cash=100000, commission=0.00045)

print("\n🌙 ===== VPT + EMA CROSSOVER - FIXED PARAMETERS ===== 🌙")
print(f"VPT MA Period: {VPT_MA_PERIOD}")
print(f"EMA Fast: {EMA_FAST}")
print(f"EMA Slow: {EMA_SLOW}")
print(f"EMA Signal: {EMA_SIGNAL}")
print(f"VPT Slope Lookback: {VPT_SLOPE_LOOKBACK}")
print(f"Crossover Threshold: {CROSSOVER_THRESHOLD}")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Min Volume Factor: {MIN_VOLUME_FACTOR}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VPT + EMA CROSSOVER ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(VPTEMA, 'VPTEMA')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/VPTEMA.csv")