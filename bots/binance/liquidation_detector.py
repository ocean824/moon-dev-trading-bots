"""
Liquidation Cascade Detector by Moon Dev

Detects potential liquidation events by monitoring:
1. Order book speed (trade velocity)
2. Distance from support/resistance levels
3. Combined signals for trading opportunities

Thesis: When price approaches S/R and trade velocity spikes = liquidations cascading
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
from rich import box
import csv
import os

console = Console()

class LiquidationDetector:
    def __init__(self, symbol='BTCUSDT', proximity_threshold=0.5, speed_multiplier_threshold=2.0):
        """
        Initialize the liquidation detector

        Args:
            symbol: Trading pair to monitor (e.g., 'BTCUSDT')
            proximity_threshold: % distance to S/R to consider "near" (default 0.5%)
            speed_multiplier_threshold: How many times faster than baseline to signal (default 2x)
        """
        self.symbol = symbol
        self.proximity_threshold = proximity_threshold
        self.speed_multiplier_threshold = speed_multiplier_threshold

        # Trade tracking
        self.trades = deque(maxlen=1000)  # Keep last 1000 trades
        self.trade_times = deque(maxlen=1000)

        # Current state
        self.current_price = 0.0
        self.last_signal = "CALM"
        self.last_signal_time = None

        # Support/Resistance levels
        self.support_20 = 0.0
        self.resistance_20 = 0.0
        self.support_60 = 0.0
        self.resistance_60 = 0.0

        # Baseline speed (trades per second)
        self.baseline_speed = 0.0
        self.baseline_calculated = False

        # WebSocket
        self.ws = None
        self.running = False

        # Logging
        self.log_file = f"bots/binance/logs/liquidation_log_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self._init_log_file()

    def _init_log_file(self):
        """Initialize CSV log file"""
        os.makedirs("bots/binance/logs", exist_ok=True)

        with open(self.log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'symbol', 'price',
                'trades_5s', 'trades_10s',
                'quantity_10s', 'volume_usd_10s',
                'buy_sell_ratio',
                'support_20', 'dist_support_20_pct',
                'resistance_20', 'dist_resistance_20_pct',
                'support_60', 'dist_support_60_pct',
                'resistance_60', 'dist_resistance_60_pct',
                'speed_multiplier', 'baseline_speed',
                'signal', 'signal_strength'
            ])

    def fetch_historical_candles(self, interval='1m', limit=60):
        """Fetch historical klines from Binance"""
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': self.symbol,
            'interval': interval,
            'limit': limit
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()
            return data
        except Exception as e:
            console.print(f"[red]Error fetching candles: {e}[/red]")
            return []

    def calculate_support_resistance(self):
        """Calculate support and resistance levels"""
        # Get 60 candles for longer timeframe
        candles_60 = self.fetch_historical_candles(limit=60)

        if len(candles_60) >= 60:
            # 60-candle S/R
            lows_60 = [float(c[3]) for c in candles_60]  # Low prices
            highs_60 = [float(c[2]) for c in candles_60]  # High prices
            self.support_60 = min(lows_60)
            self.resistance_60 = max(highs_60)

            # 20-candle S/R (most recent 20)
            lows_20 = lows_60[-20:]
            highs_20 = highs_60[-20:]
            self.support_20 = min(lows_20)
            self.resistance_20 = max(highs_20)

            return True
        return False

    def get_trade_metrics(self):
        """Calculate trade velocity metrics"""
        now = datetime.now()

        # Filter trades by time windows
        trades_5s = [t for t in self.trades if (now - t['time']).total_seconds() <= 5]
        trades_10s = [t for t in self.trades if (now - t['time']).total_seconds() <= 10]

        # Count trades
        count_5s = len(trades_5s)
        count_10s = len(trades_10s)

        # Calculate volumes
        quantity_10s = sum([t['quantity'] for t in trades_10s])
        volume_usd_10s = sum([t['quantity'] * t['price'] for t in trades_10s])

        # Buy/Sell pressure
        buys = sum([t['quantity'] for t in trades_10s if t['is_buyer_maker'] == False])
        sells = sum([t['quantity'] for t in trades_10s if t['is_buyer_maker'] == True])
        buy_sell_ratio = buys / sells if sells > 0 else 0

        # Speed multiplier
        current_speed = count_10s / 10.0  # trades per second

        # Set baseline after 30 seconds of data
        if not self.baseline_calculated and len(self.trades) > 100:
            self.baseline_speed = current_speed
            self.baseline_calculated = True
            console.print(f"[yellow]Baseline speed set: {self.baseline_speed:.2f} trades/sec[/yellow]")

        speed_multiplier = current_speed / self.baseline_speed if self.baseline_speed > 0 else 1.0

        return {
            'trades_5s': count_5s,
            'trades_10s': count_10s,
            'quantity_10s': quantity_10s,
            'volume_usd_10s': volume_usd_10s,
            'buy_sell_ratio': buy_sell_ratio,
            'current_speed': current_speed,
            'speed_multiplier': speed_multiplier
        }

    def calculate_distances(self):
        """Calculate percentage distances from support/resistance"""
        if self.current_price == 0:
            return {}

        dist_support_20 = ((self.current_price - self.support_20) / self.current_price) * 100
        dist_resistance_20 = ((self.resistance_20 - self.current_price) / self.current_price) * 100
        dist_support_60 = ((self.current_price - self.support_60) / self.current_price) * 100
        dist_resistance_60 = ((self.resistance_60 - self.current_price) / self.current_price) * 100

        return {
            'dist_support_20': dist_support_20,
            'dist_resistance_20': dist_resistance_20,
            'dist_support_60': dist_support_60,
            'dist_resistance_60': dist_resistance_60
        }

    def generate_signal(self, metrics, distances):
        """
        Generate trading signal based on speed and position

        Returns: tuple (signal_type, signal_strength)
        - signal_type: CALM, SUPPORT_TEST, RESISTANCE_TEST, SUPPORT_BREAK, RESISTANCE_BREAK
        - signal_strength: 0-100 (confidence level)
        """
        speed_mult = metrics['speed_multiplier']

        # Not enough data yet
        if not self.baseline_calculated:
            return "CALM", 0

        # Check if speed is elevated
        speed_elevated = speed_mult >= self.speed_multiplier_threshold

        if not speed_elevated:
            return "CALM", 0

        # Check proximity to levels (using 20-candle by default, 60-candle for confirmation)
        near_support_20 = distances['dist_support_20'] <= self.proximity_threshold
        near_resistance_20 = distances['dist_resistance_20'] <= self.proximity_threshold
        near_support_60 = distances['dist_support_60'] <= self.proximity_threshold
        near_resistance_60 = distances['dist_resistance_60'] <= self.proximity_threshold

        # Calculate signal strength (0-100)
        strength = min(100, int((speed_mult - 1) * 30))  # Higher speed = higher strength

        # Add strength for multiple timeframe confirmation
        if near_support_20 and near_support_60:
            strength += 20
        if near_resistance_20 and near_resistance_60:
            strength += 20

        # Determine signal type
        if near_resistance_20 and speed_elevated:
            if distances['dist_resistance_20'] < 0:  # Broke through
                return "RESISTANCE_BREAK", min(100, strength + 10)
            else:
                return "RESISTANCE_TEST", strength

        if near_support_20 and speed_elevated:
            if distances['dist_support_20'] < 0:  # Broke through
                return "SUPPORT_BREAK", min(100, strength + 10)
            else:
                return "SUPPORT_TEST", strength

        # Speed elevated but not near S/R
        if speed_mult >= self.speed_multiplier_threshold * 1.5:
            return "HIGH_VELOCITY", strength

        return "CALM", 0

    def log_data(self, metrics, distances, signal, signal_strength):
        """Log all data to CSV"""
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                self.symbol,
                self.current_price,
                metrics['trades_5s'],
                metrics['trades_10s'],
                f"{metrics['quantity_10s']:.4f}",
                f"{metrics['volume_usd_10s']:.2f}",
                f"{metrics['buy_sell_ratio']:.2f}",
                self.support_20,
                f"{distances['dist_support_20']:.3f}",
                self.resistance_20,
                f"{distances['dist_resistance_20']:.3f}",
                self.support_60,
                f"{distances['dist_support_60']:.3f}",
                self.resistance_60,
                f"{distances['dist_resistance_60']:.3f}",
                f"{metrics['speed_multiplier']:.2f}",
                f"{self.baseline_speed:.2f}",
                signal,
                signal_strength
            ])

    def print_signal(self, signal, signal_strength, metrics, distances):
        """Print signal to console with Moon Dev style"""
        if signal == "CALM":
            return  # Don't spam console with calm signals

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

        # Create signal panel
        table = Table(box=box.ROUNDED, border_style=color, show_header=False)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white bold")

        table.add_row("Signal", f"[{color}]{signal}[/{color}]")
        table.add_row("Direction", f"[{color}]{direction}[/{color}]")
        table.add_row("Strength", f"[{color}]{signal_strength}/100[/{color}]")
        table.add_row("Price", f"${self.current_price:,.2f}")
        table.add_row("Speed", f"{metrics['speed_multiplier']:.2f}x baseline")
        table.add_row("Volume (10s)", f"${metrics['volume_usd_10s']:,.0f}")

        if "SUPPORT" in signal:
            table.add_row("Support (20)", f"${self.support_20:,.2f} ({distances['dist_support_20']:.2f}%)")
        else:
            table.add_row("Resistance (20)", f"${self.resistance_20:,.2f} ({distances['dist_resistance_20']:.2f}%)")

        panel = Panel(
            table,
            title=f"{emoji} Moon Dev Liquidation Alert {emoji}",
            border_style=color,
            padding=(1, 2)
        )

        console.print("\n")
        console.print(panel)
        console.print("\n")

    def on_message(self, ws, message):
        """Handle WebSocket trade messages"""
        data = json.loads(message)

        if 'e' in data and data['e'] == 'trade':
            trade = {
                'time': datetime.now(),
                'price': float(data['p']),
                'quantity': float(data['q']),
                'is_buyer_maker': data['m']  # True = sell, False = buy
            }

            self.trades.append(trade)
            self.current_price = trade['price']

    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        console.print(f"[red]WebSocket Error: {error}[/red]")

    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        console.print("[yellow]WebSocket Connection Closed[/yellow]")
        self.running = False

    def on_open(self, ws):
        """Subscribe to trade stream when connection opens"""
        console.print(f"[green]Moon Dev's Liquidation Detector Connected! 🚀[/green]")
        console.print(f"[green]Monitoring {self.symbol} for liquidation cascades...[/green]\n")

        # Subscribe to trade stream
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [f"{self.symbol.lower()}@trade"],
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
        """Periodically update S/R levels"""
        while self.running:
            self.calculate_support_resistance()
            time.sleep(60)  # Update every minute

    def monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            if len(self.trades) < 10:
                time.sleep(1)
                continue

            # Get metrics
            metrics = self.get_trade_metrics()
            distances = self.calculate_distances()

            # Generate signal
            signal, signal_strength = self.generate_signal(metrics, distances)

            # Log data
            self.log_data(metrics, distances, signal, signal_strength)

            # Print significant signals
            if signal != "CALM" and signal != self.last_signal:
                self.print_signal(signal, signal_strength, metrics, distances)
                self.last_signal = signal
                self.last_signal_time = datetime.now()

            # Reset signal after 10 seconds
            if self.last_signal != "CALM" and self.last_signal_time:
                if (datetime.now() - self.last_signal_time).total_seconds() > 10:
                    self.last_signal = "CALM"

            time.sleep(1)  # Update every second

    def run(self):
        """Start the detector"""
        self.running = True

        # Initial S/R calculation
        console.print("[yellow]Calculating initial support/resistance levels...[/yellow]")
        if self.calculate_support_resistance():
            console.print(f"[green]✓ Support (20): ${self.support_20:,.2f}[/green]")
            console.print(f"[green]✓ Resistance (20): ${self.resistance_20:,.2f}[/green]")
            console.print(f"[green]✓ Support (60): ${self.support_60:,.2f}[/green]")
            console.print(f"[green]✓ Resistance (60): ${self.resistance_60:,.2f}[/green]\n")

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

    def get_latest_signal(self):
        """
        Get the latest signal for bot consumption

        Returns: dict with signal info
        """
        metrics = self.get_trade_metrics()
        distances = self.calculate_distances()
        signal, signal_strength = self.generate_signal(metrics, distances)

        return {
            'signal': signal,
            'strength': signal_strength,
            'price': self.current_price,
            'speed_multiplier': metrics['speed_multiplier'],
            'metrics': metrics,
            'distances': distances,
            'timestamp': datetime.now()
        }


def main():
    """Main entry point"""
    console.print("\n[bold cyan]" + "="*60 + "[/bold cyan]")
    console.print("[bold cyan]🌙 Moon Dev's Liquidation Cascade Detector 🚀[/bold cyan]")
    console.print("[bold cyan]" + "="*60 + "[/bold cyan]\n")

    console.print("[yellow]Thesis: Speed + Proximity to S/R = Liquidation Cascades[/yellow]")
    console.print("[yellow]Monitoring for high-velocity liquidation events...[/yellow]\n")

    # You can change these parameters
    detector = LiquidationDetector(
        symbol='BTCUSDT',
        proximity_threshold=0.5,  # Within 0.5% of S/R
        speed_multiplier_threshold=2.0  # 2x normal speed
    )

    console.print(f"[cyan]Configuration:[/cyan]")
    console.print(f"  • Symbol: {detector.symbol}")
    console.print(f"  • Proximity Threshold: {detector.proximity_threshold}%")
    console.print(f"  • Speed Multiplier: {detector.speed_multiplier_threshold}x")
    console.print(f"  • Log File: {detector.log_file}\n")

    detector.run()


if __name__ == "__main__":
    main()
