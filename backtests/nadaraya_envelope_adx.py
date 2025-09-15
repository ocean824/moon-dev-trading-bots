import pandas as pd
import numpy as np
import talib
from backtesting import Strategy

print("🚀 Moon Dev's Nadaraya-Watson Envelope + ADX Strategy Loading... 🌙")

class NadarayaWatsonEnvelopeADX(Strategy):
    # Parameters
    bandwidth = 100
    kernel_type = 'gaussian'
    
    # ADX parameters
    adx_period = 14
    adx_strong_trend = 30  # Strong trend
    adx_trending = 25  # Normal trend
    adx_ranging = 20  # Ranging market
    
    atr_period = 14
    base_band_multiplier = 2.0
    exit_at_middle = True
    volume_confirm_period = 20
    volume_threshold = 1.1
    
    def init(self):
        # Calculate ATR for band width
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
        
        # Calculate dynamic band multiplier based on ADX
        def calc_adx_adjusted_multiplier(adx, base_mult):
            """Adjust band width based on ADX - wider bands in strong trends, tighter in ranges"""
            multipliers = np.zeros(len(adx))
            adx_array = np.array(adx)
            
            for i in range(len(adx)):
                if adx_array[i] > 30:  # Strong trend - wider bands
                    multipliers[i] = base_mult * 1.3
                elif adx_array[i] > 25:  # Normal trend - normal bands
                    multipliers[i] = base_mult * 1.1
                elif adx_array[i] < 20:  # Ranging - tighter bands
                    multipliers[i] = base_mult * 0.8
                else:  # Transition zone
                    multipliers[i] = base_mult
            
            return multipliers
        
        self.dynamic_multiplier = self.I(calc_adx_adjusted_multiplier, self.adx, self.base_band_multiplier)
        
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
        self.entry_adx = None
        self.entry_di_spread = None
    
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
        current_adx = self.adx[-1]
        current_plus_di = self.plus_di[-1]
        current_minus_di = self.minus_di[-1]
        di_spread = abs(current_plus_di - current_minus_di)
        
        # Check if we have a position
        if self.position:
            # Dynamic exit based on market conditions
            market_changed = False
            if self.entry_adx:
                # Check if market regime changed significantly
                if self.entry_adx > 25 and current_adx < 20:  # Trend to range
                    market_changed = True
                elif self.entry_adx < 20 and current_adx > 25:  # Range to trend
                    market_changed = True
            
            # Exit logic based on position type
            if self.is_long:
                # Long exit conditions
                if self.exit_at_middle:
                    # Exit at middle line in ranging markets
                    if current_price >= current_nw and current_adx < self.adx_ranging:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                        self.entry_adx = None
                        self.entry_di_spread = None
                    # Exit at upper band in trending markets
                    elif current_price >= current_upper and current_adx >= self.adx_trending:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                        self.entry_adx = None
                        self.entry_di_spread = None
                else:
                    # Always exit at upper band
                    if current_price >= current_upper:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                        self.entry_adx = None
                        self.entry_di_spread = None
                
                # Stop loss or market regime change
                if current_price < current_lower * 0.98 or market_changed or \
                   (current_minus_di > current_plus_di * 1.5):  # Strong bearish DI
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                    self.entry_adx = None
                    self.entry_di_spread = None
            
            else:  # Short position
                # Short exit conditions
                if self.exit_at_middle:
                    # Exit at middle line in ranging markets
                    if current_price <= current_nw and current_adx < self.adx_ranging:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                        self.entry_adx = None
                        self.entry_di_spread = None
                    # Exit at lower band in trending markets
                    elif current_price <= current_lower and current_adx >= self.adx_trending:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                        self.entry_adx = None
                        self.entry_di_spread = None
                else:
                    # Always exit at lower band
                    if current_price <= current_lower:
                        self.position.close()
                        self.entry_price = None
                        self.is_long = None
                        self.entry_adx = None
                        self.entry_di_spread = None
                
                # Stop loss or market regime change
                if current_price > current_upper * 1.02 or market_changed or \
                   (current_plus_di > current_minus_di * 1.5):  # Strong bullish DI
                    self.position.close()
                    self.entry_price = None
                    self.is_long = None
                    self.entry_adx = None
                    self.entry_di_spread = None
        
        else:
            # Entry logic - Adapt to market conditions
            volume_confirm = current_volume > (volume_avg * self.volume_threshold)
            
            # Determine market quality for entry
            good_trend_long = current_adx > self.adx_trending and current_plus_di > current_minus_di
            good_trend_short = current_adx > self.adx_trending and current_minus_di > current_plus_di
            good_range = current_adx < self.adx_ranging and di_spread < 10  # Low DI spread in range
            
            # Long entry - Lower band touch with directional confirmation
            if (current_low <= current_lower and  # Low touched lower band
                current_price > current_lower and  # Closing above it
                (good_trend_long or good_range) and  # Good market conditions
                volume_confirm):  # Volume confirmation
                
                # Larger position in strong trends
                if current_adx > self.adx_strong_trend:
                    self.buy(size=1.3)
                else:
                    self.buy()
                
                self.entry_price = current_price
                self.is_long = True
                self.entry_adx = current_adx
                self.entry_di_spread = di_spread
            
            # Short entry - Upper band touch with directional confirmation
            elif (current_high >= current_upper and  # High touched upper band
                  current_price < current_upper and  # Closing below it
                  (good_trend_short or good_range) and  # Good market conditions
                  volume_confirm):  # Volume confirmation
                
                # Larger position in strong trends
                if current_adx > self.adx_strong_trend:
                    self.sell(size=1.3)
                else:
                    self.sell()
                
                self.entry_price = current_price
                self.is_long = False
                self.entry_adx = current_adx
                self.entry_di_spread = di_spread

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING NADARAYA-WATSON ENVELOPE + ADX STRATEGY ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    results = test_on_all_data(NadarayaWatsonEnvelopeADX, 'NadarayaWatsonEnvelopeADX')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/NadarayaWatsonEnvelopeADX.csv")