"""
Moon Dev's Bollinger + ADX Combo Strategy
==========================================
Combines BB squeeze detection with ADX trend strength for high probability trades.
Enters when BB squeeze releases with strong ADX confirmation.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class BollingerADXComboStrategy(Strategy):
    """
    Bollinger Bands + ADX Combination Strategy
    - Detects Bollinger Band squeeze (low volatility periods)
    - Uses ADX to confirm trend strength when squeeze releases
    - Enters positions when squeeze breaks with strong directional movement
    - Combines volatility and trend strength for high probability setups
    """
    
    # Bollinger Band parameters
    bb_period = 20
    bb_std = 2.0
    squeeze_threshold = 0.025  # BB width as % of price for squeeze detection
    
    # ADX parameters
    adx_period = 14
    adx_threshold = 25  # Minimum ADX for trend confirmation
    di_diff_threshold = 5  # Minimum DI difference
    
    # Keltner Channel for squeeze detection
    kc_period = 20
    kc_multiplier = 1.5
    
    # Risk management
    atr_period = 14
    atr_stop_multiplier = 2.0
    atr_target_multiplier = 3.5
    
    def init(self):
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        
        # Calculate Bollinger Bands
        bb_result = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        upper_col = f'BBU_{self.bb_period}_{self.bb_std}'
        middle_col = f'BBM_{self.bb_period}_{self.bb_std}'
        lower_col = f'BBL_{self.bb_period}_{self.bb_std}'
        
        self.bb_upper = self.I(lambda: bb_result[upper_col].ffill().values, name='BB_Upper')
        self.bb_middle = self.I(lambda: bb_result[middle_col].ffill().values, name='BB_Middle')
        self.bb_lower = self.I(lambda: bb_result[lower_col].ffill().values, name='BB_Lower')
        
        # Calculate BB width for squeeze detection
        bb_width = (bb_result[upper_col] - bb_result[lower_col]) / bb_result[middle_col]
        self.bb_width_pct = self.I(lambda: bb_width.ffill().values, name='BB_Width_Pct')
        
        # Calculate Keltner Channels for squeeze comparison
        kc_result = ta.kc(high, low, close, length=self.kc_period, scalar=self.kc_multiplier)
        self.kc_upper = self.I(lambda: kc_result[f'KCUe_{self.kc_period}_{self.kc_multiplier}'].ffill().values, name='KC_Upper')
        self.kc_lower = self.I(lambda: kc_result[f'KCLe_{self.kc_period}_{self.kc_multiplier}'].ffill().values, name='KC_Lower')
        
        # Calculate ADX and DI indicators
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        self.adx = self.I(lambda: adx_result[f'ADX_{self.adx_period}'].ffill().values, name='ADX')
        self.di_plus = self.I(lambda: adx_result[f'DMP_{self.adx_period}'].ffill().values, name='DI_Plus')
        self.di_minus = self.I(lambda: adx_result[f'DMN_{self.adx_period}'].ffill().values, name='DI_Minus')
        
        # ATR for risk management
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # Momentum oscillator for additional confirmation
        self.momentum = self.I(ta.mom, close, 10)
        
        # Track squeeze state
        self.in_squeeze = False
        self.squeeze_count = 0
        
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.bb_period, self.adx_period) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        bb_upper = self.bb_upper[-1]
        bb_middle = self.bb_middle[-1]
        bb_lower = self.bb_lower[-1]
        bb_width = self.bb_width_pct[-1]
        kc_upper = self.kc_upper[-1]
        kc_lower = self.kc_lower[-1]
        adx_value = self.adx[-1]
        di_plus_value = self.di_plus[-1]
        di_minus_value = self.di_minus[-1]
        atr_value = self.atr[-1]
        momentum_value = self.momentum[-1]
        
        # Check for valid values
        if pd.isna(bb_upper) or pd.isna(adx_value) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Get previous values
        if len(self.data.Close) > 1:
            prev_bb_width = self.bb_width_pct[-2]
            prev_close = self.data.Close[-2]
            prev_adx = self.adx[-2]
        else:
            return
        
        # Detect Bollinger Band Squeeze
        # Squeeze occurs when BB is inside KC
        current_squeeze = (bb_upper < kc_upper) and (bb_lower > kc_lower)
        
        # Alternative squeeze detection using BB width
        width_squeeze = bb_width < self.squeeze_threshold
        
        # Combine both squeeze conditions
        is_squeeze = current_squeeze or width_squeeze
        
        # Track squeeze duration
        if is_squeeze:
            self.squeeze_count += 1
        else:
            # Squeeze just released
            if self.squeeze_count > 3:  # Minimum squeeze duration
                self.in_squeeze = False
            self.squeeze_count = 0
        
        # Calculate DI difference for direction
        di_diff = di_plus_value - di_minus_value
        
        # Entry logic - Squeeze Release with ADX Confirmation
        if not self.position:
            # Long signal: Squeeze release with bullish breakout
            # Conditions:
            # 1. Squeeze was active for at least 3 bars and just released
            # 2. ADX > threshold (strong trend)
            # 3. DI+ > DI- (uptrend direction)
            # 4. Price breaks above BB upper or middle
            # 5. Positive momentum
            if (self.squeeze_count == 0 and prev_bb_width < self.squeeze_threshold and 
                bb_width > self.squeeze_threshold and
                adx_value > self.adx_threshold and
                di_plus_value > di_minus_value and
                di_diff > self.di_diff_threshold and
                price > bb_middle and
                (pd.isna(momentum_value) or momentum_value > 0)):
                
                # Strong setup - price breaking out with volatility expansion
                stop_loss = min(bb_lower, price - (atr_value * self.atr_stop_multiplier))
                take_profit = price + (atr_value * self.atr_target_multiplier)
                
                if take_profit > price and stop_loss < price:
                    self.buy(sl=stop_loss, tp=take_profit, size=0.95)
            
            # Short signal: Squeeze release with bearish breakout
            # Conditions:
            # 1. Squeeze was active for at least 3 bars and just released
            # 2. ADX > threshold (strong trend)
            # 3. DI- > DI+ (downtrend direction)
            # 4. Price breaks below BB lower or middle
            # 5. Negative momentum
            elif (self.squeeze_count == 0 and prev_bb_width < self.squeeze_threshold and 
                  bb_width > self.squeeze_threshold and
                  adx_value > self.adx_threshold and
                  di_minus_value > di_plus_value and
                  abs(di_diff) > self.di_diff_threshold and
                  price < bb_middle and
                  (pd.isna(momentum_value) or momentum_value < 0)):
                
                # Strong setup - price breaking down with volatility expansion
                stop_loss = max(bb_upper, price + (atr_value * self.atr_stop_multiplier))
                take_profit = price - (atr_value * self.atr_target_multiplier)
                
                if take_profit < price and stop_loss > price:
                    self.sell(sl=stop_loss, tp=take_profit, size=0.95)
        
        # Exit logic
        else:
            # For long positions
            if self.position.is_long:
                # Exit conditions:
                # 1. ADX falls below 20 (trend weakening)
                # 2. DI- crosses above DI+ (trend reversal)
                # 3. Price falls back below BB middle (momentum loss)
                # 4. New squeeze forming (volatility contraction)
                if (adx_value < 20 or 
                    di_minus_value > di_plus_value or
                    price < bb_middle or
                    is_squeeze):
                    self.position.close()
            
            # For short positions
            elif self.position.is_short:
                # Exit conditions:
                # 1. ADX falls below 20 (trend weakening)
                # 2. DI+ crosses above DI- (trend reversal)
                # 3. Price rises back above BB middle (momentum loss)
                # 4. New squeeze forming (volatility contraction)
                if (adx_value < 20 or 
                    di_plus_value > di_minus_value or
                    price > bb_middle or
                    is_squeeze):
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S BOLLINGER + ADX COMBO STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Bollinger Squeeze with ADX Trend Confirmation across all datasets...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        BollingerADXComboStrategy,
        'BollingerADXCombo',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/BollingerADXCombo.csv")
        print("="*80)

if __name__ == "__main__":
    main()