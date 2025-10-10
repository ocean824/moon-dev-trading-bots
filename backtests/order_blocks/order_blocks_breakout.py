import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Order Blocks Breakout Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - optimized for breakout trading
RELEVANT_PERIODS = 4  # Shorter periods for faster breakouts
MIN_PERCENT_MOVE = 0.3  # Lower threshold to catch more blocks
USE_WHOLE_RANGE = True  # Use whole range for better zones
LOOKBACK_PERIOD = 25  # Shorter lookback for fresher blocks
POSITION_SIZE = 0.95  # 95% position sizing
TAKE_PROFIT_PERCENT = 4.0  # Higher TP for breakouts
STOP_LOSS_PERCENT = 1.5  # Moderate SL for breakouts
BREAKOUT_THRESHOLD = 0.2  # % above/below block for breakout confirmation
VOLUME_MULTIPLIER = 1.5  # Volume should be X times average
VOLUME_PERIOD = 20  # Period for volume average

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class OrderBlocksBreakout(Strategy):
    # Strategy parameters
    relevant_periods = RELEVANT_PERIODS
    min_percent_move = MIN_PERCENT_MOVE / 100
    use_whole_range = USE_WHOLE_RANGE
    lookback_period = LOOKBACK_PERIOD
    size = POSITION_SIZE
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    breakout_threshold = BREAKOUT_THRESHOLD / 100
    volume_multiplier = VOLUME_MULTIPLIER
    volume_period = VOLUME_PERIOD

    def init(self):
        # Convert data to numpy arrays for faster processing
        self.open_prices = np.array(self.data.Open)
        self.high_prices = np.array(self.data.High)
        self.low_prices = np.array(self.data.Low)
        self.close_prices = np.array(self.data.Close)
        self.volume_data = np.array(self.data.Volume)

        # Order block tracking
        self.bullish_blocks = []  # List of (index, high, low, avg) tuples
        self.bearish_blocks = []  # List of (index, high, low, avg) tuples

        # Technical indicators for confluence
        self.volume_sma = self.I(talib.SMA, self.data.Volume, self.volume_period)
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)

        # Momentum indicators for breakout confirmation
        self.macd, self.macd_signal, self.macd_hist = self.I(talib.MACD, self.data.Close, 12, 26, 9)
        self.rsi = self.I(talib.RSI, self.data.Close, 14)

        # Track broken order blocks to avoid re-entry
        self.broken_bullish_blocks = set()
        self.broken_bearish_blocks = set()

    def identify_order_blocks(self, current_index):
        """
        Identify bullish and bearish order blocks based on Pine Script logic
        """
        if current_index < self.relevant_periods + 1:
            return

        # Check for Bullish Order Block
        bullish_candidate_idx = current_index - self.relevant_periods

        if bullish_candidate_idx > 0:
            # Check if candidate candle is down (red)
            if (self.close_prices[bullish_candidate_idx] < self.open_prices[bullish_candidate_idx]):

                # Check if next N candles are up (green)
                all_up = True
                for i in range(1, self.relevant_periods + 1):
                    idx = bullish_candidate_idx + i
                    if idx >= len(self.close_prices) or self.close_prices[idx] <= self.open_prices[idx]:
                        all_up = False
                        break

                if all_up:
                    # Calculate price move
                    start_price = self.close_prices[bullish_candidate_idx]
                    end_price = self.close_prices[current_index - 1]
                    percent_move = (end_price - start_price) / start_price

                    if percent_move >= self.min_percent_move:
                        # Define order block levels
                        if self.use_whole_range:
                            high_level = self.high_prices[bullish_candidate_idx]
                            low_level = self.low_prices[bullish_candidate_idx]
                        else:
                            high_level = self.open_prices[bullish_candidate_idx]
                            low_level = self.low_prices[bullish_candidate_idx]

                        avg_level = (high_level + low_level) / 2

                        # Store the order block with unique ID
                        block_id = f"bull_{bullish_candidate_idx}_{high_level:.2f}_{low_level:.2f}"
                        self.bullish_blocks.append((bullish_candidate_idx, high_level, low_level, avg_level, block_id))

        # Check for Bearish Order Block
        bearish_candidate_idx = current_index - self.relevant_periods

        if bearish_candidate_idx > 0:
            # Check if candidate candle is up (green)
            if (self.close_prices[bearish_candidate_idx] > self.open_prices[bearish_candidate_idx]):

                # Check if next N candles are down (red)
                all_down = True
                for i in range(1, self.relevant_periods + 1):
                    idx = bearish_candidate_idx + i
                    if idx >= len(self.close_prices) or self.close_prices[idx] >= self.open_prices[idx]:
                        all_down = False
                        break

                if all_down:
                    # Calculate price move
                    start_price = self.close_prices[bearish_candidate_idx]
                    end_price = self.close_prices[current_index - 1]
                    percent_move = (start_price - end_price) / start_price

                    if percent_move >= self.min_percent_move:
                        # Define order block levels
                        if self.use_whole_range:
                            high_level = self.high_prices[bearish_candidate_idx]
                            low_level = self.low_prices[bearish_candidate_idx]
                        else:
                            high_level = self.high_prices[bearish_candidate_idx]
                            low_level = self.open_prices[bearish_candidate_idx]

                        avg_level = (high_level + low_level) / 2

                        # Store the order block with unique ID
                        block_id = f"bear_{bearish_candidate_idx}_{high_level:.2f}_{low_level:.2f}"
                        self.bearish_blocks.append((bearish_candidate_idx, high_level, low_level, avg_level, block_id))

    def get_active_order_blocks(self, current_index):
        """
        Get order blocks that are still relevant (within lookback period)
        """
        min_index = max(0, current_index - self.lookback_period)

        active_bullish = [block for block in self.bullish_blocks if block[0] >= min_index]
        active_bearish = [block for block in self.bearish_blocks if block[0] >= min_index]

        return active_bullish, active_bearish

    def check_volume_confirmation(self):
        """
        Check if current volume supports the breakout
        """
        if len(self.volume_sma) < 1:
            return False

        current_volume = self.data.Volume[-1]
        avg_volume = self.volume_sma[-1]

        return current_volume >= avg_volume * self.volume_multiplier

    def check_momentum_confirmation(self, direction):
        """
        Check momentum indicators for breakout confirmation
        """
        if len(self.macd) < 2 or len(self.rsi) < 1:
            return False

        current_macd = self.macd[-1]
        current_rsi = self.rsi[-1]

        if direction == 'long':
            # For bullish breakout: MACD should be positive or turning up, RSI not overbought
            return current_macd > 0 and current_rsi < 75
        elif direction == 'short':
            # For bearish breakout: MACD should be negative or turning down, RSI not oversold
            return current_macd < 0 and current_rsi > 25

        return False

    def next(self):
        current_index = len(self.data) - 1
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]

        # Update order blocks
        self.identify_order_blocks(current_index)

        # Get active order blocks
        active_bullish, active_bearish = self.get_active_order_blocks(current_index)

        # Breakout trading logic
        if not self.position:

            # Check for bullish breakout above bearish order blocks
            for block_data in active_bearish:
                if len(block_data) == 5:
                    block_idx, block_high, block_low, block_avg, block_id = block_data
                else:
                    block_idx, block_high, block_low, block_avg = block_data
                    block_id = f"bear_{block_idx}_{block_high:.2f}_{block_low:.2f}"

                # Skip if already broken
                if block_id in self.broken_bearish_blocks:
                    continue

                # Check for breakout above bearish block
                breakout_level = block_high * (1 + self.breakout_threshold)
                if current_price > breakout_level:
                    # Confirm with volume and momentum
                    if self.check_volume_confirmation() and self.check_momentum_confirmation('long'):
                        sl_price = block_high  # Stop at the broken level
                        tp_price = current_price * (1 + self.take_profit)

                        self.buy(size=self.size, sl=sl_price, tp=tp_price)
                        self.broken_bearish_blocks.add(block_id)
                        break

            # Check for bearish breakout below bullish order blocks
            if not self.position:  # Only if we didn't already enter long
                for block_data in active_bullish:
                    if len(block_data) == 5:
                        block_idx, block_high, block_low, block_avg, block_id = block_data
                    else:
                        block_idx, block_high, block_low, block_avg = block_data
                        block_id = f"bull_{block_idx}_{block_high:.2f}_{block_low:.2f}"

                    # Skip if already broken
                    if block_id in self.broken_bullish_blocks:
                        continue

                    # Check for breakout below bullish block
                    breakout_level = block_low * (1 - self.breakout_threshold)
                    if current_price < breakout_level:
                        # Confirm with volume and momentum
                        if self.check_volume_confirmation() and self.check_momentum_confirmation('short'):
                            sl_price = block_low  # Stop at the broken level
                            tp_price = current_price * (1 - self.take_profit)

                            self.sell(size=self.size, sl=sl_price, tp=tp_price)
                            self.broken_bullish_blocks.add(block_id)
                            break

# Run single backtest (default behavior)
bt = Backtest(data, OrderBlocksBreakout, cash=1000000, commission=0.00045)

print("\n🌙 ===== ORDER BLOCKS BREAKOUT STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Relevant Periods: {RELEVANT_PERIODS}")
print(f"Min Percent Move: {MIN_PERCENT_MOVE}%")
print(f"Use Whole Range: {USE_WHOLE_RANGE}")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Position Size: {POSITION_SIZE}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Breakout Threshold: {BREAKOUT_THRESHOLD}%")
print(f"Volume Multiplier: {VOLUME_MULTIPLIER}x")
print(f"Volume Period: {VOLUME_PERIOD}")

stats_default = bt.run()
print(stats_default)

# Show plot for visualization
try:
    bt.plot()
except Exception as e:
    print(f"Plot error: {e}")

# TEST ON ALL DATA SOURCES
if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING ORDER BLOCKS BREAKOUT STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(OrderBlocksBreakout, 'OrderBlocksBreakout')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/OrderBlocksBreakout.csv")