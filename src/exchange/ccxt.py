"""
CCXT-based multi-exchange implementation.

Supports 100+ exchanges (Binance, Kraken, Bybit, OKX, Coinbase, etc.)
through the unified CCXT library.

Usage:
    exchange = CCXTExchange(
        exchange_name="binance",
        api_key="...",
        secret="...",
        sandbox=True,
    )
    exchange.connect()
    ohlcv = exchange.fetch_ohlcv("BTC/USDT", "15m", count=100)
"""

import time
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import ccxt
import pandas as pd
import numpy as np

from src.exchange.base import IExchange
from src.utils.logging import get_logger
from src.utils.exceptions import (
    ExchangeError, ConnectionError, OrderError,
    InvalidPriceError, InvalidVolumeError,
)

logger = get_logger(__name__)

# Map our timeframe labels to CCXT timeframe strings
TIMEFRAME_TO_CCXT: Dict[str, str] = {
    "TIMEFRAME_M1": "1m",
    "TIMEFRAME_M5": "5m",
    "TIMEFRAME_M15": "15m",
    "TIMEFRAME_M30": "30m",
    "TIMEFRAME_H1": "1h",
    "TIMEFRAME_H2": "2h",
    "TIMEFRAME_H4": "4h",
    "TIMEFRAME_D1": "1d",
    "TIMEFRAME_W1": "1w",
}

# Reverse map: CCXT → our labels
CCXT_TO_TIMEFRAME = {v: k for k, v in TIMEFRAME_TO_CCXT.items()}


