"""
Moon Dev's Stochastic Reversal Base Strategy
=============================================
Identifies overbought/oversold conditions using Stochastic Oscillator
and enters reversal trades when conditions normalize.
Tests across all datasets with comprehensive stats output.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class StochasticReversalBase(Strategy):
    """
    Stochastic Reversal Strategy - Base Implementation
    - Uses Stochastic Oscillator to identify extreme conditions
    - Overbought when %K > 80, Oversold when %K < 20
    - Enters long when exiting oversold, short when exiting overbought
    - Confirms with divergence detection when available
    - Uses ATR-based stops and targets
    """
    
    # Stochastic parameters
    stoch_k_period = 14
    stoch_d_period = 3
    stoch_smooth = 3
    overbought_level = 80
    oversold_level = 20
    
    # Divergence detection
    lookback_period = 20
    divergence_threshold = 0.02  # 2% minimum price difference
    
    # Risk management
    atr_period = 14
    atr_sl_multiplier = 2.0
    atr_tp_multiplier = 3.0
    trailing_stop_pct = 0.025
    
    # Volume confirmation
    volume_period = 20
    volume_multiplier = 1.2
    
    def find_divergences(self, price_data, stoch_data):
        """Detect bullish and bearish divergences"""
        bullish_div = np.zeros(len(price_data))
        bearish_div = np.zeros(len(price_data))
        
        for i in range(self.lookback_period * 2, len(price_data)):
            # Look for recent pivot points
            recent_prices = price_data[i-self.lookback_period:i]
            recent_stoch = stoch_data[i-self.lookback_period:i]
            
            if len(recent_prices) < self.lookback_period:
                continue
                
            # Find local minima for bullish divergence
            price_min_idx = np.argmin(recent_prices)
            if price_min_idx > 2 and price_min_idx < len(recent_prices) - 2:
                # Check if current low is lower than previous low
                prev_low_idx = np.argmin(price_data[i-self.lookback_period*2:i-self.lookback_period])
                if (recent_prices[price_min_idx] < price_data[i-self.lookback_period*2+prev_low_idx] * (1 - self.divergence_threshold) and
                    recent_stoch[price_min_idx] > stoch_data[i-self.lookback_period*2+prev_low_idx]):
                    bullish_div[i] = 1
            
            # Find local maxima for bearish divergence
            price_max_idx = np.argmax(recent_prices)
            if price_max_idx > 2 and price_max_idx < len(recent_prices) - 2:
                # Check if current high is higher than previous high
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
        
        # Previous values for zone exit detection
        stoch_k_prev = np.roll(stoch_k_full, 1)
        stoch_k_prev[0] = np.nan
        self.stoch_k_prev = self.I(lambda: stoch_k_prev, name='Stoch_K_Prev')
        
        # Detect divergences
        bullish_div, bearish_div = self.find_divergences(close.values, stoch_k_full)
        self.bullish_divergence = self.I(lambda: bullish_div, name='Bullish_Div')
        self.bearish_divergence = self.I(lambda: bearish_div, name='Bearish_Div')
        
        # ATR for stop loss and take profit
        atr = ta.atr(high, low, close, length=self.atr_period)
        atr_full = np.full(len(close), np.nan)
        atr_full[-len(atr):] = atr.values
        self.atr = self.I(lambda: atr_full, name='ATR')
        
        # Volume SMA for confirmation
        volume_sma = ta.sma(volume, length=self.volume_period)
        volume_sma_full = np.full(len(close), np.nan)
        volume_sma_full[-len(volume_sma):] = volume_sma.values
        self.volume_sma = self.I(lambda: volume_sma_full, name='Volume_SMA')
        
        # Track entry price for trailing stop
        self.entry_price = 0
        self.highest_price = 0
        self.lowest_price = float('inf')
    
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.stoch_k[-1]) or np.isnan(self.atr[-1]):
            return
        
        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        
        # Update trailing stop tracking
        if self.position:
            if self.position.is_long:
                self.highest_price = max(self.highest_price, self.data.High[-1])
                # Check trailing stop
                trailing_stop = self.highest_price * (1 - self.trailing_stop_pct)
                if current_price <= trailing_stop:
                    self.position.close()
                    return
            else:
                self.lowest_price = min(self.lowest_price, self.data.Low[-1])
                # Check trailing stop
                trailing_stop = self.lowest_price * (1 + self.trailing_stop_pct)
                if current_price >= trailing_stop:
                    self.position.close()
                    return
        
        # Entry logic
        if not self.position:
            # Volume confirmation
            volume_confirmed = current_volume > self.volume_sma[-1] * self.volume_multiplier if not np.isnan(self.volume_sma[-1]) else True
            
            # Long entry: Exiting oversold zone
            if (self.stoch_k_prev[-1] <= self.oversold_level and 
                self.stoch_k[-1] > self.oversold_level and
                self.stoch_k[-1] < 50):  # Still in lower half
                
                # Check for bullish divergence as additional confirmation
                has_divergence = any(self.bullish_divergence[-self.lookback_period:] == 1) if len(self.bullish_divergence) >= self.lookback_period else False
                
                if volume_confirmed or has_divergence:
                    # Calculate stop loss and take profit
                    sl_price = current_price - (self.atr[-1] * self.atr_sl_multiplier)
                    tp_price = current_price + (self.atr[-1] * self.atr_tp_multiplier)
                    
                    self.buy(sl=sl_price, tp=tp_price)
                    self.entry_price = current_price
                    self.highest_price = current_price
            
            # Short entry: Exiting overbought zone
            elif (self.stoch_k_prev[-1] >= self.overbought_level and
                  self.stoch_k[-1] < self.overbought_level and
                  self.stoch_k[-1] > 50):  # Still in upper half
                
                # Check for bearish divergence as additional confirmation
                has_divergence = any(self.bearish_divergence[-self.lookback_period:] == 1) if len(self.bearish_divergence) >= self.lookback_period else False
                
                if volume_confirmed or has_divergence:
                    # Calculate stop loss and take profit
                    sl_price = current_price + (self.atr[-1] * self.atr_sl_multiplier)
                    tp_price = current_price - (self.atr[-1] * self.atr_tp_multiplier)
                    
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
    bt = Backtest(data, StochasticReversalBase, cash=10000000, commission=0.00045)
    stats = bt.run()
    
    print("\n" + "="*80)
    print("STOCHASTIC REVERSAL BASE STRATEGY - BACKTEST RESULTS")
    print("="*80)
    print(stats)
    print("="*80)
    
    # Show plot
    bt.plot()
    
    # TEST ON ALL DATA SOURCES
    print("\n" + "="*80)
    print("TESTING STOCHASTIC REVERSAL BASE ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(StochasticReversalBase, 'StochasticReversalBase')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/StochasticReversalBase_[timestamp].csv")