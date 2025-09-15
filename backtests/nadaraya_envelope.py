import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's Nadaraya-Watson Envelope Strategy Loading... 🌙")

class NadarayaWatsonEnvelope(Strategy):
    # Parameters
    bandwidth = 100
    kernel_type = 'gaussian'
    atr_period = 14
    band_multiplier = 2.0  # ATR multiplier for bands
    exit_at_middle = True  # Exit at middle line or opposite band
    volume_confirm_period = 20
    volume_threshold = 1.1
    
    def init(self):
        # Calculate ATR for band width
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=self.atr_period)
        
        # Calculate volume MA for confirmation
        self.volume_ma = self.I(talib.SMA, self.data.Volume, timeperiod=self.volume_confirm_period)
        
        # Calculate standard deviation for alternative band calculation
        self.std = self.I(talib.STDDEV, self.data.Close, timeperiod=self.bandwidth // 2)
        
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
        
        # Calculate envelope bands using ATR
        def calc_upper_band(nw, atr, multiplier):
            return nw + (atr * multiplier)
        
        def calc_lower_band(nw, atr, multiplier):
            return nw - (atr * multiplier)
        
        self.upper_band = self.I(calc_upper_band, self.nw_line, self.atr, self.band_multiplier)
        self.lower_band = self.I(calc_lower_band, self.nw_line, self.atr, self.band_multiplier)
        
        # Track entry details
        self.entry_price = None
        self.is_long = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.bandwidth:
            return
        
        # Current values
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        current_nw = self.nw_line[-1]
        current_upper = self.upper_band[-1]
        current_lower = self.lower_band[-1]
        current_volume = self.data.Volume[-1]
        volume_avg = self.volume_ma[-1]
        
        # Check if we have a position
        if self.position:
            # Exit logic based on position type
            if self.is_long:
                # Long exit conditions
                if self.exit_at_middle:
                    # Exit at middle line or upper band
                    if current_price >= current_nw:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                else:
                    # Exit only at upper band
                    if current_price >= current_upper:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                
                # Stop loss if price goes below lower band
                if current_price < current_lower * 0.98:  # 2% below lower band
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
            
            else:  # Short position
                # Short exit conditions
                if self.exit_at_middle:
                    # Exit at middle line or lower band
                    if current_price <= current_nw:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                else:
                    # Exit only at lower band
                    if current_price <= current_lower:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                
                # Stop loss if price goes above upper band
                if current_price > current_upper * 1.02:  # 2% above upper band
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
        
        else:
            # Entry logic - Touch of envelope bands
            volume_confirm = current_volume > (volume_avg * self.volume_threshold)
            
            # Long entry - Price touches lower band
            if (current_low <= current_lower and  # Low touched or pierced lower band
                current_price > current_lower and  # But closing above it (rejection)
                volume_confirm):  # Volume confirmation
                
                self.buy()
                self.entry_price = current_price
                self.is_long = True
            
            # Short entry - Price touches upper band
            elif (current_high >= current_upper and  # High touched or pierced upper band
                  current_price < current_upper and  # But closing below it (rejection)
                  volume_confirm):  # Volume confirmation
                
                self.sell()
                self.entry_price = current_price
                self.is_long = False

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING NADARAYA-WATSON ENVELOPE STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(NadarayaWatsonEnvelope, 'NadarayaWatsonEnvelope')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/NadarayaWatsonEnvelope.csv")