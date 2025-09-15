"""
Moon Dev's Volume Price Trend (VPT) + Money Flow Index (MFI) Strategy
======================================================================
VPT indicator combined with MFI for additional volume confirmation
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's VPT + MFI Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - FIXED, NO OPTIMIZATION
VPT_MA_PERIOD = 14  # Moving average for VPT smoothing
MFI_PERIOD = 14  # MFI period
MFI_OVERBOUGHT = 80  # MFI overbought level
MFI_OVERSOLD = 20  # MFI oversold level
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

class VPTMFI(Strategy):
    """
    VPT + MFI Strategy
    - Use VPT for volume-price trend analysis
    - MFI for money flow strength and overbought/oversold conditions
    - Look for convergence/divergence between VPT and MFI
    - Enter when both indicators align with volume confirmation
    """
    
    # VPT parameters
    vpt_ma_period = VPT_MA_PERIOD
    vpt_slope_lookback = VPT_SLOPE_LOOKBACK
    divergence_lookback = DIVERGENCE_LOOKBACK
    
    # MFI parameters
    mfi_period = MFI_PERIOD
    mfi_overbought = MFI_OVERBOUGHT
    mfi_oversold = MFI_OVERSOLD
    
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
        
        # Calculate MFI (Money Flow Index)
        mfi = ta.mfi(high, low, close, volume, length=self.mfi_period)
        mfi_full = np.full(len(close), np.nan)
        mfi_full[-len(mfi):] = mfi.values
        self.mfi = self.I(lambda: mfi_full, name='MFI')
        
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
    
    def calculate_mfi_slope(self):
        """Calculate the slope of MFI over recent periods"""
        if len(self.data) < self.vpt_slope_lookback + 1:
            return 0
        
        recent_mfi = self.mfi[-self.vpt_slope_lookback:]
        if any(np.isnan(recent_mfi)):
            return 0
        
        # Calculate linear regression slope
        x = np.arange(len(recent_mfi))
        slope = np.polyfit(x, recent_mfi, 1)[0]
        
        return slope
    
    def detect_vpt_mfi_divergence(self):
        """Detect divergences between VPT and MFI"""
        if len(self.data) < self.divergence_lookback + 1:
            return None
        
        # Get recent price, VPT, and MFI data
        recent_prices = self.data.Close[-self.divergence_lookback:]
        recent_vpt = self.vpt_ma[-self.divergence_lookback:]
        recent_mfi = self.mfi[-self.divergence_lookback:]
        
        if any(np.isnan(recent_vpt)) or any(np.isnan(recent_mfi)):
            return None
        
        # Find recent highs and lows
        price_high_idx = np.argmax(recent_prices)
        price_low_idx = np.argmin(recent_prices)
        vpt_high_idx = np.argmax(recent_vpt)
        vpt_low_idx = np.argmin(recent_vpt)
        mfi_high_idx = np.argmax(recent_mfi)
        mfi_low_idx = np.argmin(recent_mfi)
        
        # Check for bearish divergence (price makes new high, VPT/MFI don't)
        if price_high_idx > len(recent_prices) * 0.6:  # Recent high
            vpt_diverging = (vpt_high_idx < len(recent_vpt) * 0.4 and 
                           recent_vpt[price_high_idx] < recent_vpt[vpt_high_idx])
            mfi_diverging = (mfi_high_idx < len(recent_mfi) * 0.4 and 
                           recent_mfi[price_high_idx] < recent_mfi[mfi_high_idx])
            
            if vpt_diverging and mfi_diverging:
                return 'bearish'
        
        # Check for bullish divergence (price makes new low, VPT/MFI don't)
        if price_low_idx > len(recent_prices) * 0.6:  # Recent low
            vpt_diverging = (vpt_low_idx < len(recent_vpt) * 0.4 and 
                           recent_vpt[price_low_idx] > recent_vpt[vpt_low_idx])
            mfi_diverging = (mfi_low_idx < len(recent_mfi) * 0.4 and 
                           recent_mfi[price_low_idx] > recent_mfi[mfi_low_idx])
            
            if vpt_diverging and mfi_diverging:
                return 'bullish'
        
        return None
    
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.vpt_ma[-1]) or np.isnan(self.mfi[-1]) or np.isnan(self.volume_ma[-1]):
            return
        
        # Skip if we need more data
        if len(self.data) < max(self.vpt_ma_period, self.mfi_period) * 2:
            return
        
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        current_vpt_ma = self.vpt_ma[-1]
        current_mfi = self.mfi[-1]
        current_volume_ma = self.volume_ma[-1]
        
        # Calculate slopes
        vpt_slope = self.calculate_vpt_slope()
        mfi_slope = self.calculate_mfi_slope()
        
        # Determine trend conditions
        vpt_trend_up = vpt_slope > 0.001
        vpt_trend_down = vpt_slope < -0.001
        mfi_trend_up = mfi_slope > 0.5  # MFI slope threshold
        mfi_trend_down = mfi_slope < -0.5
        
        # MFI levels
        mfi_overbought = current_mfi > self.mfi_overbought
        mfi_oversold = current_mfi < self.mfi_oversold
        mfi_neutral = self.mfi_oversold <= current_mfi <= self.mfi_overbought
        
        # Detect divergences
        divergence = self.detect_vpt_mfi_divergence()
        
        # Volume filter
        volume_sufficient = current_volume > current_volume_ma * self.min_volume_factor
        
        if not self.position:
            # LONG ENTRY CONDITIONS
            
            # Primary: Both VPT and MFI trending up from oversold
            if vpt_trend_up and mfi_trend_up and (mfi_oversold or current_mfi < 30) and volume_sufficient:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Secondary: Bullish divergence detected
            if divergence == 'bullish' and volume_sufficient:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Tertiary: VPT rising with MFI in neutral zone but trending up
            if vpt_trend_up and mfi_trend_up and mfi_neutral and volume_sufficient:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Alternative: Strong VPT momentum with MFI not overbought
            if vpt_slope > 0.002 and not mfi_overbought and volume_sufficient:
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # SHORT ENTRY CONDITIONS
            
            # Primary: Both VPT and MFI trending down from overbought
            if vpt_trend_down and mfi_trend_down and (mfi_overbought or current_mfi > 70) and volume_sufficient:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Secondary: Bearish divergence detected
            if divergence == 'bearish' and volume_sufficient:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Tertiary: VPT falling with MFI in neutral zone but trending down
            if vpt_trend_down and mfi_trend_down and mfi_neutral and volume_sufficient:
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.in_position = True
                return
            
            # Alternative: Strong VPT momentum down with MFI not oversold
            if vpt_slope < -0.002 and not mfi_oversold and volume_sufficient:
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
bt = Backtest(data, VPTMFI, cash=100000, commission=0.00045)

print("\n🌙 ===== VPT + MFI - FIXED PARAMETERS ===== 🌙")
print(f"VPT MA Period: {VPT_MA_PERIOD}")
print(f"MFI Period: {MFI_PERIOD}")
print(f"MFI Overbought: {MFI_OVERBOUGHT}")
print(f"MFI Oversold: {MFI_OVERSOLD}")
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
    print("TESTING VPT + MFI ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(VPTMFI, 'VPTMFI')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/VPTMFI.csv")