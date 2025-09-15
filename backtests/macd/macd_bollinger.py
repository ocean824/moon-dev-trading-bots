"""
Moon Dev's MACD Bollinger Strategy
===================================
MACD strategy with Bollinger Bands for volatility-based filtering
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's MACD Bollinger Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# MACD parameters
FAST_PERIOD = 12
SLOW_PERIOD = 26
SIGNAL_PERIOD = 9

# Bollinger Bands parameters
BB_PERIOD = 20
BB_STD = 2.0

# Risk management
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class MACDBollinger(Strategy):
    """
    MACD Bollinger Strategy
    - Uses MACD crossovers with Bollinger Bands for volatility filtering
    - Bollinger Bands identify overbought/oversold conditions
    - Band squeeze indicates low volatility (potential breakout)
    - Combines momentum (MACD) with volatility (BB) analysis
    """
    
    # MACD parameters
    fast_period = FAST_PERIOD
    slow_period = SLOW_PERIOD
    signal_period = SIGNAL_PERIOD
    
    # Bollinger Bands parameters
    bb_period = BB_PERIOD
    bb_std = BB_STD
    
    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    # Histogram momentum threshold
    histogram_threshold = 0.0001
    
    # Bollinger Band squeeze threshold (as % of price)
    squeeze_threshold = 0.02  # 2% squeeze
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Calculate MACD
        macd_result = ta.macd(close, 
                              fast=self.fast_period, 
                              slow=self.slow_period, 
                              signal=self.signal_period)
        
        # Extract MACD components
        macd_line = macd_result[f'MACD_{self.fast_period}_{self.slow_period}_{self.signal_period}']
        signal_line = macd_result[f'MACDs_{self.fast_period}_{self.slow_period}_{self.signal_period}']
        histogram = macd_result[f'MACDh_{self.fast_period}_{self.slow_period}_{self.signal_period}']
        
        # Ensure arrays are same length as data
        macd_full = np.full(len(close), np.nan)
        signal_full = np.full(len(close), np.nan)
        histogram_full = np.full(len(close), np.nan)
        
        macd_full[-len(macd_line):] = macd_line.values
        signal_full[-len(signal_line):] = signal_line.values
        histogram_full[-len(histogram):] = histogram.values
        
        self.macd = self.I(lambda: macd_full, name='MACD')
        self.signal = self.I(lambda: signal_full, name='Signal')
        self.histogram = self.I(lambda: histogram_full, name='Histogram')
        
        # Previous values for crossover detection
        macd_prev = np.roll(macd_full, 1)
        signal_prev = np.roll(signal_full, 1)
        histogram_prev = np.roll(histogram_full, 1)
        
        macd_prev[0] = np.nan
        signal_prev[0] = np.nan
        histogram_prev[0] = np.nan
        
        self.macd_prev = self.I(lambda: macd_prev, name='MACD_Prev')
        self.signal_prev = self.I(lambda: signal_prev, name='Signal_Prev')
        self.histogram_prev = self.I(lambda: histogram_prev, name='Histogram_Prev')
        
        # Calculate histogram momentum
        histogram_momentum = histogram_full - histogram_prev
        self.histogram_momentum = self.I(lambda: histogram_momentum, name='Histogram_Momentum')
        
        # Calculate Bollinger Bands
        bb_result = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        
        # Extract Bollinger Band components
        bb_lower = bb_result[f'BBL_{self.bb_period}_{self.bb_std}']
        bb_middle = bb_result[f'BBM_{self.bb_period}_{self.bb_std}']
        bb_upper = bb_result[f'BBU_{self.bb_period}_{self.bb_std}']
        bb_bandwidth = bb_result[f'BBB_{self.bb_period}_{self.bb_std}']
        bb_percent = bb_result[f'BBP_{self.bb_period}_{self.bb_std}']
        
        # Create full-length arrays for Bollinger Bands
        bb_lower_full = np.full(len(close), np.nan)
        bb_middle_full = np.full(len(close), np.nan)
        bb_upper_full = np.full(len(close), np.nan)
        bb_bandwidth_full = np.full(len(close), np.nan)
        bb_percent_full = np.full(len(close), np.nan)
        
        bb_lower_full[-len(bb_lower):] = bb_lower.values
        bb_middle_full[-len(bb_middle):] = bb_middle.values
        bb_upper_full[-len(bb_upper):] = bb_upper.values
        bb_bandwidth_full[-len(bb_bandwidth):] = bb_bandwidth.values
        bb_percent_full[-len(bb_percent):] = bb_percent.values
        
        self.bb_lower = self.I(lambda: bb_lower_full, name='BB_Lower')
        self.bb_middle = self.I(lambda: bb_middle_full, name='BB_Middle')
        self.bb_upper = self.I(lambda: bb_upper_full, name='BB_Upper')
        self.bb_bandwidth = self.I(lambda: bb_bandwidth_full, name='BB_Width')
        self.bb_percent = self.I(lambda: bb_percent_full, name='BB_Percent')
        
        # Calculate band squeeze indicator
        # Squeeze occurs when bandwidth is at recent lows
        bb_squeeze = np.full(len(close), 0)
        for i in range(20, len(bb_bandwidth_full)):
            if not np.isnan(bb_bandwidth_full[i]):
                recent_bandwidth = bb_bandwidth_full[i-20:i]
                recent_bandwidth = recent_bandwidth[~np.isnan(recent_bandwidth)]
                if len(recent_bandwidth) > 0:
                    min_bandwidth = np.min(recent_bandwidth)
                    if bb_bandwidth_full[i] <= min_bandwidth * 1.1:  # Within 10% of recent minimum
                        bb_squeeze[i] = 1
        
        self.bb_squeeze = self.I(lambda: bb_squeeze, name='BB_Squeeze')
        
        # Previous BB percent for trend detection
        bb_percent_prev = np.roll(bb_percent_full, 1)
        bb_percent_prev[0] = np.nan
        self.bb_percent_prev = self.I(lambda: bb_percent_prev, name='BB_Percent_Prev')
        
    def next(self):
        # Skip if indicators not ready
        if (np.isnan(self.macd[-1]) or np.isnan(self.signal[-1]) or 
            np.isnan(self.histogram[-1]) or np.isnan(self.bb_upper[-1])):
            return
        
        # Skip if previous values not ready
        if np.isnan(self.macd_prev[-1]) or np.isnan(self.signal_prev[-1]):
            return
        
        current_price = self.data.Close[-1]
        
        # Detect MACD crossovers
        bullish_crossover = (self.macd_prev[-1] <= self.signal_prev[-1] and 
                            self.macd[-1] > self.signal[-1])
        
        bearish_crossover = (self.macd_prev[-1] >= self.signal_prev[-1] and 
                            self.macd[-1] < self.signal[-1])
        
        # Check histogram momentum
        histogram_increasing = self.histogram_momentum[-1] > self.histogram_threshold
        histogram_decreasing = self.histogram_momentum[-1] < -self.histogram_threshold
        
        # Check if histogram is positive or negative
        histogram_positive = self.histogram[-1] > 0
        histogram_negative = self.histogram[-1] < 0
        
        # Bollinger Band conditions
        at_lower_band = current_price <= self.bb_lower[-1] * 1.01  # Within 1% of lower band
        at_upper_band = current_price >= self.bb_upper[-1] * 0.99  # Within 1% of upper band
        above_middle = current_price > self.bb_middle[-1]
        below_middle = current_price < self.bb_middle[-1]
        
        # BB percent conditions (0 = at lower band, 1 = at upper band)
        bb_oversold = self.bb_percent[-1] < 0.2  # Below 20%
        bb_overbought = self.bb_percent[-1] > 0.8  # Above 80%
        bb_neutral = 0.2 <= self.bb_percent[-1] <= 0.8
        
        # Check for band squeeze
        in_squeeze = self.bb_squeeze[-1] == 1
        
        # BB percent momentum
        bb_turning_up = (self.bb_percent[-1] > self.bb_percent_prev[-1] 
                         if not np.isnan(self.bb_percent_prev[-1]) else False)
        bb_turning_down = (self.bb_percent[-1] < self.bb_percent_prev[-1] 
                          if not np.isnan(self.bb_percent_prev[-1]) else False)
        
        # Band expansion after squeeze
        expanding_after_squeeze = (self.bb_squeeze[-2] == 1 and self.bb_squeeze[-1] == 0 
                                  if not np.isnan(self.bb_squeeze[-2]) else False)
        
        if not self.position:
            # Long entry: MACD bullish with BB oversold bounce
            if (bullish_crossover and histogram_increasing and histogram_positive and 
                (at_lower_band or bb_oversold) and bb_turning_up):
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
            
            # Alternative long: Squeeze breakout to upside with MACD confirmation
            elif (expanding_after_squeeze and above_middle and 
                  histogram_positive and self.macd[-1] > self.signal[-1]):
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
            
            # Short entry: MACD bearish with BB overbought reversal
            elif (bearish_crossover and histogram_decreasing and histogram_negative and 
                  (at_upper_band or bb_overbought) and bb_turning_down):
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
            
            # Alternative short: Squeeze breakout to downside with MACD confirmation
            elif (expanding_after_squeeze and below_middle and 
                  histogram_negative and self.macd[-1] < self.signal[-1]):
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
        
        # Exit conditions for existing positions
        elif self.position.is_long:
            # Exit long if price hits upper band or MACD turns bearish
            if (at_upper_band and bb_turning_down) or bearish_crossover:
                self.position.close()
            # Also exit if price breaks below middle band with negative momentum
            elif below_middle and histogram_negative:
                self.position.close()
        
        elif self.position.is_short:
            # Exit short if price hits lower band or MACD turns bullish
            if (at_lower_band and bb_turning_up) or bullish_crossover:
                self.position.close()
            # Also exit if price breaks above middle band with positive momentum
            elif above_middle and histogram_positive:
                self.position.close()

# Run single backtest
bt = Backtest(data, MACDBollinger, cash=100000, commission=0.00045)

print("\n🌙 ===== MACD BOLLINGER STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Fast Period: {FAST_PERIOD}")
print(f"Slow Period: {SLOW_PERIOD}")
print(f"Signal Period: {SIGNAL_PERIOD}")
print(f"Bollinger Period: {BB_PERIOD}")
print(f"Bollinger Std Dev: {BB_STD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MACD BOLLINGER STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(MACDBollinger, 'MACDBollinger')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MACDBollinger_[timestamp].csv")