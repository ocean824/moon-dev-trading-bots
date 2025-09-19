#!/usr/bin/env python3
"""
Test all Smart Money strategies and save results
Dr. Data Dawg's Smart Money Testing Suite 🌙
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
from backtesting import Backtest
import warnings
warnings.filterwarnings('ignore')

# Test with the simplified working strategy first
from smart_money_simple import SmartMoneySimple

# Data to test
TEST_DATA = [
    ('BTC-1h-500wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'),
    ('BTC-15m-150wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-15m-150wks-data.csv'),
    ('BTC-1d-100wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-100wks-data.csv'),
    ('ETH-1h-250wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1h-250wks-data.csv'),
    ('SOL-1h-250wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1h-250wks-data.csv'),
]

def load_data(filepath, limit_rows=None):
    """Load and prepare data"""
    try:
        df = pd.read_csv(filepath)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime')
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        df = df.sort_index()
        df = df.dropna()

        if limit_rows:
            df = df.tail(limit_rows)

        return df
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def test_strategy(strategy_class, strategy_name, data_name, df):
    """Run a single backtest"""
    try:
        bt = Backtest(df, strategy_class, cash=1000000, commission=0.002)
        stats = bt.run()

        result = {
            'Strategy': strategy_name,
            'Dataset': data_name,
            'Rows': len(df),
            'Return_%': round(stats['Return [%]'], 2),
            'Buy_Hold_%': round(stats['Buy & Hold Return [%]'], 2),
            'Sharpe': round(stats['Sharpe Ratio'], 3),
            'Sortino': round(stats['Sortino Ratio'], 3),
            'Max_DD_%': round(stats['Max. Drawdown [%]'], 2),
            'Win_Rate_%': round(stats.get('Win Rate [%]', 0), 1),
            'Trades': stats['# Trades'],
            'Avg_Trade_%': round(stats.get('Avg. Trade [%]', 0), 3),
            'Profit_Factor': round(stats.get('Profit Factor', 0), 3),
            'Exposure_%': round(stats['Exposure Time [%]'], 1),
        }

        return result, stats

    except Exception as e:
        print(f"Error testing {strategy_name} on {data_name}: {str(e)[:100]}")
        return None, None

def main():
    print("\n" + "="*80)
    print("🌙 DR. DATA DAWG'S SMART MONEY BREAKOUT TESTING 🌙")
    print("="*80)

    # Results storage
    all_results = []

    # Results directory
    results_dir = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/smart_money_breakout/results"
    os.makedirs(results_dir, exist_ok=True)

    # Test the simplified strategy on all datasets
    print("\nTesting SmartMoneySimple strategy...")
    print("-"*60)

    for data_name, data_path in TEST_DATA:
        print(f"\nTesting on {data_name}...", end=" ")

        # Load data (use last 20,000 bars for speed)
        df = load_data(data_path, limit_rows=20000)

        if df is None:
            print("❌ Failed to load data")
            continue

        # Test strategy
        result, stats = test_strategy(SmartMoneySimple, 'SmartMoneySimple', data_name, df)

        if result:
            all_results.append(result)
            print(f"✅ Return: {result['Return_%']}%, Trades: {result['Trades']}, Sharpe: {result['Sharpe']}")
        else:
            print("❌ Test failed")

    # Now try to import and test other strategies
    print("\n" + "="*60)
    print("Testing other Smart Money strategies...")
    print("-"*60)

    # Try to import other strategies
    try:
        from smart_money_base import SmartMoneyBreakoutBase
        print("Testing SmartMoneyBreakoutBase...")

        # Test on BTC hourly only for now
        df = load_data(TEST_DATA[0][1], limit_rows=10000)
        if df is not None:
            result, stats = test_strategy(SmartMoneyBreakoutBase, 'SmartMoney_Base', 'BTC-1h-10k', df)
            if result:
                all_results.append(result)
                print(f"✅ Base strategy: Return {result['Return_%']}%, Trades: {result['Trades']}")
            else:
                print("❌ Base strategy failed")
    except Exception as e:
        print(f"❌ Could not test base strategy: {e}")

    try:
        from smart_money_volume import SmartMoneyBreakoutVolume
        print("Testing SmartMoneyBreakoutVolume...")

        df = load_data(TEST_DATA[0][1], limit_rows=10000)
        if df is not None:
            result, stats = test_strategy(SmartMoneyBreakoutVolume, 'SmartMoney_Volume', 'BTC-1h-10k', df)
            if result:
                all_results.append(result)
                print(f"✅ Volume strategy: Return {result['Return_%']}%, Trades: {result['Trades']}")
            else:
                print("❌ Volume strategy failed")
    except Exception as e:
        print(f"❌ Could not test volume strategy: {e}")

    try:
        from smart_money_rsi import SmartMoneyBreakoutRSI
        print("Testing SmartMoneyBreakoutRSI...")

        df = load_data(TEST_DATA[0][1], limit_rows=10000)
        if df is not None:
            result, stats = test_strategy(SmartMoneyBreakoutRSI, 'SmartMoney_RSI', 'BTC-1h-10k', df)
            if result:
                all_results.append(result)
                print(f"✅ RSI strategy: Return {result['Return_%']}%, Trades: {result['Trades']}")
            else:
                print("❌ RSI strategy failed")
    except Exception as e:
        print(f"❌ Could not test RSI strategy: {e}")

    # Save results
    if all_results:
        results_df = pd.DataFrame(all_results)

        # Save to CSV
        csv_file = f"{results_dir}/smart_money_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        results_df.to_csv(csv_file, index=False)

        print("\n" + "="*80)
        print("📊 RESULTS SUMMARY")
        print("="*80)

        # Print summary
        print("\n📈 ALL TEST RESULTS:")
        print(results_df.to_string())

        # Calculate averages
        print("\n📊 STRATEGY AVERAGES:")
        strategy_avg = results_df.groupby('Strategy')[['Return_%', 'Sharpe', 'Trades', 'Win_Rate_%']].mean().round(2)
        print(strategy_avg)

        # Best performers
        print("\n🏆 TOP PERFORMERS BY RETURN:")
        top_return = results_df.nlargest(3, 'Return_%')[['Strategy', 'Dataset', 'Return_%', 'Trades']]
        print(top_return.to_string())

        print("\n🎯 TOP PERFORMERS BY SHARPE:")
        top_sharpe = results_df.nlargest(3, 'Sharpe')[['Strategy', 'Dataset', 'Sharpe', 'Return_%']]
        print(top_sharpe.to_string())

        print(f"\n✅ Results saved to: {csv_file}")

        # Also save the stats to a text file
        txt_file = f"{results_dir}/smart_money_test_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(txt_file, 'w') as f:
            f.write("SMART MONEY BREAKOUT TESTING RESULTS\n")
            f.write("="*80 + "\n\n")
            f.write("ALL RESULTS:\n")
            f.write(results_df.to_string())
            f.write("\n\n")
            f.write("STRATEGY AVERAGES:\n")
            f.write(strategy_avg.to_string())
            f.write("\n\n")
            f.write("TOP PERFORMERS BY RETURN:\n")
            f.write(top_return.to_string())
            f.write("\n\n")
            f.write("TOP PERFORMERS BY SHARPE:\n")
            f.write(top_sharpe.to_string())

        print(f"📄 Stats saved to: {txt_file}")

    else:
        print("\n❌ No successful tests to save")

    print("\n" + "="*80)
    print("✅ TESTING COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()