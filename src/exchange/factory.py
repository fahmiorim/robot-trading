"""Exchange factory — creates the appropriate exchange backend from config.

Currently only MT5 is supported (bybit and ccxt backends have been removed).

Usage:
    exchange = ExchangeFactory.from_config(config)
"""

from typing import Optional

from src.configuration.manager import ConfigManager
from src.exchange.base import IExchange
from src.exchange.mt5 import MT5Exchange
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ExchangeFactory:
    """Factory for creating exchange instances based on config."""

    @staticmethod
    def from_config(config: ConfigManager, symbol: Optional[str] = None) -> IExchange:
        """Create and return the appropriate exchange backend.

        Currently only returns a configured MT5Exchange instance.

        Args:
            config: Application config manager.
            symbol: Trading symbol (falls back to ``general.symbol``).

        Returns:
            Configured exchange instance.
        """
        sym = symbol or config.get("general", "symbol")
        magic = config.get("general", "magic_number")
        sl_pct = config.get("exchange", "default_sl_pct")
        tp_pct = config.get("exchange", "default_tp_pct")

        return MT5Exchange(symbol=sym, magic_number=magic,
                           default_sl_pct=sl_pct, default_tp_pct=tp_pct)
