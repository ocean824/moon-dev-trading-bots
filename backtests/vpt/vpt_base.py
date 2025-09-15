"""
Moon Dev's Volume Price Trend (VPT) Base Strategy
==================================================
Classic VPT indicator strategy for trend following with volume confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's VPT Base Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - FIXED, NO OPTIMIZATION
VPT_MA_PERIOD = 14  # Moving average for VPT smoothing
TREND_MA_PERIOD = 50  # MA period for overall trend determination
VPT_SLOPE_LOOKBACK = 5  # Periods to calculate VPT slope
DIVERGENCE_LOOKBACK = 20  # Periods to check for divergences
STOP_LOSS_PERCENT = 2.5  # Stop loss percentage
TAKE_PROFIT_PERCENT = 4.0  # Take profit percentage
MIN_VOLUME_FACTOR = 0.8  # Minimum volume as factor of average

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class VPTBase(Strategy):
    """
    Volume Price Trend Base Strategy - Simplified
    - Calculate VPT indicator combining price and volume
    - Use VPT direction/slope for trend identification
    - Apply moving average to smooth VPT signal
    - Detect divergences between price and VPT
    - Enter trades based on VPT trend and confirmation
    """
    
    # VPT parameters
    vpt_ma_period = VPT_MA_PERIOD
    trend_ma_period = TREND_MA_PERIOD
    vpt_slope_lookback = VPT_SLOPE_LOOKBACK
    divergence_lookback = DIVERGENCE_LOOKBACK
    
    # Risk management
    stop_loss = STOP_LOSS_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    min_volume_factor = MIN_VOLUME_FACTOR
    
    def init(self):
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)
        
        # Calculate VPT manually
        # VPT = VPT_prev + Volume * ((Close - Close_prev) / Close_prev)
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
        
        # Calculate price trend MA
        price_ma = ta.sma(close, length=self.trend_ma_period)
        price_ma_full = np.full(len(close), np.nan)
        price_ma_full[-len(price_ma):] = price_ma.values
        self.price_ma = self.I(lambda: price_ma_full, name='Price_MA')
        
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
    
    def detect_divergence(self):
        """Detect divergences between price and VPT"""
        if len(self.data) < self.divergence_lookback + 1:
            return None
        
        # Get recent price and VPT data
        recent_prices = self.data.Close[-self.divergence_lookback:]
        recent_vpt = self.vpt_ma[-self.divergence_lookback:]
        
        if any(np.isnan(recent_vpt)):
            return None
        
        # Find recent highs and lows
        price_high_idx = np.argmax(recent_prices)
        price_low_idx = np.argmin(recent_prices)
        vpt_high_idx = np.argmax(recent_vpt)
        vpt_low_idx = np.argmin(recent_vpt)
        
        # Check for bearish divergence (price makes new high, VPT doesn't)
        if price_high_idx > len(recent_prices) * 0.6:  # Recent high
            if vpt_high_idx < len(recent_vpt) * 0.4:  # VPT high was earlier
                if recent_prices[price_high_idx] > recent_prices[vpt_high_idx]:
                    if recent_vpt[price_high_idx] < recent_vpt[vpt_high_idx]:
                        return 'bearish'
        
        # Check for bullish divergence (price makes new low, VPT doesn't)
        if price_low_idx > len(recent_prices) * 0.6:  # Recent low
            if vpt_low_idx < len(recent_vpt) * 0.4:  # VPT low was earlier
                if recent_prices[price_low_idx] < recent_prices[vpt_low_idx]:
                    if recent_vpt[price_low_idx] > recent_vpt[vpt_low_idx]:
                        return 'bullish'
        
        return None
    
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.vpt_ma[-1]) or np.isnan(self.price_ma[-1]) or np.isnan(self.volume_ma[-1]):
            return
        
        # Skip if we need more data
        if len(self.data) < max(self.vpt_ma_period, self.trend_ma_period) * 2:
            return
        
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        current_vpt = self.vpt[-1]
        current_vpt_ma = self.vpt_ma[-1]
        current_price_ma = self.price_ma[-1]
        current_volume_ma = self.volume_ma[-1]
        
        # Calculate VPT slope
        vpt_slope = self.calculate_vpt_slope()
        
        # Detect divergences
        divergence = self.detect_divergence()
        
        # Determine overall trend
        price_trend_up = current_price > current_price_ma
        vpt_trend_up = vpt_slope > 0.001  # Small positive threshold
        vpt_trend_down = vpt_slope < -0.001  # Small negative threshold
        
        # Volume filter - require decent volume
        volume_sufficient = current_volume > current_volume_ma * self.min_volume_factor
        
        if not self.position:
            # LONG ENTRY CONDITIONS
            if vpt_trend_up and volume_sufficient:
                # Primary condition: VPT is rising with good volume
                if price_trend_up:
                    # Additional confirmation: price above MA
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)
                    self.buy(sl=sl_price, tp=tp_price)
                    self.entry_price = current_price
                    self.in_position = True
                    return
                
                # Alternative: Bullish divergence detected
                if divergence == 'bullish':
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)
                    self.buy(sl=sl_price, tp=tp_price)
                    self.entry_price = current_price
                    self.in_position = True
                    return
            
            # SHORT ENTRY CONDITIONS
            if vpt_trend_down and volume_sufficient:
                # Primary condition: VPT is falling with good volume
                if not price_trend_up:
                    # Additional confirmation: price below MA
                    sl_price = current_price * (1 + self.stop_loss)
                    tp_price = current_price * (1 - self.take_profit)
                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_price = current_price
                    self.in_position = True
                    return
                
                # Alternative: Bearish divergence detected
                if divergence == 'bearish':
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
bt = Backtest(data, VPTBase, cash=100000, commission=0.00045)

print("\n🌙 ===== VPT BASE - FIXED PARAMETERS ===== 🌙")
print(f"VPT MA Period: {VPT_MA_PERIOD}")
print(f"Trend MA Period: {TREND_MA_PERIOD}")
print(f"VPT Slope Lookback: {VPT_SLOPE_LOOKBACK}")
print(f"Divergence Lookback: {DIVERGENCE_LOOKBACK}")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Min Volume Factor: {MIN_VOLUME_FACTOR}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VPT BASE ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(VPTBase, 'VPTBase')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/VPTBase.csv")