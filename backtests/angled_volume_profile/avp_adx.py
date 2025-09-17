"""
Angled Volume Profile + ADX Strategy
Combines AVP with ADX for trend strength confirmation
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
import os
import glob

class AVPADXStrategy(Strategy):
    # Parameters
    lookback_period = 50  # Bars for volume profile calculation
    volume_percentile = 60  # Percentile for HVN identification
    adx_period = 14  # ADX period
    adx_threshold = 25  # Minimum ADX for trend trading
    adx_strong = 40  # Strong trend threshold
    di_threshold = 20  # Minimum DI for directional bias
    breakout_threshold = 1.002  # Price must break HVN by 0.2%
    stop_loss = 0.98  # 2% stop loss
    take_profit = 1.045  # 4.5% take profit
    min_volume_ratio = 1.4  # Volume must be 1.4x average

    def init(self):
        """Initialize indicators including ADX"""
        # Calculate volume moving average
        self.volume_ma = self.I(ta.sma, pd.Series(self.data.Volume), length=20)

        # Calculate ADX and directional indicators
        high_series = pd.Series(self.data.High)
        low_series = pd.Series(self.data.Low)
        close_series = pd.Series(self.data.Close)

        # ADX calculation with DI+ and DI-
        adx_result = ta.adx(high_series, low_series, close_series, length=self.adx_period)
        if adx_result is not None and not adx_result.empty:
            self.adx = self.I(lambda: adx_result[f'ADX_{self.adx_period}'].values)
            self.di_plus = self.I(lambda: adx_result[f'DMP_{self.adx_period}'].values)
            self.di_minus = self.I(lambda: adx_result[f'DMN_{self.adx_period}'].values)
        else:
            # Fallback if ADX calculation fails
            self.adx = self.I(lambda: np.full(len(close_series), 25))
            self.di_plus = self.I(lambda: np.full(len(close_series), 20))
            self.di_minus = self.I(lambda: np.full(len(close_series), 20))

        # Volume profile levels
        self.hvn_levels = self.I(self._calculate_hvn_levels)
        self.lvn_levels = self.I(self._calculate_lvn_levels)

        # Additional trend indicators
        self.ema_20 = self.I(ta.ema, close_series, length=20)
        self.ema_50 = self.I(ta.ema, close_series, length=50)
        self.atr = self.I(ta.atr, high_series, low_series, close_series, length=14)

        # MACD for momentum confirmation
        macd_result = ta.macd(close_series, fast=12, slow=26, signal=9)
        if macd_result is not None and not macd_result.empty:
            self.macd = self.I(lambda: macd_result['MACD_12_26_9'].values)
            self.macd_signal = self.I(lambda: macd_result['MACDs_12_26_9'].values)
            self.macd_histogram = self.I(lambda: macd_result['MACDh_12_26_9'].values)
        else:
            # Fallback
            self.macd = self.I(ta.ema, close_series, length=12)
            self.macd_signal = self.I(ta.ema, close_series, length=26)
            self.macd_histogram = self.I(lambda: np.zeros(len(close_series)))

    def _calculate_hvn_levels(self):
        """Calculate High Volume Node levels with trend strength weighting"""
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
            n_bins = 25
            price_bins = np.linspace(price_min, price_max, n_bins)

            # Accumulate volume at each price level with angular and trend weighting
            volume_profile = np.zeros(n_bins - 1)

            for j, (price, vol, high, low) in enumerate(zip(price_slice, volume_slice,
                                                            high_slice, low_slice)):
                bin_idx = np.searchsorted(price_bins[1:], price)
                if bin_idx < len(volume_profile):
                    # Angular weight increases for recent data
                    angle_weight = 1 + (j / self.lookback_period) * 0.7

                    # Calculate true range for volatility weighting
                    if j > 0:
                        prev_close = price_slice.iloc[j-1]
                        true_range = max(high - low,
                                        abs(high - prev_close),
                                        abs(low - prev_close))
                        # Higher volatility = more significant level
                        volatility_weight = 1 + (true_range / price) * 10
                    else:
                        volatility_weight = 1.0

                    volume_profile[bin_idx] += vol * angle_weight * volatility_weight

            # Find HVN with emphasis on high volatility areas
            threshold = np.percentile(volume_profile, self.volume_percentile)
            hvn_indices = np.where(volume_profile >= threshold)[0]

            if len(hvn_indices) > 0:
                current_price = closes.iloc[i]
                hvn_prices = [(price_bins[idx] + price_bins[idx + 1]) / 2 for idx in hvn_indices]

                # Select HVN based on strength and proximity
                best_hvn = None
                best_score = 0

                for hvn_price, idx in zip(hvn_prices, hvn_indices):
                    # Prefer HVNs that have been tested multiple times
                    touches = sum(1 for p in price_slice if abs(p - hvn_price) / hvn_price < 0.005)
                    touch_score = min(touches / 5, 1)  # Normalize to max 1

                    # Proximity score
                    distance = abs(hvn_price - current_price) / current_price
                    proximity_score = 1 / (1 + distance * 10)

                    # Volume strength score
                    strength_score = volume_profile[idx] / np.max(volume_profile)

                    # Combined score
                    total_score = touch_score * 0.3 + proximity_score * 0.4 + strength_score * 0.3

                    if total_score > best_score:
                        best_score = total_score
                        best_hvn = hvn_price

                hvn_levels.append(best_hvn if best_hvn else closes.iloc[i])
            else:
                hvn_levels.append(closes.iloc[i])

        return np.array(hvn_levels)

    def _calculate_lvn_levels(self):
        """Calculate Low Volume Node levels with trend strength weighting"""
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
            n_bins = 25
            price_bins = np.linspace(price_min, price_max, n_bins)

            # Accumulate volume at each price level
            volume_profile = np.zeros(n_bins - 1)

            for j, (price, vol, high, low) in enumerate(zip(price_slice, volume_slice,
                                                            high_slice, low_slice)):
                bin_idx = np.searchsorted(price_bins[1:], price)
                if bin_idx < len(volume_profile):
                    # Angular weight increases for recent data
                    angle_weight = 1 + (j / self.lookback_period) * 0.7

                    # Calculate true range for volatility weighting
                    if j > 0:
                        prev_close = price_slice.iloc[j-1]
                        true_range = max(high - low,
                                        abs(high - prev_close),
                                        abs(low - prev_close))
                        volatility_weight = 1 + (true_range / price) * 10
                    else:
                        volatility_weight = 1.0

                    volume_profile[bin_idx] += vol * angle_weight * volatility_weight

            # Find LVN - gaps in volume profile
            threshold = np.percentile(volume_profile, 100 - self.volume_percentile)
            lvn_indices = np.where(volume_profile <= threshold)[0]

            if len(lvn_indices) > 0:
                current_price = closes.iloc[i]
                lvn_prices = [(price_bins[idx] + price_bins[idx + 1]) / 2 for idx in lvn_indices]

                # Find LVN that represents a true gap (not just low volume)
                best_lvn = None
                best_gap_score = 0

                for lvn_price, idx in zip(lvn_prices, lvn_indices):
                    # Check if this is a real gap (low volume surrounded by higher volume)
                    gap_score = 0
                    if idx > 0 and idx < len(volume_profile) - 1:
                        surrounding_avg = (volume_profile[idx-1] + volume_profile[idx+1]) / 2
                        if surrounding_avg > 0:
                            gap_score = surrounding_avg / (volume_profile[idx] + 1)

                    if gap_score > best_gap_score:
                        best_gap_score = gap_score
                        best_lvn = lvn_price

                lvn_levels.append(best_lvn if best_lvn else closes.iloc[i])
            else:
                lvn_levels.append(closes.iloc[i])

        return np.array(lvn_levels)

    def next(self):
        """Execute trading logic with ADX trend strength confirmation"""
        # Skip if not enough data
        if len(self.data) < self.lookback_period:
            return

        current_price = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        hvn = self.hvn_levels[-1]
        lvn = self.lvn_levels[-1]
        adx = self.adx[-1]
        di_plus = self.di_plus[-1]
        di_minus = self.di_minus[-1]

        # Volume confirmation
        volume_confirmed = current_volume > self.volume_ma[-1] * self.min_volume_ratio

        # ADX trend strength assessment
        trending = adx > self.adx_threshold
        strong_trend = adx > self.adx_strong
        bullish_bias = di_plus > di_minus and di_plus > self.di_threshold
        bearish_bias = di_minus > di_plus and di_minus > self.di_threshold

        # MACD momentum
        macd_bullish = self.macd[-1] > self.macd_signal[-1]
        macd_bearish = self.macd[-1] < self.macd_signal[-1]

        # EMA trend
        ema_bullish = self.ema_20[-1] > self.ema_50[-1]
        ema_bearish = self.ema_20[-1] < self.ema_50[-1]

        if not self.position:
            # Long entry conditions with ADX:
            # 1. Price breaks above HVN (or bounces in strong trend)
            # 2. ADX confirms trending market
            # 3. DI+ > DI- (bullish directional movement)
            # 4. Volume confirmation
            # 5. MACD and EMA alignment
            hvn_breakout = current_price > hvn * self.breakout_threshold
            hvn_bounce = (abs(current_price - hvn) / hvn < 0.003 and
                         current_price > hvn and strong_trend)

            if ((hvn_breakout or hvn_bounce) and
                trending and
                bullish_bias and
                volume_confirmed and
                macd_bullish and
                ema_bullish):

                # Position sizing based on trend strength
                if strong_trend:
                    risk_per_trade = 0.03  # Higher risk in strong trends
                elif trending:
                    risk_per_trade = 0.02  # Normal risk in moderate trends
                else:
                    risk_per_trade = 0.015  # Lower risk in weak trends

                # Tighter stops in strong trends
                atr_multiplier = 1.5 if strong_trend else 2
                atr_stop = self.atr[-1] * atr_multiplier
                position_size = min(0.95, risk_per_trade / (atr_stop / current_price))

                self.buy(size=position_size)

            # Short entry conditions with ADX:
            # 1. Price breaks below LVN (or rejection in strong trend)
            # 2. ADX confirms trending market
            # 3. DI- > DI+ (bearish directional movement)
            # 4. Volume confirmation
            # 5. MACD and EMA alignment
            lvn_breakdown = current_price < lvn / self.breakout_threshold
            lvn_rejection = (abs(current_price - lvn) / lvn < 0.003 and
                           current_price < lvn and strong_trend)

            if ((lvn_breakdown or lvn_rejection) and
                  trending and
                  bearish_bias and
                  volume_confirmed and
                  macd_bearish and
                  ema_bearish):

                # Position sizing based on trend strength
                if strong_trend:
                    risk_per_trade = 0.03  # Higher risk in strong trends
                elif trending:
                    risk_per_trade = 0.02  # Normal risk in moderate trends
                else:
                    risk_per_trade = 0.015  # Lower risk in weak trends

                # Tighter stops in strong trends
                atr_multiplier = 1.5 if strong_trend else 2
                atr_stop = self.atr[-1] * atr_multiplier
                position_size = min(0.95, risk_per_trade / (atr_stop / current_price))

                self.sell(size=position_size)

            # Range trading when ADX is low (non-trending market)
            # Long at HVN support in ranging market
            if (adx < 20 and
                  abs(current_price - hvn) / hvn < 0.002 and
                  current_price > hvn and
                  di_plus > di_minus):

                # Smaller position for range trading
                risk_per_trade = 0.01
                atr_stop = self.atr[-1]
                position_size = min(0.3, risk_per_trade / (atr_stop / current_price))

                self.buy(size=position_size)

            # Short at LVN resistance in ranging market
            if (adx < 20 and
                  abs(current_price - lvn) / lvn < 0.002 and
                  current_price < lvn and
                  di_minus > di_plus):

                # Smaller position for range trading
                risk_per_trade = 0.01
                atr_stop = self.atr[-1]
                position_size = min(0.3, risk_per_trade / (atr_stop / current_price))

                self.sell(size=position_size)

        else:
            # Exit logic for long positions
            if self.position.is_long:
                entry_price = self.trades[-1].entry_price if self.trades else self.data.Close[-1]

                # Dynamic exit based on ADX
                if strong_trend and bullish_bias:
                    # Let profits run in strong trends
                    dynamic_take_profit = self.take_profit * 1.2
                    dynamic_stop_loss = self.stop_loss * 1.01  # Looser stop
                else:
                    dynamic_take_profit = self.take_profit
                    dynamic_stop_loss = self.stop_loss

                # Exit conditions:
                # 1. Stop loss hit
                # 2. Take profit reached
                # 3. Trend weakening (ADX falling below threshold)
                # 4. DI crossover (trend reversal)
                # 5. Price breaks below HVN (support broken)
                trend_weakening = (adx < self.adx_threshold * 0.8 and
                                 adx < self.adx[-2] if len(self.adx) > 1 else False)
                di_crossover = di_minus > di_plus and di_minus > self.di_threshold

                if (current_price <= entry_price * dynamic_stop_loss or
                    current_price >= entry_price * dynamic_take_profit or
                    trend_weakening or
                    di_crossover or
                    current_price < hvn * 0.995):
                    self.position.close()

            # Exit logic for short positions
            elif self.position.is_short:
                entry_price = self.trades[-1].entry_price if self.trades else self.data.Close[-1]

                # Dynamic exit based on ADX
                if strong_trend and bearish_bias:
                    # Let profits run in strong trends
                    dynamic_take_profit = self.take_profit * 1.2
                    dynamic_stop_loss = self.stop_loss * 1.01  # Looser stop
                else:
                    dynamic_take_profit = self.take_profit
                    dynamic_stop_loss = self.stop_loss

                # Exit conditions:
                # 1. Stop loss hit
                # 2. Take profit reached
                # 3. Trend weakening (ADX falling)
                # 4. DI crossover (trend reversal)
                # 5. Price breaks above LVN (resistance broken)
                trend_weakening = (adx < self.adx_threshold * 0.8 and
                                 adx < self.adx[-2] if len(self.adx) > 1 else False)
                di_crossover = di_plus > di_minus and di_plus > self.di_threshold

                if (current_price >= entry_price / dynamic_stop_loss or
                    current_price <= entry_price / dynamic_take_profit or
                    trend_weakening or
                    di_crossover or
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
            AVPADXStrategy,
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
    print("ANGLED VOLUME PROFILE + ADX STRATEGY - MULTI-DATA TEST")
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
        csv_path = 'results/avp_adx_multi_data_results.csv'
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
        print("AVP + ADX STRATEGY - MULTI-DATA TEST COMPLETE")
        print(f"Successfully tested on {len(results)} data sources")
        print("="*80)