"""
Momentum Crossover - Stochastic Divergence with Kalman Filter (OPTIMIZED VERSION)
Uses vectorized operations for fast pivot detection and Kalman smoothing
"""

from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import pandas as pd
import numpy as np
import pandas_ta as ta
from scipy.signal import argrelextrema

class MomentumCrossStochasticDivKalmanFast(Strategy):
    # Stochastic parameters
    stoch_k_period = 14
    stoch_d_period = 3
    stoch_smooth = 3
    
    # Kalman filter
    kalman_gain = 0.12
    
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
    
    def kalman_filter_vectorized(self, data, gain=0.12):
        """Vectorized Kalman filter for better performance"""
        filtered = np.empty_like(data)
        filtered[0] = data[0] if not pd.isna(data[0]) else 0
        
        # Vectorized approach using cumulative operations
        mask = ~pd.isna(data)
        for i in range(1, len(data)):
            if mask[i]:
                filtered[i] = filtered[i-1] + gain * (data[i] - filtered[i-1])
            else:
                filtered[i] = filtered[i-1]
        
        return filtered
    
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
        
        # Apply Kalman filter to smooth prices
        close_kalman = self.kalman_filter_vectorized(close.values, self.kalman_gain)
        high_kalman = self.kalman_filter_vectorized(high.values, self.kalman_gain)
        low_kalman = self.kalman_filter_vectorized(low.values, self.kalman_gain)
        
        # Convert back to Series for pandas_ta
        close_smooth = pd.Series(close_kalman, index=close.index)
        high_smooth = pd.Series(high_kalman, index=high.index)
        low_smooth = pd.Series(low_kalman, index=low.index)
        
        # Calculate Stochastic oscillator on smoothed data
        stoch = ta.stoch(high_smooth, low_smooth, close_smooth, 
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
        
        # Apply additional Kalman smoothing to stochastic
        stoch_k_smooth = self.kalman_filter_vectorized(stoch_k_full, self.kalman_gain * 0.5)
        stoch_d_smooth = self.kalman_filter_vectorized(stoch_d_full, self.kalman_gain * 0.5)
        
        self.stoch_k = self.I(lambda: stoch_k_smooth, name='Stoch_K_Kalman')
        self.stoch_d = self.I(lambda: stoch_d_smooth, name='Stoch_D_Kalman')
        
        # Store smoothed close for signals
        self.close_kalman = self.I(lambda: close_kalman, name='Close_Kalman')
        
        # Previous values for crossover detection
        stoch_k_prev = np.roll(stoch_k_smooth, 1)
        stoch_d_prev = np.roll(stoch_d_smooth, 1)
        stoch_k_prev[0] = np.nan
        stoch_d_prev[0] = np.nan
        
        self.stoch_k_prev = self.I(lambda: stoch_k_prev, name='Stoch_K_Prev')
        self.stoch_d_prev = self.I(lambda: stoch_d_prev, name='Stoch_D_Prev')
        
        # Find pivot points using FAST method on Kalman filtered data
        self.price_pivot_highs, self.price_pivot_lows = self.find_pivot_highs_lows_fast(close_kalman, order=5)
        self.stoch_pivot_highs, self.stoch_pivot_lows = self.find_pivot_highs_lows_fast(stoch_k_smooth, order=5)
        
        # Volume average for confirmation
        volume_avg = ta.sma(volume, self.volume_period)
        self.volume_avg = self.I(lambda: volume_avg.values, name='Volume_Avg')
        
        # Volume spike detection with Kalman smoothing
        volume_ratio = volume / volume_avg
        volume_ratio_smooth = self.kalman_filter_vectorized(volume_ratio.values, self.kalman_gain)
        volume_spike = volume_ratio_smooth > self.volume_multiplier
        self.volume_spike = self.I(lambda: volume_spike, name='Volume_Spike')
        
        # ATR for stops (on smoothed data)
        self.atr = self.I(ta.atr, high_smooth, low_smooth, close_smooth, self.atr_period)
        
        # Track highest/lowest prices for trailing stops
        self.highest_price = 0
        self.lowest_price = float('inf')
        
        # Track recent divergences
        self.recent_bullish_div = False
        self.recent_bearish_div = False
        self.div_signal_bar = 0
        
        # Momentum confirmation
        self.momentum_threshold = 0.5
    
    def detect_divergence(self, current_idx):
        """Detect bullish and bearish divergences with Kalman smoothed data"""
        if current_idx < self.lookback_period * 2:
            return False, False
        
        price = self.close_kalman[-1]
        stoch_k = self.stoch_k[-1]
        
        if np.isnan(stoch_k) or np.isnan(price):
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
            last_price_low = self.close_kalman[last_price_low_idx]
            
            # Find corresponding stochastic low (simplified matching)
            if recent_stoch_lows:
                closest_stoch_idx = recent_stoch_lows[-1]
                last_stoch_low = self.stoch_k[closest_stoch_idx]
                
                # Bullish divergence: price makes lower low, stoch makes higher low
                # With Kalman, require stronger divergence
                if price < last_price_low * 0.998 and stoch_k > last_stoch_low + 2:
                    bullish_div = True
        
        # Look for recent pivot highs for bearish divergence
        recent_price_highs = [idx for idx in self.price_pivot_highs 
                             if current_idx - self.lookback_period <= idx < current_idx - 3]
        recent_stoch_highs = [idx for idx in self.stoch_pivot_highs 
                             if current_idx - self.lookback_period <= idx < current_idx - 3]
        
        if recent_price_highs and recent_stoch_highs:
            # Get the most recent pivot high
            last_price_high_idx = recent_price_highs[-1]
            last_price_high = self.close_kalman[last_price_high_idx]
            
            # Find corresponding stochastic high (simplified matching)
            if recent_stoch_highs:
                closest_stoch_idx = recent_stoch_highs[-1]
                last_stoch_high = self.stoch_k[closest_stoch_idx]
                
                # Bearish divergence: price makes higher high, stoch makes lower high
                # With Kalman, require stronger divergence
                if price > last_price_high * 1.002 and stoch_k < last_stoch_high - 2:
                    bearish_div = True
        
        return bullish_div, bearish_div
    
    def next(self):
        # Skip if not enough data or NaN values
        if len(self.data) < self.lookback_period * 2:
            return
        
        if np.isnan(self.stoch_k[-1]) or np.isnan(self.stoch_d[-1]):
            return
        
        if np.isnan(self.atr[-1]) or np.isnan(self.close_kalman[-1]):
            return
        
        current_idx = len(self.data) - 1
        price = self.data.Close[-1]
        smooth_price = self.close_kalman[-1]
        
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
        
        # Entry signals with Kalman smoothed thresholds
        stoch_oversold = self.stoch_k[-1] < 25  # Slightly higher threshold with smoothing
        stoch_overbought = self.stoch_k[-1] > 75  # Slightly lower threshold with smoothing
        
        # Stochastic crossovers
        bullish_cross = (self.stoch_k_prev[-1] <= self.stoch_d_prev[-1] and 
                        self.stoch_k[-1] > self.stoch_d[-1])
        bearish_cross = (self.stoch_k_prev[-1] >= self.stoch_d_prev[-1] and 
                        self.stoch_k[-1] < self.stoch_d[-1])
        
        # Volume confirmation (already smoothed)
        volume_confirmed = self.volume_spike[-1] if not np.isnan(self.volume_spike[-1]) else False
        
        # Check momentum strength
        if current_idx > 5:
            momentum = (smooth_price - self.close_kalman[-5]) / self.close_kalman[-5] * 100
            strong_momentum = abs(momentum) > self.momentum_threshold
        else:
            strong_momentum = False
        
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
            # Entry signals with Kalman confirmation
            # Long entry: Bullish divergence or oversold crossover with volume and momentum
            if (self.recent_bullish_div or (bullish_cross and stoch_oversold)) and (volume_confirmed or strong_momentum):
                stop_loss = price - self.stop_loss_atr * self.atr[-1]
                take_profit = price + self.take_profit_atr * self.atr[-1]
                
                self.buy(sl=stop_loss, tp=take_profit)
                self.highest_price = price
            
            # Short entry: Bearish divergence or overbought crossover with volume and momentum
            elif (self.recent_bearish_div or (bearish_cross and stoch_overbought)) and (volume_confirmed or strong_momentum):
                stop_loss = price + self.stop_loss_atr * self.atr[-1]
                take_profit = price - self.take_profit_atr * self.atr[-1]
                
                self.sell(sl=stop_loss, tp=take_profit)
                self.lowest_price = price

# Multi-data testing integration
if __name__ == '__main__':
    from multi_data_tester import test_on_all_data
    
    # Test the strategy
    test_on_all_data(MomentumCrossStochasticDivKalmanFast)