"""
Binance WebSocket Price Tracker
By Moon Dev

A super fun, compact terminal-based price tracker that shows real-time crypto prices
with colors and time-based changes!
"""

import json
import websocket
import threading
from datetime import datetime, timedelta
from collections import deque
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich import box
import time

# Moon Dev's Crypto Price Tracker
console = Console()

class PriceTracker:
    def __init__(self, symbols):
        self.symbols = symbols
        self.prices = {}
        self.price_history = {}  # Store price history with timestamps
        self.ws = None

        # Initialize price data
        for symbol in symbols:
            self.prices[symbol] = 0.0
            self.price_history[symbol] = deque(maxlen=1800)  # Keep 30 mins at 1 update/sec

    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        data = json.loads(message)

        if 's' in data and 'c' in data:
            symbol = data['s'].replace('USDT', '')
            current_price = float(data['c'])
            current_time = datetime.now()

            # Update current price
            self.prices[symbol] = current_price

            # Store price with timestamp
            self.price_history[symbol].append((current_time, current_price))

    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        console.print(f"[red]WebSocket Error: {error}[/red]")

    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        console.print("[yellow]WebSocket Connection Closed[/yellow]")

    def on_open(self, ws):
        """Subscribe to ticker streams when connection opens"""
        console.print("[green]Moon Dev's Price Tracker Connected! 🚀[/green]")

        # Subscribe to all symbols
        streams = [f"{symbol.lower()}usdt@ticker" for symbol in self.symbols]
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": 1
        }
        ws.send(json.dumps(subscribe_message))

    def start_websocket(self):
        """Start WebSocket connection in a separate thread"""
        websocket.enableTrace(False)

        # Create WebSocket URL
        ws_url = "wss://stream.binance.com:9443/ws"

        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )

        # Run WebSocket in separate thread
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

    def get_change_percentage(self, symbol, minutes_ago):
        """Calculate percentage change from N minutes ago"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 2:
            return 0.0

        current_price = self.prices[symbol]
        target_time = datetime.now() - timedelta(minutes=minutes_ago)

        # Find the closest price to the target time
        history = list(self.price_history[symbol])
        old_price = None

        for timestamp, price in history:
            if timestamp <= target_time:
                old_price = price
            else:
                break

        # If we don't have data that old, use the oldest we have
        if old_price is None and len(history) > 0:
            old_price = history[0][1]

        if old_price and old_price != 0:
            return ((current_price - old_price) / old_price) * 100
        return 0.0

    def create_display(self):
        """Create the beautiful compact terminal display"""
        # Create compact table
        table = Table(
            title="🌙 Moon Dev Tracker 🚀",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            title_style="bold cyan",
            border_style="bright_blue",
            padding=(0, 1)
        )

        table.add_column("Coin", style="cyan bold", justify="center", width=6)
        table.add_column("Price", style="white", justify="right", width=11)
        table.add_column("5m", justify="center", width=8)
        table.add_column("30m", justify="center", width=8)

        for symbol in self.symbols:
            price = self.prices.get(symbol, 0.0)
            change_5m = self.get_change_percentage(symbol, 5)
            change_30m = self.get_change_percentage(symbol, 30)

            # Format price
            if price >= 1000:
                price_str = f"${price:,.2f}"
            elif price >= 1:
                price_str = f"${price:.2f}"
            else:
                price_str = f"${price:.6f}"

            # Format 5min change
            if change_5m > 0:
                change_5m_str = f"[bold green]+{change_5m:.2f}%[/bold green]"
            elif change_5m < 0:
                change_5m_str = f"[bold red]{change_5m:.2f}%[/bold red]"
            else:
                change_5m_str = f"[white]{change_5m:.2f}%[/white]"

            # Format 30min change
            if change_30m > 0:
                change_30m_str = f"[bold green]+{change_30m:.2f}%[/bold green]"
            elif change_30m < 0:
                change_30m_str = f"[bold red]{change_30m:.2f}%[/bold red]"
            else:
                change_30m_str = f"[white]{change_30m:.2f}%[/white]"

            # Add row
            table.add_row(
                symbol,
                price_str,
                change_5m_str,
                change_30m_str
            )

        # Add compact timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Create compact panel
        panel = Panel(
            table,
            subtitle=f"⏰ {timestamp}",
            subtitle_align="right",
            border_style="bright_blue",
            padding=(0, 1)
        )

        return panel

    def run(self):
        """Run the live display"""
        # Start WebSocket
        self.start_websocket()

        # Wait for initial data
        console.print("[yellow]Connecting to Binance WebSocket...[/yellow]")
        time.sleep(2)

        # Start live display
        try:
            with Live(self.create_display(), refresh_per_second=4, console=console) as live:
                while True:
                    live.update(self.create_display())
                    time.sleep(0.25)
        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down Moon Dev's Price Tracker... 👋[/yellow]")
            if self.ws:
                self.ws.close()


def main():
    """Main entry point"""
    # Symbols to track
    symbols = ['BTC', 'ETH']

    console.print("\n[bold cyan]🌙 Moon Dev's Compact Price Tracker 🚀[/bold cyan]\n")

    tracker = PriceTracker(symbols)
    tracker.run()


if __name__ == "__main__":
    main()
