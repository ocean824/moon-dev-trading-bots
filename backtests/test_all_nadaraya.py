#!/usr/bin/env python3
"""
Run all Nadaraya-Watson strategies and display summary results
"""

import pandas as pd
import os
import sys
import time

# Add parent directory to path for imports if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import all Nadaraya-Watson strategies
from nadaraya_reversal import NadarayaWatsonReversal
from nadaraya_reversal_long_only import NadarayaWatsonReversalLongOnly
from nadaraya_envelope import NadarayaWatsonEnvelope
from nadaraya_envelope_long_only import NadarayaWatsonEnvelopeLongOnly
from nadaraya_reversal_kalman import NadarayaWatsonReversalKalman
from nadaraya_envelope_kalman import NadarayaWatsonEnvelopeKalman
from nadaraya_reversal_mfi import NadarayaWatsonReversalMFI
from nadaraya_envelope_mfi import NadarayaWatsonEnvelopeMFI
from nadaraya_reversal_adx import NadarayaWatsonReversalADX
from nadaraya_envelope_adx import NadarayaWatsonEnvelopeADX
from multi_data_tester import test_on_all_data

# List of all strategies
strategies = [
    # Base strategies
    (NadarayaWatsonReversal, 'NadarayaWatsonReversal'),
    (NadarayaWatsonReversalLongOnly, 'NadarayaWatsonReversalLongOnly'),
    (NadarayaWatsonEnvelope, 'NadarayaWatsonEnvelope'),
    (NadarayaWatsonEnvelopeLongOnly, 'NadarayaWatsonEnvelopeLongOnly'),
    
    # Kalman Filter combinations
    (NadarayaWatsonReversalKalman, 'NadarayaWatsonReversalKalman'),
    (NadarayaWatsonEnvelopeKalman, 'NadarayaWatsonEnvelopeKalman'),
    
    # MFI combinations
    (NadarayaWatsonReversalMFI, 'NadarayaWatsonReversalMFI'),
    (NadarayaWatsonEnvelopeMFI, 'NadarayaWatsonEnvelopeMFI'),
    
    # ADX combinations
    (NadarayaWatsonReversalADX, 'NadarayaWatsonReversalADX'),
    (NadarayaWatsonEnvelopeADX, 'NadarayaWatsonEnvelopeADX')
]

print("="*80)
print("NADARAYA-WATSON STRATEGIES - COMPREHENSIVE TEST")
print("="*80)
print(f"\nTesting {len(strategies)} strategies across 28 data sources...")
print("This will take several minutes. Please be patient.\n")

# Track overall stats
total_start = time.time()
all_summaries = {}

for i, (strategy_class, strategy_name) in enumerate(strategies, 1):
    print(f"\n[{i}/{len(strategies)}] Testing: {strategy_name}")
    print("-"*40)
    
    start_time = time.time()
    
    try:
        # Run the strategy and capture results (verbose=False to suppress individual stats)
        results = test_on_all_data(strategy_class, strategy_name, verbose=False)
        
        elapsed = time.time() - start_time
        
        if results is not None:
            # Store the summary
            all_summaries[strategy_name] = results
            
            print(f"\n✅ {strategy_name} completed in {elapsed:.1f} seconds")
            print(f"Results saved to: ./results/{strategy_name}.csv")
            
            # Display the nice summary table
            print("\nSUMMARY:")
            print(results[['Data_Source', 'Return_%', 'Buy_Hold_%', 'Sharpe', 'Sortino', 
                          'Max_DD_%', 'Profit_Factor', 'Expectancy_%', 'Trades', 'Win_Rate_%']].to_string())
            
            # Show quick stats
            if not results.empty:
                avg_return = results['Return_%'].mean()
                positive_returns = (results['Return_%'] > 0).sum()
                total_data_sources = len(results)
                avg_sharpe = results['Sharpe'].mean()
                avg_win_rate = results['Win_Rate_%'].mean()
                
                print(f"\nKey Metrics:")
                print(f"  Average Return: {avg_return:.2f}%")
                print(f"  Average Sharpe: {avg_sharpe:.3f}")
                print(f"  Average Win Rate: {avg_win_rate:.1f}%")
                print(f"  Profitable on {positive_returns}/{total_data_sources} data sources")
        else:
            print(f"⚠️ {strategy_name} returned no results")
            
    except Exception as e:
        print(f"❌ Error running {strategy_name}: {e}")

# Final summary
total_elapsed = time.time() - total_start

print("\n" + "="*80)
print("FINAL SUMMARY - ALL NADARAYA-WATSON STRATEGIES")
print("="*80)

