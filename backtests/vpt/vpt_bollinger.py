"""
Moon Dev's Volume Price Trend (VPT) + Bollinger Bands Strategy
===============================================================
VPT indicator combined with Bollinger Bands for volatility confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's VPT + Bollinger Bands Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - FIXED, NO OPTIMIZATION
VPT_MA_PERIOD = 14  # Moving average for VPT smoothing
BB_PERIOD = 20  # Bollinger Bands period
BB_STD = 2.0  # Bollinger Bands standard deviation
VPT_SLOPE_LOOKBACK = 5  # Periods to calculate VPT slope
BB_SQUEEZE_THRESHOLD = 0.4  # Threshold for BB squeeze (as % of price)
STOP_LOSS_PERCENT = 2.5  # Stop loss percentage
TAKE_PROFIT_PERCENT = 4.0  # Take profit percentage
MIN_VOLUME_FACTOR = 0.8  # Minimum volume as factor of average

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class VPTBollinger(Strategy):
    """
    VPT + Bollinger Bands Strategy
    - Use VPT for volume-price trend analysis
    - Bollinger Bands for volatility and breakout signals
    - Look for BB squeezes followed by VPT confirmation
    - Trade breakouts with volume confirmation
    """
    
    # VPT parameters
    vpt_ma_period = VPT_MA_PERIOD
    vpt_slope_lookback = VPT_SLOPE_LOOKBACK
    
    # Bollinger Bands parameters
    bb_period = BB_PERIOD
    bb_std = BB_STD
    bb_squeeze_threshold = BB_SQUEEZE_THRESHOLD
    
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
        
        # Calculate Bollinger Bands
        bb_result = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        
        # Extract BB components
        bb_upper = bb_result[f'BBU_{self.bb_period}_{self.bb_std}']
        bb_middle = bb_result[f'BBM_{self.bb_period}_{self.bb_std}']
        bb_lower = bb_result[f'BBL_{self.bb_period}_{self.bb_std}']
        
        bb_upper_full = np.full(len(close), np.nan)
        bb_upper_full[-len(bb_upper):] = bb_upper.values
        self.bb_upper = self.I(lambda: bb_upper_full, name='BB_Upper')
        
        bb_middle_full = np.full(len(close), np.nan)
        bb_middle_full[-len(bb_middle):] = bb_middle.values
        self.bb_middle = self.I(lambda: bb_middle_full, name='BB_Middle')
        
        bb_lower_full = np.full(len(close), np.nan)
        bb_lower_full[-len(bb_lower):] = bb_lower.values
        self.bb_lower = self.I(lambda: bb_lower_full, name='BB_Lower')
        
        # Calculate BB width for squeeze detection
        bb_width = (bb_upper - bb_lower) / bb_middle * 100
        bb_width_full = np.full(len(close), np.nan)
        bb_width_full[-len(bb_width):] = bb_width.values
        self.bb_width = self.I(lambda: bb_width_full, name='BB_Width')
        
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
    
    def is_bb_squeeze(self):
        """Check if Bollinger Bands are in a squeeze"""
        if np.isnan(self.bb_width[-1]):
            return False
        
        # Look at recent BB width history
        if len(self.data) < 10:
            return False
        
        recent_width = self.bb_width[-10:]
        if any(np.isnan(recent_width)):
            return False
        
        # Current width is low compared to recent average
        current_width = self.bb_width[-1]
        avg_width = np.mean(recent_width)
        
        return current_width < avg_width * 0.7  # Squeeze when width is 30% below average
    
    def next(self):
        # Skip if indicators not ready
        if (np.isnan(self.vpt_ma[-1]) or np.isnan(self.bb_upper[-1]) or 
            np.isnan(self.bb_lower[-1]) or np.isnan(self.volume_ma[-1])):
            return
        
        # Skip if we need more data
        if len(self.data) < self.bb_period * 2:
            return
        
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        current_vpt_ma = self.vpt_ma[-1]
        current_bb_upper = self.bb_upper[-1]
        current_bb_middle = self.bb_middle[-1]
        current_bb_lower = self.bb_lower[-1]
        current_bb_width = self.bb_width[-1]
        current_volume_ma = self.volume_ma[-1]
        
        # Previous values for crossover detection
        prev_price = self.data.Close[-2] if len(self.data) > 1 else current_price
        prev_bb_upper = self.bb_upper[-2] if len(self.data) > 1 else current_bb_upper
        prev_bb_lower = self.bb_lower[-2] if len(self.data) > 1 else current_bb_lower
        
        # Calculate VPT slope
        vpt_slope = self.calculate_vpt_slope()
        
        # Determine trend conditions
        vpt_trend_up = vpt_slope > 0.001
        vpt_trend_down = vpt_slope < -0.001
        
        # BB position
        price_near_upper = (current_bb_upper - current_price) / current_price < 0.005  # Within 0.5% of upper band
        price_near_lower = (current_price - current_bb_lower) / current_price < 0.005  # Within 0.5% of lower band
        price_above_middle = current_price > current_bb_middle
        price_below_middle = current_price < current_bb_middle
        
        # BB breakout signals
        upper_breakout = current_price > current_bb_upper and prev_price <= prev_bb_upper
        lower_breakout = current_price < current_bb_lower and prev_price >= prev_bb_lower
        
        # Check for BB squeeze
        in_squeeze = self.is_bb_squeeze()
        
        # Volume filter
        volume_sufficient = current_volume > current_volume_ma * self.min_volume_factor
        
        if not self.position:
            # LONG ENTRY CONDITIONS
            
            # Primary: Upper band breakout with VPT confirmation
            if upper_breakout and vpt_trend_up and volume_sufficient:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Secondary: Bounce from lower band with VPT turning up
            if price_near_lower and vpt_trend_up and volume_sufficient:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Tertiary: Squeeze breakout to upside
            if in_squeeze and price_above_middle and vpt_trend_up:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # SHORT ENTRY CONDITIONS
            
            # Primary: Lower band breakout with VPT confirmation
            if lower_breakout and vpt_trend_down and volume_sufficient:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Secondary: Rejection from upper band with VPT turning down
            if price_near_upper and vpt_trend_down and volume_sufficient:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Tertiary: Squeeze breakout to downside
            if in_squeeze and price_below_middle and vpt_trend_down:
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
bt = Backtest(data, VPTBollinger, cash=100000, commission=0.00045)

print("\n🌙 ===== VPT + BOLLINGER BANDS - FIXED PARAMETERS ===== 🌙")
print(f"VPT MA Period: {VPT_MA_PERIOD}")
print(f"BB Period: {BB_PERIOD}")
print(f"BB Std Dev: {BB_STD}")
print(f"VPT Slope Lookback: {VPT_SLOPE_LOOKBACK}")
print(f"BB Squeeze Threshold: {BB_SQUEEZE_THRESHOLD}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Min Volume Factor: {MIN_VOLUME_FACTOR}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VPT + BOLLINGER BANDS ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(VPTBollinger, 'VPTBollinger')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/VPTBollinger.csv")