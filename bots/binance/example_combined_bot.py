"""
Example Combined Bot Integration by Moon Dev

Shows how to use the combined BTC+ETH liquidation detector in a trading bot.
ONE SIGNAL based on combined market velocity!

This is a MOCK bot for testing - replace with your exchange integration.
"""

import time
from combined_liquidation_detector import CombinedLiquidationDetector
from rich.console import Console

console = Console()

class MockCombinedBot:
    """
    Example trading bot using combined BTC+ETH signals

    Replace mock_place_order with your actual exchange API calls
    """

    def __init__(self, position_size_usd=10):
        self.position_size_usd = position_size_usd
        self.in_position = False
        self.position_side = None
        self.position_symbols = []  # Which symbols we're trading

        # Initialize COMBINED detector
        self.detector = CombinedLiquidationDetector(
            proximity_threshold=0.5,
            speed_multiplier_threshold=2.0
        )

        # Start detector in background
        import threading
        detector_thread = threading.Thread(target=self.detector.run)
        detector_thread.daemon = True
        detector_thread.start()

        time.sleep(5)  # Let detector initialize

    def mock_place_order(self, symbols, side, size_usd):
        """
        Mock order placement - replace with your exchange API

        Args:
            symbols: List of symbols involved (e.g., ['BTC', 'ETH'])
            side: 'BUY' or 'SELL'
            size_usd: Dollar amount
        """
        symbols_str = ' + '.join(symbols)
        console.print(f"\n[bold yellow]🎯 MOCK ORDER: {side} ${size_usd} on {symbols_str}[/bold yellow]")
        console.print(f"[yellow]   Replace this with your exchange API call![/yellow]\n")

        # In a real bot, you might split the order across symbols:
        # if 'BTC' in symbols:
        #     exchange.place_market_order('BTC', side, size_usd / len(symbols))
        # if 'ETH' in symbols:
        #     exchange.place_market_order('ETH', side, size_usd / len(symbols))

    def mock_close_position(self):
        """Mock position close"""
        symbols_str = ' + '.join(self.position_symbols)
        console.print(f"\n[bold yellow]🎯 MOCK CLOSE: {self.position_side} position on {symbols_str}[/bold yellow]\n")

    def execute_signal(self, signal_data):
        """
        Execute trades based on combined signal

        Signal logic:
        - RESISTANCE_BREAK: Shorts liquidating across market → Go LONG
        - SUPPORT_BREAK: Longs liquidating across market → Go SHORT

        When both BTC and ETH signal together = ULTRA strong signal!
        """
        signal = signal_data['signal']
        strength = signal_data['strength']
        symbols = signal_data['symbols']

        # Minimum signal strength threshold
        if strength < 60:
            return

        # Already in position - manage exit
        if self.in_position:
            # Close position on opposite signal
            if signal == 'RESISTANCE_BREAK' and self.position_side == 'SHORT':
                self.mock_close_position()
                self.in_position = False
                self.position_side = None
                self.position_symbols = []

            elif signal == 'SUPPORT_BREAK' and self.position_side == 'LONG':
                self.mock_close_position()
                self.in_position = False
                self.position_side = None
                self.position_symbols = []

            return

        # Not in position - look for entry
        if signal == 'RESISTANCE_BREAK' and strength >= 70:
            # Market liquidating shorts
            console.print(f"[bold green]🚀 COMBINED LONG SIGNAL[/bold green]")
            console.print(f"[green]   Strength: {strength}/100[/green]")
            console.print(f"[green]   Symbols: {' + '.join(symbols)}[/green]")
            console.print(f"[green]   Speed: {signal_data['speed_multiplier']:.2f}x[/green]")

            self.mock_place_order(symbols, 'BUY', self.position_size_usd)
            self.in_position = True
            self.position_side = 'LONG'
            self.position_symbols = symbols

        elif signal == 'SUPPORT_BREAK' and strength >= 70:
            # Market liquidating longs
            console.print(f"[bold red]💥 COMBINED SHORT SIGNAL[/bold red]")
            console.print(f"[red]   Strength: {strength}/100[/red]")
            console.print(f"[red]   Symbols: {' + '.join(symbols)}[/red]")
            console.print(f"[red]   Speed: {signal_data['speed_multiplier']:.2f}x[/red]")

            self.mock_place_order(symbols, 'SELL', self.position_size_usd)
            self.in_position = True
            self.position_side = 'SHORT'
            self.position_symbols = symbols

    def run(self):
        """Main bot loop"""
        console.print("\n[bold cyan]🌙 Moon Dev's Combined BTC+ETH Bot Starting...[/bold cyan]")
        console.print(f"[cyan]Position Size: ${self.position_size_usd}[/cyan]")
        console.print(f"[cyan]Monitoring: BTC + ETH combined market[/cyan]\n")
        console.print("[yellow]This is a MOCK bot - no real orders will be placed![/yellow]")
        console.print("[yellow]Replace mock_place_order() with your exchange API calls.[/yellow]\n")

        try:
            while True:
                # Get latest COMBINED signal
                signal_data = self.detector.get_latest_signal()

                if signal_data:
                    # Execute trading logic
                    self.execute_signal(signal_data)

                # Sleep before next check
                time.sleep(2)

        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down bot... 👋[/yellow]")


def main():
    """Run the example bot"""

    # Initialize bot with small size for testing
    bot = MockCombinedBot(
        position_size_usd=10  # Start small!
    )

    # Run bot
    bot.run()


if __name__ == "__main__":
    main()
