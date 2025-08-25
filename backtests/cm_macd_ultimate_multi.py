"""
🌙 Moon Dev's CM MACD Ultimate Strategy - Multi-Data Tester
============================================================
Based on ChrisMoody's MACD Ultimate MTF indicator
Tests across all datasets with FULL stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import DATA_SOURCES, load_data_universal
import warnings
warnings.filterwarnings('ignore')

class CMMACDUltimateStrategy(Strategy):
    """
    CM MACD Ultimate Strategy
    Uses MACD crossovers with histogram confirmation
    """
    
    # MACD parameters
    fast_length = 12      # Fast EMA period
    slow_length = 26      # Slow EMA period  
    signal_length = 9     # Signal SMA period
    
    # Histogram settings
    use_histogram = True  # Use histogram for confirmation
    histogram_threshold = 0  # Histogram must be > 0 for long, < 0 for short
    
    # Risk management
    use_sl = True         # Use stop loss
    atr_period = 14       # ATR period for stops
    atr_multiplier = 2.0  # ATR multiplier for stop loss
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        
        # Calculate MACD components
        fast_ma = ta.ema(close, self.fast_length)
        slow_ma = ta.ema(close, self.slow_length)
        
        # MACD line
        macd = fast_ma - slow_ma
        
        # Signal line (SMA of MACD)
        signal = ta.sma(macd, self.signal_length)
        
        # Histogram
        histogram = macd - signal
        
        # Store indicators
        self.macd = self.I(lambda: macd.values, name='MACD')
        self.signal = self.I(lambda: signal.values, name='Signal')
        self.histogram = self.I(lambda: histogram.values, name='Histogram')
        
        # Histogram direction analysis
        hist_up = histogram > histogram.shift(1)
        hist_down = histogram < histogram.shift(1)
        
        # Four histogram states (like in PineScript)
        hist_a_up = (histogram > histogram.shift(1)) & (histogram > 0)  # Green
        hist_a_down = (histogram < histogram.shift(1)) & (histogram > 0)  # Blue
        hist_b_down = (histogram < histogram.shift(1)) & (histogram <= 0)  # Red
        hist_b_up = (histogram > histogram.shift(1)) & (histogram <= 0)  # Maroon
        
        self.hist_a_up = self.I(lambda: hist_a_up.values, name='HistAUp')
        self.hist_a_down = self.I(lambda: hist_a_down.values, name='HistADown')
        self.hist_b_down = self.I(lambda: hist_b_down.values, name='HistBDown')
        self.hist_b_up = self.I(lambda: hist_b_up.values, name='HistBUp')
        
        # ATR for stop loss
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.slow_length, self.signal_length, self.atr_period) + 1:
            return
        
        # Get current values
        price = self.data.Close[-1]
        macd_curr = self.macd[-1]
        macd_prev = self.macd[-2]
        signal_curr = self.signal[-1]
        signal_prev = self.signal[-2]
        hist_curr = self.histogram[-1]
        
        # Check for valid values
        if pd.isna(macd_curr) or pd.isna(signal_curr):
            return
        
        # === SIGNAL GENERATION ===
        
        # MACD crossover signals
        macd_cross_up = macd_prev <= signal_prev and macd_curr > signal_curr
        macd_cross_down = macd_prev >= signal_prev and macd_curr < signal_curr
        
        # MACD position relative to signal
        macd_above_signal = macd_curr >= signal_curr
        macd_below_signal = macd_curr < signal_curr
        
        # Histogram confirmation
        if self.use_histogram:
            # Strong bullish: Histogram positive and increasing
            hist_bullish = self.hist_a_up[-1]
            # Strong bearish: Histogram negative and decreasing
            hist_bearish = self.hist_b_down[-1]
            
            # Moderate signals
            hist_weakening_bull = self.hist_a_down[-1]  # Still positive but decreasing
            hist_weakening_bear = self.hist_b_up[-1]    # Still negative but increasing
        else:
            hist_bullish = True
            hist_bearish = True
        
        # === COMBINED SIGNALS ===
        
        # Entry signals with optional histogram confirmation
        if self.use_histogram:
            # Enter on crossover with histogram confirmation
            long_signal = macd_cross_up and (hist_curr > self.histogram_threshold)
            short_signal = macd_cross_down and (hist_curr < -self.histogram_threshold)
        else:
            # Simple crossover strategy
            long_signal = macd_cross_up
            short_signal = macd_cross_down
        
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
            if not self.position:
                if self.use_sl:
                    stop_loss = price + (atr_value * self.atr_multiplier)
                    self.sell(sl=stop_loss)
                else:
                    self.sell()
        
        # === EXIT CONDITIONS ===
        # Exit on opposite MACD position (optional)
        if self.position:
            # Exit long if MACD goes below signal
            if self.position.is_long and macd_below_signal and hist_curr < 0:
                self.position.close()
            # Exit short if MACD goes above signal
            elif self.position.is_short and macd_above_signal and hist_curr > 0:
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
        bt = Backtest(data, CMMACDUltimateStrategy, 
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
    print("🌙 MOON DEV'S CM MACD ULTIMATE - MULTI-DATA TESTER")
    print("="*80)
    print("Testing ChrisMoody's MACD Ultimate Strategy")
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
        output_file = 'results/cm_macd_ultimate_results.csv'
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
    
    print("\n✅ CM MACD Ultimate testing complete with FULL STATS!")

if __name__ == "__main__":
    main()