import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's Nadaraya-Watson Envelope + MFI Strategy Loading... 🌙")

class NadarayaWatsonEnvelopeMFI(Strategy):
    # Parameters
    bandwidth = 100
    kernel_type = 'gaussian'
    
    # MFI parameters
    mfi_period = 14
    mfi_extreme_oversold = 20
    mfi_extreme_overbought = 80
    
    atr_period = 14
    band_multiplier = 2.0
    exit_at_middle = True
    volume_confirm_period = 20
    volume_threshold = 1.1
    
    def init(self):
        # Calculate ATR for band width
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=self.atr_period)
        
        # Calculate MFI for extreme overbought/oversold confirmation
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
        
        # Calculate dynamic band width based on MFI
        def calc_dynamic_band_multiplier(mfi, base_multiplier):
            """Adjust band width based on MFI - wider bands in extreme conditions"""
            multipliers = np.zeros(len(mfi))
            mfi_array = np.array(mfi)
            
            for i in range(len(mfi)):
                if mfi_array[i] < 30 or mfi_array[i] > 70:
                    # Wider bands in extreme conditions
                    multipliers[i] = base_multiplier * 1.2
                elif mfi_array[i] < 20 or mfi_array[i] > 80:
                    # Even wider bands in very extreme conditions
                    multipliers[i] = base_multiplier * 1.4
                else:
                    # Normal band width
                    multipliers[i] = base_multiplier
            
            return multipliers
        
        self.dynamic_multiplier = self.I(calc_dynamic_band_multiplier, self.mfi, self.band_multiplier)
        
        # Calculate envelope bands using dynamic multiplier
        def calc_upper_band(nw, atr, multiplier):
            return nw + (atr * multiplier)
        
        def calc_lower_band(nw, atr, multiplier):
            return nw - (atr * multiplier)
        
        self.upper_band = self.I(calc_upper_band, self.nw_line, self.atr, self.dynamic_multiplier)
        self.lower_band = self.I(calc_lower_band, self.nw_line, self.atr, self.dynamic_multiplier)
        
        # Track entry details
        self.entry_price = None
        self.is_long = None
        self.entry_mfi = None
    
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
        current_mfi = self.mfi[-1]
        
        # Check for MFI divergence
        if len(self.mfi) > 20:
            recent_price_trend = (current_price - self.data.Close[-20]) / self.data.Close[-20]
            recent_mfi_trend = (current_mfi - self.mfi[-20]) / max(self.mfi[-20], 1)
            divergence = (recent_price_trend < 0 and recent_mfi_trend > 0) or \
                        (recent_price_trend > 0 and recent_mfi_trend < 0)
        else:
            divergence = False
        
        # Check if we have a position
        if self.position:
            # Exit logic based on position type
            if self.is_long:
                # Long exit conditions
                if self.exit_at_middle:
                    # Exit at middle line if MFI is no longer oversold
                    if current_price >= current_nw and current_mfi > 50:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                        self.entry_mfi = None
                else:
                    # Exit at upper band
                    if current_price >= current_upper:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                        self.entry_mfi = None
                
                # Stop loss if price goes below lower band or MFI reverses strongly
                if current_price < current_lower * 0.98 or \
                   (self.entry_mfi < 30 and current_mfi > 70):  # MFI reversed from oversold to overbought
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                    self.entry_mfi = None
            
            else:  # Short position
                # Short exit conditions
                if self.exit_at_middle:
                    # Exit at middle line if MFI is no longer overbought
                    if current_price <= current_nw and current_mfi < 50:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                        self.entry_mfi = None
                else:
                    # Exit at lower band
                    if current_price <= current_lower:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                        self.entry_mfi = None
                
                # Stop loss if price goes above upper band or MFI reverses strongly
                if current_price > current_upper * 1.02 or \
                   (self.entry_mfi > 70 and current_mfi < 30):  # MFI reversed from overbought to oversold
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                    self.entry_mfi = None
        
        else:
            # Entry logic - Band touches with extreme MFI confirmation
            volume_confirm = current_volume > (volume_avg * self.volume_threshold)
            
            # Long entry - Lower band touch with extreme oversold MFI
            if (current_low <= current_lower and  # Low touched lower band
                current_price > current_lower and  # Closing above it
                current_mfi < self.mfi_extreme_oversold and  # Extreme oversold
                volume_confirm):  # Volume confirmation
                
                # Extra size if we have divergence
                if divergence:
                    self.buy(size=1.5)
                else:
                    self.buy()
                
                self.entry_price = current_price
                self.is_long = True
                self.entry_mfi = current_mfi
            
            # Short entry - Upper band touch with extreme overbought MFI
            elif (current_high >= current_upper and  # High touched upper band
                  current_price < current_upper and  # Closing below it
                  current_mfi > self.mfi_extreme_overbought and  # Extreme overbought
                  volume_confirm):  # Volume confirmation
                
                # Extra size if we have divergence
                if divergence:
                    self.sell(size=1.5)
                else:
                    self.sell()
                
                self.entry_price = current_price
                self.is_long = False
                self.entry_mfi = current_mfi

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING NADARAYA-WATSON ENVELOPE + MFI STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(NadarayaWatsonEnvelopeMFI, 'NadarayaWatsonEnvelopeMFI')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/NadarayaWatsonEnvelopeMFI.csv")