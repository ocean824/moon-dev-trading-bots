"""
Moon Dev's Momentum Cross Stochastic Divergence Strategy
=========================================================
Stochastic Divergence Strategy with price/oscillator divergence detection
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class MomentumCrossStochasticDivStrategy(Strategy):
    """
    Stochastic Divergence Strategy
    - Calculate Stochastic oscillator (14, 3, 3 periods standard)
    - Detect divergences between price and Stochastic
    - Bullish divergence: price makes lower lows, Stochastic makes higher lows
    - Bearish divergence: price makes higher highs, Stochastic makes lower highs
    - Enter on divergence confirmation with appropriate stops
    """
    
    # Stochastic parameters
    stoch_k_period = 14
    stoch_d_period = 3
    stoch_smooth = 3
    
    # Divergence detection
    lookback_period = 20  # Look back for highs/lows
    divergence_threshold = 0.02  # 2% minimum price difference for divergence
    
    # Risk management
    atr_period = 14
    atr_sl_multiplier = 2.0
    trailing_stop_pct = 0.025
    
    # Volume confirmation
    volume_period = 20
    volume_multiplier = 1.2
    
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
        
        # Find pivot points in price and stochastic
        pivot_lookback = 5
        price_highs, price_lows = self.find_pivot_highs_lows(close.values, pivot_lookback)
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
        """Detect bullish and bearish divergences"""
        if current_idx < self.lookback_period * 2:
            return False, False
        
        price = self.data.Close[-1]
        stoch_k = self.stoch_k[-1]
        
        bullish_div = False
        bearish_div = False
        
        # Look for recent pivot lows for bullish divergence
        recent_price_lows = [idx for idx in self.price_pivot_lows if current_idx - self.lookback_period <= idx < current_idx - 3]
        recent_stoch_lows = [idx for idx in self.stoch_pivot_lows if current_idx - self.lookback_period <= idx < current_idx - 3]
        
        if recent_price_lows and recent_stoch_lows:
            # Get the most recent pivot low
            last_price_low_idx = recent_price_lows[-1]
            last_price_low = self.data.Close[last_price_low_idx]
            
            # Find corresponding stochastic low
            closest_stoch_idx = min(recent_stoch_lows, key=lambda x: abs(x - last_price_low_idx))
            last_stoch_low = self.stoch_k[closest_stoch_idx]
            
            # Check for bullish divergence
            price_diff_pct = (price - last_price_low) / last_price_low
            if price < last_price_low and stoch_k > last_stoch_low:
                if abs(price_diff_pct) > self.divergence_threshold:
                    bullish_div = True
        
        # Look for recent pivot highs for bearish divergence
        recent_price_highs = [idx for idx in self.price_pivot_highs if current_idx - self.lookback_period <= idx < current_idx - 3]
        recent_stoch_highs = [idx for idx in self.stoch_pivot_highs if current_idx - self.lookback_period <= idx < current_idx - 3]
        
        if recent_price_highs and recent_stoch_highs:
            # Get the most recent pivot high
            last_price_high_idx = recent_price_highs[-1]
            last_price_high = self.data.Close[last_price_high_idx]
            
            # Find corresponding stochastic high
            closest_stoch_idx = min(recent_stoch_highs, key=lambda x: abs(x - last_price_high_idx))
            last_stoch_high = self.stoch_k[closest_stoch_idx]
            
            # Check for bearish divergence
            price_diff_pct = (price - last_price_high) / last_price_high
            if price > last_price_high and stoch_k < last_stoch_high:
                if abs(price_diff_pct) > self.divergence_threshold:
                    bearish_div = True
        
        return bullish_div, bearish_div
    
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
        
        # Detect divergences
        bullish_div, bearish_div = self.detect_divergence(current_idx)
        
        # Update divergence tracking
        if bullish_div:
            self.recent_bullish_div = True
            self.div_signal_bar = current_idx
        if bearish_div:
            self.recent_bearish_div = True
            self.div_signal_bar = current_idx
        
        # Clear old divergence signals (after 5 bars)
        if current_idx - self.div_signal_bar > 5:
            self.recent_bullish_div = False
            self.recent_bearish_div = False
        
        # Stochastic crossovers
        stoch_cross_up = (stoch_k_prev <= stoch_d_prev) and (stoch_k_curr > stoch_d_curr)
        stoch_cross_down = (stoch_k_prev >= stoch_d_prev) and (stoch_k_curr < stoch_d_curr)
        
        # Oversold/overbought levels
        oversold = stoch_k_curr < 20
        overbought = stoch_k_curr > 80
        
        # Long signal: Bullish divergence confirmed by stochastic crossover or oversold bounce
        long_signal = (
            (self.recent_bullish_div and (stoch_cross_up or (oversold and stoch_k_curr > stoch_k_prev))) or
            (oversold and stoch_cross_up and volume_confirmed)
        )
        
        # Short signal: Bearish divergence confirmed by stochastic crossover or overbought reversal
        short_signal = (
            (self.recent_bearish_div and (stoch_cross_down or (overbought and stoch_k_curr < stoch_k_prev))) or
            (overbought and stoch_cross_down and volume_confirmed)
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
                
                # Exit if stochastic drops below 50 after being above 80
                if stoch_k_prev > 80 and stoch_k_curr < 50:
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
                
                # Exit if stochastic rises above 50 after being below 20
                if stoch_k_prev < 20 and stoch_k_curr > 50:
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S MOMENTUM CROSS STOCHASTIC DIVERGENCE STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Stochastic Divergence across all datasets...")
    print("="*80)
    
    # Run tests on all data sources without optimization
    results = test_on_all_data(
        MomentumCrossStochasticDivStrategy,
        'MomentumCrossStochasticDiv',
        optimize=False,  # No optimization as requested
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/MomentumCrossStochasticDiv.csv")
        print("="*80)

if __name__ == "__main__":
    main()