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
from src.utils.logging import get_logger

logger = get_logger(__name__)

# ── Cross-thread shared state ────────────────────────────────
_shared_state: Dict[str, Any] = {}
_shared_lock = threading.Lock()
_active_server = None
_active_server_lock = threading.Lock()


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

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.latest_data: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop = None
        self._thread: threading.Thread = None
        self._running = False
        self.server = None

    def name(self) -> str:
        return f"WebSocket ({self.host}:{self.port})"

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Broadcast a text message to all clients."""
        self.broadcast({"type": "message", "text": message})
        return True

    # ── Lifecycle ─────────────────────────────────────────────

    def start(self) -> None:
        global _active_server
        if self._running:
            return

        with _active_server_lock:
            if _active_server is not None:
                try:
                    logger.info("Stopping previous WebSocket server instance...")
                    _active_server.stop()
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Error stopping previous WS server: {e}")
            _active_server = self

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True,
                                        name="ws-server")
        self._thread.start()
        logger.info(f"WS server starting on ws://{self.host}:{self.port}")

    def stop(self) -> None:
        self._running = False
        if self.server:
            try:
                self.server.close()
            except Exception:
                pass
        if self._loop and self._loop.is_running():
            try:
                def _cancel_all():
                    for task in asyncio.all_tasks(self._loop):
                        task.cancel()
                self._loop.call_soon_threadsafe(_cancel_all)
            except Exception:
                pass

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
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"WS loop error: {e}")
        finally:
            try:
                # Cancel any remaining tasks
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            try:
                self._loop.close()
            except Exception:
                pass
            self._loop = None



    async def _serve(self) -> None:
        while self._running:
            try:
                self.server = await websockets.serve(
                    self._handler, self.host, self.port,
                    ping_interval=20, ping_timeout=10,
                )
                set_shared("ws_port", self.port)
                logger.info(f"WS ready on ws://{self.host}:{self.port}")
                
                while self._running:
                    await asyncio.sleep(0.5)
                
                self.server.close()
                await self.server.wait_closed()
                return
            except OSError as e:
                logger.warning(f"WS server port {self.port} in use, retrying in 0.5s... (Error: {e})")
                await asyncio.sleep(0.5)

    async def _handler(self, ws: WebSocketServerProtocol) -> None:
        self.clients.add(ws)
        remote = ws.remote_address
        logger.info(f"WS client connected: {remote}")
        try:
            with self._lock:
                if self.latest_data:
                    await ws.send(json.dumps(self.latest_data))
            async for message in ws:
                try:
                    payload = json.loads(message)
                    action = payload.get("action")
                    if action == "close_position" and getattr(self, "bot", None):
                        ticket = int(payload.get("ticket"))
                        logger.info(f"WS client requested close position: ticket={ticket}")
                        result = self.bot.close_position(ticket)
                        if result.get("success"):
                            await ws.send(json.dumps({
                                "type": "action_result",
                                "success": True,
                                "message": f"Position #{ticket} closed successfully!"
                            }))
                        else:
                            await ws.send(json.dumps({
                                "type": "action_result",
                                "success": False,
                                "message": f"Failed to close position: {result.get('error', 'Unknown error')}"
                            }))
                    elif action == "start_auto_trade" and getattr(self, "bot", None):
                        logger.info("WS client requested start auto trading")
                        if self.bot.exchange.connect() and self.bot.exchange.is_connected():
                            self.bot.config.set_global("general", "auto_trade", True)
                            set_shared("auto_trading", True)
                            worker = getattr(self.bot, "worker", None)
                            if worker:
                                worker.start()
                            with self._lock:
                                if self.latest_data and "status" in self.latest_data:
                                    self.latest_data["status"]["auto_trading"] = True
                            if self.latest_data:
                                await self._do_broadcast(self.latest_data)
                            await ws.send(json.dumps({
                                "type": "action_result",
                                "success": True,
                                "message": "Auto Trading started!"
                            }))
                        else:
                            await ws.send(json.dumps({
                                "type": "action_result",
                                "success": False,
                                "message": "Failed to start Auto Trading: MT5 connection failed!"
                            }))
                    elif action == "stop_auto_trade" and getattr(self, "bot", None):
                        logger.info("WS client requested stop auto trading")
                        self.bot.config.set_global("general", "auto_trade", False)
                        set_shared("auto_trading", False)
                        worker = getattr(self.bot, "worker", None)
                        if worker:
                            worker.stop()
                        with self._lock:
                            if self.latest_data and "status" in self.latest_data:
                                self.latest_data["status"]["auto_trading"] = False
                        if self.latest_data:
                            await self._do_broadcast(self.latest_data)
                        await ws.send(json.dumps({
                            "type": "action_result",
                            "success": True,
                            "message": "Auto Trading stopped!"
                        }))
                    elif action == "open_trade" and getattr(self, "bot", None):
                        sym = payload.get("symbol")
                        side = payload.get("side")
                        vol = float(payload.get("volume", 0.1))
                        logger.info(f"WS client requested open trade: {side} {vol} {sym}")
                        result = self.bot.open_trade(sym, side, vol)
                        if result.get("success"):
                            await ws.send(json.dumps({
                                "type": "action_result",
                                "success": True,
                                "message": f"Successfully executed {side.upper()} order!"
                            }))
                        else:
                            await ws.send(json.dumps({
                                "type": "action_result",
                                "success": False,
                                "message": f"Failed to execute order: {result.get('error', 'Unknown error')}"
                            }))
                except Exception as e:
                    logger.error(f"WS message handling error: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(ws)
            logger.info(f"WS client disconnected: {remote}")

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



