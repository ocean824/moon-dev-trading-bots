"""
Moon Dev's Fibonacci Retracement Strategy Comparison
====================================================
Tests all Fibonacci retracement strategy variations and compares results
"""

import sys
import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all strategies
from fibonacci_retracement_base import FibonacciRetracementBase
from fibonacci_retracement_adx import FibonacciRetracementADX
from fibonacci_retracement_bollinger import FibonacciRetracementBollinger
from fibonacci_retracement_ema import FibonacciRetracementEMA
from fibonacci_retracement_kalman import FibonacciRetracementKalman
from fibonacci_retracement_mfi import FibonacciRetracementMFI

# Import testing framework
from multi_data_tester import test_on_all_data

print("="*80)
print("🚀 MOON DEV'S FIBONACCI RETRACEMENT STRATEGY COMPARISON 🌙")
print("="*80)
print("\nTesting all Fibonacci retracement strategy variations across all data sources...")
print("This comprehensive test will evaluate each strategy's performance.")
print("="*80)

# Define strategies to test
strategies = [
    (FibonacciRetracementBase, 'FibonacciRetracementBase', 'Base Fibonacci retracement strategy'),
    (FibonacciRetracementADX, 'FibonacciRetracementADX', 'Fibonacci + ADX trend strength'),
    (FibonacciRetracementBollinger, 'FibonacciRetracementBollinger', 'Fibonacci + Bollinger Bands'),
    (FibonacciRetracementEMA, 'FibonacciRetracementEMA', 'Fibonacci + EMA crossovers'),
    (FibonacciRetracementKalman, 'FibonacciRetracementKalman', 'Fibonacci + Kalman filter'),
    (FibonacciRetracementMFI, 'FibonacciRetracementMFI', 'Fibonacci + Money Flow Index'),
]

# Store results for comparison
all_results = {}
summary_data = []

print("\n" + "="*80)
print("STARTING COMPREHENSIVE STRATEGY TESTING")
print("="*80)

for strategy_class, strategy_name, description in strategies:
    print(f"\n{'='*80}")
    print(f"🎯 Testing: {strategy_name}")
    print(f"📊 Description: {description}")
    print(f"{'='*80}")
    
    try:
        # Test on all data sources
        results = test_on_all_data(strategy_class, strategy_name)
        
        if results is not None:
            all_results[strategy_name] = results
            
            # Calculate summary statistics
            avg_return = results['Return [%]'].mean()
            avg_sharpe = results['Sharpe Ratio'].mean()
            avg_trades = results['# Trades'].mean()
            avg_win_rate = results['Win Rate [%]'].mean()
            avg_max_dd = results['Max. Drawdown [%]'].mean()
            
            summary_data.append({
                'Strategy': strategy_name,
                'Avg Return %': round(avg_return, 2),
                'Avg Sharpe': round(avg_sharpe, 3),
                'Avg Win Rate %': round(avg_win_rate, 2),
                'Avg Max DD %': round(avg_max_dd, 2),
                'Avg Trades': round(avg_trades, 1),
                'Total Tests': len(results),
                'Profitable Tests': len(results[results['Return [%]'] > 0])
            })
            
            print(f"\n✅ Completed: {strategy_name}")
            print(f"   Average Return: {avg_return:.2f}%")
            print(f"   Average Sharpe: {avg_sharpe:.3f}")
            print(f"   Average Win Rate: {avg_win_rate:.2f}%")
            print(f"   Profitable Tests: {len(results[results['Return [%]'] > 0])}/{len(results)}")
        else:
            print(f"\n❌ Failed to get results for {strategy_name}")
            
    except Exception as e:
        print(f"\n❌ Error testing {strategy_name}: {str(e)}")
        continue

