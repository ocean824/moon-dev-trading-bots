"""
Angled Volume Profile + Money Flow Index Strategy
Combines AVP with MFI for overbought/oversold conditions
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta

class AVPMFIStrategy(Strategy):
    # Parameters
    lookback_period = 50  # Bars for volume profile calculation
    volume_percentile = 60  # Percentile for HVN identification
    mfi_period = 14  # MFI period
    mfi_oversold = 30  # MFI oversold level
    mfi_overbought = 70  # MFI overbought level
    breakout_threshold = 1.002  # Price must break HVN by 0.2%
    stop_loss = 0.975  # 2.5% stop loss
    take_profit = 1.04  # 4% take profit
    min_volume_ratio = 1.3  # Volume must be 1.3x average

    def init(self):
        """Initialize indicators including MFI"""
        # Calculate volume moving average
        self.volume_ma = self.I(ta.sma, pd.Series(self.data.Volume), length=20)

        # Calculate MFI (Money Flow Index)
        high_series = pd.Series(self.data.High)
        low_series = pd.Series(self.data.Low)
        close_series = pd.Series(self.data.Close)
        volume_series = pd.Series(self.data.Volume)

        self.mfi = self.I(ta.mfi, high_series, low_series, close_series,
                         volume_series, length=self.mfi_period)

        # Volume profile levels
        self.hvn_levels = self.I(self._calculate_hvn_levels)
        self.lvn_levels = self.I(self._calculate_lvn_levels)

        # Additional indicators
        self.ema_9 = self.I(ta.ema, close_series, length=9)
        self.ema_21 = self.I(ta.ema, close_series, length=21)
        self.atr = self.I(ta.atr, high_series, low_series, close_series, length=14)

        # Bollinger Bands for volatility context
        bb = ta.bbands(close_series, length=20, std=2)
        if bb is not None and not bb.empty:
            self.bb_upper = self.I(lambda: bb.iloc[:, 2].values)  # Upper band
            self.bb_middle = self.I(lambda: bb.iloc[:, 1].values)  # Middle band
            self.bb_lower = self.I(lambda: bb.iloc[:, 0].values)  # Lower band
        else:
            # Fallback if bbands fails
            self.bb_middle = self.I(ta.sma, close_series, length=20)
            self.bb_upper = self.I(lambda: self.bb_middle[-1] * 1.02 if len(self.bb_middle) > 0 else close_series.iloc[-1])
            self.bb_lower = self.I(lambda: self.bb_middle[-1] * 0.98 if len(self.bb_middle) > 0 else close_series.iloc[-1])

    def _calculate_hvn_levels(self):
        """Calculate High Volume Node levels with MFI weighting"""
        closes = pd.Series(self.data.Close)
        volumes = pd.Series(self.data.Volume)
        highs = pd.Series(self.data.High)
        lows = pd.Series(self.data.Low)
        hvn_levels = []

        for i in range(len(closes)):
            if i < self.lookback_period:
                hvn_levels.append(closes.iloc[i] if i > 0 else closes.iloc[0])
                continue

            # Get price and volume data for lookback period
            start_idx = i - self.lookback_period + 1
            price_slice = closes.iloc[start_idx:i+1]
            volume_slice = volumes.iloc[start_idx:i+1]
            high_slice = highs.iloc[start_idx:i+1]
            low_slice = lows.iloc[start_idx:i+1]

            # Create price bins for volume profile
            price_min = price_slice.min()
            price_max = price_slice.max()

            if price_max - price_min < 0.01:
                hvn_levels.append(closes.iloc[i])
                continue

            # Create price levels for volume accumulation
            n_bins = 30  # More bins for MFI integration
            price_bins = np.linspace(price_min, price_max, n_bins)

            # Accumulate volume at each price level with angular and MFI weighting
            volume_profile = np.zeros(n_bins - 1)

            for j, (price, vol, high, low) in enumerate(zip(price_slice, volume_slice,
                                                            high_slice, low_slice)):
                bin_idx = np.searchsorted(price_bins[1:], price)
                if bin_idx < len(volume_profile):
                    # Angular weight increases for recent data
                    angle_weight = 1 + (j / self.lookback_period) * 0.5

                    # Calculate money flow for this bar
                    typical_price = (high + low + price) / 3
                    raw_money_flow = typical_price * vol

                    # Weight by money flow direction
                    if j > 0:
                        prev_typical = (high_slice.iloc[j-1] + low_slice.iloc[j-1] +
                                      price_slice.iloc[j-1]) / 3
                        mf_weight = 1.2 if typical_price > prev_typical else 0.8
                    else:
                        mf_weight = 1.0

                    volume_profile[bin_idx] += vol * angle_weight * mf_weight

            # Find HVN with emphasis on high money flow areas
            threshold = np.percentile(volume_profile, self.volume_percentile)
            hvn_indices = np.where(volume_profile >= threshold)[0]

            if len(hvn_indices) > 0:
                current_price = closes.iloc[i]
                hvn_prices = [(price_bins[idx] + price_bins[idx + 1]) / 2 for idx in hvn_indices]

                # Weight HVN selection by proximity and strength
                weighted_hvns = []
                for hvn_price, idx in zip(hvn_prices, hvn_indices):
                    distance_weight = 1 / (1 + abs(hvn_price - current_price) / current_price)
                    strength_weight = volume_profile[idx] / np.max(volume_profile)
                    weighted_hvns.append((hvn_price, distance_weight * strength_weight))

                # Select HVN with highest combined weight
                best_hvn = max(weighted_hvns, key=lambda x: x[1])
                hvn_levels.append(best_hvn[0])
            else:
                hvn_levels.append(closes.iloc[i])

        return np.array(hvn_levels)

    def _calculate_lvn_levels(self):
        """Calculate Low Volume Node levels with MFI weighting"""
        closes = pd.Series(self.data.Close)
        volumes = pd.Series(self.data.Volume)
        highs = pd.Series(self.data.High)
        lows = pd.Series(self.data.Low)
        lvn_levels = []

        for i in range(len(closes)):
            if i < self.lookback_period:
                lvn_levels.append(closes.iloc[i] if i > 0 else closes.iloc[0])
                continue

            # Get price and volume data for lookback period
            start_idx = i - self.lookback_period + 1
            price_slice = closes.iloc[start_idx:i+1]
            volume_slice = volumes.iloc[start_idx:i+1]
            high_slice = highs.iloc[start_idx:i+1]
            low_slice = lows.iloc[start_idx:i+1]

            # Create price bins for volume profile
            price_min = price_slice.min()
            price_max = price_slice.max()

            if price_max - price_min < 0.01:
                lvn_levels.append(closes.iloc[i])
                continue

            # Create price levels for volume accumulation
            n_bins = 30
            price_bins = np.linspace(price_min, price_max, n_bins)

            # Accumulate volume at each price level with angular and MFI weighting
            volume_profile = np.zeros(n_bins - 1)

            for j, (price, vol, high, low) in enumerate(zip(price_slice, volume_slice,
                                                            high_slice, low_slice)):
                bin_idx = np.searchsorted(price_bins[1:], price)
                if bin_idx < len(volume_profile):
                    # Angular weight increases for recent data
                    angle_weight = 1 + (j / self.lookback_period) * 0.5

                    # Calculate money flow for this bar
                    typical_price = (high + low + price) / 3
                    raw_money_flow = typical_price * vol

                    # Weight by money flow direction
                    if j > 0:
                        prev_typical = (high_slice.iloc[j-1] + low_slice.iloc[j-1] +
                                      price_slice.iloc[j-1]) / 3
                        mf_weight = 1.2 if typical_price > prev_typical else 0.8
                    else:
                        mf_weight = 1.0

                    volume_profile[bin_idx] += vol * angle_weight * mf_weight

            # Find LVN - areas with low money flow
            threshold = np.percentile(volume_profile, 100 - self.volume_percentile)
            lvn_indices = np.where(volume_profile <= threshold)[0]

            if len(lvn_indices) > 0:
                current_price = closes.iloc[i]
                lvn_prices = [(price_bins[idx] + price_bins[idx + 1]) / 2 for idx in lvn_indices]

                # Select LVN closest to current price (most relevant gap)
                closest_lvn = min(lvn_prices, key=lambda x: abs(x - current_price))
                lvn_levels.append(closest_lvn)
            else:
                lvn_levels.append(closes.iloc[i])

        return np.array(lvn_levels)

    def next(self):
        """Execute trading logic with MFI conditions"""
        # Skip if not enough data
        if len(self.data) < self.lookback_period:
            return

        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        hvn = self.hvn_levels[-1]
        lvn = self.lvn_levels[-1]
        mfi = self.mfi[-1]

        # Volume confirmation
        volume_confirmed = current_volume > self.volume_ma[-1] * self.min_volume_ratio

        # MFI conditions
        mfi_oversold = mfi < self.mfi_oversold
        mfi_overbought = mfi > self.mfi_overbought
        mfi_neutral = not mfi_oversold and not mfi_overbought

        # Trend alignment
        bullish_trend = self.ema_9[-1] > self.ema_21[-1]
        bearish_trend = self.ema_9[-1] < self.ema_21[-1]

        if not self.position:
            # Long entry conditions with MFI:
            # 1. Price breaks above HVN or bounces from HVN support
            # 2. MFI is oversold or rising from oversold (not overbought)
            # 3. Volume confirmation
            # 4. Bullish trend alignment
            hvn_breakout = current_price > hvn * self.breakout_threshold
            hvn_bounce = abs(current_price - hvn) / hvn < 0.003 and current_price > hvn

            if ((hvn_breakout or hvn_bounce) and
                (mfi_oversold or (mfi < 50 and mfi > self.mfi[-2] if len(self.mfi) > 1 else False)) and
                not mfi_overbought and
                volume_confirmed and
                bullish_trend):

                # Position sizing based on MFI confidence
                if mfi_oversold:
                    risk_per_trade = 0.03  # Higher risk when deeply oversold
                else:
                    risk_per_trade = 0.02  # Normal risk

                atr_stop = self.atr[-1] * 2
                position_size = min(0.95, risk_per_trade / (atr_stop / current_price))

                self.buy(size=position_size)

            # Short entry conditions with MFI:
            # 1. Price breaks below LVN or gets rejected at LVN resistance
            # 2. MFI is overbought or falling from overbought (not oversold)
            # 3. Volume confirmation
            # 4. Bearish trend alignment
            lvn_breakdown = current_price < lvn / self.breakout_threshold
            lvn_rejection = abs(current_price - lvn) / lvn < 0.003 and current_price < lvn

            if ((lvn_breakdown or lvn_rejection) and
                (mfi_overbought or (mfi > 50 and mfi < self.mfi[-2] if len(self.mfi) > 1 else False)) and
                not mfi_oversold and
                volume_confirmed and
                bearish_trend):

                # Position sizing based on MFI confidence
                if mfi_overbought:
                    risk_per_trade = 0.03  # Higher risk when deeply overbought
                else:
                    risk_per_trade = 0.02  # Normal risk

                atr_stop = self.atr[-1] * 2
                position_size = min(0.95, risk_per_trade / (atr_stop / current_price))

                self.sell(size=position_size)

            # Mean reversion entries at extreme MFI with volume profile support
            # Long at extreme oversold with HVN support
            elif (mfi < 20 and
                  current_price > hvn * 0.995 and
                  current_price < self.bb_lower[-1] * 1.01):

                # Smaller position for mean reversion
                risk_per_trade = 0.015
                atr_stop = self.atr[-1] * 1.5
                position_size = min(0.5, risk_per_trade / (atr_stop / current_price))

                self.buy(size=position_size)

            # Short at extreme overbought with LVN resistance
            elif (mfi > 80 and
                  current_price < lvn * 1.005 and
                  current_price > self.bb_upper[-1] * 0.99):

                # Smaller position for mean reversion
                risk_per_trade = 0.015
                atr_stop = self.atr[-1] * 1.5
                position_size = min(0.5, risk_per_trade / (atr_stop / current_price))

                self.sell(size=position_size)

        else:
            # Exit logic for long positions
            if self.position.is_long:
                entry_price = self.trades[-1].entry_price if self.trades else self.data.Close[-1]

                # Exit conditions:
                # 1. Stop loss hit
                # 2. Take profit reached
                # 3. MFI becomes overbought (momentum exhaustion)
                # 4. Price breaks below HVN (support broken)
                # 5. Bearish divergence (price up, MFI down)
                bearish_divergence = (current_price > entry_price * 1.01 and
                                     mfi < self.mfi[-5] if len(self.mfi) > 5 else False)

                if (current_price <= entry_price * self.stop_loss or
                    current_price >= entry_price * self.take_profit or
                    mfi > self.mfi_overbought + 5 or
                    current_price < hvn * 0.995 or
                    bearish_divergence):
                    self.position.close()

            # Exit logic for short positions
            elif self.position.is_short:
                entry_price = self.trades[-1].entry_price if self.trades else self.data.Close[-1]

                # Exit conditions:
                # 1. Stop loss hit
                # 2. Take profit reached
                # 3. MFI becomes oversold (momentum exhaustion)
                # 4. Price breaks above LVN (resistance broken)
                # 5. Bullish divergence (price down, MFI up)
                bullish_divergence = (current_price < entry_price * 0.99 and
                                     mfi > self.mfi[-5] if len(self.mfi) > 5 else False)

                if (current_price >= entry_price / self.stop_loss or
                    current_price <= entry_price / self.take_profit or
                    mfi < self.mfi_oversold - 5 or
                    current_price > lvn * 1.005 or
                    bullish_divergence):
                    self.position.close()


def main():
    """Run the backtest"""
    # Load data
    data = pd.read_csv('/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/BTCUSD-15m-150wks-data.csv')
    data['datetime'] = pd.to_datetime(data['datetime'])
    data = data.set_index('datetime')

    # Rename columns to match backtesting.py requirements
    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

    # Sort data in ascending order
    data = data.sort_index()

    # Remove any NaN values
    data = data.dropna()

    # Initialize and run backtest
    bt = Backtest(
        data,
        AVPMFIStrategy,
        cash=100000,  # Increased to handle BTC prices
        commission=0.002,
        exclusive_orders=True
    )

    # Run the backtest
    stats = bt.run()

    # Print complete stats
    results = []
    successful_tests = 0

    for i, (symbol, source) in enumerate(data_sources, 1):
        print(f"[{i}/{len(data_sources)}] Testing {symbol} ({source})...", end=' ')

        # Load data
        data = load_data(symbol, source)

        if data is None:
            print("❌ No data found")
            continue

        # Adjust cash based on asset type
        if symbol in ['BTC', 'ETH']:
            cash = 1000000  # Higher for crypto
        else:
            cash = 100000

        # Run backtest
        stats = run_single_backtest(symbol, data, cash)

        if stats is not None:
            successful_tests += 1
            result = {
                'Symbol': symbol,
                'Source': source,
                'Data_Points': len(data),
                'Return_%': round(stats.get('Return [%]', 0), 2),
                'Sharpe': round(stats.get('Sharpe Ratio', 0), 3) if pd.notna(stats.get('Sharpe Ratio')) else 0,
                'Max_DD_%': round(stats.get('Max. Drawdown [%]', 0), 2),
                'Win_Rate_%': round(stats.get('Win Rate [%]', 0), 2) if pd.notna(stats.get('Win Rate [%]')) else 0,
                'Num_Trades': stats.get('# Trades', 0),
                'Profit_Factor': round(stats.get('Profit Factor', 0), 3) if pd.notna(stats.get('Profit Factor')) else 0,
                'Avg_Trade_%': round(stats.get('Avg. Trade [%]', 0), 3) if pd.notna(stats.get('Avg. Trade [%]')) else 0,
                'Buy_Hold_%': round(stats.get('Buy & Hold Return [%]', 0), 2)
            }
            results.append(result)

            # Print summary
            print(f"✅ Return: {result['Return_%']:.1f}%, Sharpe: {result['Sharpe']:.2f}, Trades: {result['Num_Trades']}")
        else:
            print("❌ Backtest failed")

    # Create summary DataFrame
    if results:
        results_df = pd.DataFrame(results)

        # Save to CSV
        os.makedirs('results', exist_ok=True)
        csv_path = 'results/avp_mfi_multi_data_results.csv'
        results_df.to_csv(csv_path, index=False)

        print("\n" + "="*80)
        print("SUMMARY STATISTICS")
        print("="*80)

        # Overall statistics
        print(f"\nSuccessful tests: {successful_tests}/{len(data_sources)}")
        print(f"Average Return: {results_df['Return_%'].mean():.2f}%")
        print(f"Average Sharpe: {results_df['Sharpe'].mean():.3f}")
        print(f"Average Max DD: {results_df['Max_DD_%'].mean():.2f}%")
        print(f"Average Win Rate: {results_df['Win_Rate_%'].mean():.2f}%")
        print(f"Total Trades: {results_df['Num_Trades'].sum()}")

        # Best and worst performers
        print("\n" + "-"*60)
        print("TOP 5 PERFORMERS BY RETURN:")
        print("-"*60)
        top5 = results_df.nlargest(5, 'Return_%')[['Symbol', 'Source', 'Return_%', 'Sharpe', 'Num_Trades']]
        print(top5.to_string(index=False))

        print("\n" + "-"*60)
        print("TOP 5 PERFORMERS BY SHARPE RATIO:")
        print("-"*60)
        top5_sharpe = results_df.nlargest(5, 'Sharpe')[['Symbol', 'Source', 'Sharpe', 'Return_%', 'Num_Trades']]
        print(top5_sharpe.to_string(index=False))

        print("\n" + "-"*60)
        print("BOTTOM 5 PERFORMERS:")
        print("-"*60)
        bottom5 = results_df.nsmallest(5, 'Return_%')[['Symbol', 'Source', 'Return_%', 'Sharpe', 'Max_DD_%']]
        print(bottom5.to_string(index=False))

        # Group by source type
        print("\n" + "-"*60)
        print("PERFORMANCE BY DATA SOURCE:")
        print("-"*60)
        source_summary = results_df.groupby('Source').agg({
            'Return_%': 'mean',
            'Sharpe': 'mean',
            'Win_Rate_%': 'mean',
            'Num_Trades': 'mean'
        }).round(2)
        print(source_summary.to_string())

        print("\n" + "="*80)
        print(f"Results saved to: {os.path.abspath(csv_path)}")
        print("="*80)

        return results_df
    else:
        print("\n❌ No successful backtests completed")
        return None


if __name__ == "__main__":
    results = main()
    if results is not None and len(results) > 0:
        print("\n" + "="*80)
        print("AVP + MFI STRATEGY - MULTI-DATA TEST COMPLETE")
        print(f"Successfully tested on {len(results)} data sources")
        print("="*80)