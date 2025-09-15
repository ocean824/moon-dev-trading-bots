"""
Moon Dev's VWAP Crossover Strategy
===================================
Buys when price crosses above VWAP with volume confirmation, 
sells on cross below. VWAP acts as dynamic support/resistance.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class VWAPCrossoverStrategy(Strategy):
    """
    VWAP Crossover Strategy
    - VWAP (Volume Weighted Average Price) as dynamic support/resistance
    - Buy when price crosses above VWAP with volume surge
    - Sell when price crosses below VWAP with volume surge
    - Uses volume confirmation and price momentum
    """
    
    # VWAP parameters
    vwap_anchor = 'D'  # Daily anchor (reset daily)
    
    # Volume parameters
    volume_sma_period = 20
    volume_multiplier = 1.5  # Volume must be 1.5x average for confirmation
    
    # Price momentum parameters
    momentum_period = 10
    momentum_threshold = 0.5  # Minimum momentum % for entry
    
    # Risk management
    atr_period = 14
    atr_stop_multiplier = 2.0
    atr_target_multiplier = 3.0
    
    def init(self):
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)
        
        # Calculate VWAP
        # Note: pandas_ta VWAP requires proper implementation
        # Using a custom VWAP calculation for backtesting
        typical_price = (high + low + close) / 3
        cumulative_tpv = (typical_price * volume).cumsum()
        cumulative_volume = volume.cumsum()
        
        # Create daily reset points (simplified for backtesting)
        # In production, this would reset at market open
        vwap_values = cumulative_tpv / cumulative_volume
        vwap_values = vwap_values.ffill()
        
        self.vwap = self.I(lambda: vwap_values.values, name='VWAP')
        
        # Calculate VWAP bands (standard deviation bands)
        price_vwap_diff = typical_price - vwap_values
        squared_diff = price_vwap_diff ** 2
        variance = (squared_diff * volume).rolling(window=20).sum() / volume.rolling(window=20).sum()
        std_dev = np.sqrt(variance.ffill())
        
        self.vwap_upper = self.I(lambda: (vwap_values + 2 * std_dev).ffill().values, name='VWAP_Upper')
        self.vwap_lower = self.I(lambda: (vwap_values - 2 * std_dev).ffill().values, name='VWAP_Lower')
        
        # Volume analysis
        self.volume_sma = self.I(ta.sma, volume, self.volume_sma_period)
        
        # Price momentum (ROC - Rate of Change)
        self.momentum = self.I(ta.roc, close, self.momentum_period)
        
        # ATR for risk management
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # RSI for overbought/oversold conditions
        self.rsi = self.I(ta.rsi, close, 14)
        
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.volume_sma_period, self.momentum_period) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        volume = self.data.Volume[-1]
        vwap_value = self.vwap[-1]
        vwap_upper = self.vwap_upper[-1]
        vwap_lower = self.vwap_lower[-1]
        volume_avg = self.volume_sma[-1]
        momentum_value = self.momentum[-1]
        atr_value = self.atr[-1]
        rsi_value = self.rsi[-1]
        
        # Check for valid values
        if pd.isna(vwap_value) or pd.isna(volume_avg) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Get previous values for crossover detection
        if len(self.data.Close) > 1:
            prev_close = self.data.Close[-2]
            prev_vwap = self.vwap[-2]
        else:
            return
        
        # Calculate volume surge
        volume_surge = volume > (volume_avg * self.volume_multiplier) if volume_avg > 0 else False
        
        # Entry logic - VWAP Crossover with Volume Confirmation
        if not self.position:
            # Long signal: Price crosses above VWAP with volume surge
            # Additional filters:
            # - Positive momentum
            # - Not overbought (RSI < 70)
            # - Volume confirmation
            if (prev_close <= prev_vwap and 
                price > vwap_value and 
                volume_surge and
                (pd.isna(momentum_value) or momentum_value > self.momentum_threshold) and
                (pd.isna(rsi_value) or rsi_value < 70)):
                
                # Stop loss below VWAP or recent low
                stop_loss = min(vwap_value - (atr_value * self.atr_stop_multiplier), 
                               self.data.Low[-1] - atr_value)
                
                # Target at VWAP upper band or ATR-based
                take_profit = max(vwap_upper, price + (atr_value * self.atr_target_multiplier))
                
                if take_profit > price and stop_loss < price:
                    self.buy(sl=stop_loss, tp=take_profit, size=0.95)
            
            # Short signal: Price crosses below VWAP with volume surge
            # Additional filters:
            # - Negative momentum
            # - Not oversold (RSI > 30)
            # - Volume confirmation
            elif (prev_close >= prev_vwap and 
                  price < vwap_value and 
                  volume_surge and
                  (pd.isna(momentum_value) or momentum_value < -self.momentum_threshold) and
                  (pd.isna(rsi_value) or rsi_value > 30)):
                
                # Stop loss above VWAP or recent high
                stop_loss = max(vwap_value + (atr_value * self.atr_stop_multiplier), 
                               self.data.High[-1] + atr_value)
                
                # Target at VWAP lower band or ATR-based
                take_profit = min(vwap_lower, price - (atr_value * self.atr_target_multiplier))
                
                if take_profit < price and stop_loss > price:
                    self.sell(sl=stop_loss, tp=take_profit, size=0.95)
        
        # Dynamic exit logic
        else:
            # For long positions
            if self.position.is_long:
                # Exit conditions:
                # 1. Price crosses back below VWAP (trend reversal)
                # 2. Price reaches upper band (overbought)
                # 3. Momentum turns negative
                if (price < vwap_value or 
                    price >= vwap_upper or 
                    (not pd.isna(momentum_value) and momentum_value < -self.momentum_threshold)):
                    self.position.close()
            
            # For short positions
            elif self.position.is_short:
                # Exit conditions:
                # 1. Price crosses back above VWAP (trend reversal)
                # 2. Price reaches lower band (oversold)
                # 3. Momentum turns positive
                if (price > vwap_value or 
                    price <= vwap_lower or 
                    (not pd.isna(momentum_value) and momentum_value > self.momentum_threshold)):
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S VWAP CROSSOVER STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing VWAP Crossover with Volume Confirmation across all datasets...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        VWAPCrossoverStrategy,
        'VWAPCrossover',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/VWAPCrossover.csv")
        print("="*80)

if __name__ == "__main__":
    main()