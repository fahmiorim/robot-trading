"""
Exchange interface (abstract) and MT5 implementation.

Architecture inspired by Freqtrade's exchange module:
  - ``IExchange`` defines the contract (abstract base).
  - ``MT5Exchange`` implements it via MetaTrader 5.
  - Future exchange backends (OANDA, IBKR) just implement IExchange.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


class IExchange(ABC):
    """Abstract interface for all exchange backends."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the exchange/broker."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Gracefully close the connection."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if the connection is alive."""
        ...

    @abstractmethod
    def fetch_ohlcv(self, symbol: str, timeframe: str,
                    count: int = 1000) -> pd.DataFrame:
        """Fetch OHLCV candles. Must return a DataFrame with columns
        ['open', 'high', 'low', 'close', 'volume'] and a datetime index."""
        ...

    @abstractmethod
    def fetch_ticker(self, symbol: str) -> Dict[str, float]:
        """Return current bid/ask/spot price dict."""
        ...

    @abstractmethod
    def create_order(self, symbol: str, side: str, volume: float,
                     order_type: str = "market",
                     price: Optional[float] = None,
                     sl: Optional[float] = None,
                     tp: Optional[float] = None,
                     **kwargs) -> Dict[str, Any]:
        """Place an order. Returns dict with at least 'order_id' and 'filled'."""
        ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order by ID."""
        ...

    @abstractmethod
    def get_open_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return list of open positions with at least:
        'id', 'symbol', 'side', 'volume', 'entry_price', 'current_price', 'pnl'."""
        ...

    @abstractmethod
    def close_position(self, position_id: str) -> Dict[str, Any]:
        """Close a specific position. Returns result dict."""
        ...

    @abstractmethod
    def get_balance(self) -> Dict[str, float]:
        """Return account balance info: balance, equity, margin, free_margin."""
        ...

    @abstractmethod
    def get_trade_history(self, days: int = 30) -> pd.DataFrame:
        """Fetch historical closed trades."""
        ...

    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Return symbol metadata (digits, lot steps, trade mode, etc.)."""
        ...

    @abstractmethod
    def get_broker_time(self) -> datetime:
        """Get current broker/server time."""
        ...

    @abstractmethod
    def wait_for_new_candle(self, timeframe_minutes: int = 15,
                            buffer_seconds: int = 3) -> bool:
        """Block until a new candle opens."""
        ...

    def create_stop_loss_limit_order(self, symbol: str, side: str, volume: float,
                                      stop_price: float, limit_price: float,
                                      **kwargs) -> Dict[str, Any]:
        """Place a stop-loss-limit order.

        Stops at stop_price, then enters a limit order at limit_price.
        Not all exchanges support this natively.
        """
        raise NotImplementedError("stop-loss-limit not supported by this exchange")

    def create_oco_order(self, symbol: str, side: str, volume: float,
                          price: float, stop_loss_price: float,
                          take_profit_price: float,
                          **kwargs) -> Dict[str, Any]:
        """Place an OCO (One-Cancels-Other) order.

        Places both a limit order (take-profit) and a stop order (stop-loss)
        simultaneously. When one fills, the other is auto-cancelled.
        """
        raise NotImplementedError("OCO not supported by this exchange")

    @abstractmethod
    def get_symbols(self) -> List[str]:
        """Return list of all available trading symbols."""
        ...
