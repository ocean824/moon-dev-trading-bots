"""
Moon Dev's Volume Price Trend (VPT) + ADX Strategy
===================================================
VPT indicator combined with ADX for trend strength filtering
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's VPT + ADX Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - FIXED, NO OPTIMIZATION
VPT_MA_PERIOD = 14  # Moving average for VPT smoothing
ADX_PERIOD = 14  # ADX period for trend strength
ADX_THRESHOLD = 20  # Minimum ADX for trend trading
DI_DIFF_THRESHOLD = 5  # Minimum difference between +DI and -DI
VPT_SLOPE_LOOKBACK = 5  # Periods to calculate VPT slope
STOP_LOSS_PERCENT = 2.5  # Stop loss percentage
TAKE_PROFIT_PERCENT = 4.0  # Take profit percentage
MIN_VOLUME_FACTOR = 0.8  # Minimum volume as factor of average

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class VPTADX(Strategy):
    """
    VPT + ADX Strategy
    - Use VPT for volume-price trend analysis
    - ADX for confirming trend strength
    - +DI/-DI for directional confirmation
    - Enter only in strong trends with volume confirmation
    """
    
    # VPT parameters
    vpt_ma_period = VPT_MA_PERIOD
    vpt_slope_lookback = VPT_SLOPE_LOOKBACK
    
    # ADX parameters
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    di_diff_threshold = DI_DIFF_THRESHOLD
    
    # Risk management
    stop_loss = STOP_LOSS_PERCENT / 100
    take_profit = TAKE_PROFIT_PERCENT / 100
    min_volume_factor = MIN_VOLUME_FACTOR
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
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
        
        # Calculate ADX, +DI, -DI
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        
        # Extract ADX
        adx = adx_result[f'ADX_{self.adx_period}']
        adx_full = np.full(len(close), np.nan)
        adx_full[-len(adx):] = adx.values
        self.adx = self.I(lambda: adx_full, name='ADX')
        
        # Extract +DI
        plus_di = adx_result[f'DMP_{self.adx_period}']
        plus_di_full = np.full(len(close), np.nan)
        plus_di_full[-len(plus_di):] = plus_di.values
        self.plus_di = self.I(lambda: plus_di_full, name='+DI')
        
        # Extract -DI
        minus_di = adx_result[f'DMN_{self.adx_period}']
        minus_di_full = np.full(len(close), np.nan)
        minus_di_full[-len(minus_di):] = minus_di.values
        self.minus_di = self.I(lambda: minus_di_full, name='-DI')
        
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
    
    def next(self):
        # Skip if indicators not ready
        if (np.isnan(self.vpt_ma[-1]) or np.isnan(self.adx[-1]) or 
            np.isnan(self.plus_di[-1]) or np.isnan(self.minus_di[-1]) or
            np.isnan(self.volume_ma[-1])):
            return
        
        # Skip if we need more data
        if len(self.data) < self.adx_period * 3:
            return
        
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        current_vpt_ma = self.vpt_ma[-1]
        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]
        current_volume_ma = self.volume_ma[-1]
        
        # Calculate VPT slope
        vpt_slope = self.calculate_vpt_slope()
        
        # Determine trend conditions
        vpt_trend_up = vpt_slope > 0.001  # Small positive threshold
        vpt_trend_down = vpt_slope < -0.001  # Small negative threshold
        
        # ADX trend strength
        strong_trend = current_adx > self.adx_threshold
        
        # Directional indicator signals
        di_diff = current_plus_di - current_minus_di
        bullish_di = di_diff > self.di_diff_threshold
        bearish_di = di_diff < -self.di_diff_threshold
        
        # Volume filter
        volume_sufficient = current_volume > current_volume_ma * self.min_volume_factor
        
        if not self.position:
            # LONG ENTRY CONDITIONS
            if vpt_trend_up and strong_trend and bullish_di and volume_sufficient:
                # All conditions aligned for long
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Alternative long: Very strong ADX with VPT confirmation
            if current_adx > 30 and vpt_trend_up and current_plus_di > current_minus_di:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # SHORT ENTRY CONDITIONS
            if vpt_trend_down and strong_trend and bearish_di and volume_sufficient:
                # All conditions aligned for short
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Alternative short: Very strong ADX with VPT confirmation
            if current_adx > 30 and vpt_trend_down and current_minus_di > current_plus_di:
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
bt = Backtest(data, VPTADX, cash=100000, commission=0.00045)

print("\n🌙 ===== VPT + ADX - FIXED PARAMETERS ===== 🌙")
print(f"VPT MA Period: {VPT_MA_PERIOD}")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Threshold: {ADX_THRESHOLD}")
print(f"DI Difference Threshold: {DI_DIFF_THRESHOLD}")
print(f"VPT Slope Lookback: {VPT_SLOPE_LOOKBACK}")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Min Volume Factor: {MIN_VOLUME_FACTOR}")

stats = bt.run()
print(stats)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING VPT + ADX ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(VPTADX, 'VPTADX')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/VPTADX.csv")