# Create comparison summary
if summary_data:
    print("\n" + "="*80)
    print("📊 FIBONACCI RETRACEMENT STRATEGIES - FINAL COMPARISON SUMMARY")
    print("="*80)
    
    summary_df = pd.DataFrame(summary_data)
    summary_df = summary_df.sort_values('Avg Return %', ascending=False)
    
    print("\n🏆 Strategy Rankings by Average Return:")
    print(summary_df.to_string(index=False))
    
    # Find best performers
    print("\n" + "="*80)
    print("🌟 KEY INSIGHTS:")
    print("="*80)
    
    best_return = summary_df.iloc[0]
    print(f"\n📈 Highest Average Return: {best_return['Strategy']}")
    print(f"   Return: {best_return['Avg Return %']}%")
    print(f"   Sharpe: {best_return['Avg Sharpe']}")
    
    best_sharpe = summary_df.nlargest(1, 'Avg Sharpe').iloc[0]
    print(f"\n📊 Best Risk-Adjusted Return (Sharpe): {best_sharpe['Strategy']}")
    print(f"   Sharpe: {best_sharpe['Avg Sharpe']}")
    print(f"   Return: {best_sharpe['Avg Return %']}%")
    
    best_win_rate = summary_df.nlargest(1, 'Avg Win Rate %').iloc[0]
    print(f"\n🎯 Highest Win Rate: {best_win_rate['Strategy']}")
    print(f"   Win Rate: {best_win_rate['Avg Win Rate %']}%")
    print(f"   Return: {best_win_rate['Avg Return %']}%")
    
    lowest_dd = summary_df.nsmallest(1, 'Avg Max DD %').iloc[0]
    print(f"\n🛡️ Lowest Drawdown: {lowest_dd['Strategy']}")
    print(f"   Max Drawdown: {lowest_dd['Avg Max DD %']}%")
    print(f"   Return: {lowest_dd['Avg Return %']}%")
    
    most_profitable = summary_df.nlargest(1, 'Profitable Tests').iloc[0]
    print(f"\n💰 Most Consistently Profitable: {most_profitable['Strategy']}")
    print(f"   Profitable Tests: {most_profitable['Profitable Tests']}/{most_profitable['Total Tests']}")
    print(f"   Success Rate: {(most_profitable['Profitable Tests']/most_profitable['Total Tests']*100):.1f}%")
    
    # Save comparison to CSV
    comparison_file = './results/fibonacci_retracement_comparison.csv'
    summary_df.to_csv(comparison_file, index=False)
    print(f"\n💾 Comparison summary saved to: {comparison_file}")
    
    # Performance by market condition insights
    print("\n" + "="*80)
    print("📈 STRATEGY RECOMMENDATIONS:")
    print("="*80)
    
    print("\n1. CONSERVATIVE APPROACH:")
    conservative = summary_df[summary_df['Avg Max DD %'] < -20].sort_values('Avg Sharpe', ascending=False)
    if not conservative.empty:
        print(f"   Recommended: {conservative.iloc[0]['Strategy']}")
        print(f"   Low drawdown with good Sharpe ratio")
    
    print("\n2. AGGRESSIVE APPROACH:")
    aggressive = summary_df.nlargest(3, 'Avg Return %')
    print(f"   Recommended: {aggressive.iloc[0]['Strategy']}")
    print(f"   Highest returns but consider the drawdown")
    
    print("\n3. BALANCED APPROACH:")
    # Calculate a balanced score
    summary_df['Balanced Score'] = (
        summary_df['Avg Return %'] / summary_df['Avg Return %'].max() * 0.4 +
        summary_df['Avg Sharpe'] / summary_df['Avg Sharpe'].max() * 0.3 +
        summary_df['Avg Win Rate %'] / summary_df['Avg Win Rate %'].max() * 0.2 +
        (1 - abs(summary_df['Avg Max DD %']) / abs(summary_df['Avg Max DD %']).max()) * 0.1
    )
    balanced = summary_df.nlargest(1, 'Balanced Score').iloc[0]
    print(f"   Recommended: {balanced['Strategy']}")
    print(f"   Best overall balance of return, risk, and consistency")

print("\n" + "="*80)
print("✅ FIBONACCI RETRACEMENT STRATEGY TESTING COMPLETE!")
print("="*80)
print("\n🚀 All strategies have been tested across all data sources.")
print("📊 Results saved in ./results/ directory for each strategy.")
print("💡 Use the insights above to select the best strategy for your trading style.")
print("\n🌙 Moon Dev's Fibonacci Retracement Testing Complete! 🚀")