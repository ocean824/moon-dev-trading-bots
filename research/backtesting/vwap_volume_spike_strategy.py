"""
🌙 MOON DEV'S VWAP MEAN REVERSION + VOLUME SPIKE STRATEGY 🚀
=============================================================
Inspired by Market Wizards book and Chat with Traders podcast (300+ episodes!)

Strategy Logic:
- Wait for VOLUME SPIKE (volume > 2x average) - this signals institutional activity
- When volume spikes AND price is significantly BELOW VWAP → BUY (expect mean reversion UP)
- When volume spikes AND price is significantly ABOVE VWAP → SELL (expect mean reversion DOWN)
- Exit when price reverts back to VWAP (or stop loss)

The idea: Big volume = big players moving. If they push price too far from VWAP,
it tends to snap back. We ride that reversion!

Moon Dev 🌙
"""

import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy
import warnings
warnings.filterwarnings('ignore')

print("🌙 MOON DEV'S VWAP VOLUME SPIKE STRATEGY LOADING... 🚀")
print("=" * 60)
print("📚 Inspired by Market Wizards + Chat with Traders podcast!")
print("=" * 60)


class VWAP_VolSpike_Strategy(Strategy):
    """
    🌙 Moon Dev's VWAP Mean Reversion with Volume Spike Filter

    The thesis: When volume spikes, institutions are active.
    If they push price far from VWAP, expect a snap-back!

    Parameters:
    - vol_spike_mult: How much volume needs to exceed average (2.0 = 2x)
    - vol_lookback: Period for average volume calculation
    - vwap_deviation: How far from VWAP to trigger (0.01 = 1%)
    - stop_loss_pct: Stop loss percentage
    - take_profit_pct: Take profit (can also exit at VWAP)
    """

    # Strategy parameters (can be optimized!)
    vol_spike_mult = 2.0      # Volume must be 2x the average
    vol_lookback = 20         # 20-period average volume
    vwap_deviation = 0.015    # Price must be 1.5% away from VWAP
    stop_loss_pct = 0.02      # 2% stop loss
    take_profit_pct = 0.03    # 3% take profit (or exit at VWAP)

    def init(self):
        """🚀 Initialize Moon Dev's indicators"""
        print("🔧 Moon Dev initializing VWAP + Volume Spike indicators... 🌙")

        # Get the data as pandas Series
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        close = pd.Series(self.data.Close)
        volume = pd.Series(self.data.Volume)

        # Calculate VWAP manually (typical price * volume / cumulative volume)
        # Using a rolling VWAP over 20 periods for mean reversion
        def calc_rolling_vwap(high, low, close, volume, period=20):
            typical_price = (high + low + close) / 3
            tp_vol = typical_price * volume
            cum_tp_vol = tp_vol.rolling(window=period).sum()
            cum_vol = volume.rolling(window=period).sum()
            vwap = cum_tp_vol / cum_vol
            return vwap

        self.vwap = self.I(calc_rolling_vwap, high, low, close, volume, 20)

        # Calculate average volume for spike detection
        self.avg_volume = self.I(ta.sma, volume, length=self.vol_lookback)

        # Store volume for comparison
        self.volume = self.I(lambda x: x, volume)

        print(f"📊 Moon Dev's indicators ready!")
        print(f"🔊 Volume spike threshold: {self.vol_spike_mult}x average")
        print(f"📏 VWAP deviation threshold: {self.vwap_deviation*100}%")
        print(f"🛡️ Stop loss: {self.stop_loss_pct*100}%")
        print(f"🎯 Take profit: {self.take_profit_pct*100}%")
        print("=" * 50)

    def next(self):
        """🌙 Moon Dev's trading logic for each bar"""

        # Get current values
        current_price = self.data.Close[-1]
        current_vwap = self.vwap[-1]
        current_volume = self.volume[-1]
        current_avg_vol = self.avg_volume[-1]

        # Skip if indicators not ready
        if (np.isnan(current_vwap) or np.isnan(current_avg_vol) or
            current_avg_vol == 0):
            return

        # Calculate current deviation from VWAP
        vwap_deviation = (current_price - current_vwap) / current_vwap

        # Check for volume spike
        volume_ratio = current_volume / current_avg_vol
        is_volume_spike = volume_ratio >= self.vol_spike_mult

        # Check if price is significantly away from VWAP
        is_below_vwap = vwap_deviation < -self.vwap_deviation
        is_above_vwap = vwap_deviation > self.vwap_deviation

        # ===== ENTRY LOGIC =====

        # 🟢 LONG ENTRY: Volume spike + Price significantly BELOW VWAP
        # Thesis: Big volume pushed price down too far, expect snap-back UP
        if (not self.position and
            is_volume_spike and
            is_below_vwap):

            self.buy(size=0.95)  # 95% of available cash
            print(f"🟢 MOON DEV LONG ENTRY! 🚀")
            print(f"   💰 Price: ${current_price:,.2f}")
            print(f"   📈 VWAP: ${current_vwap:,.2f}")
            print(f"   📉 Deviation: {vwap_deviation*100:.2f}% (BELOW VWAP)")
            print(f"   🔊 Volume: {volume_ratio:.1f}x average (SPIKE!)")
            print(f"   🎯 Expecting mean reversion UP to VWAP")
            print("=" * 50)

        # 🔴 SHORT ENTRY: Volume spike + Price significantly ABOVE VWAP
        # Thesis: Big volume pushed price up too far, expect snap-back DOWN
        elif (not self.position and
              is_volume_spike and
              is_above_vwap):

            self.sell(size=0.95)  # 95% short
            print(f"🔴 MOON DEV SHORT ENTRY! 📉")
            print(f"   💰 Price: ${current_price:,.2f}")
            print(f"   📈 VWAP: ${current_vwap:,.2f}")
            print(f"   📈 Deviation: {vwap_deviation*100:.2f}% (ABOVE VWAP)")
            print(f"   🔊 Volume: {volume_ratio:.1f}x average (SPIKE!)")
            print(f"   🎯 Expecting mean reversion DOWN to VWAP")
            print("=" * 50)

        # ===== EXIT LOGIC =====

        elif self.position:
            # In backtesting.py, use self.position.pl_pct for P&L percentage
            # and self.trades[-1] to get entry info if needed
            pnl_pct = self.position.pl_pct / 100  # Convert from percentage to decimal

            if self.position.size > 0:  # Long position

                # Exit at VWAP (mean reversion target) or take profit
                if (current_price >= current_vwap or
                    pnl_pct >= self.take_profit_pct):

                    self.position.close()
                    print(f"🟢 MOON DEV LONG EXIT! 🎉")
                    print(f"   💰 Exit price: ${current_price:,.2f}")
                    print(f"   📈 VWAP: ${current_vwap:,.2f}")
                    print(f"   💵 PnL: {pnl_pct*100:+.2f}%")
                    reason = "Reverted to VWAP" if current_price >= current_vwap else "Take profit"
                    print(f"   🎯 Exit reason: {reason}")
                    print("=" * 50)

                # Stop loss
                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    print(f"🛑 MOON DEV LONG STOP LOSS! 😢")
                    print(f"   💰 Exit price: ${current_price:,.2f}")
                    print(f"   💵 PnL: {pnl_pct*100:+.2f}%")
                    print("=" * 50)

            else:  # Short position
                # For shorts, pl_pct is already inverted by backtesting.py

                # Exit at VWAP (mean reversion target) or take profit
                if (current_price <= current_vwap or
                    pnl_pct >= self.take_profit_pct):

                    self.position.close()
                    print(f"🔴 MOON DEV SHORT EXIT! 🎉")
                    print(f"   💰 Exit price: ${current_price:,.2f}")
                    print(f"   📈 VWAP: ${current_vwap:,.2f}")
                    print(f"   💵 PnL: {pnl_pct*100:+.2f}%")
                    reason = "Reverted to VWAP" if current_price <= current_vwap else "Take profit"
                    print(f"   🎯 Exit reason: {reason}")
                    print("=" * 50)

                # Stop loss
                elif pnl_pct <= -self.stop_loss_pct:
                    self.position.close()
                    print(f"🛑 MOON DEV SHORT STOP LOSS! 😢")
                    print(f"   💰 Exit price: ${current_price:,.2f}")
                    print(f"   💵 PnL: {pnl_pct*100:+.2f}%")
                    print("=" * 50)


