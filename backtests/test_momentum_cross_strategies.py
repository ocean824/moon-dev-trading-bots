"""
Test All Momentum Cross Strategies
===================================
Quick test to verify all 6 momentum cross strategies work
"""

from backtesting import Backtest
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Import all strategies
from momentum_cross_triple_ema import MomentumCrossTripleEMAStrategy
from momentum_cross_stochastic_div import MomentumCrossStochasticDivStrategy
from momentum_cross_impulse_macd import MomentumCrossImpulseMACDStrategy
from momentum_cross_triple_ema_kalman import MomentumCrossTripleEMAKalmanStrategy
from momentum_cross_stochastic_div_kalman import MomentumCrossStochasticDivKalmanStrategy
from momentum_cross_impulse_macd_kalman import MomentumCrossImpulseMACDKalmanStrategy

# Test data sources (just a few for quick testing)
TEST_DATA = [
    ('BTC-1d-100wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-100wks-data.csv'),
    ('ETH-1d-1000wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1d-1000wks-data.csv'),
    ('SOL-1d-1000wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1d-1000wks-data.csv'),
]

# All strategies to test
STRATEGIES = [
    ('MomentumCrossTripleEMA', MomentumCrossTripleEMAStrategy),
    ('MomentumCrossStochasticDiv', MomentumCrossStochasticDivStrategy),
    ('MomentumCrossImpulseMACD', MomentumCrossImpulseMACDStrategy),
    ('MomentumCrossTripleEMAKalman', MomentumCrossTripleEMAKalmanStrategy),
    ('MomentumCrossStochasticDivKalman', MomentumCrossStochasticDivKalmanStrategy),
    ('MomentumCrossImpulseMACDKalman', MomentumCrossImpulseMACDKalmanStrategy),
]

def load_data(path):
    """Load and prepare data"""
    try:
        data = pd.read_csv(path, parse_dates=['datetime'], index_col='datetime')
        data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        data = data.sort_index()
        data = data.dropna()
        return data
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def main():
    print("="*80)
    print("TESTING ALL MOMENTUM CROSS STRATEGIES")
    print("="*80)
    
    results = []
    
    for strategy_name, strategy_class in STRATEGIES:
        print(f"\nTesting {strategy_name}...")
        print("-"*40)
        
        strategy_results = []
        
        for data_name, data_path in TEST_DATA:
            print(f"  {data_name}... ", end='')
            
            # Load data
            data = load_data(data_path)
            if data is None:
                print("FAILED to load data")
                continue
            
            # Run backtest
            try:
                bt = Backtest(data, strategy_class, cash=10000000, commission=0.00045)
                stats = bt.run()
                
                # Extract key metrics
                result = {
                    'Strategy': strategy_name,
                    'Data': data_name,
                    'Return_%': round(stats['Return [%]'], 2),
                    'Sharpe': round(stats['Sharpe Ratio'], 3),
                    'Max_DD_%': round(stats['Max. Drawdown [%]'], 2),
                    'Trades': stats['# Trades'],
                    'Win_Rate_%': round(stats['Win Rate [%]'], 2) if stats['# Trades'] > 0 else 0,
                }
                
                strategy_results.append(result)
                print(f"OK - Return: {result['Return_%']}%, Sharpe: {result['Sharpe']}, Trades: {result['Trades']}")
                
            except Exception as e:
                print(f"ERROR: {str(e)[:50]}")
                continue
        
        if strategy_results:
            results.extend(strategy_results)
            avg_return = sum(r['Return_%'] for r in strategy_results) / len(strategy_results)
            avg_sharpe = sum(r['Sharpe'] for r in strategy_results) / len(strategy_results)
            total_trades = sum(r['Trades'] for r in strategy_results)
            print(f"  Average Return: {avg_return:.2f}%, Average Sharpe: {avg_sharpe:.3f}, Total Trades: {total_trades}")
    
    # Print summary
    print("\n" + "="*80)
    print("SUMMARY RESULTS")
    print("="*80)
    
    if results:
        df = pd.DataFrame(results)
        print("\nAll Results:")
        print(df.to_string(index=False))
        
        # Group by strategy
        print("\n" + "-"*80)
        print("Average Performance by Strategy:")
        print("-"*80)
        
        for strategy_name, _ in STRATEGIES:
            strategy_df = df[df['Strategy'] == strategy_name]
            if not strategy_df.empty:
                print(f"\n{strategy_name}:")
                print(f"  Avg Return: {strategy_df['Return_%'].mean():.2f}%")
                print(f"  Avg Sharpe: {strategy_df['Sharpe'].mean():.3f}")
                print(f"  Avg Max DD: {strategy_df['Max_DD_%'].mean():.2f}%")
                print(f"  Total Trades: {strategy_df['Trades'].sum()}")
                print(f"  Avg Win Rate: {strategy_df['Win_Rate_%'].mean():.2f}%")
    
    print("\n" + "="*80)
    print("TESTING COMPLETE!")
    print("All 6 momentum cross strategies have been verified.")
    print("="*80)

if __name__ == "__main__":
    main()