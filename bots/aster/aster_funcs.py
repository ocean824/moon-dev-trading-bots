"""
Helper functions for Aster Exchange trading bot
Adapted from nice_funcs.py for Aster Exchange API
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from termcolor import colored
import warnings

warnings.filterwarnings('ignore')


class AsterFuncs:
    """
    Helper functions for Aster Exchange trading
    """

    def __init__(self, api_client):
        """
        Initialize with Aster API client

        Args:
            api_client: Instance of AsterAPI
        """
        self.api = api_client

    def ask_bid(self, symbol):
        """
        Get ask and bid prices for a symbol

        Returns:
            (ask, bid, orderbook_data)
        """
        orderbook = self.api.get_orderbook(symbol, limit=20)

        if orderbook['bids'] and orderbook['asks']:
            bid = float(orderbook['bids'][0][0])
            ask = float(orderbook['asks'][0][0])
            return ask, bid, orderbook
        else:
            raise ValueError(f"No orderbook data available for {symbol}")

    def get_current_price(self, symbol):
        """Get current price for a symbol"""
        return self.api.get_current_price(symbol)

    def get_position(self, symbol):
        """
        Get current position info

        Returns:
            (positions, in_position, size, symbol, current_price, pnl_percent, is_long)
        """
        try:
            # First check if order is still pending
            open_orders = self.api.get_open_orders(symbol)
            if open_orders:
                print(f"📋 Found {len(open_orders)} open orders for {symbol}")
                for order in open_orders:
                    print(f"  Order ID: {order.get('orderId')} | Status: {order.get('status')} | Side: {order.get('side')}")

            position = self.api.get_position(symbol)

            if position:
                in_pos = True
                size = position['position_amount']
                pos_sym = position['symbol']
                entry_px = position['entry_price']
                current_price = position['mark_price']
                pnl_perc = position['pnl_percentage']
                is_long = position['is_long']

                print(f"Current account position: {symbol}")
                print(f"Size: {size}, Entry: ${entry_px:.2f}, PnL: {pnl_perc:.2f}%")

                return [position], in_pos, size, pos_sym, current_price, pnl_perc, is_long
            else:
                print(f"No active position found for {symbol}")
                return [], False, 0, None, 0, 0, None

        except Exception as e:
            print(f"Error getting position: {e}")
            import traceback
            traceback.print_exc()
            return [], False, 0, None, 0, 0, None

    def limit_order(self, coin, side, sz, limit_px, reduce_only):
        """
        Place a limit order on Aster Exchange

        Args:
            coin: Symbol to trade
            side: 'BUY' or 'SELL'
            sz: Size/quantity
            limit_px: Limit price
            reduce_only: Whether this is a reduce-only order
        """
        # Round price to appropriate decimals
        if 'BTC' in coin:
            # BTC price needs 1 decimal place
            limit_px = round(float(limit_px), 1)
        elif 'ETH' in coin:
            # ETH price needs 2 decimal places
            limit_px = round(float(limit_px), 2)
        elif 'SOL' in coin:
            # SOL price needs 2 decimal places
            limit_px = round(float(limit_px), 2)
        else:
            # Default to 2 decimal places
            limit_px = round(float(limit_px), 2)

        print(f"🌙 Moon Dev placing order:")
        print(f"Symbol: {coin}")
        print(f"Side: {side}")
        print(f"Size: {sz}")
        print(f"Price: ${limit_px}")
        print(f"Reduce Only: {reduce_only}")

        try:
            order_result = self.api.place_order(
                symbol=coin,
                side=side,
                order_type='LIMIT',
                quantity=sz,
                price=limit_px,
                reduce_only=reduce_only
            )

            if order_result:
                print(f"✅ Order placed successfully: {order_result.get('orderId', 'Unknown ID')}")
            return order_result

        except Exception as e:
            print(f"❌ Error placing order: {e}")
            raise

    def adjust_leverage_usd_size(self, symbol, usd_size, leverage):
        """
        Calculate position size based on USD amount and set leverage

        Args:
            symbol: Trading symbol
            usd_size: Position size in USD
            leverage: Leverage to use

        Returns:
            (leverage, size)
        """
        print(f'Setting leverage: {leverage}')

        try:
            # Set leverage for the symbol
            self.api.change_leverage(symbol, leverage)

            # Get current price
            price = self.get_current_price(symbol)

            # Calculate size based on USD amount
            # Size = USD amount / price * leverage
            size = (usd_size / price) * leverage
            size = float(size)

            # Get proper precision for the symbol
            if 'BTC' in symbol:
                # BTC usually needs 3 decimal places
                size = round(size, 3)
            elif 'ETH' in symbol:
                # ETH usually needs 2 decimal places
                size = round(size, 2)
            elif 'SOL' in symbol:
                # SOL usually needs 1 decimal place
                size = round(size, 1)
            else:
                # Default to 1 decimal place for other symbols
                size = round(size, 1)

            # Ensure minimum size (0.001 for BTC)
            if 'BTC' in symbol and size < 0.001:
                size = 0.001

            print(f'Position size for ${usd_size} at {leverage}x leverage: {size} {symbol}')

            return leverage, size

        except Exception as e:
            print(f"Error adjusting leverage and size: {e}")
            raise

    def cancel_all_orders(self, symbol=None):
        """Cancel all open orders for a symbol or all symbols"""
        try:
            if symbol:
                result = self.api.cancel_all_orders(symbol)
                print(f"Cancelled all orders for {symbol}")
            else:
                # Get all open orders and cancel them
                open_orders = self.api.get_open_orders()
                symbols_cancelled = set()
                for order in open_orders:
                    if order['symbol'] not in symbols_cancelled:
                        self.api.cancel_all_orders(order['symbol'])
                        symbols_cancelled.add(order['symbol'])
                print(f"Cancelled all orders for {len(symbols_cancelled)} symbols")

        except Exception as e:
            print(f"Error cancelling orders: {e}")

    def kill_switch(self, symbol):
        """
        Emergency close position for a symbol

        Args:
            symbol: Symbol to close position for
        """
        positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = self.get_position(symbol)

        while im_in_pos:
            # Cancel all orders first
            self.cancel_all_orders(symbol)

            # Get current orderbook
            ask, bid, _ = self.ask_bid(pos_sym)

            pos_size = abs(pos_size)

            if is_long:
                # Sell to close long position
                self.limit_order(pos_sym, 'SELL', pos_size, bid, True)
                print('Kill switch - SELL TO CLOSE SUBMITTED')
                time.sleep(2)
            else:
                # Buy to close short position
                self.limit_order(pos_sym, 'BUY', pos_size, ask, True)
                print('Kill switch - BUY TO CLOSE SUBMITTED')
                time.sleep(2)

            # Check if position is closed
            positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = self.get_position(symbol)

        print('Position successfully closed in kill switch')

    def kill_switch_mkt(self, symbol):
        """
        Market close positions using aggressive pricing

        Args:
            symbol: Symbol to close position for
        """
        positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = self.get_position(symbol)

        while im_in_pos:
            self.cancel_all_orders(symbol)

            # Use market order for faster execution
            pos_size = abs(pos_size)

            try:
                if is_long:
                    self.api.place_order(
                        symbol=pos_sym,
                        side='SELL',
                        order_type='MARKET',
                        quantity=pos_size,
                        reduce_only=True
                    )
                    print('🌙 Kill switch MKT - MARKET SELL TO CLOSE SUBMITTED')
                else:
                    self.api.place_order(
                        symbol=pos_sym,
                        side='BUY',
                        order_type='MARKET',
                        quantity=pos_size,
                        reduce_only=True
                    )
                    print('🌙 Kill switch MKT - MARKET BUY TO CLOSE SUBMITTED')

                time.sleep(1)

            except Exception as e:
                print(f"Error in market kill switch: {e}")

            positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = self.get_position(symbol)

        print('✨ Position successfully closed in market kill switch - Thanks Moon Dev! ✨')

    def pnl_close(self, symbol, target, max_loss):
        """
        Close position based on PnL thresholds

        Args:
            symbol: Symbol to check
            target: Target profit percentage
            max_loss: Maximum loss percentage (negative value)
        """
        print('Entering PnL close check')
        positions, im_in_pos, pos_size, pos_sym, entry_px, pnl_perc, is_long = self.get_position(symbol)

        if im_in_pos:
            if pnl_perc > target:
                print(f'PnL gain is {pnl_perc:.2f}% and target is {target}%... closing position WIN')
                self.kill_switch(pos_sym)
                return True
            elif pnl_perc <= max_loss:
                print(f'PnL loss is {pnl_perc:.2f}% and max loss is {max_loss}%... closing position LOSS')
                self.kill_switch(pos_sym)
                return True
            else:
                print(f'PnL is {pnl_perc:.2f}%, target {target}%, max loss {max_loss}%... not closing')
                return False
        else:
            print('No position to close')
            return False

    def get_ohlcv(self, symbol, interval, limit):
        """
        Get OHLCV data and calculate support/resistance

        Args:
            symbol: Trading symbol
            interval: Timeframe (1m, 5m, 15m, 1h, etc.)
            limit: Number of candles to fetch

        Returns:
            DataFrame with OHLCV data and support/resistance levels
        """
        try:
            klines = self.api.get_klines(symbol, interval, limit)

            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            # Convert to appropriate types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])

            # Calculate support and resistance
            df['support'] = df['close'].rolling(window=20).min()
            df['resistance'] = df['close'].rolling(window=20).max()

            return df

        except Exception as e:
            print(f"Error getting OHLCV data: {e}")
            return pd.DataFrame()

    def calculate_atr(self, df, window=14):
        """
        Calculate Average True Range (ATR)

        Args:
            df: DataFrame with OHLCV data
            window: Period for ATR calculation

        Returns:
            DataFrame with ATR added
        """
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['low'] = pd.to_numeric(df['low'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')

        df['high-low'] = df['high'] - df['low']
        df['high-prevclose'] = abs(df['high'] - df['close'].shift())
        df['low-prevclose'] = abs(df['low'] - df['close'].shift())

        df['true_range'] = df[['high-low', 'high-prevclose', 'low-prevclose']].max(axis=1)
        df['atr'] = df['true_range'].rolling(window=window, min_periods=1).mean()

        last_atr = df['atr'].iloc[-1] if not df.empty else 0

        return df, last_atr

    def calculate_bollinger_bands(self, df, length=20, std_dev=2):
        """
        Calculate Bollinger Bands

        Args:
            df: DataFrame with price data
            length: Period for moving average
            std_dev: Number of standard deviations

        Returns:
            DataFrame with Bollinger Bands
        """
        df['close'] = pd.to_numeric(df['close'], errors='coerce')

        df['bb_middle'] = df['close'].rolling(window=length).mean()
        df['bb_std'] = df['close'].rolling(window=length).std()

        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * std_dev)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * std_dev)

        df['band_width'] = df['bb_upper'] - df['bb_lower']

        # Determine if bands are tight or wide
        tight_threshold = df['band_width'].quantile(0.2)
        wide_threshold = df['band_width'].quantile(0.8)

        current_band_width = df['band_width'].iloc[-1] if not df.empty else 0
        tight = current_band_width <= tight_threshold
        wide = current_band_width >= wide_threshold

        return df, tight, wide

    def close_all_positions(self):
        """Close all open positions"""
        try:
            positions = self.api.get_positions()

            for position in positions:
                if float(position['positionAmt']) != 0:
                    symbol = position['symbol']
                    print(f"Closing position for {symbol}")
                    self.kill_switch(symbol)

            print("All positions have been closed")

        except Exception as e:
            print(f"Error closing all positions: {e}")

    def close_all_positions_mkt(self):
        """Close all open positions using market orders"""
        try:
            positions = self.api.get_positions()

            for position in positions:
                if float(position['positionAmt']) != 0:
                    symbol = position['symbol']
                    print(f"Market closing position for {symbol}")
                    self.kill_switch_mkt(symbol)

            print("All positions have been market closed")

        except Exception as e:
            print(f"Error market closing all positions: {e}")