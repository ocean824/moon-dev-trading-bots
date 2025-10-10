#!/usr/bin/env python3
"""
Test all FIXED ATR Rope strategies
Dr. Data Dawg's ATR Rope Testing Suite 🌙
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
from backtesting import Backtest
import warnings
warnings.filterwarnings('ignore')

# Import fixed strategies
from atr_rope_base_fixed import ATRRopeBase
from atr_rope_rsi_fixed import ATRRopeRSI

# Test data sources (using a subset for faster testing)
DATA_SOURCES = [
    ('BTC-1h-500wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'),
    ('BTC-15m-150wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-15m-150wks-data.csv'),
    ('BTC-6h-500wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-6h-500wks-data.csv'),
    ('BTC-1d-100wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-100wks-data.csv'),
    ('ETH-1h-250wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1h-250wks-data.csv'),
    ('ETH-6h-400wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-6h-400wks-data.csv'),
    ('SOL-1h-250wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1h-250wks-data.csv'),
    ('SOL-6h-400wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-6h-400wks-data.csv'),
]

# Strategies to test
STRATEGIES = {
    'ATRRope_Base': ATRRopeBase,
    'ATRRope_RSI': ATRRopeRSI,
}

def load_data(filepath, limit_rows=20000):
    """Load and prepare data for backtesting"""
    try:
        df = pd.read_csv(filepath)

        # Handle datetime column
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime')
        elif 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date')

        # Standardize column names
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

        # Sort and clean
        df = df.sort_index()
        df = df.dropna()

        # Limit rows for faster testing
        if limit_rows and len(df) > limit_rows:
            df = df.tail(limit_rows)

        return df
    except Exception as e:
        print(f"❌ Error loading {filepath}: {e}")
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
            'Sharpe': round(stats['Sharpe Ratio'], 3) if not pd.isna(stats['Sharpe Ratio']) else 0,
            'Max_DD_%': round(stats['Max. Drawdown [%]'], 2),
            'Win_Rate_%': round(stats.get('Win Rate [%]', 0), 1) if not pd.isna(stats.get('Win Rate [%]', 0)) else 0,
            'Trades': stats['# Trades'],
            'Avg_Trade_%': round(stats.get('Avg. Trade [%]', 0), 3) if not pd.isna(stats.get('Avg. Trade [%]', 0)) else 0,
            'Exposure_%': round(stats['Exposure Time [%]'], 1),
        }

        return result

    except Exception as e:
        print(f"❌ Error testing {strategy_name} on {data_name}: {str(e)[:100]}")
        return None

def main():
    print("\n" + "="*80)
    print("🌙 DR. DATA DAWG'S ATR ROPE - FIXED STRATEGIES TEST 🌙")
    print("="*80)
    print(f"Testing {len(STRATEGIES)} fixed strategies on {len(DATA_SOURCES)} datasets")
    print("="*80)

    # Results storage
    all_results = []

    # Results directory
    results_dir = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/atr_rope/results"
    os.makedirs(results_dir, exist_ok=True)

    # Test each strategy on each dataset
    for strategy_name, strategy_class in STRATEGIES.items():
        print(f"\n{'='*60}")
        print(f"Testing {strategy_name}")
        print('-'*60)

        for data_name, data_path in DATA_SOURCES:
            print(f"  {data_name}...", end=" ")

            # Load data
            df = load_data(data_path)
            if df is None:
                print("❌ Failed to load")
                continue

            # Test strategy
            result = test_strategy(strategy_class, strategy_name, data_name, df)

            if result:
                all_results.append(result)
                if result['Trades'] > 0:
                    print(f"✅ Return: {result['Return_%']}%, Trades: {result['Trades']}, Exposure: {result['Exposure_%']}%")
                else:
                    print(f"⚠️  No trades generated")
            else:
                print("❌ Test failed")

    # Save and display results
    if all_results:
        results_df = pd.DataFrame(all_results)

        # Save to CSV with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f"{results_dir}/atr_rope_fixed_results_{timestamp}.csv"
        results_df.to_csv(csv_file, index=False)

        print("\n" + "="*80)
        print("📊 RESULTS SUMMARY")
        print("="*80)

        # Show strategies with trades
        strategies_with_trades = results_df[results_df['Trades'] > 0]

        if len(strategies_with_trades) > 0:
            print(f"\n✅ STRATEGIES GENERATING TRADES: {len(strategies_with_trades)} / {len(all_results)}")
            print("\n📈 SUCCESSFUL RESULTS:")
            print(strategies_with_trades[['Strategy', 'Dataset', 'Return_%', 'Trades', 'Exposure_%', 'Win_Rate_%']].to_string())

            # Strategy averages (only for strategies with trades)
            print("\n📊 STRATEGY AVERAGES (with trades):")
            strategy_avg = strategies_with_trades.groupby('Strategy')[['Return_%', 'Sharpe', 'Trades', 'Exposure_%']].mean().round(2)
            print(strategy_avg)

            # Best performers
            print("\n🏆 TOP PERFORMERS BY RETURN:")
            top_return = strategies_with_trades.nlargest(5, 'Return_%')[['Strategy', 'Dataset', 'Return_%', 'Trades', 'Exposure_%']]
            print(top_return.to_string())

        else:
            print("\n⚠️  WARNING: No strategies generated trades!")

        # Show strategies without trades
        no_trades = results_df[results_df['Trades'] == 0]
        if len(no_trades) > 0:
            print(f"\n⚠️  STRATEGIES WITHOUT TRADES: {len(no_trades)}")
            print(no_trades[['Strategy', 'Dataset']].to_string())

        print(f"\n✅ Results saved to: {csv_file}")

        # Save detailed stats
        txt_file = f"{results_dir}/atr_rope_fixed_stats_{timestamp}.txt"
        with open(txt_file, 'w') as f:
            f.write("ATR ROPE - FIXED STRATEGIES TEST RESULTS\n")
            f.write("="*80 + "\n\n")
            f.write(f"Test Date: {datetime.now()}\n")
            f.write(f"Total Tests: {len(all_results)}\n")
            if len(strategies_with_trades) > 0:
                f.write(f"Successful (with trades): {len(strategies_with_trades)}\n")
            f.write(f"Failed (no trades): {len(no_trades)}\n\n")
            f.write("FULL RESULTS:\n")
            f.write(results_df.to_string())
            if len(strategies_with_trades) > 0:
                f.write("\n\nSTRATEGY AVERAGES (with trades):\n")
                f.write(strategy_avg.to_string())

        print(f"📄 Stats saved to: {txt_file}")

    else:
        print("\n❌ No successful tests to save")

    print("\n" + "="*80)
    print("✅ ATR ROPE FIXED STRATEGIES TESTING COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()