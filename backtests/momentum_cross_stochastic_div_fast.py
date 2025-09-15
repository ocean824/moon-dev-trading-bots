"""
Momentum Crossover - Stochastic Divergence Strategy (OPTIMIZED VERSION)
Uses vectorized operations for fast pivot detection
"""

from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import pandas as pd
import numpy as np
import pandas_ta as ta
from scipy.signal import argrelextrema

class MomentumCrossStochasticDivFast(Strategy):
    # Stochastic parameters
    stoch_k_period = 14
    stoch_d_period = 3
    stoch_smooth = 3
    
    # Divergence detection
    lookback_period = 20
    
    # Risk management
    atr_period = 14
    stop_loss_atr = 2.0
    take_profit_atr = 3.0
    trailing_stop_atr = 1.5
    
    # Volume confirmation
    volume_period = 20
    volume_multiplier = 1.5
    
    def find_pivot_highs_lows_fast(self, data, order=5):
        """Find pivot highs and lows using scipy for MUCH faster performance"""
        # Remove NaN values for processing
        valid_mask = ~np.isnan(data)
        valid_data = data[valid_mask]
        valid_indices = np.where(valid_mask)[0]
        
        if len(valid_data) < order * 2:
            return [], []
        
        # Use scipy's argrelextrema for efficient pivot detection
        highs = argrelextrema(valid_data, np.greater, order=order)[0]
        lows = argrelextrema(valid_data, np.less, order=order)[0]
        
        # Map back to original indices
        high_indices = valid_indices[highs] if len(highs) > 0 else []
        low_indices = valid_indices[lows] if len(lows) > 0 else []
        
        return high_indices.tolist(), low_indices.tolist()
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Calculate Stochastic oscillator
        stoch = ta.stoch(high, low, close, 
                         k=self.stoch_k_period, 
                         d=self.stoch_d_period, 
                         smooth_k=self.stoch_smooth)
        
        # Extract %K and %D lines
        stoch_k = stoch[f'STOCHk_{self.stoch_k_period}_{self.stoch_d_period}_{self.stoch_smooth}']
        stoch_d = stoch[f'STOCHd_{self.stoch_k_period}_{self.stoch_d_period}_{self.stoch_smooth}']
        
        # Ensure arrays are same length as data
        stoch_k_full = np.full(len(close), np.nan)
        stoch_d_full = np.full(len(close), np.nan)
        stoch_k_full[-len(stoch_k):] = stoch_k.values
        stoch_d_full[-len(stoch_d):] = stoch_d.values
        
        self.stoch_k = self.I(lambda: stoch_k_full, name='Stoch_K')
        self.stoch_d = self.I(lambda: stoch_d_full, name='Stoch_D')
        
        # Previous values for crossover detection
        stoch_k_prev = np.roll(stoch_k_full, 1)
        stoch_d_prev = np.roll(stoch_d_full, 1)
        stoch_k_prev[0] = np.nan
        stoch_d_prev[0] = np.nan
        
        self.stoch_k_prev = self.I(lambda: stoch_k_prev, name='Stoch_K_Prev')
        self.stoch_d_prev = self.I(lambda: stoch_d_prev, name='Stoch_D_Prev')
        
        # Find pivot points using FAST method
        self.price_pivot_highs, self.price_pivot_lows = self.find_pivot_highs_lows_fast(close.values, order=5)
        self.stoch_pivot_highs, self.stoch_pivot_lows = self.find_pivot_highs_lows_fast(stoch_k_full, order=5)
        
        # Volume average for confirmation
        volume_avg = ta.sma(volume, self.volume_period)
        self.volume_avg = self.I(lambda: volume_avg.values, name='Volume_Avg')
        
        # Volume spike detection
        volume_spike = volume / volume_avg > self.volume_multiplier
        self.volume_spike = self.I(lambda: volume_spike.values, name='Volume_Spike')
        
        # ATR for stops
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # Track highest/lowest prices for trailing stops
        self.highest_price = 0
        self.lowest_price = float('inf')
        
        # Track recent divergences
        self.recent_bullish_div = False
        self.recent_bearish_div = False
        self.div_signal_bar = 0
    
    def detect_divergence(self, current_idx):
        """Detect bullish and bearish divergences (simplified for speed)"""
        if current_idx < self.lookback_period * 2:
            return False, False
        
        price = self.data.Close[-1]
        stoch_k = self.stoch_k[-1]
        
        if np.isnan(stoch_k):
            return False, False
        
        bullish_div = False
        bearish_div = False
        
        # Look for recent pivot lows for bullish divergence
        recent_price_lows = [idx for idx in self.price_pivot_lows 
                            if current_idx - self.lookback_period <= idx < current_idx - 3]
        recent_stoch_lows = [idx for idx in self.stoch_pivot_lows 
                            if current_idx - self.lookback_period <= idx < current_idx - 3]
        
        if recent_price_lows and recent_stoch_lows:
            # Get the most recent pivot low
            last_price_low_idx = recent_price_lows[-1]
            last_price_low = self.data.Close[last_price_low_idx]
            
            # Find corresponding stochastic low (simplified matching)
            if recent_stoch_lows:
                closest_stoch_idx = recent_stoch_lows[-1]
                last_stoch_low = self.stoch_k[closest_stoch_idx]
                
                # Bullish divergence: price makes lower low, stoch makes higher low
                if price < last_price_low and stoch_k > last_stoch_low:
                    bullish_div = True
        
        # Look for recent pivot highs for bearish divergence
        recent_price_highs = [idx for idx in self.price_pivot_highs 
                             if current_idx - self.lookback_period <= idx < current_idx - 3]
        recent_stoch_highs = [idx for idx in self.stoch_pivot_highs 
                             if current_idx - self.lookback_period <= idx < current_idx - 3]
        
        if recent_price_highs and recent_stoch_highs:
            # Get the most recent pivot high
            last_price_high_idx = recent_price_highs[-1]
            last_price_high = self.data.Close[last_price_high_idx]
            
            # Find corresponding stochastic high (simplified matching)
            if recent_stoch_highs:
                closest_stoch_idx = recent_stoch_highs[-1]
                last_stoch_high = self.stoch_k[closest_stoch_idx]
                
                # Bearish divergence: price makes higher high, stoch makes lower high
                if price > last_price_high and stoch_k < last_stoch_high:
                    bearish_div = True
        
        return bullish_div, bearish_div
    
    def next(self):
        # Skip if not enough data or NaN values
        if len(self.data) < self.lookback_period * 2:
            return
        
        if np.isnan(self.stoch_k[-1]) or np.isnan(self.stoch_d[-1]):
            return
        
        if np.isnan(self.atr[-1]):
            return
        
        current_idx = len(self.data) - 1
        price = self.data.Close[-1]
        
        # Detect divergences
        bullish_div, bearish_div = self.detect_divergence(current_idx)
        
        # Store divergence signals
        if bullish_div:
            self.recent_bullish_div = True
            self.div_signal_bar = current_idx
        elif bearish_div:
            self.recent_bearish_div = True
            self.div_signal_bar = current_idx
        
        # Clear old divergence signals (after 5 bars)
        if current_idx - self.div_signal_bar > 5:
            self.recent_bullish_div = False
            self.recent_bearish_div = False
        
        # Entry signals
        stoch_oversold = self.stoch_k[-1] < 20
        stoch_overbought = self.stoch_k[-1] > 80
        
        # Stochastic crossovers
        bullish_cross = (self.stoch_k_prev[-1] <= self.stoch_d_prev[-1] and 
                        self.stoch_k[-1] > self.stoch_d[-1])
        bearish_cross = (self.stoch_k_prev[-1] >= self.stoch_d_prev[-1] and 
                        self.stoch_k[-1] < self.stoch_d[-1])
        
        # Volume confirmation
        volume_confirmed = self.volume_spike[-1] if not np.isnan(self.volume_spike[-1]) else False
        
        # Position management
        if self.position:
            # Update trailing stops
            if self.position.is_long:
                self.highest_price = max(self.highest_price, price)
                trailing_stop = self.highest_price - self.trailing_stop_atr * self.atr[-1]
                
                # Exit conditions for long
                if (bearish_cross and stoch_overbought) or self.recent_bearish_div:
                    self.position.close()
                    self.highest_price = 0
                elif price <= trailing_stop:
                    self.position.close()
                    self.highest_price = 0
            
            elif self.position.is_short:
                self.lowest_price = min(self.lowest_price, price)
                trailing_stop = self.lowest_price + self.trailing_stop_atr * self.atr[-1]
                
                # Exit conditions for short
                if (bullish_cross and stoch_oversold) or self.recent_bullish_div:
                    self.position.close()
                    self.lowest_price = float('inf')
                elif price >= trailing_stop:
                    self.position.close()
                    self.lowest_price = float('inf')
        
        else:
            # Entry signals
            # Long entry: Bullish divergence or oversold crossover with volume
            if (self.recent_bullish_div or (bullish_cross and stoch_oversold)) and volume_confirmed:
                stop_loss = price - self.stop_loss_atr * self.atr[-1]
                take_profit = price + self.take_profit_atr * self.atr[-1]
                
                self.buy(sl=stop_loss, tp=take_profit)
                self.highest_price = price
            
            # Short entry: Bearish divergence or overbought crossover with volume
            elif (self.recent_bearish_div or (bearish_cross and stoch_overbought)) and volume_confirmed:
                stop_loss = price + self.stop_loss_atr * self.atr[-1]
                take_profit = price - self.take_profit_atr * self.atr[-1]
                
                self.sell(sl=stop_loss, tp=take_profit)
                self.lowest_price = price

# Multi-data testing integration
if __name__ == '__main__':
    from multi_data_tester import test_on_all_data
    
    # Test the strategy
    test_on_all_data(MomentumCrossStochasticDivFast)