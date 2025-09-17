"""
Test all Angled Volume Profile strategies on 25+ data sources
Runs all four AVP variations across multiple assets and timeframes
"""

import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime
from backtesting import Backtest

# Import all strategies
from avp_base import AVPBaseStrategy
from avp_vwap import AVPVWAPStrategy
from avp_mfi import AVPMFIStrategy
from avp_adx import AVPADXStrategy


def load_data(symbol, data_source='crypto'):
    """Load data for a specific symbol"""
    try:
        if data_source == 'crypto_15m':
            # Try different file naming patterns for crypto 15m data
            paths = [
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}USD-15m-150wks-data.csv',
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}USD-15m-100wks-data.csv',
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}-15m-150wks-data.csv'
            ]
            for path in paths:
                if pd.io.common.file_exists(path):
                    data = pd.read_csv(path, parse_dates=['datetime'], index_col='datetime')
                    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    return data
        elif data_source == 'crypto_1h':
            paths = [
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}USD-1h-250wks-data.csv',
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}USD-1h-500wks-data.csv',
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}USD-1h-100wks-data.csv'
            ]
            for path in paths:
                if pd.io.common.file_exists(path):
                    data = pd.read_csv(path, parse_dates=['datetime'], index_col='datetime')
                    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    return data
        elif data_source == 'crypto_1d':
            paths = [
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}USD-1d-1000wks-data.csv',
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}USD-1d-100wks-data.csv'
            ]
            for path in paths:
                if pd.io.common.file_exists(path):
                    data = pd.read_csv(path, parse_dates=['datetime'], index_col='datetime')
                    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    return data
        elif data_source == 'yahoo_daily':
            path = f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/yahoo_daily/{symbol}_stock_1d.csv'
            if pd.io.common.file_exists(path):
                data = pd.read_csv(path, parse_dates=['Date'], index_col='Date')
                # Keep only OHLCV columns
                data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
                return data
        elif data_source == 'yahoo_hourly':
            path = f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/yahoo_hourly/{symbol}_hourly.csv'
            if pd.io.common.file_exists(path):
                data = pd.read_csv(path, parse_dates=['Datetime'], index_col='Datetime')
                # Drop Adj Close if it exists
                if 'Adj Close' in data.columns:
                    data = data.drop('Adj Close', axis=1)
                data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                return data
        elif data_source == 'ib_data':
            # Interactive Brokers data
            pattern = f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/IB_data/{symbol}_*.csv'
            files = glob.glob(pattern)
            if files:
                # Use the first matching file
                data = pd.read_csv(files[0], parse_dates=['date'], index_col='date')
                data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                return data

        return None
    except Exception as e:
        print(f"Error loading {symbol} from {data_source}: {e}")
        return None


def run_single_backtest(symbol, data, strategy_class, cash=100000):
    """Run backtest for a single symbol with a given strategy"""
    try:
        # Sort and clean data
        data = data.sort_index()
        data = data.dropna()

        # Skip if not enough data
        if len(data) < 200:
            return None

        # Initialize and run backtest
        bt = Backtest(
            data,
            strategy_class,
            cash=cash,
            commission=0.002,
            exclusive_orders=True
        )

        # Run the backtest
        stats = bt.run()

        return stats
    except Exception as e:
        print(f"Error running backtest for {symbol}: {e}")
        return None


