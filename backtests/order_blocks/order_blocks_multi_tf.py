import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Order Blocks Multi-Timeframe Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - optimized for multi-timeframe analysis
RELEVANT_PERIODS = 5  # Standard periods for order blocks
MIN_PERCENT_MOVE = 0.4  # Moderate threshold for quality blocks
USE_WHOLE_RANGE = True  # Use whole range for better zones
LOOKBACK_PERIOD = 50  # Longer lookback for HTF context
POSITION_SIZE = 0.95  # 95% position sizing
TAKE_PROFIT_PERCENT = 3.2  # Higher TP with HTF edge
STOP_LOSS_PERCENT = 1.6  # Moderate SL with HTF protection
HTF_MULTIPLIER = 4  # Higher timeframe multiplier (4x current TF)
HTF_TREND_PERIOD = 50  # Period for HTF trend analysis
LTF_CONFIRMATION = True  # Require lower timeframe confirmation

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class OrderBlocksMultiTF(Strategy):
    # Strategy parameters
    relevant_periods = RELEVANT_PERIODS
    min_percent_move = MIN_PERCENT_MOVE / 100
    use_whole_range = USE_WHOLE_RANGE
    lookback_period = LOOKBACK_PERIOD
    size = POSITION_SIZE
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    htf_multiplier = HTF_MULTIPLIER
    htf_trend_period = HTF_TREND_PERIOD
    ltf_confirmation = LTF_CONFIRMATION

    def init(self):
        # Convert data to numpy arrays for faster processing
        self.open_prices = np.array(self.data.Open)
        self.high_prices = np.array(self.data.High)
        self.low_prices = np.array(self.data.Low)
        self.close_prices = np.array(self.data.Close)

        # Order block tracking for current timeframe
        self.bullish_blocks = []  # List of (index, high, low, avg, tf) tuples
        self.bearish_blocks = []  # List of (index, high, low, avg, tf) tuples

        # Higher timeframe order blocks
        self.htf_bullish_blocks = []
        self.htf_bearish_blocks = []

        # Multi-timeframe trend indicators
        # Current timeframe
        self.ema_fast = self.I(talib.EMA, self.data.Close, 21)
        self.ema_slow = self.I(talib.EMA, self.data.Close, 50)
        self.rsi = self.I(talib.RSI, self.data.Close, 14)

        # Higher timeframe indicators (simulated by longer periods)
        self.htf_ema_fast = self.I(talib.EMA, self.data.Close, 21 * self.htf_multiplier)
        self.htf_ema_slow = self.I(talib.EMA, self.data.Close, 50 * self.htf_multiplier)
        self.htf_rsi = self.I(talib.RSI, self.data.Close, 14 * self.htf_multiplier)

        # Market structure indicators
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, 14)

        # Track HTF analysis
        self.last_htf_analysis = 0

    def create_htf_data(self, current_index):
        """
        Create higher timeframe data by aggregating current timeframe
        """
        if current_index < self.htf_multiplier * 10:
            return None

        # Calculate how many HTF candles we can create
        htf_periods = current_index // self.htf_multiplier

        if htf_periods < 10:
            return None

        htf_data = []
        for i in range(htf_periods):
            start_idx = i * self.htf_multiplier
            end_idx = min(start_idx + self.htf_multiplier, current_index)

            if end_idx > start_idx:
                htf_open = self.open_prices[start_idx]
                htf_high = np.max(self.high_prices[start_idx:end_idx])
                htf_low = np.min(self.low_prices[start_idx:end_idx])
                htf_close = self.close_prices[end_idx - 1]

                htf_data.append({
                    'index': end_idx - 1,  # Index of the closing candle
                    'open': htf_open,
                    'high': htf_high,
                    'low': htf_low,
                    'close': htf_close
                })

        return htf_data

    def identify_htf_order_blocks(self, htf_data):
        """
        Identify order blocks on higher timeframe data
        """
        if not htf_data or len(htf_data) < self.relevant_periods + 1:
            return

        # Clear old HTF blocks
        self.htf_bullish_blocks = []
        self.htf_bearish_blocks = []

        for i in range(self.relevant_periods, len(htf_data)):
            candidate_idx = i - self.relevant_periods

            # Check for Bullish Order Block on HTF
            candidate = htf_data[candidate_idx]
            if candidate['close'] < candidate['open']:  # Red candle

                # Check if next N candles are green
                all_up = True
                for j in range(1, self.relevant_periods + 1):
                    next_candle = htf_data[candidate_idx + j]
                    if next_candle['close'] <= next_candle['open']:
                        all_up = False
                        break

                if all_up:
                    # Calculate price move
                    start_price = candidate['close']
                    end_price = htf_data[i - 1]['close']
                    percent_move = (end_price - start_price) / start_price

                    if percent_move >= self.min_percent_move:
                        # Define HTF order block levels
                        high_level = candidate['high']
                        low_level = candidate['low']
                        avg_level = (high_level + low_level) / 2

                        self.htf_bullish_blocks.append((candidate['index'], high_level, low_level, avg_level, 'HTF'))

            # Check for Bearish Order Block on HTF
            if candidate['close'] > candidate['open']:  # Green candle

                # Check if next N candles are red
                all_down = True
                for j in range(1, self.relevant_periods + 1):
                    next_candle = htf_data[candidate_idx + j]
                    if next_candle['close'] >= next_candle['open']:
                        all_down = False
                        break

                if all_down:
                    # Calculate price move
                    start_price = candidate['close']
                    end_price = htf_data[i - 1]['close']
                    percent_move = (start_price - end_price) / start_price

                    if percent_move >= self.min_percent_move:
                        # Define HTF order block levels
                        high_level = candidate['high']
                        low_level = candidate['low']
                        avg_level = (high_level + low_level) / 2

                        self.htf_bearish_blocks.append((candidate['index'], high_level, low_level, avg_level, 'HTF'))

    def identify_order_blocks(self, current_index):
        """
        Identify bullish and bearish order blocks on current timeframe
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

                        # Store the order block
                        self.bullish_blocks.append((bullish_candidate_idx, high_level, low_level, avg_level, 'CTF'))

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

                        # Store the order block
                        self.bearish_blocks.append((bearish_candidate_idx, high_level, low_level, avg_level, 'CTF'))

    def get_active_order_blocks(self, current_index):
        """
        Get order blocks that are still relevant (within lookback period)
        """
        min_index = max(0, current_index - self.lookback_period)

        # Current timeframe blocks
        active_bullish = [block for block in self.bullish_blocks if block[0] >= min_index]
        active_bearish = [block for block in self.bearish_blocks if block[0] >= min_index]

        # Higher timeframe blocks (longer lookback)
        htf_min_index = max(0, current_index - self.lookback_period * 2)
        active_htf_bullish = [block for block in self.htf_bullish_blocks if block[0] >= htf_min_index]
        active_htf_bearish = [block for block in self.htf_bearish_blocks if block[0] >= htf_min_index]

        return active_bullish, active_bearish, active_htf_bullish, active_htf_bearish

    def price_in_order_block(self, price, block_high, block_low):
        """
        Check if price is within order block zone
        """
        return block_low <= price <= block_high

    def check_htf_trend_alignment(self, direction):
        """
        Check if higher timeframe trend aligns with trade direction
        """
        if len(self.htf_ema_fast) < 1 or len(self.htf_ema_slow) < 1:
            return False

        htf_bullish = self.htf_ema_fast[-1] > self.htf_ema_slow[-1]

        if direction == 'long':
            return htf_bullish
        elif direction == 'short':
            return not htf_bullish

        return False

    def check_multi_tf_confluence(self, direction):
        """
        Check for multi-timeframe confluence
        """
        if len(self.rsi) < 1 or len(self.htf_rsi) < 1:
            return False

        current_rsi = self.rsi[-1]
        htf_rsi = self.htf_rsi[-1]

        if direction == 'long':
            # For bullish: Current TF not overbought, HTF in bullish territory
            return current_rsi < 70 and htf_rsi > 40
        elif direction == 'short':
            # For bearish: Current TF not oversold, HTF in bearish territory
            return current_rsi > 30 and htf_rsi < 60

        return False

    def next(self):
        current_index = len(self.data) - 1
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]

        # Update HTF analysis periodically
        if current_index - self.last_htf_analysis >= self.htf_multiplier:
            htf_data = self.create_htf_data(current_index)
            if htf_data:
                self.identify_htf_order_blocks(htf_data)
            self.last_htf_analysis = current_index

        # Update current timeframe order blocks
        self.identify_order_blocks(current_index)

        # Get active order blocks from both timeframes
        active_bullish, active_bearish, active_htf_bullish, active_htf_bearish = self.get_active_order_blocks(current_index)

        # Multi-timeframe order block trading
        if not self.position:

            # Priority 1: HTF bullish blocks with CTF confluence
            for block_idx, block_high, block_low, block_avg, timeframe in active_htf_bullish:
                if self.price_in_order_block(current_low, block_high, block_low):
                    # Check HTF trend alignment and multi-TF confluence
                    if self.check_htf_trend_alignment('long') and self.check_multi_tf_confluence('long'):
                        # Higher TP/wider SL for HTF blocks
                        sl_price = current_price * (1 - self.stop_loss * 1.2)
                        tp_price = current_price * (1 + self.take_profit * 1.3)

                        self.buy(size=self.size, sl=sl_price, tp=tp_price)
                        break

            # Priority 2: CTF bullish blocks with HTF alignment
            if not self.position:
                for block_idx, block_high, block_low, block_avg, timeframe in active_bullish:
                    if self.price_in_order_block(current_low, block_high, block_low):
                        # Check HTF alignment
                        if self.check_htf_trend_alignment('long') and self.check_multi_tf_confluence('long'):
                            sl_price = current_price * (1 - self.stop_loss)
                            tp_price = current_price * (1 + self.take_profit)

                            self.buy(size=self.size, sl=sl_price, tp=tp_price)
                            break

            # Priority 3: HTF bearish blocks with CTF confluence
            if not self.position:
                for block_idx, block_high, block_low, block_avg, timeframe in active_htf_bearish:
                    if self.price_in_order_block(current_high, block_high, block_low):
                        # Check HTF trend alignment and multi-TF confluence
                        if self.check_htf_trend_alignment('short') and self.check_multi_tf_confluence('short'):
                            # Higher TP/wider SL for HTF blocks
                            sl_price = current_price * (1 + self.stop_loss * 1.2)
                            tp_price = current_price * (1 - self.take_profit * 1.3)

                            self.sell(size=self.size, sl=sl_price, tp=tp_price)
                            break

            # Priority 4: CTF bearish blocks with HTF alignment
            if not self.position:
                for block_idx, block_high, block_low, block_avg, timeframe in active_bearish:
                    if self.price_in_order_block(current_high, block_high, block_low):
                        # Check HTF alignment
                        if self.check_htf_trend_alignment('short') and self.check_multi_tf_confluence('short'):
                            sl_price = current_price * (1 + self.stop_loss)
                            tp_price = current_price * (1 - self.take_profit)

                            self.sell(size=self.size, sl=sl_price, tp=tp_price)
                            break

# Run single backtest (default behavior)
bt = Backtest(data, OrderBlocksMultiTF, cash=1000000, commission=0.00045)

print("\n🌙 ===== ORDER BLOCKS MULTI-TIMEFRAME STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Relevant Periods: {RELEVANT_PERIODS}")
print(f"Min Percent Move: {MIN_PERCENT_MOVE}%")
print(f"Use Whole Range: {USE_WHOLE_RANGE}")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Position Size: {POSITION_SIZE}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"HTF Multiplier: {HTF_MULTIPLIER}x")
print(f"HTF Trend Period: {HTF_TREND_PERIOD}")
print(f"LTF Confirmation: {LTF_CONFIRMATION}")

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
    print("TESTING ORDER BLOCKS MULTI-TIMEFRAME STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(OrderBlocksMultiTF, 'OrderBlocksMultiTF')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/OrderBlocksMultiTF.csv")