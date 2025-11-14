"""
Example Bot Integration by Moon Dev

This shows how to use the multi_symbol_liquidation_detector module in a trading bot.
Monitors BTC and ETH - the two main market movers!
This is a MOCK bot for testing - you'll need to add your exchange integration.
"""

import time
from multi_symbol_liquidation_detector import MultiSymbolLiquidationDetector
from rich.console import Console

console = Console()

class MockTradingBot:
    """
    Example trading bot that uses liquidation signals for BTC and ETH

    Replace the mock_place_order function with your actual exchange API calls
    """

    def __init__(self, symbols=['BTCUSDT', 'ETHUSDT'], position_size_usd=10):
        self.symbols = symbols
        self.position_size_usd = position_size_usd
        self.positions = {}  # Track positions per symbol

        # Initialize positions dict
        for symbol in symbols:
            self.positions[symbol] = {
                'in_position': False,
                'side': None
            }

        # Initialize detector for BTC and ETH
        self.detector = MultiSymbolLiquidationDetector(
            symbols=symbols,
            proximity_threshold=0.5,
            speed_multiplier_threshold=2.0
        )

        # Start detector in background
        import threading
        detector_thread = threading.Thread(target=self.detector.run)
        detector_thread.daemon = True
        detector_thread.start()

        time.sleep(5)  # Let detector initialize

    def mock_place_order(self, symbol, side, size_usd):
        """
        Mock order placement - replace with your exchange API

        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            size_usd: Dollar amount
        """
        display_symbol = symbol.replace('USDT', '')
        console.print(f"\n[bold yellow]🎯 MOCK ORDER: {side} ${size_usd} {display_symbol}[/bold yellow]")
        console.print(f"[yellow]   Replace this with your exchange API call![/yellow]\n")

        # In a real bot, you'd do:
        # if side == 'BUY':
        #     exchange.place_market_buy(symbol, size_usd)
        # else:
        #     exchange.place_market_sell(symbol, size_usd)

    def mock_close_position(self, symbol):
        """Mock position close"""
        display_symbol = symbol.replace('USDT', '')
        position_side = self.positions[symbol]['side']
        console.print(f"\n[bold yellow]🎯 MOCK CLOSE: {position_side} {display_symbol} position[/bold yellow]\n")

    def execute_signal(self, symbol, signal_data):
        """
        Execute trades based on signal for a specific symbol

        Signal logic:
        - RESISTANCE_BREAK: Shorts getting liquidated -> Go LONG
        - SUPPORT_BREAK: Longs getting liquidated -> Go SHORT
        - RESISTANCE_TEST: Near resistance with speed -> Watch for SHORT
        - SUPPORT_TEST: Near support with speed -> Watch for LONG
        """
        signal = signal_data['signal']
        strength = signal_data['strength']
        display_symbol = symbol.replace('USDT', '')

        # Minimum signal strength threshold
        if strength < 60:
            return

        # Already in position - manage exit
        if self.positions[symbol]['in_position']:
            # Close position on opposite signal
            if signal == 'RESISTANCE_BREAK' and self.positions[symbol]['side'] == 'SHORT':
                self.mock_close_position(symbol)
                self.positions[symbol]['in_position'] = False
                self.positions[symbol]['side'] = None

            elif signal == 'SUPPORT_BREAK' and self.positions[symbol]['side'] == 'LONG':
                self.mock_close_position(symbol)
                self.positions[symbol]['in_position'] = False
                self.positions[symbol]['side'] = None

            return

        # Not in position - look for entry
        if signal == 'RESISTANCE_BREAK' and strength >= 70:
            # Shorts liquidating, momentum up
            console.print(f"[bold green]🚀 {display_symbol} LONG SIGNAL: Resistance break with {strength}% strength[/bold green]")
            self.mock_place_order(symbol, 'BUY', self.position_size_usd)
            self.positions[symbol]['in_position'] = True
            self.positions[symbol]['side'] = 'LONG'

        elif signal == 'SUPPORT_BREAK' and strength >= 70:
            # Longs liquidating, momentum down
            console.print(f"[bold red]💥 {display_symbol} SHORT SIGNAL: Support break with {strength}% strength[/bold red]")
            self.mock_place_order(symbol, 'SELL', self.position_size_usd)
            self.positions[symbol]['in_position'] = True
            self.positions[symbol]['side'] = 'SHORT'

    def run(self):
        """Main bot loop"""
        console.print("\n[bold cyan]🌙 Moon Dev's BTC & ETH Example Bot Starting...[/bold cyan]")
        console.print(f"[cyan]Position Size: ${self.position_size_usd} per symbol[/cyan]")
        console.print(f"[cyan]Symbols: BTC, ETH[/cyan]\n")
        console.print("[yellow]This is a MOCK bot - no real orders will be placed![/yellow]")
        console.print("[yellow]Replace mock_place_order() with your exchange API calls.[/yellow]\n")

        try:
            while True:
                # Get latest signals from detector for all symbols
                all_signals = self.detector.get_latest_signals()

                # Execute trading logic for each symbol
                for symbol, signal_data in all_signals.items():
                    self.execute_signal(symbol, signal_data)

                # Sleep before next check
                time.sleep(2)

        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down bot... 👋[/yellow]")


def main():
    """Run the example bot"""

    # Initialize bot with small size for testing
    # Monitors both BTC and ETH
    bot = MockTradingBot(
        symbols=['BTCUSDT', 'ETHUSDT'],
        position_size_usd=10  # Start small!
    )

    # Run bot
    bot.run()


if __name__ == "__main__":
    main()
