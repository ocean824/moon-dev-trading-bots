#!/usr/bin/env python3
"""
Test all Bayesian Whale strategies and display comprehensive comparison
========================================================================
Moon Dev's Bayesian Whale Strategy Suite Test Runner

Runs and compares:
1. BayesianWhaleMulti - Base strategy with all three indicators
2. BayesianWhaleADXMulti - With ADX trend strength filter
3. BayesianWhaleMFIMulti - With MFI money flow filter
"""

import pandas as pd
import os
import sys
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import strategies directly
from bayesian_whale_multi import BayesianWhaleMulti
from bayesian_whale_adx_multi import BayesianWhaleADXMulti
from bayesian_whale_mfi_multi import BayesianWhaleMFIMulti
from multi_data_tester import test_on_all_data

# List of all strategies
strategies = [
    (BayesianWhaleMulti, 'BayesianWhaleMulti'),
    (BayesianWhaleADXMulti, 'BayesianWhaleADXMulti'),
    (BayesianWhaleMFIMulti, 'BayesianWhaleMFIMulti')
]

print("="*80)
print("🚀 BAYESIAN WHALE STRATEGIES - COMPREHENSIVE TESTING 🌙")
print("="*80)
print("\nTesting Configuration:")
print("  Initial Capital: $100,000")
print("  Commission: 0.2%")
print("  Data Sources: 25+ markets across crypto and stocks")
print("="*80)

# Track overall stats
total_start = time.time()
all_summaries = {}

for i, (strategy_class, strategy_name) in enumerate(strategies, 1):
    print(f"\n[{i}/{len(strategies)}] Testing: {strategy_name}")
    print("-"*40)
    
    start_time = time.time()
    
    try:
        # Run the strategy with full verbose output
        print(f"\nRunning {strategy_name} on all data sources...")
        results = test_on_all_data(
            strategy_class, 
            strategy_name, 
            cash=100000,
            commission=0.002,
            verbose=True  # Show full stats for each dataset
        )
        
        elapsed = time.time() - start_time
        
        if results is not None:
            # Store the summary
            all_summaries[strategy_name] = results
            
            print(f"\n✅ {strategy_name} completed in {elapsed:.1f} seconds")
            
            # Quick stats
            if not results.empty:
                avg_return = results['Return_%'].mean()
                positive_returns = (results['Return_%'] > 0).sum()
                total_data_sources = len(results)
                best_return = results['Return_%'].max()
                best_source = results.loc[results['Return_%'].idxmax(), 'Data_Source']
                
                print(f"\nQuick Stats for {strategy_name}:")
                print(f"  Average Return: {avg_return:.2f}%")
                print(f"  Best Return: {best_return:.2f}% on {best_source}")
                print(f"  Profitable on {positive_returns}/{total_data_sources} data sources")
                print(f"  Average Sharpe: {results['Sharpe'].mean():.3f}")
                print(f"  Total Trades: {results['Trades'].sum()}")
        else:
            print(f"⚠️ {strategy_name} returned no results")
            
    except Exception as e:
        print(f"❌ Error running {strategy_name}: {e}")

# Final summary
total_elapsed = time.time() - total_start

print("\n" + "="*80)
print("FINAL COMPARISON - ALL BAYESIAN WHALE STRATEGIES")
print("="*80)

# Display comparison table of all strategies
if len(all_summaries) > 0:
    # Create a detailed comparison
    comparison_data = []
    for strategy_name, results in all_summaries.items():
        if not results.empty:
            # Calculate additional metrics
            positive_datasets = (results['Return_%'] > 0).sum()
            total_datasets = len(results)
            
            # Best and worst performances
            best_idx = results['Return_%'].idxmax()
            worst_idx = results['Return_%'].idxmin()
            
            comparison_data.append({
                'Strategy': strategy_name.replace('BayesianWhale', 'BW'),
                'Avg_Return_%': round(results['Return_%'].mean(), 2),
                'Median_Return_%': round(results['Return_%'].median(), 2),
                'Best_Return_%': round(results['Return_%'].max(), 2),
                'Worst_Return_%': round(results['Return_%'].min(), 2),
                'Profitable': f"{positive_datasets}/{total_datasets}",
                'Win_Rate_%': round(results['Win_Rate_%'].mean(), 1),
                'Avg_Trades': round(results['Trades'].mean(), 0),
                'Total_Trades': results['Trades'].sum(),
                'Avg_Sharpe': round(results['Sharpe'].mean(), 3),
                'Best_Sharpe': round(results['Sharpe'].max(), 3),
                'Avg_DD_%': round(results['Max_DD_%'].mean(), 2),
                'Avg_PF': round(results['Profit_Factor'].mean(), 2),
            })
    
    if comparison_data:
        comparison_df = pd.DataFrame(comparison_data)
        print("\n📊 Strategy Performance Comparison:")
        print(comparison_df.to_string(index=False))
        
        # Find the best strategy
        best_by_return = comparison_df.loc[comparison_df['Avg_Return_%'].idxmax(), 'Strategy']
        best_by_sharpe = comparison_df.loc[comparison_df['Avg_Sharpe'].idxmax(), 'Strategy']
        best_by_winrate = comparison_df.loc[comparison_df['Win_Rate_%'].idxmax(), 'Strategy']
        
        print("\n🏆 Winners by Category:")
        print(f"  Best Average Return: {best_by_return}")
        print(f"  Best Sharpe Ratio: {best_by_sharpe}")
        print(f"  Best Win Rate: {best_by_winrate}")

