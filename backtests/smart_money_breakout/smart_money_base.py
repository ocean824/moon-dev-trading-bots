"""
Smart Money Breakout Channels - Base Strategy
Based on consolidation detection and breakout trading with volume analysis
"""

from backtesting import Backtest, Strategy
import pandas as pd
import numpy as np
import pandas_ta as ta
from datetime import datetime
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SmartMoneyBreakoutBase(Strategy):
    # Strategy parameters
    lookback = 20  # Lookback period for channel detection
    volatility_threshold = 0.5  # Threshold for volatility normalization
    channel_min_bars = 5  # Minimum bars for valid channel
    breakout_buffer = 0.001  # Buffer for breakout confirmation (0.1%)
    strong_close_pct = 0.5  # Percentage of candle body outside channel for strong breakout
    atr_period = 14
    stop_loss_atr = 2.0  # ATR multiplier for stop loss
    take_profit_atr = 3.0  # ATR multiplier for take profit
    position_size_pct = 0.95  # Position size as percentage of equity

    # Volume parameters
    volume_ma_period = 20
    volume_threshold = 1.2  # Volume must be X times average for valid breakout

    def init(self):
        # Price data
        self.high = self.data.High
        self.low = self.data.Low
        self.close = self.data.Close
        self.open = self.data.Open
        self.volume = self.data.Volume

        # Calculate ATR for position sizing and stops
        self.atr = self.I(ta.atr, pd.Series(self.data.High),
                         pd.Series(self.data.Low),
                         pd.Series(self.data.Close),
                         length=self.atr_period)

        # Calculate normalized volatility for channel detection
        self.hl_range = self.I(lambda: pd.Series(self.data.High - self.data.Low))
        self.volatility_ma = self.I(ta.sma, self.hl_range, length=self.lookback)
        self.normalized_volatility = self.I(lambda: self.hl_range / self.volatility_ma)

        # Volume analysis
        self.volume_ma = self.I(ta.sma, pd.Series(self.data.Volume), length=self.volume_ma_period)
        self.volume_ratio = self.I(lambda: pd.Series(self.data.Volume) / self.volume_ma)

        # Track channel state
        self.channel_top = np.nan
        self.channel_bottom = np.nan
        self.channel_start_idx = -1
        self.in_channel = False
        self.channel_volume_total = 0
        self.channel_up_volume = 0
        self.channel_down_volume = 0
        self.bars_in_channel = 0

        # Trade management
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trade_type = None  # 'long' or 'short'

    def detect_channel_formation(self, idx):
        """Detect when a consolidation channel forms"""
        if idx < self.lookback:
            return False

        # Check if volatility is below threshold (indicating consolidation)
        recent_volatility = self.normalized_volatility[idx]
        if recent_volatility < self.volatility_threshold:
            if not self.in_channel:
                # Start new channel
                self.channel_start_idx = idx
                self.in_channel = True
                self.bars_in_channel = 0
                self.channel_volume_total = 0
                self.channel_up_volume = 0
                self.channel_down_volume = 0

                # Calculate initial channel boundaries
                lookback_start = max(0, idx - self.lookback)
                self.channel_top = max(self.data.High[lookback_start:idx+1])
                self.channel_bottom = min(self.data.Low[lookback_start:idx+1])

                return True
        else:
            # Volatility increased - end channel if it exists
            if self.in_channel and self.bars_in_channel >= self.channel_min_bars:
                self.in_channel = False
                return False

        return self.in_channel

    def update_channel_stats(self, idx):
        """Update channel statistics including volume"""
        if not self.in_channel:
            return

        self.bars_in_channel += 1

        # Update channel boundaries if needed
        if self.data.High[idx] <= self.channel_top and self.data.Low[idx] >= self.channel_bottom:
            # Price still within channel - update volume stats
            self.channel_volume_total += self.volume[idx]

            if self.close[idx] > self.open[idx]:
                self.channel_up_volume += self.volume[idx]
            else:
                self.channel_down_volume += self.volume[idx]

    def check_breakout(self, idx):
        """Check for channel breakout with strong close validation"""
        if not self.in_channel or self.bars_in_channel < self.channel_min_bars:
            return None

        current_close = self.close[idx]
        current_high = self.high[idx]
        current_low = self.low[idx]
        current_open = self.open[idx]

        # Calculate candle body
        body_top = max(current_close, current_open)
        body_bottom = min(current_close, current_open)
        body_size = body_top - body_bottom

        # Check for upward breakout
        if current_close > self.channel_top * (1 + self.breakout_buffer):
            # Check strong close requirement
            body_outside_top = max(0, body_bottom - self.channel_top)
            if body_size > 0:
                pct_outside = body_outside_top / body_size
                if pct_outside >= self.strong_close_pct:
                    # Check volume confirmation
                    if self.volume_ratio[idx] >= self.volume_threshold:
                        self.in_channel = False
                        return 'long'

        # Check for downward breakout
        elif current_close < self.channel_bottom * (1 - self.breakout_buffer):
            # Check strong close requirement
            body_outside_bottom = max(0, self.channel_bottom - body_top)
            if body_size > 0:
                pct_outside = body_outside_bottom / body_size
                if pct_outside >= self.strong_close_pct:
                    # Check volume confirmation
                    if self.volume_ratio[idx] >= self.volume_threshold:
                        self.in_channel = False
                        return 'short'

        return None

    def calculate_position_size(self):
        """Calculate position size based on available equity"""
        return self.position_size_pct

    def next(self):
        idx = len(self.data) - 1
        if idx < self.lookback + 1:
            return

        # Detect channel formation
        self.detect_channel_formation(idx)

        # Update channel statistics if in channel
        if self.in_channel:
            self.update_channel_stats(idx)

        # Check for existing position
        if self.position:
            # Manage existing trade
            if self.trade_type == 'long':
                # Check stop loss
                if self.close[idx] <= self.stop_loss:
                    self.position.close()
                    self.trade_type = None
                # Check take profit
                elif self.close[idx] >= self.take_profit:
                    self.position.close()
                    self.trade_type = None

            elif self.trade_type == 'short':
                # Check stop loss
                if self.close[idx] >= self.stop_loss:
                    self.position.close()
                    self.trade_type = None
                # Check take profit
                elif self.close[idx] <= self.take_profit:
                    self.position.close()
                    self.trade_type = None

        else:
            # Look for new trade setup
            breakout_signal = self.check_breakout(idx)

            if breakout_signal == 'long':
                # Calculate position size and stops
                current_atr = self.atr[idx]
                if current_atr > 0:
                    size = self.calculate_position_size()
                    self.buy(size=size)

                    # Set trade parameters
                    self.entry_price = self.close[idx]
                    self.stop_loss = self.entry_price - (current_atr * self.stop_loss_atr)
                    self.take_profit = self.entry_price + (current_atr * self.take_profit_atr)
                    self.trade_type = 'long'

            elif breakout_signal == 'short':
                # Calculate position size and stops
                current_atr = self.atr[idx]
                if current_atr > 0:
                    size = self.calculate_position_size()
                    self.sell(size=size)

                    # Set trade parameters
                    self.entry_price = self.close[idx]
                    self.stop_loss = self.entry_price + (current_atr * self.stop_loss_atr)
                    self.take_profit = self.entry_price - (current_atr * self.take_profit_atr)
                    self.trade_type = 'short'


