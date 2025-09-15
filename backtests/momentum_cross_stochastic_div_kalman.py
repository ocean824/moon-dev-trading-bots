"""
Moon Dev's Momentum Cross Stochastic Divergence Kalman Strategy
================================================================
Stochastic Divergence with Kalman Filter for cleaner signals
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class MomentumCrossStochasticDivKalmanStrategy(Strategy):
    """
    Stochastic Divergence with Kalman Filter
    - Same as stochastic divergence strategy but use Kalman filtered prices
    - Should provide cleaner divergence signals
    - Reduces noise in oscillator calculations
    """
    
    # Stochastic parameters
    stoch_k_period = 14
    stoch_d_period = 3
    stoch_smooth = 3
    
    # Kalman filter parameters
    kalman_gain = 0.12  # Moderate gain for balance between smoothing and responsiveness
    
    # Divergence detection
    lookback_period = 20
    divergence_threshold = 0.02
    
    # Risk management
    atr_period = 14
    atr_sl_multiplier = 2.0
    trailing_stop_pct = 0.025
    
    # Volume confirmation
    volume_period = 20
    volume_multiplier = 1.2
    
    def kalman_filter(self, data, gain=0.12):
        """Apply Kalman filter to smooth data"""
        filtered = np.zeros_like(data)
        filtered[0] = data[0] if not pd.isna(data[0]) else 0
        
        for i in range(1, len(data)):
            if pd.isna(data[i]):
                filtered[i] = filtered[i-1]
            else:
                filtered[i] = filtered[i-1] + gain * (data[i] - filtered[i-1])
        
        return filtered
    
    def find_pivot_highs_lows(self, data, lookback):
        """Find pivot highs and lows in data"""
        highs = []
        lows = []
        
        for i in range(lookback, len(data) - lookback):
            # Check if current point is a pivot high
            is_high = all(data[i] >= data[j] for j in range(i - lookback, i + lookback + 1) if j != i)
            if is_high:
                highs.append(i)
            
            # Check if current point is a pivot low
            is_low = all(data[i] <= data[j] for j in range(i - lookback, i + lookback + 1) if j != i)
            if is_low:
                lows.append(i)
        
        return highs, lows
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        
        # Apply Kalman filter to high, low, and close
        high_filtered = self.kalman_filter(high.values, self.kalman_gain)
        low_filtered = self.kalman_filter(low.values, self.kalman_gain)
        close_filtered = self.kalman_filter(close.values, self.kalman_gain)
        
        # Convert back to series
        high_kalman = pd.Series(high_filtered, index=high.index)
        low_kalman = pd.Series(low_filtered, index=low.index)
        close_kalman = pd.Series(close_filtered, index=close.index)
        
        # Calculate Stochastic oscillator on filtered data
        stoch = ta.stoch(high_kalman, low_kalman, close_kalman,
                         k=self.stoch_k_period,
                         d=self.stoch_d_period,
                         smooth_k=self.stoch_smooth)
        
        # Extract %K and %D lines
        stoch_k = stoch[f'STOCHk_{self.stoch_k_period}_{self.stoch_d_period}_{self.stoch_smooth}']
        stoch_d = stoch[f'STOCHd_{self.stoch_k_period}_{self.stoch_d_period}_{self.stoch_smooth}']
        
        # Apply additional Kalman smoothing to stochastic itself
        stoch_k_smoothed = self.kalman_filter(stoch_k.values, gain=0.15)
        stoch_d_smoothed = self.kalman_filter(stoch_d.values, gain=0.15)
        
        # Ensure arrays are same length as data
        stoch_k_full = np.full(len(close), np.nan)
        stoch_d_full = np.full(len(close), np.nan)
        stoch_k_full[-len(stoch_k_smoothed):] = stoch_k_smoothed
        stoch_d_full[-len(stoch_d_smoothed):] = stoch_d_smoothed
        
        self.stoch_k = self.I(lambda: stoch_k_full, name='Stoch_K_Kalman')
        self.stoch_d = self.I(lambda: stoch_d_full, name='Stoch_D_Kalman')
        
        # Store Kalman filtered close for divergence detection
        self.close_kalman = close_kalman.values
        
        # Previous values for crossover detection
        stoch_k_prev = np.roll(stoch_k_full, 1)
        stoch_d_prev = np.roll(stoch_d_full, 1)
        stoch_k_prev[0] = np.nan
        stoch_d_prev[0] = np.nan
        
        self.stoch_k_prev = self.I(lambda: stoch_k_prev, name='Stoch_K_Prev')
        self.stoch_d_prev = self.I(lambda: stoch_d_prev, name='Stoch_D_Prev')
        
        # Find pivot points in filtered price and stochastic
        pivot_lookback = 5
        price_highs, price_lows = self.find_pivot_highs_lows(close_kalman.values, pivot_lookback)
        stoch_highs, stoch_lows = self.find_pivot_highs_lows(stoch_k_full, pivot_lookback)
        
        # Store pivot points
        self.price_pivot_highs = price_highs
        self.price_pivot_lows = price_lows
        self.stoch_pivot_highs = stoch_highs
        self.stoch_pivot_lows = stoch_lows
        
        # Volume average for confirmation
        volume_avg = ta.sma(volume, self.volume_period)
        self.volume_avg = self.I(lambda: volume_avg.values, name='Volume_Avg')
        
        # Volume spike detection
        volume_spike = volume / volume_avg > self.volume_multiplier
        self.volume_spike = self.I(lambda: volume_spike.values, name='Volume_Spike')
        
        # ATR for stops (use raw data for actual volatility)
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # Track highest/lowest prices for trailing stops
        self.highest_price = 0
        self.lowest_price = float('inf')
        
        # Track recent divergences
        self.recent_bullish_div = False
        self.recent_bearish_div = False
        self.div_signal_bar = 0
        self.div_strength = 0  # Track divergence strength
    
    def detect_divergence(self, current_idx):
        """Detect bullish and bearish divergences with Kalman filtered data"""
        if current_idx < self.lookback_period * 2:
            return False, False, 0
        
        price = self.close_kalman[current_idx] if current_idx < len(self.close_kalman) else self.data.Close[-1]
        stoch_k = self.stoch_k[-1]
        
        bullish_div = False
        bearish_div = False
        div_strength = 0
        
        # Look for recent pivot lows for bullish divergence
        recent_price_lows = [idx for idx in self.price_pivot_lows if current_idx - self.lookback_period <= idx < current_idx - 3]
        recent_stoch_lows = [idx for idx in self.stoch_pivot_lows if current_idx - self.lookback_period <= idx < current_idx - 3]
        
        if recent_price_lows and recent_stoch_lows:
            # Get the most recent pivot low
            last_price_low_idx = recent_price_lows[-1]
            last_price_low = self.close_kalman[last_price_low_idx]
            
            # Find corresponding stochastic low
            closest_stoch_idx = min(recent_stoch_lows, key=lambda x: abs(x - last_price_low_idx))
            last_stoch_low = self.stoch_k[closest_stoch_idx]
            
            # Check for bullish divergence
            price_diff_pct = (price - last_price_low) / last_price_low
            stoch_diff = stoch_k - last_stoch_low
            
            if price < last_price_low and stoch_k > last_stoch_low:
                if abs(price_diff_pct) > self.divergence_threshold:
                    bullish_div = True
                    div_strength = abs(stoch_diff)  # Strength of divergence
        
        # Look for recent pivot highs for bearish divergence
        recent_price_highs = [idx for idx in self.price_pivot_highs if current_idx - self.lookback_period <= idx < current_idx - 3]
        recent_stoch_highs = [idx for idx in self.stoch_pivot_highs if current_idx - self.lookback_period <= idx < current_idx - 3]
        
        if recent_price_highs and recent_stoch_highs:
            # Get the most recent pivot high
            last_price_high_idx = recent_price_highs[-1]
            last_price_high = self.close_kalman[last_price_high_idx]
            
            # Find corresponding stochastic high
            closest_stoch_idx = min(recent_stoch_highs, key=lambda x: abs(x - last_price_high_idx))
            last_stoch_high = self.stoch_k[closest_stoch_idx]
            
            # Check for bearish divergence
            price_diff_pct = (price - last_price_high) / last_price_high
            stoch_diff = last_stoch_high - stoch_k
            
            if price > last_price_high and stoch_k < last_stoch_high:
                if abs(price_diff_pct) > self.divergence_threshold:
                    bearish_div = True
                    div_strength = abs(stoch_diff)  # Strength of divergence
        
        return bullish_div, bearish_div, div_strength
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.stoch_k_period, self.volume_period, self.atr_period, self.lookback_period * 2) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        stoch_k_curr = self.stoch_k[-1]
        stoch_d_curr = self.stoch_d[-1]
        stoch_k_prev = self.stoch_k_prev[-1]
        stoch_d_prev = self.stoch_d_prev[-1]
        
        volume_confirmed = self.volume_spike[-1] if not pd.isna(self.volume_spike[-1]) else False
        atr_value = self.atr[-1]
        
        # Check for valid values
        if pd.isna(stoch_k_curr) or pd.isna(stoch_d_curr) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Current index for divergence detection
        current_idx = len(self.data.Close) - 1
        
        # Detect divergences with Kalman filtered data
        bullish_div, bearish_div, div_strength = self.detect_divergence(current_idx)
        
        # Update divergence tracking
        if bullish_div:
            self.recent_bullish_div = True
            self.div_signal_bar = current_idx
            self.div_strength = div_strength
        if bearish_div:
            self.recent_bearish_div = True
            self.div_signal_bar = current_idx
            self.div_strength = div_strength
        
        # Clear old divergence signals (after 5 bars)
        if current_idx - self.div_signal_bar > 5:
            self.recent_bullish_div = False
            self.recent_bearish_div = False
            self.div_strength = 0
        
        # Stochastic crossovers (cleaner with Kalman)
        stoch_cross_up = (stoch_k_prev <= stoch_d_prev) and (stoch_k_curr > stoch_d_curr)
        stoch_cross_down = (stoch_k_prev >= stoch_d_prev) and (stoch_k_curr < stoch_d_curr)
        
        # Oversold/overbought levels
        oversold = stoch_k_curr < 20
        overbought = stoch_k_curr > 80
        
        # Momentum confirmation (smoother with Kalman)
        stoch_momentum_up = stoch_k_curr > stoch_k_prev and stoch_d_curr > stoch_d_prev
        stoch_momentum_down = stoch_k_curr < stoch_k_prev and stoch_d_curr < stoch_d_prev
        
        # Strong divergence requires higher strength threshold with Kalman
        strong_divergence = self.div_strength > 5  # Minimum 5 point divergence in stochastic
        
        # Long signal: Bullish divergence with confirmation
        long_signal = (
            (self.recent_bullish_div and strong_divergence and 
             (stoch_cross_up or (oversold and stoch_momentum_up))) or
            (oversold and stoch_cross_up and volume_confirmed and stoch_momentum_up)
        )
        
        # Short signal: Bearish divergence with confirmation
        short_signal = (
            (self.recent_bearish_div and strong_divergence and 
             (stoch_cross_down or (overbought and stoch_momentum_down))) or
            (overbought and stoch_cross_down and volume_confirmed and stoch_momentum_down)
        )
        
        # Execute trades
        if long_signal:
            if self.position.is_short:
                self.position.close()
            if not self.position:
                stop_loss = price - (atr_value * self.atr_sl_multiplier)
                self.buy(sl=stop_loss)
                self.highest_price = price
                self.recent_bullish_div = False  # Reset after entry
        
        elif short_signal:
            if self.position.is_long:
                self.position.close()
            if not self.position:
                stop_loss = price + (atr_value * self.atr_sl_multiplier)
                self.sell(sl=stop_loss)
                self.lowest_price = price
                self.recent_bearish_div = False  # Reset after entry
        
        # Implement trailing stops and momentum exits
        if self.position:
            if self.position.is_long:
                # Update highest price
                if price > self.highest_price:
                    self.highest_price = price
                
                # Check trailing stop
                trailing_stop = self.highest_price * (1 - self.trailing_stop_pct)
                if price < trailing_stop:
                    self.position.close()
                
                # Exit on bearish stochastic crossover in overbought zone
                if stoch_cross_down and stoch_k_curr > 70:
                    self.position.close()
                
                # Exit if stochastic loses momentum (Kalman smoothed)
                if stoch_k_curr < 50 and not stoch_momentum_up:
                    self.position.close()
            
            elif self.position.is_short:
                # Update lowest price
                if price < self.lowest_price:
                    self.lowest_price = price
                
                # Check trailing stop
                trailing_stop = self.lowest_price * (1 + self.trailing_stop_pct)
                if price > trailing_stop:
                    self.position.close()
                
                # Exit on bullish stochastic crossover in oversold zone
                if stoch_cross_up and stoch_k_curr < 30:
                    self.position.close()
                
                # Exit if stochastic loses momentum (Kalman smoothed)
                if stoch_k_curr > 50 and not stoch_momentum_down:
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S MOMENTUM CROSS STOCHASTIC DIVERGENCE KALMAN STRATEGY")
    print("="*80)
    print("Testing Stochastic Divergence with Kalman Filter across all datasets...")
    print("="*80)
    
    # Run tests on all data sources without optimization
    results = test_on_all_data(
        MomentumCrossStochasticDivKalmanStrategy,
        'MomentumCrossStochasticDivKalman',
        optimize=False,  # No optimization as requested
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/MomentumCrossStochasticDivKalman.csv")
        print("="*80)

if __name__ == "__main__":
    main()