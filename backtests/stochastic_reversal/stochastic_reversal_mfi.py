"""
Moon Dev's Stochastic Reversal MFI Strategy
============================================
Stochastic Reversal with Money Flow Index confirmation.
Uses MFI to confirm oversold/overbought conditions with volume.
Tests across all datasets with comprehensive stats output.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class StochasticReversalMFI(Strategy):
    """
    Stochastic Reversal Strategy with MFI Confirmation
    - Stochastic identifies overbought/oversold zones
    - MFI confirms with volume-weighted momentum
    - Double confirmation reduces false signals
    - MFI divergence adds extra conviction
    """
    
    # Stochastic parameters
    stoch_k_period = 14
    stoch_d_period = 3
    stoch_smooth = 3
    overbought_level = 80
    oversold_level = 20
    
    # MFI parameters
    mfi_period = 14
    mfi_overbought = 80
    mfi_oversold = 20
    mfi_divergence_lookback = 20
    
    # Divergence detection
    lookback_period = 20
    divergence_threshold = 0.02
    
    # Risk management
    atr_period = 14
    atr_sl_multiplier = 2.0
    atr_tp_multiplier = 3.0
    trailing_stop_pct = 0.025
    
    # Signal confirmation
    require_both_oversold = True  # Both Stoch and MFI must be oversold/overbought
    
    def find_divergences(self, price_data, oscillator_data, name=""):
        """Detect bullish and bearish divergences for any oscillator"""
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
        
        # Calculate MFI
        mfi = ta.mfi(high, low, close, volume, length=self.mfi_period)
        mfi_full = np.full(len(close), np.nan)
        mfi_full[-len(mfi):] = mfi.values
        self.mfi = self.I(lambda: mfi_full, name='MFI')
        
        # Previous MFI for zone exit detection
        mfi_prev = np.roll(mfi_full, 1)
        mfi_prev[0] = np.nan
        self.mfi_prev = self.I(lambda: mfi_prev, name='MFI_Prev')
        
        # Detect divergences for both indicators
        stoch_bullish_div, stoch_bearish_div = self.find_divergences(close.values, stoch_k_full, "Stoch")
        mfi_bullish_div, mfi_bearish_div = self.find_divergences(close.values, mfi_full, "MFI")
        
        # Combine divergences (either indicator showing divergence)
        combined_bullish = np.maximum(stoch_bullish_div, mfi_bullish_div)
        combined_bearish = np.maximum(stoch_bearish_div, mfi_bearish_div)
        
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
        if np.isnan(self.stoch_k[-1]) or np.isnan(self.atr[-1]) or np.isnan(self.mfi[-1]):
            return
        
        current_price = self.data.Close[-1]
        current_stoch = self.stoch_k[-1]
        current_mfi = self.mfi[-1]
        
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
            # Check for divergences
            has_bullish_div = any(self.bullish_divergence[-self.lookback_period:] == 1) if len(self.bullish_divergence) >= self.lookback_period else False
            has_bearish_div = any(self.bearish_divergence[-self.lookback_period:] == 1) if len(self.bearish_divergence) >= self.lookback_period else False
            
            # Long entry conditions
            stoch_oversold_exit = (self.stoch_k_prev[-1] <= self.oversold_level and 
                                   current_stoch > self.oversold_level and
                                   current_stoch < 50)
            
            mfi_oversold_exit = (self.mfi_prev[-1] <= self.mfi_oversold and
                                 current_mfi > self.mfi_oversold and
                                 current_mfi < 50)
            
            if self.require_both_oversold:
                # Both indicators must confirm oversold exit
                long_signal = stoch_oversold_exit and mfi_oversold_exit
            else:
                # Either indicator confirming is enough (with divergence preference)
                long_signal = (stoch_oversold_exit and current_mfi < 50) or \
                             (mfi_oversold_exit and current_stoch < 50) or \
                             (has_bullish_div and (current_stoch < 30 or current_mfi < 30))
            
            if long_signal:
                # Calculate stop loss and take profit
                sl_price = current_price - (self.atr[-1] * self.atr_sl_multiplier)
                # Increase TP if both indicators agree
                tp_multiplier = self.atr_tp_multiplier * 1.2 if (stoch_oversold_exit and mfi_oversold_exit) else self.atr_tp_multiplier
                tp_price = current_price + (self.atr[-1] * tp_multiplier)
                
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.highest_price = current_price
            
            # Short entry conditions
            stoch_overbought_exit = (self.stoch_k_prev[-1] >= self.overbought_level and
                                     current_stoch < self.overbought_level and
                                     current_stoch > 50)
            
            mfi_overbought_exit = (self.mfi_prev[-1] >= self.mfi_overbought and
                                   current_mfi < self.mfi_overbought and
                                   current_mfi > 50)
            
            if self.require_both_oversold:
                # Both indicators must confirm overbought exit
                short_signal = stoch_overbought_exit and mfi_overbought_exit
            else:
                # Either indicator confirming is enough
                short_signal = (stoch_overbought_exit and current_mfi > 50) or \
                              (mfi_overbought_exit and current_stoch > 50) or \
                              (has_bearish_div and (current_stoch > 70 or current_mfi > 70))
            
            if short_signal:
                # Calculate stop loss and take profit
                sl_price = current_price + (self.atr[-1] * self.atr_sl_multiplier)
                # Increase TP if both indicators agree
                tp_multiplier = self.atr_tp_multiplier * 1.2 if (stoch_overbought_exit and mfi_overbought_exit) else self.atr_tp_multiplier
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
    bt = Backtest(data, StochasticReversalMFI, cash=10000000, commission=0.00045)
    stats = bt.run()
    
    print("\n" + "="*80)
    print("STOCHASTIC REVERSAL MFI STRATEGY - BACKTEST RESULTS")
    print("="*80)
    print(stats)
    print("="*80)
    
    # Show plot
    bt.plot()
    
    # TEST ON ALL DATA SOURCES
    print("\n" + "="*80)
    print("TESTING STOCHASTIC REVERSAL MFI ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(StochasticReversalMFI, 'StochasticReversalMFI')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/StochasticReversalMFI_[timestamp].csv")