def run_backtest(data_path, cash=1000000, commission=0.001):
    """Run backtest on a single dataset"""
    try:
        # Load data - handle coinbase format
        df = pd.read_csv(data_path, parse_dates=['datetime'])
        df = df.set_index('datetime')

        # Rename columns to match backtesting.py requirements
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

        # Ensure required columns exist
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required_columns:
            if col not in df.columns:
                print(f"Missing column {col} in {data_path}")
                return None

        # Clean data
        df = df.dropna()
        if len(df) < 100:
            print(f"Insufficient data in {data_path}")
            return None

        # Run backtest
        bt = Backtest(df, SmartMoneyBreakoutBase, cash=cash, commission=commission)
        stats = bt.run()

        return stats

    except Exception as e:
        print(f"Error running backtest on {data_path}: {str(e)}")
        return None


def main():
    # Test with a single dataset first
    data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv"

    if os.path.exists(data_path):
        print("Running Smart Money Breakout Base Strategy Backtest")
        print("=" * 50)

        stats = run_backtest(data_path)

        if stats is not None:
            print(f"\nResults for {os.path.basename(data_path)}:")
            print(stats)

            # Save results
            results_dir = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/backtests/smart_money_breakout/results"
            os.makedirs(results_dir, exist_ok=True)

            # Save summary stats
            summary = pd.DataFrame([{
                'Strategy': 'SmartMoneyBreakoutBase',
                'Dataset': os.path.basename(data_path),
                'Return%': stats['Return [%]'],
                'Sharpe': stats['Sharpe Ratio'],
                'Max_Drawdown%': stats['Max. Drawdown [%]'],
                'Win_Rate%': stats['Win Rate [%]'] if 'Win Rate [%]' in stats else 0,
                'Trades': stats['# Trades'],
                'Exposure%': stats['Exposure Time [%]']
            }])

            summary.to_csv(f"{results_dir}/smart_money_base_single_test.csv", index=False)
            print(f"\nResults saved to {results_dir}/smart_money_base_single_test.csv")
    else:
        print(f"Data file not found: {data_path}")


if __name__ == "__main__":
    main()