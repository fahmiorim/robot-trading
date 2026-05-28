"""
WebSocket RPC backend — real-time streaming of market data to the dashboard.

Ported from the old ``src/ws_server.py``, refactored to use the new
exchange interface and RPC base.
"""
import asyncio
import json
import threading
import time
from typing import Any, Dict, Set

import websockets
from websockets.server import WebSocketServerProtocol

from src.rpc.base import IRPC
from src.exchange.base import IExchange
from src.configuration.manager import ConfigManager
from src.utils.logging import get_logger

logger = get_logger(__name__)

# ── Cross-thread shared state ────────────────────────────────
_shared_state: Dict[str, Any] = {}
_shared_lock = threading.Lock()


def set_shared(key: str, value: Any) -> None:
    with _shared_lock:
        _shared_state[key] = value


def get_shared(key: str, default: Any = None) -> Any:
    with _shared_lock:
        return _shared_state.get(key, default)


class WebSocketRPC(IRPC):
    """WebSocket server that streams live data to dashboard clients.

    Runs in a background daemon thread alongside the main bot.
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.latest_data: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop = None
        self._thread: threading.Thread = None
        self._running = False

    def name(self) -> str:
        return f"WebSocket ({self.host}:{self.port})"

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Broadcast a text message to all clients."""
        self.broadcast({"type": "message", "text": message})
        return True

    # ── Lifecycle ─────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True,
                                        name="ws-server")
        self._thread.start()
        logger.info(f"WS server starting on ws://{self.host}:{self.port}")

    def stop(self) -> None:
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    def broadcast(self, data: Dict[str, Any]) -> None:
        """Thread-safe: push data to all connected clients."""
        with self._lock:
            self.latest_data = data
        if self._loop and self._running and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._do_broadcast(data), self._loop)

    # ── Internal ──────────────────────────────────────────────

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception as e:
            logger.error(f"WS loop error: {e}")
        finally:
            self._loop.close()
            self._loop = None

    async def _serve(self) -> None:
        for attempt in range(10):
            port = self.port + attempt
            try:
                async with websockets.serve(
                    self._handler, self.host, port,
                    ping_interval=20, ping_timeout=10,
                ):
                    self.port = port
                    set_shared("ws_port", port)
                    logger.info(f"WS ready on ws://{self.host}:{port}")
                    await asyncio.Future()  # run forever
                    return
            except OSError:
                if attempt < 9:
                    continue
                raise
        logger.warning(f"All ports {self.port}–{self.port + 9} in use")

    async def _handler(self, ws: WebSocketServerProtocol) -> None:
        self.clients.add(ws)
        remote = ws.remote_address
        logger.debug(f"WS client: {remote}")
        try:
            with self._lock:
                if self.latest_data:
                    await ws.send(json.dumps(self.latest_data))
            async for _ in ws:
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(ws)

    async def _do_broadcast(self, data: Dict[str, Any]) -> None:
        if not self.clients:
            return
        msg = json.dumps(data, default=str)
        dead = set()
        for c in self.clients:
            try:
                await c.send(msg)
            except websockets.exceptions.ConnectionClosed:
                dead.add(c)
        self.clients -= dead


def start_data_pusher(ws: WebSocketRPC, exchange: IExchange,
                       config: ConfigManager) -> None:
    """Start background thread that polls the exchange and broadcasts."""
    def _push():
        err_count = 0
        while True:
            try:
                symbol = config.get("general", "symbol")
                ticker = exchange.fetch_ticker(symbol)
                balance = exchange.get_balance()
                positions = exchange.get_open_positions(symbol)
                regime = get_shared("regime", "unknown")
                auto = get_shared("auto_trading", False)
                strategy = get_shared("best_strategy", "N/A")

                data = {
                    "type": "market_data",
                    "timestamp": time.time(),
                    "price": {
                        "symbol": symbol,
                        "bid": ticker.get("bid"),
                        "ask": ticker.get("ask"),
                        "spread": round(ticker.get("ask", 0) - ticker.get("bid", 0), 2)
                        if ticker.get("ask") and ticker.get("bid") else None,
                    },
                    "account": {
                        "balance": balance.get("balance"),
                        "equity": balance.get("equity"),
                        "free_margin": balance.get("free_margin"),
                        "margin_level": balance.get("margin_level"),
                    },
                    "positions": {"count": len(positions)},
                    "status": {
                        "auto_trading": auto,
                        "regime": regime.upper(),
                        "best_strategy": strategy,
                        "mt5_connected": exchange.is_connected(),
                    },
                }
                ws.broadcast(data)
                err_count = 0
            except Exception:
                err_count += 1
                if err_count > 10:
                    time.sleep(10)
            time.sleep(1.5)

    t = threading.Thread(target=_push, daemon=True, name="ws-pusher")
    t.start()
    logger.info("WS pusher started (every 1.5s)")
