"""
🌙 Moon Dev's Camarilla Pivot Strategies - Test All Versions
=============================================================
Tests all 5 Camarilla Pivot strategies and compares results
"""

import pandas as pd
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multi_data_tester import test_on_all_data
from camarilla_pivot_long_short import CamarillaPivotLongShort
from camarilla_pivot_long_only import CamarillaPivotLongOnly
from camarilla_pivot_80_percent import CamarillaPivot80Percent
from camarilla_pivot_kalman import CamarillaPivotKalman
from camarilla_pivot_mfi import CamarillaPivotMFI

def main():
    """Test all Camarilla strategies and compare results"""
    
    print("\n" + "="*80)
    print("🌙 MOON DEV'S CAMARILLA PIVOT STRATEGIES - COMPREHENSIVE TEST")
    print("="*80)
    print("Testing 5 Camarilla Pivot variations across all datasets...")
    print("="*80)
    
    # Define strategies to test
    strategies = [
        (CamarillaPivotLongShort, 'CamarillaPivotLongShort', 'Long/Short - Standard reversal and breakout trading'),
        (CamarillaPivotLongOnly, 'CamarillaPivotLongOnly', 'Long Only - Focus on oversold bounces'),
        (CamarillaPivot80Percent, 'CamarillaPivot80Percent', '80% Retracement - Tighter bands for more signals'),
        (CamarillaPivotKalman, 'CamarillaPivotKalman', 'Kalman Filtered - Smoothed pivots to reduce noise'),
        (CamarillaPivotMFI, 'CamarillaPivotMFI', 'MFI Combined - Money Flow Index for confirmation'),
    ]
    
    all_results = {}
    summary_data = []
    
    # Test each strategy
    for i, (strategy_class, strategy_name, description) in enumerate(strategies, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/{len(strategies)}] Testing: {strategy_name}")
        print(f"Description: {description}")
        print("="*80)
        
        try:
            # Run test on all data
            results = test_on_all_data(
                strategy_class, 
                strategy_name,
                optimize=False,
                verbose=False  # Less verbose for batch testing
            )
            
            if results is not None:
                all_results[strategy_name] = results
                
                # Calculate summary statistics
                avg_return = results['Return_%'].mean()
                avg_sharpe = results['Sharpe'].mean()
                avg_win_rate = results['Win_Rate_%'].mean()
                total_trades = results['Trades'].sum()
                profitable_datasets = len(results[results['Return_%'] > 0])
                
                summary_data.append({
                    'Strategy': strategy_name,
                    'Avg_Return_%': round(avg_return, 2),
                    'Avg_Sharpe': round(avg_sharpe, 3),
                    'Avg_Win_Rate_%': round(avg_win_rate, 2),
                    'Total_Trades': total_trades,
                    'Profitable_Datasets': profitable_datasets,
                    'Total_Datasets': len(results),
                    'Success_Rate_%': round(profitable_datasets / len(results) * 100, 1)
                })
                
                print(f"✅ {strategy_name} completed:")
                print(f"   Average Return: {avg_return:.2f}%")
                print(f"   Average Sharpe: {avg_sharpe:.3f}")
                print(f"   Profitable on {profitable_datasets}/{len(results)} datasets")
                
        except Exception as e:
            print(f"❌ Error testing {strategy_name}: {str(e)}")
            continue
    
    # Display comprehensive comparison
    if summary_data:
        print("\n" + "="*80)
        print("📊 CAMARILLA STRATEGIES COMPARISON")
        print("="*80)
        
        summary_df = pd.DataFrame(summary_data)
        summary_df = summary_df.sort_values('Avg_Return_%', ascending=False)
        
        print("\nSummary Table (sorted by Average Return):")
        print(summary_df.to_string(index=False))
        
        # Find best performers
        print("\n" + "="*80)
        print("🏆 BEST PERFORMERS")
        print("="*80)
        
        best_return = summary_df.iloc[0]
        print(f"Highest Average Return: {best_return['Strategy']} ({best_return['Avg_Return_%']}%)")
        
        best_sharpe = summary_df.loc[summary_df['Avg_Sharpe'].idxmax()]
        print(f"Best Risk-Adjusted (Sharpe): {best_sharpe['Strategy']} ({best_sharpe['Avg_Sharpe']})")
        
        best_win_rate = summary_df.loc[summary_df['Avg_Win_Rate_%'].idxmax()]
        print(f"Highest Win Rate: {best_win_rate['Strategy']} ({best_win_rate['Avg_Win_Rate_%']}%)")
        
        most_consistent = summary_df.loc[summary_df['Success_Rate_%'].idxmax()]
        print(f"Most Consistent: {most_consistent['Strategy']} (profitable on {most_consistent['Success_Rate_%']}% of datasets)")
        
        # Save comparison results
        comparison_file = 'results/camarilla_comparison.csv'
        summary_df.to_csv(comparison_file, index=False)
        print(f"\n💾 Comparison saved to: {comparison_file}")
        
        # Detailed performance by dataset
        print("\n" + "="*80)
        print("📈 TOP PERFORMING DATASETS ACROSS ALL STRATEGIES")
        print("="*80)
        
        # Combine all results to find best dataset-strategy combinations
        best_combos = []
        for strategy_name, results in all_results.items():
            for _, row in results.iterrows():
                best_combos.append({
                    'Strategy': strategy_name.replace('CamarillaPivot', 'CP_'),
                    'Dataset': row['Data_Source'],
                    'Return_%': row['Return_%'],
                    'Sharpe': row['Sharpe'],
                    'Trades': row['Trades']
                })
        
        best_combos_df = pd.DataFrame(best_combos)
        best_combos_df = best_combos_df.sort_values('Return_%', ascending=False).head(10)
        
        print("\nTop 10 Strategy-Dataset Combinations:")
        print(best_combos_df.to_string(index=False))
        
    print("\n" + "="*80)
    print("✅ All Camarilla Pivot strategies tested successfully!")
    print("="*80)

if __name__ == "__main__":
    main()