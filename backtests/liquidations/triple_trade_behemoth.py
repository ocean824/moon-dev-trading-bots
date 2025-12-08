"""
Triple Trade Behemoth - Moon Dev's Ultimate Liquidation Combo
==============================================================
Moon Dev's "Triple Trade Behemoth" Strategy

The ultimate combination of all liquidation strategies tested today!

TRADE 1 - Buy the Dip:
- Big long liquidation detected → BUY immediately
- Record the LOW price of the liquidation bar
- TP/SL: 2-4%

TRADE 2 - Flip Short:
- When Trade 1 closes (TP or SL) → FLIP SHORT immediately
- Emergency SL only (5-7%), NO TP
- Wait for price to revisit the original liquidation low

TRADE 3 - Revisit & Go Long:
- When price drops to liquidation LOW minus X% (0.25%, 0.5%, 1%)
- Close short AND go long
- TP/SL: 2-6%

Variables to Optimize:
- liquidation_threshold: Entry trigger amount
- lookback_bars: Liquidation lookback window
- trade1_tp_pct / trade1_sl_pct: Trade 1 TP/SL
- trade2_sl_pct: Trade 2 emergency SL
- revisit_below_pct: How far below liquidation low for Trade 3 entry
- trade3_tp_pct / trade3_sl_pct: Trade 3 TP/SL
- max_hold_bars_trade2: Max time to wait for revisit

Moon Dev 🌙
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("🚀 Moon Dev's TRIPLE TRADE BEHEMOTH Strategy 🌙")
print("The Ultimate Liquidation Combo: Buy Dip → Flip Short → Revisit Long")
print("=" * 70)

# Data configuration
data_path = '/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/moondev_api/liq_data_BTC_5m_ohlcv.csv'
timeframe = '5-minute'

print(f"📊 Loading preprocessed {timeframe} BTC liquidation data...")
data = pd.read_csv(data_path, index_col='datetime', parse_dates=True)

print(f"✅ Loaded {len(data):,} {timeframe} bars")
print(f"📊 Data columns: {list(data.columns)}")

# Map liquidation columns
if 'long_liquidations' in data.columns and 'short_liquidations' in data.columns:
    data['long_liq_volume'] = data['long_liquidations']
    data['short_liq_volume'] = data['short_liquidations']
    data['net_liq_volume'] = data['short_liquidations'] - data['long_liquidations']
else:
    print("⚠️ Warning: Liquidation columns not found, creating empty columns")
    data['long_liq_volume'] = 0
    data['short_liq_volume'] = 0
    data['net_liq_volume'] = 0


class TripleTradeBehemoth(Strategy):
    """
    Moon Dev's Triple Trade Behemoth Strategy

    State Machine:
    WAITING -> TRADE1_LONG -> TRADE2_SHORT -> TRADE3_LONG -> WAITING

    Trade 1: Buy the liquidation dip with TP/SL
    Trade 2: Flip short, emergency SL only, wait for revisit
    Trade 3: Close short & go long at revisit level, TP/SL
    """

    # Optimizable parameters
    liquidation_threshold = 2000000  # $2M minimum long liquidation volume
    lookback_bars = 1  # How many 5-min bars to sum

    # Trade 1 parameters (Buy the dip)
    trade1_tp_pct = 3.0  # 3% take profit
    trade1_sl_pct = 3.0  # 3% stop loss

    # Trade 2 parameters (Flip short, wait for revisit)
    trade2_sl_pct = 6.0  # 6% emergency stop loss

    # Trade 3 parameters (Revisit long)
    revisit_below_pct = 0.5  # Enter long when price is 0.5% below liquidation low
    trade3_tp_pct = 4.0  # 4% take profit
    trade3_sl_pct = 4.0  # 4% stop loss

    # Max hold for Trade 2 (waiting for revisit)
    max_hold_bars_trade2 = 576  # 48 hours on 5min data

    # Position sizing
    position_size = 0.95

    def init(self):
        """Initialize strategy indicators"""
        # Moon Dev's Triple Trade Behemoth Init

        self.long_liq_volume = self.I(lambda: self.data.long_liq_volume)

        self.rolling_long_liq = self.I(
            lambda x: pd.Series(x).rolling(self.lookback_bars, min_periods=1).sum(),
            self.long_liq_volume
        )

        # State tracking
        # States: 'waiting', 'trade1_long', 'trade2_short', 'trade3_long'
        self.state = 'waiting'
        self.liquidation_low = 0  # The low price when liquidation happened
        self.trade1_entry_price = 0
        self.trade2_entry_price = 0
        self.trade2_bar_count = 0
        self.revisit_target_price = 0

    def next(self):
        """Main strategy logic - Triple Trade Behemoth"""

        current_price = self.data.Close[-1]
        current_low = self.data.Low[-1]
        current_rolling_liq = self.rolling_long_liq[-1]

        # ============================================
        # STATE: WAITING - Look for liquidation signal
        # ============================================
        if self.state == 'waiting':
            if not self.position:
                if current_rolling_liq >= self.liquidation_threshold:
                    # Record the liquidation low for later
                    self.liquidation_low = current_low
                    self.revisit_target_price = self.liquidation_low * (1 - self.revisit_below_pct / 100)

                    # TRADE 1: BUY the dip
                    self.trade1_entry_price = current_price
                    self.buy(size=self.position_size)
                    self.state = 'trade1_long'

        # ============================================
        # STATE: TRADE1_LONG - Waiting for TP or SL
        # ============================================
        elif self.state == 'trade1_long':
            if self.position and self.position.is_long:
                pnl_pct = ((current_price - self.trade1_entry_price) / self.trade1_entry_price) * 100

                # Take profit hit - FLIP TO SHORT
                if pnl_pct >= self.trade1_tp_pct:
                    self.position.close()
                    # Flip to short
                    self.sell(size=self.position_size)
                    self.trade2_entry_price = current_price
                    self.trade2_bar_count = 0
                    self.state = 'trade2_short'

                # Stop loss hit - FLIP TO SHORT anyway
                elif pnl_pct <= -self.trade1_sl_pct:
                    self.position.close()
                    # Flip to short
                    self.sell(size=self.position_size)
                    self.trade2_entry_price = current_price
                    self.trade2_bar_count = 0
                    self.state = 'trade2_short'

            # Position closed externally
            elif not self.position:
                self.state = 'waiting'
                self._reset_state()

        # ============================================
        # STATE: TRADE2_SHORT - Waiting for revisit
        # ============================================
        elif self.state == 'trade2_short':
            if self.position and self.position.is_short:
                self.trade2_bar_count += 1

                # Calculate PnL for emergency stop loss check
                pnl_pct = ((self.trade2_entry_price - current_price) / self.trade2_entry_price) * 100

                # Emergency stop loss hit - reset to waiting
                if pnl_pct <= -self.trade2_sl_pct:
                    self.position.close()
                    self.state = 'waiting'
                    self._reset_state()

                # Max hold time exceeded - reset to waiting
                elif self.trade2_bar_count >= self.max_hold_bars_trade2:
                    self.position.close()
                    self.state = 'waiting'
                    self._reset_state()

                # Price reached revisit target - CLOSE SHORT & GO LONG
                elif current_low <= self.revisit_target_price:
                    self.position.close()
                    # Go long for Trade 3
                    self.buy(size=self.position_size)
                    self.state = 'trade3_long'

            # Position closed externally
            elif not self.position:
                self.state = 'waiting'
                self._reset_state()

        # ============================================
        # STATE: TRADE3_LONG - Final long with TP/SL
        # ============================================
        elif self.state == 'trade3_long':
            if self.position and self.position.is_long:
                # Use revisit target as entry price for PnL calc
                entry_price = self.revisit_target_price
                pnl_pct = ((current_price - entry_price) / entry_price) * 100

                # Take profit hit - done with cycle
                if pnl_pct >= self.trade3_tp_pct:
                    self.position.close()
                    self.state = 'waiting'
                    self._reset_state()

                # Stop loss hit - done with cycle
                elif pnl_pct <= -self.trade3_sl_pct:
                    self.position.close()
                    self.state = 'waiting'
                    self._reset_state()

            # Position closed externally
            elif not self.position:
                self.state = 'waiting'
                self._reset_state()

    def _reset_state(self):
        """Reset all state variables"""
        self.liquidation_low = 0
        self.trade1_entry_price = 0
        self.trade2_entry_price = 0
        self.trade2_bar_count = 0
        self.revisit_target_price = 0


# Run backtest with baseline parameters
print("\n" + "="*70)
print("RUNNING BASELINE BACKTEST (Non-Optimized)")
print("="*70)

if len(data) > 100:
    bt = Backtest(
        data[['Open', 'High', 'Low', 'Close', 'Volume', 'long_liq_volume', 'short_liq_volume', 'net_liq_volume']],
        TripleTradeBehemoth,
        cash=1000000,
        commission=0.001
    )

    # Run baseline
    baseline_stats = bt.run()

    print(f"\n📊 Moon Dev's BASELINE RESULTS (TRIPLE TRADE BEHEMOTH):")
    print(f"Liquidation Threshold: ${TripleTradeBehemoth.liquidation_threshold:,}")
    print(f"Lookback Bars: {TripleTradeBehemoth.lookback_bars} ({TripleTradeBehemoth.lookback_bars * 5} minutes)")
    print(f"Trade 1 TP/SL: {TripleTradeBehemoth.trade1_tp_pct}% / {TripleTradeBehemoth.trade1_sl_pct}%")
    print(f"Trade 2 Emergency SL: {TripleTradeBehemoth.trade2_sl_pct}%")
    print(f"Revisit Below Low: {TripleTradeBehemoth.revisit_below_pct}%")
    print(f"Trade 3 TP/SL: {TripleTradeBehemoth.trade3_tp_pct}% / {TripleTradeBehemoth.trade3_sl_pct}%")
    print("-" * 50)
    print(f"Total Trades: {baseline_stats['# Trades']}")
    print(f"Win Rate: {baseline_stats['Win Rate [%]']:.2f}%")
    print(f"Return: {baseline_stats['Return [%]']:.2f}%")
    print(f"Sharpe: {baseline_stats['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown: {baseline_stats['Max. Drawdown [%]']:.2f}%")

    print("\n📈 FULL BASELINE STATS:")
    print("="*70)
    print(baseline_stats)

    # Run optimization
    print("\n" + "="*70)
    print("RUNNING OPTIMIZATION - Moon Dev's Parameter Search")
    print("="*70)
    print("🔄 Optimizing parameters... This may take a few minutes...")

    try:
        optimization_results = bt.optimize(
            liquidation_threshold=range(1000000, 5000000, 1000000),  # $1M to $5M
            lookback_bars=[1, 2, 3],  # 5min to 15min lookback
            trade1_tp_pct=[2.0, 3.0],  # Trade 1 TP
            trade1_sl_pct=[2.0, 3.0],  # Trade 1 SL
            trade2_sl_pct=[5.0, 6.0],  # Trade 2 emergency SL
            revisit_below_pct=[0.25, 0.5],  # Revisit target
            trade3_tp_pct=[2.0, 4.0],  # Trade 3 TP
            trade3_sl_pct=[2.0, 4.0],  # Trade 3 SL
            maximize='Return [%]',
            return_heatmap=False
        )

        print("\n✨ Moon Dev's OPTIMIZED RESULTS:")
        print("="*70)
        print(optimization_results)

        # Extract and display optimized parameters
        print("\n🎯 OPTIMIZED PARAMETERS:")
        print("-" * 50)
        print(f"Liquidation Threshold: ${optimization_results._strategy.liquidation_threshold:,}")
        print(f"Lookback Bars: {optimization_results._strategy.lookback_bars} ({optimization_results._strategy.lookback_bars * 5} minutes)")
        print(f"Trade 1 TP: {optimization_results._strategy.trade1_tp_pct}%")
        print(f"Trade 1 SL: {optimization_results._strategy.trade1_sl_pct}%")
        print(f"Trade 2 Emergency SL: {optimization_results._strategy.trade2_sl_pct}%")
        print(f"Revisit Below Low: {optimization_results._strategy.revisit_below_pct}%")
        print(f"Trade 3 TP: {optimization_results._strategy.trade3_tp_pct}%")
        print(f"Trade 3 SL: {optimization_results._strategy.trade3_sl_pct}%")

        # Compare baseline vs optimized
        print("\n📊 IMPROVEMENT SUMMARY:")
        print("-" * 50)
        baseline_return = baseline_stats['Return [%]']
        optimized_return = optimization_results['Return [%]']
        print(f"Baseline Return: {baseline_return:.2f}%")
        print(f"Optimized Return: {optimized_return:.2f}%")
        print(f"Improvement: {optimized_return - baseline_return:.2f}%")

        # Show the plot
        bt.plot()

    except Exception as e:
        print(f"\n⚠️ Optimization failed: {str(e)}")
        print("This may happen if there aren't enough trades or invalid parameter combinations.")
        import traceback
        traceback.print_exc()

        # Still show the baseline plot
        bt.plot()

else:
    print("❌ Insufficient data for backtesting")
