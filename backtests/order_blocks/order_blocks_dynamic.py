import pandas as pd
import numpy as np
import talib
from backtesting import Backtest, Strategy

print("🚀 Moon Dev's Order Blocks Dynamic Strategy Loading... 🌙")

# Data configuration for single backtest
DATA_PATH = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv'

# Base strategy parameters - dynamically adjusted
BASE_RELEVANT_PERIODS = 5  # Base periods for order blocks
BASE_MIN_PERCENT_MOVE = 0.3  # Base threshold
USE_WHOLE_RANGE = True  # Use whole range for better zones
BASE_LOOKBACK_PERIOD = 40  # Base lookback period
POSITION_SIZE = 0.95  # 95% position sizing
BASE_TAKE_PROFIT_PERCENT = 2.5  # Base TP
BASE_STOP_LOSS_PERCENT = 1.5  # Base SL
VOLATILITY_PERIOD = 20  # Period for volatility calculation
VOLATILITY_THRESHOLD_LOW = 0.02  # Low volatility threshold (2%)
VOLATILITY_THRESHOLD_HIGH = 0.06  # High volatility threshold (6%)

print(f"📊 Loading data from: {DATA_PATH}")
data = pd.read_csv(DATA_PATH, parse_dates=['datetime'], index_col='datetime')
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
data = data.sort_index()
data = data.dropna()
print(f"✅ Data loaded! {len(data)} rows 🌙")