class CCXTExchange(IExchange):
    """Exchange implementation backed by the CCXT unified library.

    Supports spot, margin, and futures trading on 100+ exchanges.
    """

    def __init__(
        self,
        exchange_name: str = "binance",
        symbol: str = "BTC/USDT",
        api_key: str = "",
        secret: str = "",
        password: str = "",
        sandbox: bool = True,
        options: Optional[Dict] = None,
        enable_rate_limit: bool = True,
        magic_number: int = 2024,
    ):
        self.exchange_name = exchange_name.lower()
        self.symbol = symbol
        self.api_key = api_key
        self.secret = secret
        self.password = password
        self.sandbox = sandbox
        self._options = options or {"defaultType": "spot"}
        self.enable_rate_limit = enable_rate_limit
        self.magic_number = magic_number

        # State
        self._exchange: Optional[ccxt.Exchange] = None
        self._markets_loaded: bool = False
        self._last_heartbeat: float = 0
        self._subscribed_symbols: Set[str] = set()

        logger.debug(
            f"CCXTExchange created: {exchange_name}/{symbol}, "
            f"sandbox={sandbox}"
        )

    # ── Connection Lifecycle ──────────────────────────────────

    def connect(self) -> bool:
        """Initialise and connect to the CCXT exchange."""
        try:
            exchange_class = getattr(ccxt, self.exchange_name)
        except AttributeError:
            raise ConnectionError(
                f"Unknown exchange: '{self.exchange_name}'. "
                f"See https://docs.ccxt.com/#/README?id=exchanges"
            )

        # Build params
        params: Dict[str, Any] = {
            "enableRateLimit": self.enable_rate_limit,
        }
        if self.api_key:
            params["apiKey"] = self.api_key
        if self.secret:
            params["secret"] = self.secret
        if self.password:
            params["password"] = self.password
        if self._options:
            params["options"] = self._options

        try:
            self._exchange = exchange_class(params)
        except Exception as e:
            raise ConnectionError(
                f"Failed to initialise {self.exchange_name}: {e}"
            )

        # Sandbox mode
        if self.sandbox:
            try:
                self._exchange.set_sandbox_mode(True)
                logger.info(f"Sandbox mode enabled for {self.exchange_name}")
            except Exception as e:
                logger.warning(
                    f"Sandbox mode not supported for {self.exchange_name}: {e}"
                )

        # Load markets to verify connectivity
        try:
            self._exchange.load_markets()
            self._markets_loaded = True
            self._last_heartbeat = time.time()
            logger.info(
                f"Connected to {self.exchange_name}: "
                f"{len(self._exchange.markets)} markets loaded"
            )
            return True
        except ccxt.NetworkError as e:
            raise ConnectionError(
                f"Network error connecting to {self.exchange_name}: {e}"
            )
        except ccxt.ExchangeError as e:
            raise ConnectionError(
                f"Exchange error connecting to {self.exchange_name}: {e}"
            )

    def disconnect(self) -> None:
        """Close the exchange connection."""
        if self._exchange:
            try:
                self._exchange.close()
            except Exception:
                pass
            self._exchange = None
            self._markets_loaded = False
            self._subscribed_symbols.clear()
            logger.info(f"Disconnected from {self.exchange_name}")

    def is_connected(self) -> bool:
        """Check if the exchange connection is alive (markets loaded)."""
        return self._exchange is not None and self._markets_loaded

    def ensure_connection(self) -> bool:
        """Connect with retries if not already connected."""
        if self.is_connected():
            self._last_heartbeat = time.time()
            return True

        for attempt in range(5):
            try:
                if self.connect():
                    return True
            except Exception as e:
                logger.warning(
                    f"Reconnect attempt {attempt + 1}/5: {e}"
                )
                time.sleep(2 ** attempt)
        return False

    def load_markets(self) -> Dict:
        """Load markets from the exchange (required before trading)."""
        if not self._exchange:
            return {}
        try:
            markets = self._exchange.load_markets()
            self._markets_loaded = True
            return markets
        except Exception as e:
            logger.error(f"Failed to load markets: {e}")
            return {}

    # ── Data ──────────────────────────────────────────────────

    def _to_ccxt_timeframe(self, timeframe: str) -> str:
        """Convert our timeframe string to CCXT format."""
        if timeframe in TIMEFRAME_TO_CCXT:
            return TIMEFRAME_TO_CCXT[timeframe]
        # If it's already a CCXT format, return as-is
        if timeframe in CCXT_TO_TIMEFRAME:
            return timeframe
        # Try direct mapping from minutes
        minute_map = {
            1: "1m", 5: "5m", 15: "15m", 30: "30m",
            60: "1h", 120: "2h", 240: "4h", 1440: "1d", 10080: "1w",
        }
        try:
            minutes = int(timeframe)
            if minutes in minute_map:
                return minute_map[minutes]
        except (ValueError, TypeError):
            pass
        logger.warning(f"Unknown timeframe '{timeframe}', defaulting to 15m")
        return "15m"

    def _normalise_symbol(self, symbol: str) -> str:
        """Ensure symbol uses the exchange's market format (e.g. BTC/USDT)."""
        if "/" in symbol:
            return symbol.upper()
        # Try to find a matching market
        if self._exchange and self._exchange.markets:
            # If it looks like a MT5 symbol (XAUUSD), try to find market
            for market_id in self._exchange.markets:
                if market_id.replace("/", "").upper() == symbol.upper():
                    return market_id
                if market_id.split("/")[0].upper() == symbol.upper():
                    return market_id
        return symbol  # Let CCXT handle it

    def fetch_ohlcv(
        self, symbol: str, timeframe: str, count: int = 1000
    ) -> pd.DataFrame:
        """Fetch OHLCV candles from the exchange.

        Returns:
            DataFrame with columns [open, high, low, close, volume]
            and a datetime index.
        """
        if not self.ensure_connection():
            raise ConnectionError("Exchange not connected")

        symbol = self._normalise_symbol(symbol)
        tf = self._to_ccxt_timeframe(timeframe)
        limit = min(count, 1000)  # Most exchanges limit to 1000 per request

        try:
            raw = self._exchange.fetch_ohlcv(symbol, tf, limit=limit)
        except ccxt.BadSymbol:
            raise ExchangeError(f"Symbol '{symbol}' not found on {self.exchange_name}")
        except ccxt.NetworkError as e:
            raise ConnectionError(f"Network error fetching OHLCV: {e}")
        except Exception as e:
            raise ExchangeError(f"Failed to fetch OHLCV: {e}")

        if not raw or len(raw) == 0:
            raise ConnectionError(f"No OHLCV data received for {symbol}")

        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")
        return df

    def fetch_ticker(self, symbol: str) -> Dict[str, float]:
        """Get current ticker from the exchange."""
        if not self.ensure_connection():
            return {"bid": 0.0, "ask": 0.0, "last": 0.0, "time": 0}

        symbol = self._normalise_symbol(symbol)
        try:
            ticker = self._exchange.fetch_ticker(symbol)
            return {
                "bid": float(ticker.get("bid", 0) or 0),
                "ask": float(ticker.get("ask", 0) or 0),
                "last": float(ticker.get("last", 0) or 0),
                "time": int(ticker.get("timestamp", 0)),
                "high": float(ticker.get("high", 0) or 0),
                "low": float(ticker.get("low", 0) or 0),
                "baseVolume": float(ticker.get("baseVolume", 0) or 0),
                "quoteVolume": float(ticker.get("quoteVolume", 0) or 0),
                "change": float(ticker.get("change", 0) or 0),
                "percentage": float(ticker.get("percentage", 0) or 0),
            }
        except Exception as e:
            logger.error(f"fetch_ticker error: {e}")
            return {"bid": 0.0, "ask": 0.0, "last": 0.0, "time": 0}

    def fetch_order_book(
        self, symbol: str, limit: int = 10
    ) -> Dict[str, List[List[float]]]:
        """Get order book (bids/asks) for a symbol."""
        if not self.ensure_connection():
            return {"bids": [], "asks": []}
        symbol = self._normalise_symbol(symbol)
        try:
            book = self._exchange.fetch_order_book(symbol, limit)
            return {
                "bids": book.get("bids", []),
                "asks": book.get("asks", []),
            }
        except Exception as e:
            logger.error(f"fetch_order_book error: {e}")
            return {"bids": [], "asks": []}

    # ── Orders ────────────────────────────────────────────────

    def create_order(
        self,
        symbol: str,
        side: str,
        volume: float,
        order_type: str = "market",
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Place an order via CCXT.

        Args:
            symbol: Trading pair (e.g. BTC/USDT).
            side: 'buy' or 'sell'.
            volume: Amount in base currency.
            order_type: 'market' or 'limit'.
            price: Required for limit orders.
            sl: Stop-loss price (if supported).
            tp: Take-profit price (if supported).

        Returns:
            Dict with 'success', 'order_id', 'filled', etc.
        """
        if not self.ensure_connection():
            raise ConnectionError("Exchange not connected")

        symbol = self._normalise_symbol(symbol)
        side = side.lower()
        order_type = order_type.lower()

        # Validate
        if order_type == "limit" and price is None:
            raise InvalidPriceError("Limit orders require a price")

        # Get market info for amount precision
        market = self._exchange.market(symbol) if self._exchange else None
        if market:
            amount_precision = market.get("precision", {}).get("amount", 8)
            volume = round(volume, int(amount_precision))

        # SL/TP via order params (exchange-specific)
        order_params: Dict[str, Any] = {}
        if sl is not None:
            order_params["stopLossPrice"] = sl
        if tp is not None:
            order_params["takeProfitPrice"] = tp

        # Add any extra params from kwargs
        for key, val in kwargs.items():
            if key not in ("comment", "magic"):
                order_params[key] = val

        try:
            if order_type == "market":
                if side == "buy":
                    order = self._exchange.create_market_buy_order(
                        symbol, volume, params=order_params
                    )
                else:
                    order = self._exchange.create_market_sell_order(
                        symbol, volume, params=order_params
                    )
            elif order_type == "limit":
                if side == "buy":
                    order = self._exchange.create_limit_buy_order(
                        symbol, volume, price, params=order_params
                    )
                else:
                    order = self._exchange.create_limit_sell_order(
                        symbol, volume, price, params=order_params
                    )
            else:
                raise OrderError(f"Unsupported order type: {order_type}")

            filled = float(order.get("filled", 0) or volume)
            cost = float(order.get("cost", 0))
            avg_price = cost / filled if filled > 0 else (price or 0)

            logger.info(
                f"Order filled: {side.upper()} {volume} {symbol} @ {avg_price:.4f} "
                f"(id={order.get('id', '?')})"
            )
            return {
                "success": True,
                "order_id": str(order.get("id", "")),
                "order": order,
                "volume": filled,
                "price": avg_price,
                "cost": cost,
                "fee": order.get("fee", {}),
                "status": order.get("status", "closed"),
            }

        except ccxt.InsufficientFunds as e:
            raise OrderError(f"Insufficient funds: {e}")
        except ccxt.InvalidOrder as e:
            raise OrderError(f"Invalid order: {e}")
        except ccxt.RateLimitExceeded as e:
            logger.warning(f"Rate limit hit: {e}")
            time.sleep(self._exchange.rateLimit / 1000 if self._exchange else 1)
            raise OrderError(f"Rate limit: {e}")
        except ccxt.NetworkError as e:
            raise ConnectionError(f"Network error placing order: {e}")
        except Exception as e:
            raise OrderError(f"Order failed: {e}")

    def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """Cancel an open order by ID."""
        if not self.ensure_connection():
            return False

        sym = self._normalise_symbol(symbol) if symbol else None
        try:
            self._exchange.cancel_order(order_id, sym)
            logger.info(f"Order {order_id} cancelled")
            return True
        except ccxt.OrderNotFound:
            logger.warning(f"Order {order_id} not found")
            return False
        except Exception as e:
            logger.error(f"cancel_order error: {e}")
            return False

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all open orders."""
        if not self.ensure_connection():
            return []
        try:
            sym = self._normalise_symbol(symbol) if symbol else None
            orders = self._exchange.fetch_open_orders(sym)
            result = []
            for o in orders:
                result.append({
                    "id": str(o.get("id", "")),
                    "symbol": o.get("symbol", ""),
                    "side": o.get("side", ""),
                    "type": o.get("type", ""),
                    "volume": float(o.get("amount", 0)),
                    "filled": float(o.get("filled", 0)),
                    "price": float(o.get("price", 0)),
                    "status": o.get("status", ""),
                    "timestamp": o.get("timestamp", 0),
                })
            return result
        except Exception as e:
            logger.error(f"get_open_orders error: {e}")
            return []

    # ── Positions ─────────────────────────────────────────────

    def get_open_positions(
        self, symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get open positions from the exchange.

        For spot exchanges, this returns empty (no positions in spot mode).
        For futures, returns actual positions.
        """
        if not self.ensure_connection():
            return []

        try:
            if self._exchange and self._exchange.has.get("fetchPositions"):
                sym = self._normalise_symbol(symbol) if symbol else None
                positions = self._exchange.fetch_positions(sym)
                result = []
                for p in positions:
                    size = float(p.get("contracts", 0) or p.get("size", 0))
                    if size == 0:
                        continue
                    side = "BUY" if float(p.get("side", 1)) > 0 else "SELL"
                    pid = str(p.get("id", ""))
                    result.append({
                        "id": pid,
                        "ticket": pid,  # Alias for compatibility with bot.py/wallets.py
                        "symbol": p.get("symbol", ""),
                        "side": side,
                        "volume": abs(size),
                        "entry_price": float(p.get("entryPrice", 0) or p.get("price", 0)),
                        "current_price": float(p.get("markPrice", 0) or p.get("currentPrice", 0)),
                        "pnl": float(p.get("unrealizedPnl", 0) or p.get("pnl", 0)),
                        "leverage": float(p.get("leverage", 1)),
                        "margin": float(p.get("initialMargin", 0)),
                        "liquidation_price": float(p.get("liquidationPrice", 0) or 0),
                        "collateral": float(p.get("collateral", 0)),
                    })
                return result
            else:
                # Spot mode — no positions
                return []
        except Exception as e:
            logger.error(f"get_open_positions error: {e}")
            return []

    def close_position(self, position_id: str) -> Dict[str, Any]:
        """Close a position by creating an opposite order.

        For spot: creates a market sell order.
        For futures: creates a market order with reduceOnly flag.
        """
        logger.info(f"Closing position: {position_id}")

        # Try to get position details
        positions = self.get_open_positions()
        pos = None
        for p in positions:
            if p.get("id") == position_id or str(p.get("id", "")) == position_id:
                pos = p
                break

        if not pos:
            return {"success": False, "error": "Position not found"}

        sym = pos.get("symbol", self.symbol)
        volume = pos.get("volume", 0)
        side = "SELL" if pos.get("side") == "BUY" else "BUY"

        try:
            result = self.create_order(
                symbol=sym,
                side=side,
                volume=volume,
                order_type="market",
                reduce_only=True,  # passed as param
            )
            return result
        except Exception as e:
            logger.error(f"close_position error: {e}")
            return {"success": False, "error": str(e)}

    # ── Account ───────────────────────────────────────────────

    def get_balance(self) -> Dict[str, float]:
        """Get account balance from the exchange.

        Returns:
            Dict with 'balance', 'equity', 'margin', 'free_margin',
            and individual asset breakdown in 'assets'.
        """
        if not self.ensure_connection():
            return {"balance": 0, "equity": 0, "margin": 0, "free_margin": 0}

        try:
            balance = self._exchange.fetch_balance()

            # Calculate totals
            total_usd = 0.0
            free_usd = 0.0
            used_usd = 0.0

            # Extract quote currency from symbol (e.g. BTC/USDT → USDT)
            quote = self.symbol.split("/")[-1] if "/" in self.symbol else "USDT"
            if "total" in balance and quote in balance["total"]:
                total_usd = float(balance["total"][quote])
            if "free" in balance and quote in balance["free"]:
                free_usd = float(balance["free"][quote])
            if "used" in balance and quote in balance["used"]:
                used_usd = float(balance["used"][quote])

            return {
                "balance": total_usd,
                "equity": float(balance.get("total", {}).get(quote, total_usd)),
                "margin": used_usd,
                "free_margin": free_usd,
                "margin_level": 0.0,  # Not always available via CCXT
                "profit": 0.0,
                "assets": balance,  # Full dict for detailed inspection
            }
        except Exception as e:
            logger.error(f"get_balance error: {e}")
            return {"balance": 0, "equity": 0, "margin": 0, "free_margin": 0}

    def get_trade_history(self, days: int = 30) -> pd.DataFrame:
        """Fetch historical closed trades from the exchange."""
        if not self.ensure_connection():
            return pd.DataFrame()

        since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        try:
            # Use self.symbol — many exchanges require a symbol for fetch_my_trades
            trades = self._exchange.fetch_my_trades(symbol=self.symbol, since=since) 
            if not trades or len(trades) == 0:
                return pd.DataFrame()

            rows = []
            for t in trades:
                rows.append({
                    "time": datetime.fromtimestamp(t["timestamp"] / 1000),
                    "symbol": t.get("symbol", ""),
                    "side": t.get("side", ""),
                    "type": t.get("type", ""),
                    "volume": float(t.get("amount", 0)),
                    "price": float(t.get("price", 0)),
                    "cost": float(t.get("cost", 0)),
                    "fee": float(t.get("fee", {}).get("cost", 0)) if t.get("fee") else 0,
                    "fee_currency": t.get("fee", {}).get("currency", "") if t.get("fee") else "",
                    "profit": 0.0,  # CCXT doesn't provide P&L directly
                    "order_id": str(t.get("order", "")),
                })

            df = pd.DataFrame(rows)
            if len(df) > 0:
                df = df.sort_values("time", ascending=False)
            return df
        except Exception as e:
            logger.error(f"get_trade_history error: {e}")
            return pd.DataFrame()

    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol/trading pair metadata."""
        if not self._exchange or not self._exchange.markets:
            if not self.ensure_connection():
                return {
                    "trade_mode": None, "volume_min": 0.001,
                    "volume_step": 0.001, "volume_max": 1000.0,
                    "digits": 8, "point": 1e-8,
                }

        symbol = self._normalise_symbol(symbol)
        try:
            market = self._exchange.market(symbol)
            prec = market.get("precision", {})
            limits = market.get("limits", {})
            amount_limits = limits.get("amount", {})
            price_limits = limits.get("price", {})

            volume_min = float(amount_limits.get("min", 0.001))
            volume_max = float(amount_limits.get("max", 1000.0))
            volume_step = 10 ** (-int(prec.get("amount", 8)))

            digits = int(abs(np.log10(float(prec.get("price", 1e-8)))))
            point = float(prec.get("price", 1e-8))

            return {
                "trade_mode": "spot" if market.get("spot") else "future",
                "volume_min": volume_min,
                "volume_step": volume_step,
                "volume_max": volume_max,
                "digits": max(1, digits),
                "point": point,
                "precision": prec,
                "limits": limits,
                "tierBased": market.get("tierBased", False),
                "active": market.get("active", True),
                "contract_size": 1.0,  # Standard for most crypto
            }
        except Exception as e:
            logger.error(f"get_symbol_info error for {symbol}: {e}")
            return {
                "trade_mode": None, "volume_min": 0.001,
                "volume_step": 0.001, "volume_max": 1000.0,
                "digits": 8, "point": 1e-8,
            }

    def get_broker_time(self) -> datetime:
        """Get current exchange server time."""
        if not self.ensure_connection():
            return datetime.now()

        try:
            # Fetch server time via ticker
            ticker = self._exchange.fetch_ticker(self.symbol)
            ts = ticker.get("timestamp")
            if ts:
                return datetime.fromtimestamp(ts / 1000)
        except Exception:
            pass

        return datetime.now()

    def fetch_funding_rate(self, symbol: str) -> Dict[str, float]:
        """Fetch current funding rate for futures symbol."""
        if not self.ensure_connection():
            return {"funding_rate": 0.0, "funding_time": 0}
        symbol = self._normalise_symbol(symbol)
        try:
            rate = self._exchange.fetch_funding_rate(symbol)
            return {
                "funding_rate": float(rate.get("fundingRate", 0)),
                "funding_time": int(rate.get("fundingTimestamp", 0)),
            }
        except Exception as e:
            logger.debug(f"fetch_funding_rate not supported: {e}")
            return {"funding_rate": 0.0, "funding_time": 0}

    # ── Wait ──────────────────────────────────────────────────

    def wait_for_new_candle(
        self, timeframe_minutes: int = 15, buffer_seconds: int = 3
    ) -> bool:
        """Block until a new candle starts."""
        try:
            now = datetime.now()
            total = timeframe_minutes * 60
            secs = now.second + now.microsecond / 1_000_000
            cycle = (now.minute % timeframe_minutes) * 60 + secs
            wait = total - cycle + buffer_seconds
            if 1 < wait < 5:
                time.sleep(wait)
                return True
            return False
        except Exception as e:
            logger.error(f"wait_for_new_candle error: {e}")
            return False

    # ── Position Modification ─────────────────────────────────

    def modify_position(
        self,
        position_id: str,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        symbol: Optional[str] = None,
    ) -> bool:
        """Modify SL/TP on an open position.

        CCXT doesn't have a universal method for this, so we use
        exchange-specific params or cancel-recreate approach.
        """
        if not self.ensure_connection():
            return False

        try:
            sym = self._normalise_symbol(symbol) if symbol else None
            params: Dict[str, Any] = {}
            if sl is not None:
                params["stopLossPrice"] = sl
            if tp is not None:
                params["takeProfitPrice"] = tp

            if params:
                # Try editOrder if supported
                if self._exchange and self._exchange.has.get("editOrder"):
                    self._exchange.edit_order(position_id, sym, params=params)
                    return True

                # Otherwise, place a stop-loss/take-profit order
                if sl is not None:
                    position = None
                    for p in self.get_open_positions():
                        if p.get("id") == position_id:
                            position = p
                            break
                    if position:
                        side = "sell" if position.get("side") == "BUY" else "buy"
                        self._exchange.create_order(
                            sym or position.get("symbol", ""),
                            type="stop_loss_limit",
                            side=side,
                            amount=position.get("volume", 0),
                            price=sl,
                            params={"stopPrice": sl},
                        )
                        return True
            return False
        except Exception as e:
            logger.error(f"modify_position error: {e}")
            return False

    # ── Symbol Listing ────────────────────────────────────────

    def get_symbols(self) -> List[str]:
        """Return list of all available trading symbols."""
        if not self._exchange or not self._exchange.markets:
            if not self.ensure_connection():
                return []
        return list(self._exchange.markets.keys())

    def get_symbols_active(self) -> List[str]:
        """Return list of active (tradable) symbols only."""
        if not self._exchange or not self._exchange.markets:
            if not self.ensure_connection():
                return []
        return [
            s for s, m in self._exchange.markets.items()
            if m.get("active", True)
        ]

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def validate_volume(
        volume: float,
        volume_min: float = 0.001,
        volume_max: float = 1000.0,
        volume_step: float = 0.001,
    ) -> float:
        """Round volume to step and clamp within limits."""
        if volume <= 0:
            return volume_min
        if volume_step > 0:
            volume = round(volume / volume_step) * volume_step
        return max(volume_min, min(volume, volume_max))

    def _normalise_price(self, symbol: str, price: float) -> float:
        """Round price to symbol precision."""
        info = self.get_symbol_info(symbol)
        point = info.get("point", 1e-8)
        digits = info.get("digits", 8)
        if point > 0:
            return round(price, int(abs(np.log10(point))))
        return round(price, digits)

    @staticmethod
    def _default_sl(price: float, side: str, pct: float = 0.015) -> float:
        """Default stop-loss 1.5% away."""
        return price * (1 - pct) if side.upper() == "BUY" else price * (1 + pct)

    @staticmethod
    def _default_tp(price: float, side: str, pct: float = 0.03) -> float:
        """Default take-profit 3% away."""
        return price * (1 + pct) if side.upper() == "BUY" else price * (1 - pct)

    # ── Advanced Order Types ───────────────────────────────────

    def create_stop_loss_limit_order(self, symbol: str, side: str, volume: float,
                                      stop_price: float, limit_price: float,
                                      **kwargs) -> Dict[str, Any]:
        """Place a stop-loss-limit order via CCXT.

        Uses the unified ``stop_loss_limit`` order type if the exchange
        supports it; otherwise falls back to ``stop`` type with ``price``
        as the limit price and ``stopPrice`` as the trigger.
        """
        if not self.ensure_connection():
            raise ConnectionError("Exchange not connected")

        symbol = self._normalise_symbol(symbol)
        side = side.lower()

        # Check exchange capabilities
        has_stop_loss_limit = self._exchange and self._exchange.has.get("stopLossLimit", False)
        order_params: Dict[str, Any] = {}

        # Forward kwargs
        for k, v in kwargs.items():
            if k not in ("comment", "magic", "reduce_only"):
                order_params[k] = v

        try:
            if has_stop_loss_limit:
                # Native stop-loss-limit
                order = self._exchange.create_order(
                    symbol, "stop_loss_limit", side, volume,
                    price=limit_price,
                    params={**order_params, "stopPrice": stop_price},
                )
            else:
                # Fallback: use stop type with limit price
                order = self._exchange.create_order(
                    symbol, "stop", side, volume,
                    price=limit_price,
                    params={**order_params, "stopPrice": stop_price},
                )

            return {
                "success": True,
                "order_id": str(order.get("id", "")),
                "order": order,
                "volume": float(order.get("filled", 0) or volume),
                "price": limit_price,
                "status": order.get("status", "open"),
                "type": "stop_loss_limit",
            }
        except ccxt.InsufficientFunds as e:
            raise OrderError(f"Insufficient funds: {e}")
        except ccxt.InvalidOrder as e:
            raise OrderError(f"Invalid order: {e}")
        except Exception as e:
            raise OrderError(f"stop-loss-limit failed: {e}")

    def create_oco_order(self, symbol: str, side: str, volume: float,
                          price: float, stop_loss_price: float,
                          take_profit_price: float,
                          **kwargs) -> Dict[str, Any]:
        """Place an OCO (One-Cancels-Other) order via CCXT.

        Many exchanges support this natively via params.oco or
        ``triggerInstructions``. Falls back to creating two separate
        orders (limit TP + stop SL) if OCO is not natively supported.
        """
        if not self.ensure_connection():
            raise ConnectionError("Exchange not connected")

        symbol = self._normalise_symbol(symbol)
        side = side.lower()
        opposite_side = "sell" if side == "buy" else "buy"

        has_oco = self._exchange and self._exchange.has.get("OCO", False)
        order_params: Dict[str, Any] = {}
        for k, v in kwargs.items():
            if k not in ("comment", "magic", "reduce_only"):
                order_params[k] = v

        try:
            if has_oco:
                # Native OCO support
                order = self._exchange.create_order(
                    symbol, "oco", side, volume,
                    price=price,
                    params={
                        **order_params,
                        "stopLossPrice": stop_loss_price,
                        "takeProfitPrice": take_profit_price,
                    },
                )
                return {
                    "success": True,
                    "order_id": str(order.get("id", "")),
                    "order": order,
                    "type": "oco",
                    "status": order.get("status", "open"),
                }
            else:
                # Fallback: place TP limit + SL stop separately
                tp_order = self._exchange.create_limit_order(
                    symbol, opposite_side if side == "buy" else side,
                    volume, take_profit_price,
                    params=order_params,
                )
                sl_order = self._exchange.create_order(
                    symbol, "stop", opposite_side if side == "buy" else side,
                    volume,
                    price=stop_loss_price,
                    params={
                        **order_params,
                        "stopPrice": stop_loss_price,
                        "reduceOnly": True,
                    },
                )
                return {
                    "success": True,
                    "take_profit_order_id": str(tp_order.get("id", "")),
                    "stop_loss_order_id": str(sl_order.get("id", "")),
                    "type": "oco_fallback",
                    "status": "open",
                }
        except ccxt.InsufficientFunds as e:
            raise OrderError(f"Insufficient funds: {e}")
        except ccxt.InvalidOrder as e:
            raise OrderError(f"Invalid order: {e}")
        except Exception as e:
            raise OrderError(f"OCO order failed: {e}")
