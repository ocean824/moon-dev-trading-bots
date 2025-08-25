"""
🌙 Moon Dev's Mutanabby + ADX Combined Strategy - Multi-Data Tester
====================================================================
Combines SuperTrend signals with ADX trend strength filtering
Only trades during strong trending markets for higher quality signals
"""

from backtesting import Backtest, Strategy
import pandas as pd
import pandas_ta as ta
import numpy as np
from multi_data_tester import test_on_all_data, DATA_SOURCES, load_data_universal
import warnings
warnings.filterwarnings('ignore')

class MutanabbyADXStrategy(Strategy):
    """
    Mutanabby + ADX Combined Strategy
    Uses ADX to filter SuperTrend signals - only trading in strong trends
    """
    
    # SuperTrend parameters
    st_period = 11       # ATR period for SuperTrend
    st_multiplier = 4    # Multiplier for SuperTrend bands
    
    # Moving average parameters
    fast_ma = 8         # Fast MA
    medium_ma = 9       # Medium MA 
    slow_ma = 13        # Slow MA for trend confirmation
    
    # ADX parameters
    adx_length = 14     # ADX period
    adx_threshold = 25  # Minimum ADX for strong trend
    adx_strong = 40     # Very strong trend threshold
    adx_exit = 20       # Exit if ADX drops below this
    use_di_filter = True # Use +DI/-DI confirmation
    
    # Risk management
    use_sl = True       # Use stop loss
    use_tp = True       # Use take profit
    atr_risk = 1.5      # ATR multiplier for stop loss
    risk_reward = 2.0   # Risk:Reward ratio
    atr_period = 14     # ATR period for stop loss
    
    # Position sizing based on ADX
    use_dynamic_sizing = True  # Adjust size based on trend strength
    size_normal = 0.75         # Normal position size (75%)
    size_strong = 0.95         # Strong trend size (95%)
    
    # Trade direction
    trade_long = True   # Allow long trades
    trade_short = True  # Allow short trades

    def init(self):
        # Prepare data
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        
        # Calculate SuperTrend
        st_result = ta.supertrend(high, low, close, 
                                  length=self.st_period, 
                                  multiplier=self.st_multiplier)
        
        # Extract SuperTrend components
        st_col = f'SUPERT_{self.st_period}_{float(self.st_multiplier)}'
        st_dir_col = f'SUPERTd_{self.st_period}_{float(self.st_multiplier)}'
        
        # Handle potential column name variations
        if st_col not in st_result.columns:
            st_col = f'SUPERT_{self.st_period}_{self.st_multiplier}.0'
            st_dir_col = f'SUPERTd_{self.st_period}_{self.st_multiplier}.0'
        
        self.supertrend = self.I(lambda: st_result[st_col].values, name='SuperTrend')
        self.st_direction = self.I(lambda: st_result[st_dir_col].values, name='ST_Direction')
        
        # Calculate ADX
        df = pd.DataFrame({
            'High': high,
            'Low': low,
            'Close': close
        })
        
        adx_result = ta.adx(df['High'], df['Low'], df['Close'], length=self.adx_length)
        adx_col = f'ADX_{self.adx_length}'
        dmp_col = f'DMP_{self.adx_length}'  # +DI
        dmn_col = f'DMN_{self.adx_length}'  # -DI
        
        self.adx = self.I(lambda: adx_result[adx_col].values, name='ADX')
        self.plus_di = self.I(lambda: adx_result[dmp_col].values, name='+DI')
        self.minus_di = self.I(lambda: adx_result[dmn_col].values, name='-DI')
        
        # Moving averages
        self.sma_fast = self.I(ta.sma, close, length=self.fast_ma)
        self.sma_medium = self.I(ta.sma, close, length=self.medium_ma)
        self.sma_slow = self.I(ta.sma, close, length=self.slow_ma)
        
        # ATR for stop loss
        self.atr = self.I(ta.atr, high, low, close, length=self.atr_period)

    def next(self):
        # Skip if not enough data
        if len(self.data.Close) < max(self.st_period, self.slow_ma, self.atr_period, self.adx_length) + 1:
            return
        
        # Current values
        price = self.data.Close[-1]
        st_dir = self.st_direction[-1]
        st_dir_prev = self.st_direction[-2] if len(self.st_direction) > 1 else st_dir
        
        # ADX values
        curr_adx = self.adx[-1]
        curr_plus_di = self.plus_di[-1]
        curr_minus_di = self.minus_di[-1]
        
        # Check for valid values
        if pd.isna(st_dir) or pd.isna(st_dir_prev) or pd.isna(curr_adx):
            return
        
        # === SIGNAL GENERATION ===
        # SuperTrend signals (direction: 1 = bullish, -1 = bearish)
        st_bull_cross = (st_dir == 1 and st_dir_prev == -1)
        st_bear_cross = (st_dir == -1 and st_dir_prev == 1)
        
        # MA confirmation
        ma_bullish = price > self.sma_slow[-1]
        ma_bearish = price < self.sma_slow[-1]
        
        # ADX filter - only trade in trending markets
        trend_strong = curr_adx > self.adx_threshold
        trend_very_strong = curr_adx > self.adx_strong
        trend_weak = curr_adx < self.adx_exit
        
        # Directional confirmation
        di_bullish = not self.use_di_filter or curr_plus_di > curr_minus_di
        di_bearish = not self.use_di_filter or curr_minus_di > curr_plus_di
        
        # === COMBINED CONDITIONS ===
        # Long: SuperTrend bull + MA bullish + Strong trend + DI bullish
        long_signal = st_bull_cross and ma_bullish and trend_strong and di_bullish
        
        # Short: SuperTrend bear + MA bearish + Strong trend + DI bearish
        short_signal = st_bear_cross and ma_bearish and trend_strong and di_bearish
        
        # Risk management
        atr_value = self.atr[-1]
        if pd.isna(atr_value) or atr_value == 0:
            return
        
        # === POSITION SIZING ===
        # Adjust position size based on ADX strength
        if self.use_dynamic_sizing:
            position_size = self.size_strong if trend_very_strong else self.size_normal
        else:
            position_size = 0.95
        
        # === EXECUTE TRADES ===
        if long_signal and self.trade_long:
            if self.position.is_short:
                self.position.close()
            if not self.position:
                # Calculate stop loss and take profit
                if self.use_sl:
                    stop_loss = price - (atr_value * self.atr_risk)
                    take_profit = price + (atr_value * self.atr_risk * self.risk_reward) if self.use_tp else None
                    self.buy(size=position_size, sl=stop_loss, tp=take_profit)
                else:
                    self.buy(size=position_size)
                
        elif short_signal and self.trade_short:
            if self.position.is_long:
                self.position.close()
            if not self.position:
                # Calculate stop loss and take profit
                if self.use_sl:
                    stop_loss = price + (atr_value * self.atr_risk)
                    take_profit = price - (atr_value * self.atr_risk * self.risk_reward) if self.use_tp else None
                    self.sell(size=position_size, sl=stop_loss, tp=take_profit)
                else:
                    self.sell(size=position_size)
        
        # === EXIT CONDITIONS ===
        # Exit if trend weakens significantly
        if self.position:
            # Exit long if SuperTrend turns bearish or ADX drops too low
            if self.position.is_long and (st_dir == -1 or trend_weak):
                self.position.close()
            # Exit short if SuperTrend turns bullish or ADX drops too low
            elif self.position.is_short and (st_dir == 1 or trend_weak):
                self.position.close()


