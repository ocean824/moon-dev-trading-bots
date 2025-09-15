#!/usr/bin/env python3
"""
Run all 6 indicator strategies and display summary results
Moon Dev's Comprehensive Indicator Strategy Testing Suite
"""

import pandas as pd
import os
import sys
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all 6 strategies
from bollinger_mean_reversion import BollingerMeanReversionStrategy
from adx_trend_following import ADXTrendFollowingStrategy
from vwap_crossover import VWAPCrossoverStrategy
from bollinger_adx_combo import BollingerADXComboStrategy
from vwap_bollinger_bands import VWAPBollingerStrategy
from triple_indicator_strategy import TripleIndicatorStrategy
from multi_data_tester import test_on_all_data

# List of all strategies with descriptive names
strategies = [
    (BollingerMeanReversionStrategy, 'BollingerMeanReversion', 'BB Mean Reversion - Buy at lower band, sell at upper'),
    (ADXTrendFollowingStrategy, 'ADXTrendFollowing', 'ADX Trend Following - Strong trends with DI confirmation'),
    (VWAPCrossoverStrategy, 'VWAPCrossover', 'VWAP Crossover - Price crosses with volume surge'),
    (BollingerADXComboStrategy, 'BollingerADXCombo', 'BB + ADX Combo - Squeeze release with trend strength'),
    (VWAPBollingerStrategy, 'VWAPBollinger', 'VWAP + BB - Confluence of institutional levels and volatility'),
    (TripleIndicatorStrategy, 'TripleIndicator', 'Triple Indicator - ADX + BB + VWAP all aligned')
]

print("="*80)
print("MOON DEV'S INDICATOR STRATEGIES - COMPREHENSIVE TESTING SUITE")
print("="*80)
print("Testing 6 Advanced Indicator Strategies Across 25+ Data Sources")
print("-"*80)

# Track overall stats
total_start = time.time()
all_summaries = {}

for i, (strategy_class, strategy_name, description) in enumerate(strategies, 1):
    print(f"\n[{i}/{len(strategies)}] Testing: {strategy_name}")
    print(f"Description: {description}")
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
            
            # Display key metrics
            print("\nKEY METRICS:")
            key_metrics = results[['Data_Source', 'Return_%', 'Buy_Hold_%', 'Sharpe', 'Sortino', 
                                   'Max_DD_%', 'Win_Rate_%', 'Profit_Factor', 'Trades']]
            
            # Show top 5 performers
            top_5 = key_metrics.nlargest(5, 'Return_%')
            print("\nTop 5 Performing Data Sources:")
            print(top_5.to_string())
            
            # Show quick stats
            if not results.empty:
                avg_return = results['Return_%'].mean()
                avg_sharpe = results['Sharpe'].mean()
                avg_win_rate = results['Win_Rate_%'].mean()
                positive_returns = (results['Return_%'] > 0).sum()
                total_data_sources = len(results)
                beat_buy_hold = (results['Return_%'] > results['Buy_Hold_%']).sum()
                
                print(f"\nSUMMARY STATISTICS:")
                print(f"  Average Return: {avg_return:.2f}%")
                print(f"  Average Sharpe: {avg_sharpe:.3f}")
                print(f"  Average Win Rate: {avg_win_rate:.1f}%")
                print(f"  Profitable on {positive_returns}/{total_data_sources} data sources ({positive_returns/total_data_sources*100:.1f}%)")
                print(f"  Beat Buy&Hold on {beat_buy_hold}/{total_data_sources} data sources ({beat_buy_hold/total_data_sources*100:.1f}%)")
        else:
            print(f"⚠️ {strategy_name} returned no results")
            
    except Exception as e:
        print(f"❌ Error running {strategy_name}: {e}")

# Final summary
total_elapsed = time.time() - total_start

print("\n" + "="*80)
print("FINAL SUMMARY - ALL INDICATOR STRATEGIES")
print("="*80)

