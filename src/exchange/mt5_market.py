"""
MT5 market data — symbol subscription, OHLCV, ticker.

Mixin for ``MT5Exchange``.
"""

import time

import MetaTrader5 as mt5
import pandas as pd

from src.constants.timeframes import TIMEFRAME_MAP
from src.utils.exceptions import ConnectionError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MT5MarketMixin:
    """Mixin: symbol subscription and market data fetching."""

    def _subscribe_symbol(self, symbol: str) -> bool:
        """Add a symbol to Market Watch so tick data is received."""
        try:
            info = mt5.symbol_info(symbol)
            if info is not None and info.select:
                type(self)._subscribed_symbols.add(symbol)
                return True
            ok = mt5.symbol_select(symbol, True)
            if ok:
                type(self)._subscribed_symbols.add(symbol)
            else:
                if mt5.symbol_info(symbol) is None:
                    logger.error(f"Symbol {symbol} not found in terminal")
            return ok
        except Exception as e:
            logger.error(f"Error subscribing to {symbol}: {e}")
            return False

    def _resubscribe_all(self):
        """Re-subscribe all tracked symbols after reconnect."""
        for sym in list(type(self)._subscribed_symbols):
            try:
                mt5.symbol_select(sym, True)
            except Exception:
                pass

    def fetch_ohlcv(self, symbol: str, timeframe: str,
                    count: int = 1000) -> pd.DataFrame:
        """Fetch OHLCV candles from MT5."""
        tf_value = TIMEFRAME_MAP.get(timeframe, 15)
        if not self.ensure_connection():
            raise ConnectionError("MT5 not connected")
        self._subscribe_symbol(symbol)

        rates = None
        for attempt in range(3):
            rates = mt5.copy_rates_from_pos(symbol, tf_value, 0, count)
            if rates is not None and len(rates) > 0:
                break
            logger.warning(f"No OHLCV data for {symbol} (attempt {attempt+1}), retrying...")
            time.sleep(0.5)

        if rates is None or len(rates) == 0:
            raise ConnectionError(
                f"No data received for {symbol} after retries. Terminal might be syncing."
            )

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df = df.set_index('time')
        if 'tick_volume' in df.columns:
            df = df.rename(columns={'tick_volume': 'volume'})
        return df

    def fetch_ticker(self, symbol: str) -> dict:
        """Get current bid/ask prices and daily volume info."""
        tick = self._get_tick(symbol)
        if tick is None:
            tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {
                'bid': 0.0, 'ask': 0.0, 'last': 0.0, 'time': 0,
                'symbol': symbol, 'volume': 0.0, 'quoteVolume': 0.0,
            }
        vol = 0.0
        quote_vol = 0.0
        try:
            info = mt5.symbol_info(symbol)
            if info is not None:
                vol = float(
                    getattr(info, 'session_volume', 0.0)
                    or getattr(info, 'volume24h', 0.0)
                )
                quote_vol = float(
                    getattr(info, 'session_turnover', 0.0)
                    or (vol * float(tick.last or tick.bid or 0.0))
                )
        except Exception:
            pass
        return {
            'bid': float(tick.bid),
            'ask': float(tick.ask),
            'last': float(tick.last),
            'time': int(tick.time),
            'symbol': symbol,
            'volume': vol,
            'quoteVolume': quote_vol,
        }

    def _get_tick(self, symbol: str):
        """Get tick with auto-subscribe fallback."""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None and symbol not in type(self)._subscribed_symbols:
            if self._subscribe_symbol(symbol):
                tick = mt5.symbol_info_tick(symbol)
        return tick

    def get_broker_time(self):
        """Get broker/server time."""
        from datetime import datetime
        tick = self._get_tick(self.symbol)
        if tick is None:
            return datetime.now()
        return datetime.fromtimestamp(int(tick.time))

    def wait_for_new_candle(self, timeframe_minutes: int = 15,
                            buffer_seconds: int = 3) -> bool:
        """Block until a new candle starts."""
        import time as _time
        try:
            current = self.get_broker_time()
            total = timeframe_minutes * 60
            secs = current.second + current.microsecond / 1_000_000
            cycle = (current.minute % timeframe_minutes) * 60 + secs
            wait = total - cycle + buffer_seconds
            if 1 < wait < 5:
                _time.sleep(wait)
                return True
            return False
        except Exception as e:
            logger.error(f"wait_for_new_candle error: {e}")
            return False
