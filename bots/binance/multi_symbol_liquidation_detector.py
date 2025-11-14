"""
Multi-Symbol Liquidation Cascade Detector by Moon Dev

Monitors BTC and ETH simultaneously for liquidation events.
These are the two main market movers that matter!
"""

import json
import websocket
import threading
import time
import requests
from datetime import datetime, timedelta
from collections import deque
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich import box
import csv
import os

console = Console()

class MultiSymbolLiquidationDetector:
    def __init__(self, symbols=['BTCUSDT', 'ETHUSDT'], proximity_threshold=0.5, speed_multiplier_threshold=2.0):
        """
        Monitor multiple symbols for liquidation cascades

        Args:
            symbols: List of trading pairs to monitor
            proximity_threshold: % distance to S/R to consider "near"
            speed_multiplier_threshold: Speed multiplier to trigger signal
        """
        self.symbols = symbols
        self.proximity_threshold = proximity_threshold
        self.speed_multiplier_threshold = speed_multiplier_threshold

        # Track data per symbol
        self.data = {}
        for symbol in symbols:
            self.data[symbol] = {
                'trades': deque(maxlen=1000),
                'current_price': 0.0,
                'last_signal': "CALM",
                'last_signal_time': None,
                'support_20': 0.0,
                'resistance_20': 0.0,
                'support_60': 0.0,
                'resistance_60': 0.0,
                'baseline_speed': 0.0,
                'baseline_calculated': False,
                'log_file': f"bots/binance/logs/liquidation_log_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }

        self.ws = None
        self.running = False

        # Initialize log files
        self._init_log_files()

    def _init_log_files(self):
        """Initialize CSV log files for each symbol"""
        os.makedirs("bots/binance/logs", exist_ok=True)

        for symbol in self.symbols:
            with open(self.data[symbol]['log_file'], 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'symbol', 'price',
                    'trades_5s', 'trades_10s', 'trades_30s',
                    'volume_usd_10s', 'volume_usd_30s',
                    'buy_sell_ratio',
                    'support_20', 'dist_support_20_pct',
                    'resistance_20', 'dist_resistance_20_pct',
                    'support_60', 'dist_support_60_pct',
                    'resistance_60', 'dist_resistance_60_pct',
                    'current_speed_per_sec', 'baseline_speed_per_sec', 'speed_multiplier',
                    'signal', 'signal_strength'
                ])

    def fetch_historical_candles(self, symbol, interval='1m', limit=60):
        """Fetch historical klines from Binance"""
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()
            return data
        except Exception as e:
            console.print(f"[red]Error fetching candles for {symbol}: {e}[/red]")
            return []

    def calculate_support_resistance(self, symbol):
        """Calculate support and resistance levels for a symbol"""
        candles_60 = self.fetch_historical_candles(symbol, limit=60)

        if len(candles_60) >= 60:
            # 60-candle S/R
            lows_60 = [float(c[3]) for c in candles_60]
            highs_60 = [float(c[2]) for c in candles_60]
            self.data[symbol]['support_60'] = min(lows_60)
            self.data[symbol]['resistance_60'] = max(highs_60)

            # 20-candle S/R
            lows_20 = lows_60[-20:]
            highs_20 = highs_60[-20:]
            self.data[symbol]['support_20'] = min(lows_20)
            self.data[symbol]['resistance_20'] = max(highs_20)

            return True
        return False

    def get_trade_metrics(self, symbol):
        """
        Calculate trade velocity metrics for a symbol

        Returns dict with:
        - trades_5s: Number of trades in last 5 seconds
        - trades_10s: Number of trades in last 10 seconds
        - trades_30s: Number of trades in last 30 seconds
        - volume_usd_10s: USD volume in last 10 seconds
        - volume_usd_30s: USD volume in last 30 seconds
        - buy_sell_ratio: Buy volume / Sell volume
        - current_speed: Current trades per second (based on 10s window)
        - baseline_speed: Average trades per second (calculated at startup)
        - speed_multiplier: current_speed / baseline_speed
        """
        now = datetime.now()
        trades = self.data[symbol]['trades']

        # Filter trades by time windows
        trades_5s = [t for t in trades if (now - t['time']).total_seconds() <= 5]
        trades_10s = [t for t in trades if (now - t['time']).total_seconds() <= 10]
        trades_30s = [t for t in trades if (now - t['time']).total_seconds() <= 30]

        # Count trades
        count_5s = len(trades_5s)
        count_10s = len(trades_10s)
        count_30s = len(trades_30s)

        # Calculate USD volumes (removed coin volume as BTC vs ETH aren't comparable)
        volume_usd_10s = sum([t['quantity'] * t['price'] for t in trades_10s])
        volume_usd_30s = sum([t['quantity'] * t['price'] for t in trades_30s])

        # Buy/Sell pressure (using USD volume)
        buys = sum([t['quantity'] * t['price'] for t in trades_10s if t['is_buyer_maker'] == False])
        sells = sum([t['quantity'] * t['price'] for t in trades_10s if t['is_buyer_maker'] == True])
        buy_sell_ratio = buys / sells if sells > 0 else 0

        # Speed calculation (trades per second)
        current_speed = count_10s / 10.0

        # Set baseline after 30 seconds of data
        if not self.data[symbol]['baseline_calculated'] and len(trades) > 100:
            self.data[symbol]['baseline_speed'] = current_speed
            self.data[symbol]['baseline_calculated'] = True
            display_symbol = symbol.replace('USDT', '')
            console.print(f"[yellow]📊 {display_symbol} Baseline Set: {current_speed:.2f} trades/sec[/yellow]")

        baseline = self.data[symbol]['baseline_speed']
        speed_multiplier = current_speed / baseline if baseline > 0 else 1.0

        return {
            'trades_5s': count_5s,
            'trades_10s': count_10s,
            'trades_30s': count_30s,
            'volume_usd_10s': volume_usd_10s,
            'volume_usd_30s': volume_usd_30s,
            'buy_sell_ratio': buy_sell_ratio,
            'current_speed': current_speed,
            'baseline_speed': baseline,
            'speed_multiplier': speed_multiplier
        }

    def calculate_distances(self, symbol):
        """Calculate percentage distances from support/resistance"""
        current_price = self.data[symbol]['current_price']
        if current_price == 0:
            return {}

        support_20 = self.data[symbol]['support_20']
        resistance_20 = self.data[symbol]['resistance_20']
        support_60 = self.data[symbol]['support_60']
        resistance_60 = self.data[symbol]['resistance_60']

        dist_support_20 = ((current_price - support_20) / current_price) * 100
        dist_resistance_20 = ((resistance_20 - current_price) / current_price) * 100
        dist_support_60 = ((current_price - support_60) / current_price) * 100
        dist_resistance_60 = ((resistance_60 - current_price) / current_price) * 100

        return {
            'dist_support_20': dist_support_20,
            'dist_resistance_20': dist_resistance_20,
            'dist_support_60': dist_support_60,
            'dist_resistance_60': dist_resistance_60
        }

    def generate_signal(self, symbol, metrics, distances):
        """Generate trading signal based on speed and position"""
        speed_mult = metrics['speed_multiplier']

        # Not enough data yet
        if not self.data[symbol]['baseline_calculated']:
            return "CALM", 0

        # Check if speed is elevated
        speed_elevated = speed_mult >= self.speed_multiplier_threshold

        if not speed_elevated:
            return "CALM", 0

        # Check proximity to levels
        near_support_20 = distances['dist_support_20'] <= self.proximity_threshold
        near_resistance_20 = distances['dist_resistance_20'] <= self.proximity_threshold
        near_support_60 = distances['dist_support_60'] <= self.proximity_threshold
        near_resistance_60 = distances['dist_resistance_60'] <= self.proximity_threshold

        # Calculate signal strength (0-100)
        strength = min(100, int((speed_mult - 1) * 30))

        # Add strength for multiple timeframe confirmation
        if near_support_20 and near_support_60:
            strength += 20
        if near_resistance_20 and near_resistance_60:
            strength += 20

        # Determine signal type
        if near_resistance_20 and speed_elevated:
            if distances['dist_resistance_20'] < 0:
                return "RESISTANCE_BREAK", min(100, strength + 10)
            else:
                return "RESISTANCE_TEST", strength

        if near_support_20 and speed_elevated:
            if distances['dist_support_20'] < 0:
                return "SUPPORT_BREAK", min(100, strength + 10)
            else:
                return "SUPPORT_TEST", strength

        # Speed elevated but not near S/R
        if speed_mult >= self.speed_multiplier_threshold * 1.5:
            return "HIGH_VELOCITY", strength

        return "CALM", 0

    def log_data(self, symbol, metrics, distances, signal, signal_strength):
        """Log all data to CSV"""
        with open(self.data[symbol]['log_file'], 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                symbol,
                self.data[symbol]['current_price'],
                metrics['trades_5s'],
                metrics['trades_10s'],
                metrics['trades_30s'],
                f"{metrics['volume_usd_10s']:.2f}",
                f"{metrics['volume_usd_30s']:.2f}",
                f"{metrics['buy_sell_ratio']:.2f}",
                self.data[symbol]['support_20'],
                f"{distances['dist_support_20']:.3f}",
                self.data[symbol]['resistance_20'],
                f"{distances['dist_resistance_20']:.3f}",
                self.data[symbol]['support_60'],
                f"{distances['dist_support_60']:.3f}",
                self.data[symbol]['resistance_60'],
                f"{distances['dist_resistance_60']:.3f}",
                f"{metrics['current_speed']:.2f}",
                f"{metrics['baseline_speed']:.2f}",
                f"{metrics['speed_multiplier']:.2f}",
                signal,
                signal_strength
            ])

    def print_signal(self, symbol, signal, signal_strength, metrics, distances):
        """
        Print signal to console with clear speed comparisons and all metrics

        This shows Moon Dev exactly what data is available for trading decisions
        """
        if signal == "CALM":
            return

        # Determine color and emoji
        if "RESISTANCE" in signal:
            color = "bright_green"
            emoji = "🚀"
            direction = "LONG"
        elif "SUPPORT" in signal:
            color = "bright_red"
            emoji = "💥"
            direction = "SHORT"
        else:
            color = "yellow"
            emoji = "⚡"
            direction = "WATCH"

        # Get simple symbol name (BTC or ETH)
        display_symbol = symbol.replace('USDT', '')

        # Create signal panel
        table = Table(box=box.ROUNDED, border_style=color, show_header=False, padding=(0, 1))
        table.add_column("Key", style="cyan bold", width=20)
        table.add_column("Value", style="white", width=30)

        # Main signal info
        table.add_row("═" * 20, "═" * 30)
        table.add_row("🎯 SIGNAL", f"[{color} bold]{signal}[/{color} bold]")
        table.add_row("Symbol", f"[{color} bold]{display_symbol}[/{color} bold]")
        table.add_row("Direction", f"[{color} bold]{direction}[/{color} bold]")
        table.add_row("Strength", f"[{color} bold]{signal_strength}/100[/{color} bold]")
        table.add_row("Price", f"${self.data[symbol]['current_price']:,.2f}")

        # Speed metrics - SUPER CLEAR
        table.add_row("", "")
        table.add_row("⚡ SPEED ANALYSIS", "")
        table.add_row("Current Speed", f"{metrics['current_speed']:.2f} trades/sec")
        table.add_row("Baseline Speed", f"{metrics['baseline_speed']:.2f} trades/sec")
        table.add_row("Speed Multiplier", f"[{color} bold]{metrics['speed_multiplier']:.2f}x[/{color} bold] ({(metrics['speed_multiplier']-1)*100:+.0f}%)")

        # Trade counts
        table.add_row("", "")
        table.add_row("📊 TRADE COUNTS", "")
        table.add_row("Trades (5s)", f"{metrics['trades_5s']} trades")
        table.add_row("Trades (10s)", f"{metrics['trades_10s']} trades")
        table.add_row("Trades (30s)", f"{metrics['trades_30s']} trades")

        # Volume metrics
        table.add_row("", "")
        table.add_row("💰 USD VOLUME", "")
        table.add_row("Volume (10s)", f"${metrics['volume_usd_10s']:,.0f}")
        table.add_row("Volume (30s)", f"${metrics['volume_usd_30s']:,.0f}")
        table.add_row("Buy/Sell Ratio", f"{metrics['buy_sell_ratio']:.2f}")

        # Support/Resistance
        table.add_row("", "")
        table.add_row("📍 LEVELS (20-candle)", "")
        if "SUPPORT" in signal:
            table.add_row("Support", f"${self.data[symbol]['support_20']:,.2f}")
            table.add_row("Distance", f"{distances['dist_support_20']:.3f}% away")
        else:
            table.add_row("Resistance", f"${self.data[symbol]['resistance_20']:,.2f}")
            table.add_row("Distance", f"{distances['dist_resistance_20']:.3f}% away")

        table.add_row("═" * 20, "═" * 30)

        panel = Panel(
            table,
            title=f"{emoji} Moon Dev Liquidation Alert {emoji}",
            border_style=color,
            padding=(1, 1)
        )

        console.print("\n")
        console.print(panel)

        # Print what you'll get when calling from another file
        console.print(f"[dim]📤 Data returned by get_latest_signals()['{symbol}']:[/dim]")
        console.print(f"[dim]  signal='{signal}', strength={signal_strength}, price={self.data[symbol]['current_price']:.2f}[/dim]")
        console.print(f"[dim]  current_speed={metrics['current_speed']:.2f}, baseline={metrics['baseline_speed']:.2f}, multiplier={metrics['speed_multiplier']:.2f}[/dim]")
        console.print(f"[dim]  trades: 5s={metrics['trades_5s']}, 10s={metrics['trades_10s']}, 30s={metrics['trades_30s']}[/dim]")
        console.print(f"[dim]  volume_10s=${metrics['volume_usd_10s']:,.0f}, volume_30s=${metrics['volume_usd_30s']:,.0f}[/dim]\n")

    def create_status_display(self):
        """Create a live status display for both symbols"""
        table = Table(
            title="🌙 Moon Dev's Multi-Symbol Liquidation Monitor 🚀",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            title_style="bold cyan",
            border_style="bright_blue",
            padding=(0, 1)
        )

        table.add_column("Symbol", style="cyan bold", justify="center", width=6)
        table.add_column("Price", style="white", justify="right", width=11)
        table.add_column("Speed", justify="center", width=8)
        table.add_column("Signal", justify="center", width=18)
        table.add_column("Strength", justify="center", width=8)

        for symbol in self.symbols:
            if len(self.data[symbol]['trades']) < 10:
                continue

            display_symbol = symbol.replace('USDT', '')
            price = self.data[symbol]['current_price']
            metrics = self.get_trade_metrics(symbol)
            distances = self.calculate_distances(symbol)
            signal, strength = self.generate_signal(symbol, metrics, distances)

            # Format price
            if price >= 1000:
                price_str = f"${price:,.2f}"
            else:
                price_str = f"${price:.2f}"

            # Format speed
            speed_mult = metrics['speed_multiplier']
            if speed_mult >= self.speed_multiplier_threshold:
                speed_str = f"[bold yellow]{speed_mult:.2f}x[/bold yellow]"
            else:
                speed_str = f"{speed_mult:.2f}x"

            # Format signal
            if signal == "CALM":
                signal_str = "[dim]CALM[/dim]"
                strength_str = "[dim]-[/dim]"
            elif "RESISTANCE" in signal:
                signal_str = f"[bold green]{signal}[/bold green]"
                strength_str = f"[bold green]{strength}/100[/bold green]"
            elif "SUPPORT" in signal:
                signal_str = f"[bold red]{signal}[/bold red]"
                strength_str = f"[bold red]{strength}/100[/bold red]"
            else:
                signal_str = f"[yellow]{signal}[/yellow]"
                strength_str = f"[yellow]{strength}/100[/yellow]"

            table.add_row(
                display_symbol,
                price_str,
                speed_str,
                signal_str,
                strength_str
            )

        timestamp = datetime.now().strftime("%H:%M:%S")
        panel = Panel(
            table,
            subtitle=f"⏰ {timestamp}",
            subtitle_align="right",
            border_style="bright_blue",
            padding=(0, 1)
        )

        return panel

    def on_message(self, ws, message):
        """Handle WebSocket trade messages"""
        data = json.loads(message)

        if 'e' in data and data['e'] == 'trade':
            symbol = data['s']
            if symbol in self.data:
                trade = {
                    'time': datetime.now(),
                    'price': float(data['p']),
                    'quantity': float(data['q']),
                    'is_buyer_maker': data['m']
                }

                self.data[symbol]['trades'].append(trade)
                self.data[symbol]['current_price'] = trade['price']

    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        console.print(f"[red]WebSocket Error: {error}[/red]")

    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        console.print("[yellow]WebSocket Connection Closed[/yellow]")
        self.running = False

    def on_open(self, ws):
        """Subscribe to trade streams when connection opens"""
        console.print(f"[green]Moon Dev's Liquidation Detector Connected! 🚀[/green]")
        console.print(f"[green]Monitoring BTC & ETH for liquidation cascades...[/green]\n")

        # Subscribe to all symbol trade streams
        streams = [f"{symbol.lower()}@trade" for symbol in self.symbols]
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": 1
        }
        ws.send(json.dumps(subscribe_message))

    def start_websocket(self):
        """Start WebSocket connection"""
        websocket.enableTrace(False)
        ws_url = "wss://stream.binance.com:9443/ws"

        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )

        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

    def update_support_resistance_loop(self):
        """Periodically update S/R levels for all symbols"""
        while self.running:
            for symbol in self.symbols:
                self.calculate_support_resistance(symbol)
            time.sleep(60)

    def monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            ready = all(len(self.data[s]['trades']) >= 10 for s in self.symbols)
            if not ready:
                time.sleep(1)
                continue

            for symbol in self.symbols:
                metrics = self.get_trade_metrics(symbol)
                distances = self.calculate_distances(symbol)
                signal, signal_strength = self.generate_signal(symbol, metrics, distances)

                # Log data
                self.log_data(symbol, metrics, distances, signal, signal_strength)

                # Print significant signals
                if signal != "CALM" and signal != self.data[symbol]['last_signal']:
                    self.print_signal(symbol, signal, signal_strength, metrics, distances)
                    self.data[symbol]['last_signal'] = signal
                    self.data[symbol]['last_signal_time'] = datetime.now()

                # Reset signal after 10 seconds
                if self.data[symbol]['last_signal'] != "CALM" and self.data[symbol]['last_signal_time']:
                    if (datetime.now() - self.data[symbol]['last_signal_time']).total_seconds() > 10:
                        self.data[symbol]['last_signal'] = "CALM"

            time.sleep(1)

    def run(self):
        """Start the detector"""
        self.running = True

        # Initial S/R calculation
        console.print("[yellow]Calculating initial support/resistance levels...[/yellow]")
        for symbol in self.symbols:
            if self.calculate_support_resistance(symbol):
                display_symbol = symbol.replace('USDT', '')
                console.print(f"[green]✓ {display_symbol} Support (20): ${self.data[symbol]['support_20']:,.2f}[/green]")
                console.print(f"[green]✓ {display_symbol} Resistance (20): ${self.data[symbol]['resistance_20']:,.2f}[/green]")
        console.print()

        # Start WebSocket
        self.start_websocket()
        time.sleep(2)

        # Start S/R update thread
        sr_thread = threading.Thread(target=self.update_support_resistance_loop)
        sr_thread.daemon = True
        sr_thread.start()

        # Start monitoring
        try:
            self.monitoring_loop()
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down Moon Dev's Liquidation Detector... 👋[/yellow]")
            self.running = False
            if self.ws:
                self.ws.close()

    def get_latest_signals(self):
        """
        Get the latest signals for all symbols - USE THIS IN YOUR TRADING BOT

        Returns: dict with symbol keys containing all data for trading decisions

        Example return value:
        {
            'BTCUSDT': {
                'signal': 'RESISTANCE_BREAK',  # Signal type
                'strength': 85,                 # Confidence 0-100
                'price': 97234.52,              # Current price
                'speed_multiplier': 3.2,        # Speed vs baseline
                'metrics': {                    # All speed/volume data
                    'trades_5s': 42,
                    'trades_10s': 78,
                    'trades_30s': 235,
                    'volume_usd_10s': 1215432.10,
                    'volume_usd_30s': 3542189.50,
                    'buy_sell_ratio': 1.8,
                    'current_speed': 7.8,       # Current trades/sec
                    'baseline_speed': 2.4,      # Average trades/sec
                    'speed_multiplier': 3.25    # How many times faster
                },
                'distances': {                  # Distance to S/R levels
                    'dist_support_20': 1.2,     # % above support
                    'dist_resistance_20': -0.1, # % below resistance (negative = broke through)
                    'dist_support_60': 2.5,
                    'dist_resistance_60': 0.3
                },
                'timestamp': datetime(...)
            },
            'ETHUSDT': {
                ... same structure ...
            }
        }

        Signal types:
        - 'CALM': Normal conditions
        - 'RESISTANCE_BREAK': Broke resistance + speed spike → LONG
        - 'SUPPORT_BREAK': Broke support + speed spike → SHORT
        - 'RESISTANCE_TEST': Near resistance + speed spike → Watch for breakout
        - 'SUPPORT_TEST': Near support + speed spike → Watch for breakdown
        """
        signals = {}
        for symbol in self.symbols:
            if len(self.data[symbol]['trades']) < 10:
                continue

            metrics = self.get_trade_metrics(symbol)
            distances = self.calculate_distances(symbol)
            signal, signal_strength = self.generate_signal(symbol, metrics, distances)

            signals[symbol] = {
                'signal': signal,
                'strength': signal_strength,
                'price': self.data[symbol]['current_price'],
                'speed_multiplier': metrics['speed_multiplier'],
                'metrics': metrics,
                'distances': distances,
                'timestamp': datetime.now()
            }

        return signals


def main():
    """Main entry point"""
    console.print("\n[bold cyan]" + "="*60 + "[/bold cyan]")
    console.print("[bold cyan]🌙 Moon Dev's BTC & ETH Liquidation Detector 🚀[/bold cyan]")
    console.print("[bold cyan]" + "="*60 + "[/bold cyan]\n")

    console.print("[yellow]Thesis: Speed + Proximity to S/R = Liquidation Cascades[/yellow]")
    console.print("[yellow]Monitoring BTC & ETH - the two that move markets![/yellow]\n")

    # Monitor BTC and ETH only
    detector = MultiSymbolLiquidationDetector(
        symbols=['BTCUSDT', 'ETHUSDT'],
        proximity_threshold=0.5,
        speed_multiplier_threshold=2.0
    )

    console.print(f"[cyan]Configuration:[/cyan]")
    console.print(f"  • Symbols: BTC, ETH")
    console.print(f"  • Proximity Threshold: {detector.proximity_threshold}%")
    console.print(f"  • Speed Multiplier: {detector.speed_multiplier_threshold}x")
    console.print(f"  • Log Files: bots/binance/logs/\n")

    detector.run()


if __name__ == "__main__":
    main()
