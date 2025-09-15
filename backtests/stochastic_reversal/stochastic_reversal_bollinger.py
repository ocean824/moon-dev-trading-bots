"""
Moon Dev's Stochastic Reversal Bollinger Strategy
==================================================
Stochastic Reversal with Bollinger Bands for volatility context.
Combines overbought/oversold with band position for high-probability reversals.
Tests across all datasets with comprehensive stats output.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class StochasticReversalBollinger(Strategy):
    """
    Stochastic Reversal Strategy with Bollinger Bands
    - Stochastic identifies overbought/oversold conditions
    - Bollinger Bands confirm extreme price positions
    - Enter reversals when both conditions align
    - Band squeeze detection for breakout anticipation
    """
    
    # Stochastic parameters
    stoch_k_period = 14
    stoch_d_period = 3
    stoch_smooth = 3
    overbought_level = 80
    oversold_level = 20
    
    # Bollinger Bands parameters
    bb_period = 20
    bb_std = 2.0
    bb_squeeze_threshold = 0.01  # Bandwidth threshold for squeeze
    
    # Divergence detection
    lookback_period = 20
    divergence_threshold = 0.02
    
    # Risk management
    atr_period = 14
    atr_sl_multiplier = 2.0
    atr_tp_multiplier = 3.0
    trailing_stop_pct = 0.025
    
    # Signal filters
    require_band_touch = True  # Price must touch outer bands
    use_squeeze_breakout = True  # Trade breakouts from BB squeeze
    
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
        
        # Calculate Bollinger Bands
        bb = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        
        bb_upper = bb[f'BBU_{self.bb_period}_{self.bb_std}']
        bb_middle = bb[f'BBM_{self.bb_period}_{self.bb_std}']
        bb_lower = bb[f'BBL_{self.bb_period}_{self.bb_std}']
        bb_bandwidth = bb[f'BBB_{self.bb_period}_{self.bb_std}']
        bb_percent = bb[f'BBP_{self.bb_period}_{self.bb_std}']
        
        # Fill arrays to match data length
        bb_upper_full = np.full(len(close), np.nan)
        bb_middle_full = np.full(len(close), np.nan)
        bb_lower_full = np.full(len(close), np.nan)
        bb_bandwidth_full = np.full(len(close), np.nan)
        bb_percent_full = np.full(len(close), np.nan)
        
        bb_upper_full[-len(bb_upper):] = bb_upper.values
        bb_middle_full[-len(bb_middle):] = bb_middle.values
        bb_lower_full[-len(bb_lower):] = bb_lower.values
        bb_bandwidth_full[-len(bb_bandwidth):] = bb_bandwidth.values
        bb_percent_full[-len(bb_percent):] = bb_percent.values
        
        self.bb_upper = self.I(lambda: bb_upper_full, name='BB_Upper')
        self.bb_middle = self.I(lambda: bb_middle_full, name='BB_Middle')
        self.bb_lower = self.I(lambda: bb_lower_full, name='BB_Lower')
        self.bb_bandwidth = self.I(lambda: bb_bandwidth_full, name='BB_Width')
        self.bb_percent = self.I(lambda: bb_percent_full, name='BB_Percent')
        
        # Detect BB squeeze (low volatility)
        squeeze_threshold = np.percentile(bb_bandwidth_full[~np.isnan(bb_bandwidth_full)], 10) if np.any(~np.isnan(bb_bandwidth_full)) else self.bb_squeeze_threshold
        bb_squeeze = bb_bandwidth_full < squeeze_threshold
        self.bb_squeeze = self.I(lambda: bb_squeeze, name='BB_Squeeze')
        
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
        self.squeeze_bars = 0
    
    def next(self):
        # Skip if indicators not ready
        if np.isnan(self.stoch_k[-1]) or np.isnan(self.atr[-1]) or np.isnan(self.bb_upper[-1]):
            return
        
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        
        # Track squeeze duration
        if self.bb_squeeze[-1]:
            self.squeeze_bars += 1
        else:
            self.squeeze_bars = 0
        
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
            # Check band positions
            at_lower_band = current_low <= self.bb_lower[-1] * 1.002  # Small buffer
            at_upper_band = current_high >= self.bb_upper[-1] * 0.998  # Small buffer
            
            # Check for divergences
            has_bullish_div = any(self.bullish_divergence[-self.lookback_period:] == 1) if len(self.bullish_divergence) >= self.lookback_period else False
            has_bearish_div = any(self.bearish_divergence[-self.lookback_period:] == 1) if len(self.bearish_divergence) >= self.lookback_period else False
            
            # Squeeze breakout mode
            if self.use_squeeze_breakout and self.squeeze_bars > 5:
                # After prolonged squeeze, trade breakout direction
                if current_price > self.bb_upper[-1] and self.stoch_k[-1] > 50:
                    # Bullish breakout from squeeze
                    sl_price = self.bb_middle[-1]
                    tp_price = current_price + (self.bb_upper[-1] - self.bb_middle[-1]) * 2
                    
                    self.buy(sl=sl_price, tp=tp_price)
                    self.entry_price = current_price
                    self.highest_price = current_price
                    return
                
                elif current_price < self.bb_lower[-1] and self.stoch_k[-1] < 50:
                    # Bearish breakout from squeeze
                    sl_price = self.bb_middle[-1]
                    tp_price = current_price - (self.bb_middle[-1] - self.bb_lower[-1]) * 2
                    
                    self.sell(sl=sl_price, tp=tp_price)
                    self.entry_price = current_price
                    self.lowest_price = current_price
                    return
            
            # Long entry: Oversold + at lower band
            stoch_oversold_exit = (self.stoch_k_prev[-1] <= self.oversold_level and 
                                   self.stoch_k[-1] > self.oversold_level and
                                   self.stoch_k[-1] < 50)
            
            band_condition_long = at_lower_band if self.require_band_touch else (self.bb_percent[-1] < 0.2)
            
            if (stoch_oversold_exit and band_condition_long) or \
               (has_bullish_div and at_lower_band and self.stoch_k[-1] < 30):
                
                # Calculate stop loss and take profit
                sl_price = min(current_price - (self.atr[-1] * self.atr_sl_multiplier), 
                              self.bb_lower[-1] - (self.bb_middle[-1] - self.bb_lower[-1]) * 0.5)
                
                # Target upper band or ATR multiple
                tp_price = max(self.bb_upper[-1], 
                              current_price + (self.atr[-1] * self.atr_tp_multiplier))
                
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.highest_price = current_price
            
            # Short entry: Overbought + at upper band
            stoch_overbought_exit = (self.stoch_k_prev[-1] >= self.overbought_level and
                                     self.stoch_k[-1] < self.overbought_level and
                                     self.stoch_k[-1] > 50)
            
            band_condition_short = at_upper_band if self.require_band_touch else (self.bb_percent[-1] > 0.8)
            
            if (stoch_overbought_exit and band_condition_short) or \
               (has_bearish_div and at_upper_band and self.stoch_k[-1] > 70):
                
                # Calculate stop loss and take profit
                sl_price = max(current_price + (self.atr[-1] * self.atr_sl_multiplier),
                              self.bb_upper[-1] + (self.bb_upper[-1] - self.bb_middle[-1]) * 0.5)
                
                # Target lower band or ATR multiple
                tp_price = min(self.bb_lower[-1],
                              current_price - (self.atr[-1] * self.atr_tp_multiplier))
                
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
    bt = Backtest(data, StochasticReversalBollinger, cash=10000000, commission=0.00045)
    stats = bt.run()
    
    print("\n" + "="*80)
    print("STOCHASTIC REVERSAL BOLLINGER STRATEGY - BACKTEST RESULTS")
    print("="*80)
    print(stats)
    print("="*80)
    
    # Show plot
    bt.plot()
    
    # TEST ON ALL DATA SOURCES
    print("\n" + "="*80)
    print("TESTING STOCHASTIC REVERSAL BOLLINGER ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(StochasticReversalBollinger, 'StochasticReversalBollinger')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/StochasticReversalBollinger_[timestamp].csv")