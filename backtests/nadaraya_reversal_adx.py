import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's Nadaraya-Watson Reversal + ADX Strategy Loading... 🌙")

class NadarayaWatsonReversalADX(Strategy):
    # Parameters
    bandwidth = 100
    kernel_type = 'gaussian'
    
    # ADX parameters
    adx_period = 14
    adx_trending = 25  # Above this = trending market
    adx_choppy = 20  # Below this = choppy/ranging market
    
    atr_period = 14
    atr_multiplier_stop = 2.0
    atr_multiplier_target = 3.0
    volume_confirm_period = 20
    volume_threshold = 1.2
    min_distance = 0.001
    
    def init(self):
        # Calculate ATR for stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=self.atr_period)
        
        # Calculate ADX and directional indicators
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, timeperiod=self.adx_period)
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, timeperiod=self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, timeperiod=self.adx_period)
        
        # Calculate volume MA for confirmation
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.volume_confirm_period)
        
        # Calculate Nadaraya-Watson estimator
        def nadaraya_watson(prices, bandwidth=100, kernel='gaussian'):
            nw_line = np.zeros(len(prices))
            prices_array = np.array(prices)
            
            for i in range(len(prices)):
                if i < bandwidth:
                    nw_line[i] = prices_array[i]
                else:
                    weights = []
                    values = []
                    
                    for j in range(max(0, i - bandwidth), i + 1):
                        distance = abs(i - j)
                        
                        if kernel == 'gaussian':
                            weight = np.exp(-(distance**2) / (2 * (bandwidth/4)**2))
                        else:
                            weight = 1.0 if distance <= bandwidth else 0.0
                        
                        weights.append(weight)
                        values.append(prices_array[j])
                    
                    weights = np.array(weights)
                    values = np.array(values)
                    
                    if weights.sum() > 0:
                        nw_line[i] = (weights * values).sum() / weights.sum()
                    else:
                        nw_line[i] = prices_array[i]
            
            return nw_line
        
        # Apply NW to close prices
        self.nw_line = self.I(nadaraya_watson, self.data.Close, self.bandwidth, self.kernel_type)
        
        # Calculate distance from price to NW line
        def calc_distance(close, nw):
            return (close - nw) / nw
        
        self.distance = self.I(calc_distance, self.data.Close, self.nw_line)
        
        # Calculate DI crossover signals
        def calc_di_signal(plus_di, minus_di):
            signal = np.zeros(len(plus_di))
            plus_array = np.array(plus_di)
            minus_array = np.array(minus_di)
            
            for i in range(1, len(plus_di)):
                # Bullish crossover
                if plus_array[i] > minus_array[i] and plus_array[i-1] <= minus_array[i-1]:
                    signal[i] = 1
                # Bearish crossover
                elif minus_array[i] > plus_array[i] and minus_array[i-1] <= plus_array[i-1]:
                    signal[i] = -1
            
            return signal
        
        self.di_signal = self.I(calc_di_signal, self.plus_di, self.minus_di)
        
        # Track entry details
        self.entry_price = None
        self.entry_atr = None
        self.is_long = None
        self.entry_adx = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.bandwidth:
            return
        
        # Current values
        current_price = self.data.Close[-1]
        current_nw = self.nw_line[-1]
        current_distance = self.distance[-1]
        prev_distance = self.distance[-2] if len(self.distance) > 1 else 0
        current_volume = self.data.Volume[-1]
        volume_avg = self.volume_ma[-1]
        current_atr = self.atr[-1]
        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]
        current_di_signal = self.di_signal[-1]
        
        # Check if we have a position
        if self.position:
            # Dynamic exit based on ADX changes
            adx_weakening = self.entry_adx and current_adx < self.entry_adx * 0.8  # ADX dropped 20%
            
            # Exit logic based on position type
            if self.is_long:
                # Long exit conditions
                stop_price = self.entry_price - (self.entry_atr * self.atr_multiplier_stop)
                target_price = self.entry_price + (self.entry_atr * self.atr_multiplier_target)
                
                if current_price <= stop_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                    self.entry_adx = None
                elif current_price >= target_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                    self.entry_adx = None
                # Exit if trend weakens or DI flips bearish
                elif adx_weakening or current_minus_di > current_plus_di * 1.2:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                    self.entry_adx = None
            
            else:  # Short position
                # Short exit conditions
                stop_price = self.entry_price + (self.entry_atr * self.atr_multiplier_stop)
                target_price = self.entry_price - (self.entry_atr * self.atr_multiplier_target)
                
                if current_price >= stop_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                    self.entry_adx = None
                elif current_price <= target_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                    self.entry_adx = None
                # Exit if trend weakens or DI flips bullish
                elif adx_weakening or current_plus_di > current_minus_di * 1.2:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                    self.entry_adx = None
        
        else:
            # Entry logic - Only take reversals in trending markets
            volume_confirm = current_volume > (volume_avg * self.volume_threshold)
            trending_market = current_adx > self.adx_trending
            not_choppy = current_adx > self.adx_choppy
            
            # Avoid reversals in choppy markets
            if not not_choppy:
                return
            
            # Long entry - Price bouncing up from NW line with trend confirmation
            if (prev_distance < -self.min_distance and  # Was below NW line
                current_distance > prev_distance and  # Moving back up
                abs(current_distance) < self.min_distance * 2 and  # Close to NW line
                trending_market and  # ADX confirms trending market
                (current_plus_di > current_minus_di or current_di_signal > 0) and  # DI confirms bullish
                volume_confirm):  # Volume confirmation
                
                self.buy()
                self.entry_price = current_price
                self.entry_atr = current_atr
                self.is_long = True
                self.entry_adx = current_adx
            
            # Short entry - Price bouncing down from NW line with trend confirmation
            elif (prev_distance > self.min_distance and  # Was above NW line
                  current_distance < prev_distance and  # Moving back down
                  abs(current_distance) < self.min_distance * 2 and  # Close to NW line
                  trending_market and  # ADX confirms trending market
                  (current_minus_di > current_plus_di or current_di_signal < 0) and  # DI confirms bearish
                  volume_confirm):  # Volume confirmation
                
                self.sell()
                self.entry_price = current_price
                self.entry_atr = current_atr
                self.is_long = False
                self.entry_adx = current_adx

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING NADARAYA-WATSON REVERSAL + ADX STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(NadarayaWatsonReversalADX, 'NadarayaWatsonReversalADX')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/NadarayaWatsonReversalADX.csv")