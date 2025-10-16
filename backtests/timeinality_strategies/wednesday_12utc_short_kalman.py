"""
Wednesday 12 UTC Short + Kalman Filter Strategy
===============================================
Timeinality Strategy with Kalman Filter: Time-based trading strategy that opens SHORT positions
at 12:00 UTC on Wednesdays, filtered by Kalman Filter for price trend estimation.

Trading Logic:
- Entry: SHORT at 12:00 UTC on Wednesdays when price is above Kalman Filter (potential reversal)
- Exit: Take profit at 3% or stop loss at 5%
- Position management: Close on next signal if still open
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import sys
import os
import glob

# Disable scientific notation for better readability
pd.set_option('display.float_format', lambda x: '%.6f' % x)
pd.options.display.float_format = '{:.6f}'.format

print("🕐 Moon Dev's Wednesday 12 UTC Short + Kalman Filter Strategy Loading... 🌙")

# Strategy parameters
TAKE_PROFIT_PERCENT = 3.0  # 3% take profit
STOP_LOSS_PERCENT = 5.0    # 5% stop loss

# Kalman Filter parameters
KALMAN_TRANS_COV = 0.01    # Process noise covariance
KALMAN_OBS_COV = 1.0       # Observation noise covariance

# Get all CSV files from 1_hr_data folder
data_files = glob.glob('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/1_hr_data/*.csv')
data_files.sort()

print(f"📊 Found {len(data_files)} 1-hour data files to test")

# Use first file for quick example run
DATA_PATH = data_files[0] if data_files else None

if DATA_PATH is None:
    print("❌ No 1h data files found!")
    sys.exit(1)

def load_and_prepare_data(filepath):
    """Load CSV and prepare data for backtesting"""
    df = pd.read_csv(filepath)
    # Ensure datetime column exists and convert to datetime
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
    # Capitalize column names for backtesting.py
    df.columns = [col.capitalize() for col in df.columns]
    df = df.sort_index()
    df = df.dropna()
    return df

print(f"📊 Loading example data from: {os.path.basename(DATA_PATH)}")
data = load_and_prepare_data(DATA_PATH)
print(f"✅ Data loaded! {len(data)} rows | Columns: {list(data.columns)} 🌙")

def kalman_filter(prices, trans_cov=0.01, obs_cov=1.0):
    """
    Apply Kalman filter to price data

    Parameters:
    - prices: Array of prices
    - trans_cov: Process noise covariance (Q)
    - obs_cov: Observation noise covariance (R)

    Returns:
    - Filtered price estimates
    """
    n = len(prices)
    filtered = np.zeros(n)

    # Initial values
    x = prices[0]  # Initial state estimate
    p = 1.0        # Initial estimation error covariance

    for i in range(n):
        # Prediction step
        x_pred = x
        p_pred = p + trans_cov

        # Update step
        k = p_pred / (p_pred + obs_cov)  # Kalman gain
        x = x_pred + k * (prices[i] - x_pred)  # Updated estimate
        p = (1 - k) * p_pred  # Updated error covariance

        filtered[i] = x

    return filtered

class Wednesday12UTCShortKalman(Strategy):
    # Strategy parameters
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    kalman_trans_cov = KALMAN_TRANS_COV
    kalman_obs_cov = KALMAN_OBS_COV

    def init(self):
        # Pre-calculate which bars are Wednesday at 12 UTC
        self.is_wednesday_12utc = self.I(lambda: self.calculate_wednesday_12utc())

        # Calculate Kalman Filter
        # Convert Close to numpy array for Kalman filter
        close_array = np.array(self.data.Close)
        self.kalman_filtered = self.I(
            lambda: kalman_filter(
                close_array,
                self.kalman_trans_cov,
                self.kalman_obs_cov
            )
        )

        # Track entry prices for debugging
        self.entry_prices = []
        self.entry_times = []
        self.skipped_signals = 0

    def calculate_wednesday_12utc(self):
        """Calculate which bars are Wednesday at 12:00 UTC"""
        # Create a boolean array for Wednesday at 12 UTC
        wednesday_12utc = np.zeros(len(self.data), dtype=bool)

        for i in range(len(self.data)):
            timestamp = self.data.index[i]
            # Check if it's Wednesday (2) and hour is 12 UTC
            if timestamp.dayofweek == 2 and timestamp.hour == 12:
                wednesday_12utc[i] = True

        return wednesday_12utc

    def next(self):
        # Check if current bar is Wednesday at 12 UTC
        if self.is_wednesday_12utc[-1]:
            # Check if price is above Kalman filter (potential overbought for reversal)
            # When price is significantly above the smoothed Kalman estimate, it may revert
            if self.data.Close[-1] > self.kalman_filtered[-1] * 1.005:  # Price at least 0.5% above Kalman
                # Close any existing position before opening new one
                if self.position:
                    self.position.close()

                # Open SHORT position
                current_price = self.data.Close[-1]

                # Calculate stop loss and take profit for SHORT position
                # For SHORT: stop loss is above entry, take profit is below entry
                sl_price = current_price * (1 + self.stop_loss)  # Stop loss 5% above entry
                tp_price = current_price * (1 - self.take_profit)  # Take profit 3% below entry

                # Execute SHORT trade with 95% of equity
                self.sell(sl=sl_price, tp=tp_price, size=0.95)

                # Track entry for debugging
                self.entry_prices.append(current_price)
                self.entry_times.append(self.data.index[-1])
            else:
                # Signal occurred but Kalman filter prevented trade
                self.skipped_signals += 1

# Run single backtest with proper position sizing
bt = Backtest(
    data,
    Wednesday12UTCShortKalman,
    cash=1000000,  # Use 1M for proper position sizing
    commission=0.00045,
    trade_on_close=False,
    exclusive_orders=True
)

print("\n🌙 ===== WEDNESDAY 12 UTC SHORT + KALMAN FILTER - DEFAULT PARAMETERS ===== 🌙")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Entry Time: Wednesdays at 12:00 UTC")
print(f"Kalman Trans Covariance: {KALMAN_TRANS_COV}")
print(f"Kalman Obs Covariance: {KALMAN_OBS_COV}")
print(f"Direction: SHORT only (with Kalman Filter)")

stats_default = bt.run()
print("\n" + "="*80)
print("FULL BACKTEST STATISTICS:")
print("="*80)
print(stats_default)
print("="*80)

# Show plot without saving HTML
try:
    bt.plot(open_browser=False)
except:
    pass

# TEST ON ALL 1H DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING WEDNESDAY 12 UTC SHORT + KALMAN FILTER ON ALL 1H DATA SOURCES")
    print("="*80)

    all_results = []

    for i, data_file in enumerate(data_files, 1):
        filename = os.path.basename(data_file)
        print(f"\n{'='*80}")
        print(f"📊 [{i}/{len(data_files)}] Testing on: {filename}")
        print(f"{'='*80}")

        try:
            # Load data
            test_data = load_and_prepare_data(data_file)

            # Run backtest
            bt_test = Backtest(
                test_data,
                Wednesday12UTCShortKalman,
                cash=1000000,
                commission=0.00045,
                trade_on_close=False,
                exclusive_orders=True
            )

            stats = bt_test.run()

            # Print FULL stats for this data source
            print("\n" + stats.to_string())
            print("\n")

            # Store key results for summary
            result = {
                'Data_Source': filename,
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
            print(f"❌ Error testing {filename}: {str(e)}")
            continue

    # Save results to CSV
    if all_results:
        results_df = pd.DataFrame(all_results)
        results_df = results_df.sort_values('Return_%', ascending=False)

        os.makedirs('./results', exist_ok=True)
        results_df.to_csv('./results/wednesday_12utc_short_kalman_results.csv', index=False)

        print("\n" + "="*80)
        print("FINAL SUMMARY - ALL DATA SOURCES")
        print("="*80)
        print(results_df.to_string(index=False))
        print(f"\n✅ Full results saved to: ./results/wednesday_12utc_short_kalman_results.csv")
        print(f"📊 Tested {len(all_results)} data sources")