# Display comparison table of all strategies
if len(all_summaries) > 0:
    # Create a comprehensive comparison
    comparison_data = []
    for strategy_name, results in all_summaries.items():
        if not results.empty:
            # Find the corresponding description
            description = next((desc for _, name, desc in strategies if name == strategy_name), strategy_name)
            
            comparison_data.append({
                'Strategy': strategy_name,
                'Avg_Return_%': round(results['Return_%'].mean(), 2),
                'Best_Return_%': round(results['Return_%'].max(), 2),
                'Worst_Return_%': round(results['Return_%'].min(), 2),
                'Std_Dev_%': round(results['Return_%'].std(), 2),
                'Profitable_Sources': f"{(results['Return_%'] > 0).sum()}/{len(results)}",
                'Beat_BuyHold': f"{(results['Return_%'] > results['Buy_Hold_%']).sum()}/{len(results)}",
                'Avg_Sharpe': round(results['Sharpe'].mean(), 3),
                'Avg_Sortino': round(results['Sortino'].mean(), 3),
                'Avg_Win_Rate_%': round(results['Win_Rate_%'].mean(), 1),
                'Avg_Profit_Factor': round(results['Profit_Factor'].mean(), 2),
                'Total_Trades': results['Trades'].sum(),
                'Avg_Max_DD_%': round(results['Max_DD_%'].mean(), 2)
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        
        # Sort by average return
        comparison_df = comparison_df.sort_values('Avg_Return_%', ascending=False)
        
        print("\nSTRATEGY PERFORMANCE RANKING:")
        print(comparison_df.to_string(index=False))
        
        # Find best overall strategy
        best_strategy = comparison_df.iloc[0]
        print(f"\n🏆 BEST OVERALL STRATEGY: {best_strategy['Strategy']}")
        print(f"   Average Return: {best_strategy['Avg_Return_%']}%")
        print(f"   Average Sharpe: {best_strategy['Avg_Sharpe']}")
        print(f"   Win Rate: {best_strategy['Avg_Win_Rate_%']}%")
        
        # Additional analysis
        print("\nADDITIONAL INSIGHTS:")
        
        # Most consistent (lowest std dev)
        most_consistent = comparison_df.nsmallest(1, 'Std_Dev_%').iloc[0]
        print(f"Most Consistent: {most_consistent['Strategy']} (Std Dev: {most_consistent['Std_Dev_%']}%)")
        
        # Best risk-adjusted (highest Sharpe)
        best_sharpe = comparison_df.nlargest(1, 'Avg_Sharpe').iloc[0]
        print(f"Best Risk-Adjusted: {best_sharpe['Strategy']} (Sharpe: {best_sharpe['Avg_Sharpe']})")
        
        # Best win rate
        best_win_rate = comparison_df.nlargest(1, 'Avg_Win_Rate_%').iloc[0]
        print(f"Best Win Rate: {best_win_rate['Strategy']} ({best_win_rate['Avg_Win_Rate_%']}%)")
        
        # Lowest drawdown
        lowest_dd = comparison_df.nsmallest(1, 'Avg_Max_DD_%').iloc[0]
        print(f"Lowest Drawdown: {lowest_dd['Strategy']} ({lowest_dd['Avg_Max_DD_%']}%)")

print(f"\nTotal execution time: {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)")
print("\nAll individual results saved in: ./results/")

# Create a combined master summary
if len(all_summaries) > 0:
    print("\nCreating master summary file...")
    
    # Create results directory if it doesn't exist
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(results_dir, exist_ok=True)
    
    # Combine all results with strategy name column
    combined_results = []
    for strategy_name, df in all_summaries.items():
        df_copy = df.copy()
        df_copy['Strategy'] = strategy_name
        combined_results.append(df_copy)
    
    if combined_results:
        master_df = pd.concat(combined_results, ignore_index=True)
        
        # Add timestamp to filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        master_file = os.path.join(results_dir, f'INDICATOR_STRATEGIES_MASTER_{timestamp}.csv')
        
        master_df.to_csv(master_file, index=False)
        print(f"Master summary saved to: {master_file}")
        
        # Also save the comparison summary
        if comparison_data:
            comparison_file = os.path.join(results_dir, f'INDICATOR_STRATEGIES_COMPARISON_{timestamp}.csv')
            comparison_df.to_csv(comparison_file, index=False)
            print(f"Comparison summary saved to: {comparison_file}")

print("="*80)
print("TESTING COMPLETE - ALL 6 INDICATOR STRATEGIES EVALUATED")
print("="*80)