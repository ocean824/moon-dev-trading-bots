"""
Test All Acceleration Strategies
=================================
Runs all 5 acceleration-based strategies and compares results
"""

import pandas as pd
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import all acceleration strategies
from acceleration_bands import AccelerationBandsStrategy
from acceleration_ao import AccelerationAOStrategy
from acceleration_rsi import AccelerationRSIStrategy
from acceleration_bands_kalman import AccelerationBandsKalmanStrategy
from acceleration_ao_kalman import AccelerationAOKalmanStrategy
from multi_data_tester import test_on_all_data

def main():
    """Test all acceleration strategies and create comparison"""
    
    print("\n" + "="*80)
    print("MOON DEV'S ACCELERATION STRATEGIES - COMPREHENSIVE TEST")
    print("="*80)
    print("Testing 5 Acceleration-Based Strategies")
    print("1. Acceleration Bands")
    print("2. Acceleration AO (Awesome Oscillator)")
    print("3. Acceleration RSI")
    print("4. Acceleration Bands with Kalman Filter")
    print("5. Acceleration AO with Kalman Filter")
    print("="*80)
    
    # Define strategies to test
    strategies = [
        (AccelerationBandsStrategy, 'AccelerationBands'),
        (AccelerationAOStrategy, 'AccelerationAO'),
        (AccelerationRSIStrategy, 'AccelerationRSI'),
        (AccelerationBandsKalmanStrategy, 'AccelerationBandsKalman'),
        (AccelerationAOKalmanStrategy, 'AccelerationAOKalman'),
    ]
    
    all_results = []
    
    # Test each strategy
    for i, (strategy_class, strategy_name) in enumerate(strategies, 1):
        print(f"\n[{i}/{len(strategies)}] Testing {strategy_name}...")
        print("-" * 60)
        
        try:
            # Run tests on all data sources
            results = test_on_all_data(
                strategy_class,
                strategy_name,
                optimize=False,
                cash=10000000,
                commission=0.00045,
                verbose=True
            )
            
            if results is not None:
                # Add strategy name to results
                results['Strategy'] = strategy_name
                all_results.append(results)
                print(f"✅ {strategy_name} complete!")
            else:
                print(f"⚠️ {strategy_name} - No results generated")
                
        except Exception as e:
            print(f"❌ Error testing {strategy_name}: {str(e)}")
            continue
    
    # Combine all results
    if all_results:
        combined_df = pd.concat(all_results, ignore_index=True)
        
        # Save combined results
        output_file = 'results/ACCELERATION_STRATEGIES_ALL.csv'
        combined_df.to_csv(output_file, index=False)
        
        print("\n" + "="*80)
        print("SUMMARY STATISTICS BY STRATEGY")
        print("="*80)
        
        # Calculate summary statistics for each strategy
        summary_stats = []
        for strategy_name in combined_df['Strategy'].unique():
            strategy_data = combined_df[combined_df['Strategy'] == strategy_name]
            
            stats = {
                'Strategy': strategy_name,
                'Avg_Return_%': round(strategy_data['Return_%'].mean(), 2),
                'Median_Return_%': round(strategy_data['Return_%'].median(), 2),
                'Best_Return_%': round(strategy_data['Return_%'].max(), 2),
                'Worst_Return_%': round(strategy_data['Return_%'].min(), 2),
                'Profitable_Count': len(strategy_data[strategy_data['Return_%'] > 0]),
                'Total_Datasets': len(strategy_data),
                'Win_Rate_%': round(len(strategy_data[strategy_data['Return_%'] > 0]) / len(strategy_data) * 100, 1),
                'Avg_Sharpe': round(strategy_data['Sharpe'].mean(), 3),
                'Avg_Sortino': round(strategy_data['Sortino'].mean(), 3),
                'Avg_Max_DD_%': round(strategy_data['Max_DD_%'].mean(), 2),
                'Avg_Trades': round(strategy_data['Trades'].mean(), 0),
                'Avg_Trade_Win_%': round(strategy_data['Win_Rate_%'].mean(), 2),
            }
            summary_stats.append(stats)
        
        summary_df = pd.DataFrame(summary_stats)
        summary_df = summary_df.sort_values('Avg_Return_%', ascending=False)
        
        print(summary_df.to_string(index=False))
        
        # Save summary
        summary_file = 'results/ACCELERATION_STRATEGIES_SUMMARY.csv'
        summary_df.to_csv(summary_file, index=False)
        
        print("\n" + "="*80)
        print("TOP PERFORMING DATASETS BY STRATEGY")
        print("="*80)
        
        # Show top 3 results for each strategy
        for strategy_name in combined_df['Strategy'].unique():
            strategy_data = combined_df[combined_df['Strategy'] == strategy_name]
            top_3 = strategy_data.nlargest(3, 'Return_%')[['Data_Source', 'Return_%', 'Sharpe', 'Trades']]
            print(f"\n{strategy_name} - Top 3:")
            print(top_3.to_string(index=False))
        
        print("\n" + "="*80)
        print("FILES SAVED:")
        print(f"1. All Results: {output_file}")
        print(f"2. Summary Stats: {summary_file}")
        print(f"3. Individual Strategy Results in results/ directory")
        print("="*80)
        
        # Best overall strategy
        best_strategy = summary_df.iloc[0]
        print(f"\n🏆 BEST OVERALL STRATEGY: {best_strategy['Strategy']}")
        print(f"   Average Return: {best_strategy['Avg_Return_%']}%")
        print(f"   Win Rate: {best_strategy['Win_Rate_%']}%")
        print(f"   Average Sharpe: {best_strategy['Avg_Sharpe']}")
        
    else:
        print("\n❌ No results generated from any strategy")
    
    print("\n✅ All acceleration strategies testing complete!")

if __name__ == "__main__":
    main()