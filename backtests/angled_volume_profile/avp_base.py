"""
Angled Volume Profile Base Strategy
Uses volume profile analysis to identify high/low volume nodes as support/resistance
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import os
import glob

class AVPBaseStrategy(Strategy):
    # Parameters
    lookback_period = 50  # Bars for volume profile calculation (reduced for more signals)
    volume_percentile = 60  # Percentile for HVN identification (reduced for more sensitivity)
    breakout_threshold = 1.001  # Price must break HVN by 0.1% (reduced for more signals)
    stop_loss = 0.985  # 1.5% stop loss
    take_profit = 1.025  # 2.5% take profit
    min_volume_ratio = 1.2  # Volume must be 1.2x average for confirmation (reduced)

    def init(self):
        """Initialize indicators and volume profile calculations"""
        # Calculate volume moving average for comparison
        self.volume_ma = self.I(ta.sma, pd.Series(self.data.Volume), length=20)

        # Calculate rolling volume profile levels
        self.hvn_levels = self.I(self._calculate_hvn_levels)
        self.lvn_levels = self.I(self._calculate_lvn_levels)

        # Price action indicators
        self.sma_50 = self.I(ta.sma, pd.Series(self.data.Close), length=50)
        self.sma_200 = self.I(ta.sma, pd.Series(self.data.Close), length=200)

        # ATR for dynamic stops
        high_series = pd.Series(self.data.High)
        low_series = pd.Series(self.data.Low)
        close_series = pd.Series(self.data.Close)
        self.atr = self.I(ta.atr, high_series, low_series, close_series, length=14)

    def _calculate_hvn_levels(self):
        """Calculate High Volume Node levels using angled volume profile concept"""
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

            if price_max - price_min < 0.01:  # Avoid division by zero
                hvn_levels.append(closes.iloc[i])
                continue

            # Create 20 price levels (bins) for volume accumulation
            n_bins = 20
            price_bins = np.linspace(price_min, price_max, n_bins)

            # Accumulate volume at each price level
            volume_profile = np.zeros(n_bins - 1)

            for j, (price, vol) in enumerate(zip(price_slice, volume_slice)):
                # Find which bin this price belongs to
                bin_idx = np.searchsorted(price_bins[1:], price)
                if bin_idx < len(volume_profile):
                    # Apply angular weight (recent prices get more weight)
                    angle_weight = (j + 1) / self.lookback_period
                    volume_profile[bin_idx] += vol * angle_weight

            # Find HVN (high volume node) - price level with high volume
            threshold = np.percentile(volume_profile, self.volume_percentile)
            hvn_indices = np.where(volume_profile >= threshold)[0]

            if len(hvn_indices) > 0:
                # Get the price level of the highest volume node closest to current price
                current_price = closes.iloc[i]
                hvn_prices = [(price_bins[idx] + price_bins[idx + 1]) / 2 for idx in hvn_indices]
                closest_hvn = min(hvn_prices, key=lambda x: abs(x - current_price))
                hvn_levels.append(closest_hvn)
            else:
                hvn_levels.append(closes.iloc[i])

        return np.array(hvn_levels)

    def _calculate_lvn_levels(self):
        """Calculate Low Volume Node levels using angled volume profile concept"""
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

            if price_max - price_min < 0.01:  # Avoid division by zero
                lvn_levels.append(closes.iloc[i])
                continue

            # Create 20 price levels (bins) for volume accumulation
            n_bins = 20
            price_bins = np.linspace(price_min, price_max, n_bins)

            # Accumulate volume at each price level
            volume_profile = np.zeros(n_bins - 1)

            for j, (price, vol) in enumerate(zip(price_slice, volume_slice)):
                # Find which bin this price belongs to
                bin_idx = np.searchsorted(price_bins[1:], price)
                if bin_idx < len(volume_profile):
                    # Apply angular weight (recent prices get more weight)
                    angle_weight = (j + 1) / self.lookback_period
                    volume_profile[bin_idx] += vol * angle_weight

            # Find LVN (low volume node) - price level with low volume
            threshold = np.percentile(volume_profile, 100 - self.volume_percentile)
            lvn_indices = np.where(volume_profile <= threshold)[0]

            if len(lvn_indices) > 0:
                # Get the price level of the lowest volume node closest to current price
                current_price = closes.iloc[i]
                lvn_prices = [(price_bins[idx] + price_bins[idx + 1]) / 2 for idx in lvn_indices]
                closest_lvn = min(lvn_prices, key=lambda x: abs(x - current_price))
                lvn_levels.append(closest_lvn)
            else:
                lvn_levels.append(closes.iloc[i])

        return np.array(lvn_levels)

    def next(self):
        """Execute trading logic based on volume profile analysis"""
        # Skip if not enough data
        if len(self.data) < self.lookback_period:
            return

        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        hvn = self.hvn_levels[-1]
        lvn = self.lvn_levels[-1]

        # Volume confirmation
        volume_confirmed = current_volume > self.volume_ma[-1] * self.min_volume_ratio

        # Check for existing position
        if not self.position:
            # Long entry conditions:
            # 1. Price breaks above HVN with volume
            # 2. Price is above 50 SMA (trend filter)
            # 3. Volume confirmation
            if (current_price > hvn * self.breakout_threshold and
                current_price > self.sma_50[-1] and
                volume_confirmed):

                # Calculate position size based on ATR
                risk_per_trade = 0.02  # Risk 2% of equity
                atr_stop = self.atr[-1] * 2
                position_size = min(0.95, risk_per_trade / (atr_stop / current_price))

                # Enter long position
                self.buy(size=position_size)

            # Short entry conditions:
            # 1. Price breaks below LVN with volume
            # 2. Price is below 50 SMA (trend filter)
            # 3. Volume confirmation
            elif (current_price < lvn / self.breakout_threshold and
                  current_price < self.sma_50[-1] and
                  volume_confirmed):

                # Calculate position size based on ATR
                risk_per_trade = 0.02  # Risk 2% of equity
                atr_stop = self.atr[-1] * 2
                position_size = min(0.95, risk_per_trade / (atr_stop / current_price))

                # Enter short position
                self.sell(size=position_size)

        else:
            # Exit logic for long positions
            if self.position.is_long:
                entry_price = self.trades[-1].entry_price if self.trades else self.data.Close[-1]

                # Exit conditions:
                # 1. Stop loss hit
                # 2. Take profit reached
                # 3. Price falls back below HVN (support broken)
                if (current_price <= entry_price * self.stop_loss or
                    current_price >= entry_price * self.take_profit or
                    current_price < hvn * 0.995):
                    self.position.close()

            # Exit logic for short positions
            elif self.position.is_short:
                entry_price = self.trades[-1].entry_price if self.trades else self.data.Close[-1]

                # Exit conditions:
                # 1. Stop loss hit (price rises above entry)
                # 2. Take profit reached (price falls below entry)
                # 3. Price rises back above LVN (resistance broken)
                if (current_price >= entry_price / self.stop_loss or
                    current_price <= entry_price / self.take_profit or
                    current_price > lvn * 1.005):
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
            import glob
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
            AVPBaseStrategy,
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
    print("ANGLED VOLUME PROFILE - BASE STRATEGY - MULTI-DATA TEST")
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
        import os
        results_df = pd.DataFrame(results)

        # Save to CSV
        os.makedirs('results', exist_ok=True)
        csv_path = 'results/avp_base_multi_data_results.csv'
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
        print("AVP BASE STRATEGY - MULTI-DATA TEST COMPLETE")
        print(f"Successfully tested on {len(results)} data sources")
        print("="*80)