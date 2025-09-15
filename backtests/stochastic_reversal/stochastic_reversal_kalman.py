"""
Moon Dev's Stochastic Reversal Kalman Strategy
===============================================
Stochastic Reversal with Kalman filter for noise reduction.
Smooths price and oscillator data for cleaner signals.
Tests across all datasets with comprehensive stats output.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
import warnings
warnings.filterwarnings('ignore')

class StochasticReversalKalman(Strategy):
    """
    Stochastic Reversal Strategy with Kalman Filter
    - Kalman filter smooths price data to reduce noise
    - Stochastic on filtered price for cleaner signals
    - Trend estimation from Kalman provides direction bias
    - Reduced false signals in choppy markets
    """
    
    # Stochastic parameters
    stoch_k_period = 14
    stoch_d_period = 3
    stoch_smooth = 3
    overbought_level = 80
    oversold_level = 20
    
    # Kalman filter parameters
    kalman_gain = 0.01  # Process noise (smaller = smoother)
    measurement_noise = 0.1  # Measurement noise
    initial_estimate_error = 1.0
    use_adaptive_kalman = True  # Adapt parameters based on volatility
    
    # Divergence detection
    lookback_period = 20
    divergence_threshold = 0.02
    
    # Risk management
    atr_period = 14
    atr_sl_multiplier = 2.0
    atr_tp_multiplier = 3.0
    trailing_stop_pct = 0.025
    
    # Signal filters
    min_trend_strength = 0.001  # Minimum Kalman trend slope
    use_velocity_filter = True  # Use rate of change from Kalman
    
    def kalman_filter(self, data):
        """Apply Kalman filter to price data"""
        n = len(data)
        filtered = np.zeros(n)
        velocity = np.zeros(n)  # Rate of change estimate
        
        # Initialize
        estimate = data[0] if not np.isnan(data[0]) else 0
        estimate_error = self.initial_estimate_error
        velocity_estimate = 0
        
        for i in range(n):
            if np.isnan(data[i]):
                filtered[i] = estimate
                velocity[i] = velocity_estimate
                continue
            
            # Adapt Kalman gain based on recent volatility
            if self.use_adaptive_kalman and i > 20:
                recent_std = np.std(data[max(0, i-20):i])
                if recent_std > 0:
                    adaptive_gain = min(0.1, self.kalman_gain * (1 + recent_std / 100))
                else:
                    adaptive_gain = self.kalman_gain
            else:
                adaptive_gain = self.kalman_gain
            
            # Prediction step
            prediction = estimate + velocity_estimate
            prediction_error = estimate_error + adaptive_gain
            
            # Update step
            kalman_gain = prediction_error / (prediction_error + self.measurement_noise)
            estimate = prediction + kalman_gain * (data[i] - prediction)
            estimate_error = (1 - kalman_gain) * prediction_error
            
            # Update velocity estimate
            if i > 0:
                velocity_estimate = velocity_estimate + kalman_gain * ((estimate - filtered[i-1]) - velocity_estimate)
            
            filtered[i] = estimate
            velocity[i] = velocity_estimate
        
        return filtered, velocity
    
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
        
        # Apply Kalman filter to price data
        kalman_close, kalman_velocity = self.kalman_filter(close.values)
        kalman_high, _ = self.kalman_filter(high.values)
        kalman_low, _ = self.kalman_filter(low.values)
        
        # Store Kalman filtered prices
        self.kalman_close = self.I(lambda: kalman_close, name='Kalman_Close')
        self.kalman_high = self.I(lambda: kalman_high, name='Kalman_High')
        self.kalman_low = self.I(lambda: kalman_low, name='Kalman_Low')
        self.kalman_velocity = self.I(lambda: kalman_velocity, name='Kalman_Velocity')
        
        # Calculate trend from Kalman filter
        kalman_trend = np.zeros(len(kalman_close))
        for i in range(1, len(kalman_close)):
            kalman_trend[i] = (kalman_close[i] - kalman_close[i-1]) / kalman_close[i-1] if kalman_close[i-1] != 0 else 0
        
        self.kalman_trend = self.I(lambda: kalman_trend, name='Kalman_Trend')
        
        # Calculate Stochastic on both raw and Kalman filtered data
        # Raw Stochastic
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
        
        # Kalman Stochastic
        kalman_high_series = pd.Series(kalman_high)
        kalman_low_series = pd.Series(kalman_low)
        kalman_close_series = pd.Series(kalman_close)
        
        kalman_stoch = ta.stoch(kalman_high_series, kalman_low_series, kalman_close_series,
                                k=self.stoch_k_period,
                                d=self.stoch_d_period,
                                smooth_k=self.stoch_smooth)
        
        if kalman_stoch is not None and not kalman_stoch.empty:
            kalman_stoch_k = kalman_stoch[f'STOCHk_{self.stoch_k_period}_{self.stoch_d_period}_{self.stoch_smooth}']
            kalman_stoch_k_full = np.full(len(close), np.nan)
            kalman_stoch_k_full[-len(kalman_stoch_k):] = kalman_stoch_k.values
        else:
            kalman_stoch_k_full = stoch_k_full  # Fallback to raw if Kalman fails
        
        self.stoch_k = self.I(lambda: stoch_k_full, name='Stoch_K')
        self.stoch_d = self.I(lambda: stoch_d_full, name='Stoch_D')
        self.kalman_stoch_k = self.I(lambda: kalman_stoch_k_full, name='Kalman_Stoch_K')
        
        # Previous values for zone exit detection
        stoch_k_prev = np.roll(kalman_stoch_k_full, 1)
        stoch_k_prev[0] = np.nan
        self.stoch_k_prev = self.I(lambda: stoch_k_prev, name='Stoch_K_Prev')
        
        # Detect divergences using Kalman filtered data
        bullish_div, bearish_div = self.find_divergences(kalman_close, kalman_stoch_k_full)
        self.bullish_divergence = self.I(lambda: bullish_div, name='Bullish_Div')
        self.bearish_divergence = self.I(lambda: bearish_div, name='Bearish_Div')
        
        # ATR for stop loss and take profit (on raw data)
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
        if np.isnan(self.kalman_stoch_k[-1]) or np.isnan(self.atr[-1]):
            return
        
        current_price = self.data.Close[-1]
        kalman_price = self.kalman_close[-1]
        kalman_velocity = self.kalman_velocity[-1]
        kalman_trend = self.kalman_trend[-1]
        
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
            # Use Kalman Stochastic for cleaner signals
            current_stoch = self.kalman_stoch_k[-1]
            prev_stoch = self.stoch_k_prev[-1]
            
            # Check for divergences
            has_bullish_div = any(self.bullish_divergence[-self.lookback_period:] == 1) if len(self.bullish_divergence) >= self.lookback_period else False
            has_bearish_div = any(self.bearish_divergence[-self.lookback_period:] == 1) if len(self.bearish_divergence) >= self.lookback_period else False
            
            # Velocity filter - momentum from Kalman
            bullish_velocity = kalman_velocity > 0 if self.use_velocity_filter else True
            bearish_velocity = kalman_velocity < 0 if self.use_velocity_filter else True
            
            # Long entry conditions
            stoch_oversold_exit = (prev_stoch <= self.oversold_level and 
                                   current_stoch > self.oversold_level and
                                   current_stoch < 50)
            
            # Kalman trend should be turning up or neutral
            trend_favorable_long = kalman_trend > -self.min_trend_strength
            
            long_signal = (stoch_oversold_exit and trend_favorable_long and bullish_velocity) or \
                         (has_bullish_div and current_stoch < 30 and kalman_velocity > 0)
            
            # Extra confirmation: Price above Kalman filtered price (breakout)
            if current_price > kalman_price * 1.002 and current_stoch < 50 and bullish_velocity:
                long_signal = True
            
            if long_signal:
                # Calculate stop loss and take profit
                sl_price = current_price - (self.atr[-1] * self.atr_sl_multiplier)
                # Increase TP if strong velocity
                tp_multiplier = self.atr_tp_multiplier * 1.3 if abs(kalman_velocity) > 0.01 else self.atr_tp_multiplier
                tp_price = current_price + (self.atr[-1] * tp_multiplier)
                
                self.buy(sl=sl_price, tp=tp_price)
                self.entry_price = current_price
                self.highest_price = current_price
            
            # Short entry conditions
            stoch_overbought_exit = (prev_stoch >= self.overbought_level and
                                     current_stoch < self.overbought_level and
                                     current_stoch > 50)
            
            # Kalman trend should be turning down or neutral
            trend_favorable_short = kalman_trend < self.min_trend_strength
            
            short_signal = (stoch_overbought_exit and trend_favorable_short and bearish_velocity) or \
                          (has_bearish_div and current_stoch > 70 and kalman_velocity < 0)
            
            # Extra confirmation: Price below Kalman filtered price (breakdown)
            if current_price < kalman_price * 0.998 and current_stoch > 50 and bearish_velocity:
                short_signal = True
            
            if short_signal:
                # Calculate stop loss and take profit
                sl_price = current_price + (self.atr[-1] * self.atr_sl_multiplier)
                # Increase TP if strong velocity
                tp_multiplier = self.atr_tp_multiplier * 1.3 if abs(kalman_velocity) > 0.01 else self.atr_tp_multiplier
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
    bt = Backtest(data, StochasticReversalKalman, cash=10000000, commission=0.00045)
    stats = bt.run()
    
    print("\n" + "="*80)
    print("STOCHASTIC REVERSAL KALMAN STRATEGY - BACKTEST RESULTS")
    print("="*80)
    print(stats)
    print("="*80)
    
    # Show plot
    bt.plot()
    
    # TEST ON ALL DATA SOURCES
    print("\n" + "="*80)
    print("TESTING STOCHASTIC REVERSAL KALMAN ON ALL DATA SOURCES")
    print("="*80)
    
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data
    
    # Test this strategy on all configured data sources
    results = test_on_all_data(StochasticReversalKalman, 'StochasticReversalKalman')
    
    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/StochasticReversalKalman_[timestamp].csv")