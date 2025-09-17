"""
Test all Angled Volume Profile strategies
Runs all four AVP variations and compares results
"""

import pandas as pd
import sys
from datetime import datetime

# Import all strategies
from avp_base import AVPBaseStrategy
from avp_vwap import AVPVWAPStrategy
from avp_mfi import AVPMFIStrategy
from avp_adx import AVPADXStrategy

from backtesting import Backtest


def run_all_strategies():
    """Run all AVP strategies and compare results"""

    print("\n" + "="*80)
    print("ANGLED VOLUME PROFILE STRATEGIES - COMPREHENSIVE TEST")
    print("="*80)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Data: Coinbase BTC 15-minute bars")
    print("="*80)

    # Load data once
    print("\nLoading data...")
    data = pd.read_csv('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-15m-150wks-data.csv')
    data['datetime'] = pd.to_datetime(data['datetime'])
    data = data.set_index('datetime')
    # Rename columns to match backtesting.py requirements
    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    # Sort data in ascending order
    data = data.sort_index()
    data = data.dropna()

    print(f"Data loaded: {len(data)} bars")
    print(f"Date range: {data.index[0]} to {data.index[-1]}")
    print(f"Price range: ${data['Low'].min():.2f} - ${data['High'].max():.2f}")

    # Define strategies to test
    strategies = [
        ("AVP Base", AVPBaseStrategy),
        ("AVP + VWAP", AVPVWAPStrategy),
        ("AVP + MFI", AVPMFIStrategy),
        ("AVP + ADX", AVPADXStrategy)
    ]

    results = []

    # Run each strategy
    for name, strategy_class in strategies:
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print('='*60)

        try:
            # Initialize backtest
            bt = Backtest(
                data.copy(),
                strategy_class,
                cash=100000,  # Increased to handle BTC prices
                commission=0.002,
                exclusive_orders=True
            )

            # Run backtest
            stats = bt.run()

            # Store results
            results.append({
                'Strategy': name,
                'Total Return [%]': stats['Return [%]'],
                'Sharpe Ratio': stats['Sharpe Ratio'],
                'Max Drawdown [%]': stats['Max. Drawdown [%]'],
                'Win Rate [%]': stats['Win Rate [%]'],
                '# Trades': stats['# Trades'],
                'Avg Trade [%]': stats.get('Avg. Trade [%]', 0),
                'Profit Factor': stats.get('Profit Factor', 0),
                'Exposure Time [%]': stats['Exposure Time [%]'],
                'Buy & Hold Return [%]': stats['Buy & Hold Return [%]'],
                'Calmar Ratio': stats.get('Calmar Ratio', 0),
                'Sortino Ratio': stats.get('Sortino Ratio', 0),
                'Best Trade [%]': stats.get('Best Trade [%]', 0),
                'Worst Trade [%]': stats.get('Worst Trade [%]', 0),
            })

            # Print key metrics
            print(f"\n{name} Results:")
            print(f"  Return: {stats['Return [%]']:.2f}%")
            print(f"  Sharpe: {stats['Sharpe Ratio']:.2f}")
            print(f"  Max DD: {stats['Max. Drawdown [%]']:.2f}%")
            print(f"  Trades: {stats['# Trades']}")
            print(f"  Win Rate: {stats['Win Rate [%]']:.2f}%")

        except Exception as e:
            print(f"Error running {name}: {e}")
            results.append({
                'Strategy': name,
                'Total Return [%]': 'ERROR',
                'Error': str(e)
            })

    # Create comparison DataFrame
    print("\n" + "="*80)
    print("STRATEGY COMPARISON SUMMARY")
    print("="*80)

    results_df = pd.DataFrame(results)

    # Display main metrics
    print("\nPERFORMANCE METRICS:")
    print("-"*60)
    display_cols = ['Strategy', 'Total Return [%]', 'Sharpe Ratio', 'Max Drawdown [%]',
                   'Win Rate [%]', '# Trades', 'Profit Factor']

    for col in display_cols:
        if col in results_df.columns:
            print(f"\n{col}:")
            for _, row in results_df.iterrows():
                if col == 'Strategy':
                    print(f"  {row[col]}")
                elif pd.notna(row.get(col)) and row.get(col) != 'ERROR':
                    if isinstance(row[col], (int, float)):
                        if col == '# Trades':
                            print(f"  {row['Strategy']:20s}: {row[col]:>6.0f}")
                        else:
                            print(f"  {row['Strategy']:20s}: {row[col]:>8.2f}")
                    else:
                        print(f"  {row['Strategy']:20s}: {row[col]}")

    # Find best strategy by different metrics
    print("\n" + "="*60)
    print("BEST STRATEGIES BY METRIC:")
    print("-"*60)

    numeric_cols = results_df.select_dtypes(include=['float64', 'int64']).columns

    for metric in ['Total Return [%]', 'Sharpe Ratio', 'Win Rate [%]', 'Profit Factor']:
        if metric in numeric_cols:
            best_idx = results_df[metric].idxmax()
            if pd.notna(best_idx):
                best_strategy = results_df.loc[best_idx, 'Strategy']
                best_value = results_df.loc[best_idx, metric]
                print(f"{metric:20s}: {best_strategy:20s} ({best_value:.2f})")

    # Risk-adjusted returns
    print("\n" + "="*60)
    print("RISK-ADJUSTED PERFORMANCE:")
    print("-"*60)

    for _, row in results_df.iterrows():
        if row.get('Total Return [%]') != 'ERROR':
            strategy = row['Strategy']
            ret = row.get('Total Return [%]', 0)
            dd = row.get('Max Drawdown [%]', 1)
            sharpe = row.get('Sharpe Ratio', 0)

            if dd != 0:
                risk_adjusted = ret / abs(dd)
            else:
                risk_adjusted = 0

            print(f"{strategy:20s}: Return/DD = {risk_adjusted:>6.2f}, Sharpe = {sharpe:>6.2f}")

    # Trading activity
    print("\n" + "="*60)
    print("TRADING ACTIVITY:")
    print("-"*60)

    for _, row in results_df.iterrows():
        if row.get('Total Return [%]') != 'ERROR':
            strategy = row['Strategy']
            trades = row.get('# Trades', 0)
            win_rate = row.get('Win Rate [%]', 0)
            avg_trade = row.get('Avg Trade [%]', 0)
            exposure = row.get('Exposure Time [%]', 0)

            print(f"{strategy:20s}: {trades:>4.0f} trades, "
                  f"{win_rate:>5.1f}% win rate, "
                  f"{avg_trade:>6.2f}% avg, "
                  f"{exposure:>5.1f}% exposure")

    # Final recommendation
    print("\n" + "="*80)
    print("ANALYSIS & RECOMMENDATIONS:")
    print("="*80)

    # Calculate composite score for each strategy
    scores = []
    for _, row in results_df.iterrows():
        if row.get('Total Return [%]') != 'ERROR':
            # Weighted scoring: Return (30%), Sharpe (30%), Win Rate (20%), Profit Factor (20%)
            score = 0
            if pd.notna(row.get('Total Return [%]')):
                score += row['Total Return [%]'] * 0.3
            if pd.notna(row.get('Sharpe Ratio')):
                score += row['Sharpe Ratio'] * 30 * 0.3  # Scale Sharpe
            if pd.notna(row.get('Win Rate [%]')):
                score += row['Win Rate [%]'] * 0.2
            if pd.notna(row.get('Profit Factor')):
                score += (row['Profit Factor'] - 1) * 100 * 0.2  # Scale Profit Factor

            scores.append((row['Strategy'], score))

    scores.sort(key=lambda x: x[1], reverse=True)

    print("\nComposite Performance Ranking:")
    for i, (strategy, score) in enumerate(scores, 1):
        print(f"  {i}. {strategy:20s} (Score: {score:.2f})")

    if scores:
        print(f"\nRecommended Strategy: {scores[0][0]}")
        print("\nRationale: Based on composite scoring of return, risk-adjusted performance,")
        print("win rate, and profit factor. This strategy offers the best overall balance.")

    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)

    return results_df


if __name__ == "__main__":
    run_all_strategies()