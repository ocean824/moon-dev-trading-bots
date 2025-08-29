"""
Moon Dev's Acceleration RSI Strategy
=====================================
Uses RSI acceleration patterns for momentum trading
Tests across all datasets with comprehensive stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class AccelerationRSIStrategy(Strategy):
    """
    RSI Acceleration Strategy
    - Use 14-period RSI
    - Look for rapid RSI changes with price movements
    - Long when RSI crosses above 30 with increasing momentum
    - Short when RSI crosses below 70 with decreasing momentum
    - Tight stop-losses
    """
    
    # RSI parameters
    rsi_period = 14
    rsi_oversold = 30
    rsi_overbought = 70
    
    # Acceleration parameters
    rsi_accel_threshold = 5  # RSI must change by at least 5 points
    rsi_lookback = 3  # Bars to measure RSI acceleration
    
    # Risk management
    atr_period = 14
    atr_sl_multiplier = 1.0  # Tight stop loss
    atr_tp_multiplier = 2.5
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Calculate RSI
        rsi = ta.rsi(close, self.rsi_period)
        self.rsi = self.I(lambda: rsi.values, name='RSI')
        
        # Calculate RSI change (acceleration)
        rsi_change = rsi - rsi.shift(self.rsi_lookback)
        self.rsi_change = self.I(lambda: rsi_change.values, name='RSI_Change')
        
        # Calculate RSI velocity (rate of change)
        rsi_velocity = rsi.diff()
        self.rsi_velocity = self.I(lambda: rsi_velocity.values, name='RSI_Velocity')
        
        # Price momentum
        price_change = (close - close.shift(self.rsi_lookback)) / close.shift(self.rsi_lookback) * 100
        self.price_momentum = self.I(lambda: price_change.values, name='PriceMomentum')
        
        # ATR for stops
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # Track RSI extremes for better entry
        rsi_min = rsi.rolling(window=20).min()
        rsi_max = rsi.rolling(window=20).max()
        self.rsi_min = self.I(lambda: rsi_min.values, name='RSI_Min')
        self.rsi_max = self.I(lambda: rsi_max.values, name='RSI_Max')
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.rsi_period, self.atr_period, 20) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        rsi_current = self.rsi[-1]
        rsi_prev = self.rsi[-2] if len(self.rsi) > 1 else rsi_current
        rsi_change = self.rsi_change[-1]
        rsi_velocity = self.rsi_velocity[-1]
        price_momentum = self.price_momentum[-1]
        atr_value = self.atr[-1]
        
        # Check for valid values
        if pd.isna(rsi_current) or pd.isna(rsi_change) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Get RSI extremes
        rsi_min_val = self.rsi_min[-1] if not pd.isna(self.rsi_min[-1]) else 0
        rsi_max_val = self.rsi_max[-1] if not pd.isna(self.rsi_max[-1]) else 100
        
        # Long conditions:
        # 1. RSI crosses above oversold level
        # 2. RSI is accelerating upward (rapid change)
        # 3. Price momentum is positive
        rsi_cross_above_oversold = (rsi_prev <= self.rsi_oversold) and (rsi_current > self.rsi_oversold)
        rsi_accelerating_up = (rsi_change > self.rsi_accel_threshold) and (rsi_velocity > 0)
        near_rsi_bottom = rsi_current < (rsi_min_val + 10)
        
        long_signal = (rsi_cross_above_oversold or (near_rsi_bottom and rsi_accelerating_up)) and (price_momentum > -2)
        
        # Short conditions:
        # 1. RSI crosses below overbought level
        # 2. RSI is accelerating downward (rapid change)
        # 3. Price momentum is negative
        rsi_cross_below_overbought = (rsi_prev >= self.rsi_overbought) and (rsi_current < self.rsi_overbought)
        rsi_accelerating_down = (rsi_change < -self.rsi_accel_threshold) and (rsi_velocity < 0)
        near_rsi_top = rsi_current > (rsi_max_val - 10)
        
        short_signal = (rsi_cross_below_overbought or (near_rsi_top and rsi_accelerating_down)) and (price_momentum < 2)
        
        # Execute trades
        if long_signal:
            if self.position.is_short:
                self.position.close()
            if not self.position:
                # Tight stop loss
                stop_loss = price - (atr_value * self.atr_sl_multiplier)
                take_profit = price + (atr_value * self.atr_tp_multiplier)
                self.buy(sl=stop_loss, tp=take_profit)
        
        elif short_signal:
            if self.position.is_long:
                self.position.close()
            if not self.position:
                # Tight stop loss
                stop_loss = price + (atr_value * self.atr_sl_multiplier)
                take_profit = price - (atr_value * self.atr_tp_multiplier)
                self.sell(sl=stop_loss, tp=take_profit)
        
        # Exit conditions based on RSI extremes
        elif self.position:
            if self.position.is_long:
                # Exit if RSI becomes overbought or loses momentum
                if rsi_current > self.rsi_overbought or (rsi_velocity < -2 and rsi_current > 50):
                    self.position.close()
            
            elif self.position.is_short:
                # Exit if RSI becomes oversold or gains momentum
                if rsi_current < self.rsi_oversold or (rsi_velocity > 2 and rsi_current < 50):
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S ACCELERATION RSI STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing RSI Acceleration Strategy across all datasets...")
    print("="*80)
    
    # Run tests on all data sources without optimization
    results = test_on_all_data(
        AccelerationRSIStrategy,
        'AccelerationRSI',
        optimize=False,  # No optimization as requested
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/AccelerationRSI.csv")
        print("="*80)

if __name__ == "__main__":
    main()