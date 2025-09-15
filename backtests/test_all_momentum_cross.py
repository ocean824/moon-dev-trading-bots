"""
Test All Momentum Cross Strategies on All Datasets
===================================================
Comprehensive test of all 6 momentum cross strategies using the multi-data tester
"""

from multi_data_tester import test_on_all_data
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

def main():
    print("\n" + "="*80)
    print("MOON DEV'S MOMENTUM CROSS STRATEGIES - COMPREHENSIVE TEST")
    print("="*80)
    print("Testing all 6 momentum cross strategies on all datasets...")
    print("="*80)
    
    # All strategies to test
    strategies = [
        ('MomentumCrossTripleEMA', MomentumCrossTripleEMAStrategy),
        ('MomentumCrossStochasticDiv', MomentumCrossStochasticDivStrategy),
        ('MomentumCrossImpulseMACD', MomentumCrossImpulseMACDStrategy),
        ('MomentumCrossTripleEMAKalman', MomentumCrossTripleEMAKalmanStrategy),
        ('MomentumCrossStochasticDivKalman', MomentumCrossStochasticDivKalmanStrategy),
        ('MomentumCrossImpulseMACDKalman', MomentumCrossImpulseMACDKalmanStrategy),
    ]
    
    all_results = []
    
    for i, (name, strategy_class) in enumerate(strategies, 1):
        print(f"\n[{i}/6] Testing {name}...")
        print("-"*60)
        
        # Run tests on all data sources without optimization
        results = test_on_all_data(
            strategy_class,
            name,
            optimize=False,  # No optimization as requested
            cash=10000000,
            commission=0.00045,
            verbose=False  # Set to False for cleaner output
        )
        
        if results is not None:
            # Calculate summary statistics
            avg_return = results['Return_%'].mean()
            avg_sharpe = results['Sharpe'].mean()
            avg_max_dd = results['Max_DD_%'].mean()
            total_trades = results['Trades'].sum()
            avg_win_rate = results['Win_Rate_%'].mean()
            
            print(f"✅ Complete! Results saved to: results/{name}.csv")
            print(f"   Average Return: {avg_return:.2f}%")
            print(f"   Average Sharpe: {avg_sharpe:.3f}")
            print(f"   Average Max DD: {avg_max_dd:.2f}%")
            print(f"   Total Trades: {total_trades}")
            print(f"   Average Win Rate: {avg_win_rate:.2f}%")
            
            # Add to summary
            all_results.append({
                'Strategy': name,
                'Avg_Return_%': round(avg_return, 2),
                'Avg_Sharpe': round(avg_sharpe, 3),
                'Avg_Max_DD_%': round(avg_max_dd, 2),
                'Total_Trades': total_trades,
                'Avg_Win_Rate_%': round(avg_win_rate, 2),
                'Best_Return_%': round(results['Return_%'].max(), 2),
                'Worst_Return_%': round(results['Return_%'].min(), 2),
            })
        else:
            print(f"❌ Failed to generate results")
    
    # Print final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY - ALL MOMENTUM CROSS STRATEGIES")
    print("="*80)
    
    if all_results:
        summary_df = pd.DataFrame(all_results)
        print("\nPerformance Comparison:")
        print(summary_df.to_string(index=False))
        
        # Find best performers
        print("\n" + "-"*60)
        print("Best Performers:")
        print("-"*60)
        
        best_return = summary_df.loc[summary_df['Avg_Return_%'].idxmax()]
        print(f"Best Average Return: {best_return['Strategy']} ({best_return['Avg_Return_%']}%)")
        
        best_sharpe = summary_df.loc[summary_df['Avg_Sharpe'].idxmax()]
        print(f"Best Average Sharpe: {best_sharpe['Strategy']} ({best_sharpe['Avg_Sharpe']})")
        
        best_dd = summary_df.loc[summary_df['Avg_Max_DD_%'].idxmax()]
        print(f"Lowest Average Drawdown: {best_dd['Strategy']} ({best_dd['Avg_Max_DD_%']}%)")
        
        best_win_rate = summary_df.loc[summary_df['Avg_Win_Rate_%'].idxmax()]
        print(f"Best Win Rate: {best_win_rate['Strategy']} ({best_win_rate['Avg_Win_Rate_%']}%)")
    
    print("\n" + "="*80)
    print("TESTING COMPLETE!")
    print("All 6 momentum cross strategies have been tested on all datasets.")
    print("Results are saved in the 'results' directory.")
    print("="*80)

if __name__ == "__main__":
    main()