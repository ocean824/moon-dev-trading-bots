"""
Multi-Data Testing for Smart Money Breakout Strategies
Tests all Smart Money variations across multiple datasets
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
from backtesting import Backtest
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all strategy variations
from smart_money_base import SmartMoneyBreakoutBase
from smart_money_volume import SmartMoneyBreakoutVolume
from smart_money_rsi import SmartMoneyBreakoutRSI
from smart_money_macd import SmartMoneyBreakoutMACD

# Data paths configuration
BASE_DATA_PATH = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data"

# Define data sources as specified in MULTI_DATA_TESTING.md
DATA_SOURCES = {
    'Coinbase_BTC_Daily': 'BTC-USD_daily.csv',
    'Coinbase_BTC_Hourly': 'BTC-USD_hourly.csv',
    'Coinbase_ETH_Daily': 'ETH-USD_daily.csv',
    'Coinbase_ETH_Hourly': 'ETH-USD_hourly.csv',
    'Coinbase_SOL_Daily': 'SOL-USD_daily.csv',
    'Coinbase_SOL_Hourly': 'SOL-USD_hourly.csv',
    'Yahoo_SPY_Daily': 'SPY_daily.csv',
    'Yahoo_SPY_Hourly': 'SPY_hourly.csv',
    'Yahoo_QQQ_Daily': 'QQQ_daily.csv',
    'Yahoo_QQQ_Hourly': 'QQQ_hourly.csv',
    'Yahoo_AAPL_Daily': 'AAPL_daily.csv',
    'Yahoo_AAPL_Hourly': 'AAPL_hourly.csv',
    'Yahoo_MSFT_Daily': 'MSFT_daily.csv',
    'Yahoo_MSFT_Hourly': 'MSFT_hourly.csv',
    'Yahoo_TSLA_Daily': 'TSLA_daily.csv',
    'Yahoo_TSLA_Hourly': 'TSLA_hourly.csv',
    'Hyperliquid_BTC_1H': 'hyperliquid_BTC_1h.csv',
    'Hyperliquid_ETH_1H': 'hyperliquid_ETH_1h.csv',
    'Hyperliquid_SOL_1H': 'hyperliquid_SOL_1h.csv',
    'Hyperliquid_BTC_4H': 'hyperliquid_BTC_4h.csv',
    'Hyperliquid_ETH_4H': 'hyperliquid_ETH_4h.csv',
    'Hyperliquid_SOL_4H': 'hyperliquid_SOL_4h.csv',
    'Hyperliquid_BTC_1D': 'hyperliquid_BTC_1d.csv',
    'Hyperliquid_ETH_1D': 'hyperliquid_ETH_1d.csv',
    'Hyperliquid_SOL_1D': 'hyperliquid_SOL_1d.csv'
}

# Strategy configurations
STRATEGIES = {
    'Base': SmartMoneyBreakoutBase,
    'Volume_MFI': SmartMoneyBreakoutVolume,
    'RSI_ADX': SmartMoneyBreakoutRSI,
    'MACD_Kalman': SmartMoneyBreakoutMACD
}

def load_and_prepare_data(data_path):
    """Load and prepare data for backtesting"""
    try:
        # Check if file exists
        if not os.path.exists(data_path):
            return None

        # Load data
        df = pd.read_csv(data_path)

        # Handle different date column names
        date_columns = ['Date', 'date', 'datetime', 'timestamp']
        date_col = None
        for col in date_columns:
            if col in df.columns:
                date_col = col
                break

        if date_col is None:
            print(f"No date column found in {data_path}")
            return None

        # Parse dates and set as index
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)
        df.index.name = 'Date'

        # Standardize column names
        column_mapping = {
            'open': 'Open', 'Open': 'Open',
            'high': 'High', 'High': 'High',
            'low': 'Low', 'Low': 'Low',
            'close': 'Close', 'Close': 'Close',
            'volume': 'Volume', 'Volume': 'Volume'
        }

        df = df.rename(columns=column_mapping)

        # Ensure required columns exist
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_columns:
            if col not in df.columns:
                print(f"Missing column {col} in {data_path}")
                return None

        # Select only required columns
        df = df[required_columns]

        # Handle missing volume data
        if df['Volume'].isna().all() or (df['Volume'] == 0).all():
            # Generate synthetic volume based on price movement
            df['Volume'] = (abs(df['Close'] - df['Open']) * 1000000).fillna(100000)

        # Clean data
        df = df.dropna()

        # Ensure we have enough data
        if len(df) < 100:
            print(f"Insufficient data in {data_path} (only {len(df)} rows)")
            return None

        return df

    except Exception as e:
        print(f"Error loading {data_path}: {str(e)}")
        return None


def run_single_backtest(strategy_class, df, data_name, strategy_name, cash=1000000):
    """Run a single backtest"""
    try:
        bt = Backtest(df, strategy_class, cash=cash, commission=0.001)
        stats = bt.run()

        # Extract key metrics
        result = {
            'Strategy': strategy_name,
            'Dataset': data_name,
            'Return%': stats['Return [%]'],
            'Sharpe': stats['Sharpe Ratio'],
            'Max_Drawdown%': stats['Max. Drawdown [%]'],
            'Win_Rate%': stats['Win Rate [%]'] if 'Win Rate [%]' in stats else 0,
            'Trades': stats['# Trades'],
            'Avg_Trade%': stats['Avg. Trade [%]'] if 'Avg. Trade [%]' in stats else 0,
            'Exposure%': stats['Exposure Time [%]'],
            'Equity_Final': stats['Equity Final [$]'],
            'Equity_Peak': stats['Equity Peak [$]']
        }

        return result, stats

    except Exception as e:
        print(f"Error in backtest {strategy_name} on {data_name}: {str(e)}")
        return None, None


def main():
    """Run all Smart Money strategies on all datasets"""
    print("=" * 80)
    print("SMART MONEY BREAKOUT CHANNELS - MULTI-DATA TESTING")
    print("=" * 80)
    print(f"Testing {len(STRATEGIES)} strategies on {len(DATA_SOURCES)} datasets")
    print(f"Total backtests to run: {len(STRATEGIES) * len(DATA_SOURCES)}")
    print("=" * 80)

    # Results storage
    all_results = []
    failed_tests = []
    successful_tests = 0
    total_tests = 0

    # Test each strategy on each dataset
    for strategy_name, strategy_class in STRATEGIES.items():
        print(f"\n{'=' * 60}")
        print(f"Testing Strategy: {strategy_name}")
        print(f"{'=' * 60}")

        strategy_results = []

        for data_name, data_file in DATA_SOURCES.items():
            total_tests += 1
            data_path = os.path.join(BASE_DATA_PATH, data_file)

            print(f"\nTesting on {data_name}...", end=" ")

            # Load data
            df = load_and_prepare_data(data_path)
            if df is None:
                print(f"FAILED - Could not load data")
                failed_tests.append(f"{strategy_name} on {data_name}")
                continue

            # Run backtest
            result, stats = run_single_backtest(strategy_class, df, data_name, strategy_name)

            if result is not None:
                all_results.append(result)
                strategy_results.append(result)
                successful_tests += 1
                print(f"SUCCESS - Return: {result['Return%']:.2f}%, Sharpe: {result['Sharpe']:.2f}, Trades: {result['Trades']}")
            else:
                failed_tests.append(f"{strategy_name} on {data_name}")
                print(f"FAILED - Backtest error")

        # Print strategy summary
        if strategy_results:
            print(f"\n{strategy_name} Summary:")
            strategy_df = pd.DataFrame(strategy_results)
            print(f"  Average Return: {strategy_df['Return%'].mean():.2f}%")
            print(f"  Average Sharpe: {strategy_df['Sharpe'].mean():.2f}")
            print(f"  Average Win Rate: {strategy_df['Win_Rate%'].mean():.2f}%")
            print(f"  Total Trades: {strategy_df['Trades'].sum()}")

    # Save all results
    results_dir = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/smart_money_breakout/results"
    os.makedirs(results_dir, exist_ok=True)

    if all_results:
        # Create comprehensive results DataFrame
        results_df = pd.DataFrame(all_results)

        # Save detailed results
        results_df.to_csv(f"{results_dir}/smart_money_all_results.csv", index=False)
        print(f"\n{'=' * 80}")
        print(f"Results saved to {results_dir}/smart_money_all_results.csv")

        # Create and save summary by strategy
        strategy_summary = results_df.groupby('Strategy').agg({
            'Return%': ['mean', 'std', 'min', 'max'],
            'Sharpe': ['mean', 'std', 'min', 'max'],
            'Max_Drawdown%': ['mean', 'std', 'min', 'max'],
            'Win_Rate%': ['mean', 'std', 'min', 'max'],
            'Trades': ['sum', 'mean'],
            'Exposure%': 'mean'
        }).round(2)

        strategy_summary.to_csv(f"{results_dir}/smart_money_strategy_summary.csv")
        print(f"Strategy summary saved to {results_dir}/smart_money_strategy_summary.csv")

        # Create and save summary by dataset
        dataset_summary = results_df.groupby('Dataset').agg({
            'Return%': 'mean',
            'Sharpe': 'mean',
            'Max_Drawdown%': 'mean',
            'Win_Rate%': 'mean',
            'Trades': 'mean'
        }).round(2)

        dataset_summary.to_csv(f"{results_dir}/smart_money_dataset_summary.csv")
        print(f"Dataset summary saved to {results_dir}/smart_money_dataset_summary.csv")

        # Print overall summary
        print(f"\n{'=' * 80}")
        print("OVERALL SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total Backtests Run: {successful_tests}/{total_tests}")
        print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        print(f"\nBest Strategy by Average Return:")
        best_strat = strategy_summary['Return%']['mean'].idxmax()
        print(f"  {best_strat}: {strategy_summary.loc[best_strat, ('Return%', 'mean')]:.2f}%")

        print(f"\nBest Strategy by Average Sharpe:")
        best_sharpe = strategy_summary['Sharpe']['mean'].idxmax()
        print(f"  {best_sharpe}: {strategy_summary.loc[best_sharpe, ('Sharpe', 'mean')]:.2f}")

        print(f"\nBest Strategy by Win Rate:")
        best_wr = strategy_summary['Win_Rate%']['mean'].idxmax()
        print(f"  {best_wr}: {strategy_summary.loc[best_wr, ('Win_Rate%', 'mean')]:.2f}%")

        # Find best performing combinations
        print(f"\nTop 5 Best Performing Combinations:")
        top_5 = results_df.nlargest(5, 'Return%')[['Strategy', 'Dataset', 'Return%', 'Sharpe', 'Trades']]
        for idx, row in top_5.iterrows():
            print(f"  {row['Strategy']} on {row['Dataset']}: {row['Return%']:.2f}% (Sharpe: {row['Sharpe']:.2f})")

        print(f"\nTop 5 Highest Sharpe Combinations:")
        top_5_sharpe = results_df.nlargest(5, 'Sharpe')[['Strategy', 'Dataset', 'Sharpe', 'Return%', 'Trades']]
        for idx, row in top_5_sharpe.iterrows():
            print(f"  {row['Strategy']} on {row['Dataset']}: Sharpe {row['Sharpe']:.2f} (Return: {row['Return%']:.2f}%)")

    # Report failed tests
    if failed_tests:
        print(f"\n{'=' * 80}")
        print(f"FAILED TESTS ({len(failed_tests)})")
        print(f"{'=' * 80}")
        for failed in failed_tests:
            print(f"  - {failed}")

    print(f"\n{'=' * 80}")
    print("MULTI-DATA TESTING COMPLETE")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()