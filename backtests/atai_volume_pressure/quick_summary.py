#!/usr/bin/env python3
"""
Quick summary test on select data sources for ATAI Volume Pressure strategies
"""

import pandas as pd
import numpy as np
import sys
import os
from backtesting import Backtest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import strategies
from atai_volume_pressure_base import ATAIVolumePressureBase
from atai_volume_pressure_mfi import ATAIVolumePressureMFI
from atai_volume_pressure_adx import ATAIVolumePressureADX
from atai_volume_pressure_kalman import ATAIVolumePressureKalman

def load_and_test(data_file, strategy_class, strategy_name):
    """Load data and run backtest"""
    try:
        # Load data
        data = pd.read_csv(data_file, index_col=0, parse_dates=True)

        # Handle column names
        if 'open' in data.columns:
            data = data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low',
                                       'close': 'Close', 'volume': 'Volume'})

        # Run backtest
        bt = Backtest(data, strategy_class, cash=10000, commission=0.002)
        stats = bt.run()

        return {
            'Return_%': stats['Return [%]'],
            'Sharpe': stats['Sharpe Ratio'],
            'Max_DD_%': stats['Max. Drawdown [%]'],
            'Win_Rate_%': stats['Win Rate [%]'],
            'Trades': stats['# Trades']
        }
    except Exception as e:
        print(f"Error testing {data_file}: {e}")
        return None

def main():
    # Select key data sources for testing
    test_data = [
        ("/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-1000wks-data.csv", "BTC-1d"),
        ("/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv", "BTC-1h"),
        ("/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1d-1000wks-data.csv", "ETH-1d"),
        ("/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1d-1000wks-data.csv", "SOL-1d"),
        ("/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/yahoo_daily/AAPL_stock_1d.csv", "AAPL-1d"),
        ("/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/yahoo_daily/TSLA_stock_1d.csv", "TSLA-1d"),
        ("/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/yahoo_daily/NVDA_stock_1d.csv", "NVDA-1d")
    ]

    strategies = [
        (ATAIVolumePressureBase, 'Base'),
        (ATAIVolumePressureMFI, 'MFI'),
        (ATAIVolumePressureADX, 'ADX'),
        (ATAIVolumePressureKalman, 'Kalman')
    ]

    # Collect results
    results_table = []

    print("\n" + "="*100)
    print("ATAI VOLUME PRESSURE STRATEGIES - COMPREHENSIVE TEST RESULTS")
    print("="*100)

    for data_file, data_name in test_data:
        if not os.path.exists(data_file):
            print(f"Skipping {data_name} - file not found")
            continue

        print(f"\nTesting on {data_name}...")
        row_data = {'Dataset': data_name}

        for strategy_class, strategy_name in strategies:
            result = load_and_test(data_file, strategy_class, strategy_name)
            if result:
                row_data[f'{strategy_name}_Return'] = result['Return_%']
                row_data[f'{strategy_name}_Sharpe'] = result['Sharpe']
                row_data[f'{strategy_name}_WinRate'] = result['Win_Rate_%']
                row_data[f'{strategy_name}_Trades'] = result['Trades']

        results_table.append(row_data)

    # Create DataFrame
    df = pd.DataFrame(results_table)

    # Print results by strategy
    print("\n" + "="*100)
    print("RESULTS BY STRATEGY")
    print("="*100)

    for _, strategy_name in strategies:
        print(f"\n📊 {strategy_name} Strategy Results:")
        print("-"*50)

        return_col = f'{strategy_name}_Return'
        sharpe_col = f'{strategy_name}_Sharpe'
        win_col = f'{strategy_name}_WinRate'
        trades_col = f'{strategy_name}_Trades'

        if return_col in df.columns:
            print(f"{'Dataset':<15} {'Return%':<12} {'Sharpe':<10} {'Win%':<10} {'Trades':<10}")
            print("-"*50)

            for _, row in df.iterrows():
                dataset = row['Dataset']
                ret = row.get(return_col, np.nan)
                sharpe = row.get(sharpe_col, np.nan)
                win = row.get(win_col, np.nan)
                trades = row.get(trades_col, np.nan)

                print(f"{dataset:<15} {ret:>11.2f} {sharpe:>9.3f} {win:>9.2f} {trades:>9.0f}")

            # Summary stats
            avg_return = df[return_col].mean()
            avg_sharpe = df[sharpe_col].mean()
            avg_win = df[win_col].mean()
            total_trades = df[trades_col].sum()

            print("-"*50)
            print(f"{'AVERAGE':<15} {avg_return:>11.2f} {avg_sharpe:>9.3f} {avg_win:>9.2f} {total_trades:>9.0f}")

    # Overall comparison
    print("\n" + "="*100)
    print("STRATEGY COMPARISON SUMMARY")
    print("="*100)
    print(f"\n{'Strategy':<15} {'Avg Return%':<15} {'Avg Sharpe':<15} {'Avg Win%':<15} {'Total Trades':<15}")
    print("-"*75)

    for _, strategy_name in strategies:
        return_col = f'{strategy_name}_Return'
        sharpe_col = f'{strategy_name}_Sharpe'
        win_col = f'{strategy_name}_WinRate'
        trades_col = f'{strategy_name}_Trades'

        if return_col in df.columns:
            avg_return = df[return_col].mean()
            avg_sharpe = df[sharpe_col].mean()
            avg_win = df[win_col].mean()
            total_trades = df[trades_col].sum()

            print(f"{strategy_name:<15} {avg_return:>14.2f} {avg_sharpe:>14.3f} {avg_win:>14.2f} {total_trades:>14.0f}")

    # Best performer per metric
    print("\n" + "="*100)
    print("BEST PERFORMERS")
    print("="*100)

    # Find best return
    best_return = -float('inf')
    best_return_strategy = ""
    best_return_dataset = ""

    for _, strategy_name in strategies:
        return_col = f'{strategy_name}_Return'
        if return_col in df.columns:
            max_idx = df[return_col].idxmax()
            if df.loc[max_idx, return_col] > best_return:
                best_return = df.loc[max_idx, return_col]
                best_return_strategy = strategy_name
                best_return_dataset = df.loc[max_idx, 'Dataset']

    print(f"🏆 Best Return: {best_return_strategy} on {best_return_dataset} = {best_return:.2f}%")

    # Save results
    results_file = 'results/ATAI_Summary.csv'
    os.makedirs('results', exist_ok=True)
    df.to_csv(results_file, index=False)
    print(f"\n💾 Results saved to {results_file}")

    return df

if __name__ == "__main__":
    results = main()