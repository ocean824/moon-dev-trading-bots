"""
Moon Dev's Parabolic SAR with Kalman Filter Strategy
=====================================================
Parabolic SAR strategy with Kalman filter price smoothing
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class ParabolicSARKalmanStrategy(Strategy):
    """
    Parabolic SAR with Kalman Filter Strategy
    - Applies Kalman filter to smooth price before SAR calculation
    - Uses standard SAR settings on smoothed price
    - Reduces false signals from market noise
    - Both long and short positions based on smoothed SAR
    """
    
    # SAR parameters (standard settings)
    sar_start = 0.02
    sar_increment = 0.02
    sar_maximum = 0.2
    
    # Kalman filter parameters
    process_variance = 0.01
    measurement_variance = 0.1
    
    def kalman_filter(self, data):
        """Apply Kalman filter to smooth the data"""
        n = len(data)
        filtered = np.zeros(n)
        
        # Initialize
        x_est = data[0]
        p_est = 1.0
        
        for i in range(n):
            # Prediction
            x_pred = x_est
            p_pred = p_est + self.process_variance
            
            # Update
            k_gain = p_pred / (p_pred + self.measurement_variance)
            x_est = x_pred + k_gain * (data[i] - x_pred)
            p_est = (1 - k_gain) * p_pred
            
            filtered[i] = x_est
        
        return filtered
    
    def init(self):
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        
        # Apply Kalman filter to smooth prices
        smoothed_high = pd.Series(self.kalman_filter(high.values), index=high.index)
        smoothed_low = pd.Series(self.kalman_filter(low.values), index=low.index)
        smoothed_close = pd.Series(self.kalman_filter(close.values), index=close.index)
        
        # Store smoothed close for signals
        self.smoothed_close = self.I(lambda: smoothed_close.values, name='Smoothed_Close')
        
        # Calculate Parabolic SAR on smoothed data
        psar_result = ta.psar(smoothed_high, smoothed_low, smoothed_close, 
                              af0=self.sar_start, 
                              af=self.sar_increment, 
                              max_af=self.sar_maximum)
        
        # Combined SAR indicator
        combined_sar = psar_result['PSARl_0.02_0.2'].fillna(psar_result['PSARs_0.02_0.2'])
        self.sar = self.I(lambda: combined_sar.values, name='SAR_Kalman')
        
        # Previous SAR for crossover detection
        self.sar_prev = self.I(lambda: combined_sar.shift(1).values, name='SAR_Prev')
        
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < 20:
            return
        
        # Get current values - use smoothed close for comparison
        price = self.smoothed_close[-1]
        sar_curr = self.sar[-1]
        sar_prev = self.sar_prev[-1]
        
        # Check for valid values
        if pd.isna(sar_curr) or pd.isna(sar_prev) or pd.isna(price):
            return
        
        # Determine SAR position relative to smoothed price
        sar_below_price = sar_curr < price
        prev_price = self.smoothed_close[-2] if len(self.smoothed_close) > 1 else price
        sar_was_below = sar_prev < prev_price
        
        # Long signal: SAR below smoothed price
        if sar_below_price and not sar_was_below:
            if self.position and self.position.is_short:
                self.position.close()
                self.buy(size=0.95)
            elif not self.position:
                self.buy(size=0.95)
        
        # Short signal: SAR above smoothed price
        elif not sar_below_price and sar_was_below:
            if self.position and self.position.is_long:
                self.position.close()
                self.sell(size=0.95)
            elif not self.position:
                self.sell(size=0.95)

def main():
    """Run backtest on all data sources"""
    print("\n" + "="*80)
    print("MOON DEV'S PARABOLIC SAR WITH KALMAN FILTER STRATEGY")
    print("="*80)
    print("Testing on all available data sources...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        ParabolicSARKalmanStrategy,
        'ParabolicSARKalman',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("STRATEGY COMPLETE!")
        print("="*80)
        print(f"Total tests run: {len(results)}")
        print(f"Average Return: {results['Return_%'].mean():.2f}%")
        print(f"Average Sharpe: {results['Sharpe'].mean():.3f}")
        print(f"Average Max Drawdown: {results['Max_DD_%'].mean():.2f}%")
        print(f"Total Trades: {results['Trades'].sum()}")
        print("="*80)

if __name__ == "__main__":
    main()