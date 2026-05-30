"""
MT5 order and position management.

Mixin for ``MT5Exchange``.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import MetaTrader5 as mt5

from src.constants import (
    get_retcode_label, get_best_filling_mode, get_next_filling_mode,
    RECOVERABLE_RETCODES,
)
from src.utils.exceptions import ExchangeError, OrderError, InvalidPriceError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MT5OrderMixin:
    """Mixin: order creation and position management."""

    def create_order(self, symbol: str, side: str, volume: float,
                     order_type: str = "market",
                     price: Optional[float] = None,
                     sl: Optional[float] = None,
                     tp: Optional[float] = None,
                     **kwargs) -> Dict[str, Any]:
        """Send a market or limit order to MT5 with full retry logic."""
        if order_type != "market":
            raise NotImplementedError("Only market orders supported for now")
        if not self.ensure_connection():
            raise ConnectionError("MT5 not connected")  # noqa: F821

        is_buy = side.upper() == "BUY"
        info = self.get_symbol_info(symbol)
        volume = self.validate_volume(
            volume,
            volume_min=info.get('volume_min', 0.01),
            volume_max=info.get('volume_max', 100.0),
            volume_step=info.get('volume_step', 0.01),
        )
        mt5_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
        tick = self._get_tick(symbol)
        if tick is None:
            raise ExchangeError("Cannot get tick data")

        entry_price = tick.ask if is_buy else tick.bid
        if entry_price <= 0:
            raise InvalidPriceError(f"Invalid entry price: {entry_price}")

        entry_price = self._normalise_price(symbol, entry_price)
        if sl is not None:
            sl = self._normalise_price(symbol, sl)
        if tp is not None:
            tp = self._normalise_price(symbol, tp)
        sl, tp = self._validate_sltp_distance(symbol, entry_price, sl, tp)
        self._subscribe_symbol(symbol)

        last_error = None
        fill_label = "ORDER_FILLING_RETURN"
        fill_mode = get_best_filling_mode()

        for attempt in range(1, self.max_retries + 1):
            if attempt > 1:
                fresh = self.fetch_ticker(symbol)
                if fresh['bid'] > 0 and fresh['ask'] > 0:
                    entry_price = fresh['ask'] if is_buy else fresh['bid']
                    entry_price = self._normalise_price(symbol, entry_price)
                    sl = self._normalise_price(
                        symbol, self._default_sl(entry_price, side)
                    )
                    tp = self._normalise_price(
                        symbol, self._default_tp(entry_price, side)
                    )
                    sl, tp = self._validate_sltp_distance(symbol, entry_price, sl, tp)

            request = {
                'action': int(mt5.TRADE_ACTION_DEAL),
                'symbol': str(symbol),
                'volume': float(volume),
                'type': int(mt5_type),
                'price': float(entry_price),
                'sl': float(sl) if sl is not None else 0.0,
                'tp': float(tp) if tp is not None else 0.0,
                'deviation': int(10),
                'magic': int(self.magic_number),
                'comment': str(kwargs.get('comment', 'AI Robot')),
            }
            if fill_mode is not None:
                request['type_filling'] = int(fill_mode)

            logger.info(
                f"Order #{attempt}/{self.max_retries}: {side} {volume} {symbol} "
                f"@ {entry_price:.2f} fill={fill_label}"
            )
            try:
                result = mt5.order_send(request)
            except Exception as e:
                raise OrderError(f"order_send exception: {e}")

            if result is None:
                err = mt5.last_error()
                raise OrderError(f"order_send returned None. MT5 last_error: {err}")

            retcode = result.retcode
            if retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Order filled: ticket={result.order}")
                self.last_order_time = time.time()
                return {
                    'success': True,
                    'order_id': str(result.order),
                    'order': result.order,
                    'volume': volume,
                    'price': entry_price,
                }

            label = get_retcode_label(retcode)
            if retcode in RECOVERABLE_RETCODES:
                if retcode == 10030:
                    fill_mode = get_next_filling_mode(fill_label)
                    fill_label = (
                        "None (omit)" if fill_mode is None
                        else "ORDER_FILLING_RETURN" if fill_mode == 2
                        else "ORDER_FILLING_IOC" if fill_mode == 1
                        else "ORDER_FILLING_FOK"
                    )
                backoff = min(self.retry_delay * (2 ** (attempt - 1)), 30.0)
                logger.warning(f"Retryable error: {label}. Retry in {backoff:.1f}s")
                time.sleep(backoff)
                last_error = {'success': False, 'error': label, 'retcode': retcode}
                continue

            logger.error(f"Order rejected: {label}")
            return {'success': False, 'error': label, 'retcode': retcode}

        raise OrderError(f"All retries exhausted: {last_error}")

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order by ticket."""
        raise NotImplementedError("Pending order cancellation not yet implemented")

    def get_open_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get open positions from MT5."""
        try:
            positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            if positions is None:
                return []
            result = []
            for pos in positions:
                result.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL',
                    'volume': pos.volume,
                    'open_price': pos.price_open,
                    'current_price': pos.price_current,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'profit': pos.profit,
                    'swap': pos.swap,
                    'comment': pos.comment,
                    'magic': pos.magic,
                    'open_time': datetime.fromtimestamp(pos.time),
                })
            return result
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []

    def close_position(self, position_id: str) -> Dict[str, Any]:
        """Close a specific position by ticket number."""
        logger.info(f"Closing position: ticket={position_id}")
        ticket = int(position_id)

        for attempt in range(1, 4):
            try:
                positions = mt5.positions_get(ticket=ticket)
                if positions is None or len(positions) == 0:
                    return {'success': False, 'error': 'Position not found'}
                pos = positions[0]
                close_type = (
                    mt5.ORDER_TYPE_SELL
                    if pos.type == mt5.POSITION_TYPE_BUY
                    else mt5.ORDER_TYPE_BUY
                )
                tick = mt5.symbol_info_tick(pos.symbol)
                if tick is None:
                    return {'success': False, 'error': 'No tick data'}

                close_price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask
                close_price = self._normalise_price(pos.symbol, close_price)

                from src.constants import get_best_filling_mode
                request = {
                    'action': int(mt5.TRADE_ACTION_DEAL),
                    'symbol': str(pos.symbol),
                    'volume': float(pos.volume),
                    'type': int(close_type),
                    'position': int(ticket),
                    'price': float(close_price),
                    'deviation': int(30),
                    'magic': int(self.magic_number),
                    'comment': 'Close',
                }
                fill_mode = get_best_filling_mode()
                if fill_mode is not None:
                    request['type_filling'] = int(fill_mode)

                result = mt5.order_send(request)
                if result is None:
                    err = mt5.last_error()
                    logger.error(
                        f"order_send returned None closing position {ticket}. "
                        f"MT5 last_error: {err}"
                    )
                    continue
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"Position {ticket} closed")
                    return {'success': True, 'order': result.order}

                label = get_retcode_label(result.retcode)
                if result.retcode in (10004, 10006, 10014):
                    time.sleep(0.5)
                    continue
                return {'success': False, 'error': label, 'retcode': result.retcode}
            except Exception as e:
                logger.error(f"Close error (attempt {attempt}): {e}")
                time.sleep(0.5)

        return {'success': False, 'error': 'Max retries exhausted'}
