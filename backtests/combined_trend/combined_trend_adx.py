"""
Combined Trend Strategy - ADX Version
Adds ADX for trend strength confirmation to the base combined strategy
"""

import sys
import os
import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
import pandas_ta as ta
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multi_data_tester import test_on_all_data


class CombinedTrendADX(Strategy):
    # Target Trend parameters
    sma_length = 50
    atr_period = 14
    atr_mult = 1.5

    # Zero-Lag MA parameters
    zlma_period = 20
    ema_period = 20

    # ADX parameters
    adx_period = 14
    adx_threshold = 25  # Only trade in strong trends
    adx_extreme = 50    # Very strong trend

    # Risk management
    target1_mult = 5
    target2_mult = 10
    target3_mult = 15
    stop_loss_pct = 0.03
    take_profit_pct = 0.06

    def init(self):
        # Target Trend components
        self.sma_high = self.I(ta.sma, pd.Series(self.data.High), self.sma_length)
        self.sma_low = self.I(ta.sma, pd.Series(self.data.Low), self.sma_length)

        # ATR for bands
        high_series = pd.Series(self.data.High)
        low_series = pd.Series(self.data.Low)
        close_series = pd.Series(self.data.Close)

        self.atr = self.I(ta.atr, high_series, low_series, close_series, self.atr_period)

        # Zero-Lag MA calculation
        ema_close = ta.ema(close_series, self.ema_period)
        zlma_input = close_series + (close_series - ema_close)
        self.zlma = self.I(ta.ema, zlma_input, self.zlma_period)
        self.ema = self.I(ta.ema, close_series, self.ema_period)

        # ADX for trend strength
        adx_result = ta.adx(high_series, low_series, close_series, self.adx_period)
        if adx_result is not None and len(adx_result.columns) > 0:
            # Extract ADX, +DI and -DI
            self.adx = self.I(lambda: adx_result.iloc[:, 0].values)  # ADX
            self.plus_di = self.I(lambda: adx_result.iloc[:, 1].values) if len(adx_result.columns) > 1 else self.I(lambda: np.zeros(len(close_series)))
            self.minus_di = self.I(lambda: adx_result.iloc[:, 2].values) if len(adx_result.columns) > 2 else self.I(lambda: np.zeros(len(close_series)))
        else:
            self.adx = self.I(lambda: np.zeros(len(close_series)))
            self.plus_di = self.I(lambda: np.zeros(len(close_series)))
            self.minus_di = self.I(lambda: np.zeros(len(close_series)))

        # Track position entry for targets
        self.entry_price = 0
        self.position_type = 0
        self.target1_hit = False
        self.target2_hit = False

    def calculate_trend_signals(self, index):
        """Calculate Target Trend signals"""
        if index < max(self.sma_length, self.atr_period):
            return 0

        close = self.data.Close[index]
        sma_high = self.sma_high[index]
        sma_low = self.sma_low[index]
        atr = self.atr[index]

        # Bullish trend when close > SMA_high + ATR
        if close > sma_high + (atr * self.atr_mult):
            return 1
        # Bearish trend when close < SMA_low - ATR
        elif close < sma_low - (atr * self.atr_mult):
            return -1
        return 0

    def calculate_zlma_signals(self, index):
        """Calculate Zero-Lag MA signals"""
        if index < max(self.zlma_period, self.ema_period) + 1:
            return 0

        # ZLMA crossover signals
        zlma_curr = self.zlma[index]
        zlma_prev = self.zlma[index - 1]
        ema_curr = self.ema[index]
        ema_prev = self.ema[index - 1]

        # Bullish crossover
        if zlma_prev <= ema_prev and zlma_curr > ema_curr:
            return 1
        # Bearish crossover
        elif zlma_prev >= ema_prev and zlma_curr < ema_curr:
            return -1
        return 0

    def check_adx_confirmation(self, is_long):
        """Check ADX for trend strength confirmation"""
        adx_value = self.adx[-1]
        plus_di = self.plus_di[-1]
        minus_di = self.minus_di[-1]

        if pd.isna(adx_value) or pd.isna(plus_di) or pd.isna(minus_di):
            return False

        # ADX must be above threshold for strong trend
        if adx_value < self.adx_threshold:
            return False

        # Check directional movement alignment
        if is_long:
            # For long, +DI should be above -DI
            return plus_di > minus_di
        else:
            # For short, -DI should be above +DI
            return minus_di > plus_di

    def calculate_targets(self, entry_price, is_long):
        """Calculate ATR-based target levels with ADX adjustment"""
        atr = self.atr[-1]
        adx_value = self.adx[-1]

        # Adjust multipliers based on ADX strength
        mult_adjustment = 1.0
        if not pd.isna(adx_value):
            if adx_value > self.adx_extreme:
                mult_adjustment = 1.5  # Increase targets in very strong trends
            elif adx_value > self.adx_threshold:
                mult_adjustment = 1.2  # Moderate increase in strong trends

        if is_long:
            target1 = entry_price + (atr * self.target1_mult * mult_adjustment)
            target2 = entry_price + (atr * self.target2_mult * mult_adjustment)
            target3 = entry_price + (atr * self.target3_mult * mult_adjustment)
            stop = entry_price - (atr * self.atr_mult)
        else:
            target1 = entry_price - (atr * self.target1_mult * mult_adjustment)
            target2 = entry_price - (atr * self.target2_mult * mult_adjustment)
            target3 = entry_price - (atr * self.target3_mult * mult_adjustment)
            stop = entry_price + (atr * self.atr_mult)

        return target1, target2, target3, stop

    def next(self):
        index = len(self.data) - 1
        close = self.data.Close[-1]

        # Get signals from both indicators
        trend_signal = self.calculate_trend_signals(index)
        zlma_signal = self.calculate_zlma_signals(index)

        # Check existing position management
        if self.position:
            # Check if trend is weakening (ADX falling below threshold)
            adx_value = self.adx[-1]
            if not pd.isna(adx_value) and adx_value < 20:  # Exit if trend weakens
                self.position.close()
                self.reset_position_tracking()
                return

            # Long position management
            if self.position.is_long:
                # Calculate targets
                target1, target2, target3, stop = self.calculate_targets(self.entry_price, True)

                # Progressive exit strategy
                if not self.target1_hit and close >= target1:
                    self.position.close(0.33)
                    self.target1_hit = True
                elif self.target1_hit and not self.target2_hit and close >= target2:
                    self.position.close(0.5)
                    self.target2_hit = True
                elif self.target2_hit and close >= target3:
                    self.position.close()
                    self.reset_position_tracking()
                # Stop loss
                elif close <= stop or close <= self.entry_price * (1 - self.stop_loss_pct):
                    self.position.close()
                    self.reset_position_tracking()

            # Short position management
            elif self.position.is_short:
                # Calculate targets
                target1, target2, target3, stop = self.calculate_targets(self.entry_price, False)

                # Progressive exit strategy
                if not self.target1_hit and close <= target1:
                    self.position.close(0.33)
                    self.target1_hit = True
                elif self.target1_hit and not self.target2_hit and close <= target2:
                    self.position.close(0.5)
                    self.target2_hit = True
                elif self.target2_hit and close <= target3:
                    self.position.close()
                    self.reset_position_tracking()
                # Stop loss
                elif close >= stop or close >= self.entry_price * (1 + self.stop_loss_pct):
                    self.position.close()
                    self.reset_position_tracking()

        # Entry logic - both indicators must agree + ADX confirmation
        else:
            # Long entry: Both signals bullish + ADX confirmation
            if trend_signal == 1 and zlma_signal == 1 and self.check_adx_confirmation(True):
                self.buy()
                self.entry_price = close
                self.position_type = 1
                self.reset_targets()

            # Short entry: Both signals bearish + ADX confirmation
            elif trend_signal == -1 and zlma_signal == -1 and self.check_adx_confirmation(False):
                self.sell()
                self.entry_price = close
                self.position_type = -1
                self.reset_targets()

    def reset_targets(self):
        """Reset target tracking"""
        self.target1_hit = False
        self.target2_hit = False

    def reset_position_tracking(self):
        """Reset all position tracking variables"""
        self.entry_price = 0
        self.position_type = 0
        self.reset_targets()


def run_backtest(data, strategy_class=CombinedTrendADX, cash=10000, commission=0.002):
    """Run backtest with the strategy"""
    bt = Backtest(data, strategy_class, cash=cash, commission=commission)
    stats = bt.run()
    return stats, bt


def main():
    """Run strategy on multiple datasets"""
    strategy_name = "CombinedTrendADX"

    # Run backtests on all datasets
    results_df = test_on_all_data(
        strategy_class=CombinedTrendADX,
        strategy_name=strategy_name,
        optimize=False,
        cash=10000,
        commission=0.002
    )

    # Print aggregate statistics
    print("\n" + "="*80)
    print(f"AGGREGATE RESULTS FOR {strategy_name}")
    print("="*80)

    if results_df is not None and not results_df.empty:
        print("\nSummary Statistics:")
        print(f"Total Datasets Tested: {len(results_df)}")
        print(f"Profitable Strategies: {(results_df['Return_%'] > 0).sum()}")
        print(f"Average Return: {results_df['Return_%'].mean():.2f}%")
        print(f"Best Return: {results_df['Return_%'].max():.2f}%")
        print(f"Worst Return: {results_df['Return_%'].min():.2f}%")
        print(f"Average Sharpe Ratio: {results_df['Sharpe'].mean():.2f}")
        print(f"Average Max Drawdown: {results_df['Max_DD_%'].mean():.2f}%")
        print(f"Average Win Rate: {results_df['Win_Rate_%'].mean():.2f}%")
    else:
        print("No results generated")


if __name__ == "__main__":
    main()