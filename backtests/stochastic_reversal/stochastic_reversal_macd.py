"""
Moon Dev's Stochastic Reversal MACD Strategy
=============================================
Stochastic Reversal with MACD for trend confirmation.
Uses MACD histogram and signal crossovers to validate reversals.
Tests across all datasets with comprehensive stats output.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class StochasticReversalMACD(Strategy):
    """
    Stochastic Reversal Strategy with MACD Confirmation
    - Stochastic identifies overbought/oversold zones
    - MACD confirms momentum shift and trend direction
    - MACD histogram divergence adds conviction
    - Signal line crossovers time the entry
    """
    
    # Stochastic parameters
    stoch_k_period = 14
    stoch_d_period = 3
    stoch_smooth = 3
    overbought_level = 80
    oversold_level = 20
    
    # MACD parameters
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    
    # Divergence detection
    lookback_period = 20
    divergence_threshold = 0.02
    histogram_lookback = 10
    
    # Risk management
    atr_period = 14
    atr_sl_multiplier = 2.0
    atr_tp_multiplier = 3.0
    trailing_stop_pct = 0.025
    
    # Signal filters
    require_macd_confirmation = True
    use_histogram_divergence = True
    
    def find_divergences(self, price_data, oscillator_data, name=""):
        """Detect bullish and bearish divergences"""
        bullish_div = np.zeros(len(price_data))
        bearish_div = np.zeros(len(price_data))
        
        for i in range(self.lookback_period * 2, len(price_data)):
            recent_prices = price_data[i-self.lookback_period:i]
            recent_osc = oscillator_data[i-self.lookback_period:i]
            
            if len(recent_prices) < self.lookback_period:
                continue
            
            # Skip if oscillator data contains NaN
            if np.any(np.isnan(recent_osc)):
                continue
                
            # Find local minima for bullish divergence
            price_min_idx = np.argmin(recent_prices)
            if price_min_idx > 2 and price_min_idx < len(recent_prices) - 2:
                prev_low_idx = np.argmin(price_data[i-self.lookback_period*2:i-self.lookback_period])
                prev_osc_segment = oscillator_data[i-self.lookback_period*2:i-self.lookback_period]
                if not np.any(np.isnan(prev_osc_segment)):
                    if (recent_prices[price_min_idx] < price_data[i-self.lookback_period*2+prev_low_idx] * (1 - self.divergence_threshold) and
                        recent_osc[price_min_idx] > prev_osc_segment[prev_low_idx]):
                        bullish_div[i] = 1
            
            # Find local maxima for bearish divergence
            price_max_idx = np.argmax(recent_prices)
            if price_max_idx > 2 and price_max_idx < len(recent_prices) - 2:
                prev_high_idx = np.argmax(price_data[i-self.lookback_period*2:i-self.lookback_period])
                prev_osc_segment = oscillator_data[i-self.lookback_period*2:i-self.lookback_period]
                if not np.any(np.isnan(prev_osc_segment)):
                    if (recent_prices[price_max_idx] > price_data[i-self.lookback_period*2+prev_high_idx] * (1 + self.divergence_threshold) and
                        recent_osc[price_max_idx] < prev_osc_segment[prev_high_idx]):
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
        
        # Calculate MACD
        macd_result = ta.macd(close, fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)
        
        macd_line = macd_result[f'MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}']
        macd_signal = macd_result[f'MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}']
        macd_histogram = macd_result[f'MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}']
        
        # Fill arrays to match data length
        macd_line_full = np.full(len(close), np.nan)
        macd_signal_full = np.full(len(close), np.nan)
        macd_histogram_full = np.full(len(close), np.nan)
        
        macd_line_full[-len(macd_line):] = macd_line.values
        macd_signal_full[-len(macd_signal):] = macd_signal.values
        macd_histogram_full[-len(macd_histogram):] = macd_histogram.values
        
        self.macd_line = self.I(lambda: macd_line_full, name='MACD')
        self.macd_signal = self.I(lambda: macd_signal_full, name='MACD_Signal')
        self.macd_histogram = self.I(lambda: macd_histogram_full, name='MACD_Hist')
        
        # Previous values for crossover detection
        macd_line_prev = np.roll(macd_line_full, 1)
        macd_signal_prev = np.roll(macd_signal_full, 1)
        macd_histogram_prev = np.roll(macd_histogram_full, 1)
        
        macd_line_prev[0] = np.nan
        macd_signal_prev[0] = np.nan
        macd_histogram_prev[0] = np.nan
        
        self.macd_line_prev = self.I(lambda: macd_line_prev, name='MACD_Prev')
        self.macd_signal_prev = self.I(lambda: macd_signal_prev, name='MACD_Signal_Prev')
        self.macd_histogram_prev = self.I(lambda: macd_histogram_prev, name='MACD_Hist_Prev')
        
        # Detect divergences
        stoch_bullish_div, stoch_bearish_div = self.find_divergences(close.values, stoch_k_full, "Stoch")
        macd_bullish_div, macd_bearish_div = self.find_divergences(close.values, macd_histogram_full, "MACD")
        
        # Combine divergences
        combined_bullish = np.maximum(stoch_bullish_div, macd_bullish_div)
        combined_bearish = np.maximum(stoch_bearish_div, macd_bearish_div)
        
        self.bullish_divergence = self.I(lambda: combined_bullish, name='Bullish_Div')
        self.bearish_divergence = self.I(lambda: combined_bearish, name='Bearish_Div')
        
        # ATR for stop loss and take profit
        atr = ta.atr(high, low, close, length=self.atr_period)
        atr_full = np.full(len(close), np.nan)
        atr_full[-len(atr):] = atr.values
        self.atr = self.I(lambda: atr_full, name='ATR')
        
        # Track entry price for trailing stop
        self.entry_price = 0
        self.highest_price = 0
        self.lowest_price = float('inf')
    
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.stoch_k[-1]) or np.isnan(self.atr[-1]) or np.isnan(self.macd_line[-1]):
            return
        
        current_price = self.data.Close[-1]
        
        # Update trailing stop tracking
        if self.position:
            if self.position.is_long:
                self.highest_price = max(self.highest_price, self.data.High[-1])
                trailing_stop = self.highest_price * (1 - self.trailing_stop_pct)
                if current_price <= trailing_stop:
                    self.position.close()
                    return
            else:
                self.lowest_price = min(self.lowest_price, self.data.Low[-1])
                trailing_stop = self.lowest_price * (1 + self.trailing_stop_pct)
                if current_price >= trailing_stop:
                    self.position.close()
                    return
        
        # Entry logic
        if not self.position:
            # MACD crossover signals
            macd_bullish_cross = (self.macd_line[-1] > self.macd_signal[-1] and 
                                  self.macd_line_prev[-1] <= self.macd_signal_prev[-1])
            macd_bearish_cross = (self.macd_line[-1] < self.macd_signal[-1] and 
                                  self.macd_line_prev[-1] >= self.macd_signal_prev[-1])
            
            # MACD histogram momentum
            histogram_turning_bullish = (self.macd_histogram[-1] > self.macd_histogram_prev[-1] and
                                        self.macd_histogram[-1] > self.macd_histogram[-2] if len(self.macd_histogram) > 1 else False)
            histogram_turning_bearish = (self.macd_histogram[-1] < self.macd_histogram_prev[-1] and
                                        self.macd_histogram[-1] < self.macd_histogram[-2] if len(self.macd_histogram) > 1 else False)
            
            # Check for divergences
            has_bullish_div = any(self.bullish_divergence[-self.lookback_period:] == 1) if len(self.bullish_divergence) >= self.lookback_period else False
            has_bearish_div = any(self.bearish_divergence[-self.lookback_period:] == 1) if len(self.bearish_divergence) >= self.lookback_period else False
            
            # Long entry conditions
            stoch_oversold_exit = (self.stoch_k_prev[-1] <= self.oversold_level and 
                                   self.stoch_k[-1] > self.oversold_level and
                                   self.stoch_k[-1] < 50)
            
            if self.require_macd_confirmation:
                # Require MACD confirmation
                macd_long_confirmation = (macd_bullish_cross or 
                                         (self.macd_line[-1] > self.macd_signal[-1] and histogram_turning_bullish) or
                                         (self.macd_histogram[-1] > 0 and self.macd_histogram[-1] > self.macd_histogram_prev[-1]))
                
                long_signal = stoch_oversold_exit and macd_long_confirmation
            else:
                # MACD optional but preferred
                long_signal = stoch_oversold_exit and (macd_bullish_cross or histogram_turning_bullish or has_bullish_div)
            
            # Enhanced signal with histogram divergence
            if self.use_histogram_divergence and has_bullish_div and self.stoch_k[-1] < 30:
                long_signal = True
            
            if long_signal:
                # Calculate stop loss and take profit
                sl_price = current_price - (self.atr[-1] * self.atr_sl_multiplier)
                # Increase TP if MACD strongly bullish
                tp_multiplier = self.atr_tp_multiplier * 1.3 if macd_bullish_cross else self.atr_tp_multiplier
                tp_price = current_price + (self.atr[-1] * tp_multiplier)
                
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.highest_price = current_price
            
            # Short entry conditions
            stoch_overbought_exit = (self.stoch_k_prev[-1] >= self.overbought_level and
                                     self.stoch_k[-1] < self.overbought_level and
                                     self.stoch_k[-1] > 50)
            
            if self.require_macd_confirmation:
                # Require MACD confirmation
                macd_short_confirmation = (macd_bearish_cross or 
                                          (self.macd_line[-1] < self.macd_signal[-1] and histogram_turning_bearish) or
                                          (self.macd_histogram[-1] < 0 and self.macd_histogram[-1] < self.macd_histogram_prev[-1]))
                
                short_signal = stoch_overbought_exit and macd_short_confirmation
            else:
                # MACD optional but preferred
                short_signal = stoch_overbought_exit and (macd_bearish_cross or histogram_turning_bearish or has_bearish_div)
            
            # Enhanced signal with histogram divergence
            if self.use_histogram_divergence and has_bearish_div and self.stoch_k[-1] > 70:
                short_signal = True
            
            if short_signal:
                # Calculate stop loss and take profit
                sl_price = current_price + (self.atr[-1] * self.atr_sl_multiplier)
                # Increase TP if MACD strongly bearish
                tp_multiplier = self.atr_tp_multiplier * 1.3 if macd_bearish_cross else self.atr_tp_multiplier
                tp_price = current_price - (self.atr[-1] * tp_multiplier)
                
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
    bt = Backtest(data, StochasticReversalMACD, cash=10000000, commission=0.00045)
    stats = bt.run()
    
    print("\n" + "="*80)
    print("STOCHASTIC REVERSAL MACD STRATEGY - BACKTEST RESULTS")
    print("="*80)
    print(stats)
    print("="*80)
    
    # Show plot
    bt.plot()
    
    # TEST ON ALL DATA SOURCES
    print("\n" + "="*80)
    print("TESTING STOCHASTIC REVERSAL MACD ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(StochasticReversalMACD, 'StochasticReversalMACD')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/StochasticReversalMACD_[timestamp].csv")