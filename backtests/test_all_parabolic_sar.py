"""
Test All Parabolic SAR Strategies on All Datasets
==================================================
Comprehensive test of all 5 Parabolic SAR strategies using the multi-data tester
"""

from multi_data_tester import test_on_all_data
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Import all Parabolic SAR strategies
from parabolic_sar_long import ParabolicSARLongStrategy
from parabolic_sar_both import ParabolicSARBothStrategy
from parabolic_sar_adx import ParabolicSARADXStrategy
from parabolic_sar_kalman import ParabolicSARKalmanStrategy
from parabolic_sar_mfi import ParabolicSARMFIStrategy

def main():
    print("\n" + "="*80)
    print("MOON DEV'S PARABOLIC SAR STRATEGIES - COMPREHENSIVE TEST")
    print("="*80)
    print("Testing all 5 Parabolic SAR strategies on all datasets...")
    print("="*80)
    
    # All strategies to test
    strategies = [
        ('ParabolicSARLong', ParabolicSARLongStrategy),
        ('ParabolicSARBoth', ParabolicSARBothStrategy),
        ('ParabolicSARADX', ParabolicSARADXStrategy),
        ('ParabolicSARKalman', ParabolicSARKalmanStrategy),
        ('ParabolicSARMFI', ParabolicSARMFIStrategy),
    ]
    
    all_results = []
    
    for i, (name, strategy_class) in enumerate(strategies, 1):
        print(f"\n[{i}/5] Testing {name}...")
        print("-"*60)
        
        # Run tests on all data sources without optimization
        results = test_on_all_data(
            strategy_class,
            name,
            optimize=False,
            cash=10000000,
            commission=0.00045,
            verbose=False  # Set to False for cleaner output
        )
        
        if results is not None:
            # Calculate summary statistics
            avg_return = results['Return_%'].mean()
            avg_sharpe = results['Sharpe'].mean()
            avg_sortino = results['Sortino'].mean()
            avg_calmar = results['Calmar'].mean()
            avg_max_dd = results['Max_DD_%'].mean()
            total_trades = results['Trades'].sum()
            avg_win_rate = results['Win_Rate_%'].mean()
            avg_profit_factor = results['Profit_Factor'].mean()
            avg_expectancy = results['Expectancy_%'].mean()
            
            print(f"✅ Complete! Results saved to: results/{name}.csv")
            print(f"   Average Return: {avg_return:.2f}%")
            print(f"   Average Sharpe: {avg_sharpe:.3f}")
            print(f"   Average Sortino: {avg_sortino:.3f}")
            print(f"   Average Calmar: {avg_calmar:.3f}")
            print(f"   Average Max DD: {avg_max_dd:.2f}%")
            print(f"   Total Trades: {total_trades}")
            print(f"   Average Win Rate: {avg_win_rate:.2f}%")
            print(f"   Average Profit Factor: {avg_profit_factor:.3f}")
            print(f"   Average Expectancy: {avg_expectancy:.3f}%")
            
            # Add to summary
            all_results.append({
                'Strategy': name,
                'Avg_Return_%': round(avg_return, 2),
                'Avg_Sharpe': round(avg_sharpe, 3),
                'Avg_Sortino': round(avg_sortino, 3),
                'Avg_Calmar': round(avg_calmar, 3),
                'Avg_Max_DD_%': round(avg_max_dd, 2),
                'Total_Trades': total_trades,
                'Avg_Win_Rate_%': round(avg_win_rate, 2),
                'Avg_Profit_Factor': round(avg_profit_factor, 3),
                'Avg_Expectancy_%': round(avg_expectancy, 3),
                'Best_Return_%': round(results['Return_%'].max(), 2),
                'Worst_Return_%': round(results['Return_%'].min(), 2),
            })
        else:
            print(f"❌ Failed to generate results")
    
    # Print final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY - ALL PARABOLIC SAR STRATEGIES")
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
        
        best_sortino = summary_df.loc[summary_df['Avg_Sortino'].idxmax()]
        print(f"Best Average Sortino: {best_sortino['Strategy']} ({best_sortino['Avg_Sortino']})")
        
        best_calmar = summary_df.loc[summary_df['Avg_Calmar'].idxmax()]
        print(f"Best Average Calmar: {best_calmar['Strategy']} ({best_calmar['Avg_Calmar']})")
        
        best_dd = summary_df.loc[summary_df['Avg_Max_DD_%'].idxmin()]
        print(f"Lowest Average Drawdown: {best_dd['Strategy']} ({best_dd['Avg_Max_DD_%']}%)")
        
        best_win_rate = summary_df.loc[summary_df['Avg_Win_Rate_%'].idxmax()]
        print(f"Best Win Rate: {best_win_rate['Strategy']} ({best_win_rate['Avg_Win_Rate_%']}%)")
        
        best_profit_factor = summary_df.loc[summary_df['Avg_Profit_Factor'].idxmax()]
        print(f"Best Profit Factor: {best_profit_factor['Strategy']} ({best_profit_factor['Avg_Profit_Factor']})")
        
        best_expectancy = summary_df.loc[summary_df['Avg_Expectancy_%'].idxmax()]
        print(f"Best Expectancy: {best_expectancy['Strategy']} ({best_expectancy['Avg_Expectancy_%']}%)")
        
        # Strategy recommendations
        print("\n" + "-"*60)
        print("Strategy Recommendations:")
        print("-"*60)
        
        # Sort by Sharpe ratio for overall risk-adjusted performance
        summary_df_sorted = summary_df.sort_values('Avg_Sharpe', ascending=False)
        
        print("\nTop 3 by Risk-Adjusted Performance (Sharpe Ratio):")
        for idx, row in summary_df_sorted.head(3).iterrows():
            print(f"  {row['Strategy']}: Sharpe={row['Avg_Sharpe']}, Return={row['Avg_Return_%']}%, DD={row['Avg_Max_DD_%']}%")
        
        print("\nStrategy Characteristics:")
        for _, row in summary_df.iterrows():
            strategy_name = row['Strategy']
            characteristics = []
            
            if 'Long' in strategy_name:
                characteristics.append("Long-only")
            elif 'Both' in strategy_name:
                characteristics.append("Long/Short")
            
            if 'ADX' in strategy_name:
                characteristics.append("Trend-filtered")
            elif 'Kalman' in strategy_name:
                characteristics.append("Noise-reduced")
            elif 'MFI' in strategy_name:
                characteristics.append("Momentum-confirmed")
            
            print(f"  {strategy_name}: {', '.join(characteristics)}")
    
    print("\n" + "="*80)
    print("TESTING COMPLETE!")
    print("All 5 Parabolic SAR strategies have been tested on all datasets.")
    print("Results are saved in the 'results' directory.")
    print("="*80)

if __name__ == "__main__":
    main()