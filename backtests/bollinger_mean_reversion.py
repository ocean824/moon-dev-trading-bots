"""
Moon Dev's Bollinger Band Mean Reversion Strategy
==================================================
Classic BB mean reversion strategy that buys when price touches lower band 
and sells at upper band, expecting price to revert to the mean.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class BollingerMeanReversionStrategy(Strategy):
    """
    Bollinger Band Mean Reversion Strategy
    - Buys when price touches/crosses below lower band (oversold)
    - Sells when price touches/crosses above upper band (overbought)
    - Uses ATR-based stop losses for risk management
    - Optional: Exit at middle band for quicker profits
    """
    
    # Bollinger Band parameters
    bb_period = 20
    bb_std = 2.0
    
    # Risk management
    atr_period = 14
    atr_multiplier = 2.0
    use_middle_exit = True  # Exit at middle band vs opposite band
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Calculate Bollinger Bands
        bb_result = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        
        # Extract bands
        upper_col = f'BBU_{self.bb_period}_{self.bb_std}'
        middle_col = f'BBM_{self.bb_period}_{self.bb_std}'
        lower_col = f'BBL_{self.bb_period}_{self.bb_std}'
        
        self.bb_upper = self.I(lambda: bb_result[upper_col].ffill().values, name='BB_Upper')
        self.bb_middle = self.I(lambda: bb_result[middle_col].ffill().values, name='BB_Middle')
        self.bb_lower = self.I(lambda: bb_result[lower_col].ffill().values, name='BB_Lower')
        
        # Calculate BB width for volatility assessment
        bb_width = bb_result[upper_col] - bb_result[lower_col]
        self.bb_width = self.I(lambda: bb_width.ffill().values, name='BB_Width')
        
        # ATR for risk management
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # RSI for additional confirmation (optional)
        self.rsi = self.I(ta.rsi, close, 14)
        
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < self.bb_period + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        upper_band = self.bb_upper[-1]
        middle_band = self.bb_middle[-1]
        lower_band = self.bb_lower[-1]
        bb_width = self.bb_width[-1]
        atr_value = self.atr[-1]
        rsi_value = self.rsi[-1]
        
        # Check for valid values
        if pd.isna(upper_band) or pd.isna(middle_band) or pd.isna(lower_band) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Previous values for crossover detection
        if len(self.data.Close) > 1:
            prev_close = self.data.Close[-2]
            prev_upper = self.bb_upper[-2]
            prev_lower = self.bb_lower[-2]
        else:
            return
            
        # Entry logic - Mean Reversion
        if not self.position:
            # Long signal: Price touches or goes below lower band (oversold)
            # Additional filter: RSI < 35 for confirmation
            if price <= lower_band and (pd.isna(rsi_value) or rsi_value < 35):
                # Mean reversion expects price to bounce back up
                stop_loss = price - (atr_value * self.atr_multiplier)
                
                # Take profit at middle or upper band
                if self.use_middle_exit:
                    take_profit = middle_band
                else:
                    take_profit = upper_band
                    
                if take_profit > price:  # Ensure TP is above entry
                    self.buy(sl=stop_loss, tp=take_profit, size=0.95)
            
            # Short signal: Price touches or goes above upper band (overbought)
            # Additional filter: RSI > 65 for confirmation
            elif price >= upper_band and (pd.isna(rsi_value) or rsi_value > 65):
                # Mean reversion expects price to pull back down
                stop_loss = price + (atr_value * self.atr_multiplier)
                
                # Take profit at middle or lower band
                if self.use_middle_exit:
                    take_profit = middle_band
                else:
                    take_profit = lower_band
                    
                if take_profit < price:  # Ensure TP is below entry
                    self.sell(sl=stop_loss, tp=take_profit, size=0.95)
        
        # Dynamic exit logic (if not using fixed TP)
        else:
            # For long positions
            if self.position.is_long:
                # Exit if price reaches upper band (full mean reversion)
                if price >= upper_band:
                    self.position.close()
                # Or exit at middle band for quicker profits
                elif self.use_middle_exit and price >= middle_band:
                    self.position.close()
                # Emergency exit if price breaks far below lower band
                elif price < lower_band - (atr_value * 0.5):
                    self.position.close()
            
            # For short positions
            elif self.position.is_short:
                # Exit if price reaches lower band (full mean reversion)
                if price <= lower_band:
                    self.position.close()
                # Or exit at middle band for quicker profits
                elif self.use_middle_exit and price <= middle_band:
                    self.position.close()
                # Emergency exit if price breaks far above upper band
                elif price > upper_band + (atr_value * 0.5):
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S BOLLINGER MEAN REVERSION STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Bollinger Band Mean Reversion across all datasets...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        BollingerMeanReversionStrategy,
        'BollingerMeanReversion',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/BollingerMeanReversion.csv")
        print("="*80)

if __name__ == "__main__":
    main()