"""
Smart Money Breakout Channels - RSI + ADX Enhanced
Adds RSI for momentum confirmation and ADX for trend strength
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

class SmartMoneyBreakoutRSI(Strategy):
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

    # RSI parameters
    rsi_period = 14
    rsi_overbought = 70
    rsi_oversold = 30
    rsi_neutral_high = 60
    rsi_neutral_low = 40

    # ADX parameters
    adx_period = 14
    adx_threshold = 25  # Minimum ADX for strong trend
    adx_strong_trend = 40  # ADX level for very strong trend

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

        # Calculate RSI
        self.rsi = self.I(ta.rsi, pd.Series(self.data.Close), length=self.rsi_period)

        # Calculate ADX components
        adx_result = ta.adx(pd.Series(self.data.High),
                           pd.Series(self.data.Low),
                           pd.Series(self.data.Close),
                           length=self.adx_period)

        if adx_result is not None and len(adx_result.columns) >= 3:
            self.adx = self.I(lambda: adx_result.iloc[:, 0])  # ADX
            self.plus_di = self.I(lambda: adx_result.iloc[:, 1])  # +DI
            self.minus_di = self.I(lambda: adx_result.iloc[:, 2])  # -DI
        else:
            # Fallback if ADX calculation fails
            self.adx = self.I(lambda: pd.Series([20] * len(self.data)))
            self.plus_di = self.I(lambda: pd.Series([0] * len(self.data)))
            self.minus_di = self.I(lambda: pd.Series([0] * len(self.data)))

        # Track channel state
        self.channel_top = np.nan
        self.channel_bottom = np.nan
        self.channel_start_idx = -1
        self.in_channel = False
        self.channel_volume_total = 0
        self.channel_up_volume = 0
        self.channel_down_volume = 0
        self.bars_in_channel = 0
        self.channel_rsi_avg = 0

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

        # Also check ADX for low trend strength (consolidation)
        current_adx = self.adx[idx] if idx < len(self.adx) else 20

        if recent_volatility < self.volatility_threshold and current_adx < self.adx_threshold:
            if not self.in_channel:
                # Start new channel
                self.channel_start_idx = idx
                self.in_channel = True
                self.bars_in_channel = 0
                self.channel_volume_total = 0
                self.channel_up_volume = 0
                self.channel_down_volume = 0
                self.channel_rsi_avg = self.rsi[idx]

                # Calculate initial channel boundaries
                lookback_start = max(0, idx - self.lookback)
                self.channel_top = max(self.data.High[lookback_start:idx+1])
                self.channel_bottom = min(self.data.Low[lookback_start:idx+1])

                return True
        else:
            # Volatility increased or trend strengthened - end channel if it exists
            if self.in_channel and self.bars_in_channel >= self.channel_min_bars:
                self.in_channel = False
                return False

        return self.in_channel

    def update_channel_stats(self, idx):
        """Update channel statistics including volume and RSI"""
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

            # Update average RSI
            self.channel_rsi_avg = ((self.channel_rsi_avg * (self.bars_in_channel - 1) +
                                    self.rsi[idx]) / self.bars_in_channel)

    def check_rsi_divergence(self, idx, lookback=10):
        """Check for RSI divergence patterns"""
        if idx < lookback:
            return None

        # Get recent price and RSI data
        recent_prices = self.close[idx-lookback:idx+1]
        recent_rsi = self.rsi[idx-lookback:idx+1]

        # Find local extremes
        price_max_idx = np.argmax(recent_prices)
        price_min_idx = np.argmin(recent_prices)
        rsi_max_idx = np.argmax(recent_rsi)
        rsi_min_idx = np.argmin(recent_rsi)

        # Bearish divergence: Price makes higher high, RSI makes lower high
        if price_max_idx == len(recent_prices) - 1:  # Recent high
            if recent_prices[-1] > recent_prices[0] and recent_rsi[-1] < recent_rsi[rsi_max_idx]:
                return 'bearish'

        # Bullish divergence: Price makes lower low, RSI makes higher low
        if price_min_idx == len(recent_prices) - 1:  # Recent low
            if recent_prices[-1] < recent_prices[0] and recent_rsi[-1] > recent_rsi[rsi_min_idx]:
                return 'bullish'

        return None

    def check_breakout(self, idx):
        """Check for channel breakout with RSI and ADX confirmation"""
        if not self.in_channel or self.bars_in_channel < self.channel_min_bars:
            return None

        current_close = self.close[idx]
        current_high = self.high[idx]
        current_low = self.low[idx]
        current_open = self.open[idx]
        current_rsi = self.rsi[idx]
        current_adx = self.adx[idx] if idx < len(self.adx) else 20
        current_plus_di = self.plus_di[idx] if idx < len(self.plus_di) else 0
        current_minus_di = self.minus_di[idx] if idx < len(self.minus_di) else 0

        # Calculate candle body
        body_top = max(current_close, current_open)
        body_bottom = min(current_close, current_open)
        body_size = body_top - body_bottom

        # Calculate volume delta
        volume_delta = self.channel_up_volume - self.channel_down_volume
        volume_delta_ratio = volume_delta / max(self.channel_volume_total, 1)

        # Check for upward breakout
        if current_close > self.channel_top * (1 + self.breakout_buffer):
            # Check strong close requirement
            body_outside_top = max(0, body_bottom - self.channel_top)
            if body_size > 0:
                pct_outside = body_outside_top / body_size
                if pct_outside >= self.strong_close_pct:
                    # Enhanced confirmation with RSI and ADX
                    volume_confirmed = self.volume_ratio[idx] >= self.volume_threshold

                    # RSI should be rising but not overbought
                    rsi_confirmed = (current_rsi > self.channel_rsi_avg and
                                   current_rsi > self.rsi_neutral_low and
                                   current_rsi < self.rsi_overbought)

                    # ADX confirms trend strength is increasing
                    adx_confirmed = current_adx > self.adx_threshold

                    # +DI should be above -DI for bullish trend
                    di_confirmed = current_plus_di > current_minus_di

                    delta_confirmed = volume_delta_ratio > 0.1  # Positive delta

                    # Check for divergence
                    divergence = self.check_rsi_divergence(idx)
                    no_bearish_divergence = divergence != 'bearish'

                    if (volume_confirmed and rsi_confirmed and adx_confirmed and
                        di_confirmed and delta_confirmed and no_bearish_divergence):
                        self.in_channel = False
                        return 'long'

        # Check for downward breakout
        elif current_close < self.channel_bottom * (1 - self.breakout_buffer):
            # Check strong close requirement
            body_outside_bottom = max(0, self.channel_bottom - body_top)
            if body_size > 0:
                pct_outside = body_outside_bottom / body_size
                if pct_outside >= self.strong_close_pct:
                    # Enhanced confirmation with RSI and ADX
                    volume_confirmed = self.volume_ratio[idx] >= self.volume_threshold

                    # RSI should be falling but not oversold
                    rsi_confirmed = (current_rsi < self.channel_rsi_avg and
                                   current_rsi < self.rsi_neutral_high and
                                   current_rsi > self.rsi_oversold)

                    # ADX confirms trend strength is increasing
                    adx_confirmed = current_adx > self.adx_threshold

                    # -DI should be above +DI for bearish trend
                    di_confirmed = current_minus_di > current_plus_di

                    delta_confirmed = volume_delta_ratio < -0.1  # Negative delta

                    # Check for divergence
                    divergence = self.check_rsi_divergence(idx)
                    no_bullish_divergence = divergence != 'bullish'

                    if (volume_confirmed and rsi_confirmed and adx_confirmed and
                        di_confirmed and delta_confirmed and no_bullish_divergence):
                        self.in_channel = False
                        return 'short'

        return None

    def calculate_position_size(self):
        """Calculate position size based on available equity and ADX strength"""
        idx = len(self.data) - 1
        current_adx = self.adx[idx] if idx < len(self.adx) else 20

        # Adjust position size based on trend strength
        if current_adx > self.adx_strong_trend:
            # Strong trend - full position
            return self.position_size_pct
        elif current_adx > self.adx_threshold:
            # Moderate trend - reduced position
            return self.position_size_pct * 0.75
        else:
            # Weak trend - minimal position
            return self.position_size_pct * 0.5

    def next(self):
        idx = len(self.data) - 1
        if idx < max(self.lookback, self.rsi_period, self.adx_period) + 1:
            return

        # Detect channel formation
        self.detect_channel_formation(idx)

        # Update channel statistics if in channel
        if self.in_channel:
            self.update_channel_stats(idx)

        # Check for existing position
        if self.position:
            # Manage existing trade with RSI and ADX-based exit conditions
            current_rsi = self.rsi[idx]
            current_adx = self.adx[idx] if idx < len(self.adx) else 20

            if self.trade_type == 'long':
                # Check stop loss
                if self.close[idx] <= self.stop_loss:
                    self.position.close()
                    self.trade_type = None
                # Check take profit or overbought exit
                elif self.close[idx] >= self.take_profit or current_rsi > self.rsi_overbought:
                    self.position.close()
                    self.trade_type = None
                # Exit if trend weakens significantly
                elif current_adx < 20:
                    self.position.close()
                    self.trade_type = None
                # Check for bearish divergence exit
                elif self.check_rsi_divergence(idx) == 'bearish':
                    self.position.close()
                    self.trade_type = None

            elif self.trade_type == 'short':
                # Check stop loss
                if self.close[idx] >= self.stop_loss:
                    self.position.close()
                    self.trade_type = None
                # Check take profit or oversold exit
                elif self.close[idx] <= self.take_profit or current_rsi < self.rsi_oversold:
                    self.position.close()
                    self.trade_type = None
                # Exit if trend weakens significantly
                elif current_adx < 20:
                    self.position.close()
                    self.trade_type = None
                # Check for bullish divergence exit
                elif self.check_rsi_divergence(idx) == 'bullish':
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
        # Load data
        df = pd.read_csv(data_path, parse_dates=['datetime'])
        df = df.set_index('datetime')

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
        bt = Backtest(df, SmartMoneyBreakoutRSI, cash=cash, commission=commission)
        stats = bt.run()

        return stats

    except Exception as e:
        print(f"Error running backtest on {data_path}: {str(e)}")
        return None


def main():
    # Test with a single dataset first
    data_path = "/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-1h-500wks-data.csv"

    if os.path.exists(data_path):
        print("Running Smart Money Breakout RSI+ADX Strategy Backtest")
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
                'Strategy': 'SmartMoneyBreakoutRSI',
                'Dataset': os.path.basename(data_path),
                'Return%': stats['Return [%]'],
                'Sharpe': stats['Sharpe Ratio'],
                'Max_Drawdown%': stats['Max. Drawdown [%]'],
                'Win_Rate%': stats['Win Rate [%]'] if 'Win Rate [%]' in stats else 0,
                'Trades': stats['# Trades'],
                'Exposure%': stats['Exposure Time [%]']
            }])

            summary.to_csv(f"{results_dir}/smart_money_rsi_single_test.csv", index=False)
            print(f"\nResults saved to {results_dir}/smart_money_rsi_single_test.csv")
    else:
        print(f"Data file not found: {data_path}")


if __name__ == "__main__":
    main()