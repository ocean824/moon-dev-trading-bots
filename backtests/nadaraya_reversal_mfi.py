import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's Nadaraya-Watson Reversal + MFI Strategy Loading... 🌙")

class NadarayaWatsonReversalMFI(Strategy):
    # Parameters
    bandwidth = 100
    kernel_type = 'gaussian'
    
    # MFI parameters
    mfi_period = 14
    mfi_oversold = 30
    mfi_overbought = 70
    
    atr_period = 14
    atr_multiplier_stop = 2.0
    atr_multiplier_target = 3.0
    volume_confirm_period = 20
    volume_threshold = 1.2
    min_distance = 0.001
    
    def init(self):
        # Calculate ATR for stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=self.atr_period)
        
        # Calculate MFI for overbought/oversold confirmation
        self.mfi = self.I(talib.MFI, self.data.High, self.data.Low, self.data.Close, 
                         self.data.Volume, timeperiod=self.mfi_period)
        
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
        
        # Calculate MFI divergence indicator
        def calc_mfi_divergence(mfi, prices, lookback=20):
            divergence = np.zeros(len(prices))
            mfi_array = np.array(mfi)
            prices_array = np.array(prices)
            
            for i in range(lookback, len(prices)):
                # Find recent peaks and troughs
                price_slice = prices_array[i-lookback:i+1]
                mfi_slice = mfi_array[i-lookback:i+1]
                
                # Bullish divergence: price making lower lows, MFI making higher lows
                if i > lookback + 1:
                    price_trend = np.polyfit(range(len(price_slice)), price_slice, 1)[0]
                    mfi_trend = np.polyfit(range(len(mfi_slice)), mfi_slice, 1)[0]
                    
                    if price_trend < 0 and mfi_trend > 0:
                        divergence[i] = 1  # Bullish divergence
                    elif price_trend > 0 and mfi_trend < 0:
                        divergence[i] = -1  # Bearish divergence
            
            return divergence
        
        self.mfi_divergence = self.I(calc_mfi_divergence, self.mfi, self.data.Close, 20)
        
        # Track entry details
        self.entry_price = None
        self.entry_atr = None
        self.is_long = None
    
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
        current_mfi = self.mfi[-1]
        current_divergence = self.mfi_divergence[-1]
        
        # Check if we have a position
        if self.position:
            # Exit logic based on position type
            if self.is_long:
                # Long exit conditions
                stop_price = self.entry_price - (self.entry_atr * self.atr_multiplier_stop)
                target_price = self.entry_price + (self.entry_atr * self.atr_multiplier_target)
                
                if current_price <= stop_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                elif current_price >= target_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                # Exit if MFI becomes overbought
                elif current_mfi > 80:  # Strong overbought
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
            
            else:  # Short position
                # Short exit conditions
                stop_price = self.entry_price + (self.entry_atr * self.atr_multiplier_stop)
                target_price = self.entry_price - (self.entry_atr * self.atr_multiplier_target)
                
                if current_price >= stop_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                elif current_price <= target_price:
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                # Exit if MFI becomes oversold
                elif current_mfi < 20:  # Strong oversold
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
        
        else:
            # Entry logic - Reversals with MFI confirmation
            volume_confirm = current_volume > (volume_avg * self.volume_threshold)
            
            # Long entry - Price bouncing up from NW line with oversold MFI
            if (prev_distance < -self.min_distance and  # Was below NW line
                current_distance > prev_distance and  # Moving back up
                abs(current_distance) < self.min_distance * 2 and  # Close to NW line
                current_mfi < self.mfi_oversold and  # MFI oversold
                volume_confirm):  # Volume confirmation
                
                # Extra confirmation: bullish divergence
                if current_divergence > 0:
                    self.buy(size=1.2)  # Larger position with divergence
                else:
                    self.buy()
                
                self.entry_price = current_price
                self.entry_atr = current_atr
                self.is_long = True
            
            # Short entry - Price bouncing down from NW line with overbought MFI
            elif (prev_distance > self.min_distance and  # Was above NW line
                  current_distance < prev_distance and  # Moving back down
                  abs(current_distance) < self.min_distance * 2 and  # Close to NW line
                  current_mfi > self.mfi_overbought and  # MFI overbought
                  volume_confirm):  # Volume confirmation
                
                # Extra confirmation: bearish divergence
                if current_divergence < 0:
                    self.sell(size=1.2)  # Larger position with divergence
                else:
                    self.sell()
                
                self.entry_price = current_price
                self.entry_atr = current_atr
                self.is_long = False

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING NADARAYA-WATSON REVERSAL + MFI STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(NadarayaWatsonReversalMFI, 'NadarayaWatsonReversalMFI')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/NadarayaWatsonReversalMFI.csv")