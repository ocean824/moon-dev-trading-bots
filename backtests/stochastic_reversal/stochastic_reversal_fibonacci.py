"""
Moon Dev's Stochastic Reversal Fibonacci Strategy
==================================================
Stochastic Reversal with Fibonacci retracement levels.
Combines oversold/overbought with key Fib levels for precision entries.
Tests across all datasets with comprehensive stats output.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class StochasticReversalFibonacci(Strategy):
    """
    Stochastic Reversal Strategy with Fibonacci Retracements
    - Stochastic identifies overbought/oversold conditions
    - Fibonacci retracements provide key support/resistance levels
    - Enter reversals at confluence of Stochastic signal and Fib level
    - Dynamic Fib calculations based on recent swings
    """
    
    # Stochastic parameters
    stoch_k_period = 14
    stoch_d_period = 3
    stoch_smooth = 3
    overbought_level = 80
    oversold_level = 20
    
    # Fibonacci parameters
    fib_lookback = 50  # Bars to look back for swing high/low
    fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]  # Key Fibonacci levels
    fib_tolerance = 0.005  # 0.5% tolerance for level touches
    
    # Divergence detection
    lookback_period = 20
    divergence_threshold = 0.02
    
    # Risk management
    atr_period = 14
    atr_sl_multiplier = 2.0
    atr_tp_multiplier = 3.0
    trailing_stop_pct = 0.025
    
    # Signal filters
    require_fib_confluence = True  # Require price at Fib level
    use_golden_ratio = True  # Give extra weight to 0.618 level
    
    def calculate_fibonacci_levels(self, high_data, low_data, close_data):
        """Calculate dynamic Fibonacci retracement levels"""
        fib_supports = np.full((len(close_data), len(self.fib_levels)), np.nan)
        fib_resistances = np.full((len(close_data), len(self.fib_levels)), np.nan)
        
        for i in range(self.fib_lookback, len(close_data)):
            # Get recent price data
            recent_highs = high_data[i-self.fib_lookback:i]
            recent_lows = low_data[i-self.fib_lookback:i]
            
            if len(recent_highs) == 0:
                continue
            
            # Find swing high and low
            swing_high = np.max(recent_highs)
            swing_low = np.min(recent_lows)
            price_range = swing_high - swing_low
            
            if price_range <= 0:
                continue
            
            # Determine trend direction based on recent price action
            mid_point = i - self.fib_lookback // 2
            first_half_avg = np.mean(close_data[i-self.fib_lookback:mid_point])
            second_half_avg = np.mean(close_data[mid_point:i])
            
            if second_half_avg < first_half_avg:
                # Downtrend - calculate retracement levels from high to low
                for j, level in enumerate(self.fib_levels):
                    fib_supports[i, j] = swing_high - (price_range * level)
                    fib_resistances[i, j] = swing_high - (price_range * (1 - level))
            else:
                # Uptrend - calculate retracement levels from low to high
                for j, level in enumerate(self.fib_levels):
                    fib_supports[i, j] = swing_low + (price_range * (1 - level))
                    fib_resistances[i, j] = swing_low + (price_range * level)
        
        return fib_supports, fib_resistances
    
    def find_divergences(self, price_data, stoch_data):
        """Detect bullish and bearish divergences"""
        bullish_div = np.zeros(len(price_data))
        bearish_div = np.zeros(len(price_data))
        
        for i in range(self.lookback_period * 2, len(price_data)):
            recent_prices = price_data[i-self.lookback_period:i]
            recent_stoch = stoch_data[i-self.lookback_period:i]
            
            if len(recent_prices) < self.lookback_period:
                continue
                
            # Find local minima for bullish divergence
            price_min_idx = np.argmin(recent_prices)
            if price_min_idx > 2 and price_min_idx < len(recent_prices) - 2:
                prev_low_idx = np.argmin(price_data[i-self.lookback_period*2:i-self.lookback_period])
                if (recent_prices[price_min_idx] < price_data[i-self.lookback_period*2+prev_low_idx] * (1 - self.divergence_threshold) and
                    recent_stoch[price_min_idx] > stoch_data[i-self.lookback_period*2+prev_low_idx]):
                    bullish_div[i] = 1
            
            # Find local maxima for bearish divergence
            price_max_idx = np.argmax(recent_prices)
            if price_max_idx > 2 and price_max_idx < len(recent_prices) - 2:
                prev_high_idx = np.argmax(price_data[i-self.lookback_period*2:i-self.lookback_period])
                if (recent_prices[price_max_idx] > price_data[i-self.lookback_period*2+prev_high_idx] * (1 + self.divergence_threshold) and
                    recent_stoch[price_max_idx] < stoch_data[i-self.lookback_period*2+prev_high_idx]):
                    bearish_div[i] = 1
        
        return bullish_div, bearish_div
    
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
        
        stoch_k = stoch[f'STOCHk_{self.stoch_k_period}_{self.stoch_d_period}_{self.stoch_smooth}']
        stoch_d = stoch[f'STOCHd_{self.stoch_k_period}_{self.stoch_d_period}_{self.stoch_smooth}']
        
        stoch_k_full = np.full(len(close), np.nan)
        stoch_d_full = np.full(len(close), np.nan)
        stoch_k_full[-len(stoch_k):] = stoch_k.values
        stoch_d_full[-len(stoch_d):] = stoch_d.values
        
        self.stoch_k = self.I(lambda: stoch_k_full, name='Stoch_K')
        self.stoch_d = self.I(lambda: stoch_d_full, name='Stoch_D')
        
        # Previous values for zone exit detection
        stoch_k_prev = np.roll(stoch_k_full, 1)
        stoch_k_prev[0] = np.nan
        self.stoch_k_prev = self.I(lambda: stoch_k_prev, name='Stoch_K_Prev')
        
        # Calculate Fibonacci levels
        fib_supports, fib_resistances = self.calculate_fibonacci_levels(
            high.values, low.values, close.values
        )
        
        # Store individual Fib levels as indicators
        self.fib_236_support = self.I(lambda: fib_supports[:, 0], name='Fib_236_S')
        self.fib_382_support = self.I(lambda: fib_supports[:, 1], name='Fib_382_S')
        self.fib_500_support = self.I(lambda: fib_supports[:, 2], name='Fib_500_S')
        self.fib_618_support = self.I(lambda: fib_supports[:, 3], name='Fib_618_S')
        self.fib_786_support = self.I(lambda: fib_supports[:, 4], name='Fib_786_S')
        
        self.fib_236_resistance = self.I(lambda: fib_resistances[:, 0], name='Fib_236_R')
        self.fib_382_resistance = self.I(lambda: fib_resistances[:, 1], name='Fib_382_R')
        self.fib_500_resistance = self.I(lambda: fib_resistances[:, 2], name='Fib_500_R')
        self.fib_618_resistance = self.I(lambda: fib_resistances[:, 3], name='Fib_618_R')
        self.fib_786_resistance = self.I(lambda: fib_resistances[:, 4], name='Fib_786_R')
        
        # Store all levels for easy access
        self.fib_supports = fib_supports
        self.fib_resistances = fib_resistances
        
        # Detect divergences
        bullish_div, bearish_div = self.find_divergences(close.values, stoch_k_full)
        self.bullish_divergence = self.I(lambda: bullish_div, name='Bullish_Div')
        self.bearish_divergence = self.I(lambda: bearish_div, name='Bearish_Div')
        
        # ATR for stop loss and take profit
        atr = ta.atr(high, low, close, length=self.atr_period)
        atr_full = np.full(len(close), np.nan)
        atr_full[-len(atr):] = atr.values
        self.atr = self.I(lambda: atr_full, name='ATR')
        
        # Track entry price for trailing stop
        self.entry_price = 0
        self.highest_price = 0
        self.lowest_price = float('inf')
    
    def check_fib_level(self, price, levels, tolerance):
        """Check if price is near any Fibonacci level"""
        if np.any(np.isnan(levels)):
            return False, -1
        
        for i, level in enumerate(levels):
            if abs(price - level) / price <= tolerance:
                return True, i
        return False, -1
    
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.stoch_k[-1]) or np.isnan(self.atr[-1]):
            return
        
        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_high = self.data.High[-1]
        
        # Update trailing stop tracking
        if self.position:
            if self.position.is_long:
                self.highest_price = max(self.highest_price, current_high)
                trailing_stop = self.highest_price * (1 - self.trailing_stop_pct)
                if current_price <= trailing_stop:
                    self.position.close()
                    return
            else:
                self.lowest_price = min(self.lowest_price, current_low)
                trailing_stop = self.lowest_price * (1 + self.trailing_stop_pct)
                if current_price >= trailing_stop:
                    self.position.close()
                    return
        
        # Entry logic
        if not self.position:
            # Check Fibonacci levels
            idx = len(self.data.Close) - 1
            if idx >= len(self.fib_supports):
                return
            
            current_supports = self.fib_supports[idx]
            current_resistances = self.fib_resistances[idx]
            
            at_support, support_level_idx = self.check_fib_level(current_low, current_supports, self.fib_tolerance)
            at_resistance, resistance_level_idx = self.check_fib_level(current_high, current_resistances, self.fib_tolerance)
            
            # Golden ratio (0.618) gets special treatment
            at_golden_support = support_level_idx == 3 if at_support else False
            at_golden_resistance = resistance_level_idx == 3 if at_resistance else False
            
            # Check for divergences
            has_bullish_div = any(self.bullish_divergence[-self.lookback_period:] == 1) if len(self.bullish_divergence) >= self.lookback_period else False
            has_bearish_div = any(self.bearish_divergence[-self.lookback_period:] == 1) if len(self.bearish_divergence) >= self.lookback_period else False
            
            # Long entry conditions
            stoch_oversold_exit = (self.stoch_k_prev[-1] <= self.oversold_level and 
                                   self.stoch_k[-1] > self.oversold_level and
                                   self.stoch_k[-1] < 50)
            
            if self.require_fib_confluence:
                # Require price at Fibonacci support
                long_signal = stoch_oversold_exit and at_support
                # Enhanced signal at golden ratio
                if self.use_golden_ratio and at_golden_support and self.stoch_k[-1] < 30:
                    long_signal = True
            else:
                # Fib level optional but preferred
                long_signal = stoch_oversold_exit and (at_support or has_bullish_div)
            
            # Extra confirmation with divergence at Fib level
            if has_bullish_div and at_support:
                long_signal = True
            
            if long_signal:
                # Calculate stop loss and take profit
                sl_price = current_price - (self.atr[-1] * self.atr_sl_multiplier)
                
                # Find the nearest Fibonacci resistance above current price for target
                tp_price = None
                for fib_res in current_resistances:
                    if not np.isnan(fib_res) and fib_res > current_price * 1.001:  # At least 0.1% above current price
                        tp_price = fib_res
                        break
                
                # If no suitable Fib level found, use ATR-based target
                if tp_price is None:
                    tp_multiplier = self.atr_tp_multiplier * 1.5 if at_golden_support else self.atr_tp_multiplier
                    tp_price = current_price + (self.atr[-1] * tp_multiplier)
                
                # Final validation - ensure TP is sufficiently above entry and SL is below
                min_profit = self.atr[-1] * 0.5
                tp_price = max(tp_price, current_price + min_profit)
                sl_price = min(sl_price, current_price - min_profit)
                
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.highest_price = current_price
            
            # Short entry conditions
            stoch_overbought_exit = (self.stoch_k_prev[-1] >= self.overbought_level and
                                     self.stoch_k[-1] < self.overbought_level and
                                     self.stoch_k[-1] > 50)
            
            if self.require_fib_confluence:
                # Require price at Fibonacci resistance
                short_signal = stoch_overbought_exit and at_resistance
                # Enhanced signal at golden ratio
                if self.use_golden_ratio and at_golden_resistance and self.stoch_k[-1] > 70:
                    short_signal = True
            else:
                # Fib level optional but preferred
                short_signal = stoch_overbought_exit and (at_resistance or has_bearish_div)
            
            # Extra confirmation with divergence at Fib level
            if has_bearish_div and at_resistance:
                short_signal = True
            
            if short_signal:
                # Calculate stop loss and take profit
                sl_price = current_price + (self.atr[-1] * self.atr_sl_multiplier)
                
                # Find the nearest Fibonacci support below current price for target
                tp_price = None
                for fib_sup in reversed(current_supports):  # Start from highest support
                    if not np.isnan(fib_sup) and fib_sup < current_price * 0.999:  # At least 0.1% below current price
                        tp_price = fib_sup
                        break
                
                # If no suitable Fib level found, use ATR-based target
                if tp_price is None:
                    tp_multiplier = self.atr_tp_multiplier * 1.5 if at_golden_resistance else self.atr_tp_multiplier
                    tp_price = current_price - (self.atr[-1] * tp_multiplier)
                
                # Final validation - ensure TP is sufficiently below entry and SL is above
                min_profit = self.atr[-1] * 0.5
                tp_price = min(tp_price, current_price - min_profit)
                sl_price = max(sl_price, current_price + min_profit)
                
                self.sell(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.lowest_price = current_price

# Single backtest configuration
if __name__ == "__main__":
    # Load sample data for single backtest
    DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
    
    print(f"Loading data from: {DATA_PATH}")
    data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    data = data.sort_index()
    data = data.dropna()
    print(f"Data loaded! {len(data)} rows")
    
    # Run backtest
    bt = Backtest(data, StochasticReversalFibonacci, cash=10000000, commission=0.00045)
    stats = bt.run()
    
    print("\n" + "="*80)
    print("STOCHASTIC REVERSAL FIBONACCI STRATEGY - BACKTEST RESULTS")
    print("="*80)
    print(stats)
    print("="*80)
    
    # Show plot
    bt.plot()
    
    # TEST ON ALL DATA SOURCES
    print("\n" + "="*80)
    print("TESTING STOCHASTIC REVERSAL FIBONACCI ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(StochasticReversalFibonacci, 'StochasticReversalFibonacci')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/StochasticReversalFibonacci_[timestamp].csv")