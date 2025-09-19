#!/usr/bin/env python3
"""
Multi-Data Testing for Smart Money Breakout Strategies
Tests all Smart Money variations across multiple datasets
Dr. Data Dawg's Smart Money Breakout Testing Suite 🌙
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
from smart_money_mfi import SmartMoneyMFI
from smart_money_adx import SmartMoneyADX
from smart_money_kalman import SmartMoneyKalman

# Standard DATA_SOURCES configuration
DATA_SOURCES = [
    # BITCOIN DATA - Multiple timeframes
    ('BTC-15m-150wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-15m-150wks-data.csv', 'coinbase'),
    ('BTC-1h-500wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv', 'coinbase'),
    ('BTC-5m-70wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-5m-70wks-data.csv', 'coinbase'),
    ('BTC-6h-500wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-6h-500wks-data.csv', 'coinbase'),
    ('BTC-6h-1000wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-6h-1000wks-data.csv', 'coinbase'),
    ('BTC-1d-1000wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-1000wks-data.csv', 'coinbase'),
    ('BTC-1d-100wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1d-100wks-data.csv', 'coinbase'),
    ('BTC-1m-10wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1m-10wks-data.csv', 'coinbase'),

    # ETHEREUM DATA
    ('ETH-15m-150wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-15m-150wks-data.csv', 'coinbase'),
    ('ETH-1h-250wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1h-250wks-data.csv', 'coinbase'),
    ('ETH-6h-400wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-6h-400wks-data.csv', 'coinbase'),
    ('ETH-1d-1000wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/ETHUSD-1d-1000wks-data.csv', 'coinbase'),

    # SOLANA DATA
    ('SOL-1m-8wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1m-8wks-data.csv', 'coinbase'),
    ('SOL-15m-100wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-15m-100wks-data.csv', 'coinbase'),
    ('SOL-1h-250wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1h-250wks-data.csv', 'coinbase'),
    ('SOL-6h-400wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-6h-400wks-data.csv', 'coinbase'),
    ('SOL-1d-1000wks', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/SOLUSD-1d-1000wks-data.csv', 'coinbase'),

    # INTERACTIVE BROKERS DATA - Stocks & Futures
    ('AAPL-15m-12Y', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/IB_data/AAPL_12Y_15mins_20250219_101840.csv', 'ib'),
    ('AAPL-15m-3Y', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/IB_data/AAPL_3Y_15mins_20250219_101100.csv', 'ib'),
    ('TSLA-5m-30D', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/IB_data/TSLA_30D_5mins_20250219_095254.csv', 'ib'),
    ('ES-4h-10Y', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/IB_data/ES_10Y_4hours_20250222_081224.csv', 'ib'),
    ('NQ-4h-10Y', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/IB_data/NQ_10Y_4hours_20250222_081325.csv', 'ib'),

    # YAHOO HOURLY DATA
    ('GOOG-hourly', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/yahoo_hourly/GOOG_hourly.csv', 'yahoo'),
    ('NVDA-hourly', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/yahoo_hourly/NVDA_hourly.csv', 'yahoo'),
    ('TSLA-hourly', '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/yahoo_hourly/TSLA_hourly.csv', 'yahoo'),
]

# Strategy configurations
STRATEGIES = {
    'SmartMoney_Base': SmartMoneyBreakoutBase,
    'SmartMoney_Volume': SmartMoneyBreakoutVolume,
    'SmartMoney_RSI': SmartMoneyBreakoutRSI,
    'SmartMoney_MACD': SmartMoneyBreakoutMACD,
    'SmartMoney_MFI': SmartMoneyMFI,
    'SmartMoney_ADX': SmartMoneyADX,
    'SmartMoney_Kalman': SmartMoneyKalman,
}

def load_data_universal(path, data_type):
    """
    Load data from different sources with different formats

    Args:
        path: Path to CSV file
        data_type: 'coinbase', 'ib', or 'yahoo'

    Returns:
        DataFrame with standardized columns: Open, High, Low, Close, Volume
    """
    try:
        if not os.path.exists(path):
            print(f"❌ File not found: {path}")
            return None

        if data_type == 'coinbase':
            # Standard format: datetime,open,high,low,close,volume
            data = pd.read_csv(path, parse_dates=['datetime'], index_col='datetime')
            data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

        elif data_type == 'ib':
            # IB format: date,open,high,low,close,volume
            data = pd.read_csv(path, parse_dates=['date'], index_col='date')
            data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

        elif data_type == 'yahoo':
            # Yahoo format: Datetime,Open,High,Low,Close,Adj Close,Volume
            data = pd.read_csv(path, parse_dates=['Datetime'], index_col='Datetime')
            # Drop Adj Close and keep standard columns
            data = data[['Open', 'High', 'Low', 'Close', 'Volume']]

        else:
            # Default fallback - try standard format
            data = pd.read_csv(path)
            if 'datetime' in data.columns:
                data = pd.read_csv(path, parse_dates=['datetime'], index_col='datetime')
            elif 'date' in data.columns:
                data = pd.read_csv(path, parse_dates=['date'], index_col='date')
            elif 'Datetime' in data.columns:
                data = pd.read_csv(path, parse_dates=['Datetime'], index_col='Datetime')
            else:
                data.index = pd.to_datetime(data.index)

            # Standardize column names
            col_mapping = {
                'open': 'Open', 'high': 'High', 'low': 'Low',
                'close': 'Close', 'volume': 'Volume'
            }
            data.rename(columns=col_mapping, inplace=True)

        # Ensure data is sorted
        data = data.sort_index()

        # Handle any missing values
        data = data.dropna()

        # Check minimum data requirement
        if len(data) < 100:
            print(f"⚠️ Insufficient data: {len(data)} rows")
            return None

        return data

    except Exception as e:
        print(f"❌ Error loading data from {path}: {e}")
        return None

def run_single_backtest(strategy_class, df, data_name, strategy_name, cash=1000000):
    """Run a single backtest"""
    try:
        bt = Backtest(df, strategy_class, cash=cash, commission=0.002)
        stats = bt.run()

        # Extract key metrics
        result = {
            'Strategy': strategy_name,
            'Dataset': data_name,
            'Return%': round(stats['Return [%]'], 2),
            'Buy_Hold%': round(stats['Buy & Hold Return [%]'], 2),
            'Sharpe': round(stats['Sharpe Ratio'], 3),
            'Sortino': round(stats['Sortino Ratio'], 3),
            'Max_DD%': round(stats['Max. Drawdown [%]'], 2),
            'Win_Rate%': round(stats.get('Win Rate [%]', 0), 1),
            'Trades': stats['# Trades'],
            'Avg_Trade%': round(stats.get('Avg. Trade [%]', 0), 3),
            'Profit_Factor': round(stats.get('Profit Factor', 0), 3),
            'Exposure%': round(stats['Exposure Time [%]'], 1),
        }

        return result

    except Exception as e:
        print(f"❌ Error in backtest: {str(e)[:100]}")
        return None

def main():
    """Run all Smart Money strategies on all datasets"""
    print("\n" + "="*80)
    print("🌙 DR. DATA DAWG'S SMART MONEY BREAKOUT TESTING SUITE 🌙")
    print("="*80)
    print(f"Testing {len(STRATEGIES)} strategies on {len(DATA_SOURCES)} datasets")
    print(f"Total backtests to run: {len(STRATEGIES) * len(DATA_SOURCES)}")
    print("="*80)

    # Results storage
    all_results = []
    successful_tests = 0
    failed_tests = 0

    # CSV file for results
    results_dir = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/smart_money_breakout/results"
    os.makedirs(results_dir, exist_ok=True)
    results_file = f"{results_dir}/smart_money_multi_data_results.csv"

    # Test each strategy on each dataset
    for strategy_name, strategy_class in STRATEGIES.items():
        print(f"\n{'='*60}")
        print(f"Testing Strategy: {strategy_name}")
        print(f"{'='*60}")

        for data_name, data_path, data_type in DATA_SOURCES:
            print(f"\n📊 Testing {strategy_name} on {data_name}...", end=" ")

            # Load data
            df = load_data_universal(data_path, data_type)
            if df is None:
                failed_tests += 1
                continue

            # Run backtest
            result = run_single_backtest(strategy_class, df, data_name, strategy_name)

            if result is not None:
                all_results.append(result)
                successful_tests += 1
                print(f"✅ Return: {result['Return%']}%, Sharpe: {result['Sharpe']}")
            else:
                failed_tests += 1

    # Save all results
    if all_results:
        results_df = pd.DataFrame(all_results)
        results_df.to_csv(results_file, index=False)
        print(f"\n{'='*80}")
        print(f"✅ Results saved to {results_file}")

        # Print summary statistics
        print(f"\n{'='*80}")
        print("📈 OVERALL SUMMARY")
        print(f"{'='*80}")
        print(f"Total Backtests: {successful_tests + failed_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(successful_tests/(successful_tests+failed_tests)*100):.1f}%")

        # Best performing strategies
        print("\n🏆 TOP PERFORMERS BY RETURN:")
        top_returns = results_df.nlargest(5, 'Return%')[['Strategy', 'Dataset', 'Return%', 'Sharpe']]
        for idx, row in top_returns.iterrows():
            print(f"  {row['Strategy']} on {row['Dataset']}: {row['Return%']}%")

        print("\n🎯 TOP PERFORMERS BY SHARPE:")
        top_sharpe = results_df.nlargest(5, 'Sharpe')[['Strategy', 'Dataset', 'Sharpe', 'Return%']]
        for idx, row in top_sharpe.iterrows():
            print(f"  {row['Strategy']} on {row['Dataset']}: Sharpe {row['Sharpe']}")

        # Strategy averages
        print("\n📊 STRATEGY AVERAGES:")
        strategy_avg = results_df.groupby('Strategy').agg({
            'Return%': 'mean',
            'Sharpe': 'mean',
            'Win_Rate%': 'mean',
            'Trades': 'sum'
        }).round(2)
        print(strategy_avg)

    print(f"\n{'='*80}")
    print("✅ SMART MONEY BREAKOUT TESTING COMPLETE")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()