"""
Moon Dev's Bollinger Breakout with Kalman Filter Strategy
==========================================================
Bollinger Band breakout with Kalman filter smoothing for noise reduction
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class BollingerBreakoutKalmanStrategy(Strategy):
    """
    Bollinger Band Breakout with Kalman Filter
    - Uses 21-period BB with 2.7 std dev
    - Applies Kalman filter to price for smoother signals
    - Long when price closes above upper band
    - Exit when price closes below middle band
    """
    
    # Bollinger Band parameters
    bb_period = 21
    bb_std = 2.7
    
    # Kalman filter parameters
    kalman_gain = 0.05
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Apply Kalman filter to close prices
        kalman_filtered = self._apply_kalman_filter(close)
        self.kalman_price = self.I(lambda: kalman_filtered.values, name='Kalman_Price')
        
        # Calculate Bollinger Bands on Kalman filtered prices
        bb_result = ta.bbands(pd.Series(kalman_filtered), length=self.bb_period, std=self.bb_std)
        
        # Extract bands
        upper_col = f'BBU_{self.bb_period}_{self.bb_std}'
        middle_col = f'BBM_{self.bb_period}_{self.bb_std}'
        lower_col = f'BBL_{self.bb_period}_{self.bb_std}'
        
        self.bb_upper = self.I(lambda: bb_result[upper_col].ffill().values, name='BB_Upper')
        self.bb_middle = self.I(lambda: bb_result[middle_col].ffill().values, name='BB_Middle')
        self.bb_lower = self.I(lambda: bb_result[lower_col].ffill().values, name='BB_Lower')
        
        # ATR for risk management
        self.atr = self.I(ta.atr, high, low, close, 14)
        
    def _apply_kalman_filter(self, prices):
        """Apply Kalman filter to price series"""
        filtered = np.zeros(len(prices))
        
        # Initialize
        filtered[0] = prices.iloc[0] if not pd.isna(prices.iloc[0]) else 0
        
        # Apply Kalman filter
        for i in range(1, len(prices)):
            if not pd.isna(prices.iloc[i]):
                # Prediction
                prediction = filtered[i-1]
                # Update with measurement
                filtered[i] = prediction + self.kalman_gain * (prices.iloc[i] - prediction)
            else:
                filtered[i] = filtered[i-1]
        
        return pd.Series(filtered, index=prices.index)
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < self.bb_period + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        kalman_price = self.kalman_price[-1]
        upper_band = self.bb_upper[-1]
        middle_band = self.bb_middle[-1]
        lower_band = self.bb_lower[-1]
        atr_value = self.atr[-1]
        
        # Previous values for crossover detection
        if len(self.data.Close) > 1:
            prev_kalman = self.kalman_price[-2]
            prev_upper = self.bb_upper[-2]
            prev_middle = self.bb_middle[-2]
            prev_lower = self.bb_lower[-2]
        else:
            return
        
        # Check for valid values
        if pd.isna(kalman_price) or pd.isna(upper_band) or pd.isna(middle_band) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Entry logic
        if not self.position:
            # Long signal: Kalman price breaks above upper band
            if prev_kalman <= prev_upper and kalman_price > upper_band:
                stop_loss = price - (atr_value * 2.0)
                self.buy(sl=stop_loss, size=0.95)
            
            # Short signal: Kalman price breaks below lower band
            elif prev_kalman >= prev_lower and kalman_price < lower_band:
                stop_loss = price + (atr_value * 2.0)
                self.sell(sl=stop_loss, size=0.95)
        
        # Exit logic
        else:
            # Exit long when kalman price crosses below middle band
            if self.position.is_long and kalman_price < middle_band:
                self.position.close()
            
            # Exit short when kalman price crosses above middle band
            elif self.position.is_short and kalman_price > middle_band:
                self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S BOLLINGER BREAKOUT KALMAN STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Bollinger Breakout with Kalman Filter across all datasets...")
    print("="*80)
    
    # Run tests on all data sources without optimization
    results = test_on_all_data(
        BollingerBreakoutKalmanStrategy,
        'BollingerBreakoutKalman',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/BollingerBreakoutKalman.csv")
        print("="*80)

if __name__ == "__main__":
    main()