import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Order Blocks Momentum Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - optimized for momentum trading
RELEVANT_PERIODS = 6  # Longer periods for stronger momentum
MIN_PERCENT_MOVE = 0.4  # Moderate threshold
USE_WHOLE_RANGE = True  # Use whole range for better zones
LOOKBACK_PERIOD = 40  # Longer lookback for momentum context
POSITION_SIZE = 0.95  # 95% position sizing
TAKE_PROFIT_PERCENT = 3.5  # Balanced TP for momentum
STOP_LOSS_PERCENT = 1.8  # Moderate SL for momentum
ADX_PERIOD = 14  # ADX period for trend strength
ADX_THRESHOLD = 25  # Minimum ADX for strong trend
RSI_PERIOD = 14  # RSI period
MACD_FAST = 12  # MACD fast period
MACD_SLOW = 26  # MACD slow period
MACD_SIGNAL = 9  # MACD signal period

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class OrderBlocksMomentum(Strategy):
    # Strategy parameters
    relevant_periods = RELEVANT_PERIODS
    min_percent_move = MIN_PERCENT_MOVE / 100
    use_whole_range = USE_WHOLE_RANGE
    lookback_period = LOOKBACK_PERIOD
    size = POSITION_SIZE
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    adx_period = ADX_PERIOD
    adx_threshold = ADX_THRESHOLD
    rsi_period = RSI_PERIOD
    macd_fast = MACD_FAST
    macd_slow = MACD_SLOW
    macd_signal = MACD_SIGNAL

    def init(self):
        # Convert data to numpy arrays for faster processing
        self.open_prices = np.array(self.data.Open)
        self.high_prices = np.array(self.data.High)
        self.low_prices = np.array(self.data.Low)
        self.close_prices = np.array(self.data.Close)

        # Order block tracking
        self.bullish_blocks = []  # List of (index, high, low, avg) tuples
        self.bearish_blocks = []  # List of (index, high, low, avg) tuples

        # Momentum indicators
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.plus_di = self.I(talib.PLUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        self.minus_di = self.I(talib.MINUS_DI, self.data.High, self.data.Low, self.data.Close, self.adx_period)

        self.rsi = self.I(talib.RSI, self.data.Close, self.rsi_period)

        self.macd, self.macd_signal_line, self.macd_hist = self.I(
            talib.MACD, self.data.Close, self.macd_fast, self.macd_slow, self.macd_signal
        )

        # Moving averages for trend direction
        self.ema_fast = self.I(talib.EMA, self.data.Close, 21)
        self.ema_slow = self.I(talib.EMA, self.data.Close, 50)

        # ATR for dynamic stops
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)

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

                        # Store the order block
                        self.bullish_blocks.append((bullish_candidate_idx, high_level, low_level, avg_level))

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
                        self.bearish_blocks.append((bearish_candidate_idx, high_level, low_level, avg_level))

    def get_active_order_blocks(self, current_index):
        """
        Get order blocks that are still relevant (within lookback period)
        """
        min_index = max(0, current_index - self.lookback_period)

        active_bullish = [block for block in self.bullish_blocks if block[0] >= min_index]
        active_bearish = [block for block in self.bearish_blocks if block[0] >= min_index]

        return active_bullish, active_bearish

    def price_in_order_block(self, price, block_high, block_low):
        """
        Check if price is within order block zone
        """
        return block_low <= price <= block_high

    def check_bullish_momentum(self):
        """
        Check for strong bullish momentum confluence
        """
        if len(self.adx) < 1 or len(self.plus_di) < 1 or len(self.minus_di) < 1:
            return False
        if len(self.rsi) < 1 or len(self.macd) < 1 or len(self.ema_fast) < 1:
            return False

        # Strong trend with ADX
        strong_trend = self.adx[-1] > self.adx_threshold

        # Bullish directional movement
        bullish_di = self.plus_di[-1] > self.minus_di[-1]

        # RSI in bullish range but not overbought
        rsi_bullish = 45 < self.rsi[-1] < 75

        # MACD bullish
        macd_bullish = self.macd[-1] > self.macd_signal_line[-1]

        # EMA alignment (fast above slow)
        ema_bullish = self.ema_fast[-1] > self.ema_slow[-1]

        # Count confluences (need at least 3 out of 5)
        confluences = sum([strong_trend, bullish_di, rsi_bullish, macd_bullish, ema_bullish])

        return confluences >= 3

    def check_bearish_momentum(self):
        """
        Check for strong bearish momentum confluence
        """
        if len(self.adx) < 1 or len(self.plus_di) < 1 or len(self.minus_di) < 1:
            return False
        if len(self.rsi) < 1 or len(self.macd) < 1 or len(self.ema_fast) < 1:
            return False

        # Strong trend with ADX
        strong_trend = self.adx[-1] > self.adx_threshold

        # Bearish directional movement
        bearish_di = self.minus_di[-1] > self.plus_di[-1]

        # RSI in bearish range but not oversold
        rsi_bearish = 25 < self.rsi[-1] < 55

        # MACD bearish
        macd_bearish = self.macd[-1] < self.macd_signal_line[-1]

        # EMA alignment (fast below slow)
        ema_bearish = self.ema_fast[-1] < self.ema_slow[-1]

        # Count confluences (need at least 3 out of 5)
        confluences = sum([strong_trend, bearish_di, rsi_bearish, macd_bearish, ema_bearish])

        return confluences >= 3

    def next(self):
        current_index = len(self.data) - 1
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]

        # Update order blocks
        self.identify_order_blocks(current_index)

        # Get active order blocks
        active_bullish, active_bearish = self.get_active_order_blocks(current_index)

        # Momentum-based order block trading
        if not self.position:

            # Check for bullish entry at order block with momentum confluence
            for block_idx, block_high, block_low, block_avg in active_bullish:
                if self.price_in_order_block(current_low, block_high, block_low):
                    # Price has touched the bullish order block

                    # Check for strong bullish momentum
                    if self.check_bullish_momentum():
                        # Use ATR-based stops for better risk management
                        atr_value = self.atr[-1] if len(self.atr) > 0 else current_price * 0.02

                        sl_price = current_price - (atr_value * 2)  # 2x ATR stop
                        tp_price = current_price * (1 + self.take_profit)

                        self.buy(size=self.size, sl=sl_price, tp=tp_price)
                        break

            # Check for bearish entry at order block with momentum confluence
            if not self.position:  # Only if we didn't already enter long
                for block_idx, block_high, block_low, block_avg in active_bearish:
                    if self.price_in_order_block(current_high, block_high, block_low):
                        # Price has touched the bearish order block

                        # Check for strong bearish momentum
                        if self.check_bearish_momentum():
                            # Use ATR-based stops for better risk management
                            atr_value = self.atr[-1] if len(self.atr) > 0 else current_price * 0.02

                            sl_price = current_price + (atr_value * 2)  # 2x ATR stop
                            tp_price = current_price * (1 - self.take_profit)

                            self.sell(size=self.size, sl=sl_price, tp=tp_price)
                            break

# Run single backtest (default behavior)
bt = Backtest(data, OrderBlocksMomentum, cash=1000000, commission=0.00045)

print("\n🌙 ===== ORDER BLOCKS MOMENTUM STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Relevant Periods: {RELEVANT_PERIODS}")
print(f"Min Percent Move: {MIN_PERCENT_MOVE}%")
print(f"Use Whole Range: {USE_WHOLE_RANGE}")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Position Size: {POSITION_SIZE}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"ADX Period: {ADX_PERIOD}")
print(f"ADX Threshold: {ADX_THRESHOLD}")
print(f"RSI Period: {RSI_PERIOD}")
print(f"MACD: {MACD_FAST}, {MACD_SLOW}, {MACD_SIGNAL}")

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
    print("TESTING ORDER BLOCKS MOMENTUM STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(OrderBlocksMomentum, 'OrderBlocksMomentum')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/OrderBlocksMomentum.csv")