# Display comparison table of all strategies
if len(all_summaries) > 0:
    # Create a comparison summary
    comparison_data = []
    for strategy_name, results in all_summaries.items():
        if not results.empty:
            # Determine strategy type
            if 'long_only' in strategy_name.lower():
                strategy_type = 'Long Only'
            elif 'reversal' in strategy_name.lower():
                strategy_type = 'Reversal'
            elif 'envelope' in strategy_name.lower():
                strategy_type = 'Envelope'
            else:
                strategy_type = 'Mixed'
            
            # Determine indicator combination
            if 'kalman' in strategy_name.lower():
                indicator = 'Kalman'
            elif 'mfi' in strategy_name.lower():
                indicator = 'MFI'
            elif 'adx' in strategy_name.lower():
                indicator = 'ADX'
            else:
                indicator = 'Base'
            
            comparison_data.append({
                'Strategy': strategy_name.replace('NadarayaWatson', 'NW'),  # Shorten for display
                'Type': strategy_type,
                'Indicator': indicator,
                'Avg_Return_%': round(results['Return_%'].mean(), 2),
                'Best_Return_%': round(results['Return_%'].max(), 2),
                'Worst_Return_%': round(results['Return_%'].min(), 2),
                'Profitable_Sources': f"{(results['Return_%'] > 0).sum()}/{len(results)}",
                'Avg_Sharpe': round(results['Sharpe'].mean(), 3),
                'Avg_Win_Rate_%': round(results['Win_Rate_%'].mean(), 1),
                'Total_Trades': results['Trades'].sum(),
                'Avg_Max_DD_%': round(results['Max_DD_%'].mean(), 2)
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        
        # Sort by average return
        comparison_df = comparison_df.sort_values('Avg_Return_%', ascending=False)
        
        print("\nStrategy Performance Ranking:")
        print(comparison_df.to_string(index=False))
        
        # Group analysis
        print("\n" + "-"*60)
        print("ANALYSIS BY STRATEGY TYPE:")
        print("-"*60)
        
        # Group by Type
        type_analysis = comparison_df.groupby('Type').agg({
            'Avg_Return_%': 'mean',
            'Avg_Sharpe': 'mean',
            'Avg_Win_Rate_%': 'mean',
            'Avg_Max_DD_%': 'mean'
        }).round(2)
        print("\nBy Strategy Type:")
        print(type_analysis.to_string())
        
        # Group by Indicator
        indicator_analysis = comparison_df.groupby('Indicator').agg({
            'Avg_Return_%': 'mean',
            'Avg_Sharpe': 'mean',
            'Avg_Win_Rate_%': 'mean',
            'Avg_Max_DD_%': 'mean'
        }).round(2)
        print("\nBy Indicator Combination:")
        print(indicator_analysis.to_string())
        
        # Find best performers
        print("\n" + "-"*60)
        print("TOP PERFORMERS:")
        print("-"*60)
        
        # Best overall return
        best_return = comparison_df.iloc[0]
        print(f"\nBest Average Return: {best_return['Strategy']} ({best_return['Avg_Return_%']}%)")
        
        # Best Sharpe ratio
        best_sharpe = comparison_df.loc[comparison_df['Avg_Sharpe'].idxmax()]
        print(f"Best Sharpe Ratio: {best_sharpe['Strategy']} ({best_sharpe['Avg_Sharpe']})")
        
        # Best win rate
        best_win_rate = comparison_df.loc[comparison_df['Avg_Win_Rate_%'].idxmax()]
        print(f"Best Win Rate: {best_win_rate['Strategy']} ({best_win_rate['Avg_Win_Rate_%']}%)")
        
        # Lowest drawdown
        best_dd = comparison_df.loc[comparison_df['Avg_Max_DD_%'].idxmin()]
        print(f"Lowest Drawdown: {best_dd['Strategy']} ({best_dd['Avg_Max_DD_%']}%)")

print(f"\nTotal execution time: {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)")
print("\nAll results saved in: ./results/")

# Create a combined summary
if len(all_summaries) > 0:
    print("\nCombining all results into a master summary...")
    
    # Create results directory if it doesn't exist
    results_dir = os.path.join(current_dir, 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Combine all results with strategy name column
    combined_results = []
    for strategy_name, df in all_summaries.items():
        df_copy = df.copy()
        df_copy['Strategy'] = strategy_name
        combined_results.append(df_copy)
    
    if combined_results:
        master_df = pd.concat(combined_results, ignore_index=True)
        master_file = os.path.join(results_dir, 'NADARAYA_WATSON_ALL_RESULTS.csv')
        master_df.to_csv(master_file, index=False)
        print(f"Master summary saved to: {master_file}")
        
        # Also save the comparison summary
        if comparison_data:
            comparison_file = os.path.join(results_dir, 'NADARAYA_WATSON_COMPARISON.csv')
            comparison_df.to_csv(comparison_file, index=False)
            print(f"Comparison summary saved to: {comparison_file}")

print("="*80)
print("Testing complete! Review the results above to identify the best strategies.")
print("="*80)