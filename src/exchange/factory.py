"""Exchange factory — creates the appropriate exchange backend from config.

Extracted from TradingController._init_exchange() to keep controllers thin.

Usage:
    exchange = ExchangeFactory.from_config(config, symbol="XAUUSD")
"""

from typing import Optional

from src.configuration.manager import ConfigManager
from src.exchange.base import IExchange
from src.exchange.mt5 import MT5Exchange
from src.exchange.ccxt import CCXTExchange
from src.exchange.bybit import BybitExchange
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ExchangeFactory:
    """Factory for creating exchange instances based on config."""

    @staticmethod
    def from_config(config: ConfigManager, symbol: Optional[str] = None) -> IExchange:
        """Create and return the appropriate exchange backend.

        Reads ``exchange.type`` from config:
          - ``bybit`` → BybitExchange
          - ``ccxt``  → CCXTExchange (generic)
          - anything else → MT5Exchange (default)

        Args:
            config: Application config manager.
            symbol: Trading symbol (falls back to ``general.symbol``).

        Returns:
            Configured exchange instance.
        """
        exchange_type = (config.get("exchange", "type") or "mt5").lower()
        sym = symbol or config.get("general", "symbol")
        magic = config.get("general", "magic_number")

        if exchange_type == "bybit":
            return ExchangeFactory._create_bybit(config, sym, magic)
        elif exchange_type == "ccxt":
            return ExchangeFactory._create_ccxt(config, sym, magic)
        else:
            return MT5Exchange(symbol=sym, magic_number=magic)

    # ── Private constructors ──────────────────────────────────

    @staticmethod
    def _create_bybit(config: ConfigManager, symbol: str, magic: int) -> BybitExchange:
        bybit_cfg = config.get("exchange", "bybit")
        return BybitExchange(
            symbol=symbol,
            api_key=config.get("exchange", "api_key"),
            secret=config.get("exchange", "secret"),
            password=config.get("exchange", "password"),
            sandbox=config.get("exchange", "sandbox"),
            category=(
                bybit_cfg.get("category", "linear")
                if isinstance(bybit_cfg, dict) else "linear"
            ),
            position_mode=(
                bybit_cfg.get("position_mode", "one-way")
                if isinstance(bybit_cfg, dict) else "one-way"
            ),
            default_leverage=(
                bybit_cfg.get("default_leverage", 5)
                if isinstance(bybit_cfg, dict) else 5
            ),
            options=config.get("exchange", "options"),
            magic_number=magic,
        )

    @staticmethod
    def _create_ccxt(config: ConfigManager, symbol: str, magic: int) -> CCXTExchange:
        return CCXTExchange(
            exchange_name=config.get("exchange", "name"),
            symbol=symbol,
            api_key=config.get("exchange", "api_key"),
            secret=config.get("exchange", "secret"),
            password=config.get("exchange", "password"),
            sandbox=config.get("exchange", "sandbox"),
            options=config.get("exchange", "options"),
            magic_number=magic,
        )
