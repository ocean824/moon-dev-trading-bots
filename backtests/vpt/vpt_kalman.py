"""
Moon Dev's Volume Price Trend (VPT) + Kalman Filter Strategy
=============================================================
VPT indicator combined with Kalman filter for noise reduction
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's VPT + Kalman Filter Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - FIXED, NO OPTIMIZATION
VPT_MA_PERIOD = 14  # Moving average for VPT smoothing
KALMAN_PROCESS_VAR = 1e-5  # Kalman filter process variance
KALMAN_MEASURE_VAR = 1e-1  # Kalman filter measurement variance
VPT_SLOPE_LOOKBACK = 5  # Periods to calculate VPT slope
DEVIATION_THRESHOLD = 0.015  # Minimum deviation from Kalman fair value (1.5%)
STOP_LOSS_PERCENT = 2.5  # Stop loss percentage
TAKE_PROFIT_PERCENT = 4.0  # Take profit percentage
MIN_VOLUME_FACTOR = 0.8  # Minimum volume as factor of average

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class KalmanFilter:
    """
    Simple Kalman Filter for price smoothing
    Moon Dev's noise reduction weapon! 🎯
    """
    def __init__(self, process_variance=1e-5, measurement_variance=1e-1):
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance
        self.posteri_estimate = None
        self.posteri_error_estimate = None
        
    def filter(self, measurement):
        if self.posteri_estimate is None:
            self.posteri_estimate = measurement
            self.posteri_error_estimate = 1.0
            return measurement
            
        # Prediction step
        priori_estimate = self.posteri_estimate
        priori_error_estimate = self.posteri_error_estimate + self.process_variance
        
        # Update step
        blending_factor = priori_error_estimate / (priori_error_estimate + self.measurement_variance)
        self.posteri_estimate = priori_estimate + blending_factor * (measurement - priori_estimate)
        self.posteri_error_estimate = (1 - blending_factor) * priori_error_estimate
        
        return self.posteri_estimate

def apply_kalman_filter_price(prices, process_var=1e-5, measure_var=1e-1):
    """Apply Kalman filter to price series"""
    kf = KalmanFilter(process_var, measure_var)
    filtered_prices = []
    
    for price in prices:
        filtered_price = kf.filter(price)
        filtered_prices.append(filtered_price)
    
    return np.array(filtered_prices)

def apply_kalman_filter_vpt(vpt_values, process_var=1e-4, measure_var=5e-1):
    """Apply Kalman filter to VPT values with different parameters"""
    kf = KalmanFilter(process_var, measure_var)
    filtered_vpt = []
    
    for vpt in vpt_values:
        filtered_vpt_val = kf.filter(vpt)
        filtered_vpt.append(filtered_vpt_val)
    
    return np.array(filtered_vpt)

class VPTKalman(Strategy):
    """
    VPT + Kalman Filter Strategy
    - Use VPT for volume-price trend analysis
    - Apply Kalman filter to both price and VPT for noise reduction
    - Compare actual price to Kalman fair value for entry signals
    - VPT Kalman filter helps confirm volume-price trends
    """
    
    # VPT parameters
    vpt_ma_period = VPT_MA_PERIOD
    vpt_slope_lookback = VPT_SLOPE_LOOKBACK
    
    # Kalman parameters
    kalman_process_var = KALMAN_PROCESS_VAR
    kalman_measure_var = KALMAN_MEASURE_VAR
    deviation_threshold = DEVIATION_THRESHOLD
    
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
        
        # Apply Kalman filter to price for fair value
        self.kalman_price = self.I(lambda: apply_kalman_filter_price(
            self.data.Close, self.kalman_process_var, self.kalman_measure_var), name='Kalman_Price')
        
        # Apply Kalman filter to VPT for trend smoothing
        self.kalman_vpt = self.I(lambda: apply_kalman_filter_vpt(vpt_raw.values), name='Kalman_VPT')
        
        # Calculate VPT moving average for comparison
        vpt_ma = ta.sma(vpt_raw, length=self.vpt_ma_period)
        vpt_ma_full = np.full(len(close), np.nan)
        vpt_ma_full[-len(vpt_ma):] = vpt_ma.values
        self.vpt_ma = self.I(lambda: vpt_ma_full, name='VPT_MA')
        
        # Calculate average volume for filtering
        volume_ma = ta.sma(volume, length=20)
        volume_ma_full = np.full(len(volume), np.nan)
        volume_ma_full[-len(volume_ma):] = volume_ma.values
        self.volume_ma = self.I(lambda: volume_ma_full, name='Volume_MA')
        
        # Track entry info
        self.entry_price = None
        self.in_position = False
    
    def calculate_kalman_vpt_slope(self):
        """Calculate the slope of Kalman-filtered VPT over recent periods"""
        if len(self.data) < self.vpt_slope_lookback + 1:
            return 0
        
        recent_kalman_vpt = self.kalman_vpt[-self.vpt_slope_lookback:]
        if any(np.isnan(recent_kalman_vpt)):
            return 0
        
        # Calculate linear regression slope
        x = np.arange(len(recent_kalman_vpt))
        slope = np.polyfit(x, recent_kalman_vpt, 1)[0]
        
        # Normalize slope by average VPT value to make it relative
        avg_vpt = np.mean(np.abs(recent_kalman_vpt))
        if avg_vpt > 0:
            return slope / avg_vpt
        return 0
    
    def calculate_price_deviation(self):
        """Calculate deviation from Kalman fair value"""
        current_price = self.data.Close[-1]
        kalman_fair = self.kalman_price[-1]
        
        if np.isnan(kalman_fair) or kalman_fair <= 0:
            return 0
        
        return (current_price - kalman_fair) / kalman_fair
    
    def next(self):
        # Skip if indicators not ready
        if (np.isnan(self.kalman_price[-1]) or np.isnan(self.kalman_vpt[-1]) or 
            np.isnan(self.volume_ma[-1])):
            return
        
        # Skip if we need more data
        if len(self.data) < 30:
            return
        
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        current_kalman_price = self.kalman_price[-1]
        current_kalman_vpt = self.kalman_vpt[-1]
        current_volume_ma = self.volume_ma[-1]
        
        # Calculate VPT slope from Kalman-filtered values
        kalman_vpt_slope = self.calculate_kalman_vpt_slope()
        
        # Calculate price deviation from fair value
        price_deviation = self.calculate_price_deviation()
        
        # Determine trend conditions
        kalman_vpt_trend_up = kalman_vpt_slope > 0.0005  # Smaller threshold for Kalman
        kalman_vpt_trend_down = kalman_vpt_slope < -0.0005
        
        # Price vs fair value conditions
        price_above_fair = price_deviation > self.deviation_threshold
        price_below_fair = price_deviation < -self.deviation_threshold
        
        # Volume filter
        volume_sufficient = current_volume > current_volume_ma * self.min_volume_factor
        
        if not self.position:
            # LONG ENTRY CONDITIONS
            
            # Primary: Price below fair value with VPT turning up (mean reversion)
            if price_below_fair and kalman_vpt_trend_up and volume_sufficient:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Secondary: VPT strongly rising with price near fair value
            if abs(price_deviation) < self.deviation_threshold/2 and kalman_vpt_trend_up and volume_sufficient:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Tertiary: Momentum continuation - price and VPT both rising
            if current_price > current_kalman_price and kalman_vpt_trend_up and volume_sufficient:
                # But only if not too extended
                if price_deviation < self.deviation_threshold * 2:
                    sl_price = current_price * (1 - self.stop_loss)
                    tp_price = current_price * (1 + self.take_profit)
                    self.buy(sl=sl_price, tp=tp_price)
                    self.entry_price = current_price
                    self.in_position = True
                    return
            
            # SHORT ENTRY CONDITIONS
            
            # Primary: Price above fair value with VPT turning down (mean reversion)
            if price_above_fair and kalman_vpt_trend_down and volume_sufficient:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Secondary: VPT strongly falling with price near fair value
            if abs(price_deviation) < self.deviation_threshold/2 and kalman_vpt_trend_down and volume_sufficient:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Tertiary: Momentum continuation - price and VPT both falling
            if current_price < current_kalman_price and kalman_vpt_trend_down and volume_sufficient:
                # But only if not too extended
                if price_deviation > -self.deviation_threshold * 2:
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
bt = Backtest(data, VPTKalman, cash=100000, commission=0.00045)

print("\n🌙 ===== VPT + KALMAN FILTER - FIXED PARAMETERS ===== 🌙")
print(f"VPT MA Period: {VPT_MA_PERIOD}")
print(f"Kalman Process Variance: {KALMAN_PROCESS_VAR}")
print(f"Kalman Measurement Variance: {KALMAN_MEASURE_VAR}")
print(f"VPT Slope Lookback: {VPT_SLOPE_LOOKBACK}")
print(f"Deviation Threshold: {DEVIATION_THRESHOLD * 100}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Min Volume Factor: {MIN_VOLUME_FACTOR}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VPT + KALMAN FILTER ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(VPTKalman, 'VPTKalman')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/VPTKalman.csv")