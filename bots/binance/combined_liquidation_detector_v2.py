"""
Combined BTC+ETH Liquidation Detector V2 by Moon Dev

IMPROVED BASELINES:
- Rolling average over first 60 seconds (not just one snapshot)
- Baselines for EVERYTHING: speed, volumes, trade counts
- Clear display showing current vs baseline for all metrics

Monitors BTC and ETH as ONE COMBINED MARKET STREAM.
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

class CombinedLiquidationDetector:
    def __init__(self, proximity_threshold=0.5, speed_multiplier_threshold=2.0):
        """
        Monitor BTC and ETH as ONE COMBINED STREAM with proper baselines

        Args:
            proximity_threshold: % distance to S/R to consider "near"
            speed_multiplier_threshold: Speed multiplier to trigger signal
        """
        self.symbols = ['BTCUSDT', 'ETHUSDT']
        self.proximity_threshold = proximity_threshold
        self.speed_multiplier_threshold = speed_multiplier_threshold

        # COMBINED trade stream
        self.combined_trades = deque(maxlen=10000)

        # Individual symbol data (for prices and S/R)
        self.symbol_data = {}
        for symbol in self.symbols:
            self.symbol_data[symbol] = {
                'current_price': 0.0,
                'support_20': 0.0,
                'resistance_20': 0.0,
                'support_60': 0.0,
                'resistance_60': 0.0,
            }

        # BASELINE TRACKING - Collect samples for first 60 seconds
        self.baseline_samples = {
            'speed': [],
            'trades_5s': [],
            'trades_10s': [],
            'trades_30s': [],
            'volume_usd_10s': [],
            'volume_usd_30s': []
        }
        self.baseline_calculated = False
        self.baseline_start_time = None

        # CALCULATED BASELINES (averages)
        self.baselines = {
            'speed': 0.0,
            'trades_5s': 0.0,
            'trades_10s': 0.0,
            'trades_30s': 0.0,
            'volume_usd_10s': 0.0,
            'volume_usd_30s': 0.0
        }

        self.last_signal = "CALM"
        self.last_signal_time = None
        self.ws = None
        self.running = False

        # Logging
        self.log_file = f"bots/binance/logs/combined_v2_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self._init_log_file()

    def _init_log_file(self):
        """Initialize CSV log file with baseline columns"""
        os.makedirs("bots/binance/logs", exist_ok=True)

        with open(self.log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp',
                'btc_price', 'eth_price',
                # Current metrics
                'current_trades_5s', 'current_trades_10s', 'current_trades_30s',
                'current_volume_usd_10s', 'current_volume_usd_30s',
                'current_speed_per_sec',
                'buy_sell_ratio',
                # Baseline metrics
                'baseline_trades_5s', 'baseline_trades_10s', 'baseline_trades_30s',
                'baseline_volume_usd_10s', 'baseline_volume_usd_30s',
                'baseline_speed_per_sec',
                # Multipliers
                'speed_multiplier',
                'trades_5s_multiplier', 'trades_10s_multiplier', 'trades_30s_multiplier',
                'volume_10s_multiplier', 'volume_30s_multiplier',
                # S/R
                'btc_support_20', 'btc_dist_support_20_pct',
                'btc_resistance_20', 'btc_dist_resistance_20_pct',
                'eth_support_20', 'eth_dist_support_20_pct',
                'eth_resistance_20', 'eth_dist_resistance_20_pct',
                # Signal
                'signal', 'signal_strength', 'signal_symbols'
            ])

    def fetch_historical_candles(self, symbol, interval='1m', limit=60):
        """Fetch historical klines from Binance"""
        url = "https://api.binance.com/api/v3/klines"
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}

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
            lows_60 = [float(c[3]) for c in candles_60]
            highs_60 = [float(c[2]) for c in candles_60]
            self.symbol_data[symbol]['support_60'] = min(lows_60)
            self.symbol_data[symbol]['resistance_60'] = max(highs_60)

            lows_20 = lows_60[-20:]
            highs_20 = highs_60[-20:]
            self.symbol_data[symbol]['support_20'] = min(lows_20)
            self.symbol_data[symbol]['resistance_20'] = max(highs_20)

            return True
        return False

    def get_combined_metrics(self):
        """
        Calculate COMBINED metrics with proper baseline tracking

        Returns current metrics + multipliers vs baseline
        """
        now = datetime.now()
        trades_snapshot = list(self.combined_trades)

        # Filter by time windows
        trades_5s = [t for t in trades_snapshot if (now - t['time']).total_seconds() <= 5]
        trades_10s = [t for t in trades_snapshot if (now - t['time']).total_seconds() <= 10]
        trades_30s = [t for t in trades_snapshot if (now - t['time']).total_seconds() <= 30]

        # Count trades
        count_5s = len(trades_5s)
        count_10s = len(trades_10s)
        count_30s = len(trades_30s)

        # Calculate USD volumes
        volume_usd_10s = sum([t['volume_usd'] for t in trades_10s])
        volume_usd_30s = sum([t['volume_usd'] for t in trades_30s])

        # Buy/Sell pressure
        buys = sum([t['volume_usd'] for t in trades_10s if t['is_buyer_maker'] == False])
        sells = sum([t['volume_usd'] for t in trades_10s if t['is_buyer_maker'] == True])
        buy_sell_ratio = buys / sells if sells > 0 else 0

        # Current speed
        current_speed = count_10s / 10.0

        # BASELINE CALCULATION - Collect samples for first 60 seconds
        if not self.baseline_calculated:
            if self.baseline_start_time is None:
                self.baseline_start_time = datetime.now()

            # Collect samples (only if we have enough data)
            if len(trades_snapshot) > 50:
                self.baseline_samples['speed'].append(current_speed)
                self.baseline_samples['trades_5s'].append(count_5s)
                self.baseline_samples['trades_10s'].append(count_10s)
                self.baseline_samples['trades_30s'].append(count_30s)
                self.baseline_samples['volume_usd_10s'].append(volume_usd_10s)
                self.baseline_samples['volume_usd_30s'].append(volume_usd_30s)

            # After 60 seconds, calculate baselines as AVERAGES
            elapsed = (datetime.now() - self.baseline_start_time).total_seconds()
            if elapsed >= 60 and len(self.baseline_samples['speed']) >= 30:
                self.baselines['speed'] = sum(self.baseline_samples['speed']) / len(self.baseline_samples['speed'])
                self.baselines['trades_5s'] = sum(self.baseline_samples['trades_5s']) / len(self.baseline_samples['trades_5s'])
                self.baselines['trades_10s'] = sum(self.baseline_samples['trades_10s']) / len(self.baseline_samples['trades_10s'])
                self.baselines['trades_30s'] = sum(self.baseline_samples['trades_30s']) / len(self.baseline_samples['trades_30s'])
                self.baselines['volume_usd_10s'] = sum(self.baseline_samples['volume_usd_10s']) / len(self.baseline_samples['volume_usd_10s'])
                self.baselines['volume_usd_30s'] = sum(self.baseline_samples['volume_usd_30s']) / len(self.baseline_samples['volume_usd_30s'])

                self.baseline_calculated = True
                console.print(f"\n[yellow]📊 BASELINES CALCULATED (60-second rolling average):[/yellow]")
                console.print(f"[yellow]  • Speed: {self.baselines['speed']:.2f} trades/sec[/yellow]")
                console.print(f"[yellow]  • Trades 5s: {self.baselines['trades_5s']:.0f}[/yellow]")
                console.print(f"[yellow]  • Trades 10s: {self.baselines['trades_10s']:.0f}[/yellow]")
                console.print(f"[yellow]  • Trades 30s: {self.baselines['trades_30s']:.0f}[/yellow]")
                console.print(f"[yellow]  • Volume 10s: ${self.baselines['volume_usd_10s']:,.0f}[/yellow]")
                console.print(f"[yellow]  • Volume 30s: ${self.baselines['volume_usd_30s']:,.0f}[/yellow]\n")

        # Calculate multipliers
        speed_multiplier = current_speed / self.baselines['speed'] if self.baselines['speed'] > 0 else 1.0
        trades_5s_mult = count_5s / self.baselines['trades_5s'] if self.baselines['trades_5s'] > 0 else 1.0
        trades_10s_mult = count_10s / self.baselines['trades_10s'] if self.baselines['trades_10s'] > 0 else 1.0
        trades_30s_mult = count_30s / self.baselines['trades_30s'] if self.baselines['trades_30s'] > 0 else 1.0
        volume_10s_mult = volume_usd_10s / self.baselines['volume_usd_10s'] if self.baselines['volume_usd_10s'] > 0 else 1.0
        volume_30s_mult = volume_usd_30s / self.baselines['volume_usd_30s'] if self.baselines['volume_usd_30s'] > 0 else 1.0

        return {
            # Current values
            'combined_trades_5s': count_5s,
            'combined_trades_10s': count_10s,
            'combined_trades_30s': count_30s,
            'combined_volume_usd_10s': volume_usd_10s,
            'combined_volume_usd_30s': volume_usd_30s,
            'combined_buy_sell_ratio': buy_sell_ratio,
            'current_speed': current_speed,
            # Baselines
            'baseline_speed': self.baselines['speed'],
            'baseline_trades_5s': self.baselines['trades_5s'],
            'baseline_trades_10s': self.baselines['trades_10s'],
            'baseline_trades_30s': self.baselines['trades_30s'],
            'baseline_volume_usd_10s': self.baselines['volume_usd_10s'],
            'baseline_volume_usd_30s': self.baselines['volume_usd_30s'],
            # Multipliers
            'speed_multiplier': speed_multiplier,
            'trades_5s_multiplier': trades_5s_mult,
            'trades_10s_multiplier': trades_10s_mult,
            'trades_30s_multiplier': trades_30s_mult,
            'volume_10s_multiplier': volume_10s_mult,
            'volume_30s_multiplier': volume_30s_mult
        }

    def check_symbol_proximity(self, symbol):
        """Check if a symbol is near support or resistance"""
        current_price = self.symbol_data[symbol]['current_price']
        if current_price == 0:
            return None

        support_20 = self.symbol_data[symbol]['support_20']
        resistance_20 = self.symbol_data[symbol]['resistance_20']

        dist_support = ((current_price - support_20) / current_price) * 100
        dist_resistance = ((resistance_20 - current_price) / current_price) * 100

        near_support = dist_support <= self.proximity_threshold
        near_resistance = dist_resistance <= self.proximity_threshold
        broke_support = dist_support < 0
        broke_resistance = dist_resistance < 0

        return {
            'dist_support_20': dist_support,
            'dist_resistance_20': dist_resistance,
            'near_support': near_support,
            'near_resistance': near_resistance,
            'broke_support': broke_support,
            'broke_resistance': broke_resistance
        }

    def generate_combined_signal(self, metrics):
        """Generate signal based on COMBINED velocity + which symbols are at key levels"""
        speed_mult = metrics['speed_multiplier']

        if not self.baseline_calculated:
            return "CALM", 0, []

        speed_elevated = speed_mult >= self.speed_multiplier_threshold

        if not speed_elevated:
            return "CALM", 0, []

        # Check which symbols are near S/R
        btc_prox = self.check_symbol_proximity('BTCUSDT')
        eth_prox = self.check_symbol_proximity('ETHUSDT')

        symbols_at_resistance = []
        symbols_at_support = []
        symbols_broke_resistance = []
        symbols_broke_support = []

        if btc_prox:
            if btc_prox['broke_resistance']:
                symbols_broke_resistance.append('BTC')
            elif btc_prox['near_resistance']:
                symbols_at_resistance.append('BTC')
            if btc_prox['broke_support']:
                symbols_broke_support.append('BTC')
            elif btc_prox['near_support']:
                symbols_at_support.append('BTC')

        if eth_prox:
            if eth_prox['broke_resistance']:
                symbols_broke_resistance.append('ETH')
            elif eth_prox['near_resistance']:
                symbols_at_resistance.append('ETH')
            if eth_prox['broke_support']:
                symbols_broke_support.append('ETH')
            elif eth_prox['near_support']:
                symbols_at_support.append('ETH')

        # Calculate signal strength
        strength = min(100, int((speed_mult - 1) * 30))

        # Bonus for multiple symbols
        if len(symbols_at_resistance) == 2 or len(symbols_broke_resistance) == 2:
            strength += 30
        if len(symbols_at_support) == 2 or len(symbols_broke_support) == 2:
            strength += 30

        strength = min(100, strength)

        # Generate signal
        if symbols_broke_resistance:
            return "RESISTANCE_BREAK", strength, symbols_broke_resistance
        elif symbols_broke_support:
            return "SUPPORT_BREAK", strength, symbols_broke_support
        elif symbols_at_resistance:
            return "RESISTANCE_TEST", strength, symbols_at_resistance
        elif symbols_at_support:
            return "SUPPORT_TEST", strength, symbols_at_support
        elif speed_mult >= self.speed_multiplier_threshold * 1.5:
            return "HIGH_VELOCITY", strength, ['BTC', 'ETH']

        return "CALM", 0, []

    def log_data(self, metrics, signal, signal_strength, signal_symbols):
        """Log all data to CSV including baselines"""
        btc_prox = self.check_symbol_proximity('BTCUSDT')
        eth_prox = self.check_symbol_proximity('ETHUSDT')

        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                self.symbol_data['BTCUSDT']['current_price'],
                self.symbol_data['ETHUSDT']['current_price'],
                # Current
                metrics['combined_trades_5s'],
                metrics['combined_trades_10s'],
                metrics['combined_trades_30s'],
                f"{metrics['combined_volume_usd_10s']:.2f}",
                f"{metrics['combined_volume_usd_30s']:.2f}",
                f"{metrics['current_speed']:.2f}",
                f"{metrics['combined_buy_sell_ratio']:.2f}",
                # Baselines
                f"{metrics['baseline_trades_5s']:.0f}",
                f"{metrics['baseline_trades_10s']:.0f}",
                f"{metrics['baseline_trades_30s']:.0f}",
                f"{metrics['baseline_volume_usd_10s']:.2f}",
                f"{metrics['baseline_volume_usd_30s']:.2f}",
                f"{metrics['baseline_speed']:.2f}",
                # Multipliers
                f"{metrics['speed_multiplier']:.2f}",
                f"{metrics['trades_5s_multiplier']:.2f}",
                f"{metrics['trades_10s_multiplier']:.2f}",
                f"{metrics['trades_30s_multiplier']:.2f}",
                f"{metrics['volume_10s_multiplier']:.2f}",
                f"{metrics['volume_30s_multiplier']:.2f}",
                # S/R
                self.symbol_data['BTCUSDT']['support_20'],
                f"{btc_prox['dist_support_20']:.3f}" if btc_prox else "0",
                self.symbol_data['BTCUSDT']['resistance_20'],
                f"{btc_prox['dist_resistance_20']:.3f}" if btc_prox else "0",
                self.symbol_data['ETHUSDT']['support_20'],
                f"{eth_prox['dist_support_20']:.3f}" if eth_prox else "0",
                self.symbol_data['ETHUSDT']['resistance_20'],
                f"{eth_prox['dist_resistance_20']:.3f}" if eth_prox else "0",
                # Signal
                signal,
                signal_strength,
                '+'.join(signal_symbols) if signal_symbols else ''
            ])

    def print_signal(self, signal, signal_strength, signal_symbols, metrics):
        """Print signal with ALL baselines visible"""
        if signal == "CALM":
            return

        # Colors
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

        # Create detailed table
        table = Table(box=box.DOUBLE, border_style=color, show_header=False, padding=(0, 1))
        table.add_column("Metric", style="cyan bold", width=25)
        table.add_column("Current", style="white bold", width=18, justify="right")
        table.add_column("Baseline", style="dim", width=18, justify="right")
        table.add_column("Multiplier", style=color, width=12, justify="center")

        # Header
        table.add_row("═" * 25, "═" * 18, "═" * 18, "═" * 12)
        table.add_row(f"[{color}]🎯 {signal}[/{color}]", "", "", f"[{color} bold]{signal_strength}/100[/{color} bold]")
        table.add_row(f"[{color}]Symbols: {' + '.join(signal_symbols)}[/{color}]", "", "", f"[{color}]{direction}[/{color}]")
        table.add_row("", "", "", "")

        # Prices
        table.add_row("💵 BTC Price", f"${self.symbol_data['BTCUSDT']['current_price']:,.2f}", "", "")
        table.add_row("💵 ETH Price", f"${self.symbol_data['ETHUSDT']['current_price']:,.2f}", "", "")
        table.add_row("", "", "", "")

        # Speed (most important!)
        table.add_row(
            "⚡ SPEED (trades/sec)",
            f"{metrics['current_speed']:.1f}",
            f"{metrics['baseline_speed']:.1f}",
            f"[{color} bold]{metrics['speed_multiplier']:.2f}x[/{color} bold]"
        )
        table.add_row("", "", "", "")

        # Trade counts
        table.add_row(
            "📊 Trades (5s)",
            f"{metrics['combined_trades_5s']}",
            f"{metrics['baseline_trades_5s']:.0f}",
            f"{metrics['trades_5s_multiplier']:.2f}x"
        )
        table.add_row(
            "📊 Trades (10s)",
            f"{metrics['combined_trades_10s']}",
            f"{metrics['baseline_trades_10s']:.0f}",
            f"{metrics['trades_10s_multiplier']:.2f}x"
        )
        table.add_row(
            "📊 Trades (30s)",
            f"{metrics['combined_trades_30s']}",
            f"{metrics['baseline_trades_30s']:.0f}",
            f"{metrics['trades_30s_multiplier']:.2f}x"
        )
        table.add_row("", "", "", "")

        # USD Volumes
        table.add_row(
            "💰 Volume (10s)",
            f"${metrics['combined_volume_usd_10s']:,.0f}",
            f"${metrics['baseline_volume_usd_10s']:,.0f}",
            f"{metrics['volume_10s_multiplier']:.2f}x"
        )
        table.add_row(
            "💰 Volume (30s)",
            f"${metrics['combined_volume_usd_30s']:,.0f}",
            f"${metrics['baseline_volume_usd_30s']:,.0f}",
            f"{metrics['volume_30s_multiplier']:.2f}x"
        )
        table.add_row(
            "💰 Buy/Sell Ratio",
            f"{metrics['combined_buy_sell_ratio']:.2f}",
            "",
            ""
        )

        table.add_row("═" * 25, "═" * 18, "═" * 18, "═" * 12)

        panel = Panel(
            table,
            title=f"{emoji} Moon Dev Combined Market Alert (V2) {emoji}",
            border_style=color,
            padding=(1, 1)
        )

        console.print("\n")
        console.print(panel)
        console.print(f"[dim]All baselines calculated from 60-second rolling average[/dim]\n")

    def on_message(self, ws, message):
        """Handle WebSocket messages"""
        data = json.loads(message)

        if 'e' in data and data['e'] == 'trade':
            symbol = data['s']
            price = float(data['p'])
            quantity = float(data['q'])

            self.symbol_data[symbol]['current_price'] = price

            trade = {
                'time': datetime.now(),
                'symbol': symbol,
                'price': price,
                'quantity': quantity,
                'volume_usd': quantity * price,
                'is_buyer_maker': data['m']
            }

            self.combined_trades.append(trade)

    def on_error(self, ws, error):
        console.print(f"[red]WebSocket Error: {error}[/red]")

    def on_close(self, ws, close_status_code, close_msg):
        console.print("[yellow]WebSocket Connection Closed[/yellow]")
        self.running = False

    def on_open(self, ws):
        console.print(f"[green]Moon Dev's Combined Detector V2 Connected! 🚀[/green]")
        console.print(f"[green]Collecting baseline data for 60 seconds...[/green]\n")

        streams = [f"{symbol.lower()}@trade" for symbol in self.symbols]
        subscribe_message = {"method": "SUBSCRIBE", "params": streams, "id": 1}
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
            for symbol in self.symbols:
                self.calculate_support_resistance(symbol)
            time.sleep(60)

    def monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            if len(self.combined_trades) < 20:
                time.sleep(1)
                continue

            metrics = self.get_combined_metrics()
            signal, signal_strength, signal_symbols = self.generate_combined_signal(metrics)

            self.log_data(metrics, signal, signal_strength, signal_symbols)

            if signal != "CALM" and signal != self.last_signal:
                self.print_signal(signal, signal_strength, signal_symbols, metrics)
                self.last_signal = signal
                self.last_signal_time = datetime.now()

            if self.last_signal != "CALM" and self.last_signal_time:
                if (datetime.now() - self.last_signal_time).total_seconds() > 10:
                    self.last_signal = "CALM"

            time.sleep(1)

    def run(self):
        """Start the detector"""
        self.running = True

        console.print("[yellow]Calculating initial S/R levels...[/yellow]")
        for symbol in self.symbols:
            if self.calculate_support_resistance(symbol):
                display_symbol = symbol.replace('USDT', '')
                console.print(f"[green]✓ {display_symbol} Support: ${self.symbol_data[symbol]['support_20']:,.2f}[/green]")
                console.print(f"[green]✓ {display_symbol} Resistance: ${self.symbol_data[symbol]['resistance_20']:,.2f}[/green]")
        console.print()

        self.start_websocket()
        time.sleep(2)

        sr_thread = threading.Thread(target=self.update_support_resistance_loop)
        sr_thread.daemon = True
        sr_thread.start()

        try:
            self.monitoring_loop()
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down... 👋[/yellow]")
            self.running = False
            if self.ws:
                self.ws.close()

    def get_latest_signal(self):
        """Get latest signal for bot consumption"""
        if len(self.combined_trades) < 20:
            return None

        metrics = self.get_combined_metrics()
        signal, signal_strength, signal_symbols = self.generate_combined_signal(metrics)

        return {
            'signal': signal,
            'strength': signal_strength,
            'symbols': signal_symbols,
            'btc_price': self.symbol_data['BTCUSDT']['current_price'],
            'eth_price': self.symbol_data['ETHUSDT']['current_price'],
            'speed_multiplier': metrics['speed_multiplier'],
            'metrics': metrics,
            'timestamp': datetime.now()
        }


def main():
    console.print("\n[bold cyan]" + "="*70 + "[/bold cyan]")
    console.print("[bold cyan]🌙 Moon Dev's Combined BTC+ETH Detector V2 - PROPER BASELINES 🚀[/bold cyan]")
    console.print("[bold cyan]" + "="*70 + "[/bold cyan]\n")

    console.print("[yellow]NEW: Rolling 60-second baseline calculation[/yellow]")
    console.print("[yellow]Shows current vs baseline for ALL metrics![/yellow]\n")

    detector = CombinedLiquidationDetector(
        proximity_threshold=0.5,
        speed_multiplier_threshold=2.0
    )

    console.print(f"[cyan]Log File: {detector.log_file}[/cyan]\n")
    detector.run()


if __name__ == "__main__":
    main()
