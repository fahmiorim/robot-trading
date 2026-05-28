"""
CLI entry point — argparse-based command dispatcher.
"""
import argparse
import sys
from typing import List, Optional


class TradingBotCLI:
    """Command-line interface for the trading bot."""

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog="robot-trading",
            description="AI-Powered MT5 Trading Robot",
        )
        self._register_commands()

    def _register_commands(self):
        sub = self.parser.add_subparsers(dest="command", help="Available commands")

        # trade
        trade = sub.add_parser("trade", help="Run live trading")
        trade.add_argument("--symbol", default="XAUUSD", help="Trading symbol")
        trade.add_argument("--timeframe", default="TIMEFRAME_M15", help="Timeframe")
        trade.add_argument("--auto", action="store_true", help="Enable auto trading")
        trade.add_argument("--dry-run", action="store_true", help="Paper trading mode")

        # backtest
        bt = sub.add_parser("backtest", help="Run backtest")
        bt.add_argument("--symbol", default="XAUUSD")
        bt.add_argument("--timeframe", default="TIMEFRAME_M15")
        bt.add_argument("--days", type=int, default=30, help="Days of data")

        # hyperopt
        hp = sub.add_parser("hyperopt", help="Run hyperparameter optimization")
        hp.add_argument("--epochs", type=int, default=100)
        hp.add_argument("--symbol", default="XAUUSD")
        hp.add_argument("--timeframe", default="TIMEFRAME_M15")

        # dashboard
        db = sub.add_parser("dashboard", help="Launch Streamlit dashboard")
        db.add_argument("--port", type=int, default=8501)

        # list-strategies
        sub.add_parser("list-strategies", help="List available strategies")

    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        return self.parser.parse_args(args)

    def run(self, args: Optional[List[str]] = None) -> int:
        parsed = self.parse_args(args)
        if not parsed.command:
            self.parser.print_help()
            return 1

        command = parsed.command

        if command == "list-strategies":
            from src.strategy.registry import StrategyResolver
            strategies = StrategyResolver.get_all_strategies()
            print("Available strategies:")
            for name, cls in strategies.items():
                print(f"  - {name}: {cls.__doc__ or ''}")
            return 0

        if command == "dashboard":
            import subprocess
            import sys as _sys
            port = getattr(parsed, 'port', 8501)
            cmd = [_sys.executable, "-m", "streamlit", "run", "dashboard.py",
                   f"--server.port={port}"]
            print(f"Launching dashboard on port {port}...")
            return subprocess.call(cmd)

        if command == "trade":
            from src.trading.engine import TradingBot
            from src.configuration.manager import ConfigManager
            from src.utils.logging import get_logger

            logger = get_logger("cli.trade")
            config = ConfigManager()
            config.set("general", "symbol", parsed.symbol)
            config.set("general", "timeframe", parsed.timeframe)
            if parsed.dry_run:
                config.set("trading", "paper_trading", True)

            bot = TradingBot(config=config)
            logger.info(f"Starting trading: {parsed.symbol} @ {parsed.timeframe}")

            if parsed.auto:
                # Run one cycle
                result = bot.run_trading_cycle()
                print(f"Trading cycle result: {result}")
            return 0

        if command == "backtest":
            from src.backtesting.engine import Backtester
            from src.configuration.manager import ConfigManager
            from src.data.provider import DataProvider
            from src.utils.logging import get_logger

            logger = get_logger("cli.backtest")
            config = ConfigManager()
            config.set("general", "symbol", parsed.symbol)
            config.set("general", "timeframe", parsed.timeframe)
            config.set("general", "data_count", parsed.days * 96)  # ~96 candles/day for M15

            logger.info(f"Running backtest: {parsed.symbol} @ {parsed.timeframe}, {parsed.days}d")
            provider = DataProvider(config)
            data = provider.fetch_data()
            backtester = Backtester(config)
            results = backtester.run(data)
            print(f"Backtest results: {results}")
            return 0

        if command == "hyperopt":
            from src.backtesting.hyperopt import Hyperopt
            from src.configuration.manager import ConfigManager
            from src.utils.logging import get_logger

            logger = get_logger("cli.hyperopt")
            config = ConfigManager()
            config.set("general", "symbol", parsed.symbol)
            config.set("general", "timeframe", parsed.timeframe)

            logger.info(f"Running hyperopt: {parsed.epochs} epochs")
            hp = Hyperopt(config=config)
            results = hp.optimize(n_trials=parsed.epochs)
            print(f"Hyperopt results: {results}")
            return 0

        return 0


def main():
    cli = TradingBotCLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
