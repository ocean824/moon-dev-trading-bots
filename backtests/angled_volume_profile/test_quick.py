"""
Quick test to verify multi-data setup works
Tests one strategy on a few data sources
"""

import pandas as pd
import numpy as np
from backtesting import Backtest
from avp_base import AVPBaseStrategy, load_data, run_single_backtest

def quick_test():
    """Quick test with limited data sources"""

    print("\n" + "="*60)
    print("QUICK TEST - AVP BASE STRATEGY")
    print("="*60)

    # Test just a few data sources
    test_sources = [
        ('BTC', 'crypto_15m'),
        ('AAPL', 'yahoo_hourly'),
        ('TSLA', 'ib_data'),
    ]

    results = []

    for symbol, source in test_sources:
        print(f"\nTesting {symbol} ({source})...", end=' ')

        # Load data
        data = load_data(symbol, source)

        if data is None:
            print("❌ No data found")
            continue

        print(f"✅ Loaded {len(data)} rows")

        # Adjust cash
        cash = 1000000 if symbol == 'BTC' else 100000

        # Run backtest
        try:
            stats = run_single_backtest(symbol, data, cash)

            if stats is not None:
                print(f"  Return: {stats.get('Return [%]', 0):.2f}%")
                print(f"  Sharpe: {stats.get('Sharpe Ratio', 0):.3f}")
                print(f"  Trades: {stats.get('# Trades', 0)}")
                results.append({
                    'Symbol': symbol,
                    'Source': source,
                    'Return_%': stats.get('Return [%]', 0),
                    'Sharpe': stats.get('Sharpe Ratio', 0),
                    'Trades': stats.get('# Trades', 0)
                })
            else:
                print("  ❌ Backtest failed")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    if results:
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        df = pd.DataFrame(results)
        print(df.to_string(index=False))
        print("="*60)
        print("✅ Multi-data testing setup is working correctly!")
    else:
        print("\n❌ No successful tests - check data paths")

    return results

if __name__ == "__main__":
    quick_test()