"""
REST API backend — FastAPI server for external bot control.

Inspired by Freqtrade's REST API. Runs in a background thread alongside
the bot. All endpoints require an API key (set in config).

Endpoints:
    GET  /ping          — Health check
    GET  /status        — Bot status
    POST /start         — Start auto trading
    POST /stop          — Stop auto trading
    GET  /balance       — Account balance
    GET  /profit        — Profit summary
    GET  /trades        — Trade history
    POST /forcebuy      — Force buy a pair
    POST /forcesell     — Force sell a position
    GET  /daily         — Daily stats
    GET  /config        — Show config
    GET  /positions     — Open positions
"""
import asyncio
import threading
import time
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Header, Query

from src.utils.logging import get_logger

logger = get_logger(__name__)


class RestAPI:
    """FastAPI-based REST server that runs in a daemon thread.

    Usage::

        api = RestAPI(bot, host="0.0.0.0", port=8080, api_key="secret")
        api.start()
        # ... bot runs ...
        api.stop()
    """

    def __init__(self, bot: Any, host: str = "0.0.0.0",
                 port: int = 8080, api_key: str = ""):
        self.bot = bot
        self.host = host
        self.port = port
        self.api_key = api_key
        self._app: Optional[FastAPI] = None
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ── Lifecycle ────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="rest-api")
        self._thread.start()
        logger.info(f"REST API starting on {self.host}:{self.port}")

    def stop(self) -> None:
        self._running = False
        if self._server:
            self._server.should_exit = True

    def _run(self) -> None:
        self._app = self._create_app()
        config = uvicorn.Config(
            self._app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
            loop="asyncio",
        )
        self._server = uvicorn.Server(config)
        try:
            asyncio.run(self._server.serve())
        except Exception as e:
            logger.error(f"REST API serve error: {e}")

    # ── Auth ─────────────────────────────────────────────────

    def _verify_api_key(self, x_api_key: Optional[str] = Header(None)) -> None:
        if not self.api_key:
            return  # no key = open
        if x_api_key != self.api_key:
            raise HTTPException(status_code=403, detail="Invalid API key")

    # ── App Factory ──────────────────────────────────────────

    def _create_app(self) -> FastAPI:
        app = FastAPI(title="AI Trading Bot API", version="2.0")

        @app.get("/ping")
        def ping(x_api_key: Optional[str] = Header(None)):
            self._verify_api_key(x_api_key)
            return {"status": "pong", "timestamp": time.time()}

        @app.get("/status")
        def status(x_api_key: Optional[str] = Header(None)):
            self._verify_api_key(x_api_key)
            return _serialise_status(self.bot.status())

        @app.post("/start")
        def start(x_api_key: Optional[str] = Header(None)):
            self._verify_api_key(x_api_key)
            if getattr(self.bot, "auto_trading", False):
                return {"status": "already_running"}
            self.bot.auto_trading = True
            setattr(self.bot, "_last_cycle_time", time.time())
            from src.rpc.websocket import set_shared
            set_shared("auto_trading", True)
            return {"status": "started"}

        @app.post("/stop")
        def stop(x_api_key: Optional[str] = Header(None)):
            self._verify_api_key(x_api_key)
            if not getattr(self.bot, "auto_trading", False):
                return {"status": "already_stopped"}
            self.bot.auto_trading = False
            from src.rpc.websocket import set_shared
            set_shared("auto_trading", False)
            return {"status": "stopped"}

        @app.get("/balance")
        def balance(x_api_key: Optional[str] = Header(None)):
            self._verify_api_key(x_api_key)
            try:
                bal = self.bot.exchange.get_balance()
                return bal
            except Exception as e:
                raise HTTPException(500, str(e))

        @app.get("/profit")
        def profit(x_api_key: Optional[str] = Header(None)):
            self._verify_api_key(x_api_key)
            try:
                trades = self.bot.trade_manager.closed_trades
                total_pnl = sum(t.profit for t in trades if t.profit)
                win = sum(1 for t in trades if t.profit > 0)
                lose = sum(1 for t in trades if t.profit < 0)
                return {
                    "total_profit": round(total_pnl, 2),
                    "win_trades": win,
                    "lose_trades": lose,
                    "total_trades": len(trades),
                    "win_rate": round(win / len(trades) * 100, 1) if trades else 0,
                    "drawdown": self.bot.risk.get_drawdown_pct(),
                }
            except Exception as e:
                raise HTTPException(500, str(e))

        @app.get("/trades")
        def trades(limit: int = Query(20, ge=1, le=500),
                   x_api_key: Optional[str] = Header(None)):
            self._verify_api_key(x_api_key)
            try:
                closed = self.bot.trade_manager.closed_trades[-limit:]
                return [t.to_dict() for t in closed]
            except Exception as e:
                raise HTTPException(500, str(e))

        @app.post("/forcebuy")
        def forcebuy(pair: str = Query(...),
                     volume: Optional[float] = Query(None),
                     x_api_key: Optional[str] = Header(None)):
            self._verify_api_key(x_api_key)
            try:
                result = self.bot.execute_trade(1, volume=volume)
                if result.get("success"):
                    return {"status": "ok", "order": result}
                raise HTTPException(400, result.get("error", "Buy failed"))
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(500, str(e))

        @app.post("/forcesell")
        def forcesell(ticket: Optional[int] = Query(None),
                      x_api_key: Optional[str] = Header(None)):
            self._verify_api_key(x_api_key)
            try:
                if ticket:
                    result = self.bot.close_position(ticket)
                    if result.get("success"):
                        return {"status": "ok", "closed": str(ticket)}
                    raise HTTPException(400, result.get("error", "Sell failed"))
                # Close all
                results = []
                positions = self.bot.exchange.get_open_positions(self.bot.symbol)
                for p in positions:
                    tid = p.get("ticket") or p.get("id")
                    if tid:
                        r = self.bot.close_position(tid)
                        results.append(str(r))
                return {"status": "ok", "closed": len(results)}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(500, str(e))

        @app.get("/daily")
        def daily(x_api_key: Optional[str] = Header(None)):
            self._verify_api_key(x_api_key)
            try:
                from src.repositories.trade_repo import TradeRepository
                from src.persistence.database import get_db
                repo = TradeRepository(get_db())
                summary = repo.summary(days=1)
                return summary
            except Exception as e:
                raise HTTPException(500, str(e))

        @app.get("/config")
        def config(x_api_key: Optional[str] = Header(None)):
            self._verify_api_key(x_api_key)
            return self.bot.config.to_dict()

        @app.get("/positions")
        def positions(x_api_key: Optional[str] = Header(None)):
            self._verify_api_key(x_api_key)
            try:
                pos = self.bot.exchange.get_open_positions(self.bot.symbol)
                return {"positions": pos, "count": len(pos)}
            except Exception as e:
                raise HTTPException(500, str(e))

        return app


def _serialise_status(s: Dict[str, Any]) -> Dict[str, Any]:
    """Convert complex status dict to JSON-safe format."""
    result = {}
    for k, v in s.items():
        if isinstance(v, dict):
            result[k] = _serialise_status(v)
        elif isinstance(v, (list, tuple)):
            result[k] = [str(x) if not isinstance(x, (int, float, str, bool, type(None))) else x
                         for x in v]
        elif isinstance(v, (int, float, str, bool, type(None))):
            result[k] = v
        else:
            result[k] = str(v)
    return result
