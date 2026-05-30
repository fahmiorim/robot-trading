"""
MT5 account information and symbol metadata.

Mixin for ``MT5Exchange``.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import MetaTrader5 as mt5
import pandas as pd

from src.utils.logging import get_logger

logger = get_logger(__name__)


class MT5AccountMixin:
    """Mixin: account balance, trade history, symbol info."""

    def get_balance(self) -> Dict[str, float]:
        """Get account balance info."""
        account = mt5.account_info()
        if account is None:
            return {'balance': 0, 'equity': 0, 'margin': 0, 'free_margin': 0}
        return {
            'balance': float(account.balance),
            'equity': float(account.equity),
            'margin': float(account.margin),
            'free_margin': float(account.margin_free),
            'margin_level': float(account.margin_level or 0),
            'profit': float(account.profit or 0),
        }

    def get_trade_history(self, days: int = 30) -> pd.DataFrame:
        """Get historical closed trades."""
        from_time = int((datetime.now() - timedelta(days=days)).timestamp())
        to_time = int(datetime.now().timestamp())
        orders = mt5.history_orders_get(from_time, to_time)
        if orders is None or len(orders) == 0:
            return pd.DataFrame()
        df = pd.DataFrame(list(orders))
        cols = [
            c for c in ['time', 'symbol', 'type', 'volume',
                         'price_open', 'price_close', 'profit']
            if c in df.columns
        ]
        return df[cols].sort_values('time', ascending=False) if cols else pd.DataFrame()

    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol metadata (trade mode, lots, digits, stops level)."""
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                if self._subscribe_symbol(symbol):
                    info = mt5.symbol_info(symbol)
            if info is None:
                return {
                    'trade_mode': None, 'volume_min': 0.01,
                    'volume_step': 0.01, 'volume_max': 100.0,
                    'digits': 2, 'point': 0.01,
                }
            return {
                'trade_mode': int(info.trade_mode) if info.trade_mode is not None else None,
                'volume_min': float(getattr(info, 'volume_min', 0.01)),
                'volume_step': float(getattr(info, 'volume_step', 0.01)),
                'volume_max': float(getattr(info, 'volume_max', 100.0)),
                'digits': int(getattr(info, 'digits', 2)),
                'point': float(getattr(info, 'point', 0.01)),
                'trade_stops_level': int(getattr(info, 'trade_stops_level', 0)),
                'contract_size': float(getattr(info, 'trade_contract_size', 100.0)),
                'description': str(getattr(info, 'description', '')),
            }
        except Exception as e:
            logger.error(f"Error getting symbol info: {e}")
            return {
                'trade_mode': None, 'volume_min': 0.01,
                'volume_step': 0.01, 'volume_max': 100.0,
                'digits': 2, 'point': 0.01,
            }

    def get_symbols(self) -> List[str]:
        """Return list of all trading symbols available in Market Watch."""
        try:
            all_symbols = mt5.symbols_get()
            if all_symbols:
                return [s.name for s in all_symbols]
            return []
        except Exception as e:
            logger.error(f"get_symbols error: {e}")
            return []
