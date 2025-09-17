"""
Angled Volume Profile + VWAP Strategy
Combines AVP with VWAP as a trend filter for improved entries
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import os
import glob

class AVPVWAPStrategy(Strategy):
    # Parameters
    lookback_period = 50  # Bars for volume profile calculation
    volume_percentile = 60  # Percentile for HVN identification
    vwap_bands_std = 2  # Standard deviations for VWAP bands
    breakout_threshold = 1.002  # Price must break HVN by 0.2%
    stop_loss = 0.98  # 2% stop loss
    take_profit = 1.035  # 3.5% take profit
    min_volume_ratio = 1.5  # Volume must be 1.5x average for confirmation

    def init(self):
        """Initialize indicators including VWAP"""
        # Calculate volume moving average
        self.volume_ma = self.I(ta.sma, pd.Series(self.data.Volume), length=20)

        # Calculate VWAP and bands
        high_series = pd.Series(self.data.High)
        low_series = pd.Series(self.data.Low)
        close_series = pd.Series(self.data.Close)
        volume_series = pd.Series(self.data.Volume)

        # VWAP calculation
        self.vwap = self.I(self._calculate_vwap)
        self.vwap_upper = self.I(self._calculate_vwap_upper)
        self.vwap_lower = self.I(self._calculate_vwap_lower)

        # Volume profile levels
        self.hvn_levels = self.I(self._calculate_hvn_levels)
        self.lvn_levels = self.I(self._calculate_lvn_levels)

        # Additional indicators
        self.rsi = self.I(ta.rsi, close_series, length=14)
        self.atr = self.I(ta.atr, high_series, low_series, close_series, length=14)

    def _calculate_vwap(self):
        """Calculate VWAP (Volume Weighted Average Price)"""
        typical_price = (self.data.High + self.data.Low + self.data.Close) / 3
        cumulative_tpv = np.cumsum(typical_price * self.data.Volume)
        cumulative_volume = np.cumsum(self.data.Volume)

        # Reset VWAP daily (every 96 bars for 15-min data)
        vwap_values = []
        reset_period = 96  # 24 hours * 4 (15-min bars per hour)

        for i in range(len(typical_price)):
            if i % reset_period == 0:
                # Reset accumulation
                period_start = i
                period_tpv = 0
                period_volume = 0

            period_tpv += typical_price[i] * self.data.Volume[i]
            period_volume += self.data.Volume[i]

            if period_volume > 0:
                vwap_values.append(period_tpv / period_volume)
            else:
                vwap_values.append(typical_price[i])

        return np.array(vwap_values)

    def _calculate_vwap_upper(self):
        """Calculate upper VWAP band"""
        vwap = self._calculate_vwap()
        typical_price = (self.data.High + self.data.Low + self.data.Close) / 3

        # Calculate rolling standard deviation
        deviations = []
        reset_period = 96

        for i in range(len(typical_price)):
            if i % reset_period == 0:
                period_prices = []

            period_prices.append(typical_price[i])

            if len(period_prices) > 1:
                std_dev = np.std(period_prices)
                deviations.append(vwap[i] + self.vwap_bands_std * std_dev)
            else:
                deviations.append(vwap[i])

        return np.array(deviations)

    def _calculate_vwap_lower(self):
        """Calculate lower VWAP band"""
        vwap = self._calculate_vwap()
        typical_price = (self.data.High + self.data.Low + self.data.Close) / 3

        # Calculate rolling standard deviation
        deviations = []
        reset_period = 96

        for i in range(len(typical_price)):
            if i % reset_period == 0:
                period_prices = []

            period_prices.append(typical_price[i])

            if len(period_prices) > 1:
                std_dev = np.std(period_prices)
                deviations.append(vwap[i] - self.vwap_bands_std * std_dev)
            else:
                deviations.append(vwap[i])

        return np.array(deviations)

    def _calculate_hvn_levels(self):
        """Calculate High Volume Node levels"""
        closes = pd.Series(self.data.Close)
        volumes = pd.Series(self.data.Volume)
        hvn_levels = []

        for i in range(len(closes)):
            if i < self.lookback_period:
                hvn_levels.append(closes.iloc[i] if i > 0 else closes.iloc[0])
                continue

            # Get price and volume data for lookback period
            start_idx = i - self.lookback_period + 1
            price_slice = closes.iloc[start_idx:i+1]
            volume_slice = volumes.iloc[start_idx:i+1]

            # Create price bins for volume profile
            price_min = price_slice.min()
            price_max = price_slice.max()

            if price_max - price_min < 0.01:
                hvn_levels.append(closes.iloc[i])
                continue

            # Create price levels for volume accumulation
            n_bins = 25  # More bins for better resolution
            price_bins = np.linspace(price_min, price_max, n_bins)

            # Accumulate volume at each price level with angular weighting
            volume_profile = np.zeros(n_bins - 1)

            for j, (price, vol) in enumerate(zip(price_slice, volume_slice)):
                bin_idx = np.searchsorted(price_bins[1:], price)
                if bin_idx < len(volume_profile):
                    # Angular weight increases for recent data
                    angle_weight = 1 + (j / self.lookback_period)
                    volume_profile[bin_idx] += vol * angle_weight

            # Find HVN
            threshold = np.percentile(volume_profile, self.volume_percentile)
            hvn_indices = np.where(volume_profile >= threshold)[0]

            if len(hvn_indices) > 0:
                current_price = closes.iloc[i]
                hvn_prices = [(price_bins[idx] + price_bins[idx + 1]) / 2 for idx in hvn_indices]
                # Get HVN closest to but below current price (support)
                support_hvns = [p for p in hvn_prices if p < current_price]
                if support_hvns:
                    hvn_levels.append(max(support_hvns))
                else:
                    hvn_levels.append(min(hvn_prices))
            else:
                hvn_levels.append(closes.iloc[i])

        return np.array(hvn_levels)

    def _calculate_lvn_levels(self):
        """Calculate Low Volume Node levels"""
        closes = pd.Series(self.data.Close)
        volumes = pd.Series(self.data.Volume)
        lvn_levels = []

        for i in range(len(closes)):
            if i < self.lookback_period:
                lvn_levels.append(closes.iloc[i] if i > 0 else closes.iloc[0])
                continue

            # Get price and volume data for lookback period
            start_idx = i - self.lookback_period + 1
            price_slice = closes.iloc[start_idx:i+1]
            volume_slice = volumes.iloc[start_idx:i+1]

            # Create price bins for volume profile
            price_min = price_slice.min()
            price_max = price_slice.max()

            if price_max - price_min < 0.01:
                lvn_levels.append(closes.iloc[i])
                continue

            # Create price levels for volume accumulation
            n_bins = 25
            price_bins = np.linspace(price_min, price_max, n_bins)

            # Accumulate volume at each price level with angular weighting
            volume_profile = np.zeros(n_bins - 1)

            for j, (price, vol) in enumerate(zip(price_slice, volume_slice)):
                bin_idx = np.searchsorted(price_bins[1:], price)
                if bin_idx < len(volume_profile):
                    # Angular weight increases for recent data
                    angle_weight = 1 + (j / self.lookback_period)
                    volume_profile[bin_idx] += vol * angle_weight

            # Find LVN
            threshold = np.percentile(volume_profile, 100 - self.volume_percentile)
            lvn_indices = np.where(volume_profile <= threshold)[0]

            if len(lvn_indices) > 0:
                current_price = closes.iloc[i]
                lvn_prices = [(price_bins[idx] + price_bins[idx + 1]) / 2 for idx in lvn_indices]
                # Get LVN closest to but above current price (resistance)
                resistance_lvns = [p for p in lvn_prices if p > current_price]
                if resistance_lvns:
                    lvn_levels.append(min(resistance_lvns))
                else:
                    lvn_levels.append(max(lvn_prices))
            else:
                lvn_levels.append(closes.iloc[i])

        return np.array(lvn_levels)

    def next(self):
        """Execute trading logic with VWAP filter"""
        # Skip if not enough data
        if len(self.data) < self.lookback_period:
            return

        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        hvn = self.hvn_levels[-1]
        lvn = self.lvn_levels[-1]
        vwap = self.vwap[-1]
        vwap_upper = self.vwap_upper[-1]
        vwap_lower = self.vwap_lower[-1]

        # Volume confirmation
        volume_confirmed = current_volume > self.volume_ma[-1] * self.min_volume_ratio

        # VWAP position relative to price
        above_vwap = current_price > vwap
        near_vwap = abs(current_price - vwap) / vwap < 0.005  # Within 0.5% of VWAP

        if not self.position:
            # Long entry conditions with VWAP filter:
            # 1. Price breaks above HVN
            # 2. Price is above VWAP (bullish trend)
            # 3. Price hasn't exceeded upper VWAP band (not overextended)
            # 4. Volume confirmation
            # 5. RSI not overbought
            if (current_price > hvn * self.breakout_threshold and
                above_vwap and
                current_price < vwap_upper and
                volume_confirmed and
                self.rsi[-1] < 70):

                # Enhanced position sizing
                risk_per_trade = 0.025  # Risk 2.5% when VWAP confirms
                atr_stop = self.atr[-1] * 1.5
                position_size = min(0.95, risk_per_trade / (atr_stop / current_price))

                self.buy(size=position_size)

            # Short entry conditions with VWAP filter:
            # 1. Price breaks below LVN
            # 2. Price is below VWAP (bearish trend)
            # 3. Price hasn't exceeded lower VWAP band (not oversold)
            # 4. Volume confirmation
            # 5. RSI not oversold
            elif (current_price < lvn / self.breakout_threshold and
                  not above_vwap and
                  current_price > vwap_lower and
                  volume_confirmed and
                  self.rsi[-1] > 30):

                # Enhanced position sizing
                risk_per_trade = 0.025
                atr_stop = self.atr[-1] * 1.5
                position_size = min(0.95, risk_per_trade / (atr_stop / current_price))

                self.sell(size=position_size)

            # VWAP mean reversion entry (additional opportunity)
            # Long when price touches lower VWAP band with HVN support
            elif (abs(current_price - vwap_lower) / vwap_lower < 0.002 and
                  current_price > hvn * 0.995 and
                  self.rsi[-1] < 35):

                # Smaller position for mean reversion
                risk_per_trade = 0.015
                atr_stop = self.atr[-1]
                position_size = min(0.5, risk_per_trade / (atr_stop / current_price))

                self.buy(size=position_size)

        else:
            # Exit logic for long positions
            if self.position.is_long:
                entry_price = self.trades[-1].entry_price if self.trades else self.data.Close[-1]

                # Exit conditions:
                # 1. Stop loss hit
                # 2. Take profit reached
                # 3. Price crosses below VWAP (trend reversal)
                # 4. Price hits upper VWAP band (overextended)
                if (current_price <= entry_price * self.stop_loss or
                    current_price >= entry_price * self.take_profit or
                    (not above_vwap and not near_vwap) or
                    current_price >= vwap_upper * 0.998):
                    self.position.close()

            # Exit logic for short positions
            elif self.position.is_short:
                entry_price = self.trades[-1].entry_price if self.trades else self.data.Close[-1]

                # Exit conditions:
                # 1. Stop loss hit
                # 2. Take profit reached
                # 3. Price crosses above VWAP (trend reversal)
                # 4. Price hits lower VWAP band (oversold)
                if (current_price >= entry_price / self.stop_loss or
                    current_price <= entry_price / self.take_profit or
                    (above_vwap and not near_vwap) or
                    current_price <= vwap_lower * 1.002):
                    self.position.close()


def load_data(symbol, data_source='crypto'):
    """Load data for a specific symbol"""
    try:
        if data_source == 'crypto_15m':
            # Try different file naming patterns for crypto 15m data
            paths = [
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}USD-15m-150wks-data.csv',
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}USD-15m-100wks-data.csv',
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}-15m-150wks-data.csv'
            ]
            for path in paths:
                if pd.io.common.file_exists(path):
                    data = pd.read_csv(path, parse_dates=['datetime'], index_col='datetime')
                    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    return data
        elif data_source == 'crypto_1h':
            paths = [
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}USD-1h-250wks-data.csv',
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}USD-1h-500wks-data.csv',
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}USD-1h-100wks-data.csv'
            ]
            for path in paths:
                if pd.io.common.file_exists(path):
                    data = pd.read_csv(path, parse_dates=['datetime'], index_col='datetime')
                    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    return data
        elif data_source == 'crypto_1d':
            paths = [
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}USD-1d-1000wks-data.csv',
                f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/coinbase/{symbol}USD-1d-100wks-data.csv'
            ]
            for path in paths:
                if pd.io.common.file_exists(path):
                    data = pd.read_csv(path, parse_dates=['datetime'], index_col='datetime')
                    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    return data
        elif data_source == 'yahoo_daily':
            path = f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/yahoo_daily/{symbol}_stock_1d.csv'
            if pd.io.common.file_exists(path):
                data = pd.read_csv(path, parse_dates=['Date'], index_col='Date')
                # Keep only OHLCV columns
                data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
                return data
        elif data_source == 'yahoo_hourly':
            path = f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/yahoo_hourly/{symbol}_hourly.csv'
            if pd.io.common.file_exists(path):
                data = pd.read_csv(path, parse_dates=['Datetime'], index_col='Datetime')
                # Drop Adj Close if it exists
                if 'Adj Close' in data.columns:
                    data = data.drop('Adj Close', axis=1)
                data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                return data
        elif data_source == 'ib_data':
            # Interactive Brokers data
            pattern = f'/Users/md/Dropbox/dev/github/moon-dev-trading-bots/data/IB_data/{symbol}_*.csv'
            files = glob.glob(pattern)
            if files:
                # Use the first matching file
                data = pd.read_csv(files[0], parse_dates=['date'], index_col='date')
                data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                return data

        return None
    except Exception as e:
        print(f"Error loading {symbol} from {data_source}: {e}")
        return None


def run_single_backtest(symbol, data, cash=100000):
    """Run backtest for a single symbol"""
    try:
        # Sort and clean data
        data = data.sort_index()
        data = data.dropna()

        # Skip if not enough data
        if len(data) < 200:
            return None

        # Initialize and run backtest
        bt = Backtest(
            data,
            AVPVWAPStrategy,
            cash=cash,
            commission=0.002,
            exclusive_orders=True
        )

        # Run the backtest
        stats = bt.run()

        return stats
    except Exception as e:
        print(f"Error running backtest for {symbol}: {e}")
        return None


def main():
    """Run the backtest on multiple data sources"""

    # Define all 25 data sources
    data_sources = [
        # Crypto pairs (Coinbase 15m when available, fallback to 1h or 1d)
        ('BTC', 'crypto_15m'),
        ('ETH', 'crypto_15m'),
        ('SOL', 'crypto_15m'),
        ('BTC', 'crypto_1h'),  # Additional BTC on different timeframe
        ('ETH', 'crypto_1h'),  # Additional ETH on different timeframe
        ('SOL', 'crypto_1h'),  # Additional SOL on different timeframe
        ('BTC', 'crypto_1d'),  # Daily BTC
        ('ETH', 'crypto_1d'),  # Daily ETH
        ('SOL', 'crypto_1d'),  # Daily SOL

        # Stock indices and major stocks (Yahoo)
        ('AAPL', 'yahoo_daily'),
        ('GOOGL', 'yahoo_daily'),
        ('MSFT', 'yahoo_daily'),
        ('AMZN', 'yahoo_daily'),

        # Yahoo hourly data
        ('AAPL', 'yahoo_hourly'),
        ('GOOG', 'yahoo_hourly'),
        ('NVDA', 'yahoo_hourly'),
        ('TSLA', 'yahoo_hourly'),

        # Interactive Brokers data
        ('AAPL', 'ib_data'),
        ('TSLA', 'ib_data'),
        ('ES', 'ib_data'),  # S&P 500 futures
        ('NQ', 'ib_data'),  # NASDAQ futures
    ]

    # Add more if we find them in a scan
    additional_yahoo = ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'GLD', 'SLV', 'USO']
    for symbol in additional_yahoo:
        data_sources.append((symbol, 'yahoo_daily'))

    print("\n" + "="*80)
    print("ANGLED VOLUME PROFILE + VWAP STRATEGY - MULTI-DATA TEST")
    print("="*80)
    print(f"Testing on {len(data_sources)} data sources")
    print("="*80 + "\n")

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
        csv_path = 'results/avp_vwap_multi_data_results.csv'
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
        print("AVP + VWAP STRATEGY - MULTI-DATA TEST COMPLETE")
        print(f"Successfully tested on {len(results)} data sources")
        print("="*80)