"""
Quick Test Script for Smart Money Breakout Strategies
=======================================================

Tests all Smart Money strategies on a single dataset for rapid validation.
"""

import sys
import os
import pandas as pd
from backtesting import Backtest

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import all strategies
from smart_money_base import SmartMoneyBase
from smart_money_mfi import SmartMoneyMFI
from smart_money_adx import SmartMoneyADX
from smart_money_kalman import SmartMoneyKalman

print("\n" + "="*80)
print("🚀 QUICK TEST - Smart Money Breakout Strategies 🚀")
print("="*80)

# Load test data
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'
print(f"\n📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows")

# Test parameters
CASH = 10000000
COMMISSION = 0.00045

# Strategies to test
strategies = {
    'Base': SmartMoneyBase,
    'MFI': SmartMoneyMFI,
    'ADX': SmartMoneyADX,
    'Kalman': SmartMoneyKalman
}

# Results storage
results = []

print("\n" + "-"*80)
print("Running backtests...")
print("-"*80)

for name, strategy_class in strategies.items():
    print(f"\n📈 Testing Smart Money {name} Strategy...")

    try:
        # Run backtest
        bt = Backtest(data, strategy_class, cash=CASH, commission=COMMISSION)
        stats = bt.run()

        # Extract key metrics
        result = {
            'Strategy': f'Smart Money {name}',
            'Return %': round(stats['Return [%]'], 2),
            'Sharpe': round(stats['Sharpe Ratio'], 3) if pd.notna(stats['Sharpe Ratio']) else 0,
            'Sortino': round(stats['Sortino Ratio'], 3) if pd.notna(stats['Sortino Ratio']) else 0,
            'Max DD %': round(stats['Max. Drawdown [%]'], 2),
            'Trades': stats['# Trades'],
            'Win Rate %': round(stats['Win Rate [%]'], 2) if pd.notna(stats['Win Rate [%]']) else 0,
            'Avg Trade %': round(stats['Avg. Trade [%]'], 3) if pd.notna(stats['Avg. Trade [%]']) else 0,
            'Profit Factor': round(stats['Profit Factor'], 3) if pd.notna(stats['Profit Factor']) else 0,
        }
        results.append(result)

        print(f"✅ Complete - Return: {result['Return %']}%, Sharpe: {result['Sharpe']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        continue

# Display comparison
if results:
    print("\n" + "="*80)
    print("📊 STRATEGY COMPARISON")
    print("="*80)

    df_results = pd.DataFrame(results)
    print("\n" + df_results.to_string(index=False))

    # Find best performers
    print("\n" + "-"*80)
    print("🏆 BEST PERFORMERS")
    print("-"*80)

    # Best return
    best_return = df_results.loc[df_results['Return %'].idxmax()]
    print(f"\nHighest Return: {best_return['Strategy']}")
    print(f"  Return: {best_return['Return %']}%")

    # Best Sharpe
    best_sharpe = df_results.loc[df_results['Sharpe'].idxmax()]
    print(f"\nBest Risk-Adjusted (Sharpe): {best_sharpe['Strategy']}")
    print(f"  Sharpe: {best_sharpe['Sharpe']}")

    # Best Sortino
    best_sortino = df_results.loc[df_results['Sortino'].idxmax()]
    print(f"\nBest Downside Protection (Sortino): {best_sortino['Strategy']}")
    print(f"  Sortino: {best_sortino['Sortino']}")

    # Most trades
    most_active = df_results.loc[df_results['Trades'].idxmax()]
    print(f"\nMost Active: {most_active['Strategy']}")
    print(f"  Trades: {most_active['Trades']}")

    # Save results
    results_dir = 'results'
    os.makedirs(results_dir, exist_ok=True)
    csv_path = os.path.join(results_dir, 'quick_test_comparison.csv')
    df_results.to_csv(csv_path, index=False)
    print(f"\n💾 Results saved to: {csv_path}")

print("\n" + "="*80)
print("✅ Quick test complete!")
print("="*80)