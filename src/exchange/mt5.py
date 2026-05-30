"""
MetaTrader 5 exchange implementation.

Wraps the MetaTrader5 Python API behind the ``IExchange`` interface so
the rest of the bot never talks to the MT5 DLL directly.

This module is the main facade; domain logic is delegated to mixin
classes in sibling modules:

- ``MT5ConnectionMixin``   — connect / disconnect / reconnect
- ``MT5MarketMixin``       — market watch subscription, OHLCV, ticker
- ``MT5OrderMixin``        — order placement, position management
- ``MT5AccountMixin``      — balance, trade history, symbol info
- ``MT5HelperMixin``       — price normalisation, volume helpers
"""

import time
from typing import Any, Optional, Set

from src.exchange.base import IExchange
from src.exchange.mt5_connection import MT5ConnectionMixin
from src.exchange.mt5_market import MT5MarketMixin
from src.exchange.mt5_orders import MT5OrderMixin
from src.exchange.mt5_account import MT5AccountMixin
from src.exchange.mt5_helpers import MT5HelperMixin
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MT5Exchange(
    MT5ConnectionMixin,
    MT5MarketMixin,
    MT5OrderMixin,
    MT5AccountMixin,
    MT5HelperMixin,
    IExchange,
):
    """Exchange implementation for MetaTrader 5
    (facade — logic lives in mixins above).
    """

    _initialized: bool = False
    _subscribed_symbols: Set[str] = set()

    def __init__(self, symbol: str,
                 magic_number: int,
                 default_sl_pct: float,
                 default_tp_pct: float,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 reconnect_interval: int = 60):
        self.symbol = symbol
        self.magic_number = magic_number
        self.default_sl_pct = default_sl_pct
        self.default_tp_pct = default_tp_pct
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.reconnect_interval = reconnect_interval
        self.last_order_time: float = 0
        self.last_heartbeat: float = time.time()
        logger.debug(f"MT5Exchange created for {symbol}")

