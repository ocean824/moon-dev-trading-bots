"""
Quick test of ATAI Volume Pressure strategies on a few data sources
"""

import sys
import os
import pandas as pd
from backtesting import Backtest

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from atai_volume_pressure_base import ATAIVolumePressureBase
from atai_volume_pressure_mfi import ATAIVolumePressureMFI
from atai_volume_pressure_adx import ATAIVolumePressureADX
from atai_volume_pressure_kalman import ATAIVolumePressureKalman

def test_strategy_on_data(strategy_class, data_path, strategy_name):
    """Test a single strategy on a single data file"""
    try:
        # Load data
        df = pd.read_csv(data_path)

        # Standardize column names (handle both uppercase and lowercase)
        df.columns = [col.capitalize() for col in df.columns]

        # Ensure required columns
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in df.columns for col in required_columns):
            print(f"  Missing columns. Found: {df.columns.tolist()}")
            return None

        # Clean data
        df = df.dropna()
        if len(df) < 100:
            return None

        # Run backtest
        bt = Backtest(df, strategy_class, cash=10000, commission=0.002)
        stats = bt.run()

        return stats

    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    """Quick test of all strategies on select data sources"""

    # Test data files
    data_dir = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data"
    test_files = [
        os.path.join(data_dir, "yahoo_daily/AAPL_stock_1d.csv"),
        os.path.join(data_dir, "ge_data/BTC-USD-1h-2018-1-01T00_00.csv"),
    ]

    # Available test files
    available_files = [f for f in test_files if os.path.exists(f)]

    if not available_files:
        print("No test data files found")
        return

    # Strategies to test
    strategies = [
        ("Base", ATAIVolumePressureBase),
        ("MFI", ATAIVolumePressureMFI),
        ("ADX", ATAIVolumePressureADX),
        ("Kalman", ATAIVolumePressureKalman),
    ]

    print("\n" + "="*70)
    print("ATAI VOLUME PRESSURE STRATEGIES - QUICK TEST")
    print("="*70)

    results_summary = []

    for data_file in available_files:
        data_name = os.path.basename(data_file)
        print(f"\n{'='*60}")
        print(f"Testing on: {data_name}")
        print('='*60)

        for strat_name, strat_class in strategies:
            print(f"\n{strat_name} Strategy:")
            print("-"*30)

            stats = test_strategy_on_data(strat_class, data_file, strat_name)

            if stats is not None:
                # Extract key metrics
                ret = stats['Return [%]']
                trades = stats['# Trades']
                win_rate = stats.get('Win Rate [%]', 0)
                sharpe = stats.get('Sharpe Ratio', 0)
                max_dd = stats.get('Max. Drawdown [%]', 0)

                print(f"  Return: {ret:.2f}%")
                print(f"  Trades: {trades}")
                print(f"  Win Rate: {win_rate:.1f}%")
                print(f"  Sharpe: {sharpe:.3f}")
                print(f"  Max DD: {max_dd:.2f}%")

                results_summary.append({
                    'Data': data_name,
                    'Strategy': strat_name,
                    'Return%': ret,
                    'Trades': trades,
                    'WinRate%': win_rate,
                    'Sharpe': sharpe,
                    'MaxDD%': max_dd
                })
            else:
                print("  Failed to run backtest")

    # Print summary
    if results_summary:
        print("\n" + "="*70)
        print("SUMMARY - ALL RESULTS")
        print("="*70)

        df_summary = pd.DataFrame(results_summary)

        # Group by strategy
        print("\nAverage Performance by Strategy:")
        print("-"*40)

        for strat in df_summary['Strategy'].unique():
            strat_data = df_summary[df_summary['Strategy'] == strat]
            avg_return = strat_data['Return%'].mean()
            avg_trades = strat_data['Trades'].mean()
            avg_win = strat_data['WinRate%'].mean()

            print(f"{strat:10s}: Return={avg_return:7.2f}%  Trades={avg_trades:5.0f}  WinRate={avg_win:5.1f}%")

        # Find best result
        best_idx = df_summary['Return%'].idxmax()
        best = df_summary.loc[best_idx]

        print("\nBest Result:")
        print("-"*40)
        print(f"Strategy: {best['Strategy']}")
        print(f"Data: {best['Data']}")
        print(f"Return: {best['Return%']:.2f}%")
        print(f"Sharpe: {best['Sharpe']:.3f}")

if __name__ == "__main__":
    main()