"""
Timeinality Signal Validator
=============================
Tests discovered time-based signals on out-of-sample data (first 22 weeks of 30-week dataset).
Validates that our alpha persists beyond the 8-week training period.

Dr. Data Dawg - this script will validate if our time-based edges are real or just overfitted!
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

# Data paths
DATA_30WK_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/5_min_data_30wks'
OUTPUT_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/timeinality_strategies/5min_optimizer/validation_results'

# Validation parameters
WEEKS_TO_DROP = 8  # Drop last 8 weeks (training data)
TAKE_PROFIT = 0.03  # 3% take profit
STOP_LOSS = 0.05    # 5% stop loss
POSITION_SIZE = 0.95  # 95% position sizing

# Top signals to validate (from TIMEINALITY_BOT_ALPHA.md)
SIGNALS_TO_TEST = [
    # TIER 1: Universal Signals (highest priority)
    {'symbol': 'ALL', 'day': 'Thursday', 'time': '03:20', 'direction': 'SHORT', 'tier': 1, 'expected_symbols': ['DOGEUSD', 'HBARUSD', 'SUIUSD', 'ADAUSD', 'XRPUSD', 'ETHUSD']},
    {'symbol': 'ALL', 'day': 'Thursday', 'time': '02:55', 'direction': 'SHORT', 'tier': 1, 'expected_symbols': ['DOGEUSD', 'HBARUSD', 'SUIUSD', 'ADAUSD', 'XRPUSD', 'ETHUSD']},
    {'symbol': 'ALL', 'day': 'Thursday', 'time': '01:50', 'direction': 'SHORT', 'tier': 1, 'expected_symbols': ['DOGEUSD', 'HBARUSD', 'SUIUSD', 'ADAUSD', 'XRPUSD', 'ETHUSD']},
    {'symbol': 'ALL', 'day': 'Monday', 'time': '11:45', 'direction': 'LONG', 'tier': 1, 'expected_symbols': ['HBARUSD', 'DOGEUSD', 'ADAUSD', 'ETHUSD']},
    {'symbol': 'ALL', 'day': 'Monday', 'time': '12:00', 'direction': 'LONG', 'tier': 1, 'expected_symbols': ['HBARUSD', 'DOGEUSD', 'ADAUSD', 'ETHUSD']},
    {'symbol': 'ALL', 'day': 'Monday', 'time': '13:10', 'direction': 'LONG', 'tier': 1, 'expected_symbols': ['HBARUSD', 'DOGEUSD', 'ETHUSD']},

    # TIER 2: 100% Win Rate Signals
    {'symbol': 'HBARUSD', 'day': 'Monday', 'time': '12:30', 'direction': 'LONG', 'tier': 2, 'training_return': 24.89, 'training_winrate': 100},
    {'symbol': 'HBARUSD', 'day': 'Monday', 'time': '11:45', 'direction': 'LONG', 'tier': 2, 'training_return': 24.88, 'training_winrate': 100},
    {'symbol': 'DOGEUSD', 'day': 'Thursday', 'time': '03:20', 'direction': 'SHORT', 'tier': 2, 'training_return': 24.81, 'training_winrate': 100},
    {'symbol': 'DOGEUSD', 'day': 'Tuesday', 'time': '19:40', 'direction': 'LONG', 'tier': 2, 'training_return': 24.80, 'training_winrate': 100},
    {'symbol': 'DOGEUSD', 'day': 'Tuesday', 'time': '16:05', 'direction': 'LONG', 'tier': 2, 'training_return': 24.82, 'training_winrate': 100},
    {'symbol': 'DOGEUSD', 'day': 'Tuesday', 'time': '08:30', 'direction': 'LONG', 'tier': 2, 'training_return': 24.74, 'training_winrate': 100},

    # TIER 3: High Sharpe Signals
    {'symbol': 'HBARUSD', 'day': 'Friday', 'time': '21:10', 'direction': 'SHORT', 'tier': 3, 'training_return': 20.72, 'training_sharpe': 3.35},
    {'symbol': 'SUIUSD', 'day': 'Friday', 'time': '20:45', 'direction': 'SHORT', 'tier': 3, 'training_return': 19.63, 'training_sharpe': 2.89},
    {'symbol': 'SUIUSD', 'day': 'Friday', 'time': '19:55', 'direction': 'SHORT', 'tier': 3, 'training_return': 18.69, 'training_sharpe': 2.96},
    {'symbol': 'SUIUSD', 'day': 'Saturday', 'time': '22:05', 'direction': 'SHORT', 'tier': 3, 'training_return': 15.61, 'training_sharpe': 2.91},
]

# Day mapping
DAY_MAP = {
    'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
    'Friday': 4, 'Saturday': 5, 'Sunday': 6
}

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def load_and_prepare_data(symbol: str) -> pd.DataFrame:
    """Load 30-week data and drop last 8 weeks for validation"""

    # Find the data file
    files = [f for f in os.listdir(DATA_30WK_PATH) if symbol in f and f.endswith('.csv')]

    if not files:
        print(f"⚠️ No data file found for {symbol}")
        return None

    filepath = os.path.join(DATA_30WK_PATH, files[0])
    print(f"📂 Loading {symbol} from {files[0]}")

    # Load data
    df = pd.read_csv(filepath)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.sort_values('datetime').reset_index(drop=True)

    # Calculate how many rows to keep (first 22 weeks out of 30)
    total_rows = len(df)
    rows_per_week = 7 * 24 * 12  # 7 days * 24 hours * 12 five-min intervals
    rows_to_drop = WEEKS_TO_DROP * rows_per_week
    rows_to_keep = total_rows - rows_to_drop

    # Keep only first 22 weeks (validation data)
    df_validation = df.head(rows_to_keep).copy()

    # Add time features
    df_validation['day'] = df_validation['datetime'].dt.dayofweek
    df_validation['hour'] = df_validation['datetime'].dt.hour
    df_validation['minute'] = df_validation['datetime'].dt.minute
    df_validation['time_str'] = df_validation['datetime'].dt.strftime('%H:%M')

    weeks_in_validation = len(df_validation) / rows_per_week
    print(f"  ✅ Loaded {len(df_validation):,} rows ({weeks_in_validation:.1f} weeks of validation data)")

    return df_validation

def test_signal(df: pd.DataFrame, signal: dict) -> dict:
    """Test a single signal on validation data"""

    # Parse signal time
    hour, minute = map(int, signal['time'].split(':'))
    target_day = DAY_MAP[signal['day']]

    # Filter for target times
    mask = (df['day'] == target_day) & (df['hour'] == hour) & (df['minute'] == minute)
    entry_points = df[mask].copy()

    if len(entry_points) == 0:
        return None

    # Track trades
    trades = []

    for idx, entry_row in entry_points.iterrows():
        entry_price = entry_row['close']
        entry_time = entry_row['datetime']

        # Calculate TP/SL levels
        if signal['direction'] == 'LONG':
            tp_price = entry_price * (1 + TAKE_PROFIT)
            sl_price = entry_price * (1 - STOP_LOSS)
        else:  # SHORT
            tp_price = entry_price * (1 - TAKE_PROFIT)
            sl_price = entry_price * (1 + STOP_LOSS)

        # Look forward to find exit
        future_df = df[df['datetime'] > entry_time].head(288)  # Next 24 hours max

        exit_price = None
        exit_time = None
        exit_reason = None

        for _, future_row in future_df.iterrows():
            if signal['direction'] == 'LONG':
                if future_row['high'] >= tp_price:
                    exit_price = tp_price
                    exit_time = future_row['datetime']
                    exit_reason = 'TP'
                    break
                elif future_row['low'] <= sl_price:
                    exit_price = sl_price
                    exit_time = future_row['datetime']
                    exit_reason = 'SL'
                    break
            else:  # SHORT
                if future_row['low'] <= tp_price:
                    exit_price = tp_price
                    exit_time = future_row['datetime']
                    exit_reason = 'TP'
                    break
                elif future_row['high'] >= sl_price:
                    exit_price = sl_price
                    exit_time = future_row['datetime']
                    exit_reason = 'SL'
                    break

        # If no TP/SL hit, exit at next entry point
        if exit_price is None and len(future_df) > 0:
            next_entry_mask = (future_df['day'] == target_day) & \
                            (future_df['hour'] == hour) & \
                            (future_df['minute'] == minute)
            next_entries = future_df[next_entry_mask]

            if len(next_entries) > 0:
                exit_price = next_entries.iloc[0]['close']
                exit_time = next_entries.iloc[0]['datetime']
                exit_reason = 'NextEntry'
            else:
                # Exit at end of data
                exit_price = future_df.iloc[-1]['close'] if len(future_df) > 0 else entry_price
                exit_time = future_df.iloc[-1]['datetime'] if len(future_df) > 0 else entry_time
                exit_reason = 'EndData'

        # Calculate return
        if signal['direction'] == 'LONG':
            trade_return = (exit_price - entry_price) / entry_price
        else:  # SHORT
            trade_return = (entry_price - exit_price) / entry_price

        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'return': trade_return,
            'exit_reason': exit_reason
        })

    # Calculate statistics
    if trades:
        returns = [t['return'] for t in trades]
        winning_trades = [t for t in trades if t['return'] > 0]

        total_return = (1 + pd.Series(returns)).prod() - 1
        avg_return = np.mean(returns)
        win_rate = len(winning_trades) / len(trades) * 100

        # Calculate Sharpe ratio
        if np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(52)  # Annualized
        else:
            sharpe = 0

        # Calculate max drawdown
        cumulative = (1 + pd.Series(returns)).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()

        return {
            'total_trades': len(trades),
            'total_return_%': total_return * 100,
            'avg_return_%': avg_return * 100,
            'win_rate_%': win_rate,
            'sharpe_ratio': sharpe,
            'max_drawdown_%': max_drawdown * 100,
            'winning_trades': len(winning_trades),
            'losing_trades': len(trades) - len(winning_trades),
            'tp_exits': len([t for t in trades if t['exit_reason'] == 'TP']),
            'sl_exits': len([t for t in trades if t['exit_reason'] == 'SL'])
        }

    return None

# ============================================================================
# MAIN VALIDATION
# ============================================================================

def main():
    """Run validation on all signals"""

    print("=" * 100)
    print("🚀 TIMEINALITY SIGNAL VALIDATOR")
    print("=" * 100)
    print(f"Data path: {DATA_30WK_PATH}")
    print(f"Validation period: First 22 weeks (out-of-sample)")
    print(f"Training period: Last 8 weeks (excluded from validation)")
    print(f"Total signals to test: {len(SIGNALS_TO_TEST)}")
    print()

    # Create output directory
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    # Load all data files
    data_files = {}
    symbols = set()

    for signal in SIGNALS_TO_TEST:
        if signal['symbol'] == 'ALL':
            symbols.update(signal.get('expected_symbols', []))
        else:
            symbols.add(signal['symbol'])

    print("📊 Loading data files...")
    for symbol in symbols:
        df = load_and_prepare_data(symbol)
        if df is not None:
            data_files[symbol] = df

    print(f"\n✅ Loaded {len(data_files)} data files: {list(data_files.keys())}")

    # Validate each signal
    results = []

    print("\n" + "=" * 100)
    print("🔬 VALIDATING SIGNALS")
    print("=" * 100)

    for i, signal in enumerate(SIGNALS_TO_TEST, 1):
        print(f"\n[{i}/{len(SIGNALS_TO_TEST)}] Testing: {signal['day']} {signal['time']} {signal['direction']}", end='')

        if signal['symbol'] == 'ALL':
            # Universal signal - test on all expected symbols
            print(f" (Universal - Tier {signal['tier']})")

            signal_results = []
            for symbol in signal.get('expected_symbols', []):
                if symbol in data_files:
                    result = test_signal(data_files[symbol], signal)
                    if result:
                        signal_results.append({
                            'symbol': symbol,
                            **result
                        })

            if signal_results:
                # Aggregate results
                avg_return = np.mean([r['total_return_%'] for r in signal_results])
                avg_winrate = np.mean([r['win_rate_%'] for r in signal_results])
                avg_sharpe = np.mean([r['sharpe_ratio'] for r in signal_results])
                symbols_profitable = len([r for r in signal_results if r['total_return_%'] > 0])

                print(f"  ✅ Works on {len(signal_results)}/{len(signal.get('expected_symbols', []))} symbols")
                print(f"     Avg Return: {avg_return:.2f}% | Avg Win Rate: {avg_winrate:.1f}% | Avg Sharpe: {avg_sharpe:.2f}")
                print(f"     Profitable on {symbols_profitable}/{len(signal_results)} symbols")

                # Store result
                results.append({
                    'tier': signal['tier'],
                    'day': signal['day'],
                    'time': signal['time'],
                    'direction': signal['direction'],
                    'type': 'Universal',
                    'symbols_tested': len(signal_results),
                    'symbols_profitable': symbols_profitable,
                    'avg_return_%': avg_return,
                    'avg_winrate_%': avg_winrate,
                    'avg_sharpe': avg_sharpe,
                    'details': signal_results
                })
            else:
                print(f"  ❌ No data available for testing")

        else:
            # Specific symbol signal
            print(f" ({signal['symbol']} - Tier {signal['tier']})")

            if signal['symbol'] in data_files:
                result = test_signal(data_files[signal['symbol']], signal)
                if result:
                    # Compare to training performance
                    training_return = signal.get('training_return', 0)
                    training_winrate = signal.get('training_winrate', 0)

                    print(f"  Validation: Return: {result['total_return_%']:.2f}% | Win Rate: {result['win_rate_%']:.1f}% | Sharpe: {result['sharpe_ratio']:.2f}")

                    if training_return > 0:
                        print(f"  Training:   Return: {training_return:.2f}% | Win Rate: {training_winrate:.1f}%")
                        retention = result['total_return_%'] / training_return * 100 if training_return > 0 else 0
                        print(f"  📊 Performance retention: {retention:.1f}%")

                    # Store result
                    results.append({
                        'tier': signal['tier'],
                        'day': signal['day'],
                        'time': signal['time'],
                        'direction': signal['direction'],
                        'symbol': signal['symbol'],
                        'type': 'Specific',
                        'validation_return_%': result['total_return_%'],
                        'validation_winrate_%': result['win_rate_%'],
                        'validation_sharpe': result['sharpe_ratio'],
                        'training_return_%': training_return,
                        'training_winrate_%': training_winrate,
                        'performance_retention_%': retention if training_return > 0 else None,
                        **result
                    })
                else:
                    print(f"  ❌ No valid trades found")
            else:
                print(f"  ❌ No data file for {signal['symbol']}")

    # ============================================================================
    # SUMMARY REPORT
    # ============================================================================

    print("\n" + "=" * 100)
    print("📈 VALIDATION SUMMARY")
    print("=" * 100)

    # Convert to DataFrame for analysis
    if results:
        df_results = pd.DataFrame(results)

        # Tier 1 (Universal) Analysis
        tier1_results = [r for r in results if r['tier'] == 1]
        if tier1_results:
            print("\n🥇 TIER 1 - UNIVERSAL SIGNALS:")
            print("-" * 50)
            for r in tier1_results:
                status = "✅" if r['avg_return_%'] > 5 else "⚠️"
                print(f"{status} {r['day']} {r['time']} {r['direction']}: {r['avg_return_%']:.2f}% avg return | {r['symbols_profitable']}/{r['symbols_tested']} profitable")

        # Tier 2 (100% Win Rate) Analysis
        tier2_results = [r for r in results if r['tier'] == 2]
        if tier2_results:
            print("\n🥈 TIER 2 - 100% WIN RATE SIGNALS:")
            print("-" * 50)
            for r in tier2_results:
                if 'performance_retention_%' in r and r['performance_retention_%']:
                    status = "✅" if r['performance_retention_%'] > 50 else "⚠️"
                    print(f"{status} {r['symbol']} {r['day']} {r['time']}: {r['validation_return_%']:.2f}% ({r['performance_retention_%']:.0f}% of training)")

        # Tier 3 (High Sharpe) Analysis
        tier3_results = [r for r in results if r['tier'] == 3]
        if tier3_results:
            print("\n🥉 TIER 3 - HIGH SHARPE SIGNALS:")
            print("-" * 50)
            for r in tier3_results:
                status = "✅" if r['validation_return_%'] > 5 else "⚠️"
                print(f"{status} {r['symbol']} {r['day']} {r['time']}: {r['validation_return_%']:.2f}% | Sharpe: {r['validation_sharpe']:.2f}")

        # Overall Statistics
        print("\n" + "=" * 100)
        print("🎯 OVERALL VALIDATION RESULTS")
        print("=" * 100)

        profitable_signals = len([r for r in results if
                                 (r.get('avg_return_%', 0) > 0 if r['type'] == 'Universal'
                                  else r.get('validation_return_%', 0) > 0)])

        print(f"Total Signals Tested: {len(results)}")
        print(f"Profitable Signals: {profitable_signals} ({profitable_signals/len(results)*100:.1f}%)")

        # Save results to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(OUTPUT_PATH, f'validation_results_{timestamp}.csv')
        df_results.to_csv(output_file, index=False)
        print(f"\n💾 Results saved to: {output_file}")

        # Recommendations
        print("\n" + "=" * 100)
        print("🚀 RECOMMENDATIONS FOR BOT IMPLEMENTATION")
        print("=" * 100)

        strong_signals = []
        moderate_signals = []
        weak_signals = []

        for r in results:
            if r['type'] == 'Universal':
                if r['avg_return_%'] > 8 and r['symbols_profitable'] >= 3:
                    strong_signals.append(f"{r['day']} {r['time']} {r['direction']} (Universal)")
                elif r['avg_return_%'] > 5:
                    moderate_signals.append(f"{r['day']} {r['time']} {r['direction']} (Universal)")
                else:
                    weak_signals.append(f"{r['day']} {r['time']} {r['direction']} (Universal)")
            else:
                if r['validation_return_%'] > 10 and r['validation_winrate_%'] > 70:
                    strong_signals.append(f"{r['symbol']} {r['day']} {r['time']} {r['direction']}")
                elif r['validation_return_%'] > 5:
                    moderate_signals.append(f"{r['symbol']} {r['day']} {r['time']} {r['direction']}")
                else:
                    weak_signals.append(f"{r['symbol']} {r['day']} {r['time']} {r['direction']}")

        if strong_signals:
            print("\n💪 STRONG SIGNALS (Deploy First):")
            for sig in strong_signals[:10]:
                print(f"  • {sig}")

        if moderate_signals:
            print("\n👍 MODERATE SIGNALS (Deploy After Testing Strong):")
            for sig in moderate_signals[:5]:
                print(f"  • {sig}")

        if weak_signals:
            print("\n⚠️ WEAK SIGNALS (Need More Data or Skip):")
            for sig in weak_signals[:5]:
                print(f"  • {sig}")

    else:
        print("❌ No results generated - check data availability")

    print("\n" + "=" * 100)
    print("✅ VALIDATION COMPLETE!")
    print("=" * 100)

if __name__ == "__main__":
    main()