def run_all_strategies_multi_data():
    """Run all AVP strategies on multiple data sources"""

    print("\n" + "="*100)
    print("ANGLED VOLUME PROFILE STRATEGIES - COMPREHENSIVE MULTI-DATA TEST")
    print("="*100)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*100)

    # Define all data sources
    data_sources = [
        # Crypto pairs (multiple timeframes)
        ('BTC', 'crypto_15m'),
        ('ETH', 'crypto_15m'),
        ('SOL', 'crypto_15m'),
        ('BTC', 'crypto_1h'),
        ('ETH', 'crypto_1h'),
        ('SOL', 'crypto_1h'),
        ('BTC', 'crypto_1d'),
        ('ETH', 'crypto_1d'),
        ('SOL', 'crypto_1d'),

        # Stock indices and major stocks (Yahoo)
        ('AAPL', 'yahoo_daily'),
        ('GOOGL', 'yahoo_daily'),
        ('MSFT', 'yahoo_daily'),
        ('AMZN', 'yahoo_daily'),

        # Yahoo hourly data
        ('AAPL', 'yahoo_hourly'),
        ('GOOG', 'yahoo_hourly'),
        ('NVDA', 'yahoo_hourly'),
        ('TSLA', 'yahoo_hourly'),

        # Interactive Brokers data
        ('AAPL', 'ib_data'),
        ('TSLA', 'ib_data'),
        ('ES', 'ib_data'),
        ('NQ', 'ib_data'),
    ]

    # Add additional Yahoo symbols
    additional_yahoo = ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'GLD', 'SLV', 'USO']
    for symbol in additional_yahoo:
        data_sources.append((symbol, 'yahoo_daily'))

    # Define strategies to test
    strategies = [
        ("AVP Base", AVPBaseStrategy),
        ("AVP + VWAP", AVPVWAPStrategy),
        ("AVP + MFI", AVPMFIStrategy),
        ("AVP + ADX", AVPADXStrategy)
    ]

    # Master results collection
    all_results = []

    # Test each strategy on all data sources
    for strategy_name, strategy_class in strategies:
        print(f"\n{'='*80}")
        print(f"Testing Strategy: {strategy_name}")
        print('='*80)

        strategy_results = []
        successful_tests = 0

        for i, (symbol, source) in enumerate(data_sources, 1):
            print(f"[{i}/{len(data_sources)}] {symbol} ({source})...", end=' ')

            # Load data
            data = load_data(symbol, source)

            if data is None:
                print("❌ No data")
                continue

            # Adjust cash based on asset type
            if symbol in ['BTC', 'ETH']:
                cash = 1000000
            else:
                cash = 100000

            # Run backtest
            stats = run_single_backtest(symbol, data, strategy_class, cash)

            if stats is not None:
                successful_tests += 1
                result = {
                    'Strategy': strategy_name,
                    'Symbol': symbol,
                    'Source': source,
                    'Data_Points': len(data),
                    'Return_%': round(stats.get('Return [%]', 0), 2),
                    'Sharpe': round(stats.get('Sharpe Ratio', 0), 3) if pd.notna(stats.get('Sharpe Ratio')) else 0,
                    'Max_DD_%': round(stats.get('Max. Drawdown [%]', 0), 2),
                    'Win_Rate_%': round(stats.get('Win Rate [%]', 0), 2) if pd.notna(stats.get('Win Rate [%]')) else 0,
                    'Num_Trades': stats.get('# Trades', 0),
                    'Profit_Factor': round(stats.get('Profit Factor', 0), 3) if pd.notna(stats.get('Profit Factor')) else 0,
                    'Avg_Trade_%': round(stats.get('Avg. Trade [%]', 0), 3) if pd.notna(stats.get('Avg. Trade [%]')) else 0,
                    'Buy_Hold_%': round(stats.get('Buy & Hold Return [%]', 0), 2)
                }
                strategy_results.append(result)
                all_results.append(result)

                # Print summary
                print(f"✅ Return: {result['Return_%']:.1f}%, Sharpe: {result['Sharpe']:.2f}")
            else:
                print("❌ Failed")

        # Strategy summary
        if strategy_results:
            strategy_df = pd.DataFrame(strategy_results)
            print(f"\n{strategy_name} Summary:")
            print(f"  Successful tests: {successful_tests}/{len(data_sources)}")
            print(f"  Average Return: {strategy_df['Return_%'].mean():.2f}%")
            print(f"  Average Sharpe: {strategy_df['Sharpe'].mean():.3f}")
            print(f"  Average Win Rate: {strategy_df['Win_Rate_%'].mean():.2f}%")
            print(f"  Total Trades: {strategy_df['Num_Trades'].sum()}")

    # Save all results
    if all_results:
        results_df = pd.DataFrame(all_results)

        # Save to CSV
        os.makedirs('results', exist_ok=True)
        csv_path = 'results/all_strategies_multi_data_results.csv'
        results_df.to_csv(csv_path, index=False)

        print("\n" + "="*100)
        print("OVERALL SUMMARY STATISTICS")
        print("="*100)

        # Strategy comparison
        print("\nSTRATEGY COMPARISON:")
        print("-"*80)
        strategy_summary = results_df.groupby('Strategy').agg({
            'Return_%': ['mean', 'std', 'min', 'max'],
            'Sharpe': ['mean', 'std'],
            'Win_Rate_%': 'mean',
            'Num_Trades': 'mean',
            'Max_DD_%': 'mean'
        }).round(2)
        print(strategy_summary.to_string())

        # Best performers by strategy
        print("\n" + "-"*80)
        print("BEST PERFORMER FOR EACH STRATEGY:")
        print("-"*80)
        for strategy in results_df['Strategy'].unique():
            strategy_data = results_df[results_df['Strategy'] == strategy]
            if len(strategy_data) > 0:
                best = strategy_data.nlargest(1, 'Return_%').iloc[0]
                print(f"{strategy:20s}: {best['Symbol']:10s} ({best['Source']:15s}) - Return: {best['Return_%']:>8.2f}%, Sharpe: {best['Sharpe']:>6.3f}")

        # Asset performance across all strategies
        print("\n" + "-"*80)
        print("ASSET PERFORMANCE (AVERAGED ACROSS ALL STRATEGIES):")
        print("-"*80)
        asset_summary = results_df.groupby('Symbol').agg({
            'Return_%': 'mean',
            'Sharpe': 'mean',
            'Win_Rate_%': 'mean',
            'Num_Trades': 'sum'
        }).round(2).nlargest(10, 'Return_%')
        print(asset_summary.to_string())

        # Data source performance
        print("\n" + "-"*80)
        print("PERFORMANCE BY DATA SOURCE TYPE:")
        print("-"*80)
        source_summary = results_df.groupby('Source').agg({
            'Return_%': 'mean',
            'Sharpe': 'mean',
            'Win_Rate_%': 'mean',
            'Num_Trades': 'mean'
        }).round(2)
        print(source_summary.to_string())

        # Top 10 overall results
        print("\n" + "-"*80)
        print("TOP 10 OVERALL RESULTS:")
        print("-"*80)
        top10 = results_df.nlargest(10, 'Return_%')[['Strategy', 'Symbol', 'Source', 'Return_%', 'Sharpe', 'Win_Rate_%', 'Num_Trades']]
        print(top10.to_string(index=False))

        # Risk-adjusted performance
        print("\n" + "-"*80)
        print("TOP 10 BY SHARPE RATIO:")
        print("-"*80)
        top10_sharpe = results_df.nlargest(10, 'Sharpe')[['Strategy', 'Symbol', 'Source', 'Sharpe', 'Return_%', 'Max_DD_%']]
        print(top10_sharpe.to_string(index=False))

        # Final recommendations
        print("\n" + "="*100)
        print("ANALYSIS & RECOMMENDATIONS:")
        print("="*100)

        # Find best overall combination
        best_overall = results_df.nlargest(1, 'Return_%').iloc[0]
        best_sharpe = results_df.nlargest(1, 'Sharpe').iloc[0]

        print(f"\nBest Overall Return:")
        print(f"  Strategy: {best_overall['Strategy']}")
        print(f"  Asset: {best_overall['Symbol']} ({best_overall['Source']})")
        print(f"  Return: {best_overall['Return_%']:.2f}%")
        print(f"  Sharpe: {best_overall['Sharpe']:.3f}")

        print(f"\nBest Risk-Adjusted (Sharpe):")
        print(f"  Strategy: {best_sharpe['Strategy']}")
        print(f"  Asset: {best_sharpe['Symbol']} ({best_sharpe['Source']})")
        print(f"  Sharpe: {best_sharpe['Sharpe']:.3f}")
        print(f"  Return: {best_sharpe['Return_%']:.2f}%")

        # Strategy ranking
        strategy_scores = []
        for strategy in results_df['Strategy'].unique():
            strategy_data = results_df[results_df['Strategy'] == strategy]
            # Composite score: 40% avg return, 30% avg sharpe, 20% consistency (low std), 10% win rate
            avg_return = strategy_data['Return_%'].mean()
            avg_sharpe = strategy_data['Sharpe'].mean()
            return_std = strategy_data['Return_%'].std()
            avg_win_rate = strategy_data['Win_Rate_%'].mean()

            score = (avg_return * 0.4 +
                    avg_sharpe * 30 * 0.3 +
                    (100 - return_std) * 0.2 +
                    avg_win_rate * 0.1)

            strategy_scores.append((strategy, score, avg_return, avg_sharpe, return_std))

        strategy_scores.sort(key=lambda x: x[1], reverse=True)

        print("\nSTRATEGY RANKING (Composite Score):")
        print("-"*60)
        for i, (strategy, score, ret, sharpe, std) in enumerate(strategy_scores, 1):
            print(f"{i}. {strategy:20s} - Score: {score:>7.2f} (Return: {ret:>6.2f}%, Sharpe: {sharpe:>5.3f}, StdDev: {std:>6.2f})")

        print("\n" + "="*100)
        print(f"Results saved to: {os.path.abspath(csv_path)}")
        print(f"Total tests completed: {len(all_results)}")
        print("="*100)

        return results_df
    else:
        print("\n❌ No successful backtests completed")
        return None


if __name__ == "__main__":
    results = run_all_strategies_multi_data()

    if results is not None and len(results) > 0:
        print("\n" + "="*100)
        print("ALL AVP STRATEGIES - MULTI-DATA TEST COMPLETE")
        print(f"Successfully tested {len(results['Strategy'].unique())} strategies on {len(results['Symbol'].unique())} unique assets")
        print("="*100)