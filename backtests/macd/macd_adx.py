"""
Moon Dev's MACD ADX Strategy
=============================
MACD strategy with ADX for trend strength filtering
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's MACD ADX Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# MACD parameters
FAST_PERIOD = 12
SLOW_PERIOD = 26
SIGNAL_PERIOD = 9

# ADX parameters
ADX_PERIOD = 14
ADX_THRESHOLD = 25  # Minimum ADX for strong trend

# Risk management
TAKE_PROFIT_PERCENT = 3.0
STOP_LOSS_PERCENT = 2.0

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class MACDADX(Strategy):
    """
    MACD ADX Strategy
    - Uses MACD crossovers with ADX trend strength filter
    - ADX > 25 indicates strong trend
    - +DI and -DI indicate trend direction
    - Only trades when trend is strong (high ADX)
    """
    
    # MACD parameters
    fast_period = FAST_PERIOD
    slow_period = SLOW_PERIOD
    signal_period = SIGNAL_PERIOD
    
    # ADX parameters
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    
    # Risk management
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    
    # Histogram momentum threshold
    histogram_threshold = 0.0001
    
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
        
        # Calculate ADX for trend strength
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        
        # Extract ADX components
        adx_line = adx_result[f'ADX_{self.adx_period}']
        plus_di = adx_result[f'DMP_{self.adx_period}']  # +DI
        minus_di = adx_result[f'DMN_{self.adx_period}']  # -DI
        
        # Create full-length arrays for ADX
        adx_full = np.full(len(close), np.nan)
        plus_di_full = np.full(len(close), np.nan)
        minus_di_full = np.full(len(close), np.nan)
        
        adx_full[-len(adx_line):] = adx_line.values
        plus_di_full[-len(plus_di):] = plus_di.values
        minus_di_full[-len(minus_di):] = minus_di.values
        
        self.adx = self.I(lambda: adx_full, name='ADX')
        self.plus_di = self.I(lambda: plus_di_full, name='+DI')
        self.minus_di = self.I(lambda: minus_di_full, name='-DI')
        
        # Calculate ADX slope for trend acceleration
        adx_slope = adx_full - np.roll(adx_full, 5)
        self.adx_slope = self.I(lambda: adx_slope, name='ADX_Slope')
        
    def next(self):
        # Skip if indicators not ready
        if (np.isnan(self.macd[-1]) or np.isnan(self.signal[-1]) or 
            np.isnan(self.histogram[-1]) or np.isnan(self.adx[-1])):
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
        
        # ADX trend strength analysis
        strong_trend = self.adx[-1] > self.adx_threshold
        trend_strengthening = self.adx_slope[-1] > 0 if not np.isnan(self.adx_slope[-1]) else False
        
        # Determine trend direction using +DI and -DI
        bullish_trend = self.plus_di[-1] > self.minus_di[-1]
        bearish_trend = self.minus_di[-1] > self.plus_di[-1]
        
        # DI crossover signals
        di_bullish_cross = (self.plus_di[-1] > self.minus_di[-1] and 
                           self.plus_di[-2] <= self.minus_di[-2]) if not np.isnan(self.plus_di[-2]) else False
        
        di_bearish_cross = (self.minus_di[-1] > self.plus_di[-1] and 
                           self.minus_di[-2] <= self.plus_di[-2]) if not np.isnan(self.minus_di[-2]) else False
        
        if not self.position:
            # Long entry: MACD bullish with strong uptrend (ADX confirmation)
            if (bullish_crossover and histogram_increasing and histogram_positive and 
                strong_trend and bullish_trend):
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
            
            # Alternative long entry: Strong DI bullish cross with MACD confirmation
            elif (di_bullish_cross and strong_trend and histogram_positive and 
                  self.macd[-1] > self.signal[-1]):
                sl_price = current_price * (1 - self.stop_loss)
                tp_price = current_price * (1 + self.take_profit)
                self.buy(sl=sl_price, tp=tp_price)
            
            # Short entry: MACD bearish with strong downtrend (ADX confirmation)
            elif (bearish_crossover and histogram_decreasing and histogram_negative and 
                  strong_trend and bearish_trend):
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
            
            # Alternative short entry: Strong DI bearish cross with MACD confirmation
            elif (di_bearish_cross and strong_trend and histogram_negative and 
                  self.macd[-1] < self.signal[-1]):
                sl_price = current_price * (1 + self.stop_loss)
                tp_price = current_price * (1 - self.take_profit)
                self.sell(sl=sl_price, tp=tp_price)
        
        # Exit conditions for existing positions
        elif self.position.is_long:
            # Exit long if trend weakens or MACD turns bearish
            if (self.adx[-1] < self.adx_threshold * 0.8 or 
                bearish_crossover or bearish_trend):
                self.position.close()
        
        elif self.position.is_short:
            # Exit short if trend weakens or MACD turns bullish
            if (self.adx[-1] < self.adx_threshold * 0.8 or 
                bullish_crossover or bullish_trend):
                self.position.close()

# Run single backtest
bt = Backtest(data, MACDADX, cash=100000, commission=0.00045)

print("\n🌙 ===== MACD ADX STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Fast Period: {FAST_PERIOD}")
print(f"Slow Period: {SLOW_PERIOD}")
print(f"Signal Period: {SIGNAL_PERIOD}")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Threshold: {ADX_THRESHOLD}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")

stats_default = bt.run()
print(stats_default)

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING MACD ADX STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from backtests.multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(MACDADX, 'MACDADX')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/MACDADX_[timestamp].csv")