def test_single_dataset(name, path, data_type):
    """Test strategy on a single dataset"""
    try:
        # Load data
        data = load_data_universal(path, data_type)
        
        if data is None or len(data) < 50:
            return None
            
        # Sort index
        data = data.sort_index()
        
        # Initialize backtest
        bt = Backtest(data, MutanabbyADXStrategy, 
                     cash=100000, 
                     commission=.002,
                     exclusive_orders=True)
        
        # Run backtest
        stats = bt.run()
        
        # Create results dictionary
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
    """Main function to run multi-data testing"""
    print("\n" + "="*80)
    print("🌙 MOON DEV'S MUTANABBY + ADX STRATEGY - MULTI-DATA TESTER")
    print("="*80)
    print("Testing SuperTrend + ADX Filter Combined Strategy")
    print(f"Parameters: ST={11}/{4}, ADX={14} (threshold={25}), SMA={8}/{9}/{13}")
    print("="*80)
    
    results = []
    
    # Test on all datasets
    for name, path, data_type in DATA_SOURCES:
        print(f"\n📊 Testing on {name}...")
        result = test_single_dataset(name, path, data_type)
        if result:
            results.append(result)
            print(f"  ✅ Return: {result['Return %']}% | Sharpe: {result['Sharpe']} | Trades: {result['# Trades']}")
    
    # Create summary DataFrame
    if results:
        import pandas as pd
        df_results = pd.DataFrame(results)
        
        # Sort by return
        df_results = df_results.sort_values('Return %', ascending=False)
        
        print("\n" + "="*80)
        print("📈 SUMMARY RESULTS - TOP PERFORMERS")
        print("="*80)
        print(df_results.head(10).to_string(index=False))
        
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
        
        # Save results to CSV
        output_file = 'results/mutanabby_adx_results.csv'
        df_results.to_csv(output_file, index=False)
        print(f"\n💾 Results saved to {output_file}")
        
        # Find best timeframes
        print("\n" + "="*80)
        print("🎯 BEST TIMEFRAMES BY ASSET")
        print("="*80)
        
        for asset in ['BTC', 'ETH', 'SOL']:
            asset_data = df_results[df_results['Dataset'].str.contains(asset)]
            if not asset_data.empty:
                best = asset_data.iloc[0]
                print(f"{asset}: {best['Dataset']} | Return: {best['Return %']}% | Sharpe: {best['Sharpe']}")
        
        # Compare with ultimate strategy
        print("\n" + "="*80)
        print("📊 ADX FILTER EFFECTIVENESS")
        print("="*80)
        print(f"Average trades with ADX filter: {df_results['# Trades'].mean():.0f}")
        print(f"This strategy is more selective, filtering out choppy markets")
        print(f"Lower trade count but potentially higher quality signals")
    
    print("\n✅ Multi-data testing complete!")


if __name__ == "__main__":
    main()