"""
MT5 connection lifecycle — connect, disconnect, reconnect logic.

Mixin for ``MT5Exchange``.
"""

import time

import MetaTrader5 as mt5

from src.utils.exceptions import ConnectionError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MT5ConnectionMixin:
    """Mixin: MT5 terminal connection lifecycle."""

    def connect(self) -> bool:
        """Initialize MT5 connection (singleton)."""
        if type(self)._initialized:
            if self.is_connected():
                self._resubscribe_all()
                return True
            logger.warning("Flag set but terminal disconnected, reinitialising...")
            type(self)._initialized = False
            type(self)._subscribed_symbols.clear()
            mt5.shutdown()

        logger.info("Initialising MT5 connection...")
        if mt5.initialize():
            type(self)._initialized = True
            self.last_heartbeat = time.time()
            self._subscribe_symbol(self.symbol)
            logger.info(f"MT5 initialised, Market Watch enabled for {self.symbol}")
            return True
        logger.error("MT5 initialisation failed")
        return False

    def disconnect(self) -> None:
        """Shut down MT5 connection safely."""
        if type(self)._initialized:
            logger.info("Shutting down MT5...")
            mt5.shutdown()
            type(self)._initialized = False
            type(self)._subscribed_symbols.clear()
            logger.info("MT5 shutdown complete")

    def ensure_connection(self) -> bool:
        """Connect with retry loop (up to 30 min)."""
        if self.connect() and self.is_connected():
            return True

        for attempt in range(60):
            time.sleep(self.reconnect_interval)
            try:
                if mt5.initialize():
                    type(self)._initialized = True
                    self.last_heartbeat = time.time()
                    self._resubscribe_all()
                    logger.info(f"Reconnected on attempt {attempt + 1}")
                    return True
            except Exception as e:
                logger.error(f"Reconnect attempt {attempt + 1}: {e}")
            if attempt % 10 == 0:
                logger.warning(f"Reconnect attempt {attempt + 1}/60...")
        return False

    def is_connected(self) -> bool:
        """Check if the MT5 terminal is connected."""
        try:
            terminal = mt5.terminal_info()
            if terminal is None:
                return False
            self.last_heartbeat = time.time()
            return bool(terminal.connected)
        except Exception:
            return False
