import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's Nadaraya-Watson Envelope Long Only Strategy Loading... 🌙")

class NadarayaWatsonEnvelopeLongOnly(Strategy):
    # Parameters
    bandwidth = 100
    kernel_type = 'gaussian'
    atr_period = 14
    band_multiplier = 2.5  # Wider bands for fewer but higher quality signals
    scale_out_middle = True  # Scale out 50% at middle line
    volume_confirm_period = 20
    volume_threshold = 1.2
    
    def init(self):
        # Calculate ATR for band width
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=self.atr_period)
        
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
        
        # Calculate envelope bands using ATR
        def calc_upper_band(nw, atr, multiplier):
            return nw + (atr * multiplier)
        
        def calc_lower_band(nw, atr, multiplier):
            return nw - (atr * multiplier)
        
        self.upper_band = self.I(calc_upper_band, self.nw_line, self.atr, self.band_multiplier)
        self.lower_band = self.I(calc_lower_band, self.nw_line, self.atr, self.band_multiplier)
        
        # Track entry details
        self.entry_price = None
        self.scaled_out = False
        self.initial_size = None
    
    def next(self):
        # Skip if we don't have enough data
        if len(self.data) < self.bandwidth:
            return
        
        # Current values
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_nw = self.nw_line[-1]
        current_upper = self.upper_band[-1]
        current_lower = self.lower_band[-1]
        current_volume = self.data.Volume[-1]
        volume_avg = self.volume_ma[-1]
        
        # Check if we have a position
        if self.position:
            # Exit logic for long positions only
            
            # Scale out at middle line if enabled and not already scaled
            if self.scale_out_middle and not self.scaled_out and current_price >= current_nw:
                # Close half position at middle line
                self.position.close(0.5)
                self.scaled_out = True
            
            # Full exit at upper band
            if current_price >= current_upper:
                self.position.close()
                self.entry_price = None
                self.scaled_out = False
                self.initial_size = None
            
            # Stop loss if price goes back below lower band
            elif current_price < current_lower * 0.97:  # 3% below lower band
                self.position.close()
                self.entry_price = None
                self.scaled_out = False
                self.initial_size = None
        
        else:
            # Entry logic - Only buy at lower envelope band
            volume_confirm = current_volume > (volume_avg * self.volume_threshold)
            
            # Look for strong rejection from lower band
            touch_lower = current_low <= current_lower
            close_above = current_price > current_lower
            bullish_rejection = (current_price - current_low) > (self.data.High[-1] - current_price)  # Lower wick longer than upper
            
            if (touch_lower and  # Low touched or pierced lower band
                close_above and  # Closing above lower band
                bullish_rejection and  # Bullish rejection candle
                volume_confirm):  # Volume confirmation
                
                self.buy()
                self.entry_price = current_price
                self.scaled_out = False
                self.initial_size = self.position.size if self.position else None

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING NADARAYA-WATSON ENVELOPE LONG ONLY STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(NadarayaWatsonEnvelopeLongOnly, 'NadarayaWatsonEnvelopeLongOnly')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/NadarayaWatsonEnvelopeLongOnly.csv")