class OrderBlocksDynamic(Strategy):
    # Base strategy parameters
    base_relevant_periods = BASE_RELEVANT_PERIODS
    base_min_percent_move = BASE_MIN_PERCENT_MOVE / 100
    use_whole_range = USE_WHOLE_RANGE
    base_lookback_period = BASE_LOOKBACK_PERIOD
    size = POSITION_SIZE
    base_take_profit = BASE_TAKE_PROFIT_PERCENT / 100
    base_stop_loss = BASE_STOP_LOSS_PERCENT / 100
    volatility_period = VOLATILITY_PERIOD
    vol_threshold_low = VOLATILITY_THRESHOLD_LOW
    vol_threshold_high = VOLATILITY_THRESHOLD_HIGH

    def init(self):
        # Convert data to numpy arrays for faster processing
        self.open_prices = np.array(self.data.Open)
        self.high_prices = np.array(self.data.High)
        self.low_prices = np.array(self.data.Low)
        self.close_prices = np.array(self.data.Close)

        # Order block tracking
        self.bullish_blocks = []  # List of (index, high, low, avg, strength) tuples
        self.bearish_blocks = []  # List of (index, high, low, avg, strength) tuples

        # Volatility indicators
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, 14)
        self.atr_percentage = self.I(self.calculate_atr_percentage, self.data.Close, self.atr)

        # Rolling volatility
        self.returns = self.I(self.calculate_returns, self.data.Close)
        self.volatility = self.I(self.calculate_rolling_volatility, self.returns, self.volatility_period)

        # Market regime indicators
        self.bb_upper, self.bb_middle, self.bb_lower = self.I(
            talib.BBANDS, self.data.Close, 20, 2, 2
        )
        self.bb_width = self.I(self.calculate_bb_width, self.bb_upper, self.bb_lower, self.bb_middle)

        # Trend strength
        self.adx = self.I(talib.ADX, self.data.High, self.data.Low, self.data.Close, 14)

        # Dynamic parameters tracking
        self.current_relevant_periods = self.base_relevant_periods
        self.current_min_percent_move = self.base_min_percent_move
        self.current_lookback_period = self.base_lookback_period
        self.current_take_profit = self.base_take_profit
        self.current_stop_loss = self.base_stop_loss

    def calculate_atr_percentage(self, close, atr):
        """Calculate ATR as percentage of close price"""
        return (atr / close) * 100

    def calculate_returns(self, close):
        """Calculate period returns"""
        returns = np.zeros_like(close)
        for i in range(1, len(close)):
            returns[i] = (close[i] - close[i-1]) / close[i-1]
        return returns

    def calculate_rolling_volatility(self, returns, period):
        """Calculate rolling volatility"""
        volatility = np.zeros_like(returns)
        for i in range(period, len(returns)):
            volatility[i] = np.std(returns[i-period:i]) * np.sqrt(252)  # Annualized
        return volatility

    def calculate_bb_width(self, bb_upper, bb_lower, bb_middle):
        """Calculate Bollinger Band width as % of middle band"""
        return ((bb_upper - bb_lower) / bb_middle) * 100

    def get_market_regime(self):
        """
        Determine current market regime based on volatility and trend
        Returns: 'low_vol', 'high_vol', 'trending', 'ranging'
        """
        if len(self.volatility) < 1 or len(self.bb_width) < 1 or len(self.adx) < 1:
            return 'ranging'

        current_vol = self.volatility[-1]
        current_bb_width = self.bb_width[-1]
        current_adx = self.adx[-1]

        # Determine volatility regime
        if current_vol < self.vol_threshold_low:
            vol_regime = 'low_vol'
        elif current_vol > self.vol_threshold_high:
            vol_regime = 'high_vol'
        else:
            vol_regime = 'normal_vol'

        # Determine trend regime
        if current_adx > 25:
            trend_regime = 'trending'
        else:
            trend_regime = 'ranging'

        # Combine regimes
        if vol_regime == 'low_vol' and trend_regime == 'ranging':
            return 'low_vol_ranging'
        elif vol_regime == 'low_vol' and trend_regime == 'trending':
            return 'low_vol_trending'
        elif vol_regime == 'high_vol' and trend_regime == 'ranging':
            return 'high_vol_ranging'
        elif vol_regime == 'high_vol' and trend_regime == 'trending':
            return 'high_vol_trending'
        else:
            return 'normal'

    def adapt_parameters(self, market_regime):
        """
        Adapt strategy parameters based on market regime
        """
        if market_regime == 'low_vol_ranging':
            # Tighter parameters for low volatility ranging markets
            self.current_relevant_periods = max(3, self.base_relevant_periods - 2)
            self.current_min_percent_move = self.base_min_percent_move * 0.5
            self.current_lookback_period = self.base_lookback_period // 2
            self.current_take_profit = self.base_take_profit * 0.6
            self.current_stop_loss = self.base_stop_loss * 0.7

        elif market_regime == 'low_vol_trending':
            # Slightly tighter parameters for low volatility trending
            self.current_relevant_periods = self.base_relevant_periods - 1
            self.current_min_percent_move = self.base_min_percent_move * 0.7
            self.current_lookback_period = int(self.base_lookback_period * 0.8)
            self.current_take_profit = self.base_take_profit * 0.8
            self.current_stop_loss = self.base_stop_loss * 0.8

        elif market_regime == 'high_vol_ranging':
            # Wider parameters for high volatility ranging
            self.current_relevant_periods = self.base_relevant_periods + 1
            self.current_min_percent_move = self.base_min_percent_move * 1.5
            self.current_lookback_period = int(self.base_lookback_period * 0.7)
            self.current_take_profit = self.base_take_profit * 1.5
            self.current_stop_loss = self.base_stop_loss * 1.8

        elif market_regime == 'high_vol_trending':
            # Balanced parameters for high volatility trending
            self.current_relevant_periods = self.base_relevant_periods + 2
            self.current_min_percent_move = self.base_min_percent_move * 1.2
            self.current_lookback_period = self.base_lookback_period
            self.current_take_profit = self.base_take_profit * 1.8
            self.current_stop_loss = self.base_stop_loss * 1.5

        else:  # normal market
            # Use base parameters
            self.current_relevant_periods = self.base_relevant_periods
            self.current_min_percent_move = self.base_min_percent_move
            self.current_lookback_period = self.base_lookback_period
            self.current_take_profit = self.base_take_profit
            self.current_stop_loss = self.base_stop_loss

    def identify_order_blocks(self, current_index):
        """
        Identify bullish and bearish order blocks with dynamic parameters
        """
        if current_index < self.current_relevant_periods + 1:
            return

        # Check for Bullish Order Block
        bullish_candidate_idx = current_index - self.current_relevant_periods

        if bullish_candidate_idx > 0:
            # Check if candidate candle is down (red)
            if (self.close_prices[bullish_candidate_idx] < self.open_prices[bullish_candidate_idx]):

                # Check if next N candles are up (green)
                all_up = True
                for i in range(1, self.current_relevant_periods + 1):
                    idx = bullish_candidate_idx + i
                    if idx >= len(self.close_prices) or self.close_prices[idx] <= self.open_prices[idx]:
                        all_up = False
                        break

                if all_up:
                    # Calculate price move
                    start_price = self.close_prices[bullish_candidate_idx]
                    end_price = self.close_prices[current_index - 1]
                    percent_move = (end_price - start_price) / start_price

                    if percent_move >= self.current_min_percent_move:
                        # Define order block levels
                        if self.use_whole_range:
                            high_level = self.high_prices[bullish_candidate_idx]
                            low_level = self.low_prices[bullish_candidate_idx]
                        else:
                            high_level = self.open_prices[bullish_candidate_idx]
                            low_level = self.low_prices[bullish_candidate_idx]

                        avg_level = (high_level + low_level) / 2

                        # Calculate block strength based on price move and volatility
                        vol_factor = self.volatility[-1] if len(self.volatility) > 0 else 0.03
                        strength = percent_move / vol_factor

                        # Store the order block
                        self.bullish_blocks.append((bullish_candidate_idx, high_level, low_level, avg_level, strength))

        # Check for Bearish Order Block
        bearish_candidate_idx = current_index - self.current_relevant_periods

        if bearish_candidate_idx > 0:
            # Check if candidate candle is up (green)
            if (self.close_prices[bearish_candidate_idx] > self.open_prices[bearish_candidate_idx]):

                # Check if next N candles are down (red)
                all_down = True
                for i in range(1, self.current_relevant_periods + 1):
                    idx = bearish_candidate_idx + i
                    if idx >= len(self.close_prices) or self.close_prices[idx] >= self.open_prices[idx]:
                        all_down = False
                        break

                if all_down:
                    # Calculate price move
                    start_price = self.close_prices[bearish_candidate_idx]
                    end_price = self.close_prices[current_index - 1]
                    percent_move = (start_price - end_price) / start_price

                    if percent_move >= self.current_min_percent_move:
                        # Define order block levels
                        if self.use_whole_range:
                            high_level = self.high_prices[bearish_candidate_idx]
                            low_level = self.low_prices[bearish_candidate_idx]
                        else:
                            high_level = self.high_prices[bearish_candidate_idx]
                            low_level = self.open_prices[bearish_candidate_idx]

                        avg_level = (high_level + low_level) / 2

                        # Calculate block strength
                        vol_factor = self.volatility[-1] if len(self.volatility) > 0 else 0.03
                        strength = percent_move / vol_factor

                        # Store the order block
                        self.bearish_blocks.append((bearish_candidate_idx, high_level, low_level, avg_level, strength))

    def get_active_order_blocks(self, current_index):
        """
        Get order blocks that are still relevant (dynamic lookback period)
        """
        min_index = max(0, current_index - self.current_lookback_period)

        active_bullish = [block for block in self.bullish_blocks if block[0] >= min_index]
        active_bearish = [block for block in self.bearish_blocks if block[0] >= min_index]

        # Sort by strength (higher strength first)
        active_bullish.sort(key=lambda x: x[4], reverse=True)
        active_bearish.sort(key=lambda x: x[4], reverse=True)

        return active_bullish, active_bearish

    def price_in_order_block(self, price, block_high, block_low):
        """
        Check if price is within order block zone
        """
        return block_low <= price <= block_high

    def next(self):
        current_index = len(self.data) - 1
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]

        # Determine market regime and adapt parameters
        market_regime = self.get_market_regime()
        self.adapt_parameters(market_regime)

        # Update order blocks with dynamic parameters
        self.identify_order_blocks(current_index)

        # Get active order blocks (sorted by strength)
        active_bullish, active_bearish = self.get_active_order_blocks(current_index)

        # Dynamic order block trading
        if not self.position:

            # Check for bullish entry (prioritize stronger blocks)
            for block_idx, block_high, block_low, block_avg, strength in active_bullish[:3]:  # Top 3 strongest
                if self.price_in_order_block(current_low, block_high, block_low):
                    # Use ATR-adjusted stops in high volatility
                    if len(self.atr) > 0:
                        atr_factor = min(2.0, self.atr[-1] / current_price * 100)  # Cap ATR influence
                        dynamic_sl = self.current_stop_loss * (1 + atr_factor)
                        dynamic_tp = self.current_take_profit * (1 + atr_factor * 0.5)
                    else:
                        dynamic_sl = self.current_stop_loss
                        dynamic_tp = self.current_take_profit

                    sl_price = current_price * (1 - dynamic_sl)
                    tp_price = current_price * (1 + dynamic_tp)

                    self.buy(size=self.size, sl=sl_price, tp=tp_price)
                    break

            # Check for bearish entry (prioritize stronger blocks)
            if not self.position:
                for block_idx, block_high, block_low, block_avg, strength in active_bearish[:3]:  # Top 3 strongest
                    if self.price_in_order_block(current_high, block_high, block_low):
                        # Use ATR-adjusted stops in high volatility
                        if len(self.atr) > 0:
                            atr_factor = min(2.0, self.atr[-1] / current_price * 100)  # Cap ATR influence
                            dynamic_sl = self.current_stop_loss * (1 + atr_factor)
                            dynamic_tp = self.current_take_profit * (1 + atr_factor * 0.5)
                        else:
                            dynamic_sl = self.current_stop_loss
                            dynamic_tp = self.current_take_profit

                        sl_price = current_price * (1 + dynamic_sl)
                        tp_price = current_price * (1 - dynamic_tp)

                        self.sell(size=self.size, sl=sl_price, tp=tp_price)
                        break

# Run single backtest (default behavior)
bt = Backtest(data, OrderBlocksDynamic, cash=1000000, commission=0.00045)

print("\n🌙 ===== ORDER BLOCKS DYNAMIC STRATEGY - DEFAULT PARAMETERS ===== 🌙")
print(f"Base Relevant Periods: {BASE_RELEVANT_PERIODS}")
print(f"Base Min Percent Move: {BASE_MIN_PERCENT_MOVE}%")
print(f"Use Whole Range: {USE_WHOLE_RANGE}")
print(f"Base Lookback Period: {BASE_LOOKBACK_PERIOD}")
print(f"Position Size: {POSITION_SIZE}")
print(f"Base Take Profit: {BASE_TAKE_PROFIT_PERCENT}%")
print(f"Base Stop Loss: {BASE_STOP_LOSS_PERCENT}%")
print(f"Volatility Period: {VOLATILITY_PERIOD}")
print(f"Low Vol Threshold: {VOLATILITY_THRESHOLD_LOW*100}%")
print(f"High Vol Threshold: {VOLATILITY_THRESHOLD_HIGH*100}%")

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
    print("TESTING ORDER BLOCKS DYNAMIC STRATEGY ON ALL DATA SOURCES")
    print("="*80)

    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from multi_data_tester import test_on_all_data

    # Test this strategy on all configured data sources
    results = test_on_all_data(OrderBlocksDynamic, 'OrderBlocksDynamic')

    if results is not None:
        print("\n✅ Testing complete! Results saved in: ./results/OrderBlocksDynamic.csv")