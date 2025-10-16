"""
Hourly SHORT Strategy - Combined Days
======================================
Tests SHORT positions at each hour, taking trades on ALL specified days in the same backtest.

Configuration:
- TEST_DAYS: List of days to test [0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday]
  Examples: [0,1,2,3,4,5,6] = all days, [2] = Wednesday only, [0,1,2,3,4] = weekdays only

Trading Logic:
- Entry: SHORT at specified hour on ALL specified days (combined in same backtest)
- Exit: Take profit at 3% or stop loss at 5%
- Position size: 95% of equity

Example: Hour 10 with TEST_DAYS=[0,1,2,3,4,5,6] means trade EVERY day at 10 UTC in one backtest
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import sys
import os
import glob
from datetime import datetime

# Disable scientific notation for better readability
pd.set_option('display.float_format', lambda x: '%.6f' % x)
pd.options.display.float_format = '{:.6f}'.format

print("🕐 Moon Dev's Hourly SHORT Strategy (Combined Days) Loading... 🌙")

# ============================================================================
# CONFIGURATION - CHANGE THESE TO TEST DIFFERENT SCENARIOS
# ============================================================================
TEST_DAYS = [0, 1, 2, 3, 4, 5, 6]  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
TAKE_PROFIT_PERCENT = 3.0  # 3% take profit
STOP_LOSS_PERCENT = 5.0    # 5% stop loss
# ============================================================================

DAY_NAMES = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'}

print(f"\n📅 Testing Days (Combined): {[DAY_NAMES[d] for d in TEST_DAYS]}")
print(f"⏰ Testing Hours: 0-23 UTC")
print(f"📉 Direction: SHORT")
print(f"🎯 Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"🛑 Stop Loss: {STOP_LOSS_PERCENT}%")

# Get all CSV files from 1_hr_data folder
data_files = glob.glob('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/1_hr_data/*.csv')
data_files.sort()

print(f"\n📊 Found {len(data_files)} 1-hour data files to test")
print(f"🔢 Total backtests: {len(data_files)} files × 24 hours = {len(data_files) * 24}")
print(f"🔢 Each hour tests ALL {len(TEST_DAYS)} days in one backtest\n")

def load_and_prepare_data(filepath):
    """Load CSV and prepare data for backtesting"""
    df = pd.read_csv(filepath)
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
    df.columns = [col.capitalize() for col in df.columns]
    df = df.sort_index()
    df = df.dropna()
    return df

class HourlyShortCombinedStrategy(Strategy):
    # Strategy parameters - will be set dynamically
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    target_hour = 12  # Default, will be overridden
    target_days = [0, 1, 2, 3, 4, 5, 6]  # Default, will be overridden

    def init(self):
        # Pre-calculate which bars match our target hour and days
        self.is_target_time = self.I(lambda: self.calculate_target_times())

    def calculate_target_times(self):
        """Calculate which bars match target hour and days"""
        target_times = np.zeros(len(self.data), dtype=bool)

        for i in range(len(self.data)):
            timestamp = self.data.index[i]
            # Check if it's the right day AND the right hour
            if timestamp.dayofweek in self.target_days and timestamp.hour == self.target_hour:
                target_times[i] = True

        return target_times

    def next(self):
        # Check if current bar matches our target time
        if self.is_target_time[-1]:
            # Close any existing position before opening new one
            if self.position:
                self.position.close()

            # Open SHORT position with 95% of equity
            current_price = self.data.Close[-1]

            # Calculate stop loss and take profit for SHORT position
            sl_price = current_price * (1 + self.stop_loss)  # Stop loss 5% above entry
            tp_price = current_price * (1 - self.take_profit)  # Take profit 3% below entry

            # Execute SHORT trade with 95% of equity
            self.sell(sl=sl_price, tp=tp_price, size=0.95)


# ============================================================================
# MAIN OPTIMIZATION LOOP
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("STARTING HOURLY SHORT STRATEGY (COMBINED DAYS)")
    print("="*80)

    all_results = []
    total_backtests = len(data_files) * 24
    current_backtest = 0

    days_str_display = ','.join([DAY_NAMES[d][:3] for d in TEST_DAYS])

    for data_file in data_files:
        filename = os.path.basename(data_file)
        print(f"\n{'='*80}")
        print(f"📊 Testing {filename}")
        print(f"{'='*80}")

        try:
            # Load data once per file
            test_data = load_and_prepare_data(data_file)

            # Test each hour (with ALL days combined)
            for hour in range(24):
                current_backtest += 1
                progress = (current_backtest / total_backtests) * 100

                print(f"⏰ [{current_backtest}/{total_backtests}] ({progress:.1f}%) Testing Hour {hour:02d}:00 UTC on {days_str_display}")

                try:
                    # Create strategy class with specific hour (all days)
                    class HourlyShortOptimized(HourlyShortCombinedStrategy):
                        target_hour = hour
                        target_days = TEST_DAYS  # Use ALL specified days

                    # Run backtest
                    bt_test = Backtest(
                        test_data,
                        HourlyShortOptimized,
                        cash=1000000,
                        commission=0.00045,
                        trade_on_close=False,
                        exclusive_orders=True
                    )

                    stats = bt_test.run()

                    # Store results
                    result = {
                        'Data_Source': filename,
                        'Hour_UTC': hour,
                        'Days_Tested': days_str_display,
                        'Return_%': stats['Return [%]'],
                        'BuyHold_Return_%': stats['Buy & Hold Return [%]'],
                        'Sharpe_Ratio': stats.get('Sharpe Ratio', 0),
                        'Max_Drawdown_%': stats['Max. Drawdown [%]'],
                        'Total_Trades': stats['# Trades'],
                        'Win_Rate_%': stats['Win Rate [%]'],
                        'Profit_Factor': stats.get('Profit Factor', 0)
                    }
                    all_results.append(result)

                except Exception as e:
                    print(f"  ❌ Error: {str(e)}")
                    continue

        except Exception as e:
            print(f"❌ Error loading {filename}: {str(e)}")
            continue

    # Save and display results
    if all_results:
        results_df = pd.DataFrame(all_results)

        # Sort by return
        results_df_sorted = results_df.sort_values('Return_%', ascending=False)

        # Save to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        days_str = '_'.join([str(d) for d in TEST_DAYS])
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)
        output_file = os.path.join(results_dir, f'hourly_short_combined_days{days_str}_{timestamp}.csv')
        results_df_sorted.to_csv(output_file, index=False)

        print("\n" + "="*80)
        print("OPTIMIZATION COMPLETE!")
        print("="*80)
        print(f"✅ Completed {len(all_results)} backtests")
        print(f"✅ Results saved to: {output_file}")

        print("\n" + "="*80)
        print("TOP 20 BEST PERFORMERS:")
        print("="*80)
        print(results_df_sorted.head(20).to_string(index=False))

        print("\n" + "="*80)
        print("BOTTOM 20 WORST PERFORMERS:")
        print("="*80)
        print(results_df_sorted.tail(20).to_string(index=False))

        # Summary statistics
        print("\n" + "="*80)
        print("SUMMARY STATISTICS:")
        print("="*80)
        print(f"Average Return: {results_df['Return_%'].mean():.6f}%")
        print(f"Median Return: {results_df['Return_%'].median():.6f}%")
        print(f"Best Return: {results_df['Return_%'].max():.6f}%")
        print(f"Worst Return: {results_df['Return_%'].min():.6f}%")
        print(f"Std Dev: {results_df['Return_%'].std():.6f}%")

        # Best hour combination overall
        best_combo = results_df_sorted.iloc[0]
        print(f"\n🏆 BEST COMBINATION:")
        print(f"   Data: {best_combo['Data_Source']}")
        print(f"   Hour: {best_combo['Hour_UTC']:02.0f}:00 UTC")
        print(f"   Days: {best_combo['Days_Tested']}")
        print(f"   Return: {best_combo['Return_%']:.6f}%")
        print(f"   Win Rate: {best_combo['Win_Rate_%']:.2f}%")
        print(f"   Profit Factor: {best_combo['Profit_Factor']:.6f}")

    else:
        print("\n❌ No results collected!")
