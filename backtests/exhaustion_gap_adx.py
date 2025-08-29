"""
🌙 Moon Dev's Exhaustion Gap + ADX Strategy
============================================
Combines exhaustion gaps with ADX for trend strength confirmation
Tests across all datasets with FULL stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import DATA_SOURCES, load_data_universal
import warnings
warnings.filterwarnings('ignore')

class ExhaustionGapADXStrategy(Strategy):
    """
    Exhaustion Gap + ADX Strategy
    Uses ADX to confirm trend strength before taking gap reversal trades
    """
    
    # Gap parameters
    gap_threshold = 0.0001  # Minimum gap size (0.01% - more reasonable for crypto)
    
    # ADX parameters
    adx_period = 14       # ADX period
    adx_threshold = 25    # ADX above this = strong trend
    adx_exhaustion = 40   # ADX above this = potential exhaustion
    
    # Trend parameters  
    trend_period = 20     # SMA period for trend identification
    trend_lookback = 10  # Bars to look back for trend assessment
    
    # Volume parameters
    volume_period = 20    # Period for volume average
    volume_multiplier = 1.5  # Volume spike threshold
    
    # Confirmation parameters
    confirmation_bars = 2  # Bars to wait for confirmation
    
    # Risk management
    use_sl = True
    atr_period = 14
    atr_multiplier_sl = 2.0
    atr_multiplier_tp = 3.0
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        open_price = pd.Series(self.data.Open)
        
        # Trend indicator
        self.sma = self.I(ta.sma, close, self.trend_period)
        
        # ADX for trend strength
        adx_result = ta.adx(high, low, close, length=self.adx_period)
        self.adx = self.I(lambda: adx_result[f'ADX_{self.adx_period}'].values, name='ADX')
        self.plus_di = self.I(lambda: adx_result[f'DMP_{self.adx_period}'].values, name='+DI')
        self.minus_di = self.I(lambda: adx_result[f'DMN_{self.adx_period}'].values, name='-DI')
        
        # Volume average
        self.volume_avg = self.I(ta.sma, volume, self.volume_period)
        
        # ATR for stops
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
        
        # Gap detection
        gaps = (open_price - close.shift(1)) / close.shift(1)
        gaps = gaps.fillna(0)  # Fill NaN values
        self.gaps = self.I(lambda: gaps.values, name='Gaps')
        
        # Volume spike detection - calculate properly
        volume_avg_series = ta.sma(volume, self.volume_period)
        volume_spike = (volume / volume_avg_series) > self.volume_multiplier
        volume_spike = volume_spike.fillna(False)
        self.volume_spike = self.I(lambda: volume_spike.values, name='VolumeSpike')
        
        # Trend strength (distance from SMA)
        sma_series = ta.sma(close, self.trend_period)
        trend_strength = (close - sma_series) / sma_series
        trend_strength = trend_strength.fillna(0)
        self.trend_strength = self.I(lambda: trend_strength.values, name='TrendStrength')
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.trend_period, self.volume_period, self.atr_period, self.adx_period) + 5:
            return
        
        # Get current values
        price = self.data.Close[-1]
        gap = self.gaps[-1]
        adx_val = self.adx[-1]
        plus_di_val = self.plus_di[-1]
        minus_di_val = self.minus_di[-1]
        
        # Check for valid values
        if pd.isna(gap) or pd.isna(self.sma[-1]) or pd.isna(self.atr[-1]) or pd.isna(adx_val):
            return
        
        # === ADX TREND ANALYSIS ===
        
        # Strong trend exists when ADX is above threshold
        strong_trend = adx_val > self.adx_threshold
        
        # Exhaustion occurs when ADX is very high
        trend_exhaustion = adx_val > self.adx_exhaustion
        
        # Trend direction based on DI lines
        bullish_trend = plus_di_val > minus_di_val
        bearish_trend = minus_di_val > plus_di_val
        
        # === EXHAUSTION GAP DETECTION - LONG SIGNALS ===
        
        # 1. Check for downtrend (simplified)
        downtrend = price < self.sma[-1] * 0.99  # Price at least 1% below SMA
        
        # 2. Detect bullish exhaustion gap
        bullish_gap = gap > self.gap_threshold
        
        # 3. Volume confirmation (simplified)
        volume_confirmed = self.volume_spike[-1] if not pd.isna(self.volume_spike[-1]) else True
        
        # 4. Trend exhaustion confirmation for long (simplified)
        oversold = self.trend_strength[-1] < -0.01  # Currently oversold
        
        # 6. ADX confirmation for long
        # Best setup: High ADX (exhaustion) in bearish trend
        adx_long_confirm = (trend_exhaustion and bearish_trend) or (adx_val < self.adx_threshold)
        
        # Combined long signal with ADX (simplified)
        long_signal = (downtrend and bullish_gap and oversold and adx_long_confirm)
        
        # === EXHAUSTION GAP DETECTION - SHORT SIGNALS ===
        
        # 1. Check for uptrend (simplified)
        uptrend = price > self.sma[-1] * 1.01  # Price at least 1% above SMA
        
        # 2. Detect bearish exhaustion gap
        bearish_gap = gap < -self.gap_threshold
        
        # 4. Trend exhaustion confirmation for short (simplified)
        overbought = self.trend_strength[-1] > 0.01  # Currently overbought
        
        # 6. ADX confirmation for short
        # Best setup: High ADX (exhaustion) in bullish trend
        adx_short_confirm = (trend_exhaustion and bullish_trend) or (adx_val < self.adx_threshold)
        
        # Combined short signal with ADX (simplified)
        short_signal = (uptrend and bearish_gap and overbought and adx_short_confirm)
        
        # === EXECUTE TRADES ===
        
        atr_value = self.atr[-1]
        if pd.isna(atr_value) or atr_value <= 0:
            return
        
        # Long entry
        if long_signal:
            if self.position.is_short:
                self.position.close()
            if not self.position:
                if self.use_sl:
                    stop_loss = price - (atr_value * self.atr_multiplier_sl)
                    take_profit = price + (atr_value * self.atr_multiplier_tp)
                    self.buy(sl=stop_loss, tp=take_profit)
                else:
                    self.buy()
        
        # Short entry
        elif short_signal:
            if self.position.is_long:
                self.position.close()
            if not self.position:
                if self.use_sl:
                    stop_loss = price + (atr_value * self.atr_multiplier_sl)
                    take_profit = price - (atr_value * self.atr_multiplier_tp)
                    self.sell(sl=stop_loss, tp=take_profit)
                else:
                    self.sell()
        
        # Exit conditions with ADX
        if self.position:
            # Exit long positions
            if self.position.is_long:
                # Exit if trend reversal complete or ADX shows new trend
                exit_signal = (price > self.sma[-1] * 1.01) or (adx_val > self.adx_threshold and bearish_trend)
                
                if exit_signal:
                    self.position.close()
            
            # Exit short positions
            elif self.position.is_short:
                # Exit if trend reversal complete or ADX shows new trend
                exit_signal = (price < self.sma[-1] * 0.99) or (adx_val > self.adx_threshold and bullish_trend)
                
                if exit_signal:
                    self.position.close()

def test_single_dataset(name, path, data_type):
    """Test strategy on a single dataset and print FULL stats"""
    try:
        # Load data
        data = load_data_universal(path, data_type)
        
        if data is None or len(data) < 100:
            return None
            
        # Sort index
        data = data.sort_index()
        
        # Initialize backtest
        bt = Backtest(data, ExhaustionGapADXStrategy, 
                     cash=100000, 
                     commission=.002,
                     exclusive_orders=True)
        
        # Run backtest
        stats = bt.run()
        
        # Print FULL stats for this dataset
        print(f"\n{'='*80}")
        print(f"FULL STATS FOR: {name}")
        print('='*80)
        print(stats)
        print('='*80)
        
        # Create summary for DataFrame
        result = {
            'Dataset': name,
            'Return %': round(stats['Return [%]'], 2),
            'Buy & Hold %': round(stats['Buy & Hold Return [%]'], 2),
            'Sharpe': round(stats['Sharpe Ratio'], 2) if pd.notna(stats['Sharpe Ratio']) else 0,
            'Sortino': round(stats['Sortino Ratio'], 2) if pd.notna(stats['Sortino Ratio']) else 0,
            'Max Drawdown %': round(stats['Max. Drawdown [%]'], 2),
            'Win Rate %': round(stats['Win Rate [%]'], 2) if pd.notna(stats['Win Rate [%]']) else 0,
            '# Trades': stats['# Trades'],
            'Avg Trade %': round(stats['Avg. Trade [%]'], 2) if pd.notna(stats['Avg. Trade [%]']) else 0,
        }
        
        return result
        
    except Exception as e:
        print(f"  ⚠️ Error testing {name}: {str(e)}")
        return None

def main():
    """Main function to run multi-data testing with FULL stats output"""
    print("\n" + "="*80)
    print("🌙 MOON DEV'S EXHAUSTION GAP + ADX - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Exhaustion Gap + ADX Strategy")
    print("Showing FULL STATS for each dataset...")
    print("="*80)
    
    results = []
    
    # Test on all datasets
    for name, path, data_type in DATA_SOURCES:
        print(f"\n📊 Testing on {name}...")
        result = test_single_dataset(name, path, data_type)
        if result:
            results.append(result)
    
    # Create summary DataFrame
    if results:
        df_results = pd.DataFrame(results)
        
        # Sort by return
        df_results = df_results.sort_values('Return %', ascending=False)
        
        print("\n" + "="*80)
        print("📈 SUMMARY TABLE - ALL DATASETS")
        print("="*80)
        print(df_results.to_string(index=False))
        
        print("\n" + "="*80)
        print("📊 OVERALL STATISTICS")
        print("="*80)
        print(f"Total Datasets Tested: {len(results)}")
        print(f"Profitable Datasets: {len(df_results[df_results['Return %'] > 0])}")
        print(f"Average Return: {df_results['Return %'].mean():.2f}%")
        print(f"Best Return: {df_results['Return %'].max():.2f}%")
        print(f"Worst Return: {df_results['Return %'].min():.2f}%")
        print(f"Average Sharpe: {df_results['Sharpe'].mean():.2f}")
        print(f"Average Win Rate: {df_results['Win Rate %'].mean():.2f}%")
        print(f"Average # Trades: {df_results['# Trades'].mean():.0f}")
        
        # Save results
        output_file = 'results/exhaustion_gap_adx.csv'
        df_results.to_csv(output_file, index=False)
        print(f"\n💾 Results saved to {output_file}")
    
    print("\n✅ Exhaustion Gap + ADX testing complete with FULL STATS!")

if __name__ == "__main__":
    main()