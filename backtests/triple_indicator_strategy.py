"""
Moon Dev's Triple Indicator Strategy
=====================================
Combines all three: ADX for trend strength, BB for volatility zones, 
VWAP for institutional levels. Trades only when all three align.
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data
import warnings
warnings.filterwarnings('ignore')

class TripleIndicatorStrategy(Strategy):
    """
    Triple Indicator Strategy (ADX + BB + VWAP)
    - ADX confirms trend strength and direction
    - Bollinger Bands identify volatility zones and entry points
    - VWAP provides institutional support/resistance levels
    - Only trades when all three indicators align for maximum probability
    """
    
    # ADX parameters
    adx_period = 14
    adx_threshold = 25  # Minimum for trend strength
    di_diff_threshold = 5  # Minimum DI difference
    
    # Bollinger Band parameters
    bb_period = 20
    bb_std = 2.0
    bb_squeeze_factor = 0.025  # For squeeze detection
    
    # VWAP parameters
    vwap_period = 20  # Rolling VWAP period
    vwap_band_std = 2.0  # Standard deviation for VWAP bands
    
    # Volume parameters
    volume_period = 20
    volume_multiplier = 1.3  # Volume surge threshold
    
    # Risk management
    atr_period = 14
    atr_stop_multiplier = 2.0
    atr_target_multiplier = 3.5
    
    # Scoring system
    min_score_entry = 7  # Minimum score needed to enter trade
    
    def init(self):
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)
        
        # 1. ADX and Directional Indicators
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        self.adx = self.I(lambda: adx_result[f'ADX_{self.adx_period}'].ffill().values, name='ADX')
        self.di_plus = self.I(lambda: adx_result[f'DMP_{self.adx_period}'].ffill().values, name='DI_Plus')
        self.di_minus = self.I(lambda: adx_result[f'DMN_{self.adx_period}'].ffill().values, name='DI_Minus')
        
        # 2. Bollinger Bands
        bb_result = ta.bbands(close, length=self.bb_period, std=self.bb_std)
        upper_col = f'BBU_{self.bb_period}_{self.bb_std}'
        middle_col = f'BBM_{self.bb_period}_{self.bb_std}'
        lower_col = f'BBL_{self.bb_period}_{self.bb_std}'
        
        self.bb_upper = self.I(lambda: bb_result[upper_col].ffill().values, name='BB_Upper')
        self.bb_middle = self.I(lambda: bb_result[middle_col].ffill().values, name='BB_Middle')
        self.bb_lower = self.I(lambda: bb_result[lower_col].ffill().values, name='BB_Lower')
        
        # BB width and %B
        bb_width = (bb_result[upper_col] - bb_result[lower_col]) / bb_result[middle_col]
        self.bb_width = self.I(lambda: bb_width.ffill().values, name='BB_Width')
        
        # %B indicator (position within bands)
        percent_b = (close - bb_result[lower_col]) / (bb_result[upper_col] - bb_result[lower_col])
        self.percent_b = self.I(lambda: percent_b.ffill().values, name='Percent_B')
        
        # 3. VWAP with bands
        typical_price = (high + low + close) / 3
        
        # Rolling VWAP
        rolling_tpv = (typical_price * volume).rolling(window=self.vwap_period).sum()
        rolling_volume = volume.rolling(window=self.vwap_period).sum()
        vwap_values = rolling_tpv / rolling_volume
        vwap_values = vwap_values.ffill()
        
        self.vwap = self.I(lambda: vwap_values.values, name='VWAP')
        
        # VWAP Bands
        price_vwap_diff = typical_price - vwap_values
        vwap_std = price_vwap_diff.rolling(window=self.vwap_period).std()
        
        self.vwap_upper = self.I(lambda: (vwap_values + self.vwap_band_std * vwap_std).ffill().values, name='VWAP_Upper')
        self.vwap_lower = self.I(lambda: (vwap_values - self.vwap_band_std * vwap_std).ffill().values, name='VWAP_Lower')
        
        # 4. Supporting indicators
        self.volume_sma = self.I(ta.sma, volume, self.volume_period)
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        self.rsi = self.I(ta.rsi, close, 14)
        
        # MACD for additional trend confirmation
        macd_result = ta.macd(close, fast=12, slow=26, signal=9)
        self.macd = self.I(lambda: macd_result['MACD_12_26_9'].ffill().values, name='MACD')
        self.macd_signal = self.I(lambda: macd_result['MACDs_12_26_9'].ffill().values, name='MACD_Signal')
        self.macd_hist = self.I(lambda: macd_result['MACDh_12_26_9'].ffill().values, name='MACD_Hist')
        
    def calculate_signal_score(self, is_long=True):
        """Calculate a score based on all three indicators alignment"""
        score = 0
        
        # Get current values
        price = self.data.Close[-1]
        adx_value = self.adx[-1]
        di_plus_value = self.di_plus[-1]
        di_minus_value = self.di_minus[-1]
        bb_upper = self.bb_upper[-1]
        bb_middle = self.bb_middle[-1]
        bb_lower = self.bb_lower[-1]
        bb_width = self.bb_width[-1]
        percent_b = self.percent_b[-1]
        vwap_value = self.vwap[-1]
        vwap_upper = self.vwap_upper[-1]
        vwap_lower = self.vwap_lower[-1]
        volume = self.data.Volume[-1]
        volume_avg = self.volume_sma[-1]
        rsi_value = self.rsi[-1]
        macd_value = self.macd[-1]
        macd_signal_value = self.macd_signal[-1]
        macd_hist_value = self.macd_hist[-1]
        
        if is_long:
            # ADX scoring (max 3 points)
            if not pd.isna(adx_value) and adx_value > self.adx_threshold:
                score += 1.5  # Strong trend
            if not pd.isna(di_plus_value) and not pd.isna(di_minus_value):
                if di_plus_value > di_minus_value and (di_plus_value - di_minus_value) > self.di_diff_threshold:
                    score += 1.5  # Bullish direction confirmed
            
            # Bollinger Bands scoring (max 3 points)
            if not pd.isna(percent_b):
                if percent_b <= 0.2:  # Near or below lower band
                    score += 1.5  # Oversold
                if price <= bb_lower:
                    score += 1  # Touching lower band
                if not pd.isna(bb_width) and bb_width < self.bb_squeeze_factor:
                    score += 0.5  # Squeeze condition (volatility expansion coming)
            
            # VWAP scoring (max 3 points)
            if not pd.isna(vwap_value):
                if price < vwap_value:
                    score += 1  # Below VWAP (potential support)
                if price <= vwap_lower:
                    score += 1.5  # At VWAP lower band (strong support)
                if price > vwap_value * 0.98 and price < vwap_value * 1.02:
                    score += 0.5  # Near VWAP (institutional level)
            
            # Additional confirmations (max 3 points)
            if not pd.isna(volume_avg) and volume > volume_avg * self.volume_multiplier:
                score += 1  # Volume surge
            if not pd.isna(rsi_value) and rsi_value < 35:
                score += 1  # RSI oversold
            if not pd.isna(macd_hist_value) and macd_hist_value > 0:
                score += 1  # MACD bullish
                
        else:  # Short signal scoring
            # ADX scoring (max 3 points)
            if not pd.isna(adx_value) and adx_value > self.adx_threshold:
                score += 1.5  # Strong trend
            if not pd.isna(di_plus_value) and not pd.isna(di_minus_value):
                if di_minus_value > di_plus_value and (di_minus_value - di_plus_value) > self.di_diff_threshold:
                    score += 1.5  # Bearish direction confirmed
            
            # Bollinger Bands scoring (max 3 points)
            if not pd.isna(percent_b):
                if percent_b >= 0.8:  # Near or above upper band
                    score += 1.5  # Overbought
                if price >= bb_upper:
                    score += 1  # Touching upper band
                if not pd.isna(bb_width) and bb_width < self.bb_squeeze_factor:
                    score += 0.5  # Squeeze condition
            
            # VWAP scoring (max 3 points)
            if not pd.isna(vwap_value):
                if price > vwap_value:
                    score += 1  # Above VWAP (potential resistance)
                if price >= vwap_upper:
                    score += 1.5  # At VWAP upper band (strong resistance)
                if price > vwap_value * 0.98 and price < vwap_value * 1.02:
                    score += 0.5  # Near VWAP
            
            # Additional confirmations (max 3 points)
            if not pd.isna(volume_avg) and volume > volume_avg * self.volume_multiplier:
                score += 1  # Volume surge
            if not pd.isna(rsi_value) and rsi_value > 65:
                score += 1  # RSI overbought
            if not pd.isna(macd_hist_value) and macd_hist_value < 0:
                score += 1  # MACD bearish
        
        return score
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.bb_period, self.adx_period, self.vwap_period) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        atr_value = self.atr[-1]
        
        # Check for valid ATR
        if pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Entry logic - Triple confirmation required
        if not self.position:
            # Calculate scores for both directions
            long_score = self.calculate_signal_score(is_long=True)
            short_score = self.calculate_signal_score(is_long=False)
            
            # Long entry
            if long_score >= self.min_score_entry:
                # Strong bullish setup with triple confirmation
                bb_lower = self.bb_lower[-1]
                vwap_lower = self.vwap_lower[-1]
                
                # Stop loss at the lowest support level minus ATR
                stop_loss = min(bb_lower, vwap_lower, price - (atr_value * self.atr_stop_multiplier))
                
                # Take profit at resistance levels
                bb_upper = self.bb_upper[-1]
                vwap_upper = self.vwap_upper[-1]
                take_profit = max(bb_upper, vwap_upper, price + (atr_value * self.atr_target_multiplier))
                
                if take_profit > price and stop_loss < price:
                    self.buy(sl=stop_loss, tp=take_profit, size=0.95)
            
            # Short entry
            elif short_score >= self.min_score_entry:
                # Strong bearish setup with triple confirmation
                bb_upper = self.bb_upper[-1]
                vwap_upper = self.vwap_upper[-1]
                
                # Stop loss at the highest resistance level plus ATR
                stop_loss = max(bb_upper, vwap_upper, price + (atr_value * self.atr_stop_multiplier))
                
                # Take profit at support levels
                bb_lower = self.bb_lower[-1]
                vwap_lower = self.vwap_lower[-1]
                take_profit = min(bb_lower, vwap_lower, price - (atr_value * self.atr_target_multiplier))
                
                if take_profit < price and stop_loss > price:
                    self.sell(sl=stop_loss, tp=take_profit, size=0.95)
        
        # Exit logic - Any indicator divergence
        else:
            # Recalculate scores to check if conditions still valid
            if self.position.is_long:
                current_score = self.calculate_signal_score(is_long=True)
                opposite_score = self.calculate_signal_score(is_long=False)
                
                # Exit if:
                # 1. Long score drops significantly
                # 2. Short score becomes strong
                # 3. Price reaches target zones
                bb_upper = self.bb_upper[-1]
                vwap_upper = self.vwap_upper[-1]
                
                if (current_score < 3 or 
                    opposite_score > 5 or
                    price >= bb_upper or
                    price >= vwap_upper):
                    self.position.close()
            
            elif self.position.is_short:
                current_score = self.calculate_signal_score(is_long=False)
                opposite_score = self.calculate_signal_score(is_long=True)
                
                # Exit if:
                # 1. Short score drops significantly
                # 2. Long score becomes strong
                # 3. Price reaches target zones
                bb_lower = self.bb_lower[-1]
                vwap_lower = self.vwap_lower[-1]
                
                if (current_score < 3 or 
                    opposite_score > 5 or
                    price <= bb_lower or
                    price <= vwap_lower):
                    self.position.close()

def main():
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("MOON DEV'S TRIPLE INDICATOR STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing ADX + Bollinger Bands + VWAP Combined Strategy across all datasets...")
    print("="*80)
    
    # Run tests on all data sources
    results = test_on_all_data(
        TripleIndicatorStrategy,
        'TripleIndicator',
        optimize=False,
        cash=10000000,
        commission=0.00045,
        verbose=True
    )
    
    if results is not None:
        print("\n" + "="*80)
        print("TESTING COMPLETE!")
        print(f"Results saved to: results/TripleIndicator.csv")
        print("="*80)

if __name__ == "__main__":
    main()