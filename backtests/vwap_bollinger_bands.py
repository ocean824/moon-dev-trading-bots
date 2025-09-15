"""
Moon Dev's VWAP + Bollinger Bands Strategy
===========================================
Uses VWAP as dynamic support/resistance combined with BB for volatility-based entries.
Trades the confluence of VWAP levels and Bollinger Band extremes.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class VWAPBollingerStrategy(Strategy):
    """
    VWAP + Bollinger Bands Combined Strategy
    - VWAP provides institutional price levels (support/resistance)
    - Bollinger Bands identify volatility extremes
    - Enters at BB extremes when aligned with VWAP levels
    - High probability setups at confluence zones
    """
    
    # Bollinger Band parameters
    bb_period = 20
    bb_std = 2.0
    bb_squeeze_threshold = 0.02  # Width threshold for squeeze
    
    # VWAP parameters (simplified for backtesting)
    vwap_period = 20  # Rolling period for VWAP calculation
    
    # Volume parameters
    volume_sma_period = 20
    volume_threshold = 1.2  # Volume must be 1.2x average
    
    # Risk management
    atr_period = 14
    atr_stop_multiplier = 2.0
    atr_target_multiplier = 3.0
    
    # Position management
    use_confluence_only = True  # Only trade when VWAP and BB align
    
    def init(self):
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)
        
        # Calculate Bollinger Bands
        bb_result = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        upper_col = f'BBU_{self.bb_period}_{self.bb_std}'
        middle_col = f'BBM_{self.bb_period}_{self.bb_std}'
        lower_col = f'BBL_{self.bb_period}_{self.bb_std}'
        
        self.bb_upper = self.I(lambda: bb_result[upper_col].ffill().values, name='BB_Upper')
        self.bb_middle = self.I(lambda: bb_result[middle_col].ffill().values, name='BB_Middle')
        self.bb_lower = self.I(lambda: bb_result[lower_col].ffill().values, name='BB_Lower')
        
        # BB width for volatility assessment
        bb_width = (bb_result[upper_col] - bb_result[lower_col]) / bb_result[middle_col]
        self.bb_width = self.I(lambda: bb_width.ffill().values, name='BB_Width')
        
        # Calculate VWAP (simplified rolling VWAP for backtesting)
        typical_price = (high + low + close) / 3
        
        # Rolling VWAP calculation
        rolling_tpv = (typical_price * volume).rolling(window=self.vwap_period).sum()
        rolling_volume = volume.rolling(window=self.vwap_period).sum()
        vwap_values = rolling_tpv / rolling_volume
        vwap_values = vwap_values.ffill()
        
        self.vwap = self.I(lambda: vwap_values.values, name='VWAP')
        
        # VWAP Bands (standard deviation bands around VWAP)
        price_vwap_diff = typical_price - vwap_values
        vwap_std = price_vwap_diff.rolling(window=self.vwap_period).std()
        
        self.vwap_upper = self.I(lambda: (vwap_values + 2 * vwap_std).ffill().values, name='VWAP_Upper')
        self.vwap_lower = self.I(lambda: (vwap_values - 2 * vwap_std).ffill().values, name='VWAP_Lower')
        
        # Volume analysis
        self.volume_sma = self.I(ta.sma, volume, self.volume_sma_period)
        
        # ATR for risk management
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # RSI for additional confirmation
        self.rsi = self.I(ta.rsi, close, 14)
        
        # MACD for trend confirmation
        macd_result = ta.macd(close, fast=12, slow=26, signal=9)
        self.macd = self.I(lambda: macd_result['MACD_12_26_9'].ffill().values, name='MACD')
        self.macd_signal = self.I(lambda: macd_result['MACDs_12_26_9'].ffill().values, name='MACD_Signal')
        
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.bb_period, self.vwap_period) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        volume = self.data.Volume[-1]
        
        bb_upper = self.bb_upper[-1]
        bb_middle = self.bb_middle[-1]
        bb_lower = self.bb_lower[-1]
        bb_width = self.bb_width[-1]
        
        vwap_value = self.vwap[-1]
        vwap_upper = self.vwap_upper[-1]
        vwap_lower = self.vwap_lower[-1]
        
        volume_avg = self.volume_sma[-1]
        atr_value = self.atr[-1]
        rsi_value = self.rsi[-1]
        macd_value = self.macd[-1]
        macd_signal_value = self.macd_signal[-1]
        
        # Check for valid values
        if pd.isna(bb_upper) or pd.isna(vwap_value) or pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Calculate volume condition
        volume_condition = volume > (volume_avg * self.volume_threshold) if volume_avg > 0 else False
        
        # Calculate price position relative to indicators
        price_below_vwap = price < vwap_value
        price_above_vwap = price > vwap_value
        
        # Entry logic - Confluence of VWAP and Bollinger Bands
        if not self.position:
            # Long signal: Oversold at confluence of supports
            # Best setup: Price at BB lower AND below/near VWAP lower
            # Conditions:
            # 1. Price touches or breaks below BB lower (oversold)
            # 2. Price near or below VWAP (institutional support)
            # 3. Volume confirmation
            # 4. RSI oversold (< 35)
            # 5. Optional: MACD turning bullish
            
            # Calculate confluence score
            long_confluence = 0
            if price <= bb_lower:
                long_confluence += 2  # Strong oversold signal
            if price <= vwap_value:
                long_confluence += 1  # Below institutional level
            if price <= vwap_lower:
                long_confluence += 2  # Extreme oversold at VWAP lower
            if not pd.isna(rsi_value) and rsi_value < 35:
                long_confluence += 1  # RSI confirms oversold
            if volume_condition:
                long_confluence += 1  # Volume confirms interest
            if not pd.isna(macd_value) and not pd.isna(macd_signal_value) and macd_value > macd_signal_value:
                long_confluence += 1  # MACD bullish
            
            # Require minimum confluence score
            if long_confluence >= 4:
                # Strong reversal setup at support confluence
                stop_loss = min(price - (atr_value * self.atr_stop_multiplier), 
                               min(bb_lower, vwap_lower) - atr_value)
                
                # Target at opposite band or VWAP level
                take_profit = max(bb_upper, vwap_upper, price + (atr_value * self.atr_target_multiplier))
                
                if take_profit > price and stop_loss < price:
                    self.buy(sl=stop_loss, tp=take_profit, size=0.95)
            
            # Short signal: Overbought at confluence of resistances
            # Best setup: Price at BB upper AND above/near VWAP upper
            # Conditions:
            # 1. Price touches or breaks above BB upper (overbought)
            # 2. Price near or above VWAP (institutional resistance)
            # 3. Volume confirmation
            # 4. RSI overbought (> 65)
            # 5. Optional: MACD turning bearish
            
            # Calculate confluence score
            short_confluence = 0
            if price >= bb_upper:
                short_confluence += 2  # Strong overbought signal
            if price >= vwap_value:
                short_confluence += 1  # Above institutional level
            if price >= vwap_upper:
                short_confluence += 2  # Extreme overbought at VWAP upper
            if not pd.isna(rsi_value) and rsi_value > 65:
                short_confluence += 1  # RSI confirms overbought
            if volume_condition:
                short_confluence += 1  # Volume confirms interest
            if not pd.isna(macd_value) and not pd.isna(macd_signal_value) and macd_value < macd_signal_value:
                short_confluence += 1  # MACD bearish
            
            # Require minimum confluence score
            if short_confluence >= 4:
                # Strong reversal setup at resistance confluence
                stop_loss = max(price + (atr_value * self.atr_stop_multiplier), 
                               max(bb_upper, vwap_upper) + atr_value)
                
                # Target at opposite band or VWAP level
                take_profit = min(bb_lower, vwap_lower, price - (atr_value * self.atr_target_multiplier))
                
                if take_profit < price and stop_loss > price:
                    self.sell(sl=stop_loss, tp=take_profit, size=0.95)
        
        # Exit logic
        else:
            # For long positions
            if self.position.is_long:
                # Exit conditions:
                # 1. Price reaches BB upper (target zone)
                # 2. Price reaches VWAP upper (resistance)
                # 3. Price breaks below VWAP (support broken)
                # 4. RSI becomes overbought (> 70)
                if (price >= bb_upper or 
                    price >= vwap_upper or
                    (price < vwap_value and price < bb_middle) or
                    (not pd.isna(rsi_value) and rsi_value > 70)):
                    self.position.close()
            
            # For short positions
            elif self.position.is_short:
                # Exit conditions:
                # 1. Price reaches BB lower (target zone)
                # 2. Price reaches VWAP lower (support)
                # 3. Price breaks above VWAP (resistance broken)
                # 4. RSI becomes oversold (< 30)
                if (price <= bb_lower or 
                    price <= vwap_lower or
                    (price > vwap_value and price > bb_middle) or
                    (not pd.isna(rsi_value) and rsi_value < 30)):
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S VWAP + BOLLINGER BANDS STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing VWAP and Bollinger Bands Confluence across all datasets...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        VWAPBollingerStrategy,
        'VWAPBollinger',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/VWAPBollinger.csv")
        print("="*80)

if __name__ == "__main__":
    main()