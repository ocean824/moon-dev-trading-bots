"""
🌙 Moon Dev's CM Williams Vix Fix Strategy - Multi-Data Tester
===============================================================
Based on ChrisMoody's Williams Vix Fix indicator
Tests across all datasets with FULL stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import DATA_SOURCES, load_data_universal
import warnings
warnings.filterwarnings('ignore')

class CMWilliamsVixStrategy(Strategy):
    """
    CM Williams Vix Fix Strategy
    Uses volatility spikes to identify oversold conditions
    """
    
    # Williams Vix Fix parameters
    lookback_period = 22  # Period for highest close
    bb_length = 20        # Bollinger Band length
    bb_mult = 2.0        # Bollinger Band std dev multiplier
    percentile_period = 50  # Lookback for percentile calculation
    high_percentile = 0.85  # 85th percentile (0.85 = 85%)
    low_percentile = 0.01   # 1st percentile for lows (0.01 = 1%)
    
    # Trading settings
    vix_spike_threshold = 15  # WVF must be above this to consider oversold
    mean_reversion = True     # Trade mean reversion (long on spikes)
    trend_follow = False       # Alternative: follow volatility trend
    
    # Risk management
    use_sl = True         # Use stop loss
    atr_period = 14       # ATR period for stops
    atr_multiplier = 2.0  # ATR multiplier for stop loss
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # === WILLIAMS VIX FIX CALCULATION ===
        # WVF = ((highest(close, pd) - low) / highest(close, pd)) * 100
        highest_close = close.rolling(window=self.lookback_period).max()
        wvf = ((highest_close - low) / highest_close) * 100
        
        # Handle division by zero
        wvf = wvf.fillna(0)
        
        # === BOLLINGER BANDS ON WVF ===
        wvf_sma = ta.sma(wvf, self.bb_length)
        wvf_std = ta.stdev(wvf, self.bb_length)
        
        upper_band = wvf_sma + (self.bb_mult * wvf_std)
        lower_band = wvf_sma - (self.bb_mult * wvf_std)
        
        # === PERCENTILE RANGES ===
        # Range high/low based on percentiles
        range_high = wvf.rolling(window=self.percentile_period).quantile(self.high_percentile)
        range_low = wvf.rolling(window=self.percentile_period).quantile(self.low_percentile)
        
        # Store indicators
        self.wvf = self.I(lambda: wvf.values, name='WVF')
        self.wvf_sma = self.I(lambda: wvf_sma.values, name='WVF_SMA')
        self.upper_band = self.I(lambda: upper_band.values, name='UpperBand')
        self.lower_band = self.I(lambda: lower_band.values, name='LowerBand')
        self.range_high = self.I(lambda: range_high.values, name='RangeHigh')
        self.range_low = self.I(lambda: range_low.values, name='RangeLow')
        
        # === SIGNAL CONDITIONS ===
        # High volatility (fear) signal - potential oversold
        vix_spike = (wvf >= upper_band) | (wvf >= range_high)
        vix_normal = (wvf < upper_band) & (wvf < range_high)
        
        self.vix_spike = self.I(lambda: vix_spike.values, name='VixSpike')
        self.vix_normal = self.I(lambda: vix_normal.values, name='VixNormal')
        
        # ATR for stop loss
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.lookback_period, self.bb_length, 
                                      self.percentile_period, self.atr_period) + 1:
            return
        
        # Get current values
        price = self.data.Close[-1]
        wvf_curr = self.wvf[-1]
        wvf_prev = self.wvf[-2]
        
        # Check for valid values
        if pd.isna(wvf_curr):
            return
        
        # === SIGNAL GENERATION ===
        
        # Volatility spike detection
        spike_signal = self.vix_spike[-1]
        spike_ending = self.vix_spike[-2] and not self.vix_spike[-1]  # Spike just ended
        
        # WVF level checks
        wvf_high = wvf_curr >= self.upper_band[-1] or wvf_curr >= self.range_high[-1]
        wvf_low = wvf_curr <= self.lower_band[-1]
        wvf_above_threshold = wvf_curr > self.vix_spike_threshold
        
        # Trend analysis
        wvf_increasing = wvf_curr > wvf_prev
        wvf_decreasing = wvf_curr < wvf_prev
        
        # === TRADING LOGIC ===
        
        if self.mean_reversion:
            # Mean reversion: Buy on fear spikes (oversold), Sell when calm returns
            
            # Long signal: High WVF indicates oversold condition
            long_signal = (spike_signal and wvf_above_threshold) or spike_ending
            
            # Short signal: Low WVF after spike (overbought after recovery)
            short_signal = (not spike_signal and wvf_curr < self.wvf_sma[-1] and 
                          wvf_decreasing and self.position.is_long)
            
            # Alternative short: When WVF is very low (too calm, complacency)
            if not self.position:
                short_signal = wvf_low and wvf_curr < 5
                
        elif self.trend_follow:
            # Trend following: Trade with volatility direction
            
            # Long when volatility starts increasing (breakout potential)
            long_signal = wvf_increasing and wvf_curr > self.wvf_sma[-1]
            
            # Short when volatility decreasing (calming down)
            short_signal = wvf_decreasing and wvf_curr < self.wvf_sma[-1]
        
        else:
            # Simple spike trading
            long_signal = spike_signal
            short_signal = not spike_signal and self.position.is_long
        
        # Risk management
        atr_value = self.atr[-1]
        if pd.isna(atr_value) or atr_value == 0:
            return
        
        # === EXECUTE TRADES ===
        
        if long_signal:
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
            # Only allow shorting in certain conditions
            if not self.position and not self.mean_reversion:
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
        bt = Backtest(data, CMWilliamsVixStrategy, 
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
    print("🌙 MOON DEV'S CM WILLIAMS VIX FIX - MULTI-DATA TESTER")
    print("="*80)
    print("Testing ChrisMoody's Williams Vix Fix Strategy")
    print("Volatility-based mean reversion trading")
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
        output_file = 'results/cm_williams_vix_results.csv'
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
    
    print("\n✅ CM Williams Vix Fix testing complete with FULL STATS!")

if __name__ == "__main__":
    main()