def load_local_data(filepath):
    """
    🌙 Load data from Moon Dev's local CSV files
    """
    print(f"📂 Moon Dev loading local data: {filepath}")

    data = pd.read_csv(filepath, parse_dates=['datetime'])
    data = data.set_index('datetime')

    # Rename columns to match backtesting.py expectations
    data.columns = [col.capitalize() for col in data.columns]
    if 'Datetime' in data.columns:
        data = data.drop('Datetime', axis=1)

    data = data.dropna()

    print(f"🎉 Moon Dev loaded {len(data):,} bars! 🚀")
    print(f"📅 Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
    print(f"💰 Price range: ${data['Close'].min():,.2f} - ${data['Close'].max():,.2f}")
    print(f"📊 Avg Volume: {data['Volume'].mean():,.0f}")
    print("=" * 50)

    return data


def download_data(ticker="SPY", period="2y", interval="1d"):
    """
    🌙 Download data from Yahoo Finance
    Moon Dev recommends testing on multiple assets!
    """
    print(f"📥 Moon Dev downloading {ticker} data... 🌙")
    print(f"⏰ Period: {period}, Interval: {interval}")

    data = yf.Ticker(ticker).history(period=period, interval=interval)

    if data.empty:
        print(f"❌ Moon Dev couldn't get data for {ticker}!")
        return None

    data = data.dropna()

    print(f"🎉 Moon Dev downloaded {len(data):,} bars! 🚀")
    print(f"📅 Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")
    print(f"💰 Price range: ${data['Close'].min():,.2f} - ${data['Close'].max():,.2f}")
    print(f"📊 Avg Volume: {data['Volume'].mean():,.0f}")
    print("=" * 50)

    return data


def run_backtest(data, cash=10000, commission=0.001):
    """
    🚀 Run Moon Dev's VWAP Volume Spike backtest

    Note: backtesting.py does NOT support fractional trading!
    For high-priced assets like BTC, we need sufficient cash to buy at least 1 unit.
    Moon Dev's solution: Auto-scale cash for expensive assets! 🌙
    """
    # Check if asset price is too high for given cash (fractional trading not supported!)
    max_price = data['Close'].max()
    if max_price > cash:
        # Scale up cash so we can afford at least a few units
        cash = int(max_price * 10)  # 10x the max price gives room for multiple trades
        print(f"⚠️ Moon Dev Auto-Scaling: Asset max price (${max_price:,.2f}) > initial cash")
        print(f"   Adjusted cash to ${cash:,} (backtesting.py doesn't support fractional trading)")

    print(f"🎮 Starting Moon Dev's VWAP Volume Spike backtest... 🌙")
    print(f"💰 Starting cash: ${cash:,}")
    print(f"💸 Commission: {commission*100}%")
    print("=" * 60)

    bt = Backtest(data, VWAP_VolSpike_Strategy,
                  cash=cash,
                  commission=commission,
                  exclusive_orders=True)

    print("🚀 Moon Dev's backtest running...")
    stats = bt.run()

    # Print ALL stats (Moon Dev's rule - never partial!)
    print("\n🎯 MOON DEV'S COMPLETE BACKTEST RESULTS 🌙")
    print("=" * 60)
    print(stats)
    print("=" * 60)

    # Moon Dev's analysis
    print("\n📊 MOON DEV'S ANALYSIS 🚀")
    print("=" * 40)

    total_return = stats['Return [%]']
    max_drawdown = stats['Max. Drawdown [%]']
    sharpe = stats['Sharpe Ratio']
    win_rate = stats['Win Rate [%]']
    num_trades = stats['# Trades']

    print(f"🎯 Total Return: {total_return:.2f}%")
    print(f"📉 Max Drawdown: {max_drawdown:.2f}%")
    print(f"📈 Sharpe Ratio: {sharpe:.2f}")
    print(f"🎲 Win Rate: {win_rate:.2f}%")
    print(f"🔄 Number of Trades: {num_trades}")

    # Performance rating
    if sharpe > 1.5:
        print("🌙 Moon Dev says: EXCELLENT risk-adjusted returns! 🚀🚀🚀")
    elif sharpe > 1.0:
        print("🌙 Moon Dev says: Good Sharpe ratio! 🚀🚀")
    elif sharpe > 0.5:
        print("🌙 Moon Dev says: Decent performance 🚀")
    elif sharpe > 0:
        print("🌙 Moon Dev says: Positive but room for improvement")
    else:
        print("🌙 Moon Dev says: Needs work! 😅")

    print("=" * 60)

    # Show plot (don't save - Moon Dev's rule!)
    print("📈 Showing Moon Dev's backtest plot...")
    bt.plot()

    return stats, bt


def optimize_strategy(data):
    """
    🔧 Optimize Moon Dev's strategy parameters
    """
    print("🔧 Starting Moon Dev's optimization... 🌙")
    print("⚠️ This may take a few minutes!")

    # Auto-scale cash for expensive assets (same as run_backtest)
    cash = 10000
    max_price = data['Close'].max()
    if max_price > cash:
        cash = int(max_price * 10)

    bt = Backtest(data, VWAP_VolSpike_Strategy,
                  cash=cash,
                  commission=0.001,
                  exclusive_orders=True)

    stats = bt.optimize(
        vol_spike_mult=[1.5, 2.0, 2.5, 3.0],      # Volume spike thresholds
        vol_lookback=[10, 20, 30],                  # Volume averaging period
        vwap_deviation=[0.01, 0.015, 0.02, 0.025], # VWAP deviation thresholds
        stop_loss_pct=[0.015, 0.02, 0.025],        # Stop loss levels
        take_profit_pct=[0.02, 0.03, 0.04],        # Take profit levels
        maximize='Sharpe Ratio',
        return_heatmap=False
    )

    print("\n🎉 Moon Dev's optimization complete! 🚀")
    print("=" * 60)
    print(stats)
    print("=" * 60)

    return stats


def main():
    """
    🌙 Moon Dev's main backtesting pipeline
    """
    print("\n" + "🌙" * 30)
    print("  MOON DEV'S VWAP VOLUME SPIKE BACKTEST SYSTEM")
    print("  Inspired by Market Wizards + Chat with Traders!")
    print("🌙" * 30 + "\n")

    # Try loading local Bitcoin data first
    import os
    local_btc_file = os.path.join(os.path.dirname(__file__),
                                   "../../data/ge_data/BTC-USD-1h-2018-1-01T00_00.csv")

    data = None
    if os.path.exists(local_btc_file):
        print("📂 Found local Bitcoin data! Using that... 🌙")
        data = load_local_data(local_btc_file)
        # Use last 2 years of data for speed
        if len(data) > 17520:  # ~2 years of hourly data
            data = data.tail(17520)
            print(f"📊 Using last 2 years: {len(data):,} bars")
    else:
        # Fallback to downloading SPY daily data
        print("📥 No local data found, downloading SPY daily... 🌙")
        data = download_data(ticker="SPY", period="2y", interval="1d")

    if data is None:
        print("❌ Moon Dev can't proceed without data!")
        return

    # Run the backtest
    stats, bt = run_backtest(data, cash=10000, commission=0.001)

    # Optional: Run optimization
    print("\n🔧 Want to optimize the strategy parameters?")
    print("   This will test different combinations to find the best settings.")
    user_input = input("   Enter 'y' to optimize, any other key to skip: ").lower()

    if user_input == 'y':
        optimized_stats = optimize_strategy(data)

        print("\n📊 OPTIMIZED PARAMETERS FOUND:")
        print(f"   Volume Spike Mult: {optimized_stats._strategy.vol_spike_mult}")
        print(f"   Volume Lookback: {optimized_stats._strategy.vol_lookback}")
        print(f"   VWAP Deviation: {optimized_stats._strategy.vwap_deviation*100}%")
        print(f"   Stop Loss: {optimized_stats._strategy.stop_loss_pct*100}%")
        print(f"   Take Profit: {optimized_stats._strategy.take_profit_pct*100}%")

    print("\n" + "=" * 60)
    print("🎉 MOON DEV'S VWAP VOLUME SPIKE BACKTEST COMPLETE! 🚀🌙")
    print("=" * 60)
    print("\n💡 Moon Dev's Tips:")
    print("   • Try different tickers: 'ETH-USD', 'SPY', 'QQQ'")
    print("   • Adjust vol_spike_mult for more/fewer signals")
    print("   • Increase vwap_deviation for bigger moves only")
    print("   • Remember: Past performance ≠ future results!")
    print("=" * 60)


if __name__ == "__main__":
    main()
