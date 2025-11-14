"""
Combined BTC+ETH Liquidation Detector by Moon Dev

Monitors BTC and ETH as ONE COMBINED MARKET STREAM.
All trades from both symbols analyzed together for liquidation velocity.

Thesis: When COMBINED market velocity spikes + symbols near S/R = liquidation cascade
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
    def __init__(self, proximity_threshold=0.5, speed_multiplier_threshold=2.5):
        """
        Monitor BTC and ETH as ONE COMBINED STREAM

        Args:
            proximity_threshold: % distance to S/R to consider "near"
            speed_multiplier_threshold: Speed multiplier to trigger signal
        """
        self.symbols = ['BTCUSDT', 'ETHUSDT']
        self.proximity_threshold = proximity_threshold
        self.speed_multiplier_threshold = speed_multiplier_threshold

        # COMBINED trade stream (both BTC and ETH together)
        # Increased to 10000 to handle extreme velocity events (300+ trades/sec)
        self.combined_trades = deque(maxlen=10000)  # All trades from both symbols

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

        # PERSISTENT BASELINE SYSTEM - Moon Dev's approach!
        # Every 10 minutes, take ONE 60-second sample and store forever
        # Baseline = average of all historical samples
        self.baseline_file = "bots/binance/baseline_samples.json"
        self.baseline_samples_history = []  # List of historical samples
        self.load_baseline_history()  # Load from disk

        # Current sampling state
        self.baseline_calculated = False  # For initial bootstrap
        self.baseline_start_time = None
        self.sample_collection_start = None  # When current 60s sample started
        self.current_sample_data = []  # Collecting data for current 60s sample
        self.last_sample_time = None  # When we last took a 10-min sample
        self.sample_interval = 600  # Take sample every 10 minutes

        # CALCULATED BASELINES (average of all historical samples)
        self.baselines = {
            'speed': 0.0,
            'trades_5s': 0.0,
            'trades_10s': 0.0,
            'trades_30s': 0.0,
            'volume_usd_10s': 0.0,
            'volume_usd_30s': 0.0
        }
        self.calculate_baselines_from_history()  # Calculate from loaded history

        self.last_signal = "CALM"
        self.last_signal_time = None
        self.signal_lock_duration = 30  # Lock signal for 30 seconds once it fires
        self.locked_signal = None  # Current locked signal for display
        self.locked_signal_strength = 0
        self.locked_signal_symbols = []

        self.ws = None
        self.running = False

        # Logging
        self.log_file = f"bots/binance/logs/combined_liquidation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
                'btc_support_60', 'btc_dist_support_60_pct',
                'btc_resistance_60', 'btc_dist_resistance_60_pct',
                'eth_support_60', 'eth_dist_support_60_pct',
                'eth_resistance_60', 'eth_dist_resistance_60_pct',
                # Signal
                'signal', 'signal_strength', 'signal_symbols'
            ])

    def load_baseline_history(self):
        """Load historical baseline samples from disk"""
        if os.path.exists(self.baseline_file):
            try:
                with open(self.baseline_file, 'r') as f:
                    data = json.load(f)
                    self.baseline_samples_history = data.get('samples', [])
                    console.print(f"[green]✓ Loaded {len(self.baseline_samples_history)} historical baseline samples[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠ Could not load baseline history: {e}[/yellow]")
                self.baseline_samples_history = []
        else:
            console.print("[yellow]⚠ No baseline history found - starting fresh[/yellow]")
            self.baseline_samples_history = []

    def save_baseline_history(self):
        """Save historical baseline samples to disk"""
        try:
            os.makedirs("bots/binance", exist_ok=True)
            with open(self.baseline_file, 'w') as f:
                json.dump({'samples': self.baseline_samples_history}, f, indent=2)
            console.print(f"[green]✓ Saved {len(self.baseline_samples_history)} baseline samples to disk[/green]")
        except Exception as e:
            console.print(f"[red]✗ Error saving baseline history: {e}[/red]")

    def calculate_baselines_from_history(self):
        """Calculate baseline as average of all historical samples"""
        if not self.baseline_samples_history:
            # No history yet - use defaults
            return

        # Calculate average of all samples
        total_samples = len(self.baseline_samples_history)
        sums = {
            'speed': 0.0,
            'trades_5s': 0.0,
            'trades_10s': 0.0,
            'trades_30s': 0.0,
            'volume_usd_10s': 0.0,
            'volume_usd_30s': 0.0
        }

        for sample in self.baseline_samples_history:
            for key in sums:
                sums[key] += sample.get(key, 0)

        # Calculate averages
        for key in sums:
            self.baselines[key] = sums[key] / total_samples

        self.baseline_calculated = True
        self.last_sample_time = datetime.now()  # Start 10-min timer
        console.print(f"[cyan]📊 Baseline calculated from {total_samples} historical samples:[/cyan]")
        console.print(f"[cyan]  • Speed: {self.baselines['speed']:.2f} trades/sec[/cyan]")

    def take_baseline_sample(self):
        """Take a 60-second sample and add to history"""
        if not self.current_sample_data or len(self.current_sample_data) < 30:
            console.print("[yellow]⚠ Not enough data for 60s sample (need 30+ data points)[/yellow]")
            return

        # Calculate average of this 60-second sample
        sample = {
            'timestamp': datetime.now().isoformat(),
            'speed': sum(d['speed'] for d in self.current_sample_data) / len(self.current_sample_data),
            'trades_5s': sum(d['trades_5s'] for d in self.current_sample_data) / len(self.current_sample_data),
            'trades_10s': sum(d['trades_10s'] for d in self.current_sample_data) / len(self.current_sample_data),
            'trades_30s': sum(d['trades_30s'] for d in self.current_sample_data) / len(self.current_sample_data),
            'volume_usd_10s': sum(d['volume_usd_10s'] for d in self.current_sample_data) / len(self.current_sample_data),
            'volume_usd_30s': sum(d['volume_usd_30s'] for d in self.current_sample_data) / len(self.current_sample_data),
        }

        # Add to history
        self.baseline_samples_history.append(sample)

        # Save to disk
        self.save_baseline_history()

        # Recalculate baseline from all samples
        self.calculate_baselines_from_history()

        console.print(f"[green]✅ New baseline sample added! Total samples: {len(self.baseline_samples_history)}[/green]")

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
            self.symbol_data[symbol]['support_60'] = min(lows_60)
            self.symbol_data[symbol]['resistance_60'] = max(highs_60)

            # 20-candle S/R
            lows_20 = lows_60[-20:]
            highs_20 = highs_60[-20:]
            self.symbol_data[symbol]['support_20'] = min(lows_20)
            self.symbol_data[symbol]['resistance_20'] = max(highs_20)

            return True
        return False

    def get_combined_metrics(self):
        """
        Calculate COMBINED metrics with proper 60-second rolling baseline

        Returns current metrics + baselines + multipliers for ALL metrics
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

        # NEW PERSISTENT BASELINE SYSTEM - Moon Dev's approach!
        # Phase 1: Initial 60-second bootstrap (only if no history)
        if not self.baseline_calculated:
            if self.baseline_start_time is None:
                self.baseline_start_time = datetime.now()
                self.sample_collection_start = datetime.now()

            # Collect data for bootstrap sample
            if len(trades_snapshot) > 50:
                self.current_sample_data.append({
                    'speed': current_speed,
                    'trades_5s': count_5s,
                    'trades_10s': count_10s,
                    'trades_30s': count_30s,
                    'volume_usd_10s': volume_usd_10s,
                    'volume_usd_30s': volume_usd_30s
                })

            # After 60 seconds, save as first baseline sample
            elapsed = (datetime.now() - self.baseline_start_time).total_seconds()
            if elapsed >= 60 and len(self.current_sample_data) >= 30:
                console.print(f"\n[yellow]📊 Bootstrap complete - taking first baseline sample...[/yellow]")
                self.take_baseline_sample()

                # Start 10-minute sampling cycle
                self.last_sample_time = datetime.now()
                self.sample_collection_start = datetime.now()
                self.current_sample_data = []

                console.print(f"[green]✅ Now sampling every 10 minutes (60s samples) for persistent baseline[/green]\n")

        # Phase 2: 10-minute sampling cycle (after bootstrap or if history exists)
        else:
            # Always collecting data for current 60s sample
            if len(trades_snapshot) > 50:
                # Start new 60s sample if needed
                if self.sample_collection_start is None:
                    self.sample_collection_start = datetime.now()
                    self.current_sample_data = []

                # Check if we've been collecting for 60 seconds
                sample_elapsed = (datetime.now() - self.sample_collection_start).total_seconds()

                if sample_elapsed < 60:
                    # Still collecting this 60s sample
                    self.current_sample_data.append({
                        'speed': current_speed,
                        'trades_5s': count_5s,
                        'trades_10s': count_10s,
                        'trades_30s': count_30s,
                        'volume_usd_10s': volume_usd_10s,
                        'volume_usd_30s': volume_usd_30s
                    })
                else:
                    # 60 seconds passed - check if it's time to save this sample
                    if self.last_sample_time is None or (datetime.now() - self.last_sample_time).total_seconds() >= self.sample_interval:
                        # 10 minutes have passed - save this sample!
                        self.take_baseline_sample()
                        self.last_sample_time = datetime.now()

                    # Start new 60s collection
                    self.sample_collection_start = datetime.now()
                    self.current_sample_data = []

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
        """Check if a symbol is near support or resistance (using 60-minute levels)"""
        current_price = self.symbol_data[symbol]['current_price']
        if current_price == 0:
            return None

        # Use 60-candle S/R (hourly support/resistance) for more stability
        support_60 = self.symbol_data[symbol]['support_60']
        resistance_60 = self.symbol_data[symbol]['resistance_60']

        dist_support = ((current_price - support_60) / current_price) * 100
        dist_resistance = ((resistance_60 - current_price) / current_price) * 100

        near_support = dist_support <= self.proximity_threshold
        near_resistance = dist_resistance <= self.proximity_threshold
        broke_support = dist_support < 0
        broke_resistance = dist_resistance < 0

        return {
            'dist_support_60': dist_support,
            'dist_resistance_60': dist_resistance,
            'near_support': near_support,
            'near_resistance': near_resistance,
            'broke_support': broke_support,
            'broke_resistance': broke_resistance
        }

    def generate_combined_signal(self, metrics):
        """
        Generate signal based on COMBINED velocity + which symbols are at key levels

        Returns: (signal_type, signal_strength, symbols_involved)
        """
        speed_mult = metrics['speed_multiplier']

        # Not enough data yet
        if not self.baseline_calculated:
            return "CALM", 0, []

        # Check if combined speed is elevated
        speed_elevated = speed_mult >= self.speed_multiplier_threshold

        if not speed_elevated:
            return "CALM", 0, []

        # Check which symbols are near S/R
        # IMPORTANT: Only check the CLOSER level (never both!)
        btc_prox = self.check_symbol_proximity('BTCUSDT')
        eth_prox = self.check_symbol_proximity('ETHUSDT')

        symbols_at_resistance = []
        symbols_at_support = []
        symbols_broke_resistance = []
        symbols_broke_support = []

        # BTC - Pick CLOSER level only
        if btc_prox:
            # Which level is closer?
            dist_to_support = abs(btc_prox['dist_support_60'])
            dist_to_resistance = abs(btc_prox['dist_resistance_60'])

            if dist_to_support < dist_to_resistance:
                # Support is closer - only check support
                if btc_prox['broke_support']:
                    symbols_broke_support.append('BTC')
                elif btc_prox['near_support']:
                    symbols_at_support.append('BTC')
            else:
                # Resistance is closer - only check resistance
                if btc_prox['broke_resistance']:
                    symbols_broke_resistance.append('BTC')
                elif btc_prox['near_resistance']:
                    symbols_at_resistance.append('BTC')

        # ETH - Pick CLOSER level only
        if eth_prox:
            # Which level is closer?
            dist_to_support = abs(eth_prox['dist_support_60'])
            dist_to_resistance = abs(eth_prox['dist_resistance_60'])

            if dist_to_support < dist_to_resistance:
                # Support is closer - only check support
                if eth_prox['broke_support']:
                    symbols_broke_support.append('ETH')
                elif eth_prox['near_support']:
                    symbols_at_support.append('ETH')
            else:
                # Resistance is closer - only check resistance
                if eth_prox['broke_resistance']:
                    symbols_broke_resistance.append('ETH')
                elif eth_prox['near_resistance']:
                    symbols_at_resistance.append('ETH')

        # Calculate signal strength
        strength = min(100, int((speed_mult - 1) * 30))

        # Bonus strength for multiple symbols
        if len(symbols_at_resistance) == 2 or len(symbols_broke_resistance) == 2:
            strength += 30  # Both symbols = much stronger!
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
        """Log all data to CSV"""
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
                # S/R (60-minute)
                self.symbol_data['BTCUSDT']['support_60'],
                f"{btc_prox['dist_support_60']:.3f}" if btc_prox else "0",
                self.symbol_data['BTCUSDT']['resistance_60'],
                f"{btc_prox['dist_resistance_60']:.3f}" if btc_prox else "0",
                self.symbol_data['ETHUSDT']['support_60'],
                f"{eth_prox['dist_support_60']:.3f}" if eth_prox else "0",
                self.symbol_data['ETHUSDT']['resistance_60'],
                f"{eth_prox['dist_resistance_60']:.3f}" if eth_prox else "0",
                # Signal
                signal,
                signal_strength,
                '+'.join(signal_symbols) if signal_symbols else ''
            ])

    def print_signal(self, signal, signal_strength, signal_symbols, metrics):
        """Print signal with 3-column display: Baseline | Current | Multiplier"""

        # Clear screen for continuous updating display
        console.clear()

        # Show timestamp
        console.print(f"[dim]Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")

        # ALWAYS show red or green based on which level is CLOSER (not velocity-based)
        # Check BTC proximity to determine color
        btc_prox = self.check_symbol_proximity('BTCUSDT')
        eth_prox = self.check_symbol_proximity('ETHUSDT')

        # Determine which level is closer for BTC (primary)
        if btc_prox:
            dist_to_support = abs(btc_prox['dist_support_60'])
            dist_to_resistance = abs(btc_prox['dist_resistance_60'])

            if dist_to_support < dist_to_resistance:
                # Closer to support - Longs at risk
                color = "bright_green"
                emoji = "💥"
                direction = "LONG LIQS"
            else:
                # Closer to resistance - Shorts at risk
                color = "bright_red"
                emoji = "🚀"
                direction = "SHORT LIQS"
        else:
            # Fallback if no proximity data
            color = "cyan"
            emoji = "📊"
            direction = "MONITORING"

        # Create 3-column table with headers
        # Order: Metric | Baseline | Current | Multiplier (reads left to right mathematically)
        table = Table(box=box.DOUBLE, border_style=color, show_header=True, padding=(0, 1))
        table.add_column("Metric", style="cyan bold", width=25, no_wrap=True)
        table.add_column("Baseline", style="yellow", width=18, justify="right", no_wrap=True)
        table.add_column("Current", style="white bold", width=18, justify="right", no_wrap=True)
        table.add_column("Multiplier", style=color + " bold", width=12, justify="center", no_wrap=True)

        # Signal info row - show proximity-based status
        if btc_prox:
            dist_to_support = abs(btc_prox['dist_support_60'])
            dist_to_resistance = abs(btc_prox['dist_resistance_60'])
            closer_level = "SUPPORT" if dist_to_support < dist_to_resistance else "RESISTANCE"
            closer_dist = min(dist_to_support, dist_to_resistance)

            table.add_row(f"[{color} bold]Closer to: {closer_level}[/{color} bold]", "", "", f"[{color} bold]{direction}[/{color} bold]")
            table.add_row(f"[dim]Distance: {closer_dist:.2f}%[/dim]", "", "", f"[dim]Velocity: {metrics['speed_multiplier']:.2f}x[/dim]")
        else:
            table.add_row(f"[{color}]{direction}[/{color}]", "", "", "")

        table.add_row("", "", "", "")

        # Prices
        table.add_row("💵 BTC Price", "", f"${self.symbol_data['BTCUSDT']['current_price']:,.2f}", "")
        table.add_row("💵 ETH Price", "", f"${self.symbol_data['ETHUSDT']['current_price']:,.2f}", "")
        table.add_row("", "", "", "")

        # Speed (MOST IMPORTANT!)
        table.add_row(
            "⚡ SPEED (trades/sec)",
            f"{metrics['baseline_speed']:.1f}",
            f"{metrics['current_speed']:.1f}",
            f"[{color} bold]{metrics['speed_multiplier']:.2f}x[/{color} bold]"
        )
        table.add_row("", "", "", "")

        # Trade counts
        table.add_row(
            "📊 Trades (5s)",
            f"{metrics['baseline_trades_5s']:.0f}",
            f"{metrics['combined_trades_5s']}",
            f"{metrics['trades_5s_multiplier']:.2f}x"
        )
        table.add_row(
            "📊 Trades (10s)",
            f"{metrics['baseline_trades_10s']:.0f}",
            f"{metrics['combined_trades_10s']}",
            f"{metrics['trades_10s_multiplier']:.2f}x"
        )
        table.add_row(
            "📊 Trades (30s)",
            f"{metrics['baseline_trades_30s']:.0f}",
            f"{metrics['combined_trades_30s']}",
            f"{metrics['trades_30s_multiplier']:.2f}x"
        )
        table.add_row("", "", "", "")

        # USD Volumes
        table.add_row(
            "💰 Volume (10s)",
            f"${metrics['baseline_volume_usd_10s']:,.0f}",
            f"${metrics['combined_volume_usd_10s']:,.0f}",
            f"{metrics['volume_10s_multiplier']:.2f}x"
        )
        table.add_row(
            "💰 Volume (30s)",
            f"${metrics['baseline_volume_usd_30s']:,.0f}",
            f"${metrics['combined_volume_usd_30s']:,.0f}",
            f"{metrics['volume_30s_multiplier']:.2f}x"
        )
        table.add_row(
            "💰 Buy/Sell Ratio",
            "",
            f"{metrics['combined_buy_sell_ratio']:.2f}",
            ""
        )

        table.add_row("═" * 25, "═" * 18, "═" * 18, "═" * 12)

        panel = Panel(
            table,
            title=f"{emoji} Order Flow Velocity Tracker {emoji}",
            border_style=color,
            padding=(1, 1)
        )

        console.print("\n")
        console.print(panel)

        # Show baseline sample count and S/R debug
        sample_count = len(self.baseline_samples_history)
        status_parts = []

        # Baseline info
        if sample_count > 0:
            next_sample_in = int(self.sample_interval - (datetime.now() - self.last_sample_time).total_seconds()) if self.last_sample_time else self.sample_interval
            status_parts.append(f"Baseline: {sample_count} samples (next in {next_sample_in}s)")
        else:
            status_parts.append("Bootstrapping baseline...")

        status_parts.append("Color = Proximity to S/R")
        status_parts.append("Refreshing every 2s")

        console.print(f"\n[dim]{' • '.join(status_parts)}[/dim]")

        # S/R Debug info
        if btc_prox and eth_prox:
            btc_support = self.symbol_data['BTCUSDT']['support_60']
            btc_resistance = self.symbol_data['BTCUSDT']['resistance_60']
            btc_dist_sup = abs(btc_prox['dist_support_60'])
            btc_dist_res = abs(btc_prox['dist_resistance_60'])
            btc_closer = "SUP" if btc_dist_sup < btc_dist_res else "RES"

            eth_support = self.symbol_data['ETHUSDT']['support_60']
            eth_resistance = self.symbol_data['ETHUSDT']['resistance_60']
            eth_dist_sup = abs(eth_prox['dist_support_60'])
            eth_dist_res = abs(eth_prox['dist_resistance_60'])
            eth_closer = "SUP" if eth_dist_sup < eth_dist_res else "RES"

            console.print(f"[dim]BTC: ${btc_support:,.0f} ({btc_dist_sup:.2f}%) ← → ${btc_resistance:,.0f} ({btc_dist_res:.2f}%) • Closer: {btc_closer}[/dim]")
            console.print(f"[dim]ETH: ${eth_support:,.0f} ({eth_dist_sup:.2f}%) ← → ${eth_resistance:,.0f} ({eth_dist_res:.2f}%) • Closer: {eth_closer}[/dim]\n")

    def on_message(self, ws, message):
        """Handle WebSocket trade messages - combine all trades"""
        data = json.loads(message)

        if 'e' in data and data['e'] == 'trade':
            symbol = data['s']
            price = float(data['p'])
            quantity = float(data['q'])

            # Update symbol price
            self.symbol_data[symbol]['current_price'] = price

            # Add to COMBINED trade stream
            trade = {
                'time': datetime.now(),
                'symbol': symbol,
                'price': price,
                'quantity': quantity,
                'volume_usd': quantity * price,  # USD value
                'is_buyer_maker': data['m']
            }

            self.combined_trades.append(trade)

    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        console.print(f"[red]WebSocket Error: {error}[/red]")

    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        console.print("[yellow]WebSocket Connection Closed[/yellow]")
        self.running = False

    def on_open(self, ws):
        """Subscribe to trade streams when connection opens"""
        console.print(f"[green]Moon Dev's Combined Liquidation Detector Connected! 🚀[/green]")
        console.print(f"[green]Monitoring BTC + ETH as ONE COMBINED STREAM...[/green]")

        if len(self.baseline_samples_history) > 0:
            console.print(f"[cyan]✓ Using {len(self.baseline_samples_history)} historical baseline samples[/cyan]")
            console.print(f"[cyan]✓ Taking new 60s sample every 10 minutes ⚡[/cyan]\n")
        else:
            console.print(f"[yellow]⚠ No baseline history - bootstrapping first 60s sample...[/yellow]")
            console.print(f"[cyan]Then sampling every 10 minutes for persistent baseline ⚡[/cyan]\n")

        # Subscribe to both symbol trade streams
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
        last_display_time = None
        display_interval = 2  # Update display every 2 seconds

        while self.running:
            if len(self.combined_trades) < 20:
                time.sleep(1)
                continue

            # Get COMBINED metrics
            metrics = self.get_combined_metrics()

            # Generate signal based on combined velocity
            signal, signal_strength, signal_symbols = self.generate_combined_signal(metrics)

            # Log data (always log raw signal)
            self.log_data(metrics, signal, signal_strength, signal_symbols)

            # Track signal changes for logging
            if signal != "CALM" and signal != self.last_signal:
                self.last_signal = signal
                self.last_signal_time = datetime.now()

            # Always display table (every 2 seconds for continuous monitoring)
            # Display is now purely proximity-based (done inside print_signal)
            now = datetime.now()
            if last_display_time is None or (now - last_display_time).total_seconds() >= display_interval:
                self.print_signal(signal, signal_strength, signal_symbols, metrics)
                last_display_time = now

            time.sleep(1)

    def run(self):
        """Start the detector"""
        self.running = True

        # Initial S/R calculation
        console.print("[yellow]Calculating initial support/resistance levels (60-minute)...[/yellow]")
        for symbol in self.symbols:
            if self.calculate_support_resistance(symbol):
                display_symbol = symbol.replace('USDT', '')
                console.print(f"[green]✓ {display_symbol} Support (60min): ${self.symbol_data[symbol]['support_60']:,.2f}[/green]")
                console.print(f"[green]✓ {display_symbol} Resistance (60min): ${self.symbol_data[symbol]['resistance_60']:,.2f}[/green]")
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
            console.print("\n[yellow]Shutting down Moon Dev's Combined Detector... 👋[/yellow]")
            self.running = False
            if self.ws:
                self.ws.close()

    def get_latest_signal(self):
        """
        Get the latest signal - USE THIS IN YOUR TRADING BOT

        Returns ONE SIGNAL for the combined BTC+ETH market

        Example return value:
        {
            'signal': 'RESISTANCE_BREAK',
            'strength': 85,
            'symbols': ['BTC', 'ETH'],  # Which symbols are involved
            'btc_price': 97234.52,
            'eth_price': 3421.88,
            'speed_multiplier': 3.2,
            'metrics': {
                'combined_trades_5s': 142,
                'combined_trades_10s': 278,
                'combined_trades_30s': 835,
                'combined_volume_usd_10s': 1291584.10,
                'combined_volume_usd_30s': 3897341.50,
                'combined_buy_sell_ratio': 1.8,
                'current_speed': 27.8,
                'baseline_speed': 8.4,
                'speed_multiplier': 3.31
            },
            'timestamp': datetime(...)
        }
        """
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
    """Main entry point"""
    console.print("\n[bold cyan]" + "="*60 + "[/bold cyan]")
    console.print("[bold cyan]🌙 Moon Dev's Combined BTC+ETH Liquidation Detector 🚀[/bold cyan]")
    console.print("[bold cyan]" + "="*60 + "[/bold cyan]\n")

    console.print("[yellow]Analyzing BTC + ETH as ONE COMBINED MARKET STREAM[/yellow]")
    console.print("[yellow]Combined velocity = stronger signal![/yellow]\n")

    # Combined detector
    detector = CombinedLiquidationDetector(
        proximity_threshold=0.5,
        speed_multiplier_threshold=2.5  # Increased from 2.0 to reduce sensitivity
    )

    console.print(f"[cyan]Configuration:[/cyan]")
    console.print(f"  • Monitoring: BTC + ETH combined")
    console.print(f"  • Proximity Threshold: {detector.proximity_threshold}%")
    console.print(f"  • Speed Multiplier: {detector.speed_multiplier_threshold}x")
    console.print(f"  • Display: Color based on proximity to S/R")
    console.print(f"  • Log File: {detector.log_file}\n")

    detector.run()


if __name__ == "__main__":
    main()
