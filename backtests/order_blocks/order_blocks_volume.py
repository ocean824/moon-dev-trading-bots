import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Order Blocks Volume Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Strategy parameters - optimized for volume confirmation
RELEVANT_PERIODS = 5  # Standard periods for order blocks
MIN_PERCENT_MOVE = 0.3  # Lower threshold with volume confirmation
USE_WHOLE_RANGE = True  # Use whole range for better zones
LOOKBACK_PERIOD = 35  # Moderate lookback period
POSITION_SIZE = 0.95  # 95% position sizing
TAKE_PROFIT_PERCENT = 2.8  # Moderate TP with volume edge
STOP_LOSS_PERCENT = 1.4  # Tight SL with volume confidence
VOLUME_THRESHOLD = 1.8  # Volume must be X times average
VOLUME_PERIOD = 20  # Period for volume calculations
OBV_PERIOD = 14  # On-Balance Volume period for trend
VOLUME_SPIKE = 2.5  # Volume spike threshold for block formation

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class OrderBlocksVolume(Strategy):
    # Strategy parameters
    relevant_periods = RELEVANT_PERIODS
    min_percent_move = MIN_PERCENT_MOVE / 100
    use_whole_range = USE_WHOLE_RANGE
    lookback_period = LOOKBACK_PERIOD
    size = POSITION_SIZE
    take_profit = TAKE_PROFIT_PERCENT / 100
    stop_loss = STOP_LOSS_PERCENT / 100
    volume_threshold = VOLUME_THRESHOLD
    volume_period = VOLUME_PERIOD
    obv_period = OBV_PERIOD
    volume_spike = VOLUME_SPIKE

    def init(self):
        # Convert data to numpy arrays for faster processing
        self.open_prices = np.array(self.data.Open)
        self.high_prices = np.array(self.data.High)
        self.low_prices = np.array(self.data.Low)
        self.close_prices = np.array(self.data.Close)
        self.volume_data = np.array(self.data.Volume)

        # Order block tracking with volume data
        self.bullish_blocks = []  # List of (index, high, low, avg, volume_strength) tuples
        self.bearish_blocks = []  # List of (index, high, low, avg, volume_strength) tuples

        # Volume indicators
        self.volume_sma = self.I(talib.SMA, self.data.Volume, self.volume_period)
        self.obv = self.I(talib.OBV, self.data.Close, self.data.Volume)
        self.obv_sma = self.I(talib.SMA, self.obv, self.obv_period)

        # Price Volume Trend
        self.pvt = self.I(self.calculate_pvt, self.data.Close, self.data.Volume)

        # Volume Weighted Average Price
        self.vwap = self.I(self.calculate_vwap, self.data.High, self.data.Low, self.data.Close, self.data.Volume)

        # ATR for context
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)

    def calculate_pvt(self, close, volume):
        """Calculate Price Volume Trend"""
        pvt = np.zeros_like(close)
        for i in range(1, len(close)):
            pvt[i] = pvt[i-1] + volume[i] * ((close[i] - close[i-1]) / close[i-1])
        return pvt

    def calculate_vwap(self, high, low, close, volume):
        """Calculate Volume Weighted Average Price"""
        typical_price = (high + low + close) / 3
        vwap = np.zeros_like(close)
        cumulative_volume = 0
        cumulative_pv = 0

        for i in range(len(close)):
            cumulative_pv += typical_price[i] * volume[i]
            cumulative_volume += volume[i]
            if cumulative_volume > 0:
                vwap[i] = cumulative_pv / cumulative_volume
            else:
                vwap[i] = typical_price[i]

        return vwap

    def calculate_volume_strength(self, candidate_idx, sequence_end_idx):
        """Calculate volume strength during order block formation"""
        if candidate_idx >= len(self.volume_data) or sequence_end_idx >= len(self.volume_data):
            return 0

        # Volume during the order block formation
        block_volumes = self.volume_data[candidate_idx:sequence_end_idx + 1]
        avg_volume = np.mean(self.volume_data[max(0, candidate_idx - self.volume_period):candidate_idx])

        if avg_volume == 0:
            return 0

        # Calculate average volume strength during block formation
        volume_strength = np.mean(block_volumes) / avg_volume
        return volume_strength

    def identify_order_blocks(self, current_index):
        """
        Identify bullish and bearish order blocks with volume analysis
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
                        # Calculate volume strength during block formation
                        volume_strength = self.calculate_volume_strength(bullish_candidate_idx, current_index - 1)

                        # Only create block if volume was significant
                        if volume_strength >= self.volume_spike:
                            # Define order block levels
                            if self.use_whole_range:
                                high_level = self.high_prices[bullish_candidate_idx]
                                low_level = self.low_prices[bullish_candidate_idx]
                            else:
                                high_level = self.open_prices[bullish_candidate_idx]
                                low_level = self.low_prices[bullish_candidate_idx]

                            avg_level = (high_level + low_level) / 2

                            # Store the order block with volume strength
                            self.bullish_blocks.append((bullish_candidate_idx, high_level, low_level, avg_level, volume_strength))

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
                        # Calculate volume strength during block formation
                        volume_strength = self.calculate_volume_strength(bearish_candidate_idx, current_index - 1)

                        # Only create block if volume was significant
                        if volume_strength >= self.volume_spike:
                            # Define order block levels
                            if self.use_whole_range:
                                high_level = self.high_prices[bearish_candidate_idx]
                                low_level = self.low_prices[bearish_candidate_idx]
                            else:
                                high_level = self.high_prices[bearish_candidate_idx]
                                low_level = self.open_prices[bearish_candidate_idx]

                            avg_level = (high_level + low_level) / 2

                            # Store the order block with volume strength
                            self.bearish_blocks.append((bearish_candidate_idx, high_level, low_level, avg_level, volume_strength))

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

    def check_volume_confirmation(self):
        """
        Check current volume for trade confirmation
        """
        if len(self.volume_sma) < 1:
            return False

        current_volume = self.data.Volume[-1]
        avg_volume = self.volume_sma[-1]

        return current_volume >= avg_volume * self.volume_threshold

    def check_obv_confluence(self, direction):
        """
        Check On-Balance Volume for directional confluence
        """
        if len(self.obv) < 2 or len(self.obv_sma) < 1:
            return False

        obv_trend = self.obv[-1] > self.obv[-2]  # OBV rising
        obv_above_average = self.obv[-1] > self.obv_sma[-1]

        if direction == 'long':
            return obv_trend and obv_above_average
        elif direction == 'short':
            return not obv_trend and not obv_above_average

        return False

    def check_pvt_confluence(self, direction):
        """
        Check Price Volume Trend for confluence
        """
        if len(self.pvt) < 2:
            return False

        pvt_trend = self.pvt[-1] > self.pvt[-2]

        if direction == 'long':
            return pvt_trend  # PVT should be rising for bullish
        elif direction == 'short':
            return not pvt_trend  # PVT should be falling for bearish

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

        # Volume-confirmed order block trading
        if not self.position:

            # Check for bullish entry with volume confirmation
            for block_data in active_bullish:
                block_idx, block_high, block_low, block_avg, volume_strength = block_data

                if self.price_in_order_block(current_low, block_high, block_low):
                    # Price has touched the bullish order block

                    # Multiple volume confirmations
                    volume_confirmed = self.check_volume_confirmation()
                    obv_confirmed = self.check_obv_confluence('long')
                    pvt_confirmed = self.check_pvt_confluence('long')

                    # Higher volume strength blocks get priority
                    strength_bonus = volume_strength > 3.0

                    # Need at least 2 volume confirmations, or 1 with high strength
                    confirmations = sum([volume_confirmed, obv_confirmed, pvt_confirmed])

                    if confirmations >= 2 or (confirmations >= 1 and strength_bonus):
                        sl_price = current_price * (1 - self.stop_loss)
                        tp_price = current_price * (1 + self.take_profit)

                        self.buy(size=self.size, sl=sl_price, tp=tp_price)
                        break

            # Check for bearish entry with volume confirmation
            if not self.position:  # Only if we didn't already enter long
                for block_data in active_bearish:
                    block_idx, block_high, block_low, block_avg, volume_strength = block_data

                    if self.price_in_order_block(current_high, block_high, block_low):
                        # Price has touched the bearish order block

                        # Multiple volume confirmations
                        volume_confirmed = self.check_volume_confirmation()
                        obv_confirmed = self.check_obv_confluence('short')
                        pvt_confirmed = self.check_pvt_confluence('short')

                        # Higher volume strength blocks get priority
                        strength_bonus = volume_strength > 3.0

                        # Need at least 2 volume confirmations, or 1 with high strength
                        confirmations = sum([volume_confirmed, obv_confirmed, pvt_confirmed])

                        if confirmations >= 2 or (confirmations >= 1 and strength_bonus):
                            sl_price = current_price * (1 + self.stop_loss)
                            tp_price = current_price * (1 - self.take_profit)

                            self.sell(size=self.size, sl=sl_price, tp=tp_price)
                            break

# Run single backtest (default behavior)
bt = Backtest(data, OrderBlocksVolume, cash=1000000, commission=0.00045)

print("\n🌙 ===== ORDER BLOCKS VOLUME STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Relevant Periods: {RELEVANT_PERIODS}")
print(f"Min Percent Move: {MIN_PERCENT_MOVE}%")
print(f"Use Whole Range: {USE_WHOLE_RANGE}")
print(f"Lookback Period: {LOOKBACK_PERIOD}")
print(f"Position Size: {POSITION_SIZE}")
print(f"Take Profit: {TAKE_PROFIT_PERCENT}%")
print(f"Stop Loss: {STOP_LOSS_PERCENT}%")
print(f"Volume Threshold: {VOLUME_THRESHOLD}x")
print(f"Volume Period: {VOLUME_PERIOD}")
print(f"Volume Spike: {VOLUME_SPIKE}x")
print(f"OBV Period: {OBV_PERIOD}")

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
    print("TESTING ORDER BLOCKS VOLUME STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(OrderBlocksVolume, 'OrderBlocksVolume')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/OrderBlocksVolume.csv")