"""
🌙 Moon Dev's CM MACD + Williams Vix Combined Strategy - Multi-Data Tester
===========================================================================
Combines MACD for trend direction with Williams Vix Fix for timing
Tests across all datasets with FULL stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import DATA_SOURCES, load_data_universal
import warnings
warnings.filterwarnings('ignore')

class CMMACDVixCombinedStrategy(Strategy):
    """
    Combined CM MACD Ultimate + Williams Vix Fix Strategy
    Uses MACD for trend, WVF for volatility-based entry timing
    """
    
    # MACD parameters
    fast_length = 12      # Fast EMA period
    slow_length = 26      # Slow EMA period  
    signal_length = 9     # Signal SMA period
    
    # Williams Vix Fix parameters
    lookback_period = 22  # Period for highest close
    bb_length = 20        # Bollinger Band length
    bb_mult = 2.0        # Bollinger Band std dev multiplier
    percentile_period = 50  # Lookback for percentile calculation
    high_percentile = 0.85  # 85th percentile
    
    # Combined strategy settings
    vix_spike_threshold = 15  # WVF threshold for oversold
    require_vix_spike_long = True  # Require VIX spike for long entries
    require_macd_confirm = True    # Require MACD confirmation
    
    # Risk management
    use_sl = True         # Use stop loss
    atr_period = 14       # ATR period for stops
    atr_multiplier = 2.0  # ATR multiplier for stop loss
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # === MACD CALCULATION ===
        fast_ma = ta.ema(close, self.fast_length)
        slow_ma = ta.ema(close, self.slow_length)
        
        macd = fast_ma - slow_ma
        signal = ta.sma(macd, self.signal_length)
        histogram = macd - signal
        
        self.macd = self.I(lambda: macd.values, name='MACD')
        self.signal = self.I(lambda: signal.values, name='Signal')
        self.histogram = self.I(lambda: histogram.values, name='Histogram')
        
        # === WILLIAMS VIX FIX CALCULATION ===
        highest_close = close.rolling(window=self.lookback_period).max()
        wvf = ((highest_close - low) / highest_close) * 100
        wvf = wvf.fillna(0)
        
        # Bollinger Bands on WVF
        wvf_sma = ta.sma(wvf, self.bb_length)
        wvf_std = ta.stdev(wvf, self.bb_length)
        upper_band = wvf_sma + (self.bb_mult * wvf_std)
        lower_band = wvf_sma - (self.bb_mult * wvf_std)
        
        # Percentile ranges
        range_high = wvf.rolling(window=self.percentile_period).quantile(self.high_percentile)
        
        self.wvf = self.I(lambda: wvf.values, name='WVF')
        self.wvf_sma = self.I(lambda: wvf_sma.values, name='WVF_SMA')
        self.upper_band = self.I(lambda: upper_band.values, name='UpperBand')
        self.range_high = self.I(lambda: range_high.values, name='RangeHigh')
        
        # Signal conditions
        vix_spike = (wvf >= upper_band) | (wvf >= range_high)
        self.vix_spike = self.I(lambda: vix_spike.values, name='VixSpike')
        
        # ATR for stop loss
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.slow_length, self.lookback_period, 
                                      self.percentile_period, self.atr_period) + 1:
            return
        
        # Get current values
        price = self.data.Close[-1]
        macd_curr = self.macd[-1]
        macd_prev = self.macd[-2]
        signal_curr = self.signal[-1]
        signal_prev = self.signal[-2]
        hist_curr = self.histogram[-1]
        wvf_curr = self.wvf[-1]
        
        # Check for valid values
        if pd.isna(macd_curr) or pd.isna(signal_curr) or pd.isna(wvf_curr):
            return
        
        # === MACD SIGNALS ===
        macd_cross_up = macd_prev <= signal_prev and macd_curr > signal_curr
        macd_cross_down = macd_prev >= signal_prev and macd_curr < signal_curr
        macd_above_signal = macd_curr >= signal_curr
        macd_below_signal = macd_curr < signal_curr
        
        # Histogram trend
        hist_bullish = hist_curr > 0 and hist_curr > self.histogram[-2]
        hist_bearish = hist_curr < 0 and hist_curr < self.histogram[-2]
        
        # === WILLIAMS VIX SIGNALS ===
        spike_signal = self.vix_spike[-1]
        spike_ending = self.vix_spike[-2] and not self.vix_spike[-1]
        wvf_above_threshold = wvf_curr > self.vix_spike_threshold
        wvf_calming = wvf_curr < self.wvf_sma[-1]
        
        # === COMBINED SIGNALS ===
        
        if self.require_macd_confirm and self.require_vix_spike_long:
            # Strict combination: Both indicators must agree
            
            # Long: MACD bullish + VIX spike (oversold bounce)
            long_signal = ((macd_cross_up or (macd_above_signal and hist_bullish)) and 
                          (spike_signal or spike_ending) and wvf_above_threshold)
            
            # Short: MACD bearish + VIX normal (trend continuation)
            short_signal = ((macd_cross_down or (macd_below_signal and hist_bearish)) and 
                           not spike_signal and wvf_calming)
            
        else:
            # Flexible combination: Either indicator can trigger
            
            # Long on either MACD bullish or VIX spike
            long_signal = (macd_cross_up and hist_curr > 0) or (spike_signal and wvf_above_threshold)
            
            # Short on MACD bearish when VIX is calm
            short_signal = macd_cross_down and not spike_signal
        
        # === ENHANCED EXIT CONDITIONS ===
        # Exit long if VIX spike ends and MACD turns bearish
        exit_long = (self.position.is_long and 
                    not spike_signal and wvf_calming and 
                    (macd_below_signal or hist_curr < 0))
        
        # Exit short if VIX spikes (market oversold)
        exit_short = self.position.is_short and spike_signal
        
        # Risk management
        atr_value = self.atr[-1]
        if pd.isna(atr_value) or atr_value == 0:
            return
        
        # === EXECUTE TRADES ===
        
        # Handle exits first
        if exit_long:
            self.position.close()
        elif exit_short:
            self.position.close()
        
        # New entries
        elif long_signal:
            if self.position.is_short:
                self.position.close()
            if not self.position:
                if self.use_sl:
                    stop_loss = price - (atr_value * self.atr_multiplier)
                    self.buy(sl=stop_loss)
                else:
                    self.buy()
        
        elif short_signal:
            if self.position.is_long:
                self.position.close()
            if not self.position:
                if self.use_sl:
                    stop_loss = price + (atr_value * self.atr_multiplier)
                    self.sell(sl=stop_loss)
                else:
                    self.sell()

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
        bt = Backtest(data, CMMACDVixCombinedStrategy, 
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
    print("🌙 MOON DEV'S CM MACD + WILLIAMS VIX COMBINED - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Combined MACD (trend) + Williams Vix Fix (timing) Strategy")
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
        
        print("\n" + "="*80)
        print("📊 STRATEGY COMBINATION BENEFITS")
        print("="*80)
        print("MACD provides: Trend direction and momentum")
        print("Williams Vix provides: Volatility-based entry timing")
        print("Combined: Enter on trend + oversold conditions for better timing")
        
        # Save results
        output_file = 'results/cm_macd_vix_combined_results.csv'
        df_results.to_csv(output_file, index=False)
        print(f"\n💾 Results saved to {output_file}")
        
        # Best by asset
        print("\n" + "="*80)
        print("🎯 BEST PERFORMERS BY ASSET")
        print("="*80)
        
        for asset in ['BTC', 'ETH', 'SOL', 'AAPL', 'TSLA', 'NVDA']:
            asset_data = df_results[df_results['Dataset'].str.contains(asset)]
            if not asset_data.empty:
                best = asset_data.iloc[0]
                print(f"{asset}: {best['Dataset']} | Return: {best['Return %']}% | Sharpe: {best['Sharpe']}")
    
    print("\n✅ CM MACD + Williams Vix Combined testing complete with FULL STATS!")

if __name__ == "__main__":
    main()