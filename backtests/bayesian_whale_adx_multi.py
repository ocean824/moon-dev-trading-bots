"""
🌙 Moon Dev's Bayesian Whale + ADX Strategy - Multi-Data Tester
================================================================
Combines Bayesian BBSMA, nQQE, Bank funds with ADX trend filter
Tests across all datasets with FULL stats output
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import DATA_SOURCES, load_data_universal
import warnings
warnings.filterwarnings('ignore')

class BayesianWhaleADXStrategy(Strategy):
    """
    Bayesian Whale Detector Enhanced with ADX Filter
    Only trades during strong trending markets
    """
    
    # Bayesian BBSMA parameters
    bb_period = 20          # Bollinger Band period
    bb_std = 2.5           # Standard deviation multiplier
    bayes_period = 20      # Lookback for probability calculations
    lower_threshold = 15   # Threshold for signals (%)
    
    # nQQE parameters
    rsi_length = 14        # RSI period
    rsi_smoothing = 5      # RSI smoothing factor
    qqe_multiplier = 4.236 # QQE band multiplier
    qqe_overbought = 60    # Overbought level
    qqe_oversold = 40      # Oversold level
    
    # Bank Funds parameters
    fund_period1 = 27      # Period for highest/lowest
    fund_period2 = 34      # Period for bull/bear line calculation
    fund_ema = 13          # EMA period for bull/bear line
    banker_threshold = 25  # Threshold for banker entry
    
    # ADX parameters
    adx_period = 14        # ADX period
    adx_threshold = 25     # Minimum ADX for trend
    adx_strong = 40        # Strong trend threshold
    use_di_filter = True   # Use +DI/-DI confirmation
    
    # Risk management
    use_sl = True          # Use stop loss
    atr_period = 14        # ATR period for stops
    atr_multiplier = 2.0   # ATR multiplier for stop loss
    
    # Position sizing based on ADX
    use_dynamic_sizing = True
    size_normal = 0.75
    size_strong = 0.95
    
    def init(self):
        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        open_price = pd.Series(self.data.Open)
        
        # === BAYESIAN BBSMA ===
        bb_basis = ta.sma(close, self.bb_period)
        bb_std_dev = ta.stdev(close, self.bb_period) * self.bb_std
        bb_upper = bb_basis + bb_std_dev
        bb_lower = bb_basis - bb_std_dev
        
        # Calculate probabilities
        prob_up_upper = pd.Series(0.0, index=close.index)
        prob_up_basis = pd.Series(0.0, index=close.index)
        
        for i in range(self.bayes_period, len(close)):
            above_upper = (close[i-self.bayes_period:i] > bb_upper[i-self.bayes_period:i]).sum()
            prob_up_upper.iloc[i] = above_upper / self.bayes_period
            
            above_basis = (close[i-self.bayes_period:i] > bb_basis[i-self.bayes_period:i]).sum()
            prob_up_basis.iloc[i] = above_basis / self.bayes_period
        
        sigma_probs_up = prob_up_upper * prob_up_basis
        sigma_probs_down = (1 - prob_up_upper) * (1 - prob_up_basis)
        
        prob_prime = (sigma_probs_down * sigma_probs_up) / (sigma_probs_down * sigma_probs_up + 
                     (1 - sigma_probs_down) * (1 - sigma_probs_up) + 1e-10)
        
        self.prob_prime = self.I(lambda: prob_prime.values, name='ProbPrime')
        self.sigma_up = self.I(lambda: sigma_probs_up.values, name='SigmaUp')
        self.sigma_down = self.I(lambda: sigma_probs_down.values, name='SigmaDown')
        
        # === nQQE OSCILLATOR ===
        rsi = ta.rsi(close, self.rsi_length)
        rsi_smooth = ta.ema(rsi, self.rsi_smoothing)
        
        tr_rsi = (rsi_smooth - rsi_smooth.shift(1)).abs()
        atr_rsi = ta.ema(tr_rsi, self.rsi_length)
        
        qqe_upper = rsi_smooth + atr_rsi * self.qqe_multiplier
        qqe_lower = rsi_smooth - atr_rsi * self.qqe_multiplier
        
        qqe_slow = pd.Series(50.0, index=close.index)
        for i in range(1, len(close)):
            if pd.notna(rsi_smooth.iloc[i]) and pd.notna(qqe_slow.iloc[i-1]):
                if rsi_smooth.iloc[i] > qqe_slow.iloc[i-1]:
                    qqe_slow.iloc[i] = max(qqe_lower.iloc[i], qqe_slow.iloc[i-1])
                else:
                    qqe_slow.iloc[i] = min(qqe_upper.iloc[i], qqe_slow.iloc[i-1])
        
        self.qqe_fast = self.I(lambda: rsi_smooth.values, name='QQE_Fast')
        self.qqe_slow = self.I(lambda: qqe_slow.values, name='QQE_Slow')
        
        # === BANK FUNDS ===
        typ = (2 * close + high + low + open_price) / 5
        
        lol27 = low.rolling(window=self.fund_period1).min()
        hoh27 = high.rolling(window=self.fund_period1).max()
        fund_raw = (close - lol27) / (hoh27 - lol27 + 1e-10) * 100
        
        fund_smooth1 = ta.ema(fund_raw, 5)
        fund_smooth2 = ta.ema(fund_smooth1, 3)
        fund_trend = (3 * fund_smooth1 - 2 * fund_smooth2 - 50) * 1.032 + 50
        
        lol34 = low.rolling(window=self.fund_period2).min()
        hoh34 = high.rolling(window=self.fund_period2).max()
        bullbear_raw = (typ - lol34) / (hoh34 - lol34 + 1e-10) * 100
        bullbear_line = ta.ema(bullbear_raw, self.fund_ema)
        
        self.fund_trend = self.I(lambda: fund_trend.values, name='FundTrend')
        self.bullbear_line = self.I(lambda: bullbear_line.values, name='BullBearLine')
        
        # === ADX CALCULATION ===
        df = pd.DataFrame({
            'High': high,
            'Low': low,
            'Close': close
        })
        
        adx_result = ta.adx(df['High'], df['Low'], df['Close'], length=self.adx_period)
        adx_col = f'ADX_{self.adx_period}'
        dmp_col = f'DMP_{self.adx_period}'
        dmn_col = f'DMN_{self.adx_period}'
        
        self.adx = self.I(lambda: adx_result[adx_col].values, name='ADX')
        self.plus_di = self.I(lambda: adx_result[dmp_col].values, name='+DI')
        self.minus_di = self.I(lambda: adx_result[dmn_col].values, name='-DI')
        
        # ATR for stop loss
        self.atr = self.I(ta.atr, high, low, close, self.atr_period)
    
    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < 50:
            return
        
        price = self.data.Close[-1]
        
        # Check for valid values
        if (pd.isna(self.prob_prime[-1]) or pd.isna(self.qqe_fast[-1]) or 
            pd.isna(self.fund_trend[-1]) or pd.isna(self.adx[-1])):
            return
        
        # === SIGNAL GENERATION ===
        
        # Bayesian signals
        bayes_bullish = (self.prob_prime[-1] > self.lower_threshold/100 and 
                        self.prob_prime[-2] <= self.lower_threshold/100)
        bayes_bearish = (self.prob_prime[-1] <= self.lower_threshold/100 and 
                        self.prob_prime[-2] > self.lower_threshold/100)
        
        # nQQE signals
        qqe_bullish = (self.qqe_fast[-1] > self.qqe_slow[-1] and 
                      self.qqe_fast[-2] <= self.qqe_slow[-2])
        qqe_bearish = (self.qqe_fast[-1] < self.qqe_slow[-1] and 
                      self.qqe_fast[-2] >= self.qqe_slow[-2])
        
        qqe_not_overbought = self.qqe_fast[-1] < self.qqe_overbought
        qqe_not_oversold = self.qqe_fast[-1] > self.qqe_oversold
        
        # Bank funds signals
        banker_bullish = self.fund_trend[-1] > self.bullbear_line[-1]
        banker_bearish = self.fund_trend[-1] < self.bullbear_line[-1]
        
        # ADX filter
        trend_strong = self.adx[-1] > self.adx_threshold
        trend_very_strong = self.adx[-1] > self.adx_strong
        
        # Directional confirmation
        di_bullish = not self.use_di_filter or self.plus_di[-1] > self.minus_di[-1]
        di_bearish = not self.use_di_filter or self.minus_di[-1] > self.plus_di[-1]
        
        # === COMBINED SIGNALS ===
        # Require 2 out of 3 main indicators + ADX confirmation
        bull_signals = sum([bayes_bullish, qqe_bullish, banker_bullish])
        bear_signals = sum([bayes_bearish, qqe_bearish, banker_bearish])
        
        long_signal = bull_signals >= 2 and qqe_not_oversold and trend_strong and di_bullish
        short_signal = bear_signals >= 2 and qqe_not_overbought and trend_strong and di_bearish
        
        # Position sizing based on ADX
        if self.use_dynamic_sizing:
            position_size = self.size_strong if trend_very_strong else self.size_normal
        else:
            position_size = 0.95
        
        # Risk management
        atr_value = self.atr[-1]
        if pd.isna(atr_value) or atr_value == 0:
            return
        
        # Execute trades
        if long_signal:
            if self.position.is_short:
                self.position.close()
            if not self.position:
                if self.use_sl:
                    stop_loss = price - (atr_value * self.atr_multiplier)
                    self.buy(size=position_size, sl=stop_loss)
                else:
                    self.buy(size=position_size)
        
        elif short_signal:
            if self.position.is_long:
                self.position.close()
            if not self.position:
                if self.use_sl:
                    stop_loss = price + (atr_value * self.atr_multiplier)
                    self.sell(size=position_size, sl=stop_loss)
                else:
                    self.sell(size=position_size)
        
        # Exit if trend weakens
        if self.position and self.adx[-1] < 20:
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
        bt = Backtest(data, BayesianWhaleADXStrategy, 
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
    print("🌙 MOON DEV'S BAYESIAN WHALE + ADX - MULTI-DATA TESTER")
    print("="*80)
    print("Testing Bayesian + nQQE + Bank Funds + ADX Filter Strategy")
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
        print(f"\nADX Filter Impact:")
        print(f"This strategy is more selective due to ADX > {25} requirement")
        print(f"Trades only in trending markets for higher quality signals")
        
        # Save results
        output_file = 'results/bayesian_whale_adx_results.csv'
        df_results.to_csv(output_file, index=False)
        print(f"\n💾 Results saved to {output_file}")
        
        # Best by asset
        print("\n" + "="*80)
        print("🎯 BEST PERFORMERS BY ASSET")
        print("="*80)
        
        for asset in ['BTC', 'ETH', 'SOL', 'AAPL', 'TSLA']:
            asset_data = df_results[df_results['Dataset'].str.contains(asset)]
            if not asset_data.empty:
                best = asset_data.iloc[0]
                print(f"{asset}: {best['Dataset']} | Return: {best['Return %']}% | Sharpe: {best['Sharpe']}")
    
    print("\n✅ Multi-data testing with ADX filter complete!")

if __name__ == "__main__":
    main()