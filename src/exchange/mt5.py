"""
MetaTrader 5 exchange implementation.

Wraps the MetaTrader5 Python API behind the ``IExchange`` interface so
the rest of the bot never talks to the MT5 DLL directly.
"""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import MetaTrader5 as mt5
import pandas as pd

from src.constants import (
    get_retcode_label, get_best_filling_mode, get_next_filling_mode,
    RECOVERABLE_RETCODES, TIMEFRAME_MAP,
    TRADE_MODE_DISABLED, TRADE_MODE_LONGONLY, TRADE_MODE_SHORTONLY,
    TRADE_MODE_CLOSEONLY, TRADE_MODE_FULL, TRADE_MODE_LABELS,
)
from src.utils.exceptions import (
    ExchangeError, ConnectionError, OrderError,
    InvalidPriceError, InvalidVolumeError,
)
from src.exchange.base import IExchange
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MT5Exchange(IExchange):
    """Exchange implementation for MetaTrader 5."""

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

    # ── Connection Lifecycle ──────────────────────────────────

    def connect(self) -> bool:
        """Initialize MT5 connection (singleton)."""
        if MT5Exchange._initialized:
            if self.is_connected():
                self._resubscribe_all()
                return True
            logger.warning("Flag set but terminal disconnected, reinitialising...")
            MT5Exchange._initialized = False
            MT5Exchange._subscribed_symbols.clear()
            mt5.shutdown()

        logger.info("Initialising MT5 connection...")
        if mt5.initialize():
            MT5Exchange._initialized = True
            self.last_heartbeat = time.time()
            self._subscribe_symbol(self.symbol)
            logger.info(f"MT5 initialised, Market Watch enabled for {self.symbol}")
            return True
        logger.error("MT5 initialisation failed")
        return False

    def disconnect(self) -> None:
        """Shut down MT5 connection safely."""
        if MT5Exchange._initialized:
            logger.info("Shutting down MT5...")
            mt5.shutdown()
            MT5Exchange._initialized = False
            MT5Exchange._subscribed_symbols.clear()
            logger.info("MT5 shutdown complete")

    def ensure_connection(self) -> bool:
        """Connect with retry loop (up to 30 min)."""
        if self.connect() and self.is_connected():
            return True

        for attempt in range(60):
            time.sleep(self.reconnect_interval)
            try:
                if mt5.initialize():
                    MT5Exchange._initialized = True
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

    # ── Market Watch Subscription ─────────────────────────────

    def _subscribe_symbol(self, symbol: str) -> bool:
        """Add a symbol to Market Watch so tick data is received."""
        try:
            # First check if it is already selected
            info = mt5.symbol_info(symbol)
            if info is not None and info.select:
                MT5Exchange._subscribed_symbols.add(symbol)
                return True
                
            ok = mt5.symbol_select(symbol, True)
            if ok:
                MT5Exchange._subscribed_symbols.add(symbol)
            else:
                # Try to see if it even exists
                if mt5.symbol_info(symbol) is None:
                    logger.error(f"Symbol {symbol} not found in terminal")
            return ok
        except Exception as e:
            logger.error(f"Error subscribing to {symbol}: {e}")
            return False

    def _unsubscribe_symbol(self, symbol: str) -> bool:
        """Remove symbol from Market Watch."""
        try:
            ok = mt5.symbol_select(symbol, False)
            if ok:
                MT5Exchange._subscribed_symbols.discard(symbol)
            return ok
        except Exception:
            return False

    def _resubscribe_all(self):
        """Re-subscribe all tracked symbols after reconnect."""
        for sym in list(MT5Exchange._subscribed_symbols):
            try:
                mt5.symbol_select(sym, True)
            except Exception:
                pass

    # ── Data ──────────────────────────────────────────────────

    def fetch_ohlcv(self, symbol: str, timeframe: str,
                    count: int = 1000) -> pd.DataFrame:
        """Fetch OHLCV candles from MT5.

        Args:
            symbol: Trading symbol (e.g. XAUUSD).
            timeframe: Timeframe string (e.g. TIMEFRAME_M15).
            count: Number of candles to fetch.

        Returns:
            DataFrame with columns [open, high, low, close, volume]
            and a datetime index.
        """
        tf_value = TIMEFRAME_MAP.get(timeframe, 15)
        if not self.ensure_connection():
            raise ConnectionError("MT5 not connected")

        # Ensure symbol is selected
        self._subscribe_symbol(symbol)

        rates = None
        for attempt in range(3):
            rates = mt5.copy_rates_from_pos(symbol, tf_value, 0, count)
            if rates is not None and len(rates) > 0:
                break
            logger.warning(f"No OHLCV data for {symbol} (attempt {attempt+1}), retrying...")
            time.sleep(0.5)

        if rates is None or len(rates) == 0:
            raise ConnectionError(f"No data received for {symbol} after retries. Terminal might be syncing.")

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df = df.set_index('time')

        # Rename tick_volume -> volume if needed
        if 'tick_volume' in df.columns:
            df = df.rename(columns={'tick_volume': 'volume'})
        # Keep 'spread' and 'real_volume' columns if present
        return df

    def fetch_ticker(self, symbol: str) -> Dict[str, float]:
        """Get current bid/ask prices and daily volume info."""
        tick = self._get_tick(symbol)
        if tick is None:
            # Try a direct symbol_info_tick call if the tracked set failed
            tick = mt5.symbol_info_tick(symbol)
            
        if tick is None:
            return {'bid': 0.0, 'ask': 0.0, 'last': 0.0, 'time': 0, 'symbol': symbol, 'volume': 0.0, 'quoteVolume': 0.0}

        vol = 0.0
        quote_vol = 0.0
        try:
            info = mt5.symbol_info(symbol)
            if info is not None:
                vol = float(getattr(info, 'session_volume', 0.0) or getattr(info, 'volume24h', 0.0))
                quote_vol = float(getattr(info, 'session_turnover', 0.0) or (vol * float(tick.last or tick.bid or 0.0)))
        except Exception:
            pass

        return {
            'bid': float(tick.bid),
            'ask': float(tick.ask),
            'last': float(tick.last),
            'time': int(tick.time),
            'symbol': symbol,
            'volume': vol,
            'quoteVolume': quote_vol
        }

    def _get_tick(self, symbol: str):
        """Get tick with auto-subscribe fallback."""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None and symbol not in MT5Exchange._subscribed_symbols:
            if self._subscribe_symbol(symbol):
                tick = mt5.symbol_info_tick(symbol)
        return tick

    # ── Orders ────────────────────────────────────────────────

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
            raise ConnectionError("MT5 not connected")

        # Resolve order side
        is_buy = side.upper() == "BUY"
        
        # Validate/align volume to step and limits
        info = self.get_symbol_info(symbol)
        volume = self.validate_volume(
            volume,
            volume_min=info.get('volume_min', 0.01),
            volume_max=info.get('volume_max', 100.0),
            volume_step=info.get('volume_step', 0.01)
        )
        mt5_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
        tick = self._get_tick(symbol)
        if tick is None:
            raise ExchangeError("Cannot get tick data")

        entry_price = tick.ask if is_buy else tick.bid
        if entry_price <= 0:
            raise InvalidPriceError(f"Invalid entry price: {entry_price}")

        # Normalise price to symbol digits
        entry_price = self._normalise_price(symbol, entry_price)
        if sl is not None:
            sl = self._normalise_price(symbol, sl)
        if tp is not None:
            tp = self._normalise_price(symbol, tp)

        # Validate SL/TP distance
        sl, tp = self._validate_sltp_distance(symbol, entry_price, sl, tp)

        # Ensure symbol in Market Watch
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
                    sl = self._normalise_price(symbol,
                                                self._default_sl(entry_price, side))
                    tp = self._normalise_price(symbol,
                                                self._default_tp(entry_price, side))
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

            logger.info(f"Order #{attempt}/{self.max_retries}: {side} {volume} {symbol} "
                        f"@ {entry_price:.2f} fill={fill_label}")

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
                if retcode == 10030:  # Invalid fill mode
                    fill_mode = get_next_filling_mode(fill_label)
                    fill_label = ("None (omit)" if fill_mode is None
                                  else "ORDER_FILLING_RETURN" if fill_mode == 2
                                  else "ORDER_FILLING_IOC" if fill_mode == 1
                                  else "ORDER_FILLING_FOK")
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

    # ── Positions ─────────────────────────────────────────────

    def get_open_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get open positions from MT5."""
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
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

                close_type = (mt5.ORDER_TYPE_SELL
                              if pos.type == mt5.POSITION_TYPE_BUY
                              else mt5.ORDER_TYPE_BUY)
                tick = mt5.symbol_info_tick(pos.symbol)
                if tick is None:
                    return {'success': False, 'error': 'No tick data'}

                close_price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask
                close_price = self._normalise_price(pos.symbol, close_price)

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
                    logger.error(f"order_send returned None closing position {ticket}. MT5 last_error: {err}")
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

    # ── Account ───────────────────────────────────────────────

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
        cols = [c for c in ['time', 'symbol', 'type', 'volume',
                             'price_open', 'price_close', 'profit']
                if c in df.columns]
        return df[cols].sort_values('time', ascending=False) if cols else pd.DataFrame()

    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol metadata (trade mode, lots, digits, stops level)."""
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                if self._subscribe_symbol(symbol):
                    info = mt5.symbol_info(symbol)
            if info is None:
                return {'trade_mode': None, 'volume_min': 0.01,
                        'volume_step': 0.01, 'volume_max': 100.0,
                        'digits': 2, 'point': 0.01}
            return {
                'trade_mode': int(info.trade_mode) if info.trade_mode is not None else None,
                'volume_min': float(getattr(info, 'volume_min', 0.01)),
                'volume_step': float(getattr(info, 'volume_step', 0.01)),
                'volume_max': float(getattr(info, 'volume_max', 100.0)),
                'digits': int(getattr(info, 'digits', 2)),
                'point': float(getattr(info, 'point', 0.01)),
                'trade_stops_level': int(getattr(info, 'trade_stops_level', 0)),
                'contract_size': float(getattr(info, 'trade_contract_size', 100.0)),
            }
        except Exception as e:
            logger.error(f"Error getting symbol info: {e}")
            return {'trade_mode': None, 'volume_min': 0.01,
                    'volume_step': 0.01, 'volume_max': 100.0,
                    'digits': 2, 'point': 0.01}

    def get_broker_time(self) -> datetime:
        """Get broker/server time."""
        tick = self._get_tick(self.symbol)
        if tick is None:
            return datetime.now()
        return datetime.fromtimestamp(int(tick.time))

    def wait_for_new_candle(self, timeframe_minutes: int = 15,
                            buffer_seconds: int = 3) -> bool:
        """Block until a new candle starts."""
        try:
            current = self.get_broker_time()
            total = timeframe_minutes * 60
            secs = current.second + current.microsecond / 1_000_000
            cycle = (current.minute % timeframe_minutes) * 60 + secs
            wait = total - cycle + buffer_seconds
            if 1 < wait < 5:
                time.sleep(wait)
                return True
            return False
        except Exception as e:
            logger.error(f"wait_for_new_candle error: {e}")
            return False

    # ── Helpers ───────────────────────────────────────────────

    def _normalise_price(self, symbol: str, price: float) -> float:
        """Round price to symbol digits to avoid MT5 error 10014."""
        if price is None or price <= 0:
            return 0.0
        info = self.get_symbol_info(symbol)
        digits = info.get('digits', 2)
        return round(price, digits)

    def _validate_sltp_distance(self, symbol: str, entry: float,
                                 sl: Optional[float],
                                 tp: Optional[float]):
        """Enforce broker minimum stops level distance."""
        if sl is None and tp is None:
            return sl, tp
            
        info = self.get_symbol_info(symbol)
        min_stops = info.get('trade_stops_level', 0)
        point = info.get('point', 0.01)
        if min_stops <= 0 or point <= 0:
            return sl, tp

        min_dist = min_stops * point
        digits = info.get('digits', 2)

        if sl is not None and sl > 0:
            dist = abs(entry - sl)
            if dist < min_dist:
                adjusted = entry - min_dist if sl < entry else entry + min_dist
                sl = round(adjusted, digits)
                logger.warning(f"SL adjusted to {sl} (min dist {min_dist:.{digits}f})")
        if tp is not None and tp > 0:
            dist = abs(entry - tp)
            if dist < min_dist:
                adjusted = entry + min_dist if tp > entry else entry - min_dist
                tp = round(adjusted, digits)
                logger.warning(f"TP adjusted to {tp} (min dist {min_dist:.{digits}f})")
        return sl, tp

    @staticmethod
    def validate_volume(volume: float, volume_min: float = 0.01,
                        volume_max: float = 100.0,
                        volume_step: float = 0.01) -> float:
        """Round volume to step and clamp within broker limits."""
        if volume <= 0:
            return volume_min
        volume = round(volume / volume_step) * volume_step
        return max(volume_min, min(volume, volume_max))

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

    def _default_sl(self, price: float, side: str) -> float:
        return price * (1 - self.default_sl_pct) if side.upper() == "BUY" else price * (1 + self.default_sl_pct)

    def _default_tp(self, price: float, side: str) -> float:
        return price * (1 + self.default_tp_pct) if side.upper() == "BUY" else price * (1 - self.default_tp_pct)