# Asset class breakdown
print("\n" + "="*80)
print("PERFORMANCE BY ASSET CLASS")
print("="*80)

for strategy_name, results in all_summaries.items():
    if results.empty:
        continue
        
    print(f"\n{strategy_name}:")
    print("-" * 40)
    
    # Group by asset
    btc_results = results[results['Data_Source'].str.contains('BTC')]
    eth_results = results[results['Data_Source'].str.contains('ETH')]
    sol_results = results[results['Data_Source'].str.contains('SOL')]
    stock_results = results[~results['Data_Source'].str.contains('BTC|ETH|SOL')]
    
    asset_summary = []
    
    if not btc_results.empty:
        asset_summary.append({
            'Asset': 'Bitcoin',
            'Avg_Return_%': round(btc_results['Return_%'].mean(), 2),
            'Best_%': round(btc_results['Return_%'].max(), 2),
            'Trades': btc_results['Trades'].sum()
        })
    
    if not eth_results.empty:
        asset_summary.append({
            'Asset': 'Ethereum',
            'Avg_Return_%': round(eth_results['Return_%'].mean(), 2),
            'Best_%': round(eth_results['Return_%'].max(), 2),
            'Trades': eth_results['Trades'].sum()
        })
    
    if not sol_results.empty:
        asset_summary.append({
            'Asset': 'Solana',
            'Avg_Return_%': round(sol_results['Return_%'].mean(), 2),
            'Best_%': round(sol_results['Return_%'].max(), 2),
            'Trades': sol_results['Trades'].sum()
        })
    
    if not stock_results.empty:
        asset_summary.append({
            'Asset': 'Stocks/Futures',
            'Avg_Return_%': round(stock_results['Return_%'].mean(), 2),
            'Best_%': round(stock_results['Return_%'].max(), 2),
            'Trades': stock_results['Trades'].sum()
        })
    
    if asset_summary:
        asset_df = pd.DataFrame(asset_summary)
        print(asset_df.to_string(index=False))

# Timeframe analysis
print("\n" + "="*80)
print("PERFORMANCE BY TIMEFRAME")
print("="*80)

for strategy_name, results in all_summaries.items():
    if results.empty:
        continue
        
    print(f"\n{strategy_name}:")
    print("-" * 40)
    
    # Group by timeframe
    tf_summary = []
    
    # Define timeframe patterns
    timeframes = {
        '1m': '1m',
        '5m': '5m',
        '15m': '15m',
        '1h': '1h',
        '6h': '6h',
        '1d': '1d',
        '4h': '4h',
        'hourly': 'hourly'
    }
    
    for tf_name, tf_pattern in timeframes.items():
        tf_results = results[results['Data_Source'].str.contains(tf_pattern, case=False)]
        if not tf_results.empty:
            tf_summary.append({
                'Timeframe': tf_name,
                'Datasets': len(tf_results),
                'Avg_Return_%': round(tf_results['Return_%'].mean(), 2),
                'Win_Rate_%': round(tf_results['Win_Rate_%'].mean(), 1),
                'Avg_Trades': round(tf_results['Trades'].mean(), 0)
            })
    
    if tf_summary:
        tf_df = pd.DataFrame(tf_summary)
        tf_df = tf_df.sort_values('Avg_Return_%', ascending=False)
        print(tf_df.to_string(index=False))

print(f"\n⏱️ Total execution time: {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)")

# Create combined summary
if len(all_summaries) > 0:
    print("\n" + "="*80)
    print("CREATING MASTER SUMMARY FILES")
    print("="*80)
    
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
        master_file = os.path.join(results_dir, 'BAYESIAN_WHALE_ALL_RESULTS.csv')
        master_df.to_csv(master_file, index=False)
        print(f"✅ Master results saved to: {master_file}")
        
        # Create comparison summary
        if comparison_data:
            comparison_file = os.path.join(results_dir, 'BAYESIAN_WHALE_COMPARISON.csv')
            comparison_df.to_csv(comparison_file, index=False)
            print(f"✅ Comparison summary saved to: {comparison_file}")

print("\n" + "="*80)
print("🎯 TESTING COMPLETE - All Bayesian Whale Strategies Evaluated